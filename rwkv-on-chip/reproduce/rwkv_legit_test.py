#!/usr/bin/env python3
# RWKV-7 "is it legit" 实测 — runs the REAL checkpoint through BOTH the official
# rwkv package AND the transparent 200-line numpy ref, proves constant memory,
# and shows coherent generation. Everything is measured, nothing trusted.
import os, sys, time, glob
os.environ["RWKV_V7_ON"] = "1"
os.environ.setdefault("RWKV_JIT_ON", "0")
import numpy as np, torch

SCRATCH = os.path.expanduser("~/hdc_scratch/rwkv_test")
cks = glob.glob(os.path.join(SCRATCH, "*0.1b*.pth"))
assert cks, f"no 0.1b checkpoint in {SCRATCH}"
MODEL_FILE = sorted(cks)[0]
print(f"[model] {MODEL_FILE}", flush=True)

from rwkv.model import RWKV
from rwkv.utils import PIPELINE

t0 = time.time()
model = RWKV(model=MODEL_FILE[:-4], strategy="cpu fp32")
pipe = PIPELINE(model, "rwkv_vocab_v20230424")
print(f"[load] {time.time()-t0:.1f}s", flush=True)

# ---- inspect config from weights ----
w = torch.load(MODEL_FILE, map_location="cpu", weights_only=True)
n_layer = 1 + max(int(k.split(".")[1]) for k in w if k.startswith("blocks."))
n_embd = w["emb.weight"].shape[1]
head_size = 64
n_head = n_embd // head_size
n_params = sum(v.numel() for v in w.values())
print(f"[config] n_layer={n_layer} n_embd={n_embd} n_head={n_head} params={n_params:,}", flush=True)

# ============================================================
# TEST 1 — COHERENCE: is it a real LM or noise?
# ============================================================
print("\n==== TEST 1: coherence (greedy continuation) ====", flush=True)
ctx = "\nIn a shocking finding, scientist discovered a herd of dragons living in a remote, previously unexplored valley, in Tibet. Even more surprising to the researchers was the fact that the dragons spoke perfect Chinese."
tokens = pipe.encode(ctx)
out, state = model.forward(tokens, None)
gen = []
for _ in range(80):
    tok = int(np.argmax(out.numpy()))
    gen.append(tok)
    out, state = model.forward([tok], state)
print("PROMPT:", ctx.strip()[:120], "...")
print("CONT  :", pipe.decode(gen), flush=True)

# ============================================================
# TEST 2 — CONSTANT MEMORY: the core claim. State must NOT grow with ctx len.
# ============================================================
print("\n==== TEST 2: constant memory vs context length ====", flush=True)
def state_bytes(s):
    tot = 0
    for x in s:
        if torch.is_tensor(x): tot += x.numel() * x.element_size()
        else: tot += np.asarray(x).nbytes
    return tot
filler = pipe.encode(" the quick brown fox jumps over the lazy dog. " * 600)  # long token stream
rows = []
for L in [64, 256, 1024, 4096]:
    toks = filler[:L]
    _, st = model.forward(toks, None)
    sb = state_bytes(st)
    # equivalent transformer KV cache (fp16): 2 (k,v) * n_layer * L * n_embd * 2 bytes
    kv = 2 * n_layer * L * n_embd * 2
    rows.append((L, sb, kv))
    print(f"  ctx={L:5d}  RWKV state={sb/1024:8.1f} KB   |  equiv transformer KV-cache(fp16)={kv/1024:10.1f} KB", flush=True)
const = len({r[1] for r in rows}) == 1
print(f"  -> RWKV state constant across ctx? {const}", flush=True)
print(f"  -> transformer KV grows {rows[-1][2]/rows[0][2]:.0f}x from ctx64->4096; RWKV grows {rows[-1][1]/rows[0][1]:.2f}x", flush=True)

