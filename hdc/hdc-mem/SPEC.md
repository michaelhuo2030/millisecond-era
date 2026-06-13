# hdc-mem — SPEC

An HDC memory engine where **the entire memory is one vector**:

```
M = Σ_i  bind(content_i, role_i)
```

Every lifecycle feature the conventional memory race (Amind #6, MemPalace #34,
Memvid #36, Mirix #33) solves with a *heuristic* becomes an **exact algebraic
operation** on M. The differentiator is not "smarter recall" — on plain semantic
retrieval HDC is at best parity with a vector DB. The differentiator is **physics /
determinism**: forget is subtraction, undo is bit-restore, merge is separable, the
same content always lands on the same bits.

---

## Amind lifecycle feature → the HDC operation that does it better

| Amind / race feature | How they do it | HDC operation | Better, parity, or worse | Why |
|---|---|---|---|---|
| **Forget / GC** | `ForgetEngine`: decay model + background GC heuristic — *hopes* stale items age out, may evict the wrong one, eventually | `M -= bind(content, role)` (`forget_exact`) | **BETTER (exact)** | Removes exactly one item's contribution, immediately, with a proof: its recall drops to chance (**measured 0.288 → 0.004**, chance 0.009) while every other item's bound term in M is **bit-identical (Δ=0)**. This is the GDPR "right to be forgotten" as an algebra op, not a promise. |
| **Version chain / undo** | version chain + WAL replay (Amind, Memvid `.mv2` WAL) — rollback re-derives state from a log | restore previous M bytes (`undo`) | **BETTER (bit-exact)** | Undo of a forget/store is **max\|Δ\|=0** (measured). No log replay, no re-embedding, no "best effort." |
| **Federated merge** | merge two memory DBs = re-ingest + rebuild HNSW index; no clean separation | `M += other.M` (`merge`), `M -= other.M` (`unmerge`) | **BETTER (separable)** | Two stores live in one vector, both recoverable (**measured ~0.20 each in union**), cross-leak ~chance (**0.017**), and subtracting one store back out is **bit-exact (Δ=0)**. No retraining, no index rebuild. This is what enables on-device federation where the cloud can't reach. |
| **Conflict detection** | async LLM call: "do these two memories contradict?" (Amind Stage-2, MemPalace `fact_checker.py`) | `cos(content_a, content_b)` (`conflict`) — high alignment + opposite stated value = contradiction candidate | **PARITY / cheaper** | An O(D) dot product flags *candidates* deterministically and for free; the *judgment* of true contradiction still wants an LLM. We replace the expensive screen, not the semantic call. Honest: this is a filter, not a verdict. |
| **Provenance / lineage** | Graph Store + blood-line propagation graph (Amind), SQLite KG with validity windows (MemPalace) | `unbind(M, role)` → recover content (`provenance`) | **PARITY (and self-contained)** | Lineage of "what occupies this slot and is it still intact" is one unbind, no side graph DB. For *multi-hop* relational lineage (A caused B caused C) an explicit role-bound chain or a graph still helps — HDC holds the edges (`bind(src,dst,type)`) but doesn't *discover* them. |
| **Semantic recall** | HNSW + keyword + graph + time-decay + importance, 5-way RRF fusion (Amind); raw-verbatim + palace structure (MemPalace) | `cos(query, content)` over the bundle (`recall`) | **PARITY (often worse at scale)** | Single-vector cosine is fine at small N; a tuned HNSW + reranker wins on large, messy corpora. **We do NOT claim recall superiority.** Our recall rides on the *encoder* (the "eyes"); HDC's job is to make that recall **editable, separable, reversible, auditable** — the things a vector DB can't do. |
| **Write gate / dedup** | `WriteGate`: dup detection + quality score before insert | `cos(new, existing) > τ` set-membership check | **PARITY** | Same idea, cheaper primitive. No moat here. |
| **Importance weighting** | usage-count importance score in the fusion | `weighted_bundle` — heavier items contribute more to M | **PARITY** | Weight is a scalar on the bundle term. Straightforward, not a differentiator. |
| **Time / staleness** | time-decay weight + staleness filter; Memvid Time Index | `bind(content, time_key)` + permute for sequence | **PARITY (+ exactness)** | Time becomes a role you can unbind to query "what at time t" exactly; decay is optional, not the only knob. |
| **Counterfactual / "replace X with Y"** | not offered (would require delete + re-ingest + re-index) | `M - bind(c_old,r) + bind(c_new,r)` | **BETTER (only we have it)** | Surgical replace-in-place: old content drops to chance, new content present, **rest unchanged** (algebra verified in `monako-gift` editable-vision suite, 1.000 @ D=30k). |

---

## Where HDC is genuinely better vs. parity (be honest)

**Genuinely better — the moat (all four are PHYSICS, verified MEASURED):**
1. **Exact forget** — subtraction, drops to chance, neighbors bit-identical. (decay-GC cannot prove removal)
2. **Bit-exact undo** — Δ=0. (WAL replay re-derives, ours restores)
3. **Separable federated merge** — Δ=0 on unmerge, ~chance cross-leak. (vector-DB merge = re-ingest + rebuild)
4. **Surgical counterfactual replace** — in-place, rest unchanged.

These are what let memory live **on-device, owned, auditable, deletable** — Michael's
telos of *照护人本身 (taking care of the human being where the cloud can't reach)*.

**Parity (do not oversell):**
- Semantic recall quality (rides on the encoder; a tuned HNSW + reranker beats a single
  bundle vector on large messy corpora).
- Conflict *judgment* (we cheapen the screen; the LLM still rules).
- Multi-hop relational lineage *discovery* (HDC holds verified edges, doesn't discover them).

**Honest limits (capacity law, from the arsenal):**
- A bundle's recall cliff is at **N\* ≈ D/20 distinct items** (measured 138/751/3482 @
  D=2k/10k/50k). Beyond that, page the bundle or raise D. This is a bounded, honest
  working window — not infinite memory.
- The wall is the **distinct-atom count (vocabulary)**, not raw data volume.

---

## Trinity placement

hdc-mem is the **HDC reversible core** of the trinity, not the whole system:
- **LLM = eyes/hands** — produces the content embedding (the encoder) and reads results.
- **HDC = reversible memory core** — this engine: store/forget/undo/merge/provenance as algebra.
- **Deterministic code** — the audit log, the role-id namespace, the conflict screen.

The cloud is a **complement**, not a competitor: heavy semantic search and long-form
reasoning can stay in the cloud; hdc-mem owns the *editable, private, on-device,
deletable* memory the cloud structurally cannot give you.

---

## API (see `hdc_mem.py`)

```python
s = HDCMemStore(D=10000)
mid  = s.store(content)            # content = text str or float embedding -> id; M += bind(content, role)
hits = s.recall(query, k=5)        # [(id, content, cosine), ...]
s.forget_exact(mid)                # M -= bind(content, role); exact
s.undo()                           # bit-restore previous M
s.merge(other_store)               # M += other.M; separable
s.unmerge(other_store)             # M -= other.M; bit-exact inverse
s.provenance(mid)                  # unbind slot out of M; present_score
s.conflict(mid_a, mid_b)           # cosine alignment screen
```
