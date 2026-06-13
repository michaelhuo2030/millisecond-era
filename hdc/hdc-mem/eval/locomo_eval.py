"""
locomo_eval.py — the memory-algebra standard on PUBLIC data (LoCoMo, snap-research).

Premortem-driven SCENARIO choice (do NOT repeat the flat-recall mistake):
  * ForgetEval  : exact-delete real conversation memories, bit-exact preservation. NO vector-DB benchmark
                  tests this. This is the clean public-data proof of an OPERATION (not a leaderboard).
  * Compose-gap : measure flat bge-m3 retrieval recall stratified by #gold-evidence (1 vs >=2). Honest
                  baseline measurement showing real-data multi-hop degradation = why `compose` matters.

Capacity (L12): one bundle holds N*~D/20 items; LoCoMo conv ~150-300 turns -> D=50000 (N*~2500) keeps
preserved turns comfortably recallable. bge-m3 embeds turn text once (cached per conv).
"""
import sys, os, json, re, argparse, ast
# thermal protection: cap threads so heavy embedding never pegs all cores (protect both macs)
_thr = os.environ.get('LOCOMO_THREADS', '4')
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_v, _thr)
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from hdc_mem import HDCMemStore, _role_hv

DATA = os.environ.get('LOCOMO_DATA', '/tmp/locomo.json')
MODEL = os.environ.get('LOCOMO_MODEL', 'BAAI/bge-m3')   # override w/ a light model (e.g. BAAI/bge-small-en-v1.5) for thermal safety
EMB_CACHE = os.environ.get('LOCOMO_CACHE', '/tmp/locomo_emb_{i}.npy')
D = 50000

def flatten(conv):
    c = conv['conversation']; turns = []
    for s in range(1, 40):
        key = f'session_{s}'
        if key not in c: continue
        for t in c[key]:
            turns.append({'speaker': t['speaker'], 'dia_id': t['dia_id'], 'session': s, 'text': t.get('text', '')})
    return turns

def embed_turns(turns, i, model):
    p = EMB_CACHE.format(i=i)
    if os.path.exists(p): return np.load(p)
    E = model.encode([t['text'] for t in turns], normalize_embeddings=True, batch_size=128).astype(np.float32)
    np.save(p, E); return E

