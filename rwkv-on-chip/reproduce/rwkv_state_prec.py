#!/usr/bin/env python3
# 上三 — 闸3 STATE PRECISION. Weights ternary (chip-real). At inference, re-quantize the
# recurrent DPLR state S to {fp32,fp16,int8,int4} EACH timestep, measure CE vs eval length.
# Pre-reg: a state precision is SAFE iff CE-gap vs fp32-state stays <0.05 bit AND does NOT grow
# with sequence length (no compounding drift). fp16 expected free; int8 TBD; int4 likely drifts.
import sys, time, glob, os
import torch, torch.nn as nn, torch.nn.functional as F, numpy as np
torch.set_num_threads(4); DEV="cpu"; HEAD=64
STATE_PREC = "fp32"  # global, set before eval

def qstate(S):
    if STATE_PREC == "fp32": return S
    if STATE_PREC == "fp16": return S.half().float()
    qmax = 127 if STATE_PREC == "int8" else 7
    s = S.abs().amax(dim=(-1, -2), keepdim=True).clamp(min=1e-8) / qmax   # dynamic per-(B,H)
    return (S / s).round().clamp(-qmax, qmax) * s

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
        self.wdec,self.agen=nn.Linear(C,C),nn.Linear(C,C); self.gn=nn.GroupNorm(H,C); self.r_k=nn.Parameter(torch.zeros(H,self.N))
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
            S=qstate(S)                                              # <-- state precision applied each step
            yt=(S*rt.unsqueeze(2)).sum(-1); yt=yt+(rt*k2*self.r_k).sum(-1,keepdim=True)*vt
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
    d=np.frombuffer(bytes(buf[:maxbytes]),dtype=np.uint8).astype(np.int64); n=len(d)
    return d[:int(n*0.9)], d[int(n*0.9):]
TR,EV=load_corpus(); print(f"[state] corpus train={len(TR)}B eval={len(EV)}B",flush=True)
def batch(arr,B,T,g):
    ix=torch.randint(0,len(arr)-T-1,(B,),generator=g)
    return (torch.stack([torch.from_numpy(arr[i:i+T].copy()) for i in ix]).to(DEV),
            torch.stack([torch.from_numpy(arr[i+1:i+1+T].copy()) for i in ix]).to(DEV))
def eval_ce(model,T,iters=12,B=16):
    model.eval(); g=torch.Generator().manual_seed(999); tot=0.;n=0
    with torch.no_grad():
        for _ in range(iters):
            x,y=batch(EV,B,T,g); tot+=F.cross_entropy(model(x).view(-1,256),y.view(-1)).item()*y.numel(); n+=y.numel()
    return tot/n/np.log(2)

# train ONE ternary-weight model (chip deployment config)
C,L,Tt,B,lr,STEPS=128,2,96,32,2e-3,1200
torch.manual_seed(0); g=torch.Generator().manual_seed(1); H=C//HEAD
model=RWKV7(256,C,H,L).to(DEV); set_mode(model,"tern")
opt=torch.optim.AdamW(model.parameters(),lr=lr,betas=(0.9,0.95),weight_decay=0.01)
print(f"[state] training ternary-weight model C={C} L={L} ({sum(p.numel() for p in model.parameters())/1e6:.2f}M) ...",flush=True)
t0=time.time()
for s in range(STEPS):
    x,y=batch(TR,B,Tt,g); loss=F.cross_entropy(model(x).view(-1,256),y.view(-1))
    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
print(f"[state] trained ({time.time()-t0:.0f}s). Now sweeping STATE precision x eval-length:",flush=True)

# eval sweep: state precision x sequence length
import csv
TES=[64,128,256,512]; PRECS=["fp32","fp16","int8","int4"]; rows=[]
ref={}
for Te in TES:
    globals()["STATE_PREC"]="fp32"; ref[Te]=eval_ce(model,Te)
for prec in PRECS:
    line=[]
    for Te in TES:
        globals()["STATE_PREC"]=prec; ce=eval_ce(model,Te); gap=ce-ref[Te]
        rows.append({"prec":prec,"T":Te,"ce":round(ce,4),"gap":round(gap,4)}); line.append(f"T={Te}:{gap:+.4f}")
    print(f"  state={prec:5s}  "+"  ".join(line),flush=True)
print("\n[state] SUMMARY — CE gap vs fp32-state (bits/byte). SAFE = small AND flat across length:",flush=True)
print(f"  {'state':6s}"+"".join(f"  T={t:<4d}" for t in TES),flush=True)
for prec in PRECS:
    gs=[r["gap"] for r in rows if r["prec"]==prec]
    grow=gs[-1]-gs[0]
    print(f"  {prec:6s}"+"".join(f"  {g:+6.4f}" for g in gs)+f"   drift(T512-T64)={grow:+.4f}",flush=True)
with open(os.path.expanduser("~/hdc_scratch/rwkv_test/state_prec.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["prec","T","ce","gap"]); w.writeheader(); w.writerows(rows)
print("[state] wrote state_prec.csv\n[state] DONE",flush=True)
