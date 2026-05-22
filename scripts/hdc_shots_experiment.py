"""
HDC Multi-Shot Experiment — Accuracy vs. Training Videos per Sign
=================================================================
Answers: "how much does accuracy improve with more training data per sign?"

Fix: N=139 signs, D=10K, Path3-Retrain, 20 iters
Vary: n_shot (1, 2, 3, max) × feature set (F1 right, F2 bilateral, F2+vel)

Key hypothesis: velocity flips from harmful (1-shot) to helpful (3+ shots)
as motion patterns average out across multiple training videos.

Run: python3 hdc_shots_experiment.py [--cache /tmp/msl_full_sample.csv]
"""
import sys, os, time, argparse, warnings
import numpy as np
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

D        = 10_000
N_FRAMES = 10
MINI_SKU = 52_000

HAND_LANDMARK_COLS = [
    "RIGHT_WRIST_X","RIGHT_WRIST_Y","RIGHT_WRIST_Z",
    "RIGHT_THUMB_CMC_X","RIGHT_THUMB_CMC_Y","RIGHT_THUMB_CMC_Z",
    "RIGHT_THUMB_MCP_X","RIGHT_THUMB_MCP_Y","RIGHT_THUMB_MCP_Z",
    "RIGHT_THUMB_IP_X","RIGHT_THUMB_IP_Y","RIGHT_THUMB_IP_Z",
    "RIGHT_THUMB_TIP_X","RIGHT_THUMB_TIP_Y","RIGHT_THUMB_TIP_Z",
    "RIGHT_INDEX_FINGER_MCP_X","RIGHT_INDEX_FINGER_MCP_Y","RIGHT_INDEX_FINGER_MCP_Z",
    "RIGHT_INDEX_FINGER_PIP_X","RIGHT_INDEX_FINGER_PIP_Y","RIGHT_INDEX_FINGER_PIP_Z",
    "RIGHT_INDEX_FINGER_DIP_X","RIGHT_INDEX_FINGER_DIP_Y","RIGHT_INDEX_FINGER_DIP_Z",
    "RIGHT_INDEX_FINGER_TIP_X","RIGHT_INDEX_FINGER_TIP_Y","RIGHT_INDEX_FINGER_TIP_Z",
    "RIGHT_MIDDLE_FINGER_MCP_X","RIGHT_MIDDLE_FINGER_MCP_Y","RIGHT_MIDDLE_FINGER_MCP_Z",
    "RIGHT_MIDDLE_FINGER_PIP_X","RIGHT_MIDDLE_FINGER_PIP_Y","RIGHT_MIDDLE_FINGER_PIP_Z",
    "RIGHT_MIDDLE_FINGER_DIP_X","RIGHT_MIDDLE_FINGER_DIP_Y","RIGHT_MIDDLE_FINGER_DIP_Z",
    "RIGHT_MIDDLE_FINGER_TIP_X","RIGHT_MIDDLE_FINGER_TIP_Y","RIGHT_MIDDLE_FINGER_TIP_Z",
    "RIGHT_RING_FINGER_MCP_X","RIGHT_RING_FINGER_MCP_Y","RIGHT_RING_FINGER_MCP_Z",
    "RIGHT_RING_FINGER_PIP_X","RIGHT_RING_FINGER_PIP_Y","RIGHT_RING_FINGER_PIP_Z",
    "RIGHT_RING_FINGER_DIP_X","RIGHT_RING_FINGER_DIP_Y","RIGHT_RING_FINGER_DIP_Z",
    "RIGHT_RING_FINGER_TIP_X","RIGHT_RING_FINGER_TIP_Y","RIGHT_RING_FINGER_TIP_Z",
    "RIGHT_PINKY_MCP_X","RIGHT_PINKY_MCP_Y","RIGHT_PINKY_MCP_Z",
    "RIGHT_PINKY_PIP_X","RIGHT_PINKY_PIP_Y","RIGHT_PINKY_PIP_Z",
    "RIGHT_PINKY_DIP_X","RIGHT_PINKY_DIP_Y","RIGHT_PINKY_DIP_Z",
    "RIGHT_PINKY_TIP_X","RIGHT_PINKY_TIP_Y","RIGHT_PINKY_TIP_Z",
]
LEFT_LANDMARK_COLS = [c.replace("RIGHT_", "LEFT_") for c in HAND_LANDMARK_COLS]

FEATURE_SETS = [
    ('F1_right',     'F1 right only',   63),
    ('F2_bilateral', 'F2 bilateral',    126),
    ('F2vel',        'F2+velocity',     189),
]


