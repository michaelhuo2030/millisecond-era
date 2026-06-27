# GROUNDING — readout counter bit-width (the "don't copy a dissimilar experiment" number)

**Target:** how many bits the per-2-column up/down counter needs. SPIKA used 5-bit @64 rows; that does NOT transfer.
**Why load-bearing:** under-spec'd counter quantizes the VMM → perplexity loss; over-spec wastes area.

---

## Leg A — first principles, from OUR cell (two independent sub-derivations)

**A1 — signal/range (information):** LSB must = 1 ternary weight. Our per-weight differential signal = I_LRS−I_HRS =
5.0−0.067 = **4.93 µA** (from cell physics). Range = the **SIGNED** accumulator sum: each active +1 up-counts, each −1
down-counts, so the range is **[−N_active, +N_active]**. At 256 rows, ~50% sparsity, N_active ≈ 128 → range
**[−128, +128] = 257 distinct states** → **bits = ⌈log₂(257)⌉ = 8** (not 7).

> **Panel #5 catch (codex + minimax) — corrected:** my earlier "log₂(128) = 7" wrongly used the *count* of active
> weights (128) as the range. The counter is **signed** (up/down), so the range is the signed sum [−128,+128] ≈ 257
> states ≈ **8-bit**. So the two legs do NOT both land at exactly 7 — first-principles (signed range) argues **8-bit**;
> the D5 measurement shows **7-bit is empirically ACCEPTABLE** (+0.7% ppl), i.e. 7-bit is a tolerable 1-bit truncation
> of the full signed range, not the lossless requirement. **Honest answer: 7-bit floor (measured-OK), 8-bit for full
> signed fidelity.**

**A2 — common-mode floor (why 2-column differential is strongly favored):** 256 rows of HRS leak = 256 × 0.067 µA =
**17.1 µA common-mode**, which is **3.5× the 4.93 µA single-weight signal**. Single-ended readout buries the LSB under
common-mode; the 2-cell differential cancels it so LSB = 1 weight survives. (75× on/off alone is NOT enough — this is
the elephant.) **Honesty (codex catch):** 3.5× common-mode is a *serious* baseline problem, but "single-ended is
impossible" would need a full noise/offset/dynamic-range budget to prove; the rigorous claim is "differential is
strongly favored / the clean solution," not a proof of impossibility.

A1 (signed range → 8-bit) and A2 (SNR/common-mode → justifies the LSB) are independent; A1 puts the full-fidelity
requirement at **8-bit**, with **7-bit the measured-acceptable floor**.

## Leg B — ≥2 MEASURED anchors

| anchor | what measured | role |
|---|---|---|
| **OUR D5 ppl sweep (BUILDABILITY-LOCK D5/D1)** | **7-bit → +0.7% ppl · 5-bit → +4.0% ppl** | 🟢 primary — direct measurement of the cost |
| SPIKA 5-bit @64 rows (dissimilar — do NOT copy) | 5-bit sufficient at 64 rows | shows why copying fails: range scales with N_active, and 64≠256 |

Quantization SNR (corrected — codex catch): each added bit ≈ **+6.02 dB**, so 5→7-bit = **+12 dB** (~4× noise
reduction), consistent with the +4.0%→+0.7% ppl measurement. (My earlier "9.8 → 39 dB" mixed conventions and implied
a wrong +29 dB.)

## The three bit numbers (codex catch — reconcile, don't contradict)
The signed accumulator range = **±N_active**, and N_active depends on sparsity, so there are THREE distinct numbers:
- **7-bit = the MEASURED-acceptable floor** (D5: +0.7% ppl) — a tolerable 1-bit truncation @~50% sparsity.
- **8-bit = full signed fidelity @ ~50% sparsity** (N_active≈128 → range ±128 = 257 states → ⌈log₂257⌉ = 8).
- **10-bit = absolute worst case** (all 256 rows active, no sparsity → range ±256 = 513 states → ⌈log₂513⌉ = 10).
**Headline: 7-bit floor, 8-bit for the realistic sparse operating point, 10-bit only if sparsity vanishes.** SPIKA's
5-bit @64 rows is dissimilar (range scales with N_active; 64≠256) and was correctly NOT copied (R1).

## Area cost (corrected — codex catch)
5→7-bit = **+40% on the counter**; the counter is **10.3% of core area** (SPIKA Table-5), so this is **+4.1% core
area ⇒ ~−4% core density** (NOT the −0.5–1% I wrote). Still **zero throughput impact** (counters sit at the readout
edge; VMM/MAC count unchanged), and small relative to the array — but ~−4%, not negligible.

## Result
- **counter = 7-bit floor (measured-OK +0.7% ppl) · 8-bit full @~50% sparsity · 10-bit worst-case (256 active)** —
  🟢 measured floor + 🟡 first-principles. (Corrected twice: panel #5 fixed "exactly 7→sign", codex fixed "8→up to 10".)
- Area cost ~**−4% core density** (not −0.5–1%), 0 throughput.
- ⚫ SUPERSEDED: "5-bit counter" final; "log₂(128)=7 exactly" (ignored sign); "8-bit is full" (worst-case is 10-bit).

## Fleet verdict (panel #5 rs-1782357285 + codex re-review rs-1782362260)
- **[FOLDED] signed range** → 7-bit floor / 8-bit @50%-sparse / 10-bit worst-case (codex corrected my "8-bit full").
- **[FOLDED] SNR** = +6 dB/bit ⇒ 5→7 = +12 dB (was wrongly +29).
- **[FOLDED] area** = ~−4% core (was −0.5–1%).
- **[NOTED] "2-col differential MANDATORY"** is graded a touch strong — 17.1µA/4.93µA=3.5× shows a serious baseline
  problem, but "impossible single-ended" needs a full noise/offset budget (codex); softened to "strongly favored".
- **[NOTED] PDN 400–600 macros/die** is a compact modeled assertion (the 950→400–600 mapping isn't fully shown).
- **[NOTED] 3D physics-vs-cost** framing reworded in readout-locality.md.
