# 09 — TOKEN-GENERATION SPEED & RESPONSE CYCLE, 0.1B→3B (engine L7; panel-checked)

> Systematic sweep of **decode tok/s (生成速度)** and **response cycle 周期 + heartbeat Hz** for the ternary
> ReRAM-CIM chip across 0.1B–3B models. Built paradigm-native (weight-stationary), every number is engine-computed
> from `04-LEDGER` §3/§4 and graded. **Speed and cycle share ONE core** (`per_token_latency`), gated by ONE
> operating rate. Supersedes the old `reram-density-study/14-THROUGHPUT-response-cycle` (which reported the
> TIMING ceiling as the "heartbeat" — that's the BOX number, not the edge number; see §3).

## THE FRAMEWORK (one core, two outputs) — ledger §3, panel #3 (3/3)
Weight-stationary CIM: every weight is a physical cell; one R×C array does a **full matrix-vector in one analog
settle `t_vmm`** (28nm cohort **5–18 ns**). So decode is NOT systolic `f·P/(2N)` — it is:
```
per_token_latency = Σ_layers [ Σ weight-matmuls + attention + glue ]   (sequential VMM depth × t_vmm)
timing-ceiling tok/s = 1 / per_token_latency          (optimistic: parallel rowtile + cols-parallel readout)
energy/token         = N_params × 100 fJ/MAC          (each resident weight used once per token)
power-bound  tok/s   = Watts / energy_per_token
OPERATING rate(W)    = min(timing-ceiling, power-bound)   ← BOTH prefill & decode (single-stream) run here
响应周期 cycle = TTFT(= ctx/rate + attention O(ctx²)) + n_gen / rate ;   响应频率 Hz = 1/cycle
```
The honest on-device number is **operating(W) = min(timing, power)**: at edge sub-W..few-W it is **power-bound**;
in a box (tens of W) it approaches the **timing ceiling**. The readout (rowtile/col) parallelism is the **#1 ~10×
GAP** — the ceiling here uses the optimistic (parallel) end, and the power gate then caps it.

## [A] DECODE tok/s — single user (realistic t_vmm 10 ns, ctx 512)
| model | energy/tok | timing-ceiling | @0.5 W | @3 W | @15 W | @50 W (box) |
|---|---|---|---|---|---|---|
| **0.1B** | 10 µJ | 627k | 50k (p) | 300k (p) | 627k (**t**) | 627k (t) |
| 0.3B | 30 µJ | 313k | 17k (p) | 100k (p) | 313k (t) | 313k (t) |
| 0.5B | 50 µJ | 311k | 10k (p) | 60k (p) | 300k (p) | 311k (t) |
| **1B** | 100 µJ | 446k | **5k (p)** | **30k (p)** | **150k (p)** | 446k (t) |
| 1.5B | 150 µJ | 253k | 3.3k (p) | 20k (p) | 100k (p) | 253k (t) |
| **3B** | 300 µJ | 245k | 1.7k (p) | 10k (p) | 50k (p) | 167k (p) |

- (p) = power-bound · (**t**) = timing-bound. **The flip to timing-bound happens only above W\* = ceiling × E/tok**
  (glm panel catch): **0.1B ~6 W · 0.3B ~9 W · 0.5B ~16 W · 1.5B ~38 W · 1B ~45 W · 3B ~74 W.** So **small models
  reach their timing ceiling in a box; ≥1B stay power-bound through tens of W** (the earlier "box → timing" prose
  over-generalized — the table labels are right, the sweeping claim was not).
- ⚠️ **energy/tok = N × E_MAC is the WEIGHT-MAC term (dominant) = an optimistic FLOOR** (codex catch). Full token
  energy adds attention-on-KV, softmax, LayerNorm, activations, control → **real edge tok/s ≈ 1.3–2× LOWER** (the
  ledger §4 system-overhead factor). Treat the edge columns as a **soft ceiling**, not a guaranteed rate. (kimi:
  100 fJ/MAC is an average — ternary zeros lower it; N counts MAC weights only, not embeddings/LN.)
- **Every cell still ≫ human reading speed (~10–50 tok/s)** even after the 1.3–2× haircut — even 3B @0.5W (~1k after
  overhead) beats a reader. Generation speed is **never** the bottleneck. The product story is NOT "fast tokens";
  it's **µW always-on** (§4).
- Band: ideal t_vmm 5 ns ≈ 2× the ceiling; conservative 18 ns ≈ 0.5×; **SERIAL rowtile ≈ 10× slower** (readout GAP).

## [B] RESPONSE CYCLE 响应周期 + heartbeat Hz — edge @3W vs box (timing ceiling)
| model | scenario | ctx | gen | TTFT@3W | cycle@3W | **Hz@3W** | cycle-ceil | Hz-ceil |
|---|---|---|---|---|---|---|---|---|
| **0.1B** | short-qa | 256 | 64 | 0.87 ms | 1.1 ms | **924** | 0.52 ms | 1923 |
| 0.1B | mid-chat | 1024 | 256 | 3.7 ms | 4.5 ms | 222 | 2.3 ms | 430 |
| 0.1B | long-scan | 4096 | 0 | 17.6 ms | 17.6 ms | 57 | 10.8 ms | 93 |
| **1B** | short-qa | 256 | 64 | 8.6 ms | 10.7 ms | **94** | 0.73 ms | 1372 |
| 1B | mid-chat | 1024 | 256 | 34.5 ms | 43.0 ms | 23 | 3.2 ms | 308 |
| 1B | long-scan | 4096 | 0 | 141.8 ms | 141.8 ms | 7 | 14.8 ms | 68 |
| **3B** | short-qa | 256 | 64 | 25.6 ms | 32.0 ms | **31** | 1.3 ms | 752 |
| 3B | mid-chat | 1024 | 256 | 103 ms | 129 ms | 8 | 5.9 ms | 170 |
| 3B | long-scan | 4096 | 0 | 419 ms | 419 ms | 2 | 26.6 ms | 38 |

## READING — the honest conclusions
1. **生成速度从来不是瓶颈** (decode ≫ human-read at every size/power). The chip is fast because weights don't
   move and one VMM = a whole matmul; sequential depth is only ~layers, not N/P.
2. **周期 splits hard by power regime** — this is the correction the old doc missed:
   - **Edge @3W (honest product heartbeat):** 0.1B short-QA ~**900 Hz** (true cognitive fluid); 1B mid-chat ~**23 Hz**
     (snappy); 3B mid-chat ~**8 Hz** / long-scan ~**2 Hz** (sluggish at the edge — 3B is a box/datacenter model).
   - **Box / timing-ceiling:** 5–20× higher (1B mid-chat 308 Hz, 3B long-scan 38 Hz). The old "56–2000 Hz" numbers
     were these BOX numbers mislabeled as the edge heartbeat.
3. **The edge sweet spot is 0.1B–1B.** 0.1B is a real-time perception loop at sub-W; 1B is a usable few-Hz–tens-Hz
   assistant at 3W. **3B at the edge is power-starved** (2–8 Hz) → it wants a box, not glasses. This matches the
   density make-or-break line (0.1B fits one die; 3B is multi-die datacenter).
4. **TTFT dominates the cycle at long ctx** (prefill is ctx tokens at the same power-bound rate + attention O(ctx²)).
   For interactive short-ctx the cycle is gen-dominated; for long-scan it's all prefill.

## THE LEVERS (move the operating point)
- **Power budget** = the operating-point selector on the speed/cycle curve (the single biggest edge knob).
- **energy/MAC 100→44 fJ** via V²(periphery DVFS 0.9→0.6V) + 1/R_LRS (TaOx future) ≈ **doubles** the power-bound
  tok/s at fixed W (ledger §4) — directly speeds the edge heartbeat. Floors: V_periph ≥ 0.5; R_LRS>40k needs TaOx.
- **rowtile readout-parallelism** = the #1 ~10× timing knob (RTL/layout GAP); only matters in the box (timing-bound).
- **t_vmm** (5→18 ns) scales the whole ceiling linearly; OUR exact value = SPICE GAP.

## 🔴 GAPs (named, gate the operating point)
1. **t_vmm** — real analog-settle + counter-readout + glue latency on OUR macro (SPICE / bring-up). Band 5–18 ns.
2. **rowtile / col readout-parallelism** — picks timing-bound vs readout-bound (the ~10× knob).
3. **prefill attention impl** — the O(ctx²) term is MODELED; long-ctx TTFT is the softest number.
4. **energy/MAC split (V² / 1/R)** — the lever budget for pushing the edge heartbeat up.

## CONSERVATISM (stated, not hidden)
The timing ceiling SUMS all 7 weight-matmuls per layer sequentially, though **QKV and gate/up are physically
parallel** (true sequential depth ~4/layer) → the ceiling is ~1.5–2× pessimistic. But the **edge product point is
power-bound**, so this conservatism does **not** move the product number — it only makes the box ceiling a floor.

## TOOL VALIDATION — NeuroSim V1.4 (2026-06-26, local Mac, 22nm ReRAM, direct C++ `main`)
Ran a **single 256×256 FC microbench** (one subarray, memcelltype=RRAM, 8-bit) to isolate the per-stage latency and
cross-check our hand-calc. Per-component readLatency split of the 368 ns layer:

| component | latency | share |
|---|---|---|
| pure **analog read** (ADC/sense + array integration) | ~31 ns / 8 bit-cycles ≈ **~4 ns/read** | 8% |
| **digital periphery** (decoders/mux/switchmatrix/buffers/IC/activation) | **337 ns** | **91%** |

**Two independent confirmations (tool, not just panel):**
1. **Our `t_vmm = 5–18 ns` is REASONABLE** — NeuroSim's pure analog read ≈ 4 ns/read, in-band (slightly conservative).
   The analog crossbar itself IS fast, as our paradigm-native model assumed.
2. **The digital periphery DOMINATES latency (91%)** → independently confirms the Q1-panel catch: the raw
   analog-settle timing ceiling is **optimistic**; the realistic ceiling must carry a **~3–5× haircut** (NeuroSim shows
   even ~10× at the layer level, but its "Other Peripheries" includes IC/buffer data-movement that our weights-resident
   design amortizes → treat ~10× as an upper bound, ~3–5× as the working number). **Also re-confirms "readout/periphery-
   limited macro"** (ledger §3/§5).

**Net (folded):** the **raw timing ceiling (hundreds of k) is lowered ~3–5×** → 1B ~90–150k, 0.1B ~125–210k. **The
EDGE power-bound numbers (1B 5k@0.5W / 30k@3W) are UNCHANGED** (power-bound, t_vmm-independent). Generation speed still
≫ human-read at every size. Both the fleet panel AND NeuroSim now back this — the ceiling haircut is no longer a
single-source claim. (macOS setup + run commands archived in the CIM-simulators setup notes.)

## PANEL STATUS — fleet codex+kimi+minimax+glm (rs-1782386678, 4/4 ok)
**Core model CONFIRMED.** All four engines validated the three load-bearing claims: `energy/token = N × E_MAC` for
decode (each resident weight used once/token), the `min(timing, power)` gate, and the weight-stationary decode
physics (not systolic). Catches folded:
- **glm #1 (REAL, folded):** "box tens-W → timing" was over-generalized → replaced with the exact flip thresholds
  W\* = ceiling × E/tok (0.1B ~6 W … 3B ~74 W). ≥1B stay power-bound through tens of W.
- **codex (REAL, folded):** `N × E_MAC` is the dominant weight-MAC term = an optimistic floor; full token energy
  adds attention-KV/softmax/LN/control → edge numbers are a soft ceiling, ~1.3–2× higher energy in reality (§4).
- **kimi (minor, folded):** 100 fJ/MAC is an average (ternary zeros lower it); N = MAC weights only.
- **glm #2 (REAL, reverse-conservatism, noted):** prefill on a crossbar can pipeline across depth → the **box /
  timing-ceiling TTFT is conservative** (could be faster). The **edge power-bound TTFT (= ctx/rate) is correct** —
  the power cap binds regardless of pipelining. So the cyc-ceil column is an upper bound on cycle.
- **minimax (REJECTED — the outlier error):** claimed "prefill energy = N × E_MAC, not ctx × N — overestimates by
  ctx." **This is wrong** — prefill processes ctx tokens, each a full pass through all N weights, so prefill energy
  IS ctx × per-token (weights are *reused*, but each token still drives its own MACs). **codex + kimi + glm all
  explicitly confirm prefill = ctx × per-token energy with the power bound applying;** minimax conflated
  weight-reuse with single-pass compute. _Conclusion-gate note: the lone "significant error" flag was itself the
  error — caught by 3-engine majority + first principles, not taken on its confidence._

**Net:** model stands; two honest refinements folded (flip thresholds; system-overhead floor → edge = soft
ceiling), one reverse-conservatism noted (ceiling TTFT), one outlier rejected. Bidirectional gate held.
