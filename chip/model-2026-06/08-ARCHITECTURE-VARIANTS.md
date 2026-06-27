# 08 — ARCHITECTURE VARIANTS & the DENSITY SURVIVAL LINE (codex+panel verified, 2026-06-25)

> Density is the **make-or-break line**, not a "nice to have": density↓ → die too big → cost↑ + can't fit a useful model →
> a marginal product → no economic value → can't mobilize capital, people, and supply chain. Only a **leapfrog** advantage earns resources;
> "improved X%" does not. This doc is the strict, falsified version of the architecture design space.

## THE CONFIRMED DENSITY CEILING (panel rs-1782377887, codex+kimi+minimax+glm 4/4)
**Realistic 28nm ternary-differential CIM CORE density ≈ 1.5–2.5 Mb/mm² (hard ceiling ~3–3.5). 4–7 is NOT reachable.**
- ⚫ **The ÷1.3 periphery ceiling (7.1 Mb/mm²) is REFUTED.** The per-2-column counter+comparator+DPC readout is
  **pitch-matched, row-proportional, and does NOT amortize with column width**. glm: at 256 rows, 7-bit counter +
  comparator ≈ 1.79 mm² = **13.7× the array (0.131 mm²)**. The macro is **readout-limited, not cell-limited**.
- Sanity check (all agree): a 28nm macro beating 3nm SRAM-DCIM (3.78 Mb/mm², densest CIM at any node) is implausible.
- Real anchors: HYDAR 28nm 1.63 (whole macro, C-grade) · GT/NVIDIA 40nm binary RRAM-CIM 2.37 · 3nm SRAM-DCIM 3.78.
- **Correction to the ledger:** ③ operating 1.0–1.6 (measured) stands; the **"upside 2–4 / ÷1.3 ceiling 7.1" is wrong**
  → real product ceiling ~2.5–3.5, set by the pitch-matched readout floor.

## THE LEVERS (each: real / blind-alley / rejected, falsified)
| lever | verdict | effect |
|---|---|---|
| **Control off-chip (disaggregation, CIM_frac 0.65→0.85–0.90)** | ✅ REAL co-lever (the "CIM die = all compute, control on a 2nd die" you designed) | ~1.3–1.4× params/die. Caps ~0.90 (array die still needs local PDN + die-to-die PHY). Total system silicon ~conserved, but the *array die* shrinks — which is what matters for the edge form factor |
| **Periphery amortization (wide cols 512→1024+)** | ✅ REAL but LIMITED | pushes core HYDAR 1.63 → ~2–2.5, NOT to 7.1 — the readout is pitch-matched (above) |
| **Smaller die (50/100 vs 200mm²)** | ✅ REAL (wafer-eff +16%, fab-yield 95% vs 82%, stability) | all sizes ship ~85% w/ spares; the prior "50mm² unshippable" was a `0.985^50` arithmetic bug (=47%, not 7.8%) |
| **22nm vs 28nm** | ✅ REAL, modest | ~1.3× density; adds cost/access |
| **3D hybrid-bond** | ❌ NOT NEEDED | the realistic targets need core < the in-plane ceiling; only >~3.5 would need it; also speed-escape solved by weights-resident |
| **Move counter/readout off-die laterally** | ❌ BLIND ALLEY | 18× click-stream bandwidth trap; readout must stay local |
| **Single-ended ternary (drop ÷2 differential)** | ❌ REJECTED  | the only physical 2× lever, but kills read margin/reliability — 256-row common-mode 17µA = 3.5× the 4.93µA signal. Unreliable. Not pursued |
| **MoE** | ❌ doesn't help DENSITY | all experts resident = full die area; MoE helps throughput, not size |
| **High-speed cables / exotic interconnect** | ❌ OVERKILL | inter-die = activations-only ~0.1–0.3 GB/s; cheap organic 2.5D is ~10⁶× over. Enabler is weights-resident, not cables |

## NECESSARY CONDITIONS (reverse-calc; required core×CIM_frac to fit a model in a die)
| target | required core×CIM_frac | verdict @ realistic core ~2–2.5 |
|---|---|---|
| **0.1B @ 50mm²** | core 4.4–6.2 | ❌ **DEAD @28nm** (>realistic ceiling) |
| **0.1B @ ~100mm²** | core 2.0–2.5 (CIM 0.90) | ✅ **the credible target** (needs the optimistic end + full disaggregation) |
| 0.1B @ ~70–85mm² (22nm) | core 2.6–3.3 | ✅ stretch-credible at 22nm |
| 0.3B @ ~100mm² | core 6.7–9.2 | ❌ no (>ceiling) — 0.3B ≈ 300mm² |

