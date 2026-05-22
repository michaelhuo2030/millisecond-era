"""
HDC Benchmark Matrix — 3 Paths × 2 Tasks × D=10K vs D=100K
===========================================================
ASR task  (7 methods): Baseline / Path1-A/B/C/D / Path2-PCA / Path3-Retrain
Sign Lang (4 methods): Baseline / Path1-A / Path1-B / Path3-Retrain

Task: DIGIT RECOGNITION — given audio of someone saying a digit, predict which digit.
Data: FSDD (Free Spoken Digit Dataset) + MSL-150 (Mexican Sign Language, auto-download)

Run: python3 hdc_benchmark_matrix.py [--fsdd /tmp/fsdd] [--msl /tmp/msl_sample.csv]
"""
import sys, os, time, argparse, urllib.request, io, warnings
import numpy as np
import librosa
from glob import glob
from scipy.interpolate import interp1d
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

MINI_SKU_SPEEDUP = 52_000   # chip vs Mac numpy

# ── Backend ──────────────────────────────────────────────────────────────────
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
    def cos(self, a, b):
        af, bf = a.astype(np.float32), b.astype(np.float32)
        return float(np.dot(af, bf) / (np.linalg.norm(af) * np.linalg.norm(bf) + 1e-9))
    def cos_batch(self, protos_f, query_f):
        """protos_f: (N,D) float32, query_f: (D,) float32 → (N,) similarities."""
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
    """Return (backend, channel_hvs, level_hvs) for given D and n_channels."""
    be = Backend(D, seed=42)
    ch = np.array([be.random_hv() for _ in range(n_channels)])
    lv = make_level_hvs(n_levels, D, seed=99)
    return be, ch, lv


# ── Audio feature extraction ──────────────────────────────────────────────────
N_FRAMES = 10

def _safe_delta(mfcc):
    T = mfcc.shape[1]
    w = min(9, T if T % 2 == 1 else T - 1)
    w = max(w, 3)
    return librosa.feature.delta(mfcc, width=w)


def load_mfcc(path, n_mfcc=13, with_delta=False):
    """Load audio → (n_mfcc or 39, N_FRAMES) normalized features."""
    y, sr = librosa.load(path, sr=None)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    if with_delta:
        d1 = _safe_delta(mfcc)          # velocity: how fast each coeff changes
        d2 = _safe_delta(d1)            # acceleration: second derivative
        feat = np.vstack([mfcc, d1, d2])
    else:
        feat = mfcc
    # Normalize per channel
    for i in range(feat.shape[0]):
        mn, mx = feat[i].min(), feat[i].max()
        feat[i] = (feat[i] - mn) / (mx - mn + 1e-6)
    # Resample to N_FRAMES
    T = feat.shape[1]
    if T != N_FRAMES:
        xs = np.linspace(0, 1, T); xn = np.linspace(0, 1, N_FRAMES)
        feat = np.array([interp1d(xs, feat[i])(xn) for i in range(feat.shape[0])])
    return feat.astype(np.float64)   # (n_mfcc or 39, N_FRAMES)


def feat_to_hv(feat, ch, lv, be):
    """(n_ch, N_FRAMES) normalized features → single HV."""
    fhvs = []
    for t in range(N_FRAMES):
        hv = encode_level(feat[:, t], ch, lv, be)
        fhvs.append(be.permute(hv, t))
    return be.bundle(fhvs)


# ── Data-adaptive level calibration (Path1-D) ────────────────────────────────
def build_calibrated_levels(train_feats, n_levels, D, seed=99):
    """
    Per-channel percentile-based level HVs.
    Instead of uniform quantization, levels align to training data distribution.
    Returns: (n_channels, n_levels+1) percentile boundaries
    """
    n_ch = train_feats[0].shape[0]
    all_vals = np.concatenate([f.reshape(n_ch, -1) for f in train_feats], axis=1)
    boundaries = []
    for ch in range(n_ch):
        vals = all_vals[ch]
        bounds = np.percentile(vals, np.linspace(0, 100, n_levels + 1))
        boundaries.append(bounds)
    return np.array(boundaries)  # (n_ch, n_levels+1)


