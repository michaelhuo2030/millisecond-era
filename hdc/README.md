# HDC research — the laws, the arsenal, the method

This folder is the **research discipline** behind the Hyperdimensional Computing (HDC) module of [millisecond-era](../README.md). It is not a library — the library is **[hdc-ops](https://github.com/michaelhuo2030/hdc-ops)** (clean operators), with **[hdc-neon](https://github.com/michaelhuo2030/hdc-neon)** (NEON-SIMD, ~89×) and the **[torchhd ReRAM-CIM backend](https://github.com/michaelhuo2030/torchhd/tree/reram-cim-backend)**.

What lives here is the thing that's harder to copy than code: **how we decide what's true.**

## The three documents

| File | What it is |
|---|---|
| **[HDC-LAWS-REGISTRY.md](HDC-LAWS-REGISTRY.md)** | The locked laws (L0–L19), each with its **provenance** (which experiment earned it) and its **enforcement** (how it becomes a default or a gate the next experiment *can't* skip). The boundary law L1 — *HDC's algebra wins when structure is GIVEN/clean, ties learned embeddings when structure must be DISCOVERED from messy data* — is the master thread. |
| **[HDC-WEAPONS-ARSENAL.md](HDC-WEAPONS-ARSENAL.md)** | The computing-stack view: 6-instruction ISA (cos / bind / bundle / permute / unbind / weighted_bundle) → encoding shelf → standard library → orchestration → applications. A map of what exists so we never reinvent a weapon. |
| **[HDC-EXPERIMENT-OPS-METHOD.md](HDC-EXPERIMENT-OPS-METHOD.md)** | How an experiment actually runs: pre-mortem gate → 1-cell PoC → heavy compute → audit-before-verdict. |

## Why publish the method and not just the wins

Because the method *is* the moat. Two laws in the registry are load-bearing and uncomfortable on purpose:

- **L4 — N=1 is a PoC, not a result.** Golden Standard: before claiming HDC fails (or wins) any property, sweep **≥4 encodings × ≥3 D × ≥2 sparsity × ≥3 seeds**. A single config that fails means the *tool* was inadequate, not that the property is absent.
- **L17 — MEASURED ≠ EXPECTED (anti-fabrication).** A number enters a doc only if a saved artifact (CSV/JSON/run-log) backs it *this turn*. The registry documents a real incident where plausible-looking numbers were written before the run finished, were caught by forensics, purged, and re-run for real. *A fabricated number is more dangerous than a crash — it looks true and survives.*

The registry deliberately keeps its **deflations** visible (L18/L19 are CANDIDATE, not locked; several dramatic claims were walked back under harder measurement). That honesty — verdicts held to the same bar whether they confirm or refute — is the point.

## Honest scope

- These are **research laws and methodology**, distilled from a private monorepo. Internal cross-references (experiment filenames, `NN-folder/` paths, memory IDs) are provenance breadcrumbs and **won't all resolve in public** — they point to where each law was earned, not to shipped code. The shipped code is hdc-ops.
- The full raw evidence ledger (every verdict with its CSV path) is kept private pending a per-row review; the **LAWS-REGISTRY is the readable, vetted form** of it.
- HDC here is a **substrate** claim (deterministic, reversible, µW, on-chip — see the boundary law), **not** a "HDC beats neural nets at everything" claim. L1 says exactly where it does and doesn't.

*合抱之木，生于毫末。*