## NODE LADDER 28→7nm for 0.1B — TWO-COMPONENT scaling (engine L6; ⚠️ corrected — my first cut was too pessimistic)
**⚠️ SELF-CORRECTION (panel rs-1782379474, codex+kimi+minimax+glm 4/4):** my first node ladder used a flat ~node¹ ("the
access-FET floor caps everything at ~3×, plateau by 14nm, never leaves module-class"). **That was too pessimistic** — the
conclusion-gate-both-directions trap (same failure as the periphery-disaggregation case). The correct model has **two
components:**
- **ARRAY** (1T1R; MV access-FET LENGTH is voltage-floored, holds SET ~1.5–2.5 V) → scales ~node¹, 28→7 ≈ **2.75×**.
- **PERIPHERY** (per-2-column counters + comparators = core LOGIC) → scales ~node², **realistically ≈ 5.75×** 28→7
  (= real TSMC 28→N7 logic density, NOT ideal 16× — pitch-matched BL/PDN/MV-spacing lag; codex+glm caveat folded).

Our macro is **readout-LIMITED** (prior panel: counter+comparator many× the array → periphery fraction f@28nm ≈ 0.6–0.85).
So **node shrink RELIEVES the dominant periphery** → blended uplift 28→7 ≈ **4–5×**, not ~3×. The 28nm density is low
*because* periphery dominates; that same fact makes node shrink (and readout redesign) high-leverage.

| node | uplift/28 | 0.1B die mm² | $/good die | eReRAM access | class |
|---|---|---|---|---|---|
| 28n | 1.0× | 89–111 | $5.9–6.8 | mature/multi-foundry | MODULE↔CARD (straddle 100) |
| **22n** | 1.3× | **67–86** | $6.3–8.2 | **available** | **edge MODULE** ← realistic frontier |
| 16n | 1.8–1.9× | 46–62 | $6.1–9.1 | rare (FinFET) | edge MODULE |
| **14n** | 2.0–2.2× | **40–55** | $6.1–8.7 | rare (FinFET) | edge MODULE ← stretch |
| 12n | 2.4–2.7× | 33–47 | $6.6–9.6 | bleeding-edge | edge MODULE |
| 10n | 2.8–3.3× | 27–39 | $6.6–9.1 | ~none-commercial | edge MODULE (edge) |
| 7n | 4.0–4.9× | 18–28 | $5.8–7.9 | ~none-commercial | phone-companion↔MODULE |

**Reading (arithmetic rs-beewsqn7x; physics rs-bqwdqhela; scaling rs-1782379474 — all 4/4):**
- **Node shrink helps MORE than node¹** (relieves the readout bottleneck). 22nm: 0.1B ~67–86mm². 14nm: ~40–55mm² (notably smaller, not my earlier 50–62).
- **A smaller product class IS geometrically reachable** (I was wrong to say "never"): ~10nm → ~27–39mm², 7nm → ~18–28mm² (phone-companion). **But it is gated by eReRAM ACCESS, not geometry.**
- **eReRAM access is the hard gate**: mature 28/22nm, rare 16/14 (FinFET), ~none commercial ≤10nm. **→ PRACTICALLY capped at 22nm (realistic) / 14nm (stretch); the geometric ≤10nm path to phone-companion is NOT buildable for us today.** $/die also rises at advanced nodes (glm: 28→22 wafer +40–60%).
- **DEEPER LEVER (the real takeaway):** because the readout DOMINATES, **shrinking/sharing the readout at a FIXED node is the SAME knob as node shrink** (reduce the periphery fraction) → a readout redesign is an independent density lever, **possibly bigger than a node step** — and it's available at 28/22nm where we have access. This ties directly to the density-ceiling section (the readout is the bottleneck both places).
- Node-independent sub-25mm² unlocks: a **smaller/task-specific model**, or **1S1R** (removes the access-FET floor → 4F²).

**So 22nm (our pick) buys:** ~25% smaller die (0.1B 89–111 → 67–86mm²), reliably inside module-class — at higher
$/die + NRE, not free. 14nm (stretch, if eReRAM accessible) → ~40–55mm². **It does NOT change the winning axis (µW
always-on).** The highest-leverage density move at our accessible nodes is **attacking the readout periphery**, of which
node shrink is one instance.

## THE SURVIVAL VERDICT
- **The 50mm² fingernail dream is dead at 28nm** (and basically at 22nm). The only physical rescue (single-ended) is
  rejected on reliability.
- **The credible frontier is 0.1B resident at µW in ~90–110mm² (28nm) / ~60–85mm² (22nm)** — still a real bet
  (core must hit the optimistic ~2–2.5, ~1.3–1.5× above the best real macro), but *plausible*, not fantasy.
- This is ~1/8 of an H100, non-volatile, weights-never-move — **differentiated** (a GPU can't run at µW; a digital NPU
  can't hold 0.1B resident). But it is a "serious ~100mm² chip," **not a fingernail sensor add-on.**

## 🔴 LOAD-BEARING GAPs / OPEN QUESTIONS (the make-or-break, verify cheaply before any big spend)
1. **Real ternary-differential macro core density**: does it hit ~2–2.5 (vs the 1.63 HYDAR floor)? → measure a real
   macro (discrete part / open-node) or get a domestic ReRAM fab's product-macro number. **This single number is the project's make-or-break.**
2. **Low-Icc cell vs forming reliability** (glm catch): the ~12 µA Icc that makes the cell small may be *below*
   reliable HfOx forming current — cell-size optimism has a reliability tension. Verify.
3. **The STRATEGIC question:** is "0.1B resident at µW in ~100mm²" a leapfrog advantage with a buyer
   who'd mobilize resources — or, at that size/cost + a small (0.1B) model, is it still a marginal product? Pressure-test the
   economic value + use-case pull, not just the physics.
