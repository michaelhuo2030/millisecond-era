# Elephant #3 (FPGA) — MEASURED ternary-MAC bounds on EBAZ4205 (xc7z010)

**Date:** 2026-06-05 · **Flow:** Vivado 2023.2 (real, aux-mac QEMU VM), part `xc7z010clg400-1`.
**Goal:** turn the digital-speed *estimate* (1B ≈ 1,000–4,000 tok/s @600 MHz, 8k–32k lanes)
into *measured* hardware bounds for the two software-knowable variables —
**max parallelism P that fits the fabric**, and **Fmax** — by synthesizing a real
SPIKA-style ternary-MAC array. The third variable (sustained batch=1 utilization)
needs the physical board flashed; it is left OWED, not faked.

> This is an **EBAZ-fabric bound** = a conservative *floor*. The xc7z010 is a tiny
> 17.6k-LUT FPGA at ~225–266 MHz (speed grade −1). A real 28nm ASIC has far more
> area (→ much larger P) and a higher clock (~600 MHz–1 GHz). Read these numbers as
> "the smallest credible anchor," NOT the product number.

---

## What was synthesized

`rtl/ternary_mac_array.v` — P-lane **multiplier-free** ternary MAC:
each lane does conditional add/sub/skip of a signed 8-bit activation by a
{−1,0,+1} weight (encoded `{nz,sign}`), feeding a **balanced, fully-pipelined
adder tree** (1 registered stage per level, depth = log2 P). Registered I/O.
Parameterized in P and activation width. **0 DSPs by construction** — confirmed.

Correctness: `sim/ternary_mac_tb.v` via iverilog 13.0 on main mac →
**1991 checks, 0 errors** (pipelined dot == behavioral reference, P=64).

Methodology per P: (A) **OOC synth** of the bare array → pure datapath LUT/FF
budget ("does it fit"); (B) **synth + place + route** of a self-contained
top wrapper (LFSR-fed, single-bit signature out) with a tight clock → routed
**Fmax** from WNS. Two-part so the resource number is clean and the Fmax is the
real register-to-register datapath number (critical path verified to land inside
the MAC adder tree).

---

## (a) Max P that fits + LUT/FF table  (xc7z010 = 17,600 LUTs / 35,200 FFs / 80 DSPs)

OOC array (pure datapath, conservative upper bound):

| P     | LUTs   | LUT %   | FFs    | FF %   | DSPs | Fits? |
|-------|--------|---------|--------|--------|------|-------|
| 64    | 1,457  | 8.3 %   | 1,528  | 4.3 %  | 0    | YES   |
| 256   | 6,383  | 36.3 %  | 6,648  | 18.9 % | 0    | YES   |
| 512   | 13,294 | 75.5 %  | 13,816 | 39.3 % | 0    | **YES (max)** |
| 1024  | 27,629 | 157.0 % | 28,664 | 81.4 % | 0    | **NO**|
| 4096  | 118,763| 674.8 % | 122,872| 349.1 %| 0    | **NO**|

Scaling: ~22.8 LUTs/lane (P=64) rising to ~29 LUTs/lane (P=4096); **0 DSPs at every P**
(the ternary "multiply" never infers a multiplier — the whole thesis, confirmed in silicon-mapping).

Routed top-wrapper (after opt+place LUT-combining, what actually places):
P=64 → 1,278 LUTs (7.3%); P=256 → 4,734 LUTs (26.9%); **P=512 → 9,944 LUTs
(56.5%), routed+timing-closed**; P=1024 → 20,239 LUTs (115%, **rejected**).

**P=1024 is rejected by Vivado's hard DRC** (not an estimate):
`[DRC UTLZ-1] Slice LUTs over-utilized: requires 20239, only 17600 available`
and `CARRY4 requires 5115, only 4400 available`. The adder-tree carry chains
(CARRY4) are the tightest single constraint.

**=> Max P that fits the EBAZ fabric = 512** (75.5% LUTs, closes timing;
1024 hard-fails at 157%). The true LUT-limited ceiling is ~640 lanes (17600/27.5),
but 512 is the clean max power-of-two that places and routes.

## (b) Fmax (routed, timing-closed)

| P    | Fmax (MHz) | probe period | WNS    | crit path |
|------|------------|--------------|--------|-----------|
| 64   | **266**    | 4.0 ns       | +0.242 | into MAC lvl0 reg |
| 256  | **226**    | 5.0 ns       | +0.567 | lfsr → MAC lvl0 reg |
| 512 (max) | **194**| 6.0 ns       | +0.852 | into MAC datapath reg |

Fmax falls as the tree deepens (more pipeline levels, more routing) — expected.
~200–270 MHz is the xc7z010 −1 fabric ceiling for this datapath; the estimate's
assumed 600 MHz is an ASIC number, not reachable on this FPGA.

