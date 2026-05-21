# 毫秒纪迭代日志 — 一个诚实的研究过程记录

> **这篇文章是什么**: 不是 PR, 不是 corrigendum, 是完整的研究迭代过程。每一次我们以为对了、又发现错了、又修正的全部记录。给所有认真在做事的人看。
>
> **为什么要写**: Article 1 (2026-05-16) 和 Article 2 (2026-05-18) 里有些数字是错的。不是小错。我们在发表之后的 48 小时内自己发现了，靠的是 AI 协作 + 物理第一性原理审计。这个"发现-修正-再发现"的过程，比最终数字本身更有价值。所以完整记录下来。

---

## 起点 — Article 1 的初始 Thesis (2026-05-16)

**我们发表了什么:**

| 指标 | Article 1 原始声称 |
|---|---|
| 速度 | 3,000 – 20,000 tokens/s |
| 价格 | ¥6,000 起 ($900) |
| 架构 | 28nm ReRAM CIM，能效 "25-40× vs GPU" |
| 比较基线 | M4 Max 12 t/s @ 250K context |

**我们的信心来源**: 基于 Stage 0 的实测数据点 (antirez ds4-server on M4 Max 128 GB)，以及第一性原理推算。

**现在知道的问题**: 速度数字和能效数字来自对 "pure CIM" 架构的假设，而这个架构在物理上做不到（详见下文 Round 1）。比较基线 "M4 Max 12 t/s" 是 250K context 长度的特殊情况，不是正常推理速度（实际 M4 Max 跑 9B 模型是 30-80 t/s）。

---

## Article 2 的架构规格 (2026-05-18, 同天发现问题)

**Article 2 锁定的架构 (发表时):**

| 规格 | Article 2 数字 |
|---|---|
| 单 die 容量 | **25 GB ReRAM CIM** |
| 总容量 | **100 GB ReRAM + 7 GB SRAM** |
| 模型 | **DeepSeek V4-Flash, 81 GB Q2_K** |
| 吞吐 | **5,000 – 15,000 tokens/s, 合同底线 ≥ 3,000** |
| TDP | **35 – 50W** |

**Article 2 同天 (2026-05-18) 下午，我们就发现了里面有根本性错误。**

---

## Round 1 修正 — 物理容量 Audit (2026-05-18 下午, Phase 35)

### 发现过程

我们做 5-die floorplan 时，AI agent (A9) 做了一个底层物理计算：

```
28nm ReRAM CIM 单 die 容量：
  - 每个 bit cell 面积: ~40nm × 40nm = 1.6 × 10⁻¹⁵ m²
  - 300 mm² die = 3 × 10⁻⁴ m²
  - 理论最大 cells: ~1.9 × 10¹¹ cells
  - 4-bit MLC → 理论最大容量: ~95 GB
  
  但是: cells ≠ usable storage
  - 实际 array efficiency: ~30-50% (peripheral circuits, routing)
  - 所以: 95 GB × 40% = 38 GB "theory"
  
  现实校验: Toshiba 24nm 4-layer 3D NAND (不是 ReRAM): ~32 Gb/die = 4 GB
  Toshiba 的是成熟工艺, ReRAM 没有 Toshiba 那样的 3D 集成密度
  
  Industry SOTA ReRAM CIM: HYDAR ISSCC 2026 = 576 Kb macro @ 28nm
  576 Kb = 0.072 MB。我们的"25 GB"是它的约 350,000 倍。
```

**错误量级: 25 GB/die 在 28nm 纯 CIM 模式下，比当时 industry SOTA 高出约 1,500×。**

7 GB SRAM 的问题类似: SRAM 密度比 ReRAM 更低，7 GB 需要的面积是整个 SoC 面积的 300 倍以上。

### 我们为什么会犯这个错

"25 GB/die" 来自 top-down 需求设定：我们需要 81 GB 容量 → 4 个 die → 每个 die 需要 ~20 GB。这个数字是从需求倒推的，没有经过 bottom-up 物理验证。

这是 AI 协作的典型陷阱：AI (Claude) 可以给你计算需求，却不会自发问"这个数字在 28nm 工艺下物理上能不能做到"。

### 修正后的架构 (Path 1 Hybrid, Phase 35 lock)

| 规格 | 修正后 |
|---|---|
| 架构模式 | **Hybrid**: 每 die 95% storage zone + 5% CIM scratchpad |
| 单 die storage | 25 GB (storage-mode, 类 Toshiba precedent) ✅ |
| 单 die CIM | ~1.25 GB (5% scratchpad) |
| 能效 | **3-7× vs GPU** (不是 25-40×) |
| 吞吐 | **30-200 tokens/s** (不是 5K-15K) |

能效从 25-40× 下降到 3-7×：原因是 "pure CIM" 在每次 inference 时不需要移动权重 (理想)，而 hybrid streaming 需要把权重从 storage zone JIT stream 到 CIM scratchpad。这个数据移动重新带来了部分 von Neumann 瓶颈，但不是全部。

