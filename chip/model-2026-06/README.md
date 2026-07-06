# chip model — 2026-06 clean-room convergence

> **Public archive note, 2026-07-07:** this folder remains the public physics snapshot and derivation record. The
> current product/outreach boundary is now **C1** — 0.1B / 0.3B / 1B / bounded 3B, speed-first buyer metrics, and
> provisionable resident model slots. Start there for public positioning:
> [`../C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md`](../C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md).

A from-scratch, **rules-first** rebuild of the ternary ReRAM-CIM chip calculation system: methodology locked
*before* any number, every number grounded *before* use, each checked one-by-one, and every load-bearing claim
cross-validated by a multi-engine panel (codex + kimi + minimax + glm). It supersedes the earlier scattered
chip notes — which were valuable but had accreted on stale anchors (180nm-prototype numbers, systolic tok/s,
optimistic-ceiling densities).

**Start here → [`00-STATE-OF-MODEL.md`](00-STATE-OF-MODEL.md)** — the one-page convergence: every verified finding,
its evidence-legs, the open 🔴 GAPs, and the doc map.

## What's in this folder

| file | what |
|---|---|
| [`00-STATE-OF-MODEL.md`](00-STATE-OF-MODEL.md) | the convergence one-pager (read first) |
| [`01-RULES.md`](01-RULES.md) | the locked methodology — **the bidirectional conclusion gate** (guards both optimistic drift and harsh pessimism), node/paradigm guards, triangulation rules |
| [`04-LEDGER.md`](04-LEDGER.md) | **the single source of truth** — every number, graded 🟢/🟡/🔴/⚫, with its source |
| [`05-engine.py`](05-engine.py) | the parametric model (density cascade L4/L6 + throughput L7); reads the ledger, self-audits against it. `python3 05-engine.py` |
| [`08-ARCHITECTURE-VARIANTS.md`](08-ARCHITECTURE-VARIANTS.md) | density ceiling, the levers, the node ladder 28→7nm, the two-chip (vertical-3D) question |
| [`09-THROUGHPUT-CYCLE.md`](09-THROUGHPUT-CYCLE.md) | decode speed + response-cycle heartbeat, 0.1B→3B, edge vs box |
| [`10-PERIPHERY-BINDING-STUDY.md`](10-PERIPHERY-BINDING-STUDY.md) | where the digital periphery actually binds us (4-leg) |
| [`11-COUNTER-STUDY.md`](11-COUNTER-STUDY.md) | the ADC-free counter readout — is it the bottleneck? (4-leg + transient SPICE-class model) |
| [`03-GROUNDING/`](03-GROUNDING) | per-number derivations for the four load-bearing numbers: `t_vmm`, `energy-tops-w`, `density-cim-core`, `counter-bits` |

## The headline (one paragraph)

A **ternary ReRAM-CIM** chip: weights are **resident physical conductances**; the matrix-vector multiply happens by
**analog physics** (Ohm + Kirchhoff — the whole matrix in one settle), read out **ADC-free** by a per-2-column
differential up/down counter. The moat is **resident low-latency inference in a power envelope GPUs cannot occupy**
(a GPU can't run at µW; a digital NPU can neither hold the model resident nor compute in-memory). **Density is the
gate** (fit 0.1B in a manufacturable die); **speed/latency is the first buyer comparison axis, then power/local/privacy
decide deployment fit**. The
FPGA work elsewhere in this repo is an **execution-credibility demo** (it proves the ternary model runs correctly on
real silicon) — *not* the product (it's digital and systolic; it has none of the analog in-memory speed/energy).

What the last week added, vs the earlier [`../ADR-v1-architecture.md`](../ADR-v1-architecture.md): a single-source ledger;
`t_vmm` now on **5 convergent legs** (the 60–190 ns "naive-ramp" scare is dead); a paradigm-native throughput model
(`decode = min(timing, power)`, single-stream `1/(D·t_vmm)`, not systolic); the counter shown **not** to be the hard
bottleneck; a corrected density ceiling (readout-limited, not cell-limited); and an honest **system** efficiency number
(~2–4× H100, where an earlier draft had mislabeled the *core* number as system).

---

> ### Note on this public version
> This is a clean-room research record distilled from a private repo. Two things follow:
> - **Internal cross-references won't all resolve** — links to files not published here (device-data sourcing map,
>   some grounding notes, the HTML calculator) are intentionally omitted.
> - **A private partner/sourcing layer was genericized** — a specific domestic ReRAM fab is referred to as
>   "a domestic ReRAM fab," and partner-engagement / data-sourcing specifics and individual names were removed.
>   The technical analysis, numbers, grades, and corrections are **unchanged**.
>
> The voice is deliberately self-correcting: inline `⚠️ CORRECTED` / `SUPERSEDED` / `panel caught` markers show where an
> earlier conclusion was walked back under harder analysis — in both directions. That is the method, not an afterthought.
> See [`../../HOW-I-WORK.md`](../../HOW-I-WORK.md).
