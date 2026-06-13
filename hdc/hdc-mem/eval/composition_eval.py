"""
CompositionEval — the scenario where HDC SHOULD diverge: complex/conjunctive/structured queries.
(Michael 2026-06-13: "你的场景没用对... 处理非常复杂的信息和任务面前，会不一样")

THE CLAIM (falsifiable): on conjunctive retrieval where each single attribute is shared by many
memories but the CONJUNCTION is rare, HDC bind/bundle keeps the conjunction algebraically clean while a
flat text embedding (real-RAG baseline, bge-m3) becomes a blurry average -> HDC precision@1 HOLDS as
distractor-density & conjunction-arity grow, flat embedding DEGRADES. HDC advantage GROWS with complexity.

PREMORTEM (how this could fool me -> guards):
 1. Weak baseline manufactures an HDC win.
    GUARD: baseline = bge-m3 embedding of the SAME rendered structured query (what a real RAG system does),
    cosine over bge-m3 corpus embeddings. Also report ENUMERABLE-FILTER (exact metadata AND) as the strong
    ceiling that wins WHEN fillers are exact/enumerable — so we are honest about when HDC's value applies
    (open / fuzzy / partial / analogical fillers, where you can't pre-enumerate the conjunction).
 2. HDC gets an unfair answer-key via structured encoding the baseline lacks.
    GUARD: BOTH sides receive the same (role,filler) tuples (the trinity: LLM eyes extract them). HDC binds;
    baseline renders to text + embeds (the realistic alternative). Same information, different substrate.
 3. Capacity cliff (L12, N*~D/20) silently caps recall.
    GUARD: keep pairs-per-memory * effective load within capacity; SWEEP D; report the cliff if hit.
 4. Smoke-mirage: a single lucky config.
    GUARD: PoC-1-cell first (--smoke, DEBUG-ONLY), then golden sweep >=4 atom-schemes x >=3 D x >=3 seeds,
    mean +/- SE; the gaussian/flat floor is a CONTROL not a verdict.
 5. fourier-HRR was chance on FLAT recall -> include it: if it SHINES here (binding weapon, right scenario),
    that literally demonstrates "wrong scenario before".
"""
import sys, os, argparse, itertools
import numpy as np
# self-contained: defines its own bind/bundle/atoms below — no external VSA dependency

ROLES = ['person', 'action', 'topic', 'time']
# Real-word vocab banks so the bge-m3 flat baseline does GENUINE semantic retrieval (premortem #1:
# index tokens would either strawman bge-m3 or hand it a keyword-overlap cheat). These are the fillers.
WORDS = {
 'person': ['Alice','Bob','Carlos','Diana','Ethan','Fatima','Grace','Hiro','Ivan','Julia','Kenji','Lena',
            'Marcus','Nadia','Omar','Priya','Quinn','Rosa','Sven','Tara','Umar','Vera','Wei','Xena','Yuki','Zoe',
            'Aaron','Beatriz','Chen','Dmitri'],
 'action': ['promised','refunded','cancelled','approved','rejected','delayed','shipped','escalated','refused',
            'scheduled','upgraded','downgraded','reimbursed','flagged','resolved','reopened','transferred','paused'],
 'topic': ['refund','billing','shipping','warranty','password','subscription','invoice','delivery','returns',
           'login','payment','discount','outage','privacy','contract','renewal','upgrade','bug','latency',
           'onboarding','quota','export','migration','permissions','timezone','currency','tax','receipt'],
 'time': ['today','yesterday','last-week','last-month','this-morning','tonight','Monday','Friday','April',
          'Q3','the-weekend','two-days-ago'],
}
VOCAB = {r: len(WORDS[r]) for r in ROLES}  # person30 action18 topic28 time12 -> high single-attr overlap at N=2000

