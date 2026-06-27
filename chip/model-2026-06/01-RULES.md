# 01 — RULES (the methodology that, when skipped, produced the mess)

> Locked methodology for the cleanroom chip model. Every later artifact (`02-PARAMETERS` … `07-calculator.html`)
> obeys these. Status: **DRAFT → fleet-panel #1 → fold → LOCK.** (Panel verdict appended at bottom.)

---

## R0 — THE CONCLUSION GATE (bidirectional). Run before stating ANY number / conclusion / "done".

1. **Load-bearing or convenient proxy?** Is this the thing the decision actually rests on, or a number that was easy
   to reach? Ground the load-bearing thing.
2. **Did I try to FALSIFY it?** Actively attempt to break it (recompute the other way, find the disconfirming anchor),
   not just confirm.
3. **Surprise / conflict → suspect my own tool/data FIRST.** If a result contradicts a hard anchor or surprises me,
   the command/data/unit is wrong until proven otherwise — do not report it as a finding.
4. **Don't quit at the first wall.** Exhaust the levers, go first-principles, check how others solved it.
5. **Record the lesson NOW** (ledger/arsenal), not "later."

**Both directions are failures — this gate guards both:**
- ❌ **Optimistic drift** — wishing density up; promoting the bottom-up ÷periphery CEILING to an OPERATING number;
  defaulting all macros "free/active"; quoting a peak as a system number.
- ❌ **Harsh pessimism** — collapsing a measured RANGE to its lowest anchor; distrusting our own calc system;
  truncating a measured high end; declaring a wall before the levers are exhausted.

**The honest answer is almost always a graded RANGE, not a point.** A premature peak and a premature floor are equally wrong.

---

## R1 — NEVER anchor OUR number to a mismatched NODE or mismatched PARADIGM. (the #1 rule)

- **Mismatched node:** SPIKA is **180nm, 8 Kbit, post-layout SIM**. Its raw numbers (0.0249 Mb/mm², 60 ns/VMM,
  195 TOPS/W, 5-bit counter) are a different node and a tiny un-amortized prototype. **Use SPIKA for the SCHEME ONLY**
  — the architecture (2-cell binary-differential pair = 1 ternary weight; per-2-column up/down counter readout; no
  ADC). Never scale a 180nm prototype number and call it "our measured 28nm value."
