# 04 — LEDGER (the SINGLE SOURCE OF TRUTH for the ReRAM-CIM chip)

> Every number the engine/calculator may use, grounded in `03-GROUNDING/`, each a graded RANGE (or an explicit 🔴 GAP).
> **If a number is not here — or contradicts here — it is NOT confirmed.** Everything scattered elsewhere is
> historical; re-derive disagreements against THIS. Supersedes `01-chip-core/GROUNDED-NUMBERS-LEDGER.md`.
>
> **Grades:** 🟢 GROUNDED (primary measured/cited) · 🟡 MODELED (first-principles, not measured on our chip) ·
> 🔴 GAP (silicon-only unknown → a domestic ReRAM fab/tapeout/SPICE) · ⚫ SUPERSEDED (never use). Most "operating" numbers are 🟡/🔴.
> Do not promote a 🟡 ceiling to a 🟢 operating number (optimistic drift) or collapse a measured range to its low
> anchor (harsh) — R0 bidirectional. **Panel status (all folded):** rules ✅(#1, 3/4) · density ✅(#2, 1/3 thin —
> re-run) · throughput ✅(#3, 3/3) **+ 0.1B–3B sweep ✅(rs-1782386678, 4/4 → `09-THROUGHPUT-CYCLE.md`)** · power ✅(#4, 3/3) · readout ✅(#5, 2/3). **Big catches:** density HYDAR=macro-not-die;
> throughput 1/(D·t_vmm)=single-stream-not-aggregate; **power 12–15=core-not-system (→~2–4× H100, was 5–10×)**;
> counter signed-range→8-bit-full/7-bit-floor. kimi over-quota all cycle (refold next).

---

## 1. CELL PHYSICS — HfOx now (foundation) · → `material-HfOx.md` / `material-TaOx.md`
| number | value | grade | source |
|---|---|---|---|
| R_LRS / R_HRS / on-off | 40 kΩ / 3 MΩ / **75×** | 🟢 design-anchor | HfOx 1T1R typical |
| V_read | 0.2 V | 🟢 | LRS ohmic, ≤V_set/5 |
| I_LRS / I_HRS | 5.0 / 0.067 µA | 🟢 calc | V_read/R |
| per-weight differential signal | **4.93 µA** | 🟢 calc | I_LRS−I_HRS |
| forming | 3–4 V, OFF-chip once | 🟢 design | tester, no on-chip pump |
| I_SET (compliance) | 50–200 µA | 🟡/🔴 | sets selector-FET width → cell area |
| endurance | 10⁶–10⁸ (HfOx) · **>10¹² (TaOx)** | 🟢 LIT | write-once ⇒ low bar; rules KV out of ReRAM |
| cell = 2-cell binary differential | 2 cells / ternary weight | 🟢 design | common-mode cancel (mandatory, not optional) |

## 2. DENSITY cascade — levels distinct; ②→③ variance EXPLAINED, not collapsed · → `density-cell-area.md` / `density-cim-core.md`
| level | value @28nm | grade | source / note |
|---|---|---|---|
| ① bare 1T1R cell (STORAGE ceiling) | 6.2–11.4 Mb/mm² (k 112–205 F²; cell 0.088–0.16 µm²) | 🟡 MODELED | Leg-A selector-floor + 🟢 anchors (14nm 0.022µm², 22FFL, PKU 40nm). STORAGE, not compute |
| ② array (×array-eff 0.60–0.70) | 3.7–8.0 Mb/mm² | 🟡 MODELED | clean step (SPIKA §3 method) |
| **③ OPERATING CIM-core (MACRO/core level)** | measured **1.0 – 1.6**; realistic product **1.5 – 2.5**; HARD ceiling **~3–3.5 Mb/mm²** | 🟡 CONTESTED | HIGH-anchor = HYDAR 1.63 (C/待论文/recommendation-HMC/MACRO). **Panel rs-1782377887 (codex+kimi+minimax+glm 4/4) REFUTED the old "upside 2–4" + the ÷1.3 ceiling (see ③′): the per-2-col counter+comparator+DPC readout is PITCH-MATCHED / row-proportional and does NOT amortize with column width** → at 256 rows it's ≈13.7× the array (glm). Macro is **readout-limited, not cell-limited**. A 28nm macro beating 3nm SRAM-DCIM (3.78) is implausible. Realistic product 1.5–2.5 (amortizes above HYDAR but capped); hard ceiling ~3–3.5. Where-in-band = 🔴 GAP (real macro / a domestic ReRAM fab). See `08-ARCHITECTURE-VARIANTS.md` |
| **④ effective ternary weights** | measured **0.5–0.8**; product **0.75–1.25 M wt/mm²** | 🟡 MODELED-range | ③ ÷2 differential |
| ③′ ⚫ SUPERSEDED ÷1.3 "ceiling" (was 2–6) | — | ⚫ REFUTED | panel 4/4: readout pitch-matched, does NOT amortize → real ceiling ~3–3.5 not 6–7.1; never cite the old 2–6 upside as operating |
| per GOOD die (CIM-frac, area) | measured **~27–56 M** @200mm²·0.55–0.70 · product **~68–112 M** @100mm²·0.90 (disaggregated) | 🟡 | ④ × area × CIM-frac (**codex: NO yield here — yield cuts #good dies/wafer, NOT params/working die**). Disaggregation (control off-die, CIM-frac→0.90) + smaller die = the two REAL levers (08-VARIANTS) |
| **credible EDGE target (the make-or-break line)** | **0.1B @ ~90–110 mm² (28nm) / ~60–85 mm² (22nm)** | 🟡 | needs product core ~2–2.5 + CIM-frac→0.90. **50 mm² for 0.1B is DEAD** (needs core 4.4–6.2 > ceiling). 0.3B ≈ 300 mm² (not edge). Single-ended ÷2 rescue REJECTED (no read margin). 3D NOT needed. See `08-ARCHITECTURE-VARIANTS.md` |
| 1B model (dense, datacenter) | **~9–15 dies** × 100 mm² | 🟡 | = 1000M / per-good-die @product density. Package assembly yield (per-die^N) SEPARATE: 0.985^9≈87%. **1B is a multi-die datacenter part, NOT the edge play** — the edge leapfrog is the 0.1B single-die above |
| 28→22nm uplift | **~1.3×** (≈1.25–1.35; NOT 1.5× nor ideal 1.62×) | 🟡 | = area₂₈/area₂₂(floor); selector-floor inflates k 112–205→140–250, eating most of (28/22)²; per-node efficiency scaling UNPROVEN |
| **real-silicon @28nm (cell pitch / I_SET / periphery factor)** | — | 🔴 **#1 GAP** | decides where in ③ 0.5–1.6 we land. **Close via OUR OWN measurement** (discrete ReRAM bench-test → open-node fab sky130/IHP → a domestic university/institute collaborator → CHEAP-SILICON-PATH $300→¥50K→¥50万) **OR a domestic ReRAM fab** — not relying on them alone (they have their own blind spots; build our own to JUDGE theirs) |

## 3. THROUGHPUT — TWO devices, never conflate · → `t_vmm.md`
**(A) the ANALOG ReRAM-CIM CHIP (the product / moat) — paradigm-native, weight-stationary:**
| number | value | grade | source |
|---|---|---|---|
| FRAMEWORK | **decode = min(timing-ceiling, power-bound)**, BUT timing has TWO regimes (panel #3): **single-stream (batch-1, edge) = 1/(D·t_vmm)** latency-bound · **aggregate (B≥D concurrent) → ~tiles/t_vmm** (×D higher). power-bound = aggregate ceiling. NOT systolic. 响应周期 = TTFT + n_gen/decode | 🟢 | panel #3 (3/3): 1/(D·t_vmm) is latency-reciprocal not aggregate throughput |
| t_vmm | **5–18 ns** (22nm NTHU lineage + ISSCC'20 2Mb, node-scaled to 28nm); OUR exact 🔴 GAP (SPICE). **NeuroSim FC256 microbench (22nm RRAM): pure analog read ~4 ns ✓ in-band; digital periphery 91% of latency → raw timing-ceiling −3–5× (`09`)**. **Counter study (`11`, 4-leg): counter NOT the bottleneck (2-step/window readout ~5–20 ns); BL transient settle floor ~0.3–6 ns (sparse=slow corner) → t_vmm 5–18 ns VALIDATED, the 60–190 ns naive-ramp scare is dead.** | 🟢 cohort + 🟡 first-principles + 🟡 NeuroSim + 🟡 transient | per LIT-DIGEST, free sources don't publish 28nm per-MAC ns → anchor = 22nm NTHU; "5 ns" = ISSCC'20 16Mb FP, "9.8–18.3 ns" = ISSCC'20 2Mb (the "85 ns" was a 180nm decoy) |
| f_VMM | 55–200 MHz (work ~100 MHz) | 🟢 cohort | the binding rate (NOT the 600–1000 MHz periphery clock) |
| rows / cols per VMM | 256 / 512 (cols ~free) | 🟢 measured/design | CIM-E; IR-drop wall at rows |
| 1B single-stream timing (edge/1-user) | tens–hundreds k tok/s (= 1/(D_stages·t_vmm), D_stages = total seq. VMM stages ~10²–10³, NOT layer count) | 🟡 MODELED | **but edge sub-watt is POWER-bound, not latency-bound** (power cap below this); rowtile knob = ~10× GAP |
| 1B aggregate timing-ceiling (batched) | (tiles/D_stages)/t_vmm (≈1/t_vmm when tiles≈D_stages) | 🟡 MODELED | "tiles/t_vmm" alone = VMM/s not tok/s; uplift allocation-dependent |
| **1B power-bound (binds the aggregate / honest operating #)** | **~5k @0.5W · ~30k @3W · ~150k @15W** | 🟡 MODELED | energy/MAC 100 fJ; AGGREGATE energy ceiling |
| **0.1B–3B edge DECODE @3W** (single user) | **0.1B ~300k · 0.3B ~100k · 0.5B ~60k · 1B ~30k · 1.5B ~20k · 3B ~10k tok/s** | 🟡 MODELED | engine L7 (`09-THROUGHPUT-CYCLE.md`), panel rs-1782386678 4/4. = W/(N·E_MAC), power-bound. **flip→timing only above W\*=ceiling×E/tok: 0.1B ~6W … 1B ~45W … 3B ~74W** (glm). **Edge = SOFT ceiling: N·E_MAC is the weight-MAC floor; +attn/softmax/LN/control ⇒ ~1.3–2× lower (codex, §4 overhead).** All ≫ human-read 10–50 tok/s |
| **0.1B–3B 响应周期 / heartbeat @3W** | **0.1B short-QA ~900 Hz · 1B mid-chat ~23 Hz · 3B mid-chat ~8 Hz / long-scan ~2 Hz** | 🟡 MODELED | cycle = TTFT(ctx/rate + attn O(ctx²)) + n_gen/rate. **Edge sweet spot 0.1B–1B; 3B is power-starved at the edge** (wants a box). Box/timing-ceiling Hz = 5–20× higher (the old "56–2000 Hz" = BOX, not edge). prefill power-bound TTFT correct; ceiling-TTFT conservative (crossbar pipelines, glm). minimax "prefill=N·E not ctx·N" REJECTED (3-engine majority: prefill = ctx×per-token) |
| rowtile readout-parallelism | the #1 ~10× knob | 🔴 GAP | RTL+layout, power-gated |

**(B) the FPGA digital-datapath DEMO (execution-credibility, NOT the product) — systolic:**
| number | value | grade | source |
|---|---|---|---|
| FPGA decode | ~1–4k tok/s @1B short-ctx | 🟢 GROUNDED-for-FPGA | `tok/s=f·P/(2N)` valid HERE only; EBAZ P=512@194–266MHz |
| ⚫ SUPERSEDED | quoting FPGA `f·P/(2N)` (**204** / 4076 / P=8192) as the analog CHIP | — | category error (R1 paradigm) |

## 4. POWER / ENERGY / EFFICIENCY · → `energy-tops-w.md`
| number | value | grade | source |
|---|---|---|---|
| energy / MAC | ~100 fJ nominal (core+no-ADC readout; lever 44–100 fJ via V², 1/R) | 🟡 MODELED | E=f(V_periph², R_LRS), PERIPH_SHARE 0.83 |
| **CORE/macro TOPS/W** | **~12–15** | 🟡 MODELED | Path-C anchored (NOT system — panel #4) |
| **SYSTEM-level TOPS/W** | **~6–11 (≈2–4× H100)** | 🟡/🔴 GAP | core × ~1.3–2.5 residual overhead (control/SFU/KV-SRAM/IO/inter-die; <3–5× std because ADC-free). Exact factor = end-to-end GAP |
| Path A (per-MAC, macro-only) = **CEILING** | 25–133 TOPS/W | 🟡 | first-principles per-VMM energy (upper bound, NOT a floor — codex) |
| Path B (FPGA × ASIC gain) = floor | 2.4–4.9 TOPS/W | 🟢 anchored | FPGA 0.35 measured × 7–14× (the 7–14× gain itself is assumed, not measured) |
| Path C (published 28nm, MACRO-level) | 11.9–15 TOPS/W | 🟢 LIT | NTHU ISSCC'21 — a MACRO number (codex: do NOT call it "system-honest") |
| package power → W/cm² → ΔT | **25–35 W ⇒ 12.5–17.5 W/cm²** (codex: NOT 7–10); ΔT 8–14 K | 🟡 POC | 1-D R-stack; real power = 🔴 GAP |
| edge form | 0.3–1 W glasses / 2–3 W phone | 🟡 | DVFS throttle |
| we're colder than GPU/HBM | 12.5–17.5 vs 80–150 W/cm² = **~5–12×** | 🟡 | GPU 🟢 measured / OUR side 🟡 POC (NOT "both measured") |
| per-block periphery POWER split | comparator vs DPC vs counter | 🔴 GAP | needs primary Table-5 + SPICE |
| ⚫ SUPERSEDED | 28–195 TOPS/W (analog PEAK) as system | — | use **12–15 CORE / 6–11 SYSTEM** (codex: prior "use 12–15 system" was itself the error) |

## 5. READOUT COUNTER + LOCALITY · → `counter-bits.md` / `readout-locality.md`
| number | value | grade | source |
|---|---|---|---|
| **counter bits @256 rows** | **7-bit floor (measured-OK +0.7%) · 8-bit full signed @50% sparsity (N_active≈128) · 10-bit absolute worst case (all 256 active, range ±256=513 states)** | 🟢 floor + 🟡 ceiling | D5 ppl (7b +0.7% / 5b +4.0%); signed range = ±N_active (codex: log₂128=7 dropped the sign; worst-case 256-active → 10-bit); common-mode 17.1µA=3.5× signal ⇒ differential strongly favored |
| counter area cost 5→7-bit | +40% on counter = **~+4% core area ⇒ ~−4% core density** (codex: NOT −0.5–1%), ~0 throughput | 🟡 MODELED | counter = 10.3% of core; +40%×10.3%=+4.1% |
| readout locality (lateral 2.5D) | ~90% core area analog-local | 🟢 | SPIKA Table-5 re-derived |
| Table-5 partition (corrected) | counter ≈ 10.3% area / 3.5% power; "57% power" = input+output COMBINED | 🟢 | panel codex catch (rs-1782316312) |
| PDN ceiling | ~400–600 simultaneous macros/die | 🟡 MODELED-compact | 1B ~950 active ⇒ 78A ⇒ 156mV IR/SSN — the 950→400–600 mapping/IR budget is not fully shown (codex), treat as soft |
| 3D hybrid-bond escape | compute die **~94% array** (move DPC+counter+comp = 25.9% off; codex: NOT >95%) | 🟡 feasible / 🔴 access | AMD/Fujitsu/d-Matrix real (2-die only); access/cost/yield GAP |
| ⚫ SUPERSEDED | "5-bit counter" final; "distributed counter ⇒ unconstrained size"; old DPC 12%/57% + counter 10%/26% partition | — | use ≥7-bit; bottleneck transfers (PDN/add-tree/routing) |

## 6. THERMAL / RETENTION / 3D · → `thermal-3d.md`
| number | value | grade | source |
|---|---|---|---|
| binary-diff retention margin | large (the specific "56–62×" is a 🟡 PLACEHOLDER — no Arrhenius derivation shown, codex) | 🟡 MODELED | common-mode cancel ⇒ robust vs analog MLC (direction sound; magnitude pending) |
| power density | **12.5–17.5 W/cm²** (25–35W/200mm²; codex fixed from 7–10) | 🟡 POC | 1-D, not FEM; real power = 🔴 GAP |
| colder than GPU/HBM | **~5–12×** (12.5–17.5 vs 80–150) | 🟡 | OUR side POC-modeled, not measured (codex) |
| stacking gate | per-die assembly yield, **gradual taper not a cliff** (0.985^50=**47%** not 7.9%, codex; 0.985^20=74%) | 🟡 / 🔴 per-die GAP | "8-die sweet spot" dropped — depends on unknown hybrid-bond per-die yield |
| monolithic multilayer ReRAM | doesn't exist (lab 128 Kbit) | 🟢 LIT | IEDM/a domestic ReRAM fab/Weebit/TSMC — ruled out |
| hybrid-bond 2-die | commercially real | 🟢 LIT | the v2 path |

## 7. MODEL QUALITY (foundation under capacity)
| number | value | grade | source |
|---|---|---|---|
| ternary ≈ fp16 (near-lossless) | 8.80 vs 9.50 ppl (8B WikiText) | 🟢 MEASURED | CHIP-FEASIBILITY #10, 3-shard |
| bits / param | ~1.7 bit | 🟢 MEASURED | weights ≈ params |
| ternary robustness to ReRAM read-noise | **REAL trained ternary LM (BitCPM-0.5B, 169 Linear): perplexity +(-0.1)%@2% · +0.8%@5% · +5.5%@10% · +18.8%@20%** (sanity: 50%→ppl 7.5× = noise verified live). Plus: 1-MVM sign-survival 100%@2%/99.9%@5%; 8-layer+LayerNorm cos-sim 0.998@2%/0.99@5% (CrossSim) | 🟢 MEASURED-on-real-LM + 🟡 sim | **§7 "ternary ≈ near-lossless under read-noise" now CLOSED on a real trained LM**: at realistic 2–5% read-noise ppl moves <1%, graceful to 20%. Caveat: 209-token eval (small → absolute ppl high, but the TREND is clean & matches MVM/compounding sims). Noise = NormalProportional W·(1+ε) on Linear weights (the ReRAM-mapped projections; attention QK/AV excluded — correct). Next: full WikiText eval + programming-error. `bitcpm_ppl.py` |

---

## SUPERSEDED — never reuse (⚫)
`tok/s=f·P/(2N)` / **204** / 4076 / P=8192 as the analog chip · analog PEAK 28–195 TOPS/W as system · 90 Mb/mm²
(cross-point, abandoned) · 14.8 Mb/mm² as "CIM" (it's storage 1T2R) · 3–8 Mb/mm² quoted as OPERATING · "5-bit
counter" final · 180nm SPIKA numbers as 28nm values · collapsing ③ to harsh 0.5 / truncating ④ to 0.25–0.5M ·
promoting the ÷1.3 ceiling to operating · 600–1000 MHz periphery clock as the throughput rate · old DPC/counter %
partition · **"~5–10× H100" as the SYSTEM efficiency (that was the CORE number; system ≈ 2–4×, and even that is a soft
estimate)** · **"counter exactly 7-bit from log₂(128)"** (ignored the sign → 7-bit floor / 8-bit @50%-sparse / 10-bit
worst-case) · **"1B = ~4…29 dies"** AND **"~16…80 dies"** (both wrong — the first didn't reproduce, the second baked
yield into per-die capacity; use **~9–37 dies** off 27–112M/good-die) · **"power density 7–10 W/cm²"** (25–35W/200mm² =
**12.5–17.5**) · **"~10–20× colder"** (= **~5–12×**) · **"0.985^50 = 7.9%"** (= **47%**; 7.9% needs 0.95/die) ·
**"8-die assembly-yield sweet spot / 20+ monster"** (yield tapers gradually: 0.985^20=74%) · **"counter 5→7-bit = −0.5–1%
density"** (= **~−4% core**) · **"3D compute die >95% array"** (= **~94%**) · **"retention 56–62×"** as a precise number
(underived placeholder).

## Load-bearing 🔴 GAPs (gate the operating point — keep named, never fake)
1. **a domestic ReRAM fab real 28nm cell pitch + I_SET** → where in ③ 0.5–1.6 / ④ 0.25–0.8M we land.
2. **OUR SPICE t_vmm + rowtile-parallel RTL/layout** → which decode ceiling (the ~10× knob).
3. **per-block periphery POWER split** → the TOPS/W lever budget.
4. **hybrid-bond access/cost/yield for a small CN fabless** → whether the 3D density escape is reachable.

## How to use
1. Before quoting any chip number → find it here; if ⚫/🔴/🟡, say so. If not here, it's not confirmed — derive + add.
2. `05-engine.py` + `07-calculator.html` read ONLY this ledger.
3. A scattered doc/memory disagrees → THIS wins; flag the other SUPERSEDED.
4. Update when a 🔴 GAP closes or a 🟡 is measured.
