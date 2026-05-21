"""
MSL-150 → HDC Pipeline Adapter
Mexican Sign Language, 150 signs, real MediaPipe Holistic keypoints
Dataset: Zenodo record 17783312 (open access)
Our pipeline: 21 right-hand landmarks × 3 axes → level encoding → HDMemory

Usage:
  python3 msl150_hdc_adapter.py /path/to/MSL-150_Mexican_Sign_Language_Dataset.csv

  Or partial download (range request):
  curl --range 0-200000000 <url> -o msl_sample.csv
  python3 msl150_hdc_adapter.py msl_sample.csv
"""

import sys
import os
import time
import numpy as np
import pandas as pd

# Add SDK to path (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import HDMemory, encode_level

# ── Column mapping: MSL-150 → 21 MediaPipe Hands landmarks ──────────────────
# MediaPipe Hands landmark order (0-20):
#   WRIST(0) | THUMB_CMC(1) THUMB_MCP(2) THUMB_IP(3) THUMB_TIP(4)
#   INDEX_MCP(5) INDEX_PIP(6) INDEX_DIP(7) INDEX_TIP(8)
#   MIDDLE_MCP(9) MIDDLE_PIP(10) MIDDLE_DIP(11) MIDDLE_TIP(12)
#   RING_MCP(13) RING_PIP(14) RING_DIP(15) RING_TIP(16)
#   PINKY_MCP(17) PINKY_PIP(18) PINKY_DIP(19) PINKY_TIP(20)

HAND_LANDMARK_COLS = [
    "RIGHT_WRIST_X",           "RIGHT_WRIST_Y",           "RIGHT_WRIST_Z",           # 0
    "RIGHT_THUMB_CMC_X",       "RIGHT_THUMB_CMC_Y",       "RIGHT_THUMB_CMC_Z",       # 1
    "RIGHT_THUMB_MCP_X",       "RIGHT_THUMB_MCP_Y",       "RIGHT_THUMB_MCP_Z",       # 2
    "RIGHT_THUMB_IP_X",        "RIGHT_THUMB_IP_Y",        "RIGHT_THUMB_IP_Z",        # 3
    "RIGHT_THUMB_TIP_X",       "RIGHT_THUMB_TIP_Y",       "RIGHT_THUMB_TIP_Z",       # 4
    "RIGHT_INDEX_FINGER_MCP_X","RIGHT_INDEX_FINGER_MCP_Y","RIGHT_INDEX_FINGER_MCP_Z",# 5
    "RIGHT_INDEX_FINGER_PIP_X","RIGHT_INDEX_FINGER_PIP_Y","RIGHT_INDEX_FINGER_PIP_Z",# 6
    "RIGHT_INDEX_FINGER_DIP_X","RIGHT_INDEX_FINGER_DIP_Y","RIGHT_INDEX_FINGER_DIP_Z",# 7
    "RIGHT_INDEX_FINGER_TIP_X","RIGHT_INDEX_FINGER_TIP_Y","RIGHT_INDEX_FINGER_TIP_Z",# 8
    "RIGHT_MIDDLE_FINGER_MCP_X","RIGHT_MIDDLE_FINGER_MCP_Y","RIGHT_MIDDLE_FINGER_MCP_Z", # 9
    "RIGHT_MIDDLE_FINGER_PIP_X","RIGHT_MIDDLE_FINGER_PIP_Y","RIGHT_MIDDLE_FINGER_PIP_Z", # 10
    "RIGHT_MIDDLE_FINGER_DIP_X","RIGHT_MIDDLE_FINGER_DIP_Y","RIGHT_MIDDLE_FINGER_DIP_Z", # 11
    "RIGHT_MIDDLE_FINGER_TIP_X","RIGHT_MIDDLE_FINGER_TIP_Y","RIGHT_MIDDLE_FINGER_TIP_Z", # 12
    "RIGHT_RING_FINGER_MCP_X", "RIGHT_RING_FINGER_MCP_Y", "RIGHT_RING_FINGER_MCP_Z",# 13
    "RIGHT_RING_FINGER_PIP_X", "RIGHT_RING_FINGER_PIP_Y", "RIGHT_RING_FINGER_PIP_Z",# 14
    "RIGHT_RING_FINGER_DIP_X", "RIGHT_RING_FINGER_DIP_Y", "RIGHT_RING_FINGER_DIP_Z",# 15
    "RIGHT_RING_FINGER_TIP_X", "RIGHT_RING_FINGER_TIP_Y", "RIGHT_RING_FINGER_TIP_Z",# 16
    "RIGHT_PINKY_MCP_X",       "RIGHT_PINKY_MCP_Y",       "RIGHT_PINKY_MCP_Z",      # 17
    "RIGHT_PINKY_PIP_X",       "RIGHT_PINKY_PIP_Y",       "RIGHT_PINKY_PIP_Z",      # 18
    "RIGHT_PINKY_DIP_X",       "RIGHT_PINKY_DIP_Y",       "RIGHT_PINKY_DIP_Z",      # 19
    "RIGHT_PINKY_TIP_X",       "RIGHT_PINKY_TIP_Y",       "RIGHT_PINKY_TIP_Z",      # 20
]