**教训 D7**: 任何 spec 数字在传播前，必须 bottom-up 物理验证 (cell density × area)，不能只 top-down 需求设定。

**教训 D8**: LLM 是 pattern matcher，不是 physics simulator。Prompt 约束的 ceiling 很低。必须用外部 Python 物理模型作约束。

---

## Round 2 修正 — 产品策略 Pivot (2026-05-18 晚 ~ 2026-05-19, Phase 40-44)

### 问题: Pro SKU (V4-Flash 81 GB) 的吞吐太慢

Path 1 hybrid 修正后，Pro SKU 的吞吐变成了 30-200 tokens/s。

一个问题随之而来：**"30-200 tok/s 的 81 GB 大模型，凭什么比云端 API 好？"**

- GPT-4o API: ~100-200 tok/s (streaming)
- Claude 3.5 API: ~150-300 tok/s (streaming)
- 我们 Pro SKU hybrid: 30-200 tok/s @ $3,000-5,000 硬件

速度差距几乎没有，但用户还要花 $3,000-5,000 买硬件。这个产品不成立。

### 修正: Mini SKU PRIMARY (Phase 40-43 pivot)

**Qwen3.5-9B Q4_K_M** 模型重新计算:

- 模型大小: ~5.5 GB (vs V4-Flash 81 GB)
- 可以在 4 die × 1.4 GB CIM scratchpad = 5.6 GB CIM 中全量常驻
- 全量常驻 = 推理时权重不出 die = **真正 pure CIM inference**
- 吞吐: **1K floor / 1.5-5K sustained / 4-12K peak** (compute-limited, NOT bandwidth-limited)

这比 M4 Max 跑同模型的 30-80 tok/s 快 **20-150×**，且全程离线、隐私保护。

Pro SKU (V4-Flash 81 GB) 变为 aspirational Year 4-5+ 目标，不是当前主线。

**这是整个项目最大的一次产品策略转变**，发生在 Article 2 发表当天。

---

## Round 3 修正 — 量化精度 (2026-05-18 深夜, Phase 44)

### 问题: Q2_K 量化的质量

Article 2 写的是 "DeepSeek V4-Flash, 81 GB **Q2_K** 混合精度"。

实测 (Kimi 数据, 2026-05-18):

| 量化方式 | Perplexity 变化 | 可用性 |
|---|---|---|
| FP16 (基准) | +0% | ✅ |
| Q4_K_M | +5-10% | ✅ ⭐⭐⭐⭐⭐ |
| Q3_K_M | +15-30% | ⚠️ 边界可用 |
| **Q2_K** | **+96%** | **❌ 不可用** |

Q2_K 让模型输出质量下降了将近一倍。这不是可以接受的精度损失。

修正：Q4_K_M 为 primary。Mini SKU 9B 模型 Q4_K_M ≈ 5.5 GB，在 5.6 GB CIM 容量内勉强放得下（利用率 98%，极限）。

### 同期发现: 4-layer vs 8-layer 3D ReRAM

Article 2 用的是 "8-layer 3D ReRAM"。

实际：8-layer 3D ReRAM @ 28nm 仅有 academic demo (清华吴华强组, IEDM 2024)，**0 commercial shipment**。4-layer 3D ReRAM 已有 Toshiba 24nm 级别的 pre-production 先例。

Mini SKU 选 4-layer，接受 higher-risk 的 8-layer 只用于 Pro SKU (far future)。

---

## Round 4 修正 — 数值计算 Bug (2026-05-19 深夜, Phase 47.7.10)

Phase 47.7.10 的 W0.5 self-audit 在 SHIP 之前抓到 3 个 magnitude-level 数值错误：

1. **Mb/MB 换算错误**: 某处用 Mb/1024 换算 MB，但应该 Mb/8。误差 8×。
2. **LLM architecture underestimate**: 某个 layer count 计算少数了几个 transformer block。
3. **Mid SKU CIM ≠ NAND**: Mid SKU 的 CIM 容量和 NAND 存储容量混用，是完全不同的物理实体。

**教训**: Magnitude error (> 2× 偏差) = BUG。任何新数字在 ship 前必须过 self-audit。

---

## 新发现 (2026-05-19 ~ 2026-05-21)

以上是"修正已有错误"的部分。但迭代过程也带来了真正的新发现：

### 发现 1: Mid SKU (Phase 47.7.8, 2026-05-19)

| SKU | 模型 | 方式 | 吞吐目标 |
|---|---|---|---|
| **Mini** | Qwen3.5-9B Q4 (5.5 GB) | Pure CIM | 1K-5K sustained |
| **Mid** (NEW) | 16-30B MoE (Qwen3-VL-30B-A3B, 3B active) | Q4 | 1,500-2,500 tok/s |
| **Pro** | V4-Flash 81 GB | Hybrid streaming | 30-200 tok/s |

3-tier 产品策略的逻辑: 不把全部赌注压在一条路上。

### 发现 2: HDC (超维计算) 作为芯片第二大脑 (Phase 47.14, 2026-05-21)