# ── Backend (verbatim from hdc_feature_matrix.py) ────────────────────────────
class Backend:
    def __init__(self, d, seed=42):
        self.d = d; self.rng = np.random.default_rng(seed)
    def random_hv(self):
        return (self.rng.integers(0, 2, self.d) * 2 - 1).astype(np.int8)
    def bind(self, a, b): return (a * b).astype(np.int8)
    def bundle(self, hvs):
        arr = np.stack(hvs) if not isinstance(hvs, np.ndarray) else hvs
        s = arr.astype(np.int32).sum(axis=0)
        r = np.where(s >= 0, 1, -1).astype(np.int8)
        ties = (s == 0)
        if ties.any():
            r[ties] = (self.rng.integers(0, 2, int(ties.sum())) * 2 - 1).astype(np.int8)
        return r
    def permute(self, hv, n): return np.roll(hv, n)
    def cos_batch(self, protos_f, query_f):
        norms = np.linalg.norm(protos_f, axis=1) * np.linalg.norm(query_f) + 1e-9
        return protos_f @ query_f / norms

def make_level_hvs(n, d, seed=99):
    rng = np.random.default_rng(seed)
    base = (rng.integers(0, 2, d) * 2 - 1).astype(np.int8)
    lvls = [base.copy()]; nf = d // n
    for _ in range(1, n):
        hv = lvls[-1].copy(); idx = rng.choice(d, nf, replace=False)
        hv[idx] *= -1; lvls.append(hv)
    return np.array(lvls, dtype=np.int8)

def make_hv_space(D, n_ch, n_levels=100):
    be = Backend(D, seed=42)
    ch = np.array([be.random_hv() for _ in range(n_ch)])
    lv = make_level_hvs(n_levels, D, seed=99)
    return be, ch, lv


# ── Feature extraction ────────────────────────────────────────────────────────
def normalize_keypoints(xyz_63):
    pts = xyz_63.reshape(21, 3)
    if np.any(np.isnan(pts)):
        pts = np.nan_to_num(pts, nan=0.0)
    wrist = pts[0].copy()
    centered = pts - wrist
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)

def safe_left(xyz_63):
    pts = xyz_63.reshape(21, 3)
    if np.any(np.isnan(pts)) or np.all(pts == 0):
        return np.full(63, 0.5)
    return normalize_keypoints(xyz_63)

def extract_features(df_video, fset_name, df_has_left):
    df_s = df_video.sort_values("FRAME")
    right_raw  = df_s[HAND_LANDMARK_COLS].values.astype(np.float64)
    right_norm = np.array([normalize_keypoints(r) for r in right_raw])
    T = len(right_norm)
    if T == 0:
        return None

    if df_has_left and fset_name in ('F2_bilateral', 'F2vel'):
        left_raw  = df_s[LEFT_LANDMARK_COLS].values.astype(np.float64)
        left_norm = np.array([safe_left(r) for r in left_raw])
    else:
        left_norm = np.full((T, 63), 0.5)

    if fset_name == 'F2vel':
        vel      = np.diff(right_norm, axis=0, prepend=right_norm[:1])
        vel_norm = (np.clip(vel, -1, 1) + 1) / 2
    else:
        vel_norm = np.full((T, 63), 0.5)

    if fset_name == 'F1_right':
        feat = right_norm
    elif fset_name == 'F2_bilateral':
        feat = np.hstack([right_norm, left_norm])
    elif fset_name == 'F2vel':
        feat = np.hstack([right_norm, left_norm, vel_norm])
    else:
        feat = right_norm

    idx = np.linspace(0, T - 1, N_FRAMES).astype(int)
    return feat[idx].astype(np.float64)

def encode_video(df_video, fset_name, ch, lv, be, df_has_left):
    feat = extract_features(df_video, fset_name, df_has_left)
    if feat is None:
        return None
    fhvs = [be.permute(encode_level(feat[t], ch, lv, be), t) for t in range(N_FRAMES)]
    return be.bundle(fhvs)


# ── Perceptron + accuracy ─────────────────────────────────────────────────────
def hdc_perceptron(train_hvs, train_labels, be, n_iters=20):
    classes = sorted(set(train_labels))
    accum = {c: np.zeros(be.d, dtype=np.int32) for c in classes}
    for hv, lbl in zip(train_hvs, train_labels):
        accum[lbl] += hv.astype(np.int32)
    def get_protos():
        return {c: np.where(a >= 0, 1, -1).astype(np.int8) for c, a in accum.items()}
    for _ in range(n_iters):
        protos = get_protos()
        n_ok = 0
        for hv, lbl in zip(train_hvs, train_labels):
            hv_f = hv.astype(np.float32)
            sims = {c: float(protos[c].astype(np.float32) @ hv_f) for c in classes}
            pred = max(sims, key=sims.get)
            if pred == lbl:
                n_ok += 1
            else:
                accum[lbl] += hv.astype(np.int32)
                accum[pred] -= hv.astype(np.int32)
        if n_ok == len(train_hvs):
            break
    return get_protos()

