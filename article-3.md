# The wall we don't have: scaling a stationary-weight ternary CIM to big models

*A follow-on to Articles 1 and 2. The question this time: what would it take to run a 30 / 50 / 100 GB ternary model on this substrate — KV cache, throughput, interconnect, the design limits? Everything below is tagged **[measured] / [modeled] / [frontier-extrapolated]**; external facts link to primary sources; and — as in Article 1 — I published one of my own corrections in the body, because a thesis that can't survive its own audit isn't worth shipping.*

---

## The one idea, restated: the weights don't move

A GPU running a large model spends most of its energy **moving weights** — streaming hundreds of GB out of HBM into the compute units, every forward pass. That traffic is the "memory wall," and most of modern accelerator design — HBM stacks, NVLink at 1.8 TB/s per GPU [measured, NVIDIA], the whole optical-interconnect roadmap — exists to fight it.

This chip doesn't fight that wall. It **removes** it. In compute-in-memory (CIM) the weights are written once into a resistive (ReRAM) array and **never move** — the array *is* the compute fabric. A token's forward pass reads no weights from anywhere; the only thing that crosses a chip boundary is the small activation vector, a few KB per token. The wall that defines GPU scaling is, for us, simply absent.

Two choices make that concrete, and honest:

- **Ternary weights (−1 / 0 / +1)** — ~1.7 bits/weight in practice [measured: an 8B ternary model packs to ~1.75 GB], *not* the 1.58-bit information floor. The overhead is the FP16 embedding, output head, and per-group scales you deliberately keep in full precision. Ternary models reach full-precision quality from roughly 3B parameters up [measured: BitNet b1.58 scaling, arXiv:2402.17764].
- **Digital readout, no ADC** — each column is read by a digital up/down counter over a differential pair of binary cells, not an analog-to-digital converter. The result is **bit-exact and deterministic**: the same input always returns the same bits. Hold onto that property — it pays off at the end.

---

## What we checked, and what's actually true

Building in public means publishing the *disappointing* results too. Three:

**1. ReRAM is not a logic node. Shrinking the process buys efficiency, not capacity.**
It is tempting to assume ReRAM density scales like logic (≈ node²). It does not. The cell is bounded by the access transistor that must source the forming/SET current — not by lithography — so density is **sub-node² and it plateaus**. The cleanest evidence is a single foundry's own published bit-cells: 14 nm = 0.022 µm² [measured, ISSCC 2021] → 12 nm = **0.0249 µm²** [measured, ISSCC 2024]. The cell got *larger*. What *does* scale cleanly with the node is the **digital periphery** — counters, control, drivers — which is the dominant power term. So we shrink the process to buy **energy efficiency**, and we say plainly that it does **not** buy GB of capacity. Capacity is a die-count, and therefore cost, question.

**2. Cooling is not the wall.** This compute is low power-density — no multipliers, no ADCs. Immersion and microchannel cooling have orders of magnitude of headroom over what we need. The real ceilings are capacity, yield, and cost — and we would rather say that than wave a liquid-cooling slide.

**3. The "selectorless 4F² crosspoint" is real — but it doesn't help compute.**
You can drop the bulky access transistor and reach ~4F² crosspoint density with a threshold selector; Intel/Micron's 3D XPoint shipped exactly that — an OTS-selector + phase-change crosspoint, ~4F², BEOL-stacked [measured, teardowns]. But a 2025 peer-reviewed result is blunt: the selector's threshold nonlinearity makes the cell current **no longer proportional to the stored value**, which "impedes the implementation of an in-memory analog MAC" [Frontiers in Nanotechnology, 2025]. Every shipping analog-MAC CIM part keeps the transistor selector for exactly this reason. So the breakthrough helps **dense cold storage**, not the **live compute array** — and we won't pitch it as the latter. (3D XPoint also teaches a second lesson: it was discontinued in 2022 for **market and cost** reasons, not physics. A manufacturable device is not a moat.)

---

## A correction I owe the record

Earlier in this work I argued that a single coherent 100 GB-class model would hit a hard "die-to-die bandwidth wall," reasoning by analogy to GPUs that shovel 245 GB of weights per step. That was wrong, and it contradicted my own thesis. **Our weights don't move.** Splitting a model across chips moves only activations — a few KB per token — not weights. The bandwidth wall is the GPU's affliction precisely because the GPU streams weights; importing it onto a stationary-weight architecture was a category error. I'm leaving the corrected reasoning below, in the open, rather than quietly deleting the old claim.

---

## The positive result: tensor parallelism is *more* natural here than on a GPU

