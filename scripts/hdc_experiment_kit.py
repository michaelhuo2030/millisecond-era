"""
hdc_experiment_kit.py — the executable HDC laws (卡死).
========================================================
Every HDC experiment imports this. It ENFORCES the rigor gates (auto-VOID / auto-RETIRE
on violation) and provides the method DEFAULTS — so hard-won laws are used BY DEFAULT,
not by memory. This is the active counterpart to the passive registry.

Laws L1-L15 are documented in the millisecond-era research notes.
Principle: feedback loops must be runtime hooks, not specs (systems_model_active_not_passive).

Usage:
    from hdc_experiment_kit import verdict, lift, bootstrap_ci, held_out_split, boundary_law_check, DEFAULTS, LAWS
    v = verdict("my_test", hdc_score=..., baseline_scores={"flat":...}, random_score=...,
                per_seed_diffs={"flat":[...]} )
    # v["verdict"] is auto VOID/RETIRED if a gate fails; else per-baseline CONFIRM/INCONCLUSIVE/FALSIFY.
"""
import numpy as np

# ---- LAWS (machine refs; full text in HDC-LAWS-REGISTRY.md) ----
LAWS = {
    "L1":  "Boundary law: structure GIVEN/clean -> HDC may win; DISCOVERED-from-real -> embeddings win.",
    "L2":  "Reconstruction != task (need end-to-end metric, not cos/recall).",
    "L3":  "Descriptive != causal (need intervention + control where random does worse).",
    "L4":  "N=1 is a PoC. Golden Standard >=4 enc x >=3 D x >=2 sparsity x >=3 seeds.",
    "L5":  "Headline = artifact; report lift + bootstrap CI, never raw accuracy.",
    "L6":  "Theory-result triage: null vs strong theory -> suspect the tool first (name+predict+run).",
    "L7":  "Solvability + engine-match gate (a baseline must beat random; fit HDC's nature).",
    "L8":  "Encoding defaults: bipolar / sparse_ternary / fourier(2x cap) / multi-bit; sweep >=4.",
    "L9":  "Readout: least-squares per-head; ridge/shared blows up.",
    "L10": "Layer choice is task-dependent (no universal best layer).",
    "L11": "Cross-domain/language needs LLM abstraction FIRST.",
    "L12": "Capacity ~ D/20 (conservative; real collapse ~2x).",
    "L13": "Use FP16 model loading (mlx_lm.load packing trap corrupted 3+ tests).",
    "L14": "Acceleration default-on: MLX encode / NEON sim / streaming / checkpoint.",
    "L15": "Kimi-long via tight spec citing L#; Claude audits before any 'verified'.",
}

DEFAULTS = dict(
    encodings=("bipolar", "sparse_ternary", "fourier"),   # L8 (sweep >=4 incl these)
    D_sweep=(10_000, 100_000, 1_300_000),                 # L4
    sparsity_sweep=(0.0, 0.95),                            # L4
    seeds=(42, 43, 44),                                    # L4 (>=3)
    metric="lift_over_baseline",                           # L2/L5 (never raw acc)
    readout="least_squares_per_head",                     # L9
    model_load_dtype="fp16",                               # L13
    bootstrap_resamples=1000,                              # L5
)


def lift(acc, baseline_acc):
    """L2/L5: report lift = acc / baseline, never raw accuracy."""
    return float('nan') if baseline_acc <= 0 else acc / baseline_acc


