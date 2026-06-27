# 10 — PERIPHERY BINDING STUDY: where does the digital periphery actually bind US?

> **Method (our triangulation, non-negotiable):** every "this binds / this doesn't" verdict must stand on
> **THREE independent legs — (1) first-principles, (2) literature, (3) simulation — and be fleet cross-validated.**
> A single leg is a guess. This doc replaces the hand-wavy 2026-06-26 table with a systematic, falsifiable study.

## THE QUESTION (precise)
NeuroSim says "digital periphery = 91% of layer latency." But NeuroSim models a **conventional shared-ADC CNN
accelerator** — NOT our design (ternary, weights-resident, **ADC-free counting** readout, transformer workload).
So "periphery binds us" is **not yet established**. We must **decompose** the periphery into atomic blocks and, for
EACH block, decide on **LATENCY / AREA / ENERGY** whether it (a) **fundamentally binds OUR design**, (b) is a
**NeuroSim-architecture artifact** that our design removes, or (c) is **uncertain → name the experiment**.

## DECOMPOSITION — the per-VMM-stage signal chain + inter-stage digital
| # | block | what it does | in OUR design |
|---|---|---|---|
| 1 | **Input DAC / WL drivers** | drive activation onto wordlines | bit-serial if multi-bit input |
| 2 | **crossbar analog integrate** | the resident-weight MVM (NOT periphery) | the ~4 ns fast floor |
| 3 | **counter readout** (per-2-col) | ADC-free: count current vs reference | **our ADC replacement — scheme = the big unknown** |
| 4 | **comparator** (differential) | sign/threshold decision | per-2-col |
| 5 | **add-tree / shift-add** | combine row-tiles + bit-significance | log₂(tiles) + numBitInput levels |
| 6 | **output latch / buffer** | hold digital result | small |
| 7 | **nonlinearity** | softmax / LayerNorm / GELU | inter-stage digital — transcendentals + reductions |
| 8 | **interconnect / routing** | move activation vector to next layer; KV r/w | weights-resident ⇒ activations-only |
| 9 | **attention (QKᵀ, AV)** | activation×activation (dynamic, not weight) | digital SFU / separate path; O(ctx²) |

## FIRST-PRINCIPLES VERDICT (latency focus; from ledger §1/§3/§5 cell params)
- **#2 crossbar ≈ 4 ns** — the fast floor (NeuroSim-confirmed). Does NOT bind. ✅ our side.
- **#3 COUNTER = THE LOAD-BEARING UNKNOWN.** Latency depends entirely on the **counting SCHEME**:
  - *ramp / integrating counter* → latency ∝ **N_active** (up to ~128 for 256 rows @50% sparsity) × t_clk → at 1 GHz
    that's **~tens–128 ns** → would DOMINATE and bind hard.
  - *SAR-like* → ∝ **log₂(N)** = ~7 cycles → ~7 ns → modest.
  - NeuroSim's "ADC ~3.4 ns/read" assumes a fast SAR ADC — **but our design is a COUNTER, which may be ramp-like.**
    **⇒ This is the #1 thing to pin: which counting scheme, and its latency law. Until pinned, the whole "does
    readout bind us" question is open.** (First-principles alone can't decide — needs literature + SPICE.)
- **#7 NONLINEARITY (softmax/LN/GELU) BINDS.** O(d) reduction + transcendentals (exp/div/sqrt). d=2048 LayerNorm on a
  ~1 GHz digital unit ≈ **hundreds of cycles ≈ hundreds of ns/layer** → real inter-stage cost (the fleet-panel point).
- **#1 INPUT BIT-WIDTH binds linearly** — bit-serial ⇒ numBitInput × per-read. Low-bit activations (our advantage)
  keep it small; needs our actual activation bit-width.
- **#9 ATTENTION binds at long ctx** (O(ctx²), dynamic) — separate study.
- **#4 comparator, #5 add-tree, #6 latch** — small latency (ns / log-depth); bind AREA/ENERGY more than latency.
- **NeuroSim-artifacts we REMOVE:** shared-ADC **mux/switchmatrix** time-multiplexing (we have distributed counters,
  not a shared ADC), **pooling** (transformer has none), heavy **feature-map IC** (weights resident ⇒ activations-only).

