"""
HDC Scalability — Accuracy vs. Number of Sign Classes (8 → 150)
================================================================
Method: Path3-Retrain (iterative perceptron, our best from benchmark matrix)
Data:   MSL-150 (Mexican Sign Language, 13.29 GB Zenodo file)
        — reads 150 evenly-spaced 3 MB windows = 450 MB total (cached locally)

Run: python3 hdc_scalability.py [--cache /tmp/msl_full_sample.csv]
"""
import sys, os, time, argparse, urllib.request, io, warnings
import numpy as np
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

MINI_SKU_SPEEDUP = 52_000

MSL_ZENODO_URL = ("https://zenodo.org/records/17783312/files/"
                  "MSL-150_Mexican_Sign_Language_Dataset.csv")
MSL_FILE_SIZE   = 13_285_820_704

N_RANGES = 150
WINDOW   = 3_000_000    # 3 MB per window
STEP     = MSL_FILE_SIZE // N_RANGES  # ~88 MB apart

MSL_RANGES = [(i * STEP, min(i * STEP + WINDOW, MSL_FILE_SIZE - 1))
              for i in range(N_RANGES)]

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


# ── Sign encoding ─────────────────────────────────────────────────────────────
def normalize_keypoints(xyz_63):
    pts = xyz_63.reshape(21, 3)
    if np.any(np.isnan(pts)):
        pts = np.nan_to_num(pts, nan=0.0)
    wrist = pts[0].copy()
    centered = pts - wrist
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)


def encode_sign_sequence(df_video, ch, lv, be, n_frames=10):
    try:
        df_sorted = df_video.sort_values("FRAME")
        raw = df_sorted[HAND_LANDMARK_COLS].values.astype(np.float64)
    except Exception:
        return None
    frames = np.array([normalize_keypoints(row) for row in raw], dtype=np.float64)
    T = len(frames)
    if T == 0:
        return None
    idx = np.linspace(0, T-1, n_frames).astype(int)
    sampled = frames[idx]
    fhvs = [be.permute(encode_level(sampled[t], ch, lv, be), t) for t in range(n_frames)]
    return be.bundle(fhvs)


# ── Perceptron ────────────────────────────────────────────────────────────────
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


