# RWKV-on-our-chip — 灵魂伴侣引擎

> **一句话**：RWKV 是离我们这颗三值存算一体芯片**最近的灵魂伴侣引擎**——因为它没有 KV cache，也就没有那堵把所有 AI 设备卡死的**内存带宽墙**。这个 folder 是我们把这件事**真跑了一遍**之后的硬账。

> **TL;DR (EN)** — RWKV-7 is the LLM architecture that fits our ternary compute-in-memory chip best: a pure RNN with **no KV-cache → no memory-bandwidth wall**. We ran four "gates" to check whether a *ternary* RWKV is actually buildable. All four came back green at small (PoC) scale — every number below is labeled `[MEASURED] / [ESTIMATE] / [TARGET] / [EXTERNAL]`. The chip ASIC is **not taped out** — but as of **2026-06-13 our own ternary MAC RTL runs functionally-correct on real FPGA silicon** (xc7z010; register-read PASS: on-chip checksum == golden bit-exact over 4096 outputs, II=1, 0 DSP). This is a *defensible build*, not a free ride.

> **Scope note** — our chip is a **general ternary-inference substrate** (it runs ternary-quantized models broadly). RWKV is the architecture we found fits it *best*; this folder is that case study, **not** a claim that the chip only runs RWKV.

> **为什么这是比"跑一个 LLM"更大的故事（capacity 的真身）** — RWKV 这套轻量线性时间引擎已被移植到几乎所有模态：文本、视觉、语音、音乐、时间序列、嵌入/检索…… 而且每个领域它的赢点都是**同一组物理**：效率 / 恒定内存 / 流式 / 端侧 / 高并发。这不是巧合，是架构决定的，也**正是我们三值芯片放大的那几条**。所以一块三值芯片 = 一个**通用的端侧"感知 + 记忆 + 推理"基底**：同一块芯片、同一架构，就能在眼镜上跑视觉前端 + 听说语音 + 语言推理 + 私有记忆——全部恒定内存、µW 级、离线。我们押的不是"某个最强的模型"，是"**那个能在端上通吃所有模态的架构**"。
> *(各模态的第三方证据为 `[EXTERNAL]`、出自各自论文；按我们一贯的纪律，逐条带出处的能力地图会单列，并明确区分"我们 measured / 别人 claimed"。)*

---

## 0. 怎么读这份文档（标签纪律 — 每个数字都带身份证）

我们做事有条铁律：**不吹**。所以这里每一个数字都贴了标签，你一眼能看出它有多硬：

| 标签 | 含义 |
|---|---|
| `[MEASURED]` | 我们自己实测跑出来的（标了模型规模 / seed 数 / 语料大小） |
| `[ESTIMATE]` | 算术估算（比如适配内存账） |
| `[TARGET]` | 设计目标，**尚不存在**的硬件（比如"1GB / 3GB 芯片"本身） |
| `[EXTERNAL]` | 第三方 / 论文（RWKV 官方、Uncheatable Eval、arxiv） |

**先把最重要的边界亮在最前面**（主动亮底牌＝可信度）：

- 我们的训练实验**全部是小规模 PoC**——≤1.66M 参数、~1MB 语料、1200 步、多为单 seed。**是趋势性证据，不是发表级 scaling law。**
- 这颗芯片处在**综合 + 仿真 + 设计**阶段，**没有流片、没有量产**。"1GB / 3GB"是设计目标，不是手里的硅。
- 适配账是**算术估算**，不是测出来的功耗 / 面积。

把丑话说在前头，下面的话你才信得过。

---

## 1. 为什么 RWKV 是我们的灵魂伴侣

你先把镜头拉远一点。今天所有的大模型，本质上都在跟一堵墙搏斗——**内存带宽墙**。Transformer 每吐一个字，都要把一份越来越长的 KV cache 从内存搬进算力单元再搬出来；上下文越长，搬得越多，单流速度就越慢、越费电。这堵墙不是工程没做好，是架构自带的。

RWKV 不一样。它是个**纯 RNN**：一个**恒定大小的状态**沿着时间往前滚，**没有 KV cache**，所以**没有那堵墙**。我跟你说，这恰恰就是我们整颗芯片的命门所在——我们做的就是"**权重即计算、不搬权重**"的存算一体；RWKV 做的是"**状态恒定、不搬历史**"。两个都在干同一件事：**把数据搬运这个万恶之源摁死。** 一个在权重侧、一个在历史侧，对上了。

