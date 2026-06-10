# specs — how a hard physics question gets de-risked

Real experiment & demo specs from the project. The point isn't any single spec — it's the discipline behind them: **don't "run a giant sweep." Name the hypothesis → design the minimal experiment that de-risks it → measure only that → gate the spend.**

| File | What it is |
|---|---|
| **[exp-17-19-specs.md](exp-17-19-specs.md)** | Three **$0 simulations** (pipeline timing · thermal · hot-expert hit-rate) that close the remaining Stage-1 architecture hypotheses *before any silicon*. Each is a complete spec: mission → inputs → method → pseudo-code → output format → gate. Shows how to break a "validate a 5-die chiplet at 250K context" question into 3 independent ~500-line sims, gated by confidence. |
| **[DEMO-SPEC-talos-v3.md](DEMO-SPEC-talos-v3.md)** | The FPGA demo spec: turn a ternary transformer + HDC into something you can *watch run* on a cheap board — a real transformer using only add/subtract (0 multipliers), with live noise injection. One-liner → two story-lines → exact measurement list → staged rollout with a gate-0. |
| **[DEMO-ternary-hdc-on-fpga-SEED.md](DEMO-ternary-hdc-on-fpga-SEED.md)** | The seed behind that spec: board choice, the on-chip ternary **capacity derivation** (how many params fit in BRAM, from first principles), and the honest boundary — *FPGA proves the design, not product speed; there's no ReRAM here.* |

> Internal `[[wiki-links]]` in these files are provenance breadcrumbs to a private research repo — they won't resolve here. The published artifacts are self-contained.
