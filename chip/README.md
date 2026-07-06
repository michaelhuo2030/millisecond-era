# chip — public architecture, model, and C1 boundary

Three layers live here:

1. **[`C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md`](C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md) — the current public product boundary.**
   This is the cleanroom-derived C1 update: 0.1B / 0.3B / 1B / bounded 3B, speed-first buyer metrics,
   provisionable resident model slots, write/verify/drift support tax, and the public-safe red lines.
2. **[`model-2026-06/`](model-2026-06) — the archived public clean-room calculation model.** A rules-first, single-source-of-truth
   rebuild of every chip number: density, throughput, energy, the ADC-free counter, all panel-cross-validated and graded.
   **Start at [`model-2026-06/00-STATE-OF-MODEL.md`](model-2026-06/00-STATE-OF-MODEL.md)** when you want the physics
   snapshot and old derivations. Product/outreach wording now starts from the C1 public brief above.
3. **[`ADR-v1-architecture.md`](ADR-v1-architecture.md) — the architecture decision record** (the v1 build decision, below).

Current public rule: lead with **speed and latency on a real buyer loop**, not TOPS. Then state local/private/power,
then rewritable resident model slots. Keep measured FPGA evidence, cleanroom-modeled ASIC targets, and future dreams
separate.

Whole-picture rule: **C1 is the bridgehead, not the ceiling.** Public product wording starts at 0.1B / 0.3B / 1B /
bounded 3B because that is the first useful and falsifiable buyer wedge. 8B / 32B / 100B-class work belongs to C2/C3
frontier research until C1 evidence exists.

---

**[ADR-v1-architecture.md](ADR-v1-architecture.md)** synthesizes the whole program into one v1 chip decision:

- **Historical v1 decision now superseded for product wording** — the ADR's first target was a 4B train-time-ternary {−1,0,+1} text model (~1 GB), **weights resident on-chip**, digital SPIKA binary-cell CIM with a counter readout and **no ADC**. The current public product boundary is the C1 ladder above: 0.1B / 0.3B / 1B / bounded 3B.
- **How to de-risk it cheaply** — the **M0 → M4 tape-out ladder**: FPGA twin (¥0) → open-PDK digital shuttle (¥0) → a single-die ReRAM test-tile (~¥50万) **only** once the free rungs are green. Each rung buys exactly one missing number before the next 10× of spend.
- **The honest blocker list** — single-layer density (the 60× open question), FPGA utilization, and **market validation as the now-binding constraint** (not the physics).

This is what *first-principles · measured-vs-projected · correction-in-public* looks like at chip scale — note the inline `⚠️ CORRECTED` / `DOWNGRADED` markers where earlier conclusions were walked back under harder analysis.

> It's a working ADR distilled from a private research repo: internal cross-references won't all resolve, and a **"Public version"** note marks where private expert-consultation attributions and partner-engagement specifics were removed — the technical analysis is unchanged. See [`../HOW-I-WORK.md`](../HOW-I-WORK.md).
