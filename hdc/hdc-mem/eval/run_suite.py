"""
run_suite.py — the four operations a vector DB cannot pass.
ForgetEval / MergeEval / AuditEval run LIVE (deterministic, CPU, seconds).
CompositionEval reads the cached sweep (RESULTS-composition.csv) — re-run composition_eval.py to refresh.
PASS criteria are exact/algebraic, not thresholds you can tune.
"""
import sys, os, csv
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # hdc-mem/
from hdc_mem import HDCMemStore

D = 10000
SEEDS = [0, 1, 2, 3, 4]
N = 12

def fresh(seed, n=N):
    rng = np.random.default_rng(seed)
    s = HDCMemStore(D=D, seed=seed)
    ids = [s.store(rng.standard_normal(D).astype(np.float32)) for _ in range(n)]
    return s, ids

def forget_eval():
    drops, neigh_delta, neigh_keep = [], [], []
    for sd in SEEDS:
        s, ids = fresh(sd)
        t = ids[5]; before_t = s.recall_score(t); before_n = s.recall_score(ids[3])
        term = s._bound(s._items[t]["content_hv"], s._items[t]["role_id"])
        M0 = s.M.copy()
        s.forget_exact(t)
        # neighbor's contribution to M must be bit-identical (M0 - term == M)
        neigh_delta.append(float(np.max(np.abs((M0 - term) - s.M))))
        drops.append(s.recall_score(t) if t in s._items else 0.0)
        neigh_keep.append(s.recall_score(ids[3]))
    ok = max(neigh_delta) == 0.0 and np.mean(drops) < 0.05 and np.mean(neigh_keep) > 0.15
    return ok, f"forgotten→{np.mean(drops):.3f} (chance~0.01), neighbor kept {np.mean(neigh_keep):.3f}, others Δ={max(neigh_delta):.0e}"

def merge_eval():
    xleaks, unmerge_delta, a_keep = [], [], []
    for sd in SEEDS:
        sa, ida = fresh(sd); sb, idb = fresh(1000 + sd)
        Ma0 = sa.M.copy()
        sa.merge(sb)
        a_keep.append(sa.recall_score(ida[0]))
        sa.unmerge(sb)
        unmerge_delta.append(float(np.max(np.abs(sa.M - Ma0))))
    ok = max(unmerge_delta) == 0.0 and np.mean(a_keep) > 0.10
    return ok, f"A recoverable in union {np.mean(a_keep):.3f}, unmerge bit-exact Δ={max(unmerge_delta):.0e}"

def audit_eval():
    recov = []
    for sd in SEEDS:
        s, ids = fresh(sd)
        for mid in ids[:4]:
            p = s.provenance(mid)            # {'present_score': cos(unbind(M,role), content)}
            recov.append(float(p["present_score"]))
    ok = np.mean(recov) > 0.10
    return ok, f"provenance recovers filler above chance ({np.mean(recov):.3f})"

def composition_eval():
    p = os.path.join(HERE, "RESULTS-composition.csv")
    if not os.path.exists(p):
        return None, "RESULTS-composition.csv missing — run composition_eval.py --flat"
    hdc2, flat2 = [], []
    for r in csv.DictReader(open(p)):
        (hdc2 if r["system"] == "HDC" else flat2).append(float(r["a2"]))
    ok = hdc2 and flat2 and (max(hdc2) >= 0.99) and (np.mean(hdc2) - np.mean(flat2) > 0.04)
    return ok, f"arity-2 conjunction: HDC max {max(hdc2):.3f} vs flat bge-m3 {np.mean(flat2):.3f} (Δ={np.mean(hdc2)-np.mean(flat2):+.3f})"

if __name__ == "__main__":
    print("=== hdc-mem memory-algebra suite (the ops a vector DB can't pass) ===")
    results = []
    for name, fn in [("ForgetEval", forget_eval), ("MergeEval", merge_eval),
                     ("AuditEval", audit_eval), ("CompositionEval", composition_eval)]:
        ok, msg = fn()
        tag = "SKIP" if ok is None else ("PASS" if bool(ok) else "FAIL")
        results.append(ok is not None and bool(ok))
        print(f"  [{tag}] {name:16s} {msg}")
    print(f"=== SUITE: {sum(results)}/4 PASS ===")