To make a **single** large model fast — not just to serve many users — you split each layer's weight matrix across several chips so they compute it together. That's tensor parallelism (TP). On this architecture it is unusually clean, for three structural reasons:

1. **TP's premise is "weights are sharded and resident; only activations are communicated."** On a GPU that is a software arrangement that still fights HBM. Here it is a physical fact — each chip permanently owns its slice in ReRAM.
2. **The cross-chip merge is a bit-exact digital add.** Row-parallel TP must combine partial sums across chips. An *analog* CIM would sum currents and lose precision; our digital counter readout makes it an exact integer addition. (This "digital partial-sum across chiplets" is how shipping digital-CIM parts already work — e.g. TensorCIM [JSSC 2025]; d-Matrix Corsair [vendor].)
3. **It is the on-chip adder tree extended by one package hop.** We already combine ≤256-row tiles with a digital adder tree inside a die; crossing to the next die is the same tree, one link longer.

And the communication is cheap where it counts. At batch = 1 the per-layer all-reduce is **latency-bound, not bandwidth-bound** [Meta Engineering, 2025]; Megatron-style TP needs only two all-reduces per transformer layer [measured, arXiv:2104.04473]; the payload is a few-KB activation vector; and in-package die-to-die links run at single-digit nanoseconds and ~0.5 pJ/bit [measured, UCIe]. So **bandwidth — the thing optical interconnect sells — is not our binding constraint.** Optical earns its keep only across racks, where copper physically cannot reach.

This is a calculation, not a guess. Single-stream decode:

```
tok/s ≈ Fmax × (P × G) × util / (2 × N_active)
```

anchored on our own silicon (a 1B model on one die, at the measured datapath utilization, lands near 4,000 tok/s [modeled on a measured anchor]) and sanity-checked against a published 8B inference number. For a **sparse (MoE)** large model — where only ~13–30B parameters are active per token — **8 to 16 cooperating in-package dies** bring single-stream speed back into the ~1,000–4,000 tok/s range [frontier-extrapolated]:

| model (active params) | G=1 (one die) | G=8 | G=16 |
|---|---|---|---|
| ~100 GB MoE (≈30B active) | ~120 | ~930 | ~1,800 |
| ~30 GB MoE (≈13B active) | ~280 | ~2,100 | ~3,900 |

The honest caveats, stated up front: this needs a **tree** all-reduce and **in-package** proximity (a ring topology or a cross-package hop erases the gain at high G); it only helps **large** layers (a small dense layer underfills the array past G ≈ 8); and the cross-die latency model is **not yet silicon-measured**. It is a real, falsifiable next experiment, not a closed result.

---

## So what *can* a 30 / 50 / 100 GB ternary model look like?

Honestly: this is **frontier-extrapolated**. The largest *released, benchmarked* native-ternary model today is about 8B; everything above is a scaling-law projection, and I'd rather label it than imply otherwise. Our measured floor is an 8B ternary model running this chip's no-ADC digital datapath at near-lossless quality, plus a small ternary MAC array verified **on real silicon** — bit-exact, no multipliers.

The architecture I would build for that scale:

- **Ternary MoE, not dense.** Single-stream speed is set by *active* params, and sparse activation lights up only some tiles — native to CIM. (The bet to be tested: expert locality, so you don't pay to shuttle experts between dies.)
- **No growing KV wall.** Keep the KV cache off the write-limited ReRAM, on a small SRAM companion die; compress with int4, then latent attention (MLA, ~93% KV reduction [measured, arXiv:2405.04434]) — which conveniently moves cost onto the matmul this chip is best at. Or go further with a linear-attention / RWKV-style model that carries a **constant-size state and no KV cache at all**: this chip kills weight-movement, RWKV kills history-movement — the same enemy from two sides.
- **Tensor parallelism in-package** for single-stream speed, as above.

I'm publishing the framework, not a benchmark I don't have. Poke holes — issues and PRs welcome.

---

## What we're building toward / 亮剑

**Deterministic intelligence — private, verifiable, and *owned* — running at near-zero power in everyone's hands, not rented from a cloud.**

确定性的智能：私有、可验证、属于你自己，在近乎零的功耗上常开，是你拥有的，不是你租来的。

The memory wall is the cloud's wall. We don't have it. The moat was never "bigger" — it is *yours, private, deterministic, always on*: a chip that, before anything else, takes care of the human being holding it.

If that's the future you also want to build — devices, compilers, RWKV-on-silicon, honest CIM — come build it with us.

---

*Discipline: every claim above is tagged measured / modeled / frontier-extrapolated; external facts link to primary sources; four numbers I could not verify to a primary source were removed rather than dressed up. Memory stales; silicon is ground truth. When a measurement contradicts a note here, the note loses.*
