# GROUNDING — t_vmm (one analog VMM read) + the paradigm-native decode framework

**Target:** time for one analog integrate + counter readout (t_vmm), and the throughput framework that rides on it.
**Why load-bearing:** decode tok/s and TTFT both scale with t_vmm; it is the binding rate of the analog chip.

---

## R1 paradigm guard (first, because this is where stale tok/s came from)
The analog weight-stationary chip is **NOT systolic**. One R×C analog VMM computes R·C MACs in one t_vmm; weights are
resident. **NEVER** use the FPGA digital-datapath `tok/s = f·P/(2N)` (that gave 204 / 4076 / P=8192) — ⚫ SUPERSEDED.

### Two DIFFERENT decode numbers (panel #3 + codex re-review — folded)
**Define D_stages = the number of sequential analog VMM stages one token traverses** = L × (matmuls/layer: Q,K,V,O +
MLP-up/down ≈ 6) × (row-tiles when contraction > 256 rows) + attention + per-layer glue. **D_stages is a few ×10²–10³
for a 1B model, NOT the layer count L** (codex catch — "D = L, one t_vmm per layer" drops per-layer multiplicity and
understates latency by ~10–100×).

`1/(D_stages·t_vmm)` is **latency-reciprocal**, valid for the single-stream case: autoregressive decode of ONE sequence
is serial (token N+1's input IS token N's output), so stages can't pipeline within one sequence; across MANY concurrent
sequences they can. **Dimensionally (codex catch on units):**
```
single-stream tok/s = 1 / (D_stages · t_vmm)                    # latency-bound. 1B, D_stages~few×10²–10³ → tens–hundreds k
aggregate   tok/s = (N_resident_tiles / D_stages) / t_vmm       # parallel-VMM-throughput ÷ stages-per-token (NOT "tiles/t_vmm", that's VMM/s)
                  ≈ 1/t_vmm   ONLY WHEN tiles ≈ D_stages (every stage replicated to its own resident tile)
power_bound tok/s = W / (N_params · energy_per_mac)             # AGGREGATE energy ceiling
```
The aggregate uplift over single-stream is **up to ×(tiles / bottleneck-stage), allocation-dependent** — only ≈×D_stages
when every stage has its own tile (codex: not automatic in D).

**Which binds (corrected — codex catch):**
- **edge / 1-user, sub-watt:** power usually WINS — 0.5 W ⇒ ~5k tok/s, *below* the single-stream latency ceiling → the
  edge case is **POWER-bound, not latency-bound** (my earlier "almost always latency-bound" was wrong). Latency binds
  only when power is ample relative to D_stages.
- **datacenter / batched:** min(aggregate-timing, power) — almost always power-bound.

Caveats: weights PRE-LOADED (inference; in-situ training adds program time — minimax); t_vmm = FULL per-stage latency
(settle + integrate + counter readout + digital glue — codex), not just the crossbar shot.

## Leg A — first principles (t_vmm decomposition)
```
T_integrate = max(charge-limited, sync-limited)   # n_clicks · Q_click/I_col  vs  n_clicks/f_clk
T_click     = n_clicks · (1/f_clk + overhead)
t_settle    = 7 · R_bl · C_bl                      # bitline RC, distributed R/2
t_vmm       = T_integrate + T_click + t_settle
```
with I_col = N_rows·I_cell, Q_click = C_int·V_ref. Noise budget: Q_noise = √(kTC ⊕ mismatch); effective_bits =
log₂(Q_signal/Q_noise); IR-drop frac error = R_bl·I_col / V_read. (Prior derivation had 4 errors — kTC floor,
comparator model, phase sequencing, 256-row extrapolation; the **corrected SPIKA-aligned model** is the one used.)
> **⚠️ codex catch (to fix in the engine):** as written, when the **sync-limited** branch wins T_integrate (= n_clicks/
> f_clk), T_click ALSO carries n_clicks·(1/f_clk) → the clocked conversion time is **double-counted**, inflating t_vmm.
> The decomposition must charge the clocked-click time ONCE. Flagged for the `05-engine.py` build + SPICE check; the
> cohort anchor (Leg B) is what gates the operating band meanwhile.

## Leg B — ≥2 MEASURED 28nm-regime anchors (primary, R2b)

| anchor | node·regime | t_vmm / rate | role |
|---|---|---|---|
| **NTHU/TSMC ISSCC'19–'24 (Xue et al.)** | **22/28nm ReRAM-CIM, counting/SA readout** | **5–18 ns/VMM** (f_VMM ~55–200 MHz) | 🟢 for the 22/28nm COHORT · 🟡 when applied to OUR 28nm |
| SPIKA 8 Kbit (node-scaled cross-check ONLY) | 180nm, 64 rows | 60 ns @64 rows (raw) | 🟡 scheme cross-check, NOT our number |

