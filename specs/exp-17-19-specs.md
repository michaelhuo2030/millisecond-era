# 38 — Exp 17 / 18 / 19 Architecture-specific Validation Specs (v8.18.1)

**Date**: 2026-05-18 (post Michael 8th reframe: 250K-safe lock)
**Target**: validate Stage 4 LOCKED architecture (5-die chiplet, 28nm 8-layer 3D 4-bit MLC, 7 GB SRAM, **250K ctx**, 8-12K tps, Tier 1+2 cooling)
**Status**:
- Track E + E2 (paper deep-read 6 agents) → closed 12+ hypotheses
- Remaining Stage 1 critical: **G8 (pipeline timing)** + **G9 (hot expert hit rate)** + **G10 thermal sim** (Track E2 wave 2 gave 3/5, sim can lift to 4/5)
- Cost: $0 (all AI agents + 实验 Mac)
- Time: 2-3 days wall-clock
- Note: Exp 20 (LPDDR5 latency) **DROPPED** because 250K-safe spec has no LPDDR5

---

## Exp 17 — Pipeline Timing Simulation (G8)

**Mission**: 软件模型 5-die × 8-layer × tile 架构, map V4-Flash 43 model layer, 仿真 single-stream token latency, 确认 8-12K tps 可达 at 250K ctx with hot expert cache.

### Inputs (concrete numbers)

- **Chip topology**:
  - 4 active ReRAM-CIM die, 1 spare (N+1)
  - Each active die: 8 chip layers × ~16 tiles/layer-die = 128 tiles/die
  - Total active tiles: 512 (parallel compute capacity)
- **Latencies** (from Track E findings):
  - ReRAM cell read + ADC: ~70-100 ns per tile op
  - Digital adder tree (Path C): ~10-20 ns
  - TSV inter-layer hop: 0.5-2 ns
  - Inter-die hop: 5-10 ns (2.5D interposer)
  - SRAM read (control die): ~5-10 ns
- **Workload**: V4-Flash 43 model layers, MoE Top-6 expert routing, MLA + multi-query attention
- **Token budget**: 1/8000 s = 125 μs (8K tps target), 1/12000 s = 83 μs (12K tps stretch)

### Methodology

Python sim (~300-500 lines, NumPy):

```python
# Pseudo-spec
class ChipSim:
    def __init__(self, dies=4, layers_per_die=8, tiles_per_layer=16, 
                 sram_gb=7, hot_expert_count=128, total_experts=256):
        self.tiles = dies * layers_per_die * tiles_per_layer  # 512
        self.sram = sram_gb
        self.hot_cache = hot_expert_count
        
    def forward_token(self, kv_size_mb, hot_hit_rate):
        # 43 model layers sequential, each:
        # - Attention (10% FLOPs): KV read from SRAM (~5 ns × seq_len factor)
        # - MLP/MoE (90% FLOPs): expert dispatch (Top-6 of 256)
        #   - If all 6 in hot cache: parallel tile ops, ~1-2 μs
        #   - If 1+ in cold: cold expert load latency (~50-100 ns added)
        # Pipeline across 8 chip layers (model layer 1-5 → chip layer 1, etc.)
        layer_times = []
        for ml in range(43):
            # Compute critical path: max(attention, expert)
            t_attn = self.attention_time(kv_size_mb)
            t_expert = self.expert_time(hot_hit_rate)
            t_inter_layer = 0.5  # TSV
            layer_times.append(max(t_attn, t_expert) + t_inter_layer)
        return sum(layer_times)
    
    def attention_time(self, kv_size_mb):
        # KV read from SRAM (7 GB total, accessed proportionally)
        # MLA + multi-query keeps this small
        return 0.2 + (kv_size_mb / 100) * 0.5  # μs, scales with ctx
        
    def expert_time(self, hot_hit_rate):
        # Top-6 expert dispatch
        # If hot: 6 parallel tile ops, ~1.5 μs
        # If cold (rare with 90%+ hit): + 0.1 μs penalty per cold expert
        cold_penalty = (1 - hot_hit_rate) * 0.5  # μs
        return 1.5 + cold_penalty
    
# Sweep
for ctx in [32, 90, 128, 250]:  # K tokens
    for hit_rate in [0.50, 0.70, 0.85, 0.90, 0.95]:
        for clock in [800e6, 1e9, 1.2e9]:
            t_token = ChipSim().forward_token(kv_size_mb_at(ctx), hit_rate)
            tps = 1e6 / t_token
            print(f"ctx={ctx}K hit={hit_rate} clock={clock/1e9}GHz → {tps:.0f} tps")
```

### Output (`39-exp17-pipeline-timing-results.md`, ~2-3K char)

- §A: tps heatmap (ctx × hit_rate × clock)
- §B: Identify bottleneck (compute vs memory vs interconnect)
- §C: Recommended hot cache size + clock target for 8-12K tps at 250K ctx
- §D: G8 confidence delta (0/5 → 4/5 target)
- §E: Residual risk if hit rate < 85% in production

### Run on
实验 Mac (AI 写 code + 跑), ~1-2 天.

---

## Exp 18 — Thermal Simulation (G10 lift 3/5 → 4/5)

**Mission**: 5-die chiplet 8-layer 3D 热模型, validate Tier 1+2 cooling 把 bottom layer 控制在 ≤65°C @ 35W TDP (post 250K-safe lock).

### Inputs