而且这不是我嘴上说说。我们自己在 aux 上把一个真的 RWKV-7 checkpoint 跑了一遍，**实测**到了这个性质：

- `[MEASURED]` **状态恒定**：RWKV 状态 **2376KB 跨 ctx 64→4096 纹丝不动（1.00×）**；同规模的等价 Transformer，KV cache 一路涨 **×64**（ctx=4096 时 147MB vs 2.3MB ＝ 小 **62×**，而且上下文越长差得越多）。**我们的"内存墙"命题，在它的架构里被实测证明了。**
- `[MEASURED]` **没有暗箱**：我们拿一份透明的 200 行 numpy 实现，对照官方包，logit 偏差只有 **1.16e-5** ——逐位证实它的架构就是论文写的那样（衰减 + 低秩擦除 + 外积绑定 + 解绑＝一个学出来的联想记忆）。

外面的人怎么背书它（`[EXTERNAL]`，独立第三方）：

- `[EXTERNAL]` RWKV-7 "Goose" 真 arxiv 论文（2503.14456），理论上 **formally exceeds TC⁰**——它能做标准 Transformer 被证明做不到的 state-tracking。
- `[EXTERNAL]` **防作弊** Uncheatable Eval（用训练截止后的新数据，压缩率越低越好），同尺寸打赢主流 Transformer：

  | 模型 | RWKV-7 | 同尺寸 Qwen2.5 |
  |---|---|---|
  | 1.5B | **7.969** | 8.124 |
  | 2.9B / 3B | **7.486** | 7.722 |
  | 13B | **6.843** | 6.951 (14B) |

  （7B 档约打平。）官方 HF org，0.1B–13B 全开源。

**唯一保留**：RWKV-8 / ROSA "永不遗忘、永能召回"还没发布、没被独立验证——所以这条我们不算数。

---

## 2. 我们做了什么 —— 四道闸，全绿（小规模实证，不是吹的）

问题很直接：**RWKV 是好引擎，但它能不能塞进我们这颗"三值"芯片？** 三值（−1/0/+1）权重是我们整个物理护城河的地基；如果 RWKV 一三值化就变傻，那这条路就断了。所以我们一道一道闸去验。

### 闸 1 — 三值能不能活？（量化生存性）

`[MEASURED]`（byte-level LM，held-out CE，bits/byte，**越低越好**；2 seeds）
来源：[`results/qat_lm_ce.csv`](results/qat_lm_ce.csv)

| 条件 | bits/byte | Δ vs fp32 | 判决 |
|---|---|---|---|
| fp32 | 3.745 ± 0.005 | — | 基线 |
| **三值 + QAT** | 3.952 ± 0.007 | **+0.21** | 活了 |
| 三值 post-hoc（事后量化） | 7.122 ± 0.007 | **+3.38** | 崩了 |

**结论**：直接把训练好的模型砸成三值（post-hoc）＝**直接化死**（+3.38 bits）。但用 BitNet b1.58 那一套**量化感知训练（QAT）**，**把砸出来的洞修回了 94%**（3.38 → 0.21）。"三值上不了 RWKV 的递归"——**证伪。原生三值 RWKV 是可训练的。**

旁证 `[MEASURED]`（在一个**真的** RWKV-7 0.1B checkpoint 上做事后量化，最脆的 worst-case）：int8 **几乎免费**（ΔCE −0.015/+0.006）；int4 有损可用（+0.8~+2.4）；int3 / 三值事后量化 **+13~+19 ＝ 报废** → 印证：要三值，**必须 QAT**。

### 闸 2 — 越大会不会越无损？（规模化）

`[MEASURED]`（三值QAT − fp32 的 gap，沿参数阶梯；RWKV 标准 head_size=64；1MB 语料；1 seed/档）
来源：[`results/qat_scale_ce.csv`](results/qat_scale_ce.csv)

| 参数量 | fp32 | 三值QAT | gap |
|---|---|---|---|
| 0.15M | 3.320 | 3.513 | **+0.193** |
| 0.53M | 3.130 | 3.250 | **+0.120** |
| 1.66M | 3.084 | 3.112 | **+0.029** |