def forget_eval(d, model, convs):
    """Forget all turns by one speaker in one session; assert forgotten->chance, others bit-exact (Δ=0)."""
    drops_b, drops_a, keep_a, deltas, sizes = [], [], [], [], []
    for i in convs:
        turns = flatten(d[i]); E = embed_turns(turns, i, model)
        s = HDCMemStore(D=D, seed=i)
        ids = [s.store(E[j]) for j in range(len(turns))]
        # forget target = a speaker's turns in the middle session (a realistic "delete my session-3 messages")
        sess = sorted({t['session'] for t in turns})[len(set(t['session'] for t in turns)) // 2]
        spk = turns[0]['speaker']
        fset = [j for j, t in enumerate(turns) if t['session'] == sess and t['speaker'] == spk]
        kset = [j for j in range(len(turns)) if j not in fset][:40]
        if not fset: continue
        import hdcmem_vsa as _H
        fhv = [s._items[ids[j]]['content_hv'] for j in fset]   # keep refs before forgetting
        khv = [s._items[ids[j]]['content_hv'] for j in kset]
        frole = [s._items[ids[j]]['role_id'] for j in fset]
        krole = [s._items[ids[j]]['role_id'] for j in kset]
        drops_b.append(np.mean([_H.similarity(_H.unbind(s.M, _role_hv(frole[m], s.D)), fhv[m], 'cosine') for m in range(len(fset))]))
        M0 = s.M.copy()
        term = np.zeros(D, np.float32)
        for j in fset: term = term + s._bound(s._items[ids[j]]['content_hv'], s._items[ids[j]]['role_id'])
        for j in fset: s.forget_exact(ids[j])
        deltas.append(float(np.max(np.abs((M0 - term) - s.M))))     # others' contribution bit-identical?
        # HONEST: residual presence of forgotten content in the NEW vector M (not index-absence default)
        drops_a.append(np.mean([_H.similarity(_H.unbind(s.M, _role_hv(frole[m], s.D)), fhv[m], 'cosine') for m in range(len(fset))]))
        keep_a.append(np.mean([_H.similarity(_H.unbind(s.M, _role_hv(krole[m], s.D)), khv[m], 'cosine') for m in range(len(kset))]))
        sizes.append((len(turns), len(fset)))
    chance = 1.0 / np.sqrt(D)   # true chance = random-vector cosine ~ 1/sqrt(D)
    print(f'#### ForgetEval on LoCoMo (real conversations, D={D}, n_conv={len(drops_b)})')
    print(f'  forgotten-set recall  before={np.mean(drops_b):.4f}  after={np.mean(drops_a):.4f}  (chance~{chance:.4f})')
    print(f'  preserved-set recall  after ={np.mean(keep_a):.4f}  (stays recallable)')
    print(f'  OTHERS bit-identical  max|Δ(M - forgotten_term)| = {max(deltas):.2e}  ({"EXACT" if max(deltas)==0 else "NONZERO!"})')
    print(f'  avg turns/conv={np.mean([n for n,_ in sizes]):.0f}  avg forgotten/conv={np.mean([f for _,f in sizes]):.0f}')
    print(f'  VERDICT: {"PASS — exact-delete on real conversation memory, others untouched (Δ=0)" if max(deltas)==0 and np.mean(drops_a)<chance*1.5 else "CHECK"}')
    return dict(before=float(np.mean(drops_b)), after=float(np.mean(drops_a)), chance=float(chance),
                preserved=float(np.mean(keep_a)), max_delta=float(max(deltas)), n_conv=len(drops_b))

def gap_eval(d, model, convs, k=5):
    """Flat bge-m3 retrieval recall stratified by #gold-evidence (compose-gap motivation)."""
    rec1, recM = [], []
    for i in convs:
        turns = flatten(d[i]); E = embed_turns(turns, i, model)
        did = {t['dia_id']: j for j, t in enumerate(turns)}
        qs, gold = [], []
        for qa in d[i].get('qa', []):
            ev = qa.get('evidence')
            if isinstance(ev, str):
                try: ev = ast.literal_eval(ev)
                except Exception: ev = []
            ev = [e for e in (ev or []) if e in did]
            if not ev or 'question' not in qa: continue
            qs.append(qa['question']); gold.append([did[e] for e in ev])
        if not qs: continue
        Q = model.encode(qs, normalize_embeddings=True, batch_size=128).astype(np.float32)
        S = Q @ E.T
        for r in range(len(qs)):
            top = set(np.argpartition(-S[r], k)[:k])
            rec = len(set(gold[r]) & top) / len(gold[r])
            (rec1 if len(gold[r]) == 1 else recM).append(rec)
    print(f'#### Compose-gap: flat bge-m3 retrieval recall@{k} on LoCoMo')
    print(f'  single-evidence Q (n={len(rec1)}):  recall@{k} = {np.mean(rec1):.3f}')
    print(f'  multi-evidence  Q (n={len(recM)}):  recall@{k} = {np.mean(recM):.3f}   <-- degrades (the compose gap)')
    print(f'  degradation: {np.mean(rec1)-np.mean(recM):+.3f}  (flat embedding smears the conjunction)')
    return dict(single=float(np.mean(rec1)), multi=float(np.mean(recM)), k=k, n1=len(rec1), nM=len(recM))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='poc', choices=['poc', 'forget', 'gap', 'all'])
    a = ap.parse_args()
    d = json.load(open(DATA))
    import torch; torch.set_num_threads(int(_thr))
    from sentence_transformers import SentenceTransformer
    print(f'# model={MODEL} threads={_thr} data={DATA}')
    model = SentenceTransformer(MODEL)
    if a.mode == 'poc':
        forget_eval(d, model, [0]); print(); gap_eval(d, model, [0])
    else:
        convs = list(range(len(d)))
        if a.mode in ('forget', 'all'): r = forget_eval(d, model, convs); json.dump(r, open(HERE+'/RESULTS-locomo-forget.json','w'), indent=2)
        if a.mode in ('gap', 'all'): print(); r = gap_eval(d, model, convs); json.dump(r, open(HERE+'/RESULTS-locomo-gap.json','w'), indent=2)
    print('# DONE_LOCOMO')