**Hypothesis (not yet grounded — codex catch):** ternary + no-ADC *may* land the fast end (~5–7 ns) because there's no
multi-bit ADC conversion in the loop — but this file shows no same-node measurement or computed derivation tying our
scheme to that sub-range, so treat it as a 🟡 expectation to test in the engine/SPICE, not a grounded value. **(Note:
SPIKA's 60 ns is at 64 rows; 64→256 rows would make integrate SLOWER, not faster — the earlier "~30–60 ns @256 rows"
was backwards and is removed. Node down-scaling 180→28nm is a separate, faster axis; the two must not be conflated.)**

## Systematic variance — falsifiable mechanism (R2c)
SPIKA 60 ns vs NTHU 5–18 ns ≈ 4–12×. **Mechanism: node (180nm→28nm, RC and device speed) + row count (64→256
raises IR-drop-limited integrate) + ADC-free counting readout.** Directional and sized → the **22nm-NTHU-lineage cohort
range 5–18 ns (node-scaled to 28nm) is the operating band**, with the fast end favored by our ADC-free ternary
readout. (Per LIT-DIGEST: free sources don't publish a 28nm per-MAC ns; "5 ns" = ISSCC'20 16Mb FP, "9.8–18.3 ns" =
ISSCC'20 2Mb; the "85 ns" was a 180nm decoy.) SPIKA's 60 ns is NOT scaled into our number (R1 mismatched-node guard).

## R2a correlation note
NTHU cohort papers share the ISSCC-CIM measurement convention; the intended independent leg is our **first-principles
RC + noise model** (Leg A). **Honesty (codex catch): this file does NOT yet instantiate Leg A with our constants — the
"lands in the same band" claim is an *assertion*, not a shown calculation.** Leg A is structural here; the computed
point comes in `05-engine.py` (plug N_rows=256, I_cell=5µA, C_int, f_clk → a number with ±). Until then the band rests
on the cohort (Leg B) alone, and **OUR exact 28nm t_vmm is 🔴 GAP (needs OUR SPICE / a domestic ReRAM fab device)**.

## Decode-framework defaults (reuse `throughput_system.py` structure)
rows 256 / cols 512; t_vmm 5/10/18 ns (ideal/realistic/cons); t_glue 5/15/30 ns per-layer; t_add 0.5/1/2 ns;
**rowtile serial↔parallel = the ~10× lever (🔴 GAP, power-gated)**; G = tensor-parallel dies.
TTFT(ctx) = ctx·weight_lat + (ctx²/(2·rows))·L·t_vmm  (O(ctx²) attention).

## Result
- **t_vmm = 5–18 ns** — 🟢 for the 22/28nm NTHU COHORT; a **borrowed-cohort placeholder for OUR chip, NOT a grounded
  OUR-28nm value** (codex catch — line 66 over-grade fixed). **OUR exact = 🔴 GAP (SPICE/a domestic ReRAM fab).** Leg-A computed point
  pending the engine.
- **f_VMM = 55–200 MHz** (work point ~100 MHz). The digital periphery clock (600–1000 MHz) is NOT the throughput rate
  (⚫ SUPERSEDED) — it runs *inside* one t_vmm.
- **single-stream (edge/1-user) = 1/(D_stages·t_vmm)** ≈ tens–hundreds k tok/s — **but at sub-watt edge the power cap
  (5k@0.5W · 30k@3W · 150k@15W, 🟡 energy/MAC 100 fJ) sits BELOW that → edge is POWER-bound** (codex catch).
- **aggregate (batched/datacenter) = (tiles/D_stages)/t_vmm** (≈1/t_vmm when tiles≈D_stages); uplift over single-stream
  = up to ×(tiles/bottleneck), allocation-dependent — almost always power-bound in practice.
- rowtile serial↔parallel = the ~10× knob (🔴 GAP) — affects the per-stage t_vmm, hence both numbers.

## Fleet verdict (panel #3 run rs-1782356947 3/3 + codex re-review run rs-1782361641)
Panel #3 caught `1/(D·t_vmm)` = latency-not-aggregate. **codex re-review then caught the harder errors:** (a) D must
be total sequential VMM-STAGES (~10²–10³), not layer count L; (b) "tiles/t_vmm" is VMM/s not tok/s — needs ÷stages;
(c) the ×D aggregate uplift is allocation-dependent not automatic; (d) edge single-stream is POWER-bound, not latency-
bound; (e) Leg-A double-counts the clocked click when sync-limited; (f) the 64→256-row "30–60 ns" was backwards;
(g) 5–18 ns over-graded GROUNDED for our chip (it's a borrowed cohort); (h) "first-principles agrees" asserted without
the calc. All folded above. Framework `decode = min(timing, power)` shape upheld; the *numbers/units* were the broken part.