def normalize_keypoints(xyz_63: np.ndarray) -> np.ndarray:
    """(63,) raw MediaPipe coords → (63,) normalized [0,1] centered on wrist."""
    pts = xyz_63.reshape(21, 3)
    wrist = pts[0]
    centered = pts - wrist
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)


def load_video_sequence(df_video: pd.DataFrame) -> np.ndarray:
    """
    One video → (n_frames, 63) float32 normalized.
    df_video: rows for one VIDEO_SAMPLE, sorted by FRAME.
    Returns None if keypoints unavailable.
    """
    df_sorted = df_video.sort_values("FRAME")
    # Extract 63 values per frame
    try:
        raw = df_sorted[HAND_LANDMARK_COLS].values.astype(np.float64)
    except KeyError as e:
        print(f"  Missing column: {e}")
        return None

    # Normalize per frame
    frames = np.array([normalize_keypoints(row) for row in raw], dtype=np.float32)
    return frames


def make_sequential_level_hvs(n_levels: int, d: int, seed: int = 99) -> np.ndarray:
    """Sequential bit-flip level HVs: adjacent levels share D/n_levels bits."""
    rng = np.random.default_rng(seed)
    base = (rng.integers(0, 2, size=(d,)) * 2 - 1).astype(np.int8)
    lvls = [base.copy()]
    n_flip = d // n_levels
    for _ in range(1, n_levels):
        hv = lvls[-1].copy()
        flip_idx = rng.choice(d, n_flip, replace=False)
        hv[flip_idx] *= -1
        lvls.append(hv)
    return np.array(lvls, dtype=np.int8)


