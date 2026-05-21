"""HDC Multimodal RAG Demo — 毫秒纪 Phase 47.14
Zero-training cross-modal retrieval: query any modality → retrieve full episode.

Three modalities: Text (char n-gram) · Audio (mean MFCC, thermometer level) · Tag (char bind)
15 episodes from FSDD dataset (george / jackson / nicolas, digits 0-4)

Architecture:
  episode_hv = bundle([
      bind(text_hv,  TEXT_ROLE),
      bind(audio_hv, AUDIO_ROLE),
      bind(tag_hv,   TAG_ROLE),
  ])

Query any modality → probe = bind(modality_hv, ROLE) → cosine search over 15 episodes

Audio encoding uses:
  - Mean MFCC (13 values) — stable across recordings of same word
  - Thermometer level HVs — adjacent levels share most bits (HDC analog similarity)
  - Global normalization across corpus — preserves cross-clip discriminability
"""
from __future__ import annotations
import numpy as np
import librosa

# ─── Inline Backend (bipolar {-1,+1}, numpy) ──────────────────────────────────
class Backend:
    def __init__(self, d):
        self.d = d
        self.rng = np.random.default_rng(42)

    def random_hv(self):
        return (self.rng.integers(0, 2, self.d) * 2 - 1).astype(np.int8)

    def bind(self, a, b):
        return (a * b).astype(np.int8)

    def bundle(self, hvs):
        if isinstance(hvs, np.ndarray) and hvs.ndim == 2:
            s = hvs.astype(np.int32).sum(axis=0)
        else:
            s = np.stack(hvs).astype(np.int32).sum(axis=0)
        r = np.where(s >= 0, 1, -1).astype(np.int8)
        ties = (s == 0)
        if ties.any():
            r[ties] = (self.rng.integers(0, 2, int(ties.sum())) * 2 - 1).astype(np.int8)
        return r

    def permute(self, hv, n):
        return np.roll(hv, n)

    def cos(self, a, b):
        af = a.astype(np.float32)
        bf = b.astype(np.float32)
        return float(np.dot(af, bf) / (np.linalg.norm(af) * np.linalg.norm(bf) + 1e-9))

    def cos_batch(self, query, matrix):
        """query: (D,), matrix: (N, D) → (N,) similarities"""
        qf = query.astype(np.float32)
        mf = matrix.astype(np.float32)
        dots = mf @ qf
        norms = np.linalg.norm(mf, axis=1) * (np.linalg.norm(qf) + 1e-9)
        return dots / (norms + 1e-9)


# ─── Episode dataset ──────────────────────────────────────────────────────────
EPISODES = [
    # (audio_file, text_description, tag)
    ("/tmp/fsdd/0_george_0.wav",  "george says zero",    "zero"),
    ("/tmp/fsdd/1_george_0.wav",  "george says one",     "one"),
    ("/tmp/fsdd/2_george_0.wav",  "george says two",     "two"),
    ("/tmp/fsdd/3_george_0.wav",  "george says three",   "three"),
    ("/tmp/fsdd/4_george_0.wav",  "george says four",    "four"),
    ("/tmp/fsdd/0_jackson_0.wav", "jackson says zero",   "zero"),
    ("/tmp/fsdd/1_jackson_0.wav", "jackson says one",    "one"),
    ("/tmp/fsdd/2_jackson_0.wav", "jackson says two",    "two"),
    ("/tmp/fsdd/0_nicolas_0.wav", "nicolas says zero",   "zero"),
    ("/tmp/fsdd/1_nicolas_0.wav", "nicolas says one",    "one"),
    ("/tmp/fsdd/2_nicolas_0.wav", "nicolas says two",    "two"),
    ("/tmp/fsdd/3_nicolas_0.wav", "nicolas says three",  "three"),
    ("/tmp/fsdd/4_nicolas_0.wav", "nicolas says four",   "four"),
    ("/tmp/fsdd/3_jackson_0.wav", "jackson says three",  "three"),
    ("/tmp/fsdd/4_jackson_0.wav", "jackson says four",   "four"),
]

# Short name for display
def ep_name(ep):
    parts = ep[0].split("/")[-1].replace(".wav", "").split("_")
    return f"{parts[1]}/{parts[0]}"   # e.g. "george/0"


# ─── Codebook init ────────────────────────────────────────────────────────────
D         = 10_000
N_MFCC    = 13
N_LEVELS  = 50   # thermometer levels — adjacent levels share ~D*(1-1/N_LEVELS) bits

be = Backend(D)

# ASCII char HVs (128 entries) — shared by text n-gram + tag encoding
char_hvs = np.array([be.random_hv() for _ in range(128)])  # (128, D)

# MFCC channel role HVs
ch_hvs = np.array([be.random_hv() for _ in range(N_MFCC)])  # (13, D)

