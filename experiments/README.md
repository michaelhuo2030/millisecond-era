# experiments — prove the thesis yourself

Two small, **runnable** artifacts that test the chip thesis directly. Run them; read what they print on your own machine.

| File | What it tests |
|---|---|
| **[ternary_qat_cifar10.py](https://github.com/michaelhuo2030/millisecond-era/blob/main/experiments/ternary_qat_cifar10.py)** | Trains a small CNN three ways on CIFAR-10 — `fp32` / **train-time ternary** (BitNet-style straight-through estimator) / **post-hoc ternary** — and measures the gap. The core claim made touchable: *post-hoc ternary collapses; train-time ternary is near-lossless.* The STE code is a teaching tool for "how do you make {−1, 0, +1} learnable?" Runs on a Mac (MPS). |
| **[ternary_vs_int8_reram_noise.py](https://github.com/michaelhuo2030/millisecond-era/blob/main/experiments/ternary_vs_int8_reram_noise.py)** | Injects ReRAM conductance noise (sweeps σ) and measures level-flips + cosine corruption on real ternary vs INT8 weights. The chip's core device-risk (R1), made runnable. |

**Honest scope:** these are small-scale PoCs that isolate a *mechanism*, not product benchmarks. The numbers are whatever the code prints on your hardware — that's the point (`MEASURED`, on your machine, not asserted). The end-to-end measured versions (BitCPM-8B perplexity under the SPIKA readout, etc.) live in the articles and the evidence work; these two let you feel the mechanism in ~80 lines.