**结论**：gap **单调塌缩**（0.193 → 0.120 → 0.029），参数 **×11，惩罚掉了 85%**，到 1.66M 时三值≈免费（+0.029 ≈ 1%）。**BitNet b1.58 的规模律，第一次在 RWKV 的 DPLR 递归上被 measured 复现。** 也就是说 +0.21 是个**上界**——模型越大，越往零走。

### 闸 3 — 递归状态压低了会不会漂移？（状态精度）

`[MEASURED]`（部署配置，推理时把状态 S 每步重量化，沿长度测 CE gap vs fp32-state；1 seed）
来源：[`results/state_prec.csv`](results/state_prec.csv)

| 状态精度 | T=64 | T=512 | 漂移 T64→T512 | 判决 |
|---|---|---|---|---|
| fp16 | 0.0000 | 0.0000 | +0.0000 | 免费 |
| **int8** | −0.0007 | +0.0000 | **+0.0007（噪声级，无复利）** | **免费** |
| int4 | +0.045 | +0.058 | +0.013 | 真惩罚，不值 |

**结论**：递归状态用 **int8 ≈ 免费、且零长度漂移**（序列拉长 8× 也不累积）——"递归状态精度会复利漂移"，**证伪**。所以**完整的三值芯片 ＝ 三值权重 + int8 状态**，状态 SRAM 直接省一半。int4 有真惩罚（vs int8 差 70×），不划算。

### 闸 — HDC 正面对撞（它和我们另一半的关系）

`[MEASURED]`（机制 × 负载 × 5 seeds）来源：[`results/capacity_fidelity.csv`](results/capacity_fidelity.csv) · [`results/_kit_rwkv_wkv_vs_hdc_memory.json`](results/_kit_rwkv_wkv_vs_hdc_memory.json)

- ✅ **可逆性 ＝ HDC 的干净胜场（护城河）**：删一条记忆，HDC remove-gap = **0.00**（减法＝完全重建，精确、可交换）；RWKV 的 delta-state remove-gap = **0.116**（路径纠缠，删不干净）。
- 🐘 **真正的大象（比"谁容量大"更重要）＝ 容量 ↔ 可编辑性的根本权衡**：delta-rule 用"主动消干扰"换容量，代价是状态路径纠缠、删不干净；HDC 朴素求和放弃容量、换来精确可逆。**两端互补——不是竞品，是两层记忆。**
- 诚实说：`[MEASURED]` 里"delta 每字节碾压 HDC"这个原假设我们**没验出来**（指标被混淆，判 INCONCLUSIVE，要 MQAR 式检索 benchmark 才能定）——所以我们**不声称**它。

**四闸小结**：完整三值 RWKV ＝ **三值权重 + int8 状态**，目前在 PoC 尺度上**全部 measured 近无损**。showstopper 风险退役。

---

## 3. 我们这颗片，能跑多大？（适配账）

> ⚠️ 这一节全是 `[ESTIMATE]`（算术）＋ `[TARGET]`（芯片容量是设计目标，没流片）。可复现脚本：[`sizing.py`](sizing.py)，改假设重跑即可。

账怎么算的（全部摊开）：三值权重 ≈ **0.2 GB / 每 10 亿参数**（1.58 bit/param，BitNet b1.58 `[EXTERNAL]`）；但 RWKV 词表 65536，**embedding + head（2·V·C）不能三值化**＝一笔藏起来的"大词表税"，按 int8 算；递归状态 int8、batch=1 时只有几 MB，可忽略。

`[ESTIMATE]` × `[TARGET]`：单片、batch=1（边缘单流）

| 模型 | ~参数 | 三值权重 | emb+head(int8) | 片上合计 | 1GB `[TARGET]` | 3GB `[TARGET]` | 配置 |
|---|---|---|---|---|---|---|---|
| RWKV-7 0.4B | ~0.4B | 60 MB | 134 MB | **0.19 GB** | ✅ | ✅ | `[EXTERNAL]` |
| RWKV-7 1.5B | ~1.5B | 239 MB | 268 MB | **0.51 GB** | ✅ | ✅ | `[EXTERNAL]` |
| RWKV-7 2.9B | ~2.9B | 497 MB | 336 MB | **0.83 GB** | ✅ | ✅ | `[EXTERNAL]` |
| RWKV-7 7.2B | ~7.0B | 1272 MB | 537 MB | **1.81 GB** | ❌ | ✅ | `[EXTERNAL]` |
| RWKV-7 13.3B | ~12.8B | 2425 MB | 537 MB | **2.96 GB** | ❌ | ✅(临界) | `[ESTIMATE]` |
| ~1B（设计点） | ~1.0B | 149 MB | 268 MB | **0.42 GB** | ✅ | ✅ | `[ESTIMATE]` |
| ~4B（设计点） | ~4.0B | 716 MB | 403 MB | **1.12 GB** | ❌ | ✅ | `[ESTIMATE]` |
| ~9B（设计点） | ~9.0B | 1670 MB | 537 MB | **2.21 GB** | ❌ | ✅ | `[ESTIMATE]` |