From Track E2 Agent 5:
- HBM 8-12 layer bottom (no cooling): 75-95°C @ 30W
- HBM with Tier 1+2: 55-70°C @ 30W
- Cu TSV thermal K: 60 W/(m·K) effective @ 100 μm pitch
- Top-side cold plate: 15-25 W/cm² achievable
- ReRAM thermal limit: 100-120°C

### Methodology

**Option A (preferred, free)**: AI agent build simplified 1D thermal model in Python (~100-200 lines)
- Heat source per layer: ~3-5W (with 35W TDP / 8 layers = ~4W/layer)
- Top boundary: 25°C (water cooled cold plate)
- Material stack: 8 Si layers + 7 TSV bonded interfaces + top cold plate
- Compute steady-state temperature gradient

**Option B (high-fidelity, optional $2K)**: Hire short-term consultant with ANSYS Icepak / FloTHERM access for 2-day model.

For now, run Option A. If Option A shows margin tight (60-65°C), commission Option B.

### Output (`40-exp18-thermal-results.md`, ~1-2K char)

- §A: Steady-state thermal map (bottom + middle + top layer temps)
- §B: Sensitivity sweep: TDP 25W / 35W / 50W / 80W
- §C: Tier 3 microfluidic 是否 needed (我们预测: NO at 35W)
- §D: G10 confidence verdict (target 4/5)

### Run on
AI agent (background), ~0.5 天.

---

## Exp 19 — Hot Expert Hit Rate Sweep (G9)

**Mission**: 用 Exp 13 (in flight on 实验 Mac) 跑出的 V4-Flash 真实 Top-6 routing distribution, sweep hot cache size (32 / 64 / 96 / 128 experts), 计算 hit rate, 决定 100 GB on-chip 装 128 expert 是否最优.

### Inputs

Exp 13 output: per-token Top-6 expert IDs across diverse workloads (technical / creative / code / chat).

### Methodology

Python rolling cache simulation (~100 lines):

```python
def sweep_cache(routing_log, cache_sizes=[32, 64, 96, 128, 160, 192]):
    # routing_log = list of [(token_idx, expert_ids[:6])]
    results = {}
    for size in cache_sizes:
        for policy in ['LRU', 'LFU', 'static_topK']:
            hits = 0
            total = 0
            for token, experts in routing_log:
                # Cache check
                for e in experts:
                    total += 1
                    if e in cache:
                        hits += 1
                    cache.add(e)  # update per policy
            results[(size, policy)] = hits / total
    return results
```

### Output (`41-exp19-hit-rate-results.md`, ~1-2K char)

- §A: Hit rate curve (cache size × policy)
- §B: Recommended hot cache size for ≥ 90% hit at 250K ctx
- §C: Worst-case (10% cold miss) tps degradation (no LPDDR5, so cold expert must come from another active die or N+1 spare)
- §D: G9 confidence verdict (target 4/5)

### Run on
实验 Mac (after Exp 13 done), ~0.5-1 天.

---

## DROPPED — Exp 20 LPDDR5 latency

Per Michael 2026-05-18 第 8 reframe: 250K-safe ctx 不需 LPDDR5 spillover. Exp 20 cancelled.

---

## 执行 schedule (parallel, 1-2 天 wall-clock)

| Action | When | Who | Time |
|---|---|---|---|
| Exp 17 spec → 实验 Mac | Now (handoff via 32-file update) | 实验 Mac Claude | 1-2 天 |
| Exp 18 spec → AI agent (Python thermal sim) | Now | AI Background agent | 0.5 天 |
| Exp 13 完成 (in flight) | ~now-1 天 | 实验 Mac | running |
| Exp 19 → 实验 Mac (after Exp 13) | After Exp 13 done | 实验 Mac Claude | 0.5-1 天 |

**Net Michael time**: ~30 min review when results surface.

---

## Stage 1 final exit (post Exp 17/18/19 done)

| Critical hypothesis | Pre-experiments | Target post | Source |
|---|---|---|---|
| G8 pipeline 8-12K tps | 0/5 | **4/5** | Exp 17 timing sim |
| G9 hot hit rate ≥90% | 0/5 | **4/5** | Exp 13 + 19 |
| G10 thermal ≤65°C | 3/5 (paper) | **4/5** | Exp 18 sim |

**总 Stage 1 critical hypothesis count post all experiments**:
- Generic: 9/10 ≥ 4/5 (B4 = 3.5 Stage 2 open)
- Architecture-specific: 5/7 ≥ 4/5 (G13 Stage 3, G6/G7/G10/G11 ≥ 4/5; G8/G9 升到 4/5 via Exp 17/19)
- **Total: 14/17 ≥ 4/5, 3 explicit Stage 2/3 open (B4, G13, generic gaps)** ✅

**Stage 1 Exit = MET** (10/13 generic + architecture target hit, others explicit deferred).

**Stage 0 (FPGA tiny LM) 完成后 + Stage 1 Exit** → Article 2 ship + Stage 2 launch trigger.

---

## 一句话

> Exp 17 (pipeline timing sim) + Exp 18 (thermal sim) + Exp 19 (hot expert hit rate sweep) = 3 个 $0-cost AI/实验 Mac experiments, ~1-2 天 wall-clock, close 剩余 Stage 1 architecture-specific G8/G9/G10 hypothesis. Exp 20 LPDDR5 latency **dropped** (Michael 8th reframe 250K-safe lock). 完成后 Stage 1 Exit Criteria 满足 (14/17 ≥ 4/5), Article 2 ship + Stage 2 launch trigger.
