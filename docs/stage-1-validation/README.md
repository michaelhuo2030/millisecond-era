# Stage 1 Validation — Empirical Evidence

Summary JSON files from the six Stage 1 first-principles experiments. All reproducible from the methodology files in the parent repo.

| File | What it contains | Referenced in |
|---|---|---|
| `moe-routing-distribution.json` | DeepSeek V4-Flash Top-6 expert routing histogram across diverse prompts. Near-uniform distribution; top-32 experts cover only 20.8% of routings. | Article 2 finding #2 |
| `hot-expert-hit-rate-sweep.json` | Cache-size sweep (16–256 experts) under LRU, LFU, and static-top-K policies. No cache size under 256 reaches 99% hit rate. | Article 2 finding #2 |
| `pipeline-timing-refined.json` | 5-die × 8-layer × 16-tile pipeline timing sweep. Honest envelope: 5,000–15,000 tokens/sec at 250K context. | Article 2 finding #3 |
| `reram-crossbar-sim.json` | 128×128 4-bit MLC ReRAM crossbar Python simulation: cell variance, ADC noise, TOPS/W estimate. Result: ADC consumes 92% of tile energy in full-analog configuration. | Article 2 finding #1 |

## Methodology

These summaries are produced by Python scripts that anyone can re-run:

- `moe-routing-distribution.json` ← measured live during V4-Flash inference on the antirez `ds4-server` Q2_K build
- `hot-expert-hit-rate-sweep.json` ← derived from the routing measurement above; pure replay
- `pipeline-timing-refined.json` ← analytical model in NumPy; ~500 lines; sweep over context length × cache hit rate × clock frequency
- `reram-crossbar-sim.json` ← Monte Carlo over cell variance and ADC noise; ~200 lines

Full source scripts are tracked separately (the experiment harness is in active development). If you want a specific script for reproduction, open an issue on the repo.

## Honest gaps (per Article 2 §Honest gaps)

These four hypotheses are explicitly **not** closed by Stage 1:

1. 256×256 tile IR-drop margin — confidence 3.5/5. Awaits NeuroSim 28nm runs in Stage 2.
2. N+1 die fault-injection at scale — awaits Stage 3 FPGA emulation.
3. Full ANSYS Icepak thermal sign-off — Stage 4 silicon gate before any tape-out.
4. Software ecosystem / compiler stack — the deepest moat-work; Stage 5+, started in parallel.

We don't wave these away.