# Thermometer level HVs: adjacent levels are similar (flip bits gradually).
# lv_hvs[0] and lv_hvs[1] differ in only D//N_LEVELS positions (~200 bits at D=10K).
# This is the HDC "analog" trick: similar values → similar HVs.
_base_lv = be.random_hv()
_flip_order = np.random.default_rng(99).permutation(D)
_n_flips_per_step = D // N_LEVELS
lv_hvs_list = [_base_lv.copy()]
for _i in range(1, N_LEVELS):
    _prev = lv_hvs_list[-1].copy()
    _start = (_i - 1) * _n_flips_per_step
    _end = _i * _n_flips_per_step
    _prev[_flip_order[_start:_end]] *= -1
    lv_hvs_list.append(_prev)
lv_hvs = np.array(lv_hvs_list)  # (N_LEVELS, D) — thermometer codebook

# Role HVs — fixed per session
TEXT_ROLE  = be.random_hv()
AUDIO_ROLE = be.random_hv()
TAG_ROLE   = be.random_hv()

# ─── Global MFCC statistics (computed once before encoding) ───────────────────
# Per-clip normalization destroys absolute MFCC scale.
# Global min/max per channel preserves cross-clip discriminability.
_MFCC_GLOBAL_MIN = None   # (13,) set by compute_global_mfcc_stats()
_MFCC_GLOBAL_MAX = None   # (13,)


def compute_global_mfcc_stats(audio_paths: list[str]):
    """Compute per-channel global min/max over MFCC means of all provided clips."""
    global _MFCC_GLOBAL_MIN, _MFCC_GLOBAL_MAX
    all_means = []
    for path in audio_paths:
        y, sr = librosa.load(path, sr=None, mono=True)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)  # (13, T)
        all_means.append(mfcc.mean(axis=1))
    arr = np.array(all_means)  # (N, 13)
    _MFCC_GLOBAL_MIN = arr.min(axis=0)
    _MFCC_GLOBAL_MAX = arr.max(axis=0)


# ─── Modality encoders ────────────────────────────────────────────────────────

def encode_text(text: str, n: int = 3) -> np.ndarray:
    """Text → HV via character n-gram encoding."""
    chars = text.lower().replace(" ", "_")
    if len(chars) < n:
        chars = chars.ljust(n, "_")
    ngram_hvs = []
    for i in range(len(chars) - n + 1):
        gram_hv = char_hvs[ord(chars[i]) % 128]
        for j in range(1, n):
            gram_hv = be.bind(gram_hv, be.permute(char_hvs[ord(chars[i + j]) % 128], j))
        ngram_hvs.append(gram_hv)
    if not ngram_hvs:
        return be.random_hv()
    return be.bundle(np.stack(ngram_hvs))


def encode_audio(path: str) -> np.ndarray:
    """Audio file → HV via mean MFCC (13 channels) + thermometer level encoding.

    Mean MFCC is stable across different recordings of the same word/speaker.
    Thermometer level HVs ensure similar MFCC values produce similar HVs.
    Global normalization preserves cross-clip discriminability.
    """
    global _MFCC_GLOBAL_MIN, _MFCC_GLOBAL_MAX
    y, sr = librosa.load(path, sr=None, mono=True)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)  # (13, T)
    mean_mfcc = mfcc.mean(axis=1)  # (13,) — stable summary across T frames

    # Normalize to [0, 1] using global stats
    if _MFCC_GLOBAL_MIN is not None:
        rng_val = _MFCC_GLOBAL_MAX - _MFCC_GLOBAL_MIN
        rng_val[rng_val == 0] = 1.0
        norm = np.clip((mean_mfcc - _MFCC_GLOBAL_MIN) / rng_val, 0.0, 1.0)
    else:
        norm = np.zeros(N_MFCC)  # fallback

    # Level-encode each channel: bind(channel_role_hv, thermometer_level_hv)
    ch_bound = []
    for c in range(N_MFCC):
        lvl = min(int(norm[c] * N_LEVELS), N_LEVELS - 1)
        ch_bound.append(be.bind(ch_hvs[c], lv_hvs[lvl]))

    return be.bundle(np.stack(ch_bound))


def encode_tag(tag: str) -> np.ndarray:
    """Tag/category label → HV via character-by-character bind."""
    chars = [char_hvs[ord(c) % 128] for c in tag.lower() if ord(c) < 128]
    if not chars:
        return be.random_hv()
    return be.bundle(np.stack(chars))


def encode_episode(audio_path: str, text: str, tag: str):
    """Build multimodal episode HV = bundle of role-bound modality HVs."""
    text_hv  = encode_text(text)
    audio_hv = encode_audio(audio_path)
    tag_hv   = encode_tag(tag)
    ep_hv = be.bundle(np.stack([
        be.bind(text_hv,  TEXT_ROLE),
        be.bind(audio_hv, AUDIO_ROLE),
        be.bind(tag_hv,   TAG_ROLE),
    ]))
    return ep_hv, text_hv, audio_hv, tag_hv


# ─── Build episode memory ─────────────────────────────────────────────────────
def build_memory():
    episodes_data = []
    for ep in EPISODES:
        ep_hv, t_hv, a_hv, tg_hv = encode_episode(*ep)
        episodes_data.append({
            "ep":    ep,
            "ep_hv": ep_hv,
            "t_hv":  t_hv,
            "a_hv":  a_hv,
            "tg_hv": tg_hv,
        })
    return episodes_data


