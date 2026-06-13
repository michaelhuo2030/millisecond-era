# CompositionEval — the scenario where HDC diverges (honest writeup)

**Why this exists:** the first hdc-vec benchmark put HDC on FAISS's home turf (flat top-k semantic recall) and HDC lost on recall-per-byte. Michael's correction (2026-06-13): *"你的场景没用对... 处理非常复杂的信息和任务面前，会不一样."* This is the re-run on the **right** scenario — compositional / conjunctive / structured retrieval.

**Setup.** N structured memories, each = 4 (role, filler) pairs over roles {person, action, topic, time} with real-word vocab (30/18/28/12). A query asks for an *arity-k conjunction* (e.g. "person=Alice AND topic=refund"). Both substrates get the **same tuples** (the trinity: LLM eyes extract them); HDC **binds** them (`Σ bind(role,filler)`, cosine over corpus HVs), the baseline **embeds** the real-word query with **bge-m3** and does cosine over bge-m3 corpus embeddings — i.e. exactly what a real RAG system does. Metric: precision@1. Arsenal `bind`/`bundle`; 3 binding schemes × 3 D × 3 arities × 3 seeds + the flat baseline.

**Premortem guards honored:** real-word baseline (no strawman, no keyword-overlap cheat); same tuples to both; paired queries; capacity-safe; PoC-1-cell first; the gaussian/flat single-attr case is the control, not the verdict.

## Result 1 — arity sweep (N=2000, P@1, mean±SE/3 seeds) → `RESULTS-composition.csv`

| scheme | arity-1 | **arity-2** | arity-3 (≈unique needle) |
|---|---|---|---|
| **fourier-HRR** | 1.000 | **1.000** | 1.000 |
| bipolar | 0.997 | 0.985 | 0.99 |
| sparse-ternary | 1.000 | 0.997 | 0.987 |
| **flat bge-m3** | 0.988 | **0.898** | 0.910 |

- **arity-1 = TIE** (single lookup; both fine).
- **arity-2 = HDC win ~+10pts** (fourier-HRR 1.000 vs flat 0.898). The flat embedding of a conjunction is a **blurry average** of its parts → it retrieves things sharing *either* attribute.
- **arity-3 ≈ unique-match needle** (a 3-of-4 conjunction is almost always satisfied by exactly one memory, so this metric is *self-de-confounding*): HDC 0.99 vs flat 0.91 — the win is **real, not a metric artifact**.

## Result 2 — N-scaling at arity-2 (D=30000) → `RESULTS-scale.csv`

| N | fourier-HRR | bipolar | flat bge-m3 | gap |
|---|---|---|---|---|
| 500 | 1.000 | 0.992 | 0.835 | +0.165 |
| 1000 | 1.000 | 0.987 | 0.890 | +0.110 |
| 2000 | 1.000 | 0.985 | 0.898 | +0.102 |
| 4000 | 1.000 | 0.985 | 0.922 | +0.078 |
| 8000 | 1.000 | 0.995 | 0.920 | +0.080 |

- **fourier-HRR = 1.000, perfectly invariant across N=500→8000.** HDC bind retrieval is **untouched by distractor density** — the conjunction is algebraically exact regardless of corpus size. This is the clean, metric-independent claim.
- **The gap SHRINKS (+0.165→+0.08), and I do NOT claim "advantage grows with N."** Honest reason: the P@1 metric counts a hit against *all* memories satisfying the conjunction, and that match-set *inflates* with N, making the flat baseline artificially easier at large N. The flat number rising is a metric-leniency effect, not bge-m3 getting better at composition. The de-confounded signal is **arity** (Result 1) and **fourier invariance** (the 1.000 line).

## The tell (proves the "wrong scenario" point literally)
**fourier-HRR scored chance (0.004) on flat semantic recall** (`../hdc-vec/RESULTS-ROUND2-real.csv`) **and perfect (1.000) here.** Same arsenal weapon, opposite verdict — because it's a *binding* operator, wrong tool for flat similarity, right tool for composition. The earlier "HDC loses to FAISS" was the wrong scenario, not a weak method.

## Honest limits
- This is **structured/symbolic** retrieval (clean role-filler tuples). The win assumes the trinity actually extracts tuples; on raw unstructured text with no extraction, you're back in flat-recall land (FAISS wins).
- Fillers here are exact categorical. For **enumerable exact** fillers a SQL `WHERE a AND b` filter also wins — HDC's value is **open/fuzzy/partial/analogical** conjunctions a filter can't enumerate and a flat embedding smears.
- Capacity: each memory is its own HV (no bundle-cliff here); a single-bundle store still obeys N*≈D/20 (see hdc-mem SPEC).
- Emitted to organism L1 (POC; no held-out split — it's retrieval, not a learned model).

**Bottom line:** on flat recall HDC loses to FAISS; on **composition** HDC (fourier-HRR) is **perfect and size-invariant** where the flat embedding degrades. That is the `compose` operator of the memory-algebra standard — and the empirical core of "complex tasks are different."
