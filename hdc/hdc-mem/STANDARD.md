# The Memory-Algebra Standard — five operations a vector DB cannot do

> **Memory is not search. It is an algebra.**
> Vector databases (FAISS, ChromaDB, Pinecone, Qdrant) and quantized indexes (turbovec) win *nearest-neighbour search* — recall-per-byte, decisively (measured: FAISS-PQ beats HDC ~8–20× on bytes). **We concede search.** What no vector DB can do — and what an HDC bundle does as *exact algebra* — are these five operations. This document defines them as a portable standard: an operator layer that sits on **any** store.

This is deliberately a *new axis*. You do not beat FAISS on recall; you define the operations recall can't express, and make them a benchmark everyone else fails.

---

## The five operators

Let a memory store be one hypervector `M = Σ_i bind(content_i, role_i)` (bundle of bound pairs).

| Operator | Signature | Deterministic contract | Vector DB equivalent | Why a vector DB can't |
|---|---|---|---|---|
| **forget** | `M ← M − bind(c,r)` | removed item's recall → chance; **every other item's contribution bit-identical (Δ=0)** | decay-GC / TTL / re-index | deletion is a *side effect of re-indexing*, never a proof; can't show "exactly this, nothing else" |
| **undo** | restore `M` bytes | **bit-exact (Δ=0)**, no log replay | WAL replay re-derives state | re-derivation ≠ restoration; floating drift, re-embed |
| **merge / unmerge** | `M_∪ = M_A + M_B`; `M_∪ − M_B` | both stores recoverable from union; cross-leak ≈ chance; **unmerge bit-exact** | re-ingest A∪B, rebuild HNSW | merge is a rebuild; you cannot *subtract* a federated peer back out |
| **audit / provenance** | `unbind(M, r) → content` | recover the filler at a role; self-contained, no side graph | metadata join / KG | provenance lives in a *separate* system, not the vector itself |
| **compose** | `q = Σ bind(c_k, r_k)`; `argmax cos(q, M_j)` | conjunctive query stays algebraically clean as arity & distractor-density grow | embed-query-text + cosine | the embedding of a conjunction is a **blurry average** → degrades at composition |

The first four are *physics* (exactness/reversibility). The fifth is *where flat embedding breaks* — the regime this whole standard is built to own.

---

## Measured evidence (this repo, 3-seed ±SE, independently verified, emitted to organism L1)

**forget / merge / undo** — `eval/RESULTS-demo.json`, verified by an independent agent:
- forget: target recall **0.288 → 0.004** (chance 0.009); neighbour bound-term **Δ=0**, neighbour recall preserved.
- merge: A & B both recoverable in union; cross-leak **0.017 ≈ chance**; unmerge **Δ=0**.
- undo: **Δ=0** bit-exact. Holds across D∈{2k,10k,30k} × 3 seeds.

**compose** — `eval/RESULTS-composition.csv` (N=2000, conjunctive retrieval, P@1, 3 seeds):
| | arity-1 | **arity-2** | arity-3 |
|---|---|---|---|
| **fourier-HRR** (proper binding) | 1.000 | **1.000** | 1.000 |
| bipolar / sparse-ternary | ~0.99 | 0.985–0.997 | ~0.99 |
| **flat bge-m3** (real-RAG baseline) | 0.988 | **0.898** | 0.910 |

At single-attribute lookup (arity-1) it's a **tie**. At the **conjunction** the flat embedding degrades to 0.90 while HDC holds 0.98–1.0 — a clean ~10-point win, fourier-HRR *perfect*. (N-scaling — does the gap *widen* with distractor density — in `eval/RESULTS-scale.*`.)

> The tell: **fourier-HRR scored *chance (0.004)* on flat semantic recall, and *perfect (1.000)* on composition.** Same weapon, opposite verdict by scenario. The earlier "HDC loses to FAISS" was the wrong scenario, not a weak tool.

---

## Public-data evidence (LoCoMo) — `eval/RESULTS-locomo.md`

Validated on **LoCoMo** (snap-research; 10 real multi-session conversations, 588 turns avg, 1986 QA). Embeddings computed offline with bge-m3, thread-throttled.

- **forget on real conversations:** delete a speaker's turns → forgotten content residual **0.0415 → −0.0005** (chance ~0.0045, *gone from the vector*), every other turn **bit-identical (Δ=0)**, across all 10 conversations. The GDPR right-to-be-forgotten as an algebra op, proven on public data. *No memory benchmark in the race tests this.*
- **compose on real conversations (demonstrated):** binding one extractable structural key (the speaker — named in ~91% of questions) lifts retrieval recall@5 from **0.198→0.511 single (2.6×)** and **0.063→0.298 multi (4.7×)**. HDC soft-compose **matches a hard speaker-filter** (0.511/0.298) as one composable, soft op. Honest scope: on a single 1-bit key it *matches* explicit filtering (not beats it); its differentiation — AND-ing multiple constraints in one vector + soft robustness to mis-detection — needs a richer trinity extraction (more roles). See `eval/RESULTS-locomo-compose.md`.

So on public conversation data, **forget** is proven exact (Δ=0) and **compose** turns extractable structure into a 2.6–4.7× recall gain flat retrieval can't reach — both operators no vector DB exposes.

## The benchmark suite (the operations nobody else passes)

Run `python3 eval/run_suite.py` (CPU, minutes):

- **ForgetEval** — store K items, forget one, assert: forgotten→chance, others Δ=0, recall preserved. Pass = exact.
- **MergeEval** — merge two federated stores, assert both recoverable + cross-leak≈chance + unmerge Δ=0.
- **AuditEval** — unbind every role, assert filler recovery above chance; bit-exact provenance.
- **CompositionEval** — conjunctive P@1 vs a flat-embedding baseline across arity & N; assert HDC ≥ flat + the arity-1 tie / arity-2 win shape.

A conventional vector DB **fails ForgetEval/MergeEval/AuditEval by construction** (no exact subtraction, no separable merge, no in-vector provenance) and **loses CompositionEval** at arity≥2.

---

## Positioning

`hdc-mem` is **not** a vector DB and **not** a recall-leaderboard contender. It is the **editable / reversible / auditable / composable memory layer** — the deterministic core of the trinity (LLM eyes + HDC core + deterministic code) — that runs **on-device, owned, at µW**, where the cloud can't reach. It sits *on top of* your existing store (FAISS/ChromaDB/.mv2/pgvector own the recall; we own the algebra).

**Telos:** 照护人本身 — memory you can prove you deleted, carry offline, merge without a server, and audit. That is the GDPR "right to be forgotten" as an algebra op, not a promise.

*MIT (part of [millisecond-era](https://github.com/michaelhuo2030/millisecond-era)). Measured-only; every headline traces to a CSV/JSON artifact in this repo.*
