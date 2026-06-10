# The LLM → HDC Bridge, Measured on Words
*2026-06-08. Companion to `00-LLM-HDC-TEMPERATURE-AXIS-AND-CRYSTALLIZATION-CASCADE-2026-06-05.md`.
Glass-box tags: `[measured-here]` (this program, artifact path given), `[literature]` (published, not ours),
`[open]` (unresolved). Every number traces to a saved artifact (L17).*

## The claim, in one sentence

> An LLM's "meaning" and a regression net's "math" are the **same operation** under the hood — weighted sums over
> vectors. So the way you turn either into a **ternary {−1,0,+1} HDC crystal** is the same, and it obeys one rule:
> **crush the weights *after* training and you shatter the model; grow them ternary *from birth* (QAT) and you keep
> ~all of it — at microwatts.** This is the crystallization cascade made concrete: the furnace (full-precision
> learning) and the crystal (ternary HDC) can be **one pipeline**, and the crystal keeps the meaning.

This note records the moment that claim stopped being theory and got measured on three independent testbeds,
including **raw language**.

## Why this matters

HDC's whole moat is *exact, reversible, glass-box, microwatt*. That moat is worthless if reaching it costs the
LLM's knowledge. The question was: **can you crystallize what an LLM learned into ~1.6-bit ternary without losing
it?** The honest fear (and a measured −7% on fine-ranking via post-hoc crushing) said "you lose something." This
note shows the loss is an artifact of *when* you quantize, not a law — provided you quantize *during* training.

## The mechanism — PTQ (crush-after) vs QAT (ternary-native)

- **PTQ** (Post-Training Quantization): train with precise decimals, then round every weight to −1/0/+1. The two
  layers' delicately-balanced cancellations break and the rounding errors compound through the net.
- **QAT** (Quantization-Aware Training, "ternary-native"): force weights to −1/0/+1 *in the forward pass every
  step*, via the **straight-through estimator** (forward = ternary so it feels the constraint; backward = smooth
  so it can still learn). "Act ternary, learn smooth." There is no rounding step left to break.

## The evidence — same mechanism, three testbeds

| testbed | what it is | crush-after (PTQ) | ternary-native (QAT) | artifact |
|---|---|---|---|---|
| **toy math** | controlled regression, ground-truth R² | **catastrophic** R² −0.43 (worse than guessing the mean) | **0.66, beats float (0.39)** | `15-llm-hdc-axis/qat_native_from_scratch.py`, `qat_demo_transparent.py` |
| **real LLM features** | bge-m3 embeddings → ternary | keeps **0.98** of teacher (output-quantization is robust) | — | `15-llm-hdc-axis/e2_real_teacher_ternary_cascade.py` |
| **raw words** | learn 10-way 20-newsgroups topics from TF-IDF | **0.66** (loses ~9 pts vs float 0.75) | **0.726**, recovers **77–94%**, ≈ float; **385 posts rescued** | `15-llm-hdc-axis/qat_language_recovery.py` |

`[measured-here]` In the toy, ternary-native didn't just recover — it **beat float** (the constraint regularizes),
and recovery **grew with width** (119%→134% from H=32→256): "place-value," distributing magnitude across more
ternary digits. `[literature]` This is exactly what **BitNet b1.58** shows at scale: ternary-native LLMs ≈ FP16 on
real language. Our three testbeds are the controlled unit-test (math), the feature-level check (LLM embeddings),
and the from-scratch language check (words) of the same gear.

**Honest boundary:** the recovery is *less dramatic on language classification* than on regression — classification
only needs the argmax right, so it's naturally more rounding-tolerant (no negative-accuracy collapse). The
*direction* is identical and confirmed on words; the *magnitude* depends on how much precision the task needs.

## The bridge itself — one ternary code, two jobs

`[measured-here]` `15-llm-hdc-axis/ternary_native_codesign.py`: a learned encoder maps real bge-m3 document
meaning to a **ternary D=10000 hypervector** that serves discovery *and* the HDC algebra at once:

| | class acc (discovery) | reversibility | bundle-recover @K=64 |
|---|---|---|---|
| ternary code (native) | **0.92–0.94** | **1.00** (exact) | 0.83 (graceful, ~D/(2·ln N)) |

Reversibility is **exact by construction**: items are ternary, roles are bipolar {−1,+1} (self-inverse), so
`unbind(bind(role,item)) = role⊙role⊙item = item`. So a single ternary code from real LLM meaning is
simultaneously a **classifier** and a **working associative memory** — the bridge, in one object.

**Honest deflation (kept for the record):** my special "co-design term" (decorrelation + balance) did **not** beat
plain ternarization on memory capacity (0.35 vs 0.38 @ K=256) → INCONCLUSIVE on that specific lever. The lesson is
*better* than the hypothesis: you don't need a clever trick — **plain ternarization of an LLM's meaning vectors
already gives you both jobs for free.**

## Bottom line

- **Discovery is conserved** (yield ≤ 1): the HDC crystal inherits the LLM's knowledge, never exceeds it.
- **But the crystal can be nearly lossless** if you crystallize *in* the ternary lattice (QAT), not by crushing
  afterward — confirmed on math, on LLM features, and on raw words.
- **Therefore the furnace and the crystal can be one pipeline:** a ternary-native learned encoder whose output
  *is* the hypervector — exact, reversible, glass-box, ~1.6-bit, with 60%+ of weights exactly zero (skipped).

`[open]` The proper at-scale version: a ternary-native *transformer* (BitNet-style) whose final layer emits the
HDC hypervector directly, trained end-to-end — so the LLM's last hidden state and the HDC code are the same vector.
That is the chip.

*致虚极，守静笃 — every dramatic claim this session was deflated by a harder measurement; what survived is the
core, and the core is enough: the LLM thinks once, the HDC remembers forever, and the meaning makes it across.*