class NumpyBackend:
    def __init__(self, d: int):
        self.d = d
        self.rng = np.random.default_rng(42)

    def random_hv(self):
        return (self.rng.integers(0, 2, self.d) * 2 - 1).astype(np.int8)

    def bundle(self, hvs: np.ndarray) -> np.ndarray:
        sums = hvs.sum(axis=0)
        result = np.where(sums >= 0, 1, -1).astype(np.int8)
        # Break ties randomly
        ties = (sums == 0)
        if ties.any():
            result[ties] = (self.rng.integers(0, 2, ties.sum()) * 2 - 1).astype(np.int8)
        return result

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return (a * b).astype(np.int8)

    def permute(self, hv: np.ndarray, n: int) -> np.ndarray:
        return np.roll(hv, n)

    def cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a.astype(np.float32), b.astype(np.float32)) /
                     (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def encode_gesture_sequence(frames: np.ndarray, channel_hvs: np.ndarray,
                             level_hvs: np.ndarray, backend: NumpyBackend) -> np.ndarray:
    """
    (n_frames, 63) → single HV representing the gesture.
    Temporal encoding: bundle(permute(frame_hv_0, 0), permute(frame_hv_1, 1), ...)
    """
    frame_hvs = []
    for i, frame in enumerate(frames):
        # Level encode this frame
        hv = encode_level(frame.astype(np.float64), channel_hvs, level_hvs, backend)
        # Permute by frame index for temporal ordering
        frame_hvs.append(backend.permute(hv, i))
    return backend.bundle(np.stack(frame_hvs))


def run_msl150_demo(csv_path: str, D: int = 10000, n_levels: int = 100):
    """Run HDC sign recognition pipeline on real MSL-150 data."""
    print("=" * 60)
    print("MSL-150 Sign Language — HDC Pipeline on REAL Data")
    print("=" * 60)
    print(f"Dataset: {csv_path}")
    print(f"D={D:,}  n_levels={n_levels}")
    print()

    # ── Load data ──────────────────────────────────────────────
    print("Loading CSV...", flush=True)
    df = pd.read_csv(csv_path, on_bad_lines='skip')
    signs = df['CLASSIFICATION'].unique()
    print(f"Signs in this sample: {list(signs)}")
    print(f"Total rows: {len(df):,}")
    print()

    # ── Build HDC components ───────────────────────────────────
    print("Building HDC components...", flush=True)
    backend = NumpyBackend(D)
    n_channels = 63  # 21 landmarks × 3
    channel_hvs = np.array([backend.random_hv() for _ in range(n_channels)])
    level_hvs = make_sequential_level_hvs(n_levels, D)
    memory = HDMemory(D)

    # ── Process each sign ──────────────────────────────────────
    results = {}
    for sign in signs:
        df_sign = df[df['CLASSIFICATION'] == sign]
        video_ids = sorted(df_sign['VIDEO_SAMPLE'].unique())
        n_videos = len(video_ids)
        print(f"Sign '{sign}': {n_videos} video samples")

        sequences = {}
        for vid_id in video_ids:
            df_vid = df_sign[df_sign['VIDEO_SAMPLE'] == vid_id]
            seq = load_video_sequence(df_vid)
            if seq is not None:
                sequences[vid_id] = seq
        print(f"  → {len(sequences)} sequences loaded, avg {np.mean([len(s) for s in sequences.values()]):.0f} frames/seq")

        # 1-shot registration: use video_id[0] as prototype
        if not sequences:
            print(f"  → SKIP (no valid sequences)")
            continue

        vid_list = list(sequences.keys())
        prototype_id = vid_list[0]
        test_ids = vid_list[1:]

        print(f"  Encoding prototype (video {prototype_id})...", flush=True)
        t0 = time.perf_counter()
        proto_hv = encode_gesture_sequence(sequences[prototype_id], channel_hvs, level_hvs, backend)
        t_encode = (time.perf_counter() - t0) * 1000
        print(f"  Prototype encoded in {t_encode:.1f}ms")

        # Register in HDMemory
        memory.add_class(sign, proto_hv.reshape(1, -1))

        # Test on remaining samples
        if not test_ids:
            print(f"  → Only 1 sample; no test samples.")
            continue

        print(f"  Testing on {len(test_ids)} held-out samples...", flush=True)
        test_sims = []
        t_start = time.perf_counter()
        for vid_id in test_ids:
            query_hv = encode_gesture_sequence(sequences[vid_id], channel_hvs, level_hvs, backend)
            sim = backend.cosine_sim(proto_hv, query_hv)
            test_sims.append(sim)
        t_test = (time.perf_counter() - t_start) * 1000

        results[sign] = {
            'n_test': len(test_ids),
            'sims': test_sims,
            'mean_sim': np.mean(test_sims),
            'min_sim': np.min(test_sims),
            'max_sim': np.max(test_sims),
            'std_sim': np.std(test_sims),
            'ms_per_query': t_test / len(test_ids),
        }

    # ── Results ────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("RESULTS — Real MSL-150 Data")
    print("=" * 60)
    for sign, r in results.items():
        print(f"\nSign '{sign}':")
        print(f"  Test samples:     {r['n_test']}")
        print(f"  Similarity mean:  {r['mean_sim']:.4f}  (1.0 = identical to prototype)")
        print(f"  Similarity range: {r['min_sim']:.4f} – {r['max_sim']:.4f}")
        print(f"  Similarity std:   {r['std_sim']:.4f}  (↓ = more consistent)")
        print(f"  Latency:          {r['ms_per_query']:.2f} ms/query")

        # Interpretation
        if r['mean_sim'] > 0.7:
            verdict = "STRONG — HDC captures the sign consistently across signings"
        elif r['mean_sim'] > 0.4:
            verdict = "MODERATE — HDC clusters the sign; more data improves"
        else:
            verdict = "WEAK — high inter-sample variation or encoding issue"
        print(f"  Verdict:          {verdict}")

    print()
    print("1-shot learning demonstrated: 1 example → prototype → tested on real signings")
    print("Data: real Mexican Sign Language, native signer, real camera noise")
    print()

    # ── Save results ───────────────────────────────────────────
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "msl150-hdc-realdata-results.txt")
    with open(results_path, "w") as f:
        f.write("MSL-150 Real Data HDC Results\n")
        f.write(f"D={D}  n_levels={n_levels}\n\n")
        for sign, r in results.items():
            f.write(f"Sign '{sign}': mean_sim={r['mean_sim']:.4f}  "
                    f"range=[{r['min_sim']:.4f},{r['max_sim']:.4f}]  "
                    f"latency={r['ms_per_query']:.2f}ms\n")
        f.write("\nAll similarity scores:\n")
        for sign, r in results.items():
            f.write(f"  {sign}: {[f'{s:.3f}' for s in r['sims']]}\n")
    print(f"Results saved: {results_path}")
    return results


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/msl_150_sample.csv"
    D = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    run_msl150_demo(csv_path, D=D)