# ── MSL-150 download (150 ranges) ────────────────────────────────────────────
def load_msl_range(byte_start, byte_end, header_cols):
    import pandas as pd
    req = urllib.request.Request(
        MSL_ZENODO_URL,
        headers={"Range": f"bytes={byte_start}-{byte_end}", "User-Agent": "HDC-scalability"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None
    lines = raw.split('\n')
    if byte_start == 0:
        try:
            return pd.read_csv(io.StringIO(raw), on_bad_lines='skip')
        except Exception:
            return None
    if header_cols is None:
        return None
    complete = [l for l in lines[1:] if l.count(',') >= len(header_cols) - 1]
    if not complete:
        return None
    try:
        return pd.read_csv(io.StringIO(','.join(header_cols) + '\n' + '\n'.join(complete)),
                           on_bad_lines='skip')
    except Exception:
        return None


def download_full_msl(cache_path):
    import pandas as pd
    print(f"Downloading {N_RANGES} ranges × {WINDOW//1_000_000}MB = "
          f"{N_RANGES * WINDOW // 1_000_000}MB total from Zenodo...")
    dfs = []
    header_cols = None
    failed = 0

    for i, (start, end) in enumerate(MSL_RANGES):
        pct = (i + 1) / N_RANGES * 100
        print(f"  [{i+1:3d}/{N_RANGES}] {pct:5.1f}%  bytes {start//1_000_000}M–{end//1_000_000}M  ",
              end='', flush=True)
        df = load_msl_range(start, end, header_cols)
        if df is not None and len(df) > 0:
            if header_cols is None:
                header_cols = list(df.columns)
            signs = df['CLASSIFICATION'].dropna().unique() if 'CLASSIFICATION' in df.columns else []
            print(f"rows={len(df):5d}  signs={list(signs)[:4]}")
            dfs.append(df)
        else:
            failed += 1
            print("FAILED")

    if not dfs:
        print("All ranges failed — check internet."); return None
    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv(cache_path, index=False)
    print(f"\nSaved {len(combined):,} rows → {cache_path}")
    print(f"Failed ranges: {failed}/{N_RANGES}")
    return combined


def load_or_download(cache_path):
    import pandas as pd
    if os.path.exists(cache_path):
        sz = os.path.getsize(cache_path) // 1_000_000
        print(f"Loading cache ({sz} MB): {cache_path}")
        return pd.read_csv(cache_path, on_bad_lines='skip')
    return download_full_msl(cache_path)


# ── Scalability experiment ────────────────────────────────────────────────────
def build_sequences(df, signs):
    """Pre-encode all video DataFrames per sign. Returns dict sign → {vid: df}."""
    seqs = {}
    for sign in signs:
        df_s = df[df['CLASSIFICATION'] == sign]
        vids = sorted(df_s['VIDEO_SAMPLE'].unique())
        vid_dfs = {}
        for vid in vids:
            dv = df_s[df_s['VIDEO_SAMPLE'] == vid]
            if all(c in dv.columns for c in HAND_LANDMARK_COLS[:3]):
                vid_dfs[vid] = dv
        if len(vid_dfs) >= 4:
            seqs[sign] = vid_dfs
    return seqs


def run_at_n(n, all_seqs, sign_pool, D):
    """Run Path3-Retrain for the first n signs at given D. Returns (acc, lat_ms, n_test)."""
    signs = sign_pool[:n]
    be, ch, lv = make_hv_space(D, 63)
    enc = lambda dv: encode_sign_sequence(dv, ch, lv, be)

    train_hvs, train_labels = [], []
    test_hvs,  test_labels  = [], []

    for sign in signs:
        seqs = all_seqs[sign]
        vids = list(seqs.keys())
        # 1-shot: first video trains, rest test
        h = enc(seqs[vids[0]])
        if h is None:
            continue
        train_hvs.append(h); train_labels.append(sign)
        for vid in vids[1:]:
            h = enc(seqs[vid])
            if h is not None:
                test_hvs.append(h); test_labels.append(sign)

    if not train_hvs or not test_hvs:
        return None, None, 0

    protos = hdc_perceptron(train_hvs, train_labels, be, n_iters=20)
    acc, lat = measure_accuracy(protos, test_hvs, test_labels, be)
    return acc, lat, len(test_hvs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', default='/tmp/msl_full_sample.csv')
    parser.add_argument('--min-videos', type=int, default=4)
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  HDC SCALABILITY — Sign Language  (Accuracy vs. Number of Sign Classes) ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print(f"Method: Path3-Retrain (iterative perceptron, 20 iters, 1-shot enrollment)")
    print(f"Data:   MSL-150 ({N_RANGES} ranges × {WINDOW//1_000_000}MB = "
          f"{N_RANGES*WINDOW//1_000_000}MB sampled from 13.29GB)\n")

    df = load_or_download(args.cache)
    if df is None:
        print("ERROR: could not load data"); return

    if 'CLASSIFICATION' not in df.columns:
        print("ERROR: CSV missing CLASSIFICATION column"); return

    # Normalize: cast CLASSIFICATION to str (file mixes string signs + integer digit signs)
    df['CLASSIFICATION'] = df['CLASSIFICATION'].astype(str)

    # Filter signs
    sign_counts = df.groupby('CLASSIFICATION')['VIDEO_SAMPLE'].nunique()
    all_signs_raw = sorted(df['CLASSIFICATION'].dropna().unique())
    eligible = [s for s in all_signs_raw if sign_counts.get(s, 0) >= args.min_videos]
    print(f"\nTotal unique signs in sample: {len(all_signs_raw)}")
    print(f"Signs with ≥{args.min_videos} videos:  {len(eligible)}")
    print(f"Sign list: {eligible}\n")

    if len(eligible) < 2:
        print("Not enough signs — try widening WINDOW or lowering --min-videos"); return

    # Pre-build sequence DataFrames
    print("Building sequence index...", flush=True)
    all_seqs = build_sequences(df, eligible)
    sign_pool = sorted(all_seqs.keys())
    print(f"Signs with valid sequences: {len(sign_pool)}")
    if len(sign_pool) < 2:
        print("Not enough valid sequences"); return

    # Scale points: 8, 20, 40, 80, all
    N_MAX = len(sign_pool)
    raw_points = [8, 20, 40, 80, N_MAX]
    scale_points = sorted(set(min(n, N_MAX) for n in raw_points if n <= N_MAX))
    if N_MAX not in scale_points:
        scale_points.append(N_MAX)
    scale_points = sorted(set(scale_points))

    print(f"\nScale points: {scale_points}")
    print(f"\nRunning experiments (D=10K and D=100K at each N)...\n")

    rows = []
    for n in scale_points:
        print(f"  N={n:3d}  D=10K   ", end='', flush=True)
        t0 = time.perf_counter()
        acc10, lat10, n_test10 = run_at_n(n, all_seqs, sign_pool, 10_000)
        elapsed10 = (time.perf_counter() - t0) * 1000
        if acc10 is not None:
            print(f"acc={acc10:.1f}%  n_test={n_test10}  {elapsed10:.0f}ms total", flush=True)
        else:
            print("FAILED", flush=True)

        print(f"  N={n:3d}  D=100K  ", end='', flush=True)
        t0 = time.perf_counter()
        acc100, lat100, n_test100 = run_at_n(n, all_seqs, sign_pool, 100_000)
        elapsed100 = (time.perf_counter() - t0) * 1000
        if acc100 is not None:
            print(f"acc={acc100:.1f}%  n_test={n_test100}  {elapsed100:.0f}ms total", flush=True)
        else:
            print("FAILED", flush=True)

        rows.append({
            'n': n,
            'acc10': acc10, 'lat10': lat10,
            'acc100': acc100, 'lat100': lat100,
            'n_test': n_test10,
        })

    # Print final table
    SEP = "═" * 74
    print(f"\n{SEP}")
    print(f"  HDC SCALABILITY — Sign Language (MSL-150)  {time.strftime('%Y-%m-%d')}")
    print(f"  Method: Path3-Retrain  |  1-shot enrollment  |  20 perceptron iters")
    print(f"{SEP}")
    print(f"  {'N signs':>8}   {'D=10K':>7}   {'D=100K':>7}   {'Δ (100K−10K)':>13}   "
          f"{'Mac lat (10K)':>14}   {'Chip lat (10K)':>14}")
    print(f"  {'─'*8}   {'─'*7}   {'─'*7}   {'─'*13}   {'─'*14}   {'─'*14}")

    for r in rows:
        a10  = f"{r['acc10']:.1f}%"  if r['acc10']  is not None else "FAIL"
        a100 = f"{r['acc100']:.1f}%" if r['acc100'] is not None else "FAIL"
        if r['acc10'] is not None and r['acc100'] is not None:
            delta = r['acc100'] - r['acc10']
            d_str = f"{delta:+.1f}pp"
        else:
            d_str = "—"
        lat_str  = f"{r['lat10']:.3f}ms"   if r['lat10']  is not None else "—"
        chip_str = f"{r['lat10']/MINI_SKU_SPEEDUP*1000:.4f}μs" if r['lat10'] is not None else "—"
        marker = "  ← prev benchmark" if r['n'] == 8 else ""
        print(f"  {r['n']:>8}   {a10:>7}   {a100:>7}   {d_str:>13}   "
              f"{lat_str:>14}   {chip_str:>14}{marker}")

    print(f"\n  HDC capacity (theory):")
    print(f"    D=10K  → ~1,087 distinguishable items  (D / ln D)")
    print(f"    D=100K → ~8,695 distinguishable items")
    print(f"    {N_MAX} sign classes tested  →  well within D=10K theoretical capacity")
    print(f"{SEP}")

    # Save results
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"hdc-scalability-results-{time.strftime('%Y-%m-%d')}.txt")
    with open(out, 'w') as f:
        f.write(f"HDC Scalability  MSL-150  {time.strftime('%Y-%m-%d')}\n")
        f.write(f"Method: Path3-Retrain  1-shot  20 iters\n")
        f.write(f"Signs available: {N_MAX}\n\n")
        f.write(f"{'N':>6}  {'D=10K':>7}  {'D=100K':>7}  {'Delta':>8}  {'lat10ms':>9}\n")
        for r in rows:
            a10  = f"{r['acc10']:.1f}%"  if r['acc10']  is not None else "FAIL"
            a100 = f"{r['acc100']:.1f}%" if r['acc100'] is not None else "FAIL"
            d_str = f"{r['acc100']-r['acc10']:+.1f}pp" if r['acc10'] and r['acc100'] else "—"
            lat   = f"{r['lat10']:.3f}" if r['lat10'] else "—"
            f.write(f"{r['n']:>6}  {a10:>7}  {a100:>7}  {d_str:>8}  {lat:>9}\n")
    print(f"\nResults saved: {out}")


if __name__ == "__main__":
    main()
