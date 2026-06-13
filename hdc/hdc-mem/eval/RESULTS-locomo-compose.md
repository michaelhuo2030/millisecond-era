# LoCoMo compose — the compose operator on public data (trinity-lite)

**Goal:** turn the LoCoMo compose-gap from *motivation* into a *demonstrated* operator, using real structure with **no heavy LLM**. LoCoMo gives one clean structural key for free: every turn has a **speaker**, and ~91% of questions name the person they ask about. The trinity step is a dumb name-match (extract speaker from question); HDC **binds** it.

`turn_HV = norm(R_c ⊙ emb(turn)) + α·norm(R_s ⊙ A_spk[turn.speaker])`, query likewise → `cos ≈ semantic(q,t) + α²·[same-speaker bonus]` (a **soft algebraic speaker-boost**). Embeddings computed offline with bge-m3, thread-throttled. 10 convs, 3 atom-seeds ±SE.

## Result → `RESULTS-locomo-compose.json` (recall@5, n=1554 single / 423 multi, speaker-detected 1809/1977)

| method | single | multi (compose-relevant) |
|---|---|---|
| flat bge (semantic only) | 0.198±0.010 | 0.063±0.009 |
| flat + **hard** speaker-filter | 0.511±0.013 | 0.298±0.016 |
| HDC compose@0.5 | 0.511±0.007 | 0.289±0.009 |
| **HDC compose@1.0** | **0.511±0.007** | **0.298±0.009** |

## Reading it (honest, premortem-driven)

1. **Structure is a huge lever on real data.** Binding one extractable key (speaker) lifts recall **2.6× (single, 0.198→0.511)** and **4.7× (multi, 0.063→0.298)**. This is the public-data proof that *the compose thesis is right* — when you can extract and bind structure, retrieval improves massively, and flat embedding simply cannot access it.
2. **HDC soft-compose matches the hard filter exactly** (0.511 / 0.298 at α=1.0). So on this **1-bit** structural key, the honest verdict is **compose ≈ filter, not compose > filter.** The compose operator *delivers* the structure gain; it does not beat explicit filtering at it.
3. **Where compose's edge actually is** (not shown by a 1-bit key): it ANDs *multiple* constraints in one vector (speaker AND time AND topic — a hard filter must enumerate every combination), and it is **soft** (a +α² boost, robust to mis-detection — a hard filter fails completely on a wrong speaker). At α=0.5 the soft version already nearly matches (0.289 vs 0.298), showing the graceful-degradation knob.

## Bottom line
`compose` is now **demonstrated on public conversation data**: it converts extractable structure into a 2.6–4.7× recall gain that flat retrieval can't reach, as one composable soft algebraic operation. The honest caveat is that a single structural key only lets it *match* explicit filtering — its differentiation (multi-constraint composition, soft robustness) needs a richer extraction (more roles/time/topic), which is the next trinity step. Combined with the **forget** win (exact, Δ=0 on real conversations) and the **synthetic CompositionEval** (bind beats flat by ~10pt given multi-attribute structure), the standard now has forget + compose evidence on both synthetic and public data. Emitted organism L1 (CONFIRM→POC, no held-out).