def feat_to_hv_calibrated(feat, ch, lv, be, boundaries):
    """Like feat_to_hv but uses data-adaptive quantization.
    encode_level uses BUNDLE across channels (not bind) — must match here."""
    fhvs = []
    for t in range(N_FRAMES):
        frame = feat[:, t]
        channel_hvs = []
        for c in range(feat.shape[0]):
            lv_idx = int(np.searchsorted(boundaries[c], frame[c]) - 1)
            lv_idx = max(0, min(lv_idx, len(lv) - 1))
            channel_hvs.append(be.bind(lv[lv_idx], ch[c]))  # bind: level × role
        frame_hv = be.bundle(np.stack(channel_hvs))           # bundle: across channels
        fhvs.append(be.permute(frame_hv, t))
    return be.bundle(fhvs)


# ── Path 2: PCA embedding (sklearn) ──────────────────────────────────────────
def build_pca_encoder(train_paths, n_components=64):
    """Train PCA on mel spectrograms of training clips → sklearn PCA object."""
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    N_MEL = 128
    vecs = []
    for path in train_paths:
        y, sr = librosa.load(path, sr=None)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=N_MEL)
        mel_db = librosa.power_to_db(mel + 1e-6)
        # Mean + std per mel bin → 256-dim vector
        vec = np.concatenate([mel_db.mean(axis=1), mel_db.std(axis=1)])
        vecs.append(vec)
    X = np.stack(vecs)
    scaler = StandardScaler().fit(X)
    X_scaled = scaler.transform(X)
    n_comp = min(n_components, X_scaled.shape[0] - 1, X_scaled.shape[1])
    pca = PCA(n_components=n_comp, random_state=42).fit(X_scaled)
    return pca, scaler


def audio_to_hv_pca(path, pca, scaler):
    """Audio → PCA embedding → binary HV."""
    N_MEL = 128
    y, sr = librosa.load(path, sr=None)
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=N_MEL)
    mel_db = librosa.power_to_db(mel + 1e-6)
    vec = np.concatenate([mel_db.mean(axis=1), mel_db.std(axis=1)]).reshape(1, -1)
    emb = pca.transform(scaler.transform(vec)).squeeze()
    return np.where(emb > 0, 1, -1).astype(np.int8)


# ── Path 3: Iterative HDC Perceptron ─────────────────────────────────────────
def hdc_perceptron(train_hvs, train_labels, be, n_iters=20):
    """
    HDC perceptron: update prototypes by rewarding correct, penalizing wrong.
    Uses integer accumulators (not binarized until query).
    This is the closest HDC equivalent to the perceptron learning rule.
    """
    classes = sorted(set(train_labels))
    accum = {c: np.zeros(be.d, dtype=np.int32) for c in classes}

    # Initialize with all training samples
    for hv, lbl in zip(train_hvs, train_labels):
        accum[lbl] += hv.astype(np.int32)

    def get_protos():
        return {c: np.where(a >= 0, 1, -1).astype(np.int8) for c, a in accum.items()}

    for iteration in range(n_iters):
        protos = get_protos()
        n_correct = 0
        for hv, lbl in zip(train_hvs, train_labels):
            hv_f = hv.astype(np.float32)
            sims = {c: float(protos[c].astype(np.float32) @ hv_f) for c in classes}
            pred = max(sims, key=sims.get)
            if pred == lbl:
                n_correct += 1
            else:
                accum[lbl] += hv.astype(np.int32)   # reward correct class
                accum[pred] -= hv.astype(np.int32)   # penalize wrong class
        if n_correct == len(train_hvs):
            break  # converged

    return get_protos()


# ── Accuracy measurement ──────────────────────────────────────────────────────
def measure_accuracy(protos, test_hvs, test_labels, be):
    """Given prototype dict, measure accuracy on test set. Returns (acc, ms_per_query)."""
    classes = sorted(protos.keys())
    proto_mat = np.stack([protos[c].astype(np.float32) for c in classes])
    correct = 0
    t_start = time.perf_counter()
    for hv, lbl in zip(test_hvs, test_labels):
        hv_f = hv.astype(np.float32)
        sims = be.cos_batch(proto_mat, hv_f)
        pred = classes[int(np.argmax(sims))]
        if pred == lbl:
            correct += 1
    elapsed = (time.perf_counter() - t_start) * 1000
    acc = correct / max(len(test_hvs), 1) * 100
    ms = elapsed / max(len(test_hvs), 1)
    return acc, ms