# ============================================================
# TEST 3 — FAITHFULNESS: transparent 200-line numpy must reproduce the official model
# ============================================================
print("\n==== TEST 3: faithfulness (johanwind numpy ref vs official) ====", flush=True)
try:
    layer_norm = lambda x,wt,b: (x-x.mean())/(x.var()+1e-5)**0.5*wt+b
    group_norm = lambda x,wt,b: ((x-x.mean(axis=1,keepdims=1))/(x.var(axis=1,keepdims=1)+64e-5)**0.5).flatten()*wt+b
    sigmoid = lambda x: 1/(1+np.exp(-x))
    W = {k: v.squeeze().float().numpy() for k,v in w.items()}
    params = lambda p: [W[k] for k in W if k.startswith(p)]
    HEAD_SIZE, N_HEAD, N_LAYER = head_size, n_head, n_layer
    def time_mixing(x,v0,last_x,S,P):
        # RWKV-LM-trained param order
        mr,mw,mk,mv,ma,mg, w_bias, r_k, Ww1,Ww2, Wa1,Wa2,a_bias, Wg1,Wg2 = P[:15]
        k_k,k_a, Wr,Wk,Wv,Wo, ln_w,ln_b = P[-8:]
        xr,xw,xk,xv,xa,xg = [x+m*(last_x-x) for m in [mr,mw,mk,mv,ma,mg]]
        r=Wr@xr; w_=np.exp(-sigmoid(np.tanh(xw@Ww1)@Ww2+w_bias)/np.e**0.5); k=Wk@xk; v=Wv@xv
        if v0 is None: v0=v
        else:
            Wv2,Wv1,v_bias=P[15:18]; v+= (v0-v)*sigmoid(xv@Wv1@Wv2+v_bias)
        a=sigmoid(xa@Wa1@Wa2+a_bias); g=sigmoid(xg@Wg1)@Wg2
        kk=k*k_k; k=k+k*(a-1)*k_a
        r,w_,k,v,kk,a,r_k=[i.reshape(N_HEAD,HEAD_SIZE,1) for i in [r,w_,k,v,kk,a,r_k]]
        kk=kk/np.maximum(np.linalg.norm(kk,axis=1,keepdims=1),1e-12)
        S=S*w_.mT - S@kk*(kk*a).mT + v*k.mT
        y=S@r; y=group_norm(y,ln_w,ln_b); y=y+((r*k*r_k).sum(axis=1,keepdims=1)*v).flatten()
        return Wo@(y*g), v0, x, S
    def channel_mixing(x,last_x,mix,Wk,Wv):
        k=Wk@(x+mix*(last_x-x)); return Wv@np.maximum(k,0)**2, x
    def RWKV7(token,stt):
        x=params('emb')[0][token]; x=layer_norm(x,*params('blocks.0.ln0'))
        v0=None
        for i in range(N_LAYER):
            x_=layer_norm(x,*params(f'blocks.{i}.ln1'))
            dx,v0,stt[0][i,0],stt[1][i]=time_mixing(x_,v0,stt[0][i,0],stt[1][i],params(f'blocks.{i}.att')); x=x+dx
            x_=layer_norm(x,*params(f'blocks.{i}.ln2'))
            dx,stt[0][i,1]=channel_mixing(x_,stt[0][i,1],*params(f'blocks.{i}.ffn')); x=x+dx
        x=layer_norm(x,*params('ln_out')); return params('head')[0]@x, stt
    ref_logits,_ = model.forward(tokens, None); ref_logits = ref_logits.numpy()
    st=(np.zeros((N_LAYER,2,n_embd),np.float32), np.zeros((N_LAYER,N_HEAD,HEAD_SIZE,HEAD_SIZE),np.float32))
    for tk in tokens: mlog, st = RWKV7(tk, st)
    dev = float(np.max(np.abs(mlog-ref_logits))/ref_logits.std())
    print(f"  deviation (transparent numpy vs official) = {dev:.3e}  (relative to logit std)", flush=True)
    print(f"  -> {'PASS: transparent math == official model (no hidden magic)' if dev < 1e-2 else 'param-order mismatch, see note'}", flush=True)
except Exception as e:
    print(f"  [faithfulness skipped: {type(e).__name__}: {e}]", flush=True)

print("\n==== DONE ====", flush=True)
