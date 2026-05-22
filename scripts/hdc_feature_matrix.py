"""
HDC Feature Matrix — A/B Testing Richer Features for Sign Language
==================================================================
Fixes D=10K, Path3-Retrain, 1-shot.
Tests 5 feature sets × 5 scale points (N signs) → 2D accuracy matrix.

Feature sets (incremental additions):
  F1: Right hand only           (63 dims)  — current baseline
  F2: +Left hand               (126 dims)  — bilateral signing
  F3: +Velocity                (126 dims)  — motion over time
  F4: +Left hand + Velocity    (189 dims)  — bilateral + motion
  F5: +Face landmarks          (198 dims)  — everything

Data: /tmp/msl_full_sample.csv (already cached, 118K rows, 331 columns)

Run: python3 hdc_feature_matrix.py [--cache /tmp/msl_full_sample.csv]
"""
import sys, os, time, argparse, warnings
import numpy as np
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

MINI_SKU_SPEEDUP = 52_000
D = 10_000
N_FRAMES = 10

# ── Column definitions ────────────────────────────────────────────────────────
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

FACE_COLS = [
    'NOSE_X', 'NOSE_Y', 'NOSE_Z',
    'MOUTH_LEFT_X', 'MOUTH_LEFT_Y', 'MOUTH_LEFT_Z',
    'MOUTH_RIGHT_X', 'MOUTH_RIGHT_Y', 'MOUTH_RIGHT_Z',
]

FEATURE_SETS = [
    ('F1_right',     'Right only',          63),
    ('F2_bilateral', '+Left hand',         126),
    ('F3_right+vel', '+Velocity',          126),
    ('F4_bilat+vel', '+Left+Velocity',     189),
    ('F5_all',       '+Left+Vel+Face',     198),
]


# ── Backend ───────────────────────────────────────────────────────────────────
class Backend:
    def __init__(self, d, seed=42):
        self.d = d
        self.rng = np.random.default_rng(seed)
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
        hv = lvls[-1].copy()
        idx = rng.choice(d, nf, replace=False)
        hv[idx] *= -1; lvls.append(hv)
    return np.array(lvls, dtype=np.int8)


def make_hv_space(D, n_channels, n_levels=100):
    be = Backend(D, seed=42)
    ch = np.array([be.random_hv() for _ in range(n_channels)])
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


def safe_normalize_left(xyz_63, df_has_left):
    if not df_has_left:
        return np.full(63, 0.5)
    pts = xyz_63.reshape(21, 3)
    if np.any(np.isnan(pts)) or np.all(pts == 0):
        return np.full(63, 0.5)
    return normalize_keypoints(xyz_63)


def extract_features(df_video, fset_name, df_has_left, df_has_face):
    """Extract (T, n_channels) feature array for given feature set."""
    df_s = df_video.sort_values("FRAME")

    # Right hand (always)
    right_raw = df_s[HAND_LANDMARK_COLS].values.astype(np.float64)
    right_norm = np.array([normalize_keypoints(r) for r in right_raw])   # (T,63)
    T = len(right_norm)
    if T == 0:
        return None

    # Left hand
    if df_has_left and fset_name in ('F2_bilateral', 'F4_bilat+vel', 'F5_all'):
        left_raw = df_s[LEFT_LANDMARK_COLS].values.astype(np.float64)
        left_norm = np.array([safe_normalize_left(r, df_has_left) for r in left_raw])
    else:
        left_norm = np.full((T, 63), 0.5)

    # Velocity (right hand frame-to-frame delta)
    if fset_name in ('F3_right+vel', 'F4_bilat+vel', 'F5_all'):
        vel = np.diff(right_norm, axis=0, prepend=right_norm[:1])   # (T,63)
        vel_norm = (np.clip(vel, -1, 1) + 1) / 2                    # [-1,1] → [0,1]
    else:
        vel_norm = np.full((T, 63), 0.5)

    # Face landmarks
    if df_has_face and fset_name == 'F5_all':
        face_raw = df_s[FACE_COLS].fillna(0.5).values.astype(np.float64)  # (T,9)
        face_norm = np.clip(face_raw, 0.0, 1.0)
    else:
        face_norm = np.full((T, 9), 0.5)

    # Assemble feature array
    if fset_name == 'F1_right':
        feat = right_norm                                              # (T,63)
    elif fset_name == 'F2_bilateral':
        feat = np.hstack([right_norm, left_norm])                     # (T,126)
    elif fset_name == 'F3_right+vel':
        feat = np.hstack([right_norm, vel_norm])                      # (T,126)
    elif fset_name == 'F4_bilat+vel':
        feat = np.hstack([right_norm, left_norm, vel_norm])           # (T,189)
    elif fset_name == 'F5_all':
        feat = np.hstack([right_norm, left_norm, vel_norm, face_norm]) # (T,198)
    else:
        feat = right_norm

    # Resample to N_FRAMES
    idx = np.linspace(0, T - 1, N_FRAMES).astype(int)
    return feat[idx].astype(np.float64)   # (N_FRAMES, n_ch)


