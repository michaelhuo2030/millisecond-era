# 00 — STATE OF THE MODEL (归档收敛, 2026-06-27)

> **Public archive note, 2026-07-07:** this 2026-06 folder remains the physics / derivation snapshot. The current public
> product boundary is **C1**: 0.1B / 0.3B / 1B / bounded 3B, speed-first buyer metrics, and provisionable resident
> model slots. Start from [`../C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md`](../C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md) for
> current public positioning.

> One-page convergence of every verified finding. **`04-LEDGER.md` stays the single number-source** — this doc does NOT
> duplicate numbers, it indexes the HEADLINE conclusions, their evidence-legs, the open GAPs, and where each lives.
> Grades: 🟢 GROUNDED · 🟡 MODELED · 🔴 GAP · ⚫ SUPERSEDED. Discipline: a conclusion stands only on multiple legs
> (first-principles + literature + simulation + fleet panel); the bidirectional gate guards BOTH over- and under-claiming.

## THE THESIS (what the chip is)
A **ternary ReRAM-CIM** chip: weights are **resident physical conductances**; the matrix-vector multiply happens by
**analog physics** (Ohm + Kirchhoff, the whole matrix in one settle), read out **ADC-free** by a per-2-column
differential up/down counter. **Moat = resident low-latency inference in a power envelope GPUs cannot occupy** (a GPU
can't run at µW; a digital NPU can neither hold the model resident nor do in-memory compute). **Density is the GATE**
(must fit 0.1B in a manufacturable die); **speed/latency is the first buyer axis, then power/local/privacy decide
deployment fit**. The FPGA is an **execution-credibility demo** (proves the ternary model runs/ is correct on real
hardware) — **NOT** the product (it's digital: it streams weights through P MACs, it has none of the
analog in-memory speed/energy).

## HEADLINE CONCLUSIONS (by topic; → detail doc)

### Density — the GATE (`08-ARCHITECTURE-VARIANTS`, ledger §2)
- CIM-core operating density **1.0–1.6 measured / 1.5–2.5 realistic-product / ~3–3.5 hard ceiling Mb/mm²** 🟡 (panel 4/4).
  Macro is **readout-limited, not cell-limited** (the per-2-col readout is pitch-matched, doesn't amortize with width).
- Credible edge target: **0.1B @ ~90–110 mm² (28nm) / ~60–85 mm² (22nm)** 🟡. **50 mm² for 0.1B is DEAD.** 0.3B+ = multi-die.
- Node: **22nm = realistic frontier, 14nm = stretch**; ≤10nm geometrically reachable but **eReRAM-access-gated**, not geometry.
- **Single-ended ÷2 REJECTED** (no read margin). **3D not needed** for the realistic in-plane targets.
- **Two-chip = VERTICAL 3D hybrid-bond** (readout tier stacked → compute die ~94% array), NOT lateral (analog can't ship
  laterally; lateral moves only digital control, CIM-frac→0.90). Gated by hybrid-bond access/cost/yield.

### Throughput & response cycle, 0.1B–3B (`09-THROUGHPUT-CYCLE`, engine L7, panel 4/4)
- **Single-stream decode = 1/(D·t_vmm)** (latency-bound, the autoregressive wall — pipelining can't help one user);
  **aggregate/multi-user = ~tiles/t_vmm** (×D higher; our resident-layers enable this, an FPGA can't). **operating = min(timing, power).**
- **Edge decode @3W:** 0.1B ~300k · 1B ~30k · 3B ~10k tok/s (= W/(N·E_MAC), power-bound). **All ≫ human-read 10–50**; public comparisons should still lead with same-task speed/latency, because that is what buyers can feel and measure.
- **Edge heartbeat @3W:** 0.1B short-QA ~900 Hz · 1B mid-chat ~23 Hz · 3B ~8 Hz. **Edge sweet spot 0.1B–1B**; 3B is power-starved at the edge.
- ⚠️ **energy/tok = N·E_MAC is the weight-MAC FLOOR** (codex): +attn/softmax/LN/control ⇒ real edge **~1.3–2× lower** → edge numbers are a SOFT ceiling.
- **FPGA vs chip:** FPGA tok/s ∝ 1/N (streams weights through P MACs, bigger model = much slower); chip ∝ 1/D (whole matrix per settle, **layer width is free**). Different machines (`f·P/2N` vs `1/(D·t_vmm)`).

### t_vmm / readout / counter (`11-COUNTER-STUDY`, ledger §3/§5)
- **t_vmm = 5–18 ns — now on 5 convergent legs** (28nm SAR cohort · NeuroSim ~4ns analog read · counter 2-step ~5–20ns · analytical RC · RK4 ODE). **The 60–190 ns naive-ramp scare is DEAD.**
- **Analog-settle floor ~0.24–5.75 ns** (sparse N=1 = slow corner), **robust to 2nd-order** (IR-drop / nonlinear-IV / comparator metastability — extended RK4). t_vmm 5–18 ns holds.
- **Counter is NOT the hard bottleneck** (4-leg, corrected DOWN from the periphery study's pessimism): naive ∝N is a SCHEME; **2-step single-slope keeps our differential counter, ~5–20 ns**; the **analog settle is the real floor**; ternary 1-phase input → no bit-serial ×B.
- **Where the periphery binds us** (corrected DOWN from my hand-wave): (1) counter/readout, (2) **attention dataflow @long-ctx** (my "weights-resident→light interconnect" was BACKWARDS for transformers). NOT: pointwise nonlinearity math (parallel), the array. **"ADC-free removes the periphery" = label-swap** (counters/comp/DPC remain; the movable counter is only **10.3% area / 3.5% power**, NOT 58.5%).

### Energy / power (`03-GROUNDING/energy-tops-w`, ledger §4)
- Core/macro **TOPS/W ~12–15**; system **~6–11 (~2–4× H100**, ADC-free keeps the penalty < standard 3–5×). NeuroSim 22nm ReRAM cross-check ~29–33 (with ADC; ours ADC-free should beat). **ADC dominates energy (68%) in conventional → validates the ADC-free moat.**
- Power density **12.5–17.5 W/cm²** (~5–12× colder than GPU/HBM).

### Model quality (ledger §7)
- **Ternary ≈ fp16** (8.80 vs 9.50 ppl, measured 🟢).
- **§7 CLOSED on a REAL trained LM:** BitCPM-0.5B perplexity **+<1% @ 2–5% ReRAM read-noise**, graceful to 20% (sanity-verified live). Ternary differential is robust to read noise.

## EVIDENCE-LEG SCOREBOARD (what's multiply-verified)
| finding | legs |
|---|---|
| t_vmm 5–18 ns | 🟢 5 legs (cohort+NeuroSim+counter-study+RC+RK4) |
| density ceiling 1.5–2.5/3.5 | 🟡 fleet 4/4 + measured anchors (SPIKA/HYDAR) |
| throughput single-stream/aggregate + power-bound | 🟡 fleet 4/4 + first-principles |
| counter not-the-bottleneck | 🟡 4-leg (first-principles+sim+lit+panel) |
| ternary noise-robust | 🟢 real BitCPM-0.5B ppl + CrossSim sims |
| TOPS/W core 12–15 / system 6–11 | 🟡 panel + NeuroSim cross-check |

## 🔴 OPEN GAPs — the make-or-break (ranked; verify cheap before any big spend)
1. **Real ternary-differential macro density** — does it hit 2–2.5? → a domestic ReRAM fab / discrete part / open-node fab. **THE make-or-break number.**
2. **Low-Icc cell vs HfOx forming reliability** — the ~12 µA that makes the cell small may be below reliable forming current.
3. **OUR t_vmm 2nd-order on silicon** — the floor is modeled (RC+RK4); real device-I-V/IR-drop/metastability need ngspice-with-models or silicon.
4. **Hybrid-bond access/cost/yield** for a small CN fabless — gates the vertical-3D readout-disaggregation escape.
5. **Per-block power split + core→system factor** — the TOPS/W lever budget + the honest system number.
6. **Full-WikiText perplexity + programming-error** — to fully nail §7 beyond the 209-token / read-noise-only result.
7. **THE STRATEGIC question** — is "0.1B resident at µW in ~100 mm²" a leapfrog advantage with a buyer who'd mobilize capital, people, and supply chain, or a marginal product at that size? Pressure-test the economic pull, not just the physics.

## DISCIPLINE LESSONS (this campaign — the bidirectional gate working)
- The gate caught me drifting **optimistic** (density ÷1.3 ceiling) AND **pessimistic** (counter ∝N binds-hard, "ADC-free frees us from periphery", node-scaling too-flat, periphery 90%-binds-us). Multiple legs + we's push pulled each back.
- **Cross-check research-agent numbers against our OWN corrected work before folding** (the "58.5% periphery" re-trod a panel-corrected misread).
- **Suspect the tool on physically-impossible results** (CrossSim `IdealDevice` 0.0000 false-positive; the gate caught it).
- **Don't thrash a dead tool** (ahkab version-incompat with modern numpy/scipy) → pivot to a robust weapon (direct RK4 ODE).

## DOC MAP (where everything lives)
`01-RULES` · `02-PARAMETERS` · `03-GROUNDING/` (per-number derivations) · **`04-LEDGER` = THE number-source** ·
`05-engine.py` (parametric model: density L4/L6 + throughput L7) · `08-ARCHITECTURE-VARIANTS` (density/levers/node/two-chip) ·
`09-THROUGHPUT-CYCLE` (0.1B–3B speed+heartbeat) · `10-PERIPHERY-BINDING-STUDY` (where periphery binds, 4-leg) ·
`11-COUNTER-STUDY` (the counter, 4-leg + SPICE floor) · `(the CIM-simulators arsenal) ` (NeuroSim/CrossSim arsenal +
macOS fixes + RK4/transient weapons). 

## NET (one line)
**Physics validated as far as a model + open-source tools can take it (density-gate, µW-axis, t_vmm-5-legs, counter-solvable,
ternary-noise-robust-on-a-real-LM); the remaining gates are SILICON-only (real macro density, forming reliability, on-chip
t_vmm) and STRATEGIC (the buyer/economic pull). The chip story is real and de-risked on paper — the next dollar goes to a
real macro density measurement (a domestic ReRAM fab / discrete / open-node), not more modeling.**