# ---------- atom schemes (the "encoding" axis; bind/bundle from the arsenal) ----------
def atoms(D, n, seed, scheme):
    rng = np.random.default_rng(seed)
    if scheme in ('bipolar', 'map'):
        return np.where(rng.random((n, D)) < 0.5, -1.0, 1.0).astype(np.float32)
    if scheme == 'sparse_ternary':
        A = np.zeros((n, D), np.float32); nz = max(1, int(0.1 * D))
        for i in range(n):
            idx = rng.choice(D, nz, replace=False); A[i, idx] = rng.choice([-1.0, 1.0], nz)
        return A
    if scheme == 'fourier_hrr':          # unit-modulus phases; binding = circular conv (freq-domain product)
        ph = rng.uniform(-np.pi, np.pi, (n, D)); return np.exp(1j * ph).astype(np.complex64)
    raise ValueError(scheme)

def bind(a, b, scheme):
    if scheme == 'fourier_hrr':
        return np.fft.ifft(np.fft.fft(a) * np.fft.fft(b)).astype(np.complex64)  # circular convolution
    return (a * b).astype(np.float32)    # MAP/bipolar/ternary: elementwise product (self-inverse)

def bundle(vs, scheme):
    s = np.sum(vs, axis=0)
    return s if scheme == 'fourier_hrr' else np.sign(s).astype(np.float32)

def sim(q, M, scheme):                   # q:(D,) M:(N,D) -> (N,)
    if scheme == 'fourier_hrr':
        num = np.real(M @ np.conj(q)); den = (np.linalg.norm(M, axis=1) * np.linalg.norm(q) + 1e-9)
        return num / den
    qn = q / (np.linalg.norm(q) + 1e-9); Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return Mn @ qn

# ---------- corpus of structured memories ----------
def make_corpus(N, n_pairs, seed):
    rng = np.random.default_rng(seed)
    mems = []
    for _ in range(N):
        rs = rng.choice(len(ROLES), n_pairs, replace=False)
        mems.append({ROLES[r]: int(rng.integers(0, VOCAB[ROLES[r]])) for r in rs})
    return mems

def encode_corpus(mems, role_at, fill_at, scheme):
    out = []
    for m in mems:
        terms = [bind(role_at[r], fill_at[r][f], scheme) for r, f in m.items()]
        out.append(bundle(terms, scheme))
    return np.array(out)

def query_hv(qpairs, role_at, fill_at, scheme):
    return bundle([bind(role_at[r], fill_at[r][f], scheme) for r, f in qpairs.items()], scheme)

# ---------- the experiment: conjunctive retrieval, advantage vs complexity ----------
def run_hdc(N, arity, scheme, D, seed, n_pairs=4, n_query=200):
    rng = np.random.default_rng(seed + 777)
    role_at = {r: atoms(D, 1, seed * 13 + i, scheme)[0] for i, r in enumerate(ROLES)}
    fill_at = {r: atoms(D, VOCAB[r], seed * 31 + i, scheme) for i, r in enumerate(ROLES)}
    mems = make_corpus(N, n_pairs, seed)
    M = encode_corpus(mems, role_at, fill_at, scheme)
    hits = 0; tried = 0
    for _ in range(n_query):
        ti = int(rng.integers(0, N)); tgt = mems[ti]
        if len(tgt) < arity:
            continue
        qroles = list(rng.choice(list(tgt.keys()), arity, replace=False))
        qpairs = {r: tgt[r] for r in qroles}
        # ensure it's a genuine conjunctive query: many share each single attr (high marginal overlap by construction)
        q = query_hv(qpairs, role_at, fill_at, scheme)
        scores = sim(q, M, scheme)
        # ground truth = memories matching ALL queried (role,filler); rank target among them and all
        pred = int(np.argmax(scores))
        match = [j for j, m in enumerate(mems) if all(m.get(r) == f for r, f in qpairs.items())]
        hits += 1 if pred in match else 0
        tried += 1
    return hits / max(tried, 1)