def encode_video(df_video, fset_name, ch, lv, be, df_has_left, df_has_face):
    feat = extract_features(df_video, fset_name, df_has_left, df_has_face)
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
        n_correct = 0
        for hv, lbl in zip(train_hvs, train_labels):
            hv_f = hv.astype(np.float32)
            sims = {c: float(protos[c].astype(np.float32) @ hv_f) for c in classes}
            pred = max(sims, key=sims.get)
            if pred == lbl:
                n_correct += 1
            else:
                accum[lbl] += hv.astype(np.int32)
                accum[pred] -= hv.astype(np.int32)
        if n_correct == len(train_hvs):
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


# ── Data loading ──────────────────────────────────────────────────────────────
def load_dataset(cache_path):
    import pandas as pd
    print(f"Loading: {cache_path}")
    df = pd.read_csv(cache_path, on_bad_lines='skip')
    df['CLASSIFICATION'] = df['CLASSIFICATION'].astype(str)
    df_has_left  = all(c in df.columns for c in LEFT_LANDMARK_COLS[:3])
    df_has_face  = all(c in df.columns for c in FACE_COLS[:3])
    print(f"  Rows: {len(df):,}  |  left hand: {df_has_left}  |  face: {df_has_face}")
    return df, df_has_left, df_has_face


def build_sequences(df, signs):
    seqs = {}
    for sign in signs:
        df_s = df[df['CLASSIFICATION'] == sign]
        vid_dfs = {}
        for vid in sorted(df_s['VIDEO_SAMPLE'].unique()):
            dv = df_s[df_s['VIDEO_SAMPLE'] == vid]
            if all(c in dv.columns for c in HAND_LANDMARK_COLS[:3]):
                vid_dfs[vid] = dv
        if len(vid_dfs) >= 4:
            seqs[sign] = vid_dfs
    return seqs