def measure_accuracy(protos, test_hvs, test_labels, be):
    classes = sorted(protos.keys())
    proto_mat = np.stack([protos[c].astype(np.float32) for c in classes])
    correct = 0
    t0 = time.perf_counter()
    for hv, lbl in zip(test_hvs, test_labels):
        sims = be.cos_batch(proto_mat, hv.astype(np.float32))
        if classes[int(np.argmax(sims))] == lbl:
            correct += 1
    elapsed = (time.perf_counter() - t0) * 1000
    return correct / max(len(test_hvs), 1) * 100, elapsed / max(len(test_hvs), 1)


# ── Data ──────────────────────────────────────────────────────────────────────
def build_sequences(df, signs):
    seqs = {}
    for sign in signs:
        df_s = df[df['CLASSIFICATION'] == sign]
        vid_dfs = {}
        for vid in sorted(df_s['VIDEO_SAMPLE'].unique()):
            dv = df_s[df_s['VIDEO_SAMPLE'] == vid]
            if all(c in dv.columns for c in HAND_LANDMARK_COLS[:3]):
                vid_dfs[vid] = dv
        if len(vid_dfs) >= 2:   # need at least 1 train + 1 test
            seqs[sign] = vid_dfs
    return seqs


# ── Multi-shot cell runner ────────────────────────────────────────────────────
def run_cell(sign_pool, all_seqs, fset_name, n_ch, n_shot, df_has_left):
    be, ch, lv = make_hv_space(D, n_ch)
    enc = lambda dv: encode_video(dv, fset_name, ch, lv, be, df_has_left)

    train_hvs, train_labels = [], []
    test_hvs,  test_labels  = [], []
    n_skipped = 0

    for sign in sign_pool:
        vids = list(all_seqs[sign].keys())
        n_avail = len(vids)
        if n_avail < 2:
            n_skipped += 1; continue
        n_train = min(n_shot, n_avail - 1)   # always keep ≥1 for test
        train_vids = vids[:n_train]
        test_vids  = vids[n_train:]

        for vid in train_vids:
            h = enc(all_seqs[sign][vid])
            if h is not None:
                train_hvs.append(h); train_labels.append(sign)
        for vid in test_vids:
            h = enc(all_seqs[sign][vid])
            if h is not None:
                test_hvs.append(h); test_labels.append(sign)

    if not train_hvs or not test_hvs:
        return None, None, 0

    protos = hdc_perceptron(train_hvs, train_labels, be, n_iters=20)
    acc, lat = measure_accuracy(protos, test_hvs, test_labels, be)
    return acc, lat, len(test_hvs)


