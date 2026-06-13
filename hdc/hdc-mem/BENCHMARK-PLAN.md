# hdc-mem — BENCHMARK PLAN (plan only, not run)

Goal: position hdc-mem honestly against the two public numbers the race brags about,
and prove our differentiators on the SAME datasets — **not** to beat them at raw
recall (we won't; recall rides on the encoder), but to show we match recall *while*
adding exact-forget / bit-undo / separable-merge that they cannot.

> Discipline: golden standard applies (≥4 encodings × ≥3 D × ≥2 sparsity × ≥3 seeds)
> for any HDC claim. Recall vs. a vector DB is an end-to-end claim, so it must be run
> end-to-end, not inferred from cosine smokes (Arsenal L2).

---

## Target 1 — LongMemEval (MemPalace's 96.6% R@5)

**Dataset.** LongMemEval (Wu et al., 2024). ~500 questions over long multi-session
chat histories; metric R@5 (is the gold evidence chunk in the top-5 retrieved).
MemPalace reports **96.6% R@5** in raw-verbatim mode (zero API), reproducible on an
M2 Ultra in <5 min — so this is a CPU-only, local target, perfect for us.

**Harness.**
1. Ingest each session's turns: `store(embed(turn))`, embedder = bge-m3 (the project's
   default recall front-end). One `HDCMemStore` per user/namespace.
2. For each question: `recall(embed(question), k=5)`, map hits back to source turns,
   compute R@5.
3. Page the bundle: with thousands of turns we exceed the N\*≈D/20 cliff, so shard into
   bundles of ≤ D/20 distinct items (PagedHVStore pattern) + a coarse cosine router, or
   raise D to 50k–100k. **Capacity is a known constraint — measure it, don't hide it.**

**Hypothesis (honest).**
- *Recall:* hdc-mem with bge-m3 + paged bundles lands **within a few points of, not
  above, MemPalace's 96.6%** — because both ultimately do cosine over embeddings, and a
  tuned HNSW + room-structure has the edge on a single bundle vector. **Prediction: 90–96%
  R@5.** If we're below 90%, the encoder/paging is the bottleneck, not the algebra.
- *Differentiator (the real point):* after building the index, run a **forget battery** —
  delete K random gold chunks with `forget_exact`, re-query: those questions drop to
  chance **with no R@5 regression on the others** (measured Δ=0 on untouched terms). No
  vector-DB baseline can show exact, provable deletion + intact neighbors. Add a
  **merge battery**: split users into two stores, `merge`, show both users' R@5 preserved
  and cross-user leak ~chance, then `unmerge` bit-exact.

**Baselines to run alongside:** raw ChromaDB (MemPalace's backend), bge-m3 + faiss HNSW.
Same embedder for all three so the comparison isolates the memory layer.

---

## Target 2 — LoCoMo (Memvid's +35% / +76% / +56%)

**Dataset.** LoCoMo (Maharana et al., 2024). Very long (~9k token) multi-session
conversations; question types include single-hop, **multi-hop**, and **temporal**
reasoning. Memvid reports **+35% accuracy, +76% multi-hop, +56% temporal** vs. a
traditional RAG baseline.

**Harness.**
1. Ingest conversation events with time: `store(bind(embed(event), time_key))` so the
   Time role is unbindable for temporal queries.
2. Single-hop QA: `recall(embed(q), k)` → feed top-k to the LLM reader.
3. Multi-hop: chain `recall` + role-bound relation edges `bind(src, dst, type)` (HVGraph
   Σ-bundle form — accumulate, read out by cosine; **never re-sign per edge**, Arsenal L12).
4. Temporal: query the Time role / use permute-sequence ordering.

**Hypothesis (honest).**
- *Single-hop:* parity-ish with Memvid; both are cosine retrieval + reader. Encoder-bound.
- *Multi-hop:* this is where we either earn it or don't. HDC **holds** verified relation
  edges (recover `type` at 0.977 @ D=30k, measured in the arsenal) but does **not discover**
  the hop structure — so multi-hop accuracy depends on the LLM proposing the chain and HDC
  executing/verifying it (trinity). **Prediction: parity to modest gain on multi-hop, and
  the gain is from deterministic edge-holding + exact composition, not from being a smarter
  retriever.** Do not pre-claim Memvid's +76%.
- *Temporal:* unbindable Time role gives exact "what at time t" — expect a real edge on
  temporal questions, the cleanest win for HDC here.
- *Differentiator battery:* same as LongMemEval — forget/undo/merge on the LoCoMo index,
  plus **counterfactual replace** ("the user later corrected fact X to Y") done in-place,
  which Memvid would have to re-ingest + re-index to do.

**Baseline to run alongside:** Memvid `.mv2` itself (it's open, Apache-2.0) on identical
chunks + embedder, so the recall comparison is apples-to-apples and the *only* thing that
differs is the memory algebra.

---

## What "winning" means for hdc-mem (set the ruler before running)

We are **not** trying to top the recall leaderboard — that ruler rewards the encoder and a
tuned ANN index, where we're parity at best. We win if:

1. **Recall within a few points** of MemPalace/Memvid on the same embedder (proves the
   bundle is a competent retrieval substrate, not a toy).
2. **Exact-forget / bit-undo / separable-merge / counterfactual-replace** demonstrated on
   the *real* benchmark indexes with Δ=0 and chance-floor drops — the four things no
   vector-DB memory in the race can do. **This** is the headline.

Lock these thresholds before any run. A recall number below 90% on LongMemEval or any
multi-hop *regression* on LoCoMo is a finding to report, not a number to tune green.
