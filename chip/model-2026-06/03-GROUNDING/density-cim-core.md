# GROUNDING — OPERATING CIM-core density (the cascade ②→③, the periphery collapse)

**Target:** operating CIM-core density @28nm (Mb/mm²) and effective ternary weights/mm² (÷2). This is the most-drifted
number in the whole project (a session drifted it 3× optimistic; another session collapsed it harsh). Both are wrong.

---

## The cascade (levels stay distinct — R3)
```
① bare cell        6.2–11.4 Mb/mm²   (storage ceiling, from density-cell-area.md)
② array  ×0.60–0.70 → 3.7–8.0 Mb/mm² (row/col drivers; SPIKA §3 method)   — CLEAN step
②→③ PERIPHERY FACTOR  ← the systematic variance lives here
③ OPERATING CIM-core   0.5–1.6 Mb/mm²
④ ternary wt/mm²  ③×1e6/2 → 0.25–0.8 M wt/mm²
```

## Leg A — first principles (periphery weight)
The counter-CIM periphery is per-2-column comparator + up/down counter + per-row DPC. From SPIKA Table-5 *structure*
(scheme only, R1): at a small 8 Kbit array, periphery is ~30% of core area → core AREA ≈ array_area / 0.70 ≈ 1.43×
array_area, so **core DENSITY ≈ array_density / 1.43** (more area for the same bits = lower bits/mm²). The bottom-up
"÷1.3" applies that thinned at product scale — but that is a **ceiling**, not operating (R3).

## Leg B — anchors (the range ENDPOINTS) — both carry caveats; neither is a clean 🟢 same-node measurement

