"""
CompositionEval — N-scaling: does HDC's advantage GROW with complexity (distractor density)?
Fixed arity-2 conjunction; sweep N (memories sharing each single attribute scale with N).
HYPOTHESIS: HDC bind holds P@1 flat; bge-m3 flat embedding decays as N grows -> gap WIDENS.
Honest: same real-word tuples to both; bge-m3 loaded ONCE; 3 seeds ±SE.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import composition_eval as C
np.seterr(all='ignore')

NS = [500, 1000, 2000, 4000, 8000]
SEEDS = [0, 1, 2]
D = 30000
ARITY = 2

from sentence_transformers import SentenceTransformer
mdl = SentenceTransformer('BAAI/bge-m3')
def embed_fn(t): return mdl.encode(t, normalize_embeddings=True, batch_size=128).astype(np.float32)

print(f'# N-scaling  arity={ARITY}  D={D}  P@1 mean±SE/{len(SEEDS)} seeds')
print(f'# {"N":>6s}  {"fourier_hrr":>14s}  {"bipolar":>14s}  {"flat-bge-m3":>14s}  {"gap(hrr-flat)":>13s}')
for N in NS:
    hrr, bip, flat = [], [], []
    for s in SEEDS:
        hrr.append(C.run_hdc(N, ARITY, 'fourier_hrr', D, s))
        bip.append(C.run_hdc(N, ARITY, 'bipolar', D, s))
        mems = C.make_corpus(N, 4, s)
        mtext = [' '.join(C.WORDS[r][m[r]] for r in C.ROLES if r in m) for m in mems]
        memb = embed_fn(mtext)
        flat.append(C.run_flat(N, ARITY, 0, s, (mems, memb, embed_fn)))
    def ms(v): return np.mean(v), np.std(v)/np.sqrt(len(v))
    h, b, f = ms(hrr), ms(bip), ms(flat)
    print(f'  {N:6d}  {h[0]:.3f}±{h[1]:.3f}  {b[0]:.3f}±{b[1]:.3f}  {f[0]:.3f}±{f[1]:.3f}  {h[0]-f[0]:+.3f}', flush=True)
print('# DONE_SCALE')