## THE 3-LEG VERIFICATION MATRIX (what each leg must independently confirm)
| block | first-principles | literature (find real numbers) | simulation | status |
|---|---|---|---|---|
| #3 counter scheme+latency | ramp∝N vs SAR∝logN derivation | RRAM-CIM counting/ramp/SAR ADC conversion-latency papers (NTHU/ISSCC/TSMC) | SPICE of OUR counter; NeuroSim ADC proxy | 🔴 OPEN — #1 |
| #7 nonlinearity | cycle-count for softmax/LN/GELU @d | CIM transformer accelerators: % latency/energy in nonlinearities | NeuroSim activation-unit; analog-attention papers | 🔴 OPEN |
| #1 input bit-width | numBitInput × per-read | low-bit activation CIM | NeuroSim numBitInput sweep | 🟡 partial |
| #9 attention | O(ctx²) dynamic | analog-attention / KV-in-memory papers | — | 🟡 |
| periphery vs array split | — | CIM macro periphery-fraction across chips | NeuroSim per-component (have: ADC/accum/other) | 🟡 have NeuroSim |

## LEG RESULTS (folding as they land)

### 🔴 #3 COUNTER — literature leg DONE (significant, challenges the ledger)
**Finding (lit):** the per-2-column up/down counter = SPIKA's exact scheme = **counting/integrating/oscillator-type
time-domain readout → latency ∝ N_active (∝ MAC magnitude), NOT ∝ log₂N (SAR) and NOT ∝1 (flash).** Each charge
quantum = one comparator "click" = one counter step. **SPIKA measures 60 ns/VMM** (30 ns integrate + 30 ns click-drain,
500 MHz, ≤15 clicks for 5-b signed, 64×128, per-2-col counter) — they amortize the ∝N law into a **fixed worst-case
window**. Contrast: NTHU SAR ~6.8 ns (∝logN), flash ~1-step. Source: **SPIKA, Front. Electron. 11:1567562 (2025)** (H);
NTHU SSCVSA / DCFTS-IMC (M).
- **⚠️ TENSION WITH LEDGER §3:** our `t_vmm = 5–18 ns` was anchored to the **SAR cohort** — but our **actual readout is a
  COUNTER (∝N, ~60 ns in SPIKA)**. So **the ledger t_vmm likely UNDERSTATES our counter-based design**; the NeuroSim
  "~4 ns analog read" was its SAR-ADC proxy, NOT our counter. **The counter conversion may be the real t_vmm driver.**