# ═══════════════════════════════════════════════════════════════════════════════
# ASR BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════════
def run_asr_benchmark(fsdd_dir):
    results = []
    files = sorted(glob(os.path.join(fsdd_dir, "*.wav")))
    if not files:
        print(f"  [SKIP] No WAV files at {fsdd_dir}")
        return results

    # Parse filenames
    clips = {}
    for f in files:
        name = os.path.basename(f).replace('.wav', '')
        parts = name.split('_')
        if len(parts) >= 3:
            clips[(parts[0], parts[1], parts[2])] = f

    speakers = sorted(set(k[1] for k in clips))
    digits   = sorted(set(k[0] for k in clips))

    # Split: train = trial 0,1,2 (3 speakers × 3 trials each per digit)
    #        test  = trial 3,4
    train_keys = {k for k in clips if k[2] in ('0', '1', '2')}
    test_keys  = {k for k in clips if k[2] in ('3', '4')}

    # Enroll train: one prototype per digit (bundle all speakers)
    def build_digit_protos(encoder_fn, trials=('0',)):
        protos = {}
        for d in digits:
            hvs = []
            for sp in speakers:
                for trial in trials:
                    k = (d, sp, trial)
                    if k in clips:
                        hvs.append(encoder_fn(clips[k]))
            if hvs:
                be_tmp = Backend(len(hvs[0]), seed=99)
                protos[d] = be_tmp.bundle(np.stack(hvs)) if len(hvs) > 1 else hvs[0]
        return protos

    def get_test_set(encoder_fn):
        hvs, labels = [], []
        for k in test_keys:
            if k in clips:
                hvs.append(encoder_fn(clips[k]))
                labels.append(k[0])
        return hvs, labels

    def run_method(name, D, feat_desc, encoder_fn, extra_desc="", train_trials=('0',), path3=False):
        print(f"  Running {name}...", flush=True)
        t0 = time.perf_counter()
        be = Backend(D, seed=42)
        try:
            protos = build_digit_protos(encoder_fn, trials=train_trials)
            test_hvs, test_labels = get_test_set(encoder_fn)
            if path3:
                train_hvs, train_labels = [], []
                for k in train_keys:
                    if k in clips and k[2] in train_trials:
                        train_hvs.append(encoder_fn(clips[k]))
                        train_labels.append(k[0])
                protos = hdc_perceptron(train_hvs, train_labels, be, n_iters=15)
            acc, ms_q = measure_accuracy(protos, test_hvs, test_labels, be)
            total_ms = (time.perf_counter() - t0) * 1000
            chip_ms  = ms_q / MINI_SKU_SPEEDUP
            results.append({
                'name': name, 'D': D, 'features': feat_desc, 'extra': extra_desc,
                'accuracy': acc, 'latency_ms': ms_q, 'chip_ms': chip_ms,
                'n_test': len(test_hvs), 'total_ms': total_ms
            })
            print(f"    acc={acc:.1f}%  lat={ms_q:.3f}ms  ({total_ms:.0f}ms total)")
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({'name': name, 'D': D, 'features': feat_desc,
                            'accuracy': None, 'latency_ms': None, 'chip_ms': None})
        return results

    # ── Baseline: D=10K, MFCC-13, trial-0 enrollment ─────────────────────
    be0, ch0, lv0 = make_hv_space(10_000, 13)
    enc0 = lambda p: feat_to_hv(load_mfcc(p, 13), ch0, lv0, be0)
    run_method("Baseline", 10_000, "MFCC-13", enc0, "trial-0 enroll")

    # ── Path1-A: D=100K, MFCC-13 ─────────────────────────────────────────
    be1a, ch1a, lv1a = make_hv_space(100_000, 13)
    enc1a = lambda p: feat_to_hv(load_mfcc(p, 13), ch1a, lv1a, be1a)
    run_method("Path1-A", 100_000, "MFCC-13", enc1a, "D×10 upgrade")

    # ── Path1-B: D=100K, MFCC-39 (delta + delta-delta) ───────────────────
    be1b, ch1b, lv1b = make_hv_space(100_000, 39)
    enc1b = lambda p: feat_to_hv(load_mfcc(p, 13, with_delta=True), ch1b, lv1b, be1b)
    run_method("Path1-B", 100_000, "MFCC-39 (Δ+ΔΔ)", enc1b, "+Δ (short-clip noisy)")

    # ── Path1-C: D=100K, MFCC-39, ALL trials enrolled ────────────────────
    run_method("Path1-C", 100_000, "MFCC-39 (Δ+ΔΔ)", enc1b,
               "+3× enrollment", train_trials=('0', '1', '2'))

    # ── Path1-D: D=100K, MFCC-39, data-adaptive levels ───────────────────
    print("  Running Path1-D (calibrating levels from training data)...", flush=True)
    t0 = time.perf_counter()
    try:
        train_paths = [clips[k] for k in train_keys if k in clips and k[2] == '0']
        train_feats = [load_mfcc(p, 13, with_delta=True) for p in train_paths]
        bounds = build_calibrated_levels(train_feats, 100, 100_000)
        be1d, ch1d, lv1d = make_hv_space(100_000, 39)
        enc1d = lambda p: feat_to_hv_calibrated(load_mfcc(p, 13, with_delta=True),
                                                  ch1d, lv1d, be1d, bounds)
        protos1d = build_digit_protos(enc1d, trials=('0', '1', '2'))
        test_hvs, test_labels = get_test_set(enc1d)
        acc1d, ms1d = measure_accuracy(protos1d, test_hvs, test_labels, be1d)
        total1d = (time.perf_counter() - t0) * 1000
        results.append({'name': 'Path1-D', 'D': 100_000,
                        'features': 'MFCC-39 (Δ+ΔΔ)', 'extra': '+calibrated quant',
                        'accuracy': acc1d, 'latency_ms': ms1d,
                        'chip_ms': ms1d / MINI_SKU_SPEEDUP,
                        'n_test': len(test_hvs), 'total_ms': total1d})
        print(f"    acc={acc1d:.1f}%  lat={ms1d:.3f}ms  ({total1d:.0f}ms total)")
    except Exception as e:
        print(f"    ERROR: {e}")

    # ── Path2: PCA embedding (Mel spectrogram → sklearn PCA → binary HV) ──
    print("  Running Path2-PCA (building Mel+PCA encoder)...", flush=True)
    t0 = time.perf_counter()
    try:
        train_paths_all = [clips[k] for k in train_keys if k in clips]
        pca, scaler = build_pca_encoder(train_paths_all, n_components=64)
        n_comp = pca.n_components_
        enc2 = lambda p: audio_to_hv_pca(p, pca, scaler)
        be2 = Backend(n_comp, seed=42)

        protos2 = {}
        for d in digits:
            hvs = [enc2(clips[k]) for k in train_keys
                   if k in clips and k[0] == d and k[2] == '0']
            if hvs:
                protos2[d] = be2.bundle(np.stack(hvs)) if len(hvs) > 1 else hvs[0]
        test_hvs2 = [enc2(clips[k]) for k in test_keys if k in clips]
        test_labels2 = [k[0] for k in test_keys if k in clips]
        acc2, ms2 = measure_accuracy(protos2, test_hvs2, test_labels2, be2)
        total2 = (time.perf_counter() - t0) * 1000
        var_explained = pca.explained_variance_ratio_.sum() * 100
        results.append({'name': 'Path2-PCA', 'D': n_comp,
                        'features': f'Mel→PCA-{n_comp}', 'extra': f'{var_explained:.0f}% var',
                        'accuracy': acc2, 'latency_ms': ms2,
                        'chip_ms': ms2 / MINI_SKU_SPEEDUP,
                        'n_test': len(test_hvs2), 'total_ms': total2})
        print(f"    acc={acc2:.1f}%  D={n_comp}  ({var_explained:.0f}% variance)  ({total2:.0f}ms total)")
    except Exception as e:
        print(f"    ERROR: {e}")

    # ── Path3: Iterative HDC Perceptron (D=10K, MFCC-13) ──────────────────
    print("  Running Path3-Retrain (iterative perceptron)...", flush=True)
    t0 = time.perf_counter()
    try:
        all_train_hvs  = [enc0(clips[k]) for k in train_keys if k in clips]
        all_train_lbls = [k[0] for k in train_keys if k in clips]
        test_hvs0, test_labels0 = get_test_set(enc0)
        protos3 = hdc_perceptron(all_train_hvs, all_train_lbls, be0, n_iters=20)
        acc3, ms3 = measure_accuracy(protos3, test_hvs0, test_labels0, be0)
        total3 = (time.perf_counter() - t0) * 1000
        results.append({'name': 'Path3-Retrain', 'D': 10_000,
                        'features': 'MFCC-13', 'extra': '+perceptron 20 iter',
                        'accuracy': acc3, 'latency_ms': ms3,
                        'chip_ms': ms3 / MINI_SKU_SPEEDUP,
                        'n_test': len(test_hvs0), 'total_ms': total3})
        print(f"    acc={acc3:.1f}%  lat={ms3:.3f}ms  ({total3:.0f}ms total)")
    except Exception as e:
        print(f"    ERROR: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# SIGN LANGUAGE BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════════
MSL_ZENODO_URL = ("https://zenodo.org/records/17783312/files/"
                  "MSL-150_Mexican_Sign_Language_Dataset.csv")
MSL_FILE_SIZE = 13_285_820_704  # 13.29 GB confirmed
# Sample 8 evenly-spaced ranges across the 13GB file → should hit ~8 different signs
MSL_RANGES = [
    (0,                   3_000_000),    # sign ~A (hospital area)
    (100_000_000,       103_000_000),    # sign ~B (si area, proven working)
    (500_000_000,       503_000_000),    # sign ~D-E
    (1_200_000_000,   1_203_000_000),    # sign ~G-H
    (2_500_000_000,   2_503_000_000),    # sign ~J-K
    (5_000_000_000,   5_003_000_000),    # sign ~M-N
    (8_000_000_000,   8_003_000_000),    # sign ~P-R
    (11_000_000_000, 11_003_000_000),    # sign ~S-T
]

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


def normalize_keypoints(xyz_63):
    pts = xyz_63.reshape(21, 3)
    if np.any(np.isnan(pts)):
        pts = np.nan_to_num(pts, nan=0.0)
    wrist = pts[0].copy()
    centered = pts - wrist
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)


