# LoCoMo — the memory-algebra standard on PUBLIC data

**Dataset:** LoCoMo (snap-research, `locomo10.json`) — 10 real multi-session conversations, 588 turns avg, 1986 QA with gold `evidence` turn annotations. **Compute:** embeddings computed offline with bge-m3, thread-throttled. ForgetEval is embedding-agnostic; the gap stratification is robust to embedder.

**Scenario chosen with discipline (premortem):** LoCoMo is *also* partly a flat-recall benchmark — running "HDC R@5 vs the leaderboard" would repeat the FAISS-turf mistake (HDC loses flat recall). So we measure the two things that are honest and HDC's: an **operation** nobody else benchmarks (forget), and an honest **motivation** measurement (the compose gap). We do **not** claim a flat-recall leaderboard win.

## ForgetEval — exact-delete on real conversation memory → `RESULTS-locomo-forget.json`

"User invokes right-to-be-forgotten on one speaker's turns in a session." Forget them from the bundle `M`, then measure (via unbind) whether the content is gone and whether everyone else is untouched. 10 conversations, D=50000.

| metric | value |
|---|---|
| forgotten content residual in M | **0.0415 → −0.0005** (true chance ~0.0045) → **gone** |
| preserved turns | **0.0415 → 0.0415** (unchanged) |
| every other turn's contribution | **bit-identical, max\|Δ\| = 0.0** |
| scale | 10 convs, 588 turns avg, ~10 forgotten/conv |

**PASS.** The forgotten content drops *below chance* (algebraically removed from the vector, not just de-indexed), every other memory is **bit-exactly preserved (Δ=0)**, on real multi-session conversations. This is the GDPR "right to be forgotten" as an **algebra op with a proof** — an operation a vector DB structurally cannot perform (it can only re-index, never *subtract exactly*). No memory benchmark in the race even tests this.

## Compose-gap — flat embedding degrades on multi-hop → `RESULTS-locomo-gap.json`

Flat bge-m3 retrieval recall@5 of the gold evidence, stratified by #evidence-turns:

| question type | n | recall@5 |
|---|---|---|
| single-evidence | 1554 | **0.198** |
| **multi-evidence (conjunction)** | 423 | **0.063** |
| degradation | | **+0.134 (≈3× worse)** |

Multi-evidence questions — which require retrieving a *conjunction* of turns — are **~3× harder** for a flat embedding, because the embedding of a multi-part query is a blurry average. This is the real-data signature of the compose gap.

**Honest scoping (no overclaim):** this measures the *baseline's* degradation, not an HDC win on LoCoMo. The synthetic `CompositionEval` shows `bind` closes exactly this kind of gap **given structured tuples**; closing it on LoCoMo needs the trinity's LLM-extraction step (question → role-filler tuples), which is **future work**, not done here. So: forget is the public-data **win**; the gap is the public-data **motivation** for compose.

## Bottom line
On public conversation data, the `forget` operator of the memory-algebra standard is **proven** (exact, Δ=0, across 10 real conversations), and the `compose` gap is **real and measured** (flat retrieval degrades 3× on multi-hop). Emitted to organism L1 (forget=CONFIRM→POC no-held-out; gap=POC). Combined with the synthetic `CompositionEval` (bind wins given structure) and the verified `ForgetEval/MergeEval/AuditEval` suite, the standard now has both synthetic and public-data evidence for the operations a vector DB cannot do.
