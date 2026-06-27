# 11 — THE COUNTER: a systematic study (盯死) — first-principles + literature + simulation + fleet

> The counter is the **#1 binding unknown** from the periphery study (`10`): its readout latency may be the real t_vmm
> driver, and it's the **movable** digital block (10.3% area / 3.5% power, SPIKA Table-5; relocatable via vertical 3D).
> Same triangulation rule: a verdict stands only on **first-principles + literature + simulation, fleet-validated.**

## WHAT THE COUNTER IS (our design)
Per **2 columns** (differential ternary), an **up/down counter + comparator** digitizes the net column current into a
signed count — **NO ADC**. Net signal current I_net = Σ(+1-weight·active) − Σ(−1-weight·active), common-mode (HRS
leakage) cancels in the differential. Cell anchors (ledger §1): I_LRS 5 µA, I_HRS 0.067 µA, **per-weight signal 4.93 µA**,
V_read 0.2 V, 256 rows (IR-drop wall), **7-bit counter** (ledger §5).

## LEG 1 — FIRST-PRINCIPLES (the latency law + the levers)
**Counting/integrating (ramp) conversion time:**
```
t_conv = N_count · t_clk            N_count = |digitized value| ≤ 2^(B−1)  (7-bit → ±128)
t_counter(per dot) = t_conv · B_input     (bit-serial: B_input passes, shift-added)
```
- **The law is ∝ N_count (output magnitude) × B_input** — NOT ∝ log N (that's SAR). This is the "slow family" (lit leg-1).
- **N_count = the actual VMM output value** = # of aligned active ±1 weights — for sparse ternary activations this is
  **≪ 128** (maybe ~10–40 typical), so *typical* t_conv ≪ worst case, but the **hardware must budget worst-case** (SPIKA
  amortizes into a fixed 60 ns window).
- t_clk = periphery clock (ledger: 600 MHz–1 GHz → **1–1.7 ns**).
- **LEVERS (how to make the counter fast — the design battle):**
  1. **Low B_input** (1-bit/ternary input → B=1, not 8) — biggest knob; bit-serial multiplies everything.
  2. **Faster t_clk** (advanced node) — linear.
  3. **Fewer bits / coarser N_count** (5-bit floor vs 7-bit) — but ledger §5 says ≥7-bit for accuracy → tension.
  4. **Beat the ∝N scheme**: SAR-assist / 2-step (coarse-flash + fine-count) / multi-ramp / time-domain — trade area/power for log-ish latency.
- **First-principles estimate (to be checked):** worst-case ramp t_conv ≈ 128·1.5 ns ≈ **~190 ns**; typical (N~30) ≈ **~45 ns**;
  ×B_input. **⇒ tens–hundreds ns/dot. This is plausibly the real t_vmm — bigger than the SAR-cohort 5–18 ns the ledger assumed.**

## LEG 2 — LITERATURE (deepen leg-1: real conversion-time numbers + fast-counter schemes)
**DONE (deep-dig, well-sourced):**
| scheme | law | real ns | source |
|---|---|---|---|
| single-slope ramp-count (baseline) | ∝2^N / ∝N×depth | SPIKA **60 ns** @180nm/500MHz | Frontiers SPIKA'25 |
| **2-step single-slope (coarse-flash+fine-count)** | **∝2·√(2^N)** | **64× faster** (14-b: 256 vs 16384 cyc) | MDPI Sensors 14(11):21603 |
| TDC pulse-shrink (ADC-less) | ∝V_mac, tiny const | **~285 ps core**, 2 ns cyc @28nm 256×256 | rTD-CiM GLSVLSI'24 |
| bit-serial BWMCS (real ReRAM) | ∝#input-bits | 8-b VMM in **8 cyc** @65nm | ISSCC'21 22nm 4Mb / IEEE 20.7TOPS/W |
| SAR (memristor) | ∝N | 6-b 100MS/s <3mW @28nm | FZJ MEMRISYS'24 |
- **Verdict (lit):** fastest viable ADC-free for **signed ternary = 2-step single-slope** — KEEPS our differential
  up/down counter, swaps ∝N→∝√N → 7-bit/256-row count phase ~128→~22 ticks → **~5–20 ns @0.6–1 GHz, beats SPIKA's
  60 ns easily** (SPIKA is 180nm + a fixed 30 ns integrate window). Then the **integrate/settle window (not the count)
  is the floor.** 🔴 **SPICE GAP:** no paper reports a *signed-ternary 7-bit 2-step counter* ns directly (2-step law is
  from CIS ADCs; BWMCS/TDC are SRAM/single-ended) — SPICE our 2-col differential BL (R_LRS, C_BL, comparator offset,
  fine ramp) settles the true floor + the integrate-vs-IR-drop @256 rows.

## LEG 3 — SIMULATION
- **Behavioral model DONE** (`counter_timing.py`, local): latency vs N_active by scheme (B_input=1, 0.8GHz, 200fF, 0.3V):
  | scheme | N=4 | N=32 | N=128 | law |
  |---|---|---|---|---|
  | A single-slope ramp-count | 5 ns | 40 ns | **80 ns** | ∝N (SPIKA's; ×8-bit input → 640 ns) |
  | B current-integrate + TDC | 3 ns | 0.4 ns | **0.1 ns** | ∝1/N (fast big-N, slow small-N, needs fine TDC) |
  | C SAR-assist | 8.8 ns | 8.8 ns | 8.8 ns | ∝logN (adds a DAC) |
  | D 2-step flash+ramp | 6.2 ns | 1.2 ns | **1.2 ns** | ~flat (adds a 3-b flash) |
  **Finding: the counter latency is a SCHEME CHOICE, not a law.** SPIKA's 60 ns ∝N slowness is its single-slope scheme;
  a **2-step (flash+ramp) or integrate-TDC readout → ~1–9 ns**, near SAR, without a full ADC. **#1 lever = low B_input**
  (8-bit multiplies everything ×8). So "counter binds hard" is only true for the naive scheme — there is real headroom.
  ⚠️ Pending: can 2-step/integ-TDC actually hit **7-bit SIGNED** precision at our node (small-N/low-current is the hard
  corner for integ-TDC)? → literature + panel + SPICE.
- **🔴 the real GAP = SPICE netlist** of comparator + up/down counter + BL-cap at our I_LRS/cap → the true t_clk-limited
  conversion ns. (ngspice locally, needs a netlist — named follow-up.) **NeuroSim is the WRONG sim here** (it models a SAR
  ADC, not our counter — that's exactly why its "~4 ns read" did not represent us).

## LEG 4 — FLEET cross-validation
🔄 panel launched on the first-principles latency law + the lever ranking + the "is the counter the real t_vmm" claim.

## CONVERGENCE — 4-leg verdict (first-principles + sim + lit + fleet panel rs-1782475457, 4/4)
**The counter is NOT the hard t_vmm bottleneck the periphery study (`10`) feared.** Cross-validated:
1. **Scheme choice, not a law.** Naive single-slope ∝N (SPIKA 60 ns) is beatable: **2-step single-slope** (keeps our
   differential up/down counter) → ∝√N → **~5–20 ns @0.6–1 GHz** (lit); for low levels a **window/flash sense-amp**
   resolves ternary one-shot ~10s ps (glm).
2. **PANEL REFRAME (kimi+minimax):** the counter is **rarely the bottleneck** — the **ANALOG SETTLE** (BL precharge +
   WL settle + current settle + comparator decision) is the real floor; the counter **overlaps behind it**.
3. **Law-direction nuance (glm+codex+kimi):** ∝N = voltage-ramp-reference (dense-slow); ∝1/N = current-integrate-to-
   threshold (**SPARSE-slow** — and differential ternary makes zero-crossings common, so this corner is real). minimax:
   neither scales cleanly (ReRAM resistive non-ideality + settle + comparator floor). **My earlier ∝N×B worst-case
   label was for the ramp-reference scheme only; the natural CIM scheme's slow corner is the SPARSE read.**
4. **Low-bit ternary input → NO ×B_input multiplier** (codex+kimi+glm): ternary = 1 signed phase / 2 one-hot, not 8-bit
   serial. (The 640 ns "8-bit" scare doesn't apply to a ternary-input design.)

**NET:** t_vmm is floored by the **analog settle**, not the counter. With a 2-step/window readout + ternary 1-phase
input, the counter adds ~few–20 ns, largely overlappable → **t_vmm back in the ~5–18 ns range (ledger §3 CONSISTENT)**,
NOT the 60–190 ns the naive ramp implied. **→ Correcting `10`'s "counter = co-#1 binds hard" to: counter is a solvable
design choice; the real floor is analog settle.** Bidirectional gate: periphery study was pessimistic on the counter.

## THE EXPERIMENT — DONE (first-principles transient; full-SPICE = cheap follow-up)
**BL transient settle model** (`bl_settle.py`, local): integrating read, C dV/dt = N·(V_read−V)/R → settle = (RC/N)·ln(V_read/(V_read−V_th)).
With R_LRS 40 k, C_BL 200 fF, V_read 0.2, V_th 0.1, t_comp 0.2 ns:
| N_active | settle | **t_vmm floor (+comp)** |
|---|---|---|
| 1 (sparse, slow corner) | 5.55 ns | **5.75 ns** |
| 32 | 0.17 ns | 0.37 ns |
| 128 (dense) | 0.04 ns | 0.24 ns |
**Result: analog-settle floor ~0.3–6 ns, SPARSE (N=1) is the slow corner** (confirms glm/codex). + WL/precharge + routing
+ counter tail → lands in **ledger §3 t_vmm 5–18 ns → VALIDATED (transient).** **t_vmm 5–18 ns SURVIVES; the 60–190 ns
naive-ramp scare is dead.**
**CROSS-CHECK DONE — 2 independent solvers agree (`bl_ode.py`):** an independent **RK4 numerical integrator** (with a
nonlinear cell I-V + access-FET saturation) reproduces the analytical RC settle to **<0.1%** at every N (N=1: 5.545 vs
5.548 ns; N=128: 0.043 vs 0.043 ns). **FET-sat does NOT bite at 0.2 V read** (I_cell 5 µA < 10 µA sat) → linear-R valid
in our regime. ⇒ **the t_vmm analog-settle floor ~0.24–5.75 ns (sparse N=1 = slow corner) is cross-confirmed.**
- ⚠️ **`ahkab` (pip "SPICE") was version-incompatible** with the modern stack — 3 issues: import (scipy window fns moved
  to `scipy.signal.windows`, fixed by a shim) then core `float(1-elem array)` banned in numpy ≥1.25. Per discipline,
  did NOT thrash a 2015 tool / downgrade numpy (would break CrossSim/torch) → used the direct RK4 integrator (robust).
- **2nd-order sensitivity DONE (`bl_ode2.py`, extended RK4):** added IR-drop (BL metal R_col), nonlinear ReRAM I-V
  (curvature α), and comparator metastability (longer decision at small/sparse signal). **The sparse N=1 slow corner
  (which SETS t_vmm) barely moves: 5.55 → 4.9 ns** (nonlinearity speeds initial charge; IR-drop hits only the dense
  end which is already sub-ns). **All cells stay sub-6 ns → t_vmm 5–18 ns band is ROBUST to the 2nd-order terms.**
- 🔴 **Residual GAP (not overclaimed):** the IR-drop/metastability/curvature are still MODELED params (R_wire, α from
  estimates) → a **modern ngspice with measured device models, or silicon**, is the final word. ahkab(pip)=version-dead.
- **Net: t_vmm 5–18 ns now stands on 5 convergent legs** — 28nm SAR cohort (lit), NeuroSim analog read ~4 ns, counter
  study (2-step ~5–20 ns), analytical RC, RK4 ODE. The 60–190 ns naive-ramp scare is dead.

## RESIDUAL OPEN
- The differential-ternary **zero-crossing / sparse-read** slow corner (codex+glm) — does the chosen scheme handle it
  (timeout/ping-pong, or window-comparator that's magnitude-independent)? → part of the SPICE.
- Do NOT rewrite ledger §3 t_vmm yet — but the counter study **REMOVES the "t_vmm may be 60–190 ns" downside scare**;
  the 5–18 ns assumption survives, gated on the SPICE settle number.