# ── Log-curve projection ──────────────────────────────────────────────────────
def project_accuracy(shots, accs, target_shots):
    """Fit acc = a*log(k) + b to (shots, accs), project to target_shots."""
    if len(shots) < 2:
        return None
    xs = np.log(np.array(shots, dtype=float))
    ys = np.array(accs, dtype=float)
    # Least squares: [log(k), 1] * [a, b]^T = acc
    A = np.column_stack([xs, np.ones_like(xs)])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(A, ys, rcond=None)
        a, b = coeffs
        return min(99.0, a * np.log(target_shots) + b)
    except Exception:
        return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', default='/tmp/msl_full_sample.csv')
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  HDC MULTI-SHOT EXPERIMENT — How Many Training Videos Per Sign?         ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print(f"D={D:,}  |  Path3-Retrain  |  N=139 signs  |  20 iters\n")

    import pandas as pd
    print(f"Loading: {args.cache}")
    df = pd.read_csv(args.cache, on_bad_lines='skip')
    df['CLASSIFICATION'] = df['CLASSIFICATION'].astype(str)
    df_has_left = all(c in df.columns for c in LEFT_LANDMARK_COLS[:3])
    print(f"  {len(df):,} rows  |  left hand: {df_has_left}\n")

    sign_counts = df.groupby('CLASSIFICATION')['VIDEO_SAMPLE'].nunique()
    eligible = [s for s in sorted(df['CLASSIFICATION'].dropna().unique())
                if sign_counts.get(s, 0) >= 2]

    all_seqs = build_sequences(df, eligible)
    sign_pool = sorted(all_seqs.keys())
    N_MAX_SIGNS = len(sign_pool)

    # Video count distribution
    vid_counts = [len(v) for v in all_seqs.values()]
    print(f"Signs available: {N_MAX_SIGNS}")
    print(f"Videos/sign: min={min(vid_counts)} max={max(vid_counts)} "
          f"mean={np.mean(vid_counts):.1f} median={np.median(vid_counts):.0f}\n")

    # Shot levels: 1, 2, 3, max-available
    max_possible = max(v - 1 for v in vid_counts)   # max train shots (keep 1 test)
    shot_levels = sorted(set([1, 2, 3, max_possible]))
    print(f"Shot levels to test: {shot_levels}")
    print(f"(max={max_possible} means all-but-1 as train)\n")

    total_cells = len(FEATURE_SETS) * len(shot_levels)
    results = {}   # (fset_name, n_shot) → (acc, lat)
    cell = 0

    for fset_name, fset_label, n_ch in FEATURE_SETS:
        print(f"── {fset_label} ({n_ch} dims) ──────────────────────────────")
        for n_shot in shot_levels:
            cell += 1
            print(f"  [{cell:2d}/{total_cells}] {n_shot}-shot  ", end='', flush=True)
            t0 = time.perf_counter()
            acc, lat, n_test = run_cell(sign_pool, all_seqs, fset_name,
                                        n_ch, n_shot, df_has_left)
            elapsed = (time.perf_counter() - t0) * 1000
            results[(fset_name, n_shot)] = (acc, lat)
            if acc is not None:
                print(f"acc={acc:.1f}%  n_test={n_test}  ({elapsed:.0f}ms)")
            else:
                print("FAILED")
        print()

    # ── Final table ───────────────────────────────────────────────────────────
    SEP = "═" * 72
    print(f"\n{SEP}")
    print(f"  HDC MULTI-SHOT — Sign Language (MSL-150)  {time.strftime('%Y-%m-%d')}")
    print(f"  N=139 signs  |  D={D:,}  |  Path3-Retrain  |  20 iters")
    print(f"{SEP}")

    shot_labels = [f"{k}-shot" for k in shot_levels]
    hdr = f"  {'Feature set':<18}  " + "  ".join(f"{s:>8}" for s in shot_labels)
    hdr += f"  {'proj@30':>8}  {'proj@100':>9}"
    print(hdr)
    print("  " + "─" * 68)

    for fset_name, fset_label, n_ch in FEATURE_SETS:
        accs = []
        row  = f"  {fset_label:<18}  "
        for n_shot in shot_levels:
            acc, _ = results.get((fset_name, n_shot), (None, None))
            accs.append((n_shot, acc))
            row += f"  {acc:.1f}%  " if acc else "  FAIL   "

        # Project
        valid = [(k, a) for k, a in accs if a is not None]
        p30  = project_accuracy([k for k,_ in valid], [a for _,a in valid], 30)
        p100 = project_accuracy([k for k,_ in valid], [a for _,a in valid], 100)
        row += f"  {p30:.1f}%*" if p30 else "      —  "
        row += f"  {p100:.1f}%*" if p100 else "       —"
        print(row)

    print(f"\n  * projected (log fit: acc = a·log(k) + b) — not measured")
    print(f"\n  Key question: at which n_shot does velocity (+vel) surpass bilateral?")
    print(f"  Velocity hurts at 1-shot (noise > signal), should help at 3+ shots.")
    print(f"{SEP}")

    # Save
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"hdc-shots-results-{time.strftime('%Y-%m-%d')}.txt")
    with open(out, 'w') as f:
        f.write(f"HDC Multi-Shot  MSL-150  N=139  D={D}  {time.strftime('%Y-%m-%d')}\n\n")
        f.write(f"{'Feature':<18}")
        for k in shot_levels:
            f.write(f"  {k}-shot")
        f.write(f"  proj@30  proj@100\n")
        for fset_name, fset_label, n_ch in FEATURE_SETS:
            f.write(f"{fset_label:<18}")
            valid = []
            for n_shot in shot_levels:
                acc, _ = results.get((fset_name, n_shot), (None, None))
                f.write(f"  {acc:.1f}%" if acc else "   FAIL")
                if acc: valid.append((n_shot, acc))
            p30  = project_accuracy([k for k,_ in valid], [a for _,a in valid], 30)
            p100 = project_accuracy([k for k,_ in valid], [a for _,a in valid], 100)
            f.write(f"  {p30:.1f}%*" if p30 else "      —")
            f.write(f"  {p100:.1f}%*\n" if p100 else "       —\n")
        f.write("\n* log fit projection\n")
    print(f"Results saved: {out}")


if __name__ == "__main__":
    main()
