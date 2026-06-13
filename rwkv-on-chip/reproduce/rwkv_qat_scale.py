#!/usr/bin/env python3
# 上二 — SCALING study: does the ternary-QAT vs fp32 byte-LM gap SHRINK with model size?
# Pre-reg: gap(ternary-QAT) monotonically decreases across a size ladder => +0.21 was an upper
# bound, native ternary RWKV holds at scale. RWKV-standard head_size=64. Bigger (1MB) corpus.
import sys, time, glob, os
import torch, torch.nn as nn, torch.nn.functional as F, numpy as np
torch.set_num_threads(4); DEV="cpu"; HEAD=64

class QLinear(nn.Module):
    def __init__(self,i,o): super().__init__(); self.w=nn.Parameter(torch.randn(o,i)*(i**-0.5)); self.mode="fp32"
    def qw(self):
        W=self.w
        if self.mode=="fp32": return W
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
        self.r_k=nn.Parameter(torch.zeros(H,self.N))
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
            yt=(S*rt.unsqueeze(2)).sum(-1)                          # (B,H,N) = S@r
            yt=yt+ (rt*k2*self.r_k).sum(-1,keepdim=True)*vt         # r_k bonus (RWKV-7 faithful)
            ys.append(yt.reshape(B,C))
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

def load_corpus(maxbytes=1_000_000):
    root=os.path.expanduser(os.environ.get("CORPUS_DIR","./corpus"))  # ~1MB of any UTF-8 text; we used our local research notes (PoC corpus, not a benchmark)
    files=sorted(glob.glob(root+"/**/*.md",recursive=True))+sorted(glob.glob(root+"/**/*.py",recursive=True))
    buf=bytearray()
    for f in files:
        try: buf+=open(f,"rb").read()+b"\n\n"
        except: pass
        if len(buf)>=maxbytes: break
    data=np.frombuffer(bytes(buf[:maxbytes]),dtype=np.uint8).astype(np.int64); n=len(data)
    return data[:int(n*0.9)], data[int(n*0.9):]
TR,EV=load_corpus(); print(f"[scale] corpus train={len(TR)}B held-out={len(EV)}B",flush=True)
def batch(arr,B,T,g):
    ix=torch.randint(0,len(arr)-T-1,(B,),generator=g)
    x=torch.stack([torch.from_numpy(arr[i:i+T].copy()) for i in ix]); y=torch.stack([torch.from_numpy(arr[i+1:i+1+T].copy()) for i in ix])
    return x.to(DEV),y.to(DEV)
def eval_ce(model,T,iters=20,B=32):
    model.eval(); g=torch.Generator().manual_seed(999); tot=0.;n=0
    with torch.no_grad():
        for _ in range(iters):
            x,y=batch(EV,B,T,g); tot+=F.cross_entropy(model(x).view(-1,256),y.view(-1)).item()*y.numel(); n+=y.numel()
    model.train(); return tot/n/np.log(2)
def train_one(mode,seed,C,L,steps,T,B,lr):
    torch.manual_seed(seed); g=torch.Generator().manual_seed(seed+1); H=max(1,C//HEAD)
    model=RWKV7(256,C,H,L).to(DEV); set_mode(model,mode)
    npar=sum(p.numel() for p in model.parameters())
    opt=torch.optim.AdamW(model.parameters(),lr=lr,betas=(0.9,0.95),weight_decay=0.01)
    for s in range(steps):
        x,y=batch(TR,B,T,g); loss=F.cross_entropy(model(x).view(-1,256),y.view(-1))
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
    return eval_ce(model,T), npar

T,B,lr,STEPS,SEED=96,32,2e-3,1200,0
SIZES=[(64,2),(128,2),(192,3)]   # (C, L); H=C//64
print(f"[scale] ladder={SIZES} head_size={HEAD} steps={STEPS}",flush=True)
import csv; rows=[]
for (C,L) in SIZES:
    res={}
    for cond in ["fp32","tern"]:
        t0=time.time(); ce,npar=train_one(cond,SEED,C,L,STEPS,T,B,lr)
        res[cond]=ce
        print(f"  C={C} L={L} ({npar/1e6:.2f}M) {cond:5s} CE={ce:.4f} bits/byte  ({time.time()-t0:.0f}s)",flush=True)
    gap=res["tern"]-res["fp32"]; rows.append({"C":C,"L":L,"params_M":round(npar/1e6,3),"fp32":round(res["fp32"],4),"tern":round(res["tern"],4),"gap":round(gap,4)})
    print(f"  => C={C} L={L}: gap(tern-fp32)={gap:+.4f} bits/byte",flush=True)
print("\n[scale] SUMMARY — ternary-QAT penalty vs model size:",flush=True)
print(f"  {'params':>8s} {'fp32':>7s} {'tern':>7s} {'gap':>7s}",flush=True)
for r in rows: print(f"  {r['params_M']:>7.2f}M {r['fp32']:>7.3f} {r['tern']:>7.3f} {r['gap']:>+7.4f}",flush=True)
gaps=[r["gap"] for r in rows]
mono = all(gaps[i]>=gaps[i+1]-0.01 for i in range(len(gaps)-1))
print(f"  trend: gaps={['%+.3f'%x for x in gaps]}  monotonic-shrink={mono}",flush=True)
with open(os.path.expanduser("~/hdc_scratch/rwkv_test/qat_scale_ce.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["C","L","params_M","fp32","tern","gap"]); w.writeheader(); w.writerows(rows)
print("[scale] wrote qat_scale_ce.csv\n[scale] DONE",flush=True)
