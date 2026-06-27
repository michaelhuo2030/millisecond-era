# chip — the architecture & the model

Two layers live here:

1. **[`model-2026-06/`](model-2026-06) — the clean-room calculation model (newest).** A rules-first, single-source-of-truth
   rebuild of every chip number: density, throughput, energy, the ADC-free counter, all panel-cross-validated and graded.
   **Start at [`model-2026-06/00-STATE-OF-MODEL.md`](model-2026-06/00-STATE-OF-MODEL.md).** This is where the numbers are now
   most rigorous — it refines several conclusions in the ADR below (a single ledger; `t_vmm` on 5 legs; a paradigm-native
   `decode = min(timing, power)` throughput model; a corrected, readout-limited density ceiling; an honest ~2–4× H100 *system*
   efficiency number).
2. **[`ADR-v1-architecture.md`](ADR-v1-architecture.md) — the architecture decision record** (the v1 build decision, below).

---

**[ADR-v1-architecture.md](ADR-v1-architecture.md)** synthesizes the whole program into one v1 chip decision:

- **What to build first** — a 4B train-time-ternary {−1,0,+1} text model (~1 GB), **weights resident on-chip**, digital SPIKA binary-cell CIM with a counter readout and **no ADC**. (Not 8B, not 9B-Q4, not analog — each rejection argued.)
- **How to de-risk it cheaply** — the **M0 → M4 tape-out ladder**: FPGA twin (¥0) → open-PDK digital shuttle (¥0) → a single-die ReRAM test-tile (~¥50万) **only** once the free rungs are green. Each rung buys exactly one missing number before the next 10× of spend.
- **The honest blocker list** — single-layer density (the 60× open question), FPGA utilization, and **market validation as the now-binding constraint** (not the physics).

This is what *first-principles · measured-vs-projected · correction-in-public* looks like at chip scale — note the inline `⚠️ CORRECTED` / `DOWNGRADED` markers where earlier conclusions were walked back under harder analysis.

> It's a working ADR distilled from a private research repo: internal cross-references won't all resolve, and a **"Public version"** note marks where private expert-consultation attributions and partner-engagement specifics were removed — the technical analysis is unchanged. See [`../HOW-I-WORK.md`](../HOW-I-WORK.md).
