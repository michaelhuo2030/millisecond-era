#!/usr/bin/env python3
"""
sizing.py  —  "RWKV-7 model zoo  x  ternary-CIM chip" fit estimator.

WHAT THIS IS:  an arithmetic sizing account  [ESTIMATE].  It is NOT a measurement
and NOT a chip.  No silicon exists yet — the on-chip capacity is a design [TARGET]
we sweep ({1 GB, 3 GB}).  Everything here is openly recomputable; change the
assumptions at the top and re-run.

WHY IT EXISTS:  to answer one honest question — "given a ternary compute-in-memory
chip of capacity C, which real RWKV-7 models fit on a single die, at batch=1 (edge)?"

ASSUMPTIONS (all explicit, all editable):
  V        = 65536                 RWKV-7 vocab size                       [EXTERNAL: RWKV-7]
  TERN_BPP = 1.58 bit/param        BitNet b1.58 ternary weight density     [EXTERNAL: BitNet b1.58]
           = 0.1975 byte/param     (this is the "~0.2 GB per 1B params" rule)
  transformer / attention params (TERNARIZABLE)   ~= 12 * L * C**2
  embedding + head params (NOT ternarizable)       = 2 * V * C   (untied emb & head)
        -> kept at int8 (1 byte/param).  Conservative; could go lower with care.
        Why not ternary: they are the lookup/projection to a 65536-way vocab;
        ternarizing them wrecks quality -> they are the "hidden tax" of a big vocab,
        and they are NOT covered by our measured gates, so we keep them int8.
  recurrent state S (int8, per measured Gate-3)    = (C**2 / head_size) * L bytes  @ batch=1
        -> a few MB; negligible vs weights, reported separately.

  on-chip total  =  ternary_weights  +  embhead_int8     (state is rounding error @ batch=1)

The 12*L*C**2 formula is a ~10% under-estimate of true RWKV-7 param count (it omits the
decay/a-gate LoRAs, r_k bonus, token-shift vectors) — so the implied param count printed
below runs slightly under each model's nameplate size. Storage numbers are ESTIMATE-grade.

CAVEAT printed at the end: batch=1 is the EDGE regime. High-concurrency serving multiplies
state per stream and is a different (server) account — see note.
"""

V          = 65536
TERN_BPP   = 1.58 / 8.0          # bytes per ternary param  = 0.1975
INT8_BPP   = 1.0                 # bytes per int8 param (emb/head)
HEAD_SIZE  = 64                  # RWKV-7 head_size
CHIP_TARGETS_GB = [1.0, 3.0]     # [TARGET] design points to test fit against

GB = 1e9

# (name, C, L, source-label, kind)
#   EXTERNAL  = config from RWKV-7 public releases
#   ESTIMATE  = config not independently confirmed / generic round-number design point
MODELS = [
    ("RWKV-7 0.4B",  1024, 24, "EXTERNAL", "real"),
    ("RWKV-7 1.5B",  2048, 24, "EXTERNAL", "real"),
    ("RWKV-7 2.9B",  2560, 32, "EXTERNAL", "real"),
    ("RWKV-7 7.2B",  4096, 32, "EXTERNAL", "real"),
    ("RWKV-7 13.3B", 4096, 61, "ESTIMATE", "real"),   # config not web-confirmed; L set to ~match nameplate
    ("~1B  (design point)", 2048, 15, "ESTIMATE", "generic"),
    ("~4B  (design point)", 3072, 32, "ESTIMATE", "generic"),
    ("~9B  (design point)", 4096, 42, "ESTIMATE", "generic"),
]

def account(C, L):
    transformer = 12 * L * C * C          # ternarizable
    embhead     = 2 * V * C               # not ternarizable -> int8
    implied_P   = transformer + embhead
    tern_gb     = transformer * TERN_BPP / GB
    emb_gb      = embhead     * INT8_BPP / GB
    state_bytes = (C * C // HEAD_SIZE) * L            # int8 state @ batch=1
    total_gb    = tern_gb + emb_gb
    return dict(transformer=transformer, embhead=embhead, implied_P=implied_P,
                tern_gb=tern_gb, emb_gb=emb_gb, state_mb=state_bytes/1e6, total_gb=total_gb)

def fit_str(total_gb, cap):
    return "fits" if total_gb <= cap else "no"

rows = []
for name, C, L, src, kind in MODELS:
    a = account(C, L)
    rows.append((name, C, L, src, kind, a))

# ---- human-readable ----
print("=" * 96)
print("RWKV-7 model zoo  x  ternary-CIM chip  —  single-die fit @ batch=1 (edge)   [ESTIMATE]")
print("assumptions: ternary weights 1.58bit/param; emb+head(2*V*C, V=65536) int8; chip cap = TARGET")
print("=" * 96)
hdr = f"{'model':22s} {'C':>5s} {'L':>4s} {'~params':>8s} {'tern.W':>8s} {'emb+head':>9s} {'state':>7s} {'on-chip':>8s}  {'1GB':>4s} {'3GB':>4s}  src"
print(hdr); print("-" * 96)
for name, C, L, src, kind, a in rows:
    print(f"{name:22s} {C:5d} {L:4d} {a['implied_P']/1e9:7.2f}B {a['tern_gb']:7.3f}G {a['emb_gb']:8.3f}G "
          f"{a['state_mb']:6.1f}M {a['total_gb']:7.3f}G  {fit_str(a['total_gb'],1.0):>4s} {fit_str(a['total_gb'],3.0):>4s}  [{src}]")
print("-" * 96)
print("batch=1 = EDGE single-stream (what a 1GB on-chip-weight chip is born for).")
print("High-concurrency serving (e.g. 256 streams) multiplies STATE per stream -> GB-scale -> a")
print("different (server) account; not what this edge chip targets.")
print("13.3B sits right at the 3GB line -> single-die only on the 3GB target, else a 2-die module")
print("(RWKV is layer-recursive with constant state -> splits cleanly across dies).")

# ---- markdown table (paste into README / cards) ----
print("\n\n--- MARKDOWN (model zoo fit table) ---\n")
print("| model | C | L | ~params | ternary weights | emb+head (int8) | on-chip total | 1GB [TARGET] | 3GB [TARGET] | config |")
print("|---|---|---|---|---|---|---|---|---|---|")
for name, C, L, src, kind, a in rows:
    f1 = "✅" if a['total_gb'] <= 1.0 else "❌"
    f3 = "✅" if a['total_gb'] <= 3.0 else "❌"
    print(f"| {name} | {C} | {L} | ~{a['implied_P']/1e9:.1f}B | {a['tern_gb']*1000:.0f} MB | "
          f"{a['emb_gb']*1000:.0f} MB | **{a['total_gb']:.2f} GB** | {f1} | {f3} | [{src}] |")