HDC (Hyperdimensional Computing) = 10 万维 binary 向量 + 3 个操作 (bind/bundle/permute)。

在 ReRAM CIM 上运行 HDC 有几个神奇的性质：

| 性质 | HDC 表现 | NN 对比 |
|---|---|---|
| 1-shot 学习 | 1000 类 100% 准确 | 需要 50-200 gradient 步 |
| 代数可逆性 | A ⊗ B ⊗ B = A 精确 | Attention 无精确逆 |
| 噪声免疫 | 30% bit-flip 仍功能正常 | NN weights 在 30% noise 下随机输出 |
| 搜索延迟 | 1.27 μs (comparator mode) | GPU 相似搜索 50-200 μs |

**关键应用**: MoE expert routing (零参数, 在线更新), KV cache episodic memory (655× 压缩), tokamak 等离子体控制 (1-2μs vs DeepMind AlphaControl 10ms)。

这个发现让 Mini SKU 从"单一推理芯片"变成了"推理 + 记忆 双系统"。

### 发现 3: DP.tech (NN-MD) 应用场景 (2026-05-20)

DP-GEN + DeePMD-kit = 用神经网络做分子动力学模拟。原本需要 GPU 集群。

我们的 ReRAM CIM 对这类 workload 的能效优势可能达到 100-1000×。这让 Mid/Pro SKU 有了一个明确的 AI-for-Science 客户锚点。

---

## 当前状态 (2026-05-21, 作为时间戳)

**Mini SKU (80% 主线, 目标 Stage 3 MPW):**

| 指标 | 当前最佳数字 | 可信度 |
|---|---|---|
| 模型 | Qwen3.5-9B Q4_K_M, ~5.5 GB | ✅ 已验证 (aux Mac 实测) |
| CIM 容量 | 4 die × 6L 4-bit = 5.58 GB | ✅ bottom-up 物理验证 |
| 吞吐 | 1K floor / 1.5-5K sustained / 4-12K peak | ⚠️ 模型预测，待 Stage 2 FPGA 验证 |
| 能效 | 3-7× vs GPU | ⚠️ 模型预测 |
| TDP | 28W | ⚠️ 模型预测 |
| 价格 | ¥2,500-3,500 | 估算 |
| 工艺 | 28nm，4-layer 3D ReRAM | 需 custom partnership (显芯/Crossbar/昕原) |

**还没验证的 (已知的未知):**
- 9B LLM on ReRAM CIM 推理质量 (Q4 perplexity @ analog noise)：无公开 benchmark，0 先例
- Stage 2 FPGA 实测吞吐 (A45.5 给了 MLX analog，还不是 FPGA)
- 散热：28W @ 10×6×3 cm 被动散热是否够

---

## 元教训: AI 协作下的硬件研究长什么样

这 5 天 (2026-05-16 ~ 2026-05-21) 的全部迭代给我留下的最深教训:

**1. AI 发现了我们的错误，也造成了我们的错误**

Phase 35 的 A9 agent 通过 bottom-up 物理计算发现了 25 GB/die 的错误。

但错误本身也是 AI 造成的：Claude 在没有物理约束的情况下，从需求 top-down 推算 capacity，给出了"听起来合理"但物理不可行的数字。

**AI 是 pattern matcher，不是 physics simulator。这句话要反复在脑子里过。**

**2. 错误从发现到修正: 同日**

Article 2 发表 (2026-05-18 上午) → Phase 35 floorplan audit (2026-05-18 下午) → 错误发现 → 同天修正。

这是迭代速度的极限情况: 发表的时候已经知道了错误。Article 2 的数字在发表当天就过期了。

这不是罕见情况。这是 AI 协作下的正常研究速度。

**3. 公开学习路径吸引同行，隐瞒赶走同行**

我们本可以悄悄改数字，然后假装一直对。没人会知道。

我们选择记录下来。原因: 能看懂这个迭代过程、并且认为它有价值的人，正是我们需要的合作者。一个看到错误就跑的人，和一个看到"发现错误-修正-继续"就留下来的人，是完全不同的人。我们需要后者。

**4. D7 + D8 是所有防御层里最重要的两条**

- **D7 (底层物理验证)**: 任何 spec 数字，在传播给任何人之前，必须 bottom-up 物理验证 (cell density × area)。不能只 top-down 需求设定。
- **D8 (物理模型先于 spec)**: 写 Python 物理模型 (chip_model_adapter.py)，让所有 spec 先过模型，再出 narrative。LLM 的 ceiling 永远低于 physical model 的 ceiling。

---

## 致谢

这份迭代日志是和 Claude (Anthropic) 协作完成的。大多数错误是 Claude 参与计算时没有自发提问的。大多数修正也是 Claude 做的。

这就是 2026 年 AI 协作研究的现实：加速了迭代，也放大了错误。工具的价值在于使用者的纪律。

Michael ([@michaelhuo2030](https://github.com/michaelhuo2030))  
2026-05-21, Shanghai

---

*原始 Article 1 (2026-05-16) 和 Article 2 (2026-05-18) 保留原文，不删不改。这份日志是 delta。*