| anchor | node·regime | density | role | caveat (R2a/R2b) |
|---|---|---|---|---|
| **HYDAR** (华为-字节-清华 ISSCC'26, 36Mb/22.08mm²) | node only *asserted* 28nm; **recommendation-system HMC accelerator** | **1.63 Mb/mm²** | HIGH end | **grade C / 待论文** (second-hand, full paper unpulled); reports **QPS not ns**; **regime may NOT be our ternary 2-cell-differential CIM** → possible R2b mismatch |
| SPIKA 8 Kbit, node-scaled to 28nm | 180nm→28nm (SCHEME only, R1) | ~0.5 Mb/mm² | LOW end | node-mismatched (180nm); periphery UN-amortized at 8 Kbit |

**Honest grade (corrected from the old ledger's 🟢):** neither endpoint is a clean same-node measurement of OUR
scheme. LOW is a node-scaled scheme number; HIGH is a C-grade pending-paper number from a possibly-different regime.
So **③ is 🟡 MODELED with measured-adjacent anchors**, not 🟢 GROUNDED. (This is itself a cleanroom catch: the prior
`GROUNDED-NUMBERS-LEDGER` over-graded ③ as 🟢 — the very optimistic-drift R0/R5 guard against.) The **range 0.5–1.6
stays** (correcting the grade ≠ collapsing the range — that would be the harsh-pessimism error).

## Systematic variance — falsifiable mechanism (R2c), not a label
LOW (0.5) → HIGH (1.6) ≈ 3.2× spread. **Mechanism: periphery amortization with array size.** An 8 Kbit prototype
spends ~30% of core area on periphery; a product ≥1 Mb macro amortizes the same per-2-col counter + per-row DPC over
many more cells → periphery fraction falls and core density climbs toward the HYDAR-measured 1.63. This is a
checkable, directional, sized mechanism — so the range is honest, **not** 🔴 contested. **Do not collapse to 0.5**
(harsh) and **do not promote the ÷1.3 ceiling 2–6** (optimistic). Operating = **0.5–1.6 Mb/mm²**.

## Panel #2 catch (minimax — codex/glm timed out, panel thin, re-run next cycle)
**HYDAR 1.63 is MACRO-level (the 36 Mb / 22.08 mm² array block), NOT die-level all-in.** The amortization mechanism
above applies ONLY to *on-array* periphery (column drivers, DPC). Die-level **routing / PDN / clock-distribution / I-O /
controller** are *fixed* overheads that do NOT amortize with array size — at product-die scale they pull effective
density BELOW the macro number. **So ③ 0.5–1.6 Mb/mm² is a CORE/MACRO density; the die-level fixed overhead is
captured DOWNSTREAM in the per-die `× CIM-frac 0.55–0.70` step** (the **CIM-frac** is the fraction of die area that is
CIM array — the 30–45% non-CIM is exactly control / I-O / PDN / routing; codex catch: **yield does NOT capture this
overhead, CIM-frac does** — yield is the separate defect term). The wording "climbs toward 1.63" is scoped to the
macro level. Net effect: do not read ③'s high end as a die-level number.

## R2a correlation / common-mode note
HYDAR and SPIKA are both *published ReRAM-CIM macros* → they share the field's "small-macro periphery is light"
convention and publication bias. The independent check is **Leg A device-physics** (our own counter/comparator area
budget) + the **HYDAR all-in measurement explicitly INCLUDES periphery** (not a cell-pitch number), which breaks the
common-mode "periphery-light" optimism. The residual common-mode risk (both could under-count product-scale routing
/ PDN area) is why ③ is graded **🟡 with a range**, not a point, and why the upper end is HYDAR-capped, not the ÷1.3 ceiling.

## ⚠️ UNRESOLVED TENSION between two prior analyses (do NOT fake-resolve — name it)
Two prior docs disagree on ③, in OPPOSITE directions:
- **Jun-23 `10-DENSITY`:** operating core = **0.5–4 Mb/mm²**. Argues SPIKA-scaled **0.5 is a SUB-SCALE (8 Kbit) prototype
  floor that should NOT be the product operating number**; a ≥1 Mb product macro amortizes on-array periphery UP toward
  ~2–4 (cell-pitch ceiling 3–6). → pushes ③ HIGHER.
- **Jun-25 ledger + panel #2 (minimax):** HYDAR macro 1.63 is the best large-array MEASURED anchor and is macro-not-die;
  die-level routing/PDN pulls effective density LOWER. → caps/pulls ③ LOWER.

**Honest synthesis (R3 + R0 bidirectional):** the cleanroom rule says report the **measured** operating band and treat
the ÷periphery product-projection as a (modeled) UPSIDE, not the base case:
- **Base operating band ≈ 0.5–1.6 Mb/mm²** — anchored by **one weak measured macro claim (HYDAR, grade-C) + one
  node-scaled scheme floor (SPIKA)**; NOT a clean "measured" band (codex catch — don't label it MEASURED). 🟡.
- **Upside ≈ 2–4 Mb/mm² (MODELED: ≥1 Mb-macro amortization toward the 3–6 cell-pitch ceiling)** — realized only if
  on-array amortization beats die-level fixed overhead; R3 flags this as the optimistic bound, NOT operating.
- **Which it is = the 🔴 #1 GAP (a domestic ReRAM fab real product-macro density).** Note: SPIKA's 0.5 is itself sub-8 Kbit, so the
  true product FLOOR is probably > 0.5 — i.e. the *base band may be slightly pessimistic at the low end*. Surfaced for review; not silently picked.

## Result
- **③ OPERATING CIM-core @28nm — base (measured) 0.5–1.6 Mb/mm²; modeled upside to ~2–4** — 🟡 MODELED/CONTESTED
  (anchors: SPIKA-scaled sub-scale low 🟡, HYDAR C-grade macro high 🟡; product-scale projection 🟡-optimistic).
- **④ effective ternary weights = 0.25–0.8 M wt/mm²** — 🟡 (③ ÷2 differential; do not truncate the HYDAR-high to 0.5).
- **per GOOD 200 mm² die ≈ 27–112 M params** (④ × 200 × CIM-frac 0.55–0.70 — **no yield here**; yield reduces #good
  dies/wafer, not capacity per working die — codex catch).
- **③′ bottom-up ÷1.3 ceiling 2–6 Mb/mm² = 🟡🔴 ceiling, NEVER operating.**
- **🔴 #1 GAP:** a domestic ReRAM fab real 28nm cell pitch + array-eff + our periphery → decides where in 0.5–1.6 we actually land.

## Fleet verdict (panel #2)
*(appended after panel)*