- **Mismatched paradigm:** the **analog weight-stationary CHIP** is paradigm-native — `decode = min(timing-ceiling,
  power-bound)`, weights resident, one R×C analog VMM = R·C MACs. The **FPGA / digital-ternary-datapath DEMO** is
  systolic — `tok/s = f·P/(2N)` is valid THERE and only there. **Never quote the FPGA's systolic number as the chip.**
  (This is the #1 source of stale tok/s — e.g. 204 / 4076 / P=8192.)
- **Suspect any number whose node/paradigm you can't name.** If you can't say "this is 28nm measured / 180nm scheme /
  FPGA demo / first-principles," it isn't grounded.

---

## R2 — GROUND BEFORE USE. Triangulate. Report a graded RANGE.

No number enters a formula until it is in **`04-LEDGER.md`** with a value/range, a GRADE, and a primary source.
If it's not in the ledger, it is **not confirmed**. Every load-bearing number needs **≥2 independent EVIDENTIARY legs
(A + B)** plus an adversarial review (C). **Leg C is a CHECK, not a counted evidentiary leg** (codex catch — a critique
process generates no new evidence; don't let it inflate the independence count):

- **Leg A — first principles:** derive from device physics with OUR cell params (Ohm/Kirchhoff for the MAC; k·F² +
  selector-FET width for cell area; RC settling + kTC/quantization noise for t_vmm; C·V² for energy; Arrhenius for
  retention).
- **Leg B — ≥2 MEASURED experiments matching node AND regime (primary = 22/28nm, counting-readout):** real silicon
  macros, each cited (paper · node · what-measured). **Primary same-node anchors:** Intel 22FFL eNVM 10.1 Mb/mm²;
  NTHU/TSMC ISSCC'19–'24 t_vmm 5–18 ns (22/28nm); HYDAR ~28nm 1.63 Mb/mm² (grade-C/待论文); NTHU ISSCC'21 11.9–15
  TOPS/W. **Node-scaled CROSS-CHECKS only (R2b, NOT primary):** ISSCC'21 14nm 1T1R 0.022 µm²; PKU IEDM'23 40nm
  0.0648 µm² (selector-current floor) — used only with an explicit (node/14)² scaling, never as the 28nm number.
- **Leg C — fleet cross-check (REVIEW, not evidence):** the panel critiques the derivation + the anchors.

**The spread ACROSS legs IS the honest uncertainty.** If A and B disagree, **EXPLAIN the systematic variance** (e.g.
prototype-vs-product periphery amortization; node scaling; differential ÷2) — do **not** silently pick the lowest or
the highest. Keep the cascade LEVELS distinct (cell → array → CIM-core) and name the factor at each step.

**R2a — CORRELATION / COMMON-MODE AUDIT (panel #1 catch — codex/minimax/glm converged).** Legs only count as
*independent* if they don't share inputs. The danger is **fake convergence**: Leg A is often parameterized from the
same papers as Leg B, and all published Leg-B macros share priors (publication bias = only good results print; a
shared "small-macro periphery is light" convention; the same foundry device model). Two anchors from one pool are
**one leg, not two** — and their narrow spread *underestimates* uncertainty because the common-mode bias is invisible
to it. So for each grounded number, **list explicitly the assumptions / datasets / formulas shared across its legs**;
if Leg A and Leg B draw on the same source, say so and **widen the range** (or grade 🔴 contested). Require at least
one **structurally independent** check — our own first-principles with our own I_SET, a non-CIM teardown, or a
device-physics bound that doesn't inherit the CIM-paper convention.

**R2b — "SIMILAR NODE" is not enough; match the REGIME (panel #1 catch).** Node (nm) is one regime variable; selector
topology, read scheme (counting-ADC vs SAR vs ADC), and array size matter as much. A primary Leg-B anchor must match
node **and** regime. 14nm / 40nm anchors are allowed **only** as explicitly node-scaled cross-checks (state the
scaling law used), never as the primary same-node number.

**R2c — "EXPLAIN THE VARIANCE" must be FALSIFIABLE, not a label (panel #1 catch).** A sufficient explanation states a
**mechanism with a direction and rough magnitude** ("8 Kbit prototype → ≥1 Mb product amortizes periphery from ~30%
to ~12% of core area, i.e. usable-array share 70%→88% = **88/70 ≈ 1.26× core density**" — show the division, don't
round to a wished number), not a noun ("node scaling," "process difference"). If you cannot state the mechanism's
magnitude, you may **not** pick a point inside the spread — report the full range and grade it 🔴 CONTESTED.

---

## R3 — SEPARATE the boundaries that keep getting conflated.

1. **STORAGE density ≠ CIM-core density.** Bare cell / 1T2R (e.g. 14.8 Mb/mm²) is a storage ceiling; the CIM-core
   carries counter/comparator/DPC periphery and is much lower.
2. **Bottom-up "÷periphery-factor" CEILING ≠ OPERATING density.** The ÷1.3 cascade is the optimistic upper bound;
   the measured counter-CIM periphery collapse is heavier. Report the operating RANGE (low = un-amortized prototype
   scaled; high = best real 28nm all-in measurement). Do not collapse to the low anchor.
3. **Analog CHIP throughput ≠ FPGA-demo throughput** (see R1, paradigm).
4. **Analog-macro PEAK TOPS/W (bit-normalized) ≠ system-level TOPS/W.** Report the system-level range.

---

## R4 — FLEET CROSS-CHECK is mandatory for load-bearing items.

Before locking the RULES, each grounded NUMBER's method, the ENGINE formulas, and any strategic conclusion, run the
full panel:
```
fleet-rs compare "Critique / find errors in: <…>" --targets codex,kimi,minimax,glm
```
(binary: `fleet-rs`). Treat **every worker as UNTRUSTED**; act only on
real catches; record them. Different providers = real 互相挑错. **Slow but worth it.** Batch the checks at the
load-bearing gates rather than one panel per number.

---

## R5 — GRADE EVERYTHING.

| grade | meaning | use |
|---|---|---|
| 🟢 GROUNDED | primary MEASURED / cited source (ours or lit) | quote freely (with the range) |
| 🟡 MODELED | first-principles / derived, NOT measured on our chip | quote with "modeled" |
| 🔴 GAP / CONTESTED | **GAP** = silicon-only unknown (needs a domestic ReRAM fab / tapeout / SPICE); **CONTESTED** = legs conflict and the variance can't be sized (R2c) | name it, never fake it |
| ⚫ SUPERSEDED | stale; replacement noted | NEVER use |

Honest "🔴 GAP, needs a domestic ReRAM fab" beats a confident fake. The load-bearing GAPs — **a domestic ReRAM fab 28nm cell pitch / I_SET; our SPICE
t_vmm; hybrid-bond access for a small CN fabless** — stay named; they gate where the operating point lands.

---

## R6 — LEGO + record-as-you-go.

Smallest testable pieces first; isolation-test each; assemble incrementally. Write each lesson/number into the
ledger the same step (write-then-shelf is the failure mode). All local, $0; fleet = subscription CLIs, never metered API.

---

## SUPERSEDED — never reuse (carry into `04-LEDGER` §SUPERSEDED)

`tok/s = f·P/(2N)` and **204 tok/s** as the analog chip's decode; P=8192 / 4076 from stale density; analog PEAK
**28–195 TOPS/W** as the system number; **90 Mb/mm²** (abandoned cross-point); **14.8 Mb/mm²** quoted as "CIM"
(it's storage 1T2R); **"5-bit counter"** as the final spec (it's ≥7-bit); **180nm SPIKA numbers** as 28nm values;
collapsing density to a harsh low anchor; promoting the ÷1.3 ceiling to operating.

---

## FLEET PANEL #1 VERDICT (rules) — run `rs-1782356160`, 2026-06-25

Panel: codex ✅ · minimax ✅ · glm ✅ · kimi ❌ (quota — refold next cycle). 3/4 **agreed** on ONE load-bearing hole,
plus two refinements. (Caveat per R2a applied to the panel ITSELF: 3 LLM providers agreeing is not full independence —
they may share training priors; treat as corroboration, not proof. codex re-review caught this overclaim.) All folded:

- **[FOLDED → R2a] Correlated / common-mode error across legs (codex High · minimax #1 · glm A).** The biggest catch:
  triangulation can be pseudo-replication — Leg A parameterized from the same papers as Leg B, all Leg-B macros from
  one published pool sharing publication bias + a "small-macro periphery is light" convention. Fake convergence →
  underestimated uncertainty. Added the explicit correlation/common-mode audit + "two from one pool = one leg" +
  require one structurally-independent check.
- **[FOLDED → R2b] "Similar node 22/28nm" too loose (codex High #2).** 14nm/40nm anchors were admitted alongside;
  node isn't the only regime variable (selector topology, read scheme, array size). Primary anchor must match
  node AND regime; 14/40nm only as node-scaled cross-checks.
- **[FOLDED → R2c] "Explain the variance" is unenforceable hand-waving (minimax #2).** No bar for a sufficient
  explanation; a post-hoc label satisfies the letter. Now requires a falsifiable mechanism with direction + magnitude,
  else report the full range as 🔴 contested.

**Status: LOCKED** (re-run kimi leg opportunistically next cycle; no catch is expected to overturn R0/R1/R3).
