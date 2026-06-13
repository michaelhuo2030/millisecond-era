# hdc-mem — the memory operations a vector DB can't do

**Part of [millisecond-era](https://github.com/michaelhuo2030/millisecond-era)** — the deterministic-AI / on-chip HDC program. Pairs with the [`hdc-ops`](https://github.com/michaelhuo2030/hdc-ops) primitives library and the [HDC methodology](https://github.com/michaelhuo2030/millisecond-era/tree/main/hdc) (laws · arsenal · ops-method). `hdcmem_vsa.py` here is a self-contained mirror of the `hdc-ops` primitives so this folder runs on its own.

> **Memory is not search. It is an algebra.**

A vector DB (FAISS, ChromaDB, Pinecone, pgvector) and quantized indexes win
*nearest-neighbour recall* — recall-per-byte, decisively. **We concede that.** What no
vector DB can do — and what an HDC bundle does as *exact algebra* — are five operations:
**forget, undo, merge, audit, compose**. `hdc-mem` is the deterministic memory-algebra
layer that sits **on top of any store** (FAISS / ChromaDB / `.mv2` / pgvector own the
recall; we own the algebra). The whole memory is one vector:

```
M = Σ_i  bind(content_i, role_i)
```

`forget` is subtraction. `undo` is a byte-restore. `merge` is a separable sum. `audit` is
an unbind. `compose` is a conjunctive bind that stays clean where a flat embedding smears.
The first four are *physics* (exact, reversible). The fifth is *where flat embedding
breaks*. This is a new axis, not a recall contender: **memory you can prove you deleted.**

MIT (part of millisecond-era). Measured-only — every number below traces to a file in this repo.

---

## The five operators (a vector DB fails the first four by construction)

| Operator | What it does | Deterministic contract | Why a vector DB can't |
|---|---|---|---|
| **forget** | `M ← M − bind(c,r)` | removed item → chance; **every other item bit-identical (Δ=0)** | deletion is a side-effect of re-indexing, never a *proof* |
| **undo** | restore `M` bytes | **bit-exact (Δ=0)**, no log replay | WAL replay re-derives state; floating drift, re-embed |
| **merge / unmerge** | `M_A + M_B`; subtract one back out | both recoverable; cross-leak ≈ chance; **unmerge bit-exact** | merge = a rebuild; you can't *subtract* a federated peer back out |
| **audit** | `unbind(M, r) → content` | recover the filler at a role; no side graph | provenance lives in a *separate* system, not the vector |
| **compose** | `q = Σ bind(c_k, r_k)`; `argmax cos(q, M_j)` | conjunctive query stays clean as arity & distractors grow | the embedding of a conjunction is a **blurry average** |

Full spec: [`STANDARD.md`](STANDARD.md) (the five-operator standard) · [`SPEC.md`](SPEC.md)
(the engine + the race-feature comparison) · [`BENCHMARK-PLAN.md`](BENCHMARK-PLAN.md).

---

## Measured evidence (every number traces to a file)

### The 4/4 suite — the ops a vector DB can't pass · `eval/run_suite.py`

`ForgetEval` / `MergeEval` / `AuditEval` run live (deterministic, CPU, seconds);
`CompositionEval` reads the cached sweep. PASS criteria are exact/algebraic, not tunable
thresholds. A conventional vector DB fails the first three **by construction** and loses
the fourth at arity ≥ 2.

| Eval | Result | Source |
|---|---|---|
| **ForgetEval** | forgotten → 0.004 (chance ~0.009); neighbour **Δ=0**, recall preserved | `RESULTS-demo.json` |
| **MergeEval** | A & B both recoverable; cross-leak **0.017 ≈ chance**; unmerge **Δ=0** | `RESULTS-demo.json` |
| **AuditEval** | every role unbinds to its filler above chance; bit-exact provenance | `eval/run_suite.py` |
| **CompositionEval** | arity-2 conjunction: HDC **1.000** vs flat bge-m3 **0.898** | `eval/RESULTS-composition.csv` |

`RESULTS-demo.json` (D∈{2k,10k,30k} × seeds, independently re-implemented + verified by a
second agent): forget target **0.288 → 0.004**, neighbour Δ=0; merge cross-leak **0.017**,
unmerge Δ=0; undo Δ=0.

### compose — the scenario where HDC diverges · `eval/RESULTS-composition.csv`

N=2000 structured memories, conjunctive retrieval, P@1, 3 seeds. Both substrates get the
**same (role, filler) tuples**; HDC binds them, the baseline embeds the rendered query with
**bge-m3** and does cosine — exactly what a real RAG system does.

| scheme | arity-1 | **arity-2** | arity-3 |
|---|---|---|---|
| **fourier-HRR** | 1.000 | **1.000** | 1.000 |
| sparse-ternary | 1.000 | 0.997 | 0.987 |
| bipolar | 0.997 | 0.985 | 0.99 |
| **flat bge-m3** (real-RAG baseline) | 0.988 | **0.898** | 0.910 |

At single-attribute lookup (arity-1) it's a **tie**. At the **conjunction** the flat
embedding degrades to 0.90 while HDC holds 0.98–1.0 — a clean ~10-point win, fourier-HRR
*perfect*. The tell: fourier-HRR scored *chance* on flat semantic recall and *perfect* on
composition — **same weapon, opposite verdict by scenario**. The earlier "HDC loses to
FAISS" was the wrong scenario, not a weak tool. N-scaling (does the gap survive distractor
density) is in `eval/RESULTS-scale.csv` — fourier-HRR is **1.000 invariant from N=500 to
8000**. (We do *not* claim the advantage grows with N; the P@1 match-set inflates with N,
which is metric-leniency, not bge-m3 improving. The de-confounded signals are arity and the
fourier 1.000 line.)