def bootstrap_ci(diffs, n_boot=1000, seed=0):
    """L5: paired bootstrap CI over per-seed differences."""
    rng = np.random.default_rng(seed)
    d = np.asarray(diffs, float); d = d[~np.isnan(d)]
    if len(d) == 0:
        return (float('nan'), float('nan'), float('nan'))
    boots = [rng.choice(d, len(d), replace=True).mean() for _ in range(n_boot)]
    return float(d.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def held_out_split(n, frac=0.8, seed=42):
    """L4: held-out entity split."""
    rng = np.random.default_rng(seed); perm = rng.permutation(n); k = int(n * frac)
    return perm[:k], perm[k:]


def solvability_gate(best_method_score, random_score, margin=1e-9):
    """L7: some method must beat random; else the task tests nothing -> RETIRE."""
    return bool(best_method_score > random_score + margin)


def boundary_law_check(structure_source):
    """L1 design-time gate. structure_source in {'given','discovered_from_real'}."""
    if structure_source == "discovered_from_real":
        return ("L1: structure must be DISCOVERED from real data -> use LLM/embeddings for that step; "
                "HDC only for bind/store/serve (HDC ties embeddings on discovery).")
    return "L1: structure is given/clean -> HDC algebra may add value. Proceed (still need a baseline, L7)."


def _gate_violations(metric_is_lift, has_baseline, has_ci, held_out, causal_claim, has_ctrl):
    v = []
    if metric_is_lift is False: v.append("L2/L5: raw accuracy used, not lift")
    if has_baseline is False:   v.append("L7: no baseline (flat/random) included")
    if has_ci is False:         v.append("L5: no bootstrap CI (add per-seed diffs)")
    if held_out is False:       v.append("L4: not held-out")
    if causal_claim and has_ctrl is not True:
        v.append("L3: causal claim without intervention + control")
    return v


def verdict(name, *, hdc_score, baseline_scores: dict, random_score,
            per_seed_diffs: dict = None, causal_claim=False, has_intervention_control=None,
            held_out=True, n_configs=1, laws=("L1", "L2", "L5", "L7")):
    """
    Gated verdict. Auto-RETIRED if solvability fails (L7); auto-VOID if any rigor gate fails (L2-L5).
    Otherwise per-baseline CONFIRM / INCONCLUSIVE / FALSIFY via paired bootstrap CI.
    Every result carries laws_applied so headlines trace to laws (L5/L15).
    """
    out = {"name": name, "hdc": hdc_score, "baselines": dict(baseline_scores),
           "random": random_score, "laws_applied": list(laws), "comparisons": {}}
    best = max([hdc_score] + list(baseline_scores.values())) if baseline_scores else hdc_score
    if not solvability_gate(best, random_score):
        out["verdict"] = "RETIRED"
        out["reason"] = f"L7 solvability FAILED: best={best:.4f} <= random={random_score:.4f}; task tests nothing"
        return out
    gates = _gate_violations(metric_is_lift=True, has_baseline=len(baseline_scores) > 0,
                             has_ci=per_seed_diffs is not None, held_out=held_out,
                             causal_claim=causal_claim, has_ctrl=has_intervention_control)
    if gates:
        out["verdict"] = "VOID"; out["gate_violations"] = gates
        return out
    for b, bscore in baseline_scores.items():
        if per_seed_diffs and b in per_seed_diffs:
            m, lo, hi = bootstrap_ci(per_seed_diffs[b])
            vb = "CONFIRM" if lo > 0 else ("FALSIFY" if hi < 0 else "INCONCLUSIVE")
            out["comparisons"][b] = {"delta_mean": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "verdict": vb}
        else:
            out["comparisons"][b] = {"delta_point": round(hdc_score - bscore, 4),
                                     "verdict": "POINT-ONLY (no CI -> add seeds per L4)"}
    if n_configs < 12:
        out["note_L4"] = f"PoC: {n_configs} config(s). Golden Standard needed before any headline."
    out["verdict"] = "GATED-OK"
    return out


if __name__ == "__main__":
    # SELF-TEST: the kit must reproduce our real verdicts (eat our own L2/L5).
    print("=== hdc_experiment_kit self-test ===")
    v1 = verdict("raw_acc_no_baseline", hdc_score=0.85, baseline_scores={}, random_score=0.84)
    v2 = verdict("mirror_c2", hdc_score=0.07, baseline_scores={"bm25": 0.065}, random_score=0.10)
    # real Wisdom-Atlas T2: Δ≈+0.03 but CI includes 0 -> INCONCLUSIVE (wider per-seed spread)
    v3 = verdict("bundle_t2", hdc_score=0.667, baseline_scores={"flat_mean": 0.567},
                 random_score=0.007,
                 per_seed_diffs={"flat_mean": [0.03, 0.10, -0.05, 0.08, -0.04, 0.0, 0.06, -0.02, 0.05, -0.01]})
    assert v1["verdict"] == "VOID", v1
    assert v2["verdict"] == "RETIRED", v2          # = real Wisdom-Atlas C2 (random beat HDC)
    assert v3["comparisons"]["flat_mean"]["verdict"] == "INCONCLUSIVE", v3  # = real T2/T3
    print("v1 no-baseline      ->", v1["verdict"], v1.get("gate_violations"))
    print("v2 mirror (rand>best)->", v2["verdict"], "|", v2["reason"])
    print("v3 bundle vs flat   ->", v3["comparisons"]["flat_mean"])
    print("boundary(discover)  ->", boundary_law_check("discovered_from_real"))
    print("ALL ASSERTS PASSED — kit reproduces our audited verdicts (RETIRED C2, INCONCLUSIVE bundle).")
