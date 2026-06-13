#!/usr/bin/env python3
# A (discriminating version) — ternary-QAT RWKV-7 on BYTE-LM (continuous CE, where post-hoc
# ternary is KNOWN to collapse). Question: does BitNet-b1.58 QAT (STE) recover what post-hoc
# ternary destroys? Corpus = local repo text (no network). Controlled A/B, multi-seed, held-out CE.
import sys, time, glob, os
import torch, torch.nn as nn, torch.nn.functional as F, numpy as np
torch.set_num_threads(4); DEV="cpu"

# ---------- quantized linear (weight-only STE) ----------
class QLinear(nn.Module):
    def __init__(self,i,o): super().__init__(); self.w=nn.Parameter(torch.randn(o,i)*(i**-0.5)); self.mode="fp32"
    def qw(self):
        W=self.w
        if self.mode=="fp32": return W
        if self.mode=="int8":
            s=W.abs().amax(1,keepdim=True).clamp(min=1e-5)/127.0; Wq=(W/s).round().clamp(-127,127)*s
        else:
            s=W.abs().mean(1,keepdim=True).clamp(min=1e-5); Wq=(W/s).round().clamp(-1,1)*s
        return W+(Wq-W).detach()
    def forward(self,x): return x@self.qw().t()
def set_mode(m,mode):
    for mod in m.modules():
        if isinstance(mod,QLinear): mod.mode=mode

class TimeMix(nn.Module):
    def __init__(self,C,H):
        super().__init__(); self.C,self.H,self.N=C,H,C//H
        self.mr,self.mw,self.mk,self.mv,self.ma=(nn.Parameter(torch.rand(C)*0.2) for _ in range(5))
        self.r,self.k,self.v,self.o=QLinear(C,C),QLinear(C,C),QLinear(C,C),QLinear(C,C)
        self.wdec,self.agen=nn.Linear(C,C),nn.Linear(C,C); self.gn=nn.GroupNorm(H,C)
    def forward(self,x):
        B,T,C=x.shape; H,N=self.H,self.N
        xs=F.pad(x,(0,0,1,0))[:,:-1]; lp=lambda m:x+(xs-x)*m
        r=self.r(lp(self.mr)).view(B,T,H,N); k=self.k(lp(self.mk)).view(B,T,H,N); v=self.v(lp(self.mv)).view(B,T,H,N)
        w=torch.sigmoid(self.wdec(lp(self.mw))).view(B,T,H,N); a=torch.sigmoid(self.agen(lp(self.ma))).view(B,T,H,N)
        kk=F.normalize(k,dim=-1); S=torch.zeros(B,H,N,N,device=x.device,dtype=x.dtype); ys=[]
        for t in range(T):
            wt,kt,at,vt,k2,rt=w[:,t],kk[:,t],a[:,t],v[:,t],k[:,t],r[:,t]
            S=S*wt.unsqueeze(2); Skk=(S*kt.unsqueeze(2)).sum(-1)
            S=S-Skk.unsqueeze(-1)*(kt*at).unsqueeze(2); S=S+vt.unsqueeze(-1)*k2.unsqueeze(2)
            ys.append((S*rt.unsqueeze(2)).sum(-1).reshape(B,C))
        y=torch.stack(ys,1); y=self.gn(y.reshape(B*T,C)).reshape(B,T,C); return self.o(y)
class ChanMix(nn.Module):
    def __init__(self,C): super().__init__(); self.mk=nn.Parameter(torch.rand(C)*0.2); self.k,self.v=QLinear(C,4*C),QLinear(4*C,C)
    def forward(self,x): xs=F.pad(x,(0,0,1,0))[:,:-1]; return self.v(torch.relu(self.k(x+(xs-x)*self.mk))**2)
class Block(nn.Module):
    def __init__(self,C,H): super().__init__(); self.ln1,self.ln2=nn.LayerNorm(C),nn.LayerNorm(C); self.tm,self.cm=TimeMix(C,H),ChanMix(C)
    def forward(self,x): x=x+self.tm(self.ln1(x)); return x+self.cm(self.ln2(x))
class RWKV7(nn.Module):
    def __init__(self,V,C,H,L): super().__init__(); self.emb=nn.Embedding(V,C); self.blocks=nn.ModuleList([Block(C,H) for _ in range(L)]); self.ln_out=nn.LayerNorm(C); self.head=nn.Linear(C,V)
    def forward(self,idx):
        x=self.emb(idx)
        for b in self.blocks: x=b(x)
        return self.head(self.ln_out(x))