- **Does NOT yet rewrite the ledger** — needs: (a) the other legs + fleet, (b) **SPICE OUR counter: sweep N_active
  1→128 at our I_LRS/BL-cap, measure click-period × max-clicks → worst-case drain (ns) @22/28 nm** (faster clock than
  SPIKA's 180 nm-class → may be < 60 ns). Mitigations to weigh: integrate/drain pipelining, lower bit-depth, parallel
  per-2-col counters (already in design) make it ∝N_active-per-column not per-array.
- **Revised verdict (preliminary):** the readout DOES bind us on latency (it's the ∝N counter), but the magnitude
  (tens of ns) and whether it pipelines is the open number. **Promotes "counter scheme" from "unknown" to "confirmed
  ∝N family; pin the ns via SPICE."**

### 🟠 periphery-vs-array split — literature leg DONE, then ⚠️ CORRECTED vs our own prior work
**⚠️ CORRECTION (we caught; I failed to grep our prior work):** the subagent's "SPIKA periphery = 58.5% area /
96.5% power, array 41.5%" **re-trod a Table-5 misread our panel ALREADY corrected** (`readout-locality.md`, rs-1782316312).
**Correct SPIKA Table-5:** 1T1R array+drivers = **70% area** (not 41.5%); the truly digital/movable **COUNTER = only
10.3% area / 3.5% power**; the "96.5% power" is the **analog-LOCAL floor** (comparator 53.8% + DPC + cap — must stay
local, it's the cost of reading a low-current array, NOT removable area). SPIKA's 64×128 is also a **tiny array** →
periphery fraction inflated. So "periphery eats most of the AREA" is FALSE; the movable digital part (counter) is ~10%.
**Lesson re-applied: cross-check any agent number against our own corrected ledger/grounding BEFORE folding.**

~~**Finding (lit):** periphery DOMINATES... 58–96% of area AND energy; array = 3.5% power / 41.5% area.~~ ⚫ SUPERSEDED by the correction above.
**What SURVIVES:** periphery dominates POWER (analog read of low-I array) and ADC-free removes the single biggest block
in *conventional* designs, but in OUR (already ADC-free) design the readout is **comparator/DPC(analog-local) + counter(10.3%)** — the AREA story is the array (70%), not the periphery. The two-chip move = **vertical 3D** (readout tier stacked) → compute die ~94% array (`readout-locality.md`). In conventional designs the **ADC is the single biggest
block** (ISAAC: ADC = **58% tile power / 31% area**, Shafiee ISCA'16). **BUT the load-bearing catch:** SPIKA (ADC-free,
counter readout = closest to OURS) still has periphery = **58.5% area / 96.5% power** — comparators/SA = 53.8% power,
drivers + input DPC carry the rest. Sources: ISAAC ISCA'16 (H), SPIKA Front.Electron.2025 (H), surveys arXiv 2109.03934
/ 2406.08413 (M).
- **⚠️ CORRECTS my 2026-06-26 claim "ADC-free frees us from the periphery bottleneck."** TOO OPTIMISTIC. ADC-free
  **deletes the single biggest BLOCK (the ADC), NOT "most of the periphery."** Even ADC-free, the periphery as a whole
  STILL dominates (SPIKA: 96.5% power is periphery). We swap "ADC dominates" → "comparators + drivers + DPC + counter
  dominate." **Conclusion-gate-both-directions: the lit caught my optimistic drift.**
- **Consistent with density** ("readout-limited macro", ledger §3/§5): the readout periphery is the bottleneck for
  **area AND energy AND latency**, EVEN in our ADC-free design. The unified takeaway holds, but "we escape it" was wrong.

### ⚠️ #7 NONLINEARITY — literature leg DONE (STRONGLY confirms; it's the Amdahl bottleneck)
**Finding (lit):** once matmul is fast analog CIM, **softmax/LayerNorm/GELU become THE latency bottleneck (Amdahl)** —
not just "bind." Real numbers: softmax "up to **40%** of inference time" (Topkima-Former, ISCAS'25); **GELU 28.8% +
softmax 15.1% = ~44%** of runtime (SoftEx/ViT-Base); **scaling the matmul unit 4× yields only 2.54× E2E** (SoftEx —
Amdahl wall is the nonlinearity); INT8 matmul → only **1.1–1.28× E2E** (SOLE — softmax/LN dominate the residual). The
field's fix: **fold softmax into the crossbar VMM** (IMC-softmax, JETCAS'26) or **compute it in-ADC** (Topkima). Sources
(M-H): arXiv 2411.13050, 2412.06321, 2510.17189, JETCAS'26. **Caveat (honest):** most figures are digital/edge/GPU
baselines re-cited by IMC papers; few CIM papers publish a clean nonlinearity-vs-crossbar ENERGY split → our own
per-token {VMM / readout / softmax / LN} log is the load-bearing measurement.
- **Confirms #7 hard, and SHARPENS it:** the chip's whole value (fast matmul) is exactly what PROMOTES the nonlinearity
  to the dominant cost. **The faster we make the array, the more softmax/LN become the wall.**

### REVISED ANSWER (after 3 of 3 legs — DOWNWARD from my hand-wave; all legs CONVERGE)
The digital periphery **binds us substantially — more than I first said.** (1) Latency: our counter is ∝N_active
(~60 ns SPIKA), the real t_vmm driver, not the SAR ~4 ns. (2) Area/energy: periphery ~58%/96.5% even ADC-free. ADC-free
is still our biggest single win, but it is **not** an escape from the periphery. Pending: nonlinearity leg + fleet panel,
then SPICE for OUR counter ns. **Net so far: I was over-optimistic; the periphery binds us, and the lever is "make the
WHOLE readout cheap (counter scheme + comparators + DPC + drivers)," not just "drop the ADC."**

## CROSS-VALIDATION — fleet panel (4th leg, rs-1782474546, codex+kimi+minimax+glm 4/4)
Panel corrected my first-principles framing in **three load-bearing places** (and refined the lit leg):
- **#4 was BACKWARDS (codex+kimi+glm):** "weights-resident → activations-only → light interconnect" is CNN-bias. For
  **transformers the activation/attention dataflow DOMINATES periphery traffic** — QK/AV, softmax-over-sequence (O(N²)),
  KV-cache transpose/traffic, residual/LN reductions — **especially long-context**. We do NOT get to lift NeuroSim's
  interconnect assumption for transformers. **My claim was wrong.**
- **#7 nonlinearity refined (minimax+codex):** the pointwise transcendental MATH (GELU/exp, LN scale) is **parallel and
  cheap** (~1–2 cycles). The bind is the **REDUCTIONS** (softmax sum/max over the sequence, LN mean/var) + the **O(N²)
  attention** + activation movement — NOT "exp is slow." The lit leg's "softmax ~40%" is real but it's the
  reduction/sequence-scaling, not the elementwise op.
- **#3 counter refined (minimax+glm), substance UNCHANGED:** it's **one ramp whose time ∝ peak-count (output magnitude)**,
  not N sequential clicks — but still the **∝magnitude slow family**, and **bit-serial input MULTIPLIES it** (glm: 8-bit
  input → ~1 µs/dot). Our **low-bit activations shrink this** (the lever). Magnitude = SPICE GAP.
- **"removed periphery" = LABEL-SWAP (glm+kimi):** distributed counters/comparators/DPC physically remain (58%/96%);
  we dropped mux-routing + ADC-quantization, not the footprint. (Consistent with leg-2.)
- **+ kimi:** readout latency also floored by analog settling / SNR / IR-drop / charge-sharing, not just the scheme.

## CONVERGENT VERDICT — where the periphery binds us (4 legs agree; DOWNWARD from my hand-wave)
| binds? | block | mechanism (cross-validated) | grade | pin it with |
|---|---|---|---|---|
| ~~🔴 #1~~ → **🟠 SOLVABLE** | **counter/readout conversion** | **CORRECTED by counter study `11` (4-leg):** NOT a hard bind — naive single-slope ∝N (60 ns) → **2-step/window readout + ternary 1-phase input → ~5–20 ns**, overlappable behind the analog settle. The real floor = **analog settle**, not the counter. **t_vmm ~5–18 ns survives.** | 🟡 4-leg | **SPICE the 2-col diff BL settle** (the true floor) |
| **🔴 #1-tie** | **attention dataflow @long-ctx** | QK/AV + softmax-reduction (O(N²)) + KV-cache traffic + residual/LN reductions = heaviest activation movement | 🟡 panel(3/4)+lit | **per-token instrumented split** + an attention/KV latency model |
| 🟠 #2 | input bit-depth | multiplies the counter time (bit-serial) | 🟡 | our real activation bit-width (low = our lever) |
| 🟠 #3 | analog settling / IR-drop floor | rows ≤256, SNR, charge-sharing | 🟡 | SPICE / array sim |
| ✅ not-latency | pointwise nonlinearity math (GELU/exp/LN-scale) | parallel ~1–2 cycles | 🟢 panel | — |
| ✅ not-bottleneck | the crossbar array itself | ~4 ns, the fast floor | 🟢 NeuroSim | — |
| ⚫ NOT our escape | "ADC-free removes the periphery" | label-swap; periphery still 58%/96% (counters/comp/DPC remain) | 🟢 lit+panel | — |

## VERIFICATION PLAN (the "how do we verify", per our method)
1. **SPICE OUR counter** (the #1 unknown): sweep N_active (1→128) × input bit-depth at our I_LRS/BL-cap @22/28nm →
   the real readout ns and its law. **This is the single most load-bearing experiment for the whole throughput story.**
2. **Per-token instrumented latency/energy split** {crossbar VMM · readout/counter · attention-reduction · softmax · LN ·
   KV traffic} at OUR D and sequence length — every leg says this is the missing load-bearing number.
3. **Attention/KV dataflow model** (the long-context bind my #4 wrongly dismissed).
4. NeuroSim cross-check configured ADC-free + low-ADC-bit to quantify how much periphery our scheme actually saves.

## STRATEGIC REFRAME (the real takeaway)
The array (matmul) is the **won / easy** part (~4 ns, dense, cold). **The chip is won or lost in the READOUT + the
ATTENTION DATAFLOW** — and *because* we make the matmul fast, those become the dominant cost (Amdahl). So the
engineering moat is **"make the whole readout + the attention/softmax/KV path cheap"** (cheap counter scheme, low-bit
input, fold softmax into VMM / in-ADC, on-chip KV) — **NOT just "drop the ADC."** My earlier "ADC-free is the moat" is
HALF the story; the other half (counter latency + attention dataflow) is where the harder, more important work is.

## IMPLICATIONS (flagged, not yet folded — need the SPICE + instrumented split first)
- **doc 09 throughput**: our real t_vmm may be **readout-counter-dominated (tens–hundreds ns), > the 5–18 ns assumed**
  → timing ceiling likely lower than even the haircut; long-context cycle worse (attention/KV). Do NOT rewrite until
  SPICE pins the counter ns.
- **ledger §3 t_vmm**: the 5–18 ns SAR-cohort anchor is **the wrong family for our counter** — flag, re-derive after SPICE.