### forget on real public data — LoCoMo · `eval/RESULTS-locomo.md`

Validated on **LoCoMo** (snap-research; 10 real multi-session conversations, 588 turns avg,
1986 QA), D=50000:

| metric | value |
|---|---|
| forgotten content residual in M | **0.0415 → −0.0005** (chance ~0.0045) → **gone** |
| every other turn's contribution | **bit-identical, max\|Δ\| = 0.0** |
| scale | 10 convs, ~10 forgotten/conv |

The forgotten content drops *below chance* — algebraically removed from the vector, not
de-indexed — and every other memory is bit-exactly preserved, on real conversations. This
is the GDPR "right to be forgotten" as an **algebra op with a proof**. No memory benchmark
in the race even tests it.

The same file measures the **compose gap** (honest motivation, not a claimed win): flat
bge-m3 recall@5 = **0.198** single-evidence vs **0.063** multi-evidence (n=1554/423) —
multi-hop is **~3× harder** for a flat embedding because the conjunction smears. `bind`
closes this *given structured tuples* (see CompositionEval); closing it on raw LoCoMo needs
the trinity's extraction step — see Limits.

---

## Quick start

```bash
# the four operations a vector DB can't pass (CPU, seconds; needs numpy + the hdc_ops arsenal on the path)
python3 eval/run_suite.py

# the differentiator demo with before/after ±SE numbers
python3 demo.py
```

```python
from hdc_mem import HDCMemStore

s = HDCMemStore(D=10000)
a = s.store("user prefers dark theme")     # M += bind(content, role)
b = s.store("user lives in Shanghai")
s.recall("dark theme", k=2)                # cosine readout (recall rides on the encoder)
s.forget_exact(a)                          # exact subtraction — a drops to chance, b untouched
s.undo()                                   # bit-restore the previous M
s.merge(other_store)                       # federated bundle; unmerge subtracts it back out, bit-exact
s.provenance(b)                            # unbind the slot — what's here, is it intact
```

`hdc-mem` is CPU-only / numpy-only. It rides on an HDC arsenal (`hdc_ops`: bind / unbind /
bundle / similarity); the recall front-end (the "eyes") is whatever encoder you feed it.

---

## Honest limits (read this)

- **Recall is parity, not a win.** Single-vector cosine is fine at small N; a tuned HNSW +
  reranker beats one bundle vector on large, messy corpora. We do **not** claim recall
  superiority — recall rides on the *encoder*. HDC's job is to make that recall *editable,
  separable, reversible, auditable*. (See SPEC: fourier-HRR scored chance on flat recall.)
- **compose-on-real-data needs trinity extraction (WIP).** The composition win assumes clean
  (role, filler) tuples. On raw unstructured text with no extraction you're back in
  flat-recall land (FAISS wins). The LoCoMo compose *gap* is measured; *closing* it on
  LoCoMo needs the LLM-extraction step (question → tuples) — that is future work, not done
  here. CompositionEval proves `bind` closes the gap *given* structure.
- **Capacity is bounded and honest.** A single bundle's recall cliff is at **N\* ≈ D/20
  distinct items** (measured 138 / 751 / 3482 @ D=2k/10k/50k). Beyond that, page the bundle
  or raise D. The wall is the distinct-atom *vocabulary*, not raw data volume.
- **For enumerable-exact fillers, a SQL `WHERE a AND b` also wins.** HDC's value is the
  open / fuzzy / partial / analogical conjunction a filter can't enumerate and a flat
  embedding smears.
- **Conflict is a screen, not a verdict.** `conflict()` flags candidates with an O(D) dot
  product; the judgment of true contradiction still wants an LLM.

---

## Positioning

`hdc-mem` is **not** a vector DB and **not** a recall-leaderboard contender. It is the
editable / reversible / auditable / composable memory layer — the deterministic core of the
trinity (LLM eyes + HDC core + deterministic code) — that runs on-device, owned, at µW,
where the cloud can't reach. It sits *on top of* your existing store: FAISS / ChromaDB /
`.mv2` / pgvector own the recall; we own the algebra.

The telos: memory you can prove you deleted, carry offline, merge without a server, and
audit. That is the right-to-be-forgotten as an algebra op, not a promise.

## License

MIT — see the [millisecond-era LICENSE](https://github.com/michaelhuo2030/millisecond-era/blob/main/LICENSE) (this lives inside that repo).