def run_cell(n, fset_name, n_ch, sign_pool, all_seqs, df_has_left, df_has_face):
    """Run one cell of the matrix: (N signs, feature set) → accuracy."""
    signs = sign_pool[:n]
    be, ch, lv = make_hv_space(D, n_ch)
    enc = lambda dv: encode_video(dv, fset_name, ch, lv, be, df_has_left, df_has_face)

    train_hvs, train_labels = [], []
    test_hvs,  test_labels  = [], []

    for sign in signs:
        vids = list(all_seqs[sign].keys())
        h = enc(all_seqs[sign][vids[0]])
        if h is None:
            continue
        train_hvs.append(h); train_labels.append(sign)
        for vid in vids[1:]:
            h = enc(all_seqs[sign][vid])
            if h is not None:
                test_hvs.append(h); test_labels.append(sign)

    if not train_hvs or not test_hvs:
        return None, None

    protos = hdc_perceptron(train_hvs, train_labels, be, n_iters=20)
    acc, lat = measure_accuracy(protos, test_hvs, test_labels, be)
    return acc, lat


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', default='/tmp/msl_full_sample.csv')
    parser.add_argument('--min-videos', type=int, default=4)
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  HDC FEATURE MATRIX — A/B Testing Richer Features for Sign Language     ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print(f"D={D:,}  |  Path3-Retrain  |  1-shot  |  20 iters\n")

    df, df_has_left, df_has_face = load_dataset(args.cache)

    sign_counts = df.groupby('CLASSIFICATION')['VIDEO_SAMPLE'].nunique()
    eligible = [s for s in sorted(df['CLASSIFICATION'].dropna().unique())
                if sign_counts.get(s, 0) >= args.min_videos]
    print(f"Signs with ≥{args.min_videos} videos: {len(eligible)}")

    all_seqs = build_sequences(df, eligible)
    sign_pool = sorted(all_seqs.keys())
    N_MAX = len(sign_pool)
    print(f"Signs with valid sequences: {N_MAX}\n")

    raw_points = [8, 20, 40, 80, N_MAX]
    scale_points = sorted(set(min(n, N_MAX) for n in raw_points if n <= N_MAX))
    if N_MAX not in scale_points:
        scale_points.append(N_MAX)
    scale_points = sorted(set(scale_points))
    print(f"Scale points: {scale_points}")
    print(f"Feature sets: {[f[1] for f in FEATURE_SETS]}\n")

    # Matrix: results[fset_name][N] = (acc, lat)
    results = {fset: {} for fset, _, _ in FEATURE_SETS}
    total_cells = len(FEATURE_SETS) * len(scale_points)
    cell = 0

    for fset_name, fset_label, n_ch in FEATURE_SETS:
        print(f"\n── {fset_label} ({n_ch} dims) ──────────────────────────────")
        for n in scale_points:
            cell += 1
            print(f"  [{cell:2d}/{total_cells}] N={n:3d}  ", end='', flush=True)
            t0 = time.perf_counter()
            acc, lat = run_cell(n, fset_name, n_ch, sign_pool, all_seqs,
                                df_has_left, df_has_face)
            elapsed = (time.perf_counter() - t0) * 1000
            results[fset_name][n] = (acc, lat)
            if acc is not None:
                print(f"acc={acc:.1f}%  lat={lat:.3f}ms  ({elapsed:.0f}ms total)")
            else:
                print("FAILED")

    # ── Print final matrix ────────────────────────────────────────────────────
    SEP = "═" * 86
    baseline_key = FEATURE_SETS[0][0]
    print(f"\n{SEP}")
    print(f"  HDC FEATURE MATRIX — Sign Language (MSL-150)  {time.strftime('%Y-%m-%d')}")
    print(f"  Method: Path3-Retrain  D={D:,}  1-shot  20 iters")
    print(f"{SEP}")

    col_w = 7
    hdr = f"  {'Feature set':<22} {'dims':>4}   "
    hdr += "   ".join(f"N={n:3d}" for n in scale_points)
    hdr += f"   {'gain@N_max':>10}"
    print(hdr)
    print("  " + "─" * 82)

    baseline_at_nmax = results[baseline_key].get(N_MAX, (None,))[0]

    for fset_name, fset_label, n_ch in FEATURE_SETS:
        row = f"  {fset_label:<22} {n_ch:>4}   "
        acc_at_nmax = results[fset_name].get(N_MAX, (None,))[0]
        for n in scale_points:
            acc, _ = results[fset_name].get(n, (None, None))
            cell_str = f"{acc:.1f}%" if acc is not None else " FAIL"
            row += f"{cell_str:>{col_w}}   "
        if acc_at_nmax is not None and baseline_at_nmax is not None:
            gain = acc_at_nmax - baseline_at_nmax
            gain_str = f"{gain:+.1f}pp"
        else:
            gain_str = "—"
        row += f"{gain_str:>10}"
        print(row)

    print(f"{SEP}")
    print(f"\n  Key question: which feature addition gives the best accuracy/cost tradeoff?")
    print(f"  Cost order: F1 < F2=F3 < F4 < F5 (more dims = slower encoding)")
    print(f"  Chip lat at D={D:,}: ~0.0005μs/query regardless of feature set")
    print(f"{SEP}")

    # Save
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"hdc-feature-matrix-results-{time.strftime('%Y-%m-%d')}.txt")
    with open(out, 'w') as f:
        f.write(f"HDC Feature Matrix  MSL-150  D={D}  {time.strftime('%Y-%m-%d')}\n")
        f.write(f"Method: Path3-Retrain  1-shot  20 iters\n\n")
        f.write(f"{'Feature':<22} {'dims':>4}")
        for n in scale_points:
            f.write(f"  N={n:3d}")
        f.write(f"  {'gain@{}'.format(N_MAX):>10}\n")
        for fset_name, fset_label, n_ch in FEATURE_SETS:
            f.write(f"{fset_label:<22} {n_ch:>4}")
            acc_at_nmax = results[fset_name].get(N_MAX, (None,))[0]
            for n in scale_points:
                acc, _ = results[fset_name].get(n, (None, None))
                f.write(f"  {acc:.1f}%" if acc else "   FAIL")
            if acc_at_nmax and baseline_at_nmax:
                f.write(f"  {acc_at_nmax - baseline_at_nmax:+.1f}pp")
            f.write("\n")
    print(f"\nResults saved: {out}")


if __name__ == "__main__":
    main()
