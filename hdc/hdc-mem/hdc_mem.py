#!/usr/bin/env python3
"""
hdc-mem — an HDC memory engine whose memory IS one vector.

The whole store is a single bundle  M = Σ_i  bind(content_i, role_i).
Every "lifecycle" feature that Amind / MemPalace / Memvid / Mirix solve with
heuristics (decay-GC, summaries, version chains, conflict LLM-calls) becomes an
EXACT algebraic operation on that one vector:

    store(content)      M += bind(content, role_id)          # append
    recall(query, k)    cosine(query_hv, stored content_hv)  # readout
    forget_exact(id)    M -= bind(content, role_id)          # exact subtraction
    undo()              restore previous bytes                # bit-exact
    merge(other)        M += other.M                          # federated bundle
    provenance(id)      unbind(M, role_id) -> content         # who/what is in here

This is NOT "smarter ML". The moat is PHYSICS / DETERMINISM:
  - forget is exact subtraction, not a decay-GC heuristic that hopes the item ages out
  - undo is bit-restore, not a best-effort rollback
  - merge of two federated stores is separable (subtract the other store back out and
    the bytes are identical — no cross-contamination, no retraining)
  - the same content always lands on the same bits (reproducible across processes)

Built on the project HDC arsenal (hdc_ops). CPU-only, numpy-only.
"""
from __future__ import annotations
import sys, os, json, hashlib, copy
import numpy as np

# --- VSA primitives (vendored standalone — see hdcmem_vsa.py) -------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hdcmem_vsa as hdc_ops        # bind/bundle/unbind/similarity/simhash
encoding = hdc_ops                  # simhash lives at top level of the vendored module


def _role_hv(role_id: int, D: int) -> np.ndarray:
    """A bipolar ±1 role key for a memory slot.

    The role is an *atom*: its identity lives entirely in the integer role_id, which
    seeds its own little rng. This is the SHARED-R rule applied correctly — role keys
    are item atoms (cheap, content-free), NOT projection encoders. Same role_id ->
    byte-identical key, any process.
    """
    rng = np.random.default_rng((role_id * 2654435761) % (2 ** 32))
    return np.where(rng.random(D) < 0.5, -1.0, 1.0).astype(np.float32)