# ---------- corpus: local repo text, byte-level ----------
def load_corpus(maxbytes=500_000):
    root=os.path.expanduser(os.environ.get("CORPUS_DIR","./corpus"))  # ~1MB of any UTF-8 text; we used our local research notes (PoC corpus, not a benchmark)
    files=sorted(glob.glob(root+"/**/*.md",recursive=True))[:120]
    buf=bytearray()
    for f in files:
        try: buf+=open(f,"rb").read()+b"\n\n"
        except: pass
        if len(buf)>=maxbytes: break
    data=np.frombuffer(bytes(buf[:maxbytes]),dtype=np.uint8).astype(np.int64)
    n=len(data); tr=data[:int(n*0.9)]; ev=data[int(n*0.9):]
    return tr,ev
TR,EV=load_corpus()
print(f"[lm] corpus train={len(TR)}B held-out={len(EV)}B",flush=True)
def batch(arr,B,T,g):
    ix=torch.randint(0,len(arr)-T-1,(B,),generator=g)
    x=torch.stack([torch.from_numpy(arr[i:i+T].copy()) for i in ix])
    y=torch.stack([torch.from_numpy(arr[i+1:i+1+T].copy()) for i in ix])
    return x.to(DEV),y.to(DEV)
def eval_ce(model,T,iters=20,B=32):
    model.eval(); g=torch.Generator().manual_seed(999); tot=0.;n=0
    with torch.no_grad():
        for _ in range(iters):
            x,y=batch(EV,B,T,g); lg=model(x)
            tot+=F.cross_entropy(lg.view(-1,256),y.view(-1)).item()*y.numel(); n+=y.numel()
    model.train(); return tot/n/np.log(2)  # bits/byte
def train_one(mode,seed,steps,C,H,L,T,B,lr,posthoc=False):
    torch.manual_seed(seed); g=torch.Generator().manual_seed(seed+1)
    model=RWKV7(256,C,H,L).to(DEV); set_mode(model,"fp32" if posthoc else mode)
    opt=torch.optim.AdamW(model.parameters(),lr=lr,betas=(0.9,0.95),weight_decay=0.01)
    for s in range(steps):
        x,y=batch(TR,B,T,g); lg=model(x)
        loss=F.cross_entropy(lg.view(-1,256),y.view(-1))
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
    if posthoc: set_mode(model,"tern")
    return eval_ce(model,T)

C,H,L,T,B,lr=64,2,2,96,32,2e-3
STEPS=1200; SEEDS=[0,1]; CONDS=["fp32","tern","tern_posthoc"]
print(f"[lm] RWKV-7 byte-LM QAT | C={C} L={L} T={T} steps={STEPS} seeds={SEEDS}",flush=True)
import csv; rows=[]
for cond in CONDS:
    ces=[]
    for sd in SEEDS:
        t0=time.time(); ph=(cond=="tern_posthoc"); mode="tern" if ph else cond
        ce=train_one(mode,sd,STEPS,C,H,L,T,B,lr,posthoc=ph); ces.append(ce)
        print(f"  {cond:13s} seed={sd} CE={ce:.4f} bits/byte  ({time.time()-t0:.0f}s)",flush=True)
    m,s=float(np.mean(ces)),float(np.std(ces)); rows.append({"cond":cond,"ce_mean":round(m,4),"ce_std":round(s,4)})
    print(f"  => {cond:13s} CE={m:.4f} ± {s:.4f}",flush=True)
fp=[r for r in rows if r["cond"]=="fp32"][0]["ce_mean"]
print("\n[lm] SUMMARY (held-out bits/byte, lower=better; Δ vs fp32):",flush=True)
for r in rows:
    print(f"  {r['cond']:13s} {r['ce_mean']:.4f} ± {r['ce_std']:.4f}   Δ={r['ce_mean']-fp:+.4f}",flush=True)
with open(os.path.expanduser("~/hdc_scratch/rwkv_test/qat_lm_ce.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["cond","ce_mean","ce_std"]); w.writeheader(); w.writerows(rows)
print("[lm] wrote qat_lm_ce.csv\n[lm] DONE",flush=True)