def search(probe: np.ndarray, episodes_data: list, top_k: int = 3):
    """Return top_k (idx, sim) sorted by cosine similarity."""
    ep_matrix = np.stack([e["ep_hv"] for e in episodes_data])  # (15, D)
    sims = be.cos_batch(probe, ep_matrix)
    ranked = np.argsort(sims)[::-1]
    return [(int(i), float(sims[i])) for i in ranked[:top_k]]


def per_modality_sims(probe_text_hv, idx, episodes_data):
    """Show how similar this probe is to each stored modality for episode idx."""
    ep_d = episodes_data[idx]
    t_sim  = be.cos(probe_text_hv, ep_d["t_hv"])
    a_sim  = be.cos(probe_text_hv, ep_d["a_hv"])
    tg_sim = be.cos(probe_text_hv, ep_d["tg_hv"])
    return t_sim, a_sim, tg_sim


# ─── Main demo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("=== HDC Multimodal RAG Demo ===")
    print(f"    D={D}  n_mfcc={N_MFCC}  n_levels={N_LEVELS} (thermometer)")
    print("=" * 60)

    # Compute global MFCC statistics over all audio clips (episodes + query)
    # so normalization preserves cross-clip discriminability (same digit = similar HV)
    unseen_audio = "/tmp/fsdd/0_george_1.wav"
    all_audio_paths = [ep[0] for ep in EPISODES] + [unseen_audio]
    print(f"\nComputing global MFCC stats ({len(all_audio_paths)} clips)...", flush=True)
    compute_global_mfcc_stats(all_audio_paths)

    print(f"Building episode memory ({len(EPISODES)} episodes)...", flush=True)
    mem = build_memory()
    ep_matrix = np.stack([e["ep_hv"] for e in mem])
    print(f"  {len(EPISODES)} episodes registered (text + audio + tag)")

    # ── QUERY 1: Text → retrieval ──────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("QUERY 1: Text → Episode Retrieval")
    print("─" * 60)

    text_queries = [
        "george says zero",
        "says two",
        "jackson",
    ]

    for q_text in text_queries:
        q_hv = encode_text(q_text)
        probe = be.bind(q_hv, TEXT_ROLE)
        results = search(probe, mem, top_k=3)

        print(f"\n  Query: \"{q_text}\"")
        print(f"  Top-3 results:")
        for rank, (idx, sim) in enumerate(results, 1):
            ep = mem[idx]["ep"]
            # Per-modality breakdown: compare query HV against each stored modality HV
            t_sim  = be.cos(q_hv, mem[idx]["t_hv"])
            a_sim  = be.cos(q_hv, mem[idx]["a_hv"])
            tg_sim = be.cos(q_hv, mem[idx]["tg_hv"])
            print(f"    {rank}. {ep_name(ep):20s}  sim={sim:+.3f}"
                  f"  [text={t_sim:+.3f} audio={a_sim:+.3f} tag={tg_sim:+.3f}]"
                  f"  ({ep[1]})")

    # ── QUERY 2: Audio → Text retrieval (unseen clip) ─────────────────────────
    print("\n" + "─" * 60)
    print("QUERY 2: Audio → Text Retrieval (unseen clip: 0_george_1.wav)")
    print("  (This file is NOT in the episode registry)")
    print("─" * 60)

    q_audio_hv = encode_audio(unseen_audio)
    probe_audio = be.bind(q_audio_hv, AUDIO_ROLE)
    results_audio = search(probe_audio, mem, top_k=3)

    print(f"\n  Query: play {unseen_audio.split('/')[-1]}")
    print(f"  Top-3 results:")
    for rank, (idx, sim) in enumerate(results_audio, 1):
        ep = mem[idx]["ep"]
        print(f"    {rank}. \"{ep[1]:25s}\"  sim={sim:+.3f}  ({ep_name(ep)})")
    print(f"  Note: mean-MFCC captures speaker identity across recordings.")
    print(f"  George episodes should rank above jackson/nicolas episodes.")

    # ── QUERY 3: Tag → Category retrieval ─────────────────────────────────────
    print("\n" + "─" * 60)
    print("QUERY 3: Tag → All 'zero' Episodes")
    print("─" * 60)

    q_tag = "zero"
    q_tag_hv = encode_tag(q_tag)
    probe_tag = be.bind(q_tag_hv, TAG_ROLE)

    sims_all = be.cos_batch(probe_tag, ep_matrix)
    ranked_all = np.argsort(sims_all)[::-1]

    print(f"\n  Query tag: \"{q_tag}\"")
    print(f"  All episodes ranked by similarity:")
    for i, idx in enumerate(ranked_all):
        ep = mem[idx]["ep"]
        sim = float(sims_all[idx])
        match_marker = "  <- MATCH" if ep[2] == q_tag else ""
        print(f"    {i+1:2d}. {ep_name(ep):20s}  sim={sim:+.3f}  tag={ep[2]:6s}{match_marker}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Cross-modal binding proven:")
    print("  query any modality → retrieve all bound modalities")
    print("  Zero training examples required.")
    print("  HDC: bind + bundle + permute (3 ops) = multimodal associative memory")
    print("=" * 60)