**Critical-path detail (load-bearing for the ASIC caveat):** at P=64 the worst
path is only **1 logic level (a single LUT)** but **84% routing delay** — the
datapath logic is trivially shallow (good pipelining); the clock is limited by
*wire delay on the small FPGA*, not by the ternary arithmetic. An ASIC (far
shorter interconnect + custom adders) would close this routing gap, which is
precisely why the ASIC clock assumption (600 MHz–1 GHz) is reasonable while the
FPGA tops out near 225–266 MHz.

## (c) Implied tok/s = Fmax × P × util / (2 × N_params)   [EBAZ floor]

Formula is the bit-verified Method-2 cycle law. At the **max-fitting P on EBAZ**:

| Config (P, Fmax)            | 1B @util.25 | 1B @util.4 | 4B @util.25 | 4B @util.4 |
|-----------------------------|-------------|------------|-------------|------------|
| P=256, 226 MHz (fits)       | ~7.2        | ~11.6      | ~1.8        | ~2.9       |
| **P=512, 194 MHz (MAX fit)**| **~12.4**   | **~19.9**  | **~3.1**    | **~5.0**   |

**=> EBAZ4205 measured floor: 1B ≈ 12–20 tok/s, 4B ≈ 3–5 tok/s** at the max-fitting
P=512, 194 MHz. (Compare human read speed ~5–10 tok/s — even this tiny FPGA's
floor is at/above reading pace for 1B.)

**ASIC-vs-FPGA caveat (load-bearing):** these single-/low-double-digit tok/s are
the EBAZ *floor*, set by the FPGA's 17.6k-LUT ceiling (P=512 max) and ~194 MHz.
The product estimate of 1,000–4,000 tok/s assumes a 28nm ASIC with **~16–64×
more lanes** (P=8k–32k vs 512 here) and **~3–5× higher clock** (600 MHz–1 GHz vs
194). Multiply the EBAZ floor by those two factors (16–64× × 3–5× ≈ 50–320×) and
1B's ~12–20 tok/s lands at **~600–6,400 tok/s** — straddling the estimate's
1,000–4,000 range. So the FPGA measurement is *consistent* with the estimate
once the area/clock gap is accounted for, and it pins down the previously-
unmeasured "how big can P actually be per unit of fabric" slope:

**Measured slope (OOC): 1457/6383/13294/27629/118763 LUTs at P=64/256/512/1024/4096
≈ 22.8 → 26 → 27 LUTs per ternary lane; 0 DSPs at every P.** Routed is lower
(~18.5 LUTs/lane via LUT-combining). This is the real "lane cost" the three
estimate-methods all flagged as their #1 unknown ("片上能塞多少 lane P"). On
28nm a ternary lane is a few dozen gates; on this FPGA a lane = ~23–27 6-LUTs,
and it bounds **P_max ≈ LUTs_available / ~27 ≈ 650** on the xc7z010 (512 = clean
max power-of-two). The carry chains (CARRY4) are co-limiting (4400 sites).

## (d) Still OWED (honest)

- **Sustained batch=1 utilization** — needs the physical EBAZ board flashed +
  a real weight/activation feed path (on-chip BRAM/SRAM streaming, layer FSM,
  attention/norm bubbles). The synthesized array proves *peak* throughput =
  P MACs/cycle and that it places+closes timing; it does NOT prove you can FEED
  P lanes from on-chip memory at Fmax every cycle. That is the util ∈ {0.25,0.4}
  knob — assumed here, not measured. Flashing + an AXI/BRAM feed harness is the
  next step.
- **A real datapath** (not LFSR stimulus) end-to-end through one transformer
  layer on the board → the true sustained tok/s number.

## (e) Artifacts

- RTL: `rtl/ternary_mac_array.v` (array + lane + pipelined adder tree),
  `rtl/ternary_mac_top.v` (self-contained synth/Fmax wrapper)
- Sim: `sim/ternary_mac_tb.v` (iverilog 13.0, **1991 checks / 0 errors, PASS**)
- Build: `build_sweep.tcl` (OOC + routed flow), `run_rest.sh`, `run_p512.sh`
- Reports: `reports/util_P{64,256,512,1024,4096}.rpt` (OOC fit budget),
  `reports/util_top_P{64,256,512}.rpt` (routed), `reports/timing_P{64,256,512}.rpt`,
  `reports/sweep_P{64,256,512}.log` (Fmax read-off)
- tok/s calc: `tok_s.py`  (`python3 tok_s.py 194.25 512`)
- Flow ran in the aux-mac Vivado 2023.2 QEMU VM (real synth+P&R, **NOT a fallback**).
- VM-side working copy: `~/projects/ternary-mac-array/run/` (build artifacts, not synced).
