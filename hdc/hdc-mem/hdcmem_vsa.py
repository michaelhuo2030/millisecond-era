"""
hdcmem_vsa.py — the minimal VSA primitives hdc-mem needs, vendored standalone (MIT).
(Mirrors the public hdc-ops library: github.com/michaelhuo2030/hdc-ops)

Faithful to the source arsenal these were lifted from:
  bind / unbind = elementwise product (self-inverse: bind(bind(a,b),b)=a)
  bundle        = superposition (sum); result is similar to every input
  similarity    = cosine / hamming / dot / overlap
  simhash       = sign of a fixed random projection (the default real→HV encoder)

SHARED-R rule (load-bearing): the projection R is cached on a VALUE key (d, D, seed), so the same
(d, D, seed) yields a byte-identical R on every call and in every process. Pass ONE experiment-level
seed; put item identity in the raw x, NOT in the seed — a fresh seed per item just churns the cache.
"""
import numpy as np
from typing import Literal

__all__ = ["bind", "unbind", "bundle", "similarity", "normalize", "simhash"]


def normalize(h: np.ndarray) -> np.ndarray:
    """Scale to unit length (direction only) — the pre-step for cosine."""
    norm = np.linalg.norm(h, axis=-1, keepdims=True)
    norm = np.where(norm == 0, 1.0, norm)
    return h / norm


def bind(h1: np.ndarray, h2: np.ndarray) -> np.ndarray:
    """bind ⊗ : elementwise product. Self-inverse — bind(bind(a, b), b) == a.
    'document X's author is Michael' → bind(doc_hv, michael_hv)."""
    return h1 * h2


def unbind(h_bound: np.ndarray, h_role: np.ndarray) -> np.ndarray:
    """unbind ≡ bind (self-inverse): recover content from bind(content, role)."""
    return h_bound * h_role


def bundle(hvs) -> np.ndarray:
    """bundle ⊕ : superpose a list/array of HVs (sum). Result is similar to every input.
    forget = subtract one bound term back out; merge = add two bundles."""
    return np.sum(np.asarray(hvs), axis=0)


def similarity(h1: np.ndarray, h2: np.ndarray,
               metric: Literal["cosine", "hamming", "dot", "overlap"] = "cosine") -> float:
    """How alike two HVs are."""
    if metric == "cosine":
        n1, n2 = normalize(h1), normalize(h2)
        return float(np.dot(n1.ravel(), n2.ravel()))
    if metric == "hamming":
        return float(np.sum(h1 != h2) / h1.shape[-1])
    if metric == "dot":
        return float(np.dot(h1.ravel(), h2.ravel()))
    if metric == "overlap":
        return float(np.mean(np.sign(h1) == np.sign(h2)))
    raise ValueError(f"Unknown metric: {metric}")


_R_CACHE: dict = {}


def _fixed_R(d: int, D: int, seed: int, scale: float = 1.0) -> np.ndarray:
    """Deterministic Gaussian projection R, cached on a VALUE key (never id(rng)).
    Same (d, D, seed) → byte-identical R, every call, every process (the SHARED-R rule)."""
    key = (int(d), int(D), int(seed), float(scale))
    R = _R_CACHE.get(key)
    if R is None:
        R = np.random.default_rng([int(seed), int(d), int(D)]).normal(0, scale, (d, D))
        _R_CACHE[key] = R
    return R


def simhash(x: np.ndarray, D: int = 10000, seed: int = 0) -> np.ndarray:
    """Random projection + sign: float x (..., d) → ±1 hypervector (..., D). The default encoder.

    1. project x through a fixed random R (d → D); 2. take the sign per dimension.
    Two similar inputs → similar ±1 patterns (Johnson–Lindenstrauss concentration).
    """
    d = x.shape[-1]
    R = _fixed_R(d, D, int(seed))
    x_norm = x / (np.linalg.norm(x) + 1e-8)
    projection = np.dot(x_norm, R)        # np.dot not @ — Accelerate's @ spuriously NaNs on macOS
    h = np.sign(projection)
    h[h == 0] = 1.0
    return h