def load_msl_range(byte_start, byte_end, header_cols=None):
    """Download one byte range from MSL-150 CSV. Returns DataFrame or None."""
    import pandas as pd
    req = urllib.request.Request(
        MSL_ZENODO_URL,
        headers={"Range": f"bytes={byte_start}-{byte_end}", "User-Agent": "HDC-research"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"    Download error: {e}")
        return None
    lines = raw.split('\n')
    # If first range, has header; otherwise use provided header
    if byte_start == 0:
        try:
            df = pd.read_csv(io.StringIO(raw), on_bad_lines='skip')
            return df
        except Exception:
            return None
    else:
        if header_cols is None:
            return None
        # Prepend header, skip partial first row (might be cut)
        complete_lines = [l for l in lines[1:] if l.count(',') >= len(header_cols) - 1]
        if not complete_lines:
            return None
        csv_str = ','.join(header_cols) + '\n' + '\n'.join(complete_lines)
        try:
            df = pd.read_csv(io.StringIO(csv_str), on_bad_lines='skip')
            return df
        except Exception:
            return None


def download_msl_data(cache_path):
    """Download MSL-150 samples covering ~10-15 sign classes. Returns DataFrame."""
    import pandas as pd
    print("  Downloading MSL-150 sample ranges from Zenodo...", flush=True)
    dfs = []
    header_cols = None

    for i, (start, end) in enumerate(MSL_RANGES):
        print(f"  Range {i+1}/{len(MSL_RANGES)}: bytes {start//1_000_000}M-{end//1_000_000}M...",
              flush=True, end=' ')
        df = load_msl_range(start, end, header_cols)
        if df is not None and len(df) > 0:
            if header_cols is None:
                header_cols = list(df.columns)
            signs = df['CLASSIFICATION'].unique() if 'CLASSIFICATION' in df.columns else []
            print(f"got {len(df)} rows, signs: {list(signs)[:3]}")
            dfs.append(df)
        else:
            print("failed/empty")

    if not dfs:
        return None
    combined = pd.concat(dfs, ignore_index=True)
    combined.to_csv(cache_path, index=False)
    print(f"  Saved combined CSV: {cache_path}")
    return combined


def encode_sign_sequence(df_video, ch, lv, be, n_frames=10):
    """One video DataFrame → HV."""
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
    fhvs = [be.permute(encode_level(sampled[t], ch, lv, be), t)
            for t in range(n_frames)]
    return be.bundle(fhvs)


def run_sign_benchmark(msl_path):
    import pandas as pd
    results = []

    # Load or download data
    if os.path.exists(msl_path):
        print(f"  Loading cached MSL-150: {msl_path}", flush=True)
        df = pd.read_csv(msl_path, on_bad_lines='skip')
    else:
        df = download_msl_data(msl_path)
        if df is None:
            print("  [SKIP] MSL-150 download failed — check internet connection")
            return results

    if 'CLASSIFICATION' not in df.columns:
        print("  [SKIP] CSV missing CLASSIFICATION column")
        return results

    signs = sorted(df['CLASSIFICATION'].dropna().unique())
    # Keep only signs with >= 4 videos (need train + test)
    sign_counts = df.groupby('CLASSIFICATION')['VIDEO_SAMPLE'].nunique()
    signs = [s for s in signs if sign_counts.get(s, 0) >= 4]
    print(f"  Signs with ≥4 videos: {signs}")
    if len(signs) < 2:
        print("  [SKIP] Need at least 2 sign classes")
        return results

    # Build sequences per sign
    all_seqs = {}
    for sign in signs:
        df_sign = df[df['CLASSIFICATION'] == sign]
        vids = sorted(df_sign['VIDEO_SAMPLE'].unique())
        seqs = {}
        for vid in vids:
            df_vid = df_sign[df_sign['VIDEO_SAMPLE'] == vid]
            # Check keypoints available
            if not all(c in df_vid.columns for c in HAND_LANDMARK_COLS[:3]):
                continue
            seqs[vid] = df_vid
        all_seqs[sign] = seqs

    signs = [s for s in signs if len(all_seqs.get(s, {})) >= 4]
    if len(signs) < 2:
        print("  [SKIP] Not enough valid sequences after filtering")
        return results

    def run_sign_method(name, D, desc, encoder_fn, multi_shot=False, path3=False):
        print(f"  Running {name}...", flush=True)
        t0 = time.perf_counter()
        be_loc = Backend(D, seed=42)
        try:
            protos = {}
            test_hvs, test_labels = [], []
            train_hvs_all, train_labels_all = [], []

            for sign in signs:
                seqs = all_seqs[sign]
                vid_list = list(seqs.keys())
                # Train: first 1 (or all but last 2) videos
                n_train = len(vid_list) - 2 if multi_shot else 1
                n_train = max(1, n_train)
                train_vids = vid_list[:n_train]
                test_vids  = vid_list[n_train:]

                # Encode train
                hvs = [encoder_fn(seqs[v]) for v in train_vids]
                hvs = [h for h in hvs if h is not None]
                if not hvs:
                    continue
                protos[sign] = be_loc.bundle(np.stack(hvs)) if len(hvs) > 1 else hvs[0]
                for h in hvs:
                    train_hvs_all.append(h); train_labels_all.append(sign)

                # Encode test
                for v in test_vids:
                    h = encoder_fn(seqs[v])
                    if h is not None:
                        test_hvs.append(h); test_labels.append(sign)

            if path3 and train_hvs_all:
                protos = hdc_perceptron(train_hvs_all, train_labels_all, be_loc, n_iters=15)

            if not test_hvs:
                print("    No test samples"); return
            acc, ms_q = measure_accuracy(protos, test_hvs, test_labels, be_loc)
            total_ms = (time.perf_counter() - t0) * 1000
            results.append({'name': name, 'D': D, 'features': desc,
                            'accuracy': acc, 'latency_ms': ms_q,
                            'chip_ms': ms_q / MINI_SKU_SPEEDUP,
                            'n_test': len(test_hvs), 'n_signs': len(signs),
                            'total_ms': total_ms})
            print(f"    acc={acc:.1f}%  n_test={len(test_hvs)}  lat={ms_q:.3f}ms")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()

    # Baseline: D=10K, 1-shot
    be_s, ch_s, lv_s = make_hv_space(10_000, 63)
    enc_s = lambda df_v: encode_sign_sequence(df_v, ch_s, lv_s, be_s)
    run_sign_method("Baseline", 10_000, "MediaPipe 21-kpt", enc_s)

    # Path1-A: D=100K, 1-shot
    be_l, ch_l, lv_l = make_hv_space(100_000, 63)
    enc_l = lambda df_v: encode_sign_sequence(df_v, ch_l, lv_l, be_l)
    run_sign_method("Path1-A", 100_000, "MediaPipe 21-kpt", enc_l)

    # Path1-B: D=100K, multi-shot (all available videos enrolled)
    run_sign_method("Path1-B", 100_000, "MediaPipe 21-kpt", enc_l, multi_shot=True)

    # Path3: Iterative retrain, D=10K
    run_sign_method("Path3-Retrain", 10_000, "MediaPipe 21-kpt", enc_s, path3=True)

    return results


# ── Final table printer ───────────────────────────────────────────────────────
def print_table(title, results, extra_col=False):
    SEP = "═" * 80
    print(f"\n{SEP}")
    print(f"  {title}")
    print(f"{SEP}")
    if not results:
        print("  No results."); return

    header = f"  {'Method':<16} {'D':>7}  {'Features':<20} {'Accuracy':>9}  {'Mac lat':>8}  {'Chip lat':>10}  Notes"
    print(header)
    print("  " + "─" * 76)

    for r in results:
        if r.get('accuracy') is None:
            print(f"  {r['name']:<16}  ERROR")
            continue
        acc_bar = "▓" * int(r['accuracy'] / 5)
        chip = f"{r['chip_ms']*1000:.4f}μs" if r['chip_ms'] is not None else "—"
        print(f"  {r['name']:<16} {r['D']:>7,}  {r['features']:<20} "
              f"{r['accuracy']:>8.1f}%  {r['latency_ms']:>7.3f}ms  {chip:>10}  {r.get('extra','')}")

    best_acc = max((r['accuracy'] for r in results if r.get('accuracy')), default=0)
    base_acc = next((r['accuracy'] for r in results if r.get('accuracy') and 'Baseline' in r['name']), None)
    print(f"\n  Best accuracy: {best_acc:.1f}%", end="")
    if base_acc:
        gain = best_acc - base_acc
        print(f"  (+{gain:.1f}pp over baseline)", end="")
    print(f"\n{SEP}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fsdd', default='/tmp/fsdd')
    parser.add_argument('--msl',  default='/tmp/msl_benchmark_sample.csv')
    parser.add_argument('--skip-msl', action='store_true')
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  HDC BENCHMARK MATRIX  —  3 Paths × 2 Tasks × D=10K vs D=100K          ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print(f"Date: 2026-05-22  |  Mini SKU speedup: {MINI_SKU_SPEEDUP:,}×  |  Mac numpy baseline\n")

    print("▶ ASR BENCHMARK (FSDD: digit recognition, 5 classes, 3 speakers)")
    asr_results = run_asr_benchmark(args.fsdd)
    print_table("ASR — Digit Recognition (FSDD)", asr_results)

    if not args.skip_msl:
        print("\n▶ SIGN LANGUAGE BENCHMARK (MSL-150)")
        sign_results = run_sign_benchmark(args.msl)
        print_table("Sign Language — MSL-150 (Mexican Sign Language)", sign_results)

    # Save results
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "hdc-benchmark-matrix-2026-05-22.txt")
    with open(out, 'w') as f:
        f.write("HDC Benchmark Matrix — 2026-05-22\n\n")
        f.write("ASR Results:\n")
        for r in asr_results:
            if r.get('accuracy'):
                f.write(f"  {r['name']:<16} D={r['D']:>7,}  acc={r['accuracy']:.1f}%  "
                        f"lat={r['latency_ms']:.3f}ms\n")
    print(f"\nResults saved: {out}")


if __name__ == '__main__':
    main()