**两条必须讲清楚的边界：**

1. **batch=1 是边缘场景**——这正是"片上常驻权重"芯片天生的命。RWKV 高并发服务时，状态是**每条序列一份**，256 路并发就把状态乘到 GB 级——那是**另一本账（服务器账）**，不是这颗边缘片要打的仗。
2. **大模型可以切片拼模组**——RWKV 是逐层递归、状态恒定，**架构天生好切**：单片放不下的，按层切到 2–3 片拼成一个模组（13.3B 就是这种）。

**甜点区怎么落：**

- **`[TARGET]` 1GB 三值片** → 舒服地单片跑 **~0.4B–3B**（正好覆盖 RWKV-7 真实可用的 0.4B / 1.5B / 2.9B）。4B 正好压在 1GB 线上（~1.1GB）。
- **`[TARGET]` 3GB 三值片**（我们的设计余量目标） → 单片直接吃下 **4B、7.2B、乃至 ~9B（~2.2GB）**；**13.3B 临界（~2.96GB）**，要么 3GB 单片擦边、要么 2 片拼模组。

换句话说：**1GB 这颗，是 1–3B 边缘 RWKV 的命；只要把密度做到 3GB，9B 这一档我们也单片吃得下。** 这就是为什么我们一直把芯片容量当成可滑动的设计旋钮，而不是写死。

---

## 4. telos —— 我们到底为谁做这件事

把镜头再拉远一次。我们做这颗片，**不是为了赢过云**——云很好，重活、偶发的大推理，连着 WiFi 调个前沿 API 就挺好。我们做的是云**结构上够不到的那一层**：要**全天在线、要本地私有、要断网照跑、要亚秒级**的那一层。

谁住在那一层？是云的光照不到的人——海上的渔民、草原上的牧民、被摄像头盯着的家政工、难民、没有文字的语言社群。**RWKV 是引擎，HDC 是那层可逆、可编辑、可联邦、可审计的私有长时记忆**（删一条 gap=0.00，钥匙在用户自己手里），**三值芯片是把这两样塞进微瓦、塞到脸上手上的物理基底。** 这三层合起来，才是"把一颗私有的 AI 大脑，真正交到一个人手上，而且这颗脑子是他自己的"。

---

## 5. 邀请 —— doers not talkers

这条线我们会自己趟完。但好东西就该开源、就该被更多人接力。

- **全部可复现**：四闸的脚本和 CSV 都在 [`results/`](results/) 和 [`reproduce/`](reproduce/)，适配账在 [`sizing.py`](sizing.py)，改了假设你自己重跑。**方法即护城河。**
- 如果你也相信"该把够用的智能，私有地、低成本地，交到云够不到的人手里"——尤其是做 RWKV / 端侧 / 存算一体的同路人——**来一起搞。** 我们要的是**真实的项目、真实的伙伴**，不是又一篇 PPT。

> 用我们一贯的话说：**doers not talkers。**

---

### 相关
- 三值 MAC 阵列**在真硅（xc7z010）上功能 PASS + II=1 + 0 DSP**（2026-06-13，读寄存器实测）+ P=512 综合可扩（194–266MHz，自有 IP）：见 [`../fpga/`](../fpga/)
- 我们的方法论 / 定律登记表 / 武器库：见 [`../hdc/`](../hdc/)
- 芯片架构决策记录（公开脱敏版）：[`../chip/ADR-v1-architecture.md`](../chip/ADR-v1-architecture.md)

*所有数字带标签；芯片为综合+仿真+设计阶段，未流片；训练结论为小规模 PoC 趋势。如发现任何越界声明，请开 issue 指正——我们当场改。*
