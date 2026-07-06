# C1 first SKU public brief (2026-07)

This is the public-safe export of the latest private cleanroom. It does not publish circuit layouts, programming-pulse detail, partner sourcing, or package/floorplan internals. It does publish the product boundary, the speed-first comparison rule, and the next falsifiable gates.

## Executive line

The first product is **C1**: a narrow resident-weight, low-bit inference accelerator.

It is not a GPU, not a CPU, not a general PyTorch target, and not a broad accelerator platform. C1 is plausible only because it is intentionally narrow:

- resident-weight inference, not general compute;
- ternary / low-bit model path, not arbitrary FP16/BF16;
- local controller, not a host-driven bare compute die;
- firmware-class resident model provisioning, not per-request hot-swap;
- one compute die family, partner foundry / OSAT / IP;
- first model ladder: **0.1B / 0.3B / 1B / bounded 3B**.

Anything **>3B** is C2/C3 future work until C1 evidence exists.

## Whole picture: C1 bridgehead, 100B frontier

Bounded 3B is a **C1 constraint**, not a technology ceiling.

C1 exists to prove the smallest useful version of the substrate: a resident low-bit model answering a real local loop much faster than the incumbent. The later vision remains larger: if density, write/refresh, packaging, low-bit training, and buyer evidence all compound, the same resident-weight idea can move toward 8B, 32B, and eventually 100B-class systems. Those are **C2/C3 frontier coordinates**, not first-SKU promises.

| horizon | public meaning | model scale | claim status |
|---|---|---:|---|
| **C0** | proof vehicles | tiny / toy | measured FPGA and lab evidence only |
| **C1** | first product boundary | 0.1B / 0.3B / 1B / bounded 3B | current public SKU target |
| **C2** | stronger modules / boxes | 3B+ / 8B / 32B | future research and buyer learning |
| **C3** | civilization-scale substrate frontier | 100B-class | possibility frontier, not a sales claim |

## Why the chip is useful

Most accelerators move model weights from memory to compute again and again. C1 is useful when the model can be a mostly-static resident matrix:

```text
GPU / NPU shape:
weights in DRAM/HBM -> move weights -> compute -> repeat

C1 shape:
weights already live in ReRAM-CIM array -> stream small input vector -> compute in place
```

The fastest data movement is the one you delete. That is why the public story should lead with **speed and latency**, not TOPS.

The resident matrix is not permanent ROM. ReRAM makes the model **provisionable and reprogrammable** at firmware / OTA / service cadence. But it is also not RAM: the model should not change every request or every token.

## Public comparison rule

Buyer-facing comparisons should use this order. The short rule is: **same-task speed first, deployment fit second,
TOPS last**.

1. **Same-task speed:** tok/s, p50/p95/p99 latency, peak-reflex Hz, ms/loop, closed-loop success.
2. **Deployment fit:** local/private, power, thermal, model-update cadence, form factor.
3. **Reference coordinates only:** TOPS, TFLOPS, watts, and vendor platform names.

If a table says "how much faster," compute the ratio in the same metric:

- tok/s vs tok/s;
- loop Hz vs loop Hz;
- latency vs latency.

If the system is camera/radar/sensor/safety-chain limited, label the speedup as **local AI-loop speedup only**, not whole-system speedup.

## C1 SKU ladder

All numbers below are **modeled cleanroom design targets**, not taped-out ASIC silicon.

| SKU | target model | form | modeled speed-first target | early role |
|---|---:|---|---|---|
| **C1-A** | 0.1B | single packaged chip | ~300k tok/s; peak-reflex ~1.9kHz (~0.53ms/loop); short-QA ~381Hz (~2.6ms/loop) | first edge proof: AI glasses, earbuds, small cameras, always-on voice |
| **C1-B0** | 0.3B | small module | ~92k tok/s; peak-reflex ~1.3kHz (~0.77ms/loop); Hz95 ~357Hz (~2.8ms/loop) | bridge if 0.1B is too weak |
| **C1-B1** | 1B | module/card | ~97k tok/s; peak-reflex ~1.4kHz (~0.71ms/loop); Hz95 ~377Hz (~2.7ms/loop) | private-edge and enterprise small-model proof |
| **C1-B2** | bounded 3B | upper module/card | ~27.6k tok/s; peak-reflex ~425Hz (~2.4ms/loop); Hz95 ~108Hz (~9.3ms/loop) | upper C1 only; needs stricter package, PDN, thermal, write-load, and buyer gates |

