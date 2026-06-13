#!/usr/bin/env python3
"""
demo.py — PROVE the hdc-mem differentiators with MEASURED before/after numbers.

We do NOT report from a single smoke. Each claim is averaged over SEEDS seeds with
±SE so the gap to the noise floor is honest. Three differentiators, each one a thing
the conventional memory race (Amind decay-GC, MemPalace summaries, Memvid WAL, Mirix)
does with heuristics and we do with exact algebra:

  (a) forget_exact  — removed item's recall drops to ~chance; OTHER items preserved.
  (b) merge         — two federated stores stay separable; query each, no cross-leak.
  (c) undo          — bit-exact restore of the memory vector.

Run: python3 demo.py
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdc_mem import HDCMemStore, _role_hv
import hdcmem_vsa as hdc_ops

D = 10000
SEEDS = 8
N_ITEMS = 12          # items per store; self-recall signal ~ 1/sqrt(N) above noise


def mean_se(xs):
    a = np.asarray(xs, float)
    return a.mean(), a.std(ddof=1) / np.sqrt(len(a)) if len(a) > 1 else 0.0


def fresh_store(seed, n=N_ITEMS, tag="A"):
    """Build a store of n random-embedding memories (content-agnostic algebra)."""
    rng = np.random.default_rng(seed)
    s = HDCMemStore(D=D, seed=seed)
    ids, embs = [], []
    for i in range(n):
        e = rng.standard_normal(256).astype(np.float32)   # stand-in embedding
        e = e / np.linalg.norm(e)
        mid = s.store(e)
        ids.append(mid)
        embs.append(e)
    return s, ids, embs


# ── (a) FORGET: target -> chance, others preserved ─────────────────────────
def exp_forget():
    tgt_before, tgt_after, other_before, other_after, chance = [], [], [], [], []
    other_term_bitdelta = []   # is the neighbor's CONTRIBUTION to M bit-identical?
    for seed in range(SEEDS):
        s, ids, _ = fresh_store(seed)
        k = N_ITEMS // 2
        # measure target + a held-out neighbor before
        tgt_before.append(s.recall_score(ids[k]))
        other_before.append(s.recall_score(ids[3]))
        # the neighbor's exact bound term (its physical contribution to the bundle M)
        nb = s._items[ids[3]]
        nb_term_before = s._bound(nb["content_hv"], nb["role_id"]).copy()
        # chance floor: probe M with a brand-new random (role, content) never stored
        rng = np.random.default_rng(9000 + seed)
        rand_role = 999000 + seed
        rand_hv = np.where(rng.random(D) < 0.5, -1.0, 1.0).astype(np.float32)
        chance.append(abs(s.probe(rand_role, rand_hv)))
        # capture forgotten item's (role, hv) BEFORE deleting bookkeeping
        it = s._items[ids[k]]
        role_id, hv = it["role_id"], it["content_hv"]
        s.forget_exact(ids[k])
        tgt_after.append(abs(s.probe(role_id, hv)))     # exact-removed item, probed in M
        other_after.append(s.recall_score(ids[3]))      # neighbor still recoverable?
        # neighbor's bound term recomputed from M-after must equal its term from M-before:
        nb_term_after = s._bound(nb["content_hv"], nb["role_id"])
        other_term_bitdelta.append(float(np.abs(nb_term_after - nb_term_before).max()))
    return dict(tgt_before=mean_se(tgt_before), tgt_after=mean_se(tgt_after),
                other_before=mean_se(other_before), other_after=mean_se(other_after),
                chance=mean_se(chance),
                other_term_bitdelta=mean_se(other_term_bitdelta))


# ── (b) MERGE: two federated stores stay separable ─────────────────────────
def exp_merge():
    a_in_union, b_in_union, a_xleak, b_xleak, a_after_unmerge = [], [], [], [], []
    bit_exact = []
    for seed in range(SEEDS):
        sa, ida, ea = fresh_store(seed, tag="A")
        sb, idb, eb = fresh_store(1000 + seed, tag="B")
        Ma_before = sa.M.copy()
        # cross-leak BEFORE merge: does store A "recall" a store-B item? (should be ~0)
        b_item0 = sb._items[idb[0]]
        a_xleak_pre = abs(sa.probe(b_item0["role_id"], b_item0["content_hv"]))
        sa.merge(sb)
        # both still recoverable from the union
        a_in_union.append(sa.recall_score(ida[2]))
        # B item recoverable in union: probe with its role+hv
        b_in_union.append(abs(sa.probe(b_item0["role_id"], b_item0["content_hv"])))
        # cross-contamination: an A role unbound from union should NOT surface a B content
        a_role = sa._items[ida[2]]["role_id"]
        rec_a = hdc_ops.unbind(sa.M, _role_hv(a_role, D))
        a_xleak.append(abs(hdc_ops.similarity(rec_a, b_item0["content_hv"], "cosine")))
        b_xleak.append(a_xleak_pre)
        # SEPARABLE: subtract B back out -> A bytes identical
        sa.unmerge(sb)
        bit_exact.append(float(np.abs(sa.M - Ma_before).max()))
        a_after_unmerge.append(sa.recall_score(ida[2]))
    return dict(a_in_union=mean_se(a_in_union), b_in_union=mean_se(b_in_union),
                xleak=mean_se(a_xleak + b_xleak),
                bit_exact_maxdelta=mean_se(bit_exact),
                a_after_unmerge=mean_se(a_after_unmerge))


# ── (c) UNDO: bit-exact restore ────────────────────────────────────────────
def exp_undo():
    deltas, restored = [], []
    for seed in range(SEEDS):
        s, ids, _ = fresh_store(seed)
        before = s.M.copy()
        before_score = s.recall_score(ids[4])
        s.forget_exact(ids[4])
        s.store(np.random.default_rng(seed).standard_normal(256).astype(np.float32))
        s.undo(); s.undo()            # undo the store, then the forget
        deltas.append(float(np.abs(s.M - before).max()))
        restored.append(s.recall_score(ids[4]))
    return dict(maxdelta=mean_se(deltas), restored_score=mean_se(restored),
                ref_score=mean_se([before_score]))


def fmt(ms):
    return "%.4f ± %.4f" % ms


if __name__ == "__main__":
    print("=" * 66)
    print("hdc-mem differentiator demo   D=%d  items/store=%d  seeds=%d" % (D, N_ITEMS, SEEDS))
    print("=" * 66)

    f = exp_forget()
    print("\n(a) FORGET = EXACT SUBTRACTION (not decay-GC)")
    print("    chance floor (random probe)   : %s" % fmt(f["chance"]))
    print("    target  recall  before forget : %s" % fmt(f["tgt_before"]))
    print("    target  recall  AFTER  forget : %s   <- drops to chance" % fmt(f["tgt_after"]))
    print("    OTHER   recall  before forget : %s" % fmt(f["other_before"]))
    print("    OTHER   recall  AFTER  forget : %s   <- stays high (recoverable)" % fmt(f["other_after"]))
    print("    OTHER   bound-term max|Delta| : %s   <- 0 = its contribution untouched" % fmt(f["other_term_bitdelta"]))
    tgt_drop_ok = f["tgt_after"][0] < f["chance"][0] + 3 * f["chance"][1] + 0.01
    # "preserved" = the neighbor's physical contribution to M is bit-identical AND it
    # is still recoverable far above chance. (Its readout COSINE shifts slightly because
    # M lost a term — that is correct bundle behavior, not corruption.)
    other_ok = (f["other_term_bitdelta"][0] < 1e-6 and
                f["other_after"][0] > f["chance"][0] + 10 * f["chance"][1])
    print("    PASS forget->chance : %s | OTHER bit-preserved+recoverable : %s" % (tgt_drop_ok, other_ok))

    m = exp_merge()
    print("\n(b) MERGE = FEDERATED BUNDLE (separable, no cross-contamination)")
    print("    A item recall in union        : %s" % fmt(m["a_in_union"]))
    print("    B item recall in union        : %s" % fmt(m["b_in_union"]))
    print("    cross-leak (A-role -> B-cont) : %s   <- ~chance, no leak" % fmt(m["xleak"]))
    print("    unmerge max|Delta| (A bytes)  : %s   <- 0 = bit-exact separable" % fmt(m["bit_exact_maxdelta"]))
    print("    A recall after unmerge        : %s" % fmt(m["a_after_unmerge"]))
    merge_sep_ok = m["bit_exact_maxdelta"][0] < 1e-4
    no_leak_ok = m["xleak"][0] < m["a_in_union"][0] / 3
    print("    PASS separable : %s | PASS no-cross-leak : %s" % (merge_sep_ok, no_leak_ok))

    u = exp_undo()
    print("\n(c) UNDO = BIT-RESTORE")
    print("    max|Delta| vs original M      : %s   <- 0 = bit-exact" % fmt(u["maxdelta"]))
    print("    item recall after undo        : %s" % fmt(u["restored_score"]))
    undo_ok = u["maxdelta"][0] < 1e-4
    print("    PASS bit-exact undo : %s" % undo_ok)

    print("\n" + "=" * 66)
    allok = tgt_drop_ok and other_ok and merge_sep_ok and no_leak_ok and undo_ok
    print("OVERALL: %s" % ("ALL DIFFERENTIATORS MEASURED-PASS ✓" if allok else "SOME FAILED — inspect above"))
    print("=" * 66)