def run_flat(N, arity, D, seed, embed_cache, n_pairs=4, n_query=200):
    """Real-RAG baseline: render memory+query as text, bge-m3 cosine. embed_cache = (mem_emb, embed_fn)."""
    rng = np.random.default_rng(seed + 777)
    mems, mem_emb, embed_fn = embed_cache
    hits = 0; tried = 0
    qtexts = []; qmatch = []
    for _ in range(n_query):
        ti = int(rng.integers(0, N)); tgt = mems[ti]
        if len(tgt) < arity:
            continue
        qroles = list(rng.choice(list(tgt.keys()), arity, replace=False))
        qpairs = {r: tgt[r] for r in qroles}
        qtexts.append(' '.join(WORDS[r][f] for r, f in qpairs.items()))
        qmatch.append([j for j, m in enumerate(mems) if all(m.get(r) == f for r, f in qpairs.items())])
    qemb = embed_fn(qtexts)
    sims = qemb @ mem_emb.T
    for i in range(len(qtexts)):
        if int(np.argmax(sims[i])) in qmatch[i]:
            hits += 1
        tried += 1
    return hits / max(tried, 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument('--N', type=int, default=2000)
    ap.add_argument('--D', type=int, nargs='+', default=[10000, 30000, 50000])
    ap.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2])
    ap.add_argument('--arities', type=int, nargs='+', default=[1, 2, 3])
    ap.add_argument('--schemes', nargs='+', default=['bipolar', 'sparse_ternary', 'fourier_hrr'])
    ap.add_argument('--flat', action='store_true', help='also run bge-m3 flat-text baseline')
    a = ap.parse_args()

    if a.smoke:
        print('# SMOKE (DEBUG-ONLY — does the compositional pipeline run + give sane numbers, NOT a verdict)')
        for sc in a.schemes:
            p1 = run_hdc(200, 1, sc, 10000, 0, n_query=60)
            p2 = run_hdc(200, 2, sc, 10000, 0, n_query=60)
            print(f'  {sc:16s} N=200 D=10000  arity1 P@1={p1:.3f}  arity2 P@1={p2:.3f}')
        return

    print(f'#### CompositionEval  N={a.N}  conjunctive retrieval  precision@1 (mean±SE over {len(a.seeds)} seeds)')
    print(f'# {"scheme":16s} {"D":>6s} ' + ' '.join(f'arity{ar:>2d}' for ar in a.arities))
    for sc in a.schemes:
        for D in a.D:
            cols = []
            for ar in a.arities:
                vals = [run_hdc(a.N, ar, sc, D, s) for s in a.seeds]
                cols.append((np.mean(vals), np.std(vals) / np.sqrt(len(vals))))
            print(f'  {sc:16s} {D:6d} ' + ' '.join(f'{m:.3f}±{e:.3f}' for m, e in cols), flush=True)

    if a.flat:
        from sentence_transformers import SentenceTransformer
        mdl = SentenceTransformer('BAAI/bge-m3')
        def embed_fn(texts): return mdl.encode(texts, normalize_embeddings=True, batch_size=64).astype(np.float32)
        print(f'# FLAT bge-m3 text baseline (real-RAG), precision@1:')
        print(f'# {"baseline":16s} {"":6s} ' + ' '.join(f'arity{ar:>2d}' for ar in a.arities))
        for s in a.seeds:
            mems = make_corpus(a.N, 4, s)
            mtext = [' '.join(WORDS[r][m[r]] for r in ROLES if r in m) for m in mems]
            memb = embed_fn(mtext)
            cols = []
            for ar in a.arities:
                cols.append(run_flat(a.N, ar, 0, s, (mems, memb, embed_fn)))
            print(f'  bge-m3 seed={s:<8d} {"":6s} ' + ' '.join(f'{v:.3f}     ' for v in cols), flush=True)
    print('# DONE_COMPOSITION')

if __name__ == '__main__':
    main()