Read both units together: **1000Hz = 1ms/loop, 100Hz = 10ms/loop, 10Hz = 100ms/loop**.

## What to say to a buyer

The clean question is:

> Do you have a task where a 0.1B / 0.3B / 1B / 3B resident low-bit model can answer so fast, locally, privately, or cheaply that your current phone NPU, Jetson, cloud, or GPU path is the wrong shape?

Strong C1 signals:

- the task can be solved by 0.1B / 0.3B / 1B / bounded 3B, not only by 8B+;
- batch-1 local latency matters more than aggregate cloud throughput;
- the buyer can supply task data, p99 latency targets, power/thermal constraints, and an incumbent baseline;
- model update cadence is daily/weekly/monthly/service-like, not per request.

Weak C1 signals:

- "come back when you run 8B+";
- arbitrary model support or full PyTorch compatibility;
- curiosity without data or a budget-holder;
- a comparison that only asks for TOPS.

## Early adopter map

| scenario | public status | C1 fit | what must be proven |
|---|---|---|---|
| AI glasses / wearables / earbuds / small cameras | current C1 outreach | C1-A first, C1-B0 if needed | same-task response, battery/thermal, privacy value, low-bit task retention |
| real-time voice / offline assistant / private short dialogue | current C1 outreach | C1-A/B0 | end-to-end ASR/NLU/TTS or command loop; p50/p99 latency; barge-in success |
| enterprise private small-model workflows | current C1 outreach | C1-B0/B1/B2 | classification, extraction, JSON repair, routing, short summaries; accuracy vs incumbent |
| robotics / drones / automotive cabin | research or validation target | C1-A/B0/B1/B2 only if a narrow loop fits | sensor-to-action p99, closed-loop success, safety partition, proof that slow-brain/action-chunking is not enough |
| AI-for-science | inspiration / research only | possible resident operator or validator, not full simulation | real trace, mappable fraction, Amdahl speedup, DFT calls saved; no 100x claim yet |
| datacenter / 8B+ / 100B | C2/C3 learning only | not C1 | same-model latency, low-bit quality, cost/J, integration, model availability |

## Writable resident slots

Public wording:

> C1 has provisionable resident model slots. A model can be written, verified, upgraded, rolled back, and health-checked. Normal inference reads the resident model; it does not rewrite the model every request.

Do not say:

- hot-swappable model memory;
- online learning inside ReRAM;
- arbitrary per-request model reload;
- "writes are free."

## Write / drift / refresh support tax

The support plane is mandatory: program drivers, verify-read, sentinel/reference cells, spares/remap metadata, temperature sensing, calibration, and local sequencer firmware.

Current modeled overhead:

| case | support tax | effective useful weight area if raw CIM = 90% | same-capacity die growth |
|---|---:|---:|---:|
| optimistic | ~4% | ~86.4% | ~1.04x |
| planning / nominal | **~12%** | **~79.2%** | **~1.136x** |
| harsh | ~30% | ~63.0% | ~1.43x |

Interpretation: nominal support tax is survivable if density lands in the product band. Harsh support tax pushes Form A/B toward rescope. This must be bounded before partner-facing package claims.

## What is measured vs modeled

Measured today:

- a tiny ternary LLM proof-of-concept runs a full autoregressive loop on real FPGA silicon at ~13,671 tok/s;
- ternary FPGA datapath evidence supports the "low-bit / no-multiplier" execution claim;
- cleanroom model-quality work shows ternary can be near-lossless in specific measured settings.

Modeled today:

- ReRAM-CIM ASIC speed, density, energy, package, support-plane tax, and C1 SKU performance;
- C1-A/B0/B1/B2 product cost and form-factor estimates;
- buyer speedup ratios until tested on a specific task and incumbent.

Open gates:

1. real ternary-differential macro density;
2. parametric analog yield;
3. on-silicon t_vmm / rowtile timing;
4. write/verify/drift/refresh support overhead;
5. package / PDN / thermal for Form B;
6. at least one C1 buyer evidence packet.

## Public red lines

Keep these out of public material unless deliberately released later:

- cell programming pulse recipes, circuit schematics, and calibration algorithms;
- private fab / OSAT / partner names or negotiation specifics;
- exact floorplan, pinout, package escape, PDN, and power-tree detail;
- unsupported AI-for-science 100x claims;
- claims that C1 replaces GPUs, DRIVE/Jetson safety stacks, or ASIL-D automotive compute.

One-line rule: **C1 wins only when a small resident low-bit model makes one real loop much faster, more local, more private, or more power-efficient than the incumbent.**