class HDCMemStore:
    """A federated, editable HDC memory whose entire content is one D-dim vector M."""

    # ONE process-wide projection seed for the simhash encoder. Per-store identity does
    # NOT go in the projection R (that would leak an R per store, SHARED-R rule); it goes
    # in the raw content. Keeping this fixed means the SAME embedding always lands on the
    # SAME bits in every store and every process — reproducibility is the moat.
    ENCODER_SEED = 0

    def __init__(self, D: int = 10000, seed: int = 0):
        self.D = D
        self.seed = seed                      # store-namespace tag (NOT the projection seed)
        self.M = np.zeros(D, dtype=np.float32)
        # bookkeeping needed to support exact subtraction / provenance / undo.
        # NOTE: content_hv is kept so forget/provenance are exact. It is the SAME bytes
        # that were bundled in — no re-encoding drift.
        self._items: dict[str, dict] = {}     # id -> {role_id, content, content_hv}
        self._next_role = 1
        self._undo_stack: list[tuple[np.ndarray, dict, int]] = []

    # -- encoding ----------------------------------------------------------
    def _encode(self, content) -> np.ndarray:
        """content -> bipolar HV. Accepts a text string (hashed to a stable vector) or
        a float embedding (simhash). Real deployments feed embeddings; strings keep the
        demo self-contained without a model."""
        if isinstance(content, np.ndarray):
            return encoding.simhash(content.astype(np.float32), D=self.D,
                                    seed=self.ENCODER_SEED)
        # deterministic pseudo-embedding for a string: hash -> stable bipolar vector.
        h = hashlib.sha256(str(content).encode()).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], "little"))
        return np.where(rng.random(self.D) < 0.5, -1.0, 1.0).astype(np.float32)

    def _bound(self, content_hv: np.ndarray, role_id: int) -> np.ndarray:
        return hdc_ops.bind(content_hv, _role_hv(role_id, self.D))

    def _snapshot(self):
        """Push current state for undo(). Bit-exact: we copy the raw bytes."""
        self._undo_stack.append((self.M.copy(),
                                 copy.deepcopy(self._items),
                                 self._next_role))

    # -- public API --------------------------------------------------------
    def store(self, content) -> str:
        """Append a memory. M += bind(content_hv, role). Returns a stable id."""
        self._snapshot()
        role_id = self._next_role
        self._next_role += 1
        content_hv = self._encode(content)
        mem_id = "m%d" % role_id
        self.M = self.M + self._bound(content_hv, role_id)
        self._items[mem_id] = {"role_id": role_id, "content": content,
                               "content_hv": content_hv}
        return mem_id

    def recall(self, query, k: int = 5):
        """Return up to k (id, content, score) by cosine of query vs each stored
        content HV. The store is a bundle, so a stored content is recoverable by
        unbinding its role; here we score against the kept content_hv (exact)."""
        if not self._items:
            return []
        q_hv = self._encode(query) if not isinstance(query, np.ndarray) else self._encode(query)
        ids = list(self._items.keys())
        # recall against what is ACTUALLY in M: unbind each role out of M and compare to
        # the query. This proves the item is still in the bundle (forget drops it).
        scored = []
        for mid in ids:
            it = self._items[mid]
            rec = hdc_ops.unbind(self.M, _role_hv(it["role_id"], self.D))  # pull slot out of M
            scored.append((mid, it["content"],
                           hdc_ops.similarity(rec, q_hv, metric="cosine")))
        scored.sort(key=lambda t: -t[2])
        return scored[:k]

    def recall_score(self, mem_id: str) -> float:
        """Self-recall confidence of one item AS IT CURRENTLY SITS IN M.
        After forget_exact this drops to ~chance; for live items it is high.
        This is the measured quantity the demo prints."""
        it = self._items.get(mem_id)
        if it is None:
            # item was forgotten: probe M with the (role, content) it used to occupy.
            return float("nan")
        rec = hdc_ops.unbind(self.M, _role_hv(it["role_id"], self.D))
        return hdc_ops.similarity(rec, it["content_hv"], metric="cosine")

    def probe(self, role_id: int, content_hv: np.ndarray) -> float:
        """Probe M for an arbitrary (role, content) pair — used to show a FORGOTTEN
        item is gone even after its bookkeeping is removed."""
        rec = hdc_ops.unbind(self.M, _role_hv(role_id, self.D))
        return hdc_ops.similarity(rec, content_hv, metric="cosine")

    def forget_exact(self, mem_id: str) -> bool:
        """EXACT forget: M -= bind(content_hv, role). The item's contribution is
        algebraically removed — not decayed, not GC'd, not hoped-to-age-out. Other
        items are bit-for-bit untouched."""
        it = self._items.get(mem_id)
        if it is None:
            return False
        self._snapshot()
        self.M = self.M - self._bound(it["content_hv"], it["role_id"])
        del self._items[mem_id]
        return True

    def undo(self) -> bool:
        """Restore the previous state, bit-exact (M bytes + bookkeeping)."""
        if not self._undo_stack:
            return False
        self.M, self._items, self._next_role = self._undo_stack.pop()
        return True

    def merge(self, other: "HDCMemStore") -> None:
        """Federated bundle: M += other.M. Both stores' memories now live in one vector
        and stay separable — subtract other.M back out and you recover the original
        bytes. No retraining, no index rebuild, no cross-contamination."""
        assert other.D == self.D, "dimension mismatch"
        self._snapshot()
        self.M = self.M + other.M
        # re-home the other store's items into this namespace, keeping their own role keys
        # (role keys are global by construction, so they stay separable inside the union).
        for mid, it in other._items.items():
            new_id = "%s/%s" % (id(other) % 1000, mid)
            self._items[new_id] = copy.deepcopy(it)

    def unmerge(self, other: "HDCMemStore") -> None:
        """Exact inverse of merge: M -= other.M. Proves federation is separable."""
        self._snapshot()
        self.M = self.M - other.M
        for mid in list(self._items.keys()):
            if mid.startswith("%s/" % (id(other) % 1000)):
                del self._items[mid]

    def provenance(self, mem_id: str):
        """Lineage by unbind: pull the slot out of M with its role key and report how
        strongly the stored content is still present. This is the deterministic answer
        to 'what is in this slot and is it intact?' — no LLM, no separate graph store."""
        it = self._items.get(mem_id)
        if it is None:
            return None
        rec = hdc_ops.unbind(self.M, _role_hv(it["role_id"], self.D))
        return {"id": mem_id,
                "content": it["content"],
                "role_id": it["role_id"],
                "present_score": hdc_ops.similarity(rec, it["content_hv"], "cosine")}

    def conflict(self, mem_id_a: str, mem_id_b: str) -> float:
        """Conflict = determinism check: how aligned are two memories' content HVs.
        High cosine + opposite stated value = contradiction candidate. This replaces
        Amind's async LLM conflict-detection with an O(D) dot product."""
        a, b = self._items.get(mem_id_a), self._items.get(mem_id_b)
        if a is None or b is None:
            return float("nan")
        return hdc_ops.similarity(a["content_hv"], b["content_hv"], "cosine")


if __name__ == "__main__":
    s = HDCMemStore(D=10000)
    i1 = s.store("user prefers dark theme")
    i2 = s.store("user lives in Shanghai")
    print("stored:", i1, i2)
    print("recall 'theme':", s.recall("user prefers dark theme", k=2))
    print("self-score i1 before forget:", round(s.recall_score(i1), 3))
    s.forget_exact(i1)
    print("self-score i1 after forget :", s.recall_score(i1))  # nan (gone from bookkeeping)
    print("i2 still intact            :", round(s.recall_score(i2), 3))
    s.undo()
    print("after undo, i1 back        :", round(s.recall_score(i1), 3))
