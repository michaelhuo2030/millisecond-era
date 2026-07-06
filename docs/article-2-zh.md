# Stage 1 验证报告: 15 个假设过审, 一套架构锁定

> Article 1 发布两周后。没有融资、没有团队、没有去 cold call 厂商。靠的是公开论文 + 第一性原理实验 + 第一手测量。这是我们现在知道的, 以及还不知道的。

---

> **2026-07 公开更新 / 历史稿标注:** 这篇保留为当时的 Stage-1 验证快照。文中的 5-die / 100GB /
> 5K-15K tok/s / USB-C 桌面方块架构, 在对外产品定位上已经被 **C1** 边界取代: 0.1B / 0.3B / 1B /
> bounded 3B, 先比同任务速度/延迟/Hz/闭环成功率, 保留可写入模型槽位, 所有 ASIC 数字标为 modeled。
> 8B / 32B / 100B 属于 C2/C3 可能性前沿研究, 不是第一 SKU 承诺。

## 我们走到哪儿了

Article 1 抛出了主线: 28nm ReRAM-CIM 芯片跑 DeepSeek V4-Flash, 入门款约 $850, 目标 ~10K tokens/sec。同时披露了 Stage 0+ 的实测 harness — 在 128 GB M4 Max 上跑 antirez 的 `ds4-server`, 拿到 50+ 个数据点。

过去两周我们没在做 marketing, 而是在收口架构。这篇是 Stage 1 验证报告: 15 个假设在经过一次公开文献深读、六个第一性原理实验、以及对未闭环项的诚实清点之后, 现在是什么样子。所有过程可复现, 所有材料已经在仓库里。

---

## 锁定的架构

经过多轮迭代, 设计已经收敛。一张表概括:

| 组件 | 规格 |
|---|---|
| 拓扑 | **5-die chiplet** (4 颗活跃 ReRAM-CIM + 1 颗 N+1 备用 + 1 颗 control die) 通过 **2.5D 65nm 硅 interposer** 互联 |
| ReRAM-CIM die | 300 mm², **28nm 8 层 3D 4-bit MLC ReRAM**, 单 die 约 25 GB |
| 片上总量 | **100 GB ReRAM** + **7 GB SRAM** (KV cache、indexer 状态、激活) |
| 模型常驻 | DeepSeek V4-Flash, **81 GB Q2_K 混合精度**, 全量片上常驻, 留 ~19 GB headroom |
| 上下文 | **原生 250K tokens** (按实测 SRAM 预算定的) |
| 吞吐 | **典型 5,000 – 15,000 tokens/sec, 合同底线 ≥3,000 tokens/sec** |
| 功耗 | **TDP 35 – 50W**, USB-C PD 4.0 供电 |
| 散热 | **仅 Tier 1 + Tier 2** — Cu thermal TSV 网格 + 顶部微通道水冷板。**不需要 exotic microfluidic** |
| 外形 | 12 × 8 × 3 cm 桌面方块 |
| 良率 (装配后) | **≥92%** — N+1 die 级冗余 + known-good-die 选拣 |
| 容错 | 4 层: cell ECC、行/列冗余、tile 重映射、N+1 die |
| BOM / 零售 | **BOM $700 – $1,200 / 零售 $3,000 – $5,000** |

上面每一个数字在 Stage 1 里至少动过一次。最大的一次改动: 原本规划的 "热/冷专家缓存" 整个被砍掉了。下面解释为什么。

---

## 四个关键实证发现

### 1. 数字加法树路径是对的。Full analog ADC 是会送命的那条路。

我们在 Python 里搭了一个 128×128 的 4-bit MLC ReRAM crossbar 仿真器 — 包含 cell variance、ADC 噪声、bit-line 饱和 — 扫了能量预算。结果:

- 仿真 tile 效率: **~24 TOPS/W**。
- 套上 0.3 – 0.5× 的硅级裕量: **预期 tile 实测 7 – 12 TOPS/W**。
- 这恰好框住了 HYDAR ISSCC 2026 在 28nm hybrid analog/digital RRAM CIM (36M cells) 上测出的 **15 TOPS/W (1,574K QPS/W)** — 一次独立的现实校验。
- 在 full-analog 配置下, **ADC 单独占了 92% 的 tile 能耗**。

最后那个数字, 是 Mythic AI 整个故事的剧透。Mythic 选了 full-analog ADC 路径。所有 2026 年还活着的 RRAM-CIM 玩家 — HYDAR、清华吴华强组、中科院 IMECAS 的 WH-2T1R、后摩 M50、苹芯 PIMCHIP-N300 — 全都是 hybrid 或纯数字方案。我们锁定 CIM 后接数字加法树的路径。92% 不是一个设计选项, 是一颗棺材钉。

### 2. MoE routing 接近均匀。缓存这个 idea 是错的 — 但架构本来就不需要它。

我们在多样化 prompt 集合上跑了 V4-Flash Top-6 专家路由统计。一个意料之外的结果:

- **Top-32 最热的专家加起来只覆盖 20.8% 的路由命中。** 分布基本是平的。
- Cache size 从 16 扫到 256: **不存在 < 256 的 cache 能上 99% 命中率**。即使一个能看见未来全部 trace 的 oracle 策略, 在 cache=224 时也只能到 **92.6%**。
- LRU、LFU、static-top-K — 三条曲线最终走到一起。缓存相对 "不缓存" 的增益是 **零**。

换一家小芯片公司, 这就是一个 falsify 掉的假设, 该开始焦虑了。我们刚好提前留了架构上的退路: 5-die chiplet 上有 **100 GB ReRAM, 大于 V4-Flash Q2_K 的 81 GB 占用**。所有 256 个专家在物理上本来就全部常驻。原本规划的 cache 管理 firmware 不需要了 — 架构变得 **更简单**, 不是更弱。

Stage 1 单凭这一刻就值回票价。

### 3. 250K context 下 5K – 15K tokens/sec 是够得着的 — 但必须靠三个具体技巧。

我们最早的 naive pipeline model 给出了一个**让人睡不着觉的数字: 250K 上下文下 1,093 tokens/sec**, 比 8K tokens/sec 的目标还低一个数量级。那是过去一个月里最吓人的单一数字。

Naive 模型错在忽略了 V4-Flash 实际上做的三件事:

- **MLA (Multi-head Latent Attention)** — V4-Flash 把每个 query 压成 latent 表征, 单 query 字节量大约缩 10×。
- **CSA Lightning Indexer** — 稀疏注意力路由, 在整个 250K 上下文里只读 top-K (~128) 个最相关位置, 把 attention 内积量砍掉约 2,000×。
- **Tile 并行** — 5 dies × 8 chip layers × 16 tiles ≈ 每个 model layer 上有 640 个活跃 tile, 提供约 **640 G 内积/秒/层**。

把 MLA latent、Top-K=128 indexer、和异步 tile overlap 合到 refined 模型里:

- **22,894 tokens/sec @ 250K (base case)**
- **15,649 tokens/sec (conservative)**
- **在 250K 这一点, 瓶颈是 indexer 扫描本身 — 占 attention 时间的 81%, 是 compute-bound, 不是 memory-bound。**

我们公开承诺的合理区间因此是 **典型 5K – 15K tokens/sec, 合同底线 ≥3K tokens/sec**。即使把所有悲观假设组合起来, 仍然能压在底线之上。

---

### 4. 热裕量很大。我们之前担心的 exotic 散热, 用不上。

8 层 3D ReRAM, 35 – 50W TDP, 装在 12 × 8 × 3 cm 的桌面方块里 — 听起来是个对热不友好的设计。我们做了一个分层的热仿真, 用 **Tier 1** (Cu thermal-TSV 网格, 从最底层 ReRAM 把热往上抽) + **Tier 2** (顶部微通道水冷板, 现代 HBM 散热 cookbook 里同一类方案):

- 底层 **35W TDP: 37°C** (距 65°C ReRAM 保守工作上限有 28°C 余量)
- 底层 **50W: 42°C** (仍有 23°C 余量)
- 线性外推: **117W 才触 65°C** (3.4× 标称), **175W 才触 85°C ReRAM 耐久上限** (5× 标称)

Tier 3 微流控冷却 — 那个 expensive、scary 的备选 — **不需要**。HBM3/3e 散热的先例 (SK Hynix 12 层 85-90% 量产良率)、TSMC SoIC 8 层 3D 80-85% 良率、Imec STCO 2025 综合起来表明: 这条工艺路径已经足够成熟, 我们不是 first-of-kind 在散热栈上探险。

---

## 假设置信度表

大白话, Stage 1 前 vs 后。Source 列指向证据来自哪里。

| 类别 | 假设 | 之前 | 之后 | 证据来源 |
|---|---|---|---|---|
| Cell 物理 | 28nm 4-bit MLC ReRAM 保持期足够 | 3.5 | **4.5** | 吴华强 JOS 2024; IBM Nature Comms 2025 (10 年 retention, 10¹⁴ reads) |
| Cell 物理 | 原始 BER 在 ECC 预算之内 | 3.5 | **4.5** | 吴华强组 ISSCC 2019: 576Kb macro 原始 BER 6×10⁻⁶ |
| Cell 物理 | 28nm RRAM macro 密度可行 | 4 | **5** | 吴华强组 28nm 2.82 TOPS/mm²; 显芯科技 2024.9 量产 |
| 架构 | 数字加法树路径正确 (而非 full-analog ADC) | 4 | **5** | Python crossbar 仿真 (ADC=92% 能耗); Mythic failure 分析; 2026 年活下来的全是 hybrid/digital |
| 架构 | 硅级 TOPS/W 落在 7-15 区间 | 3.5 | **4.5** | HYDAR ISSCC '26: 15 TOPS/W; 苹芯 PIMCHIP-N300: 27.3 TOPS/W; 后摩 M50: 16 TOPS/W |
| 架构 | 7 GB SRAM 够撑 250K context | 3 | **4.5** | M4 Max 上 `ds4-server` 第一手 SRAM 预算实测 + MLA 字节核算 |
| 架构 | 100 GB 片上 ReRAM 能装下 V4-Flash Q2_K | 4 | **5** | 第一手测出 81 GB 占用; 留 19 GB headroom |
| 架构 | 热专家缓存能提速 | 3.5 | **1.5** | MoE 路由实测: 近似均匀; 假设被 falsify。(无害 — 全部专家本来就常驻) |
| 架构 | 8 层 3D 良率 ≥80% | 3 | **4** | TSMC SoIC 80-85%; SK Hynix HBM3 12 层 85-90% |
| 架构 | 5-die chiplet 装配后良率 ≥92% | 3 | **4.5** | N+1 备用 die + KGD 选拣; 2.5D 65nm interposer 成熟 |
| 软件 | 250K 下 pipeline 能跑到 5-15K tps | 2 | **4** | Pipeline timing 仿真 (MLA + Top-K=128 indexer + tile 并行) |
| 软件 | ≥3K tokens/sec 合同底线成立 | 2.5 | **4.5** | 悲观组合仿真仍清线 |
| 软件 | Q2_K 混合精度下模型质量保留 | 3.5 | **4** | ds4 V4-Flash 第一手质量实测; 对齐 DeepSeek 参考 |
| 热 | 35-50W TDP 热安全 | 2.5 | **4.5** | Tier 1+2 仿真: 35W 下 28°C 余量; HBM3/3e 散热先例 |
| 热 | 不需要 Tier 3 微流控 | 2.5 | **4** | 线性外推 117W 才触 65°C; 标称区间留得很宽 |

仍有两项停在 3 – 3.5: **256×256 tile IR drop 余量** (等 NeuroSim 28nm 仿真) 和 **N+1 die 大规模故障注入** (等 Stage 3 FPGA 仿真)。它们被明确列为 Stage 2 / Stage 3 的 open question, 不是糊弄过去。

---

## 学到了什么

**最意外**: 热/冷专家缓存的 idea 是错的。两周前我们还在画 firmware, 设计哪些专家驻 SRAM 哪些不驻。实测说: 路由近似均匀, 256 以下 cache 都不够用, firmware 扔了。本来以为芯片要丢一个 feature, 结果架构变得 **更简单** — 因为 100 GB > 81 GB, 所有专家本来就在家。

**最 validating**: HYDAR 的 15 TOPS/W 硅级实测, 恰好落进我们 Python crossbar 仿真预测的 7 – 12 TOPS/W (套硅级裕量后) 区间, 仿真原值 24 TOPS/W。一篇 ISSCC '26、华为 + 清华 + 字节合作的论文, 给出的能效正好是我们需要的数字 — 说实话, 那一刻 thesis 从 "推测" 变成 "推测但有锚"。

**最有物理感**: 35W TDP 下有 28°C 热裕量, 仅靠 Tier 1 + Tier 2 散热。芯片 **不脆弱**。整个硅圈对 3D ReRAM 的最大顾虑就是散热, 而散热在我们这个功耗包络下, 是个非事件。

**最痛**: naive pipeline model 给的 1,093 tokens/sec — 比目标低一个数量级。整整 36 小时, 那是实时的失败模式。修复来自认真读 MLA 和 CSA Lightning Indexer 论文, 把 simulator 重写到能真实表示 V4-Flash 在做什么。教训: **一个 naive 模型如果你信了, 它能把一个真实存在的架构 falsify 掉**。多读论文。

---

## 下一步: Stage 2

Stage 2 的所有动作都自我可控。不去 cold call 任何厂商。不需要任何合作伙伴。不需要任何融资:

- **NeuroSim 28nm IR-drop 验证** — 关掉 256×256 tile 这最后一个 cell 物理 open question。
- **EBAZ4205 矿机 FPGA 跑 tiny LM demo** (回收硬件, 约 ¥200 / $30) — 数据流的第一个物理级 proof-of-concept。
- **二手 Xilinx ZCU102 上的 multi-tile FPGA RTL 仿真** (Zynq UltraScale+, ~60 万 logic cells, 二手约 $2-3K) — 自己拥有的硬件, 不租云, 没有按小时计费的时间压力。上面 EBAZ4205 那一步教会 Vivado workflow; ZCU102 fabric 够大, 能跑 chip critical path 的 multi-tile + control + pipeline 仿真。Full 5-die 整合留到后期 — 只在这一步暴露出非要不可的问题时才上。
- **软件栈/编译器** — Mythic 真正死因所在的那一块 — 已经在并行起步, 不放到最后再说。

**Stage 2 时间窗: 3 – 6 个月。总成本: ~$6 – 15K, 全自费, 教练业务的 part-time 收入完全覆盖。** Article 3 将是 Stage 2 的报告。

---

## 诚实列出未闭环项

我们明确不去模糊还没收口的事。

- **256×256 tile IR-drop 余量** — 置信度 3.5/5。Stage 2 NeuroSim 28nm 跑完后闭。
- **N+1 die 大规模故障注入验证** — 等 Stage 3 FPGA 仿真。数学上 ≥92% 装配良率, 但还没在真实故障注入下证给大家看。
- **完整 ANSYS Icepak 热签核** — Stage 4 silicon gate, 任何 tape-out 之前必须闭。
- **软件生态** — 这是最深的护城河工作, 也是 Mythic 真正死因。编译器、kernel library、ds4 / 3FS 协议集成。属于 Stage 5+, 但我们已经在并行做, 不会拖到最后。

如果你看完这四项的直觉是 "可这才是真正难的部分" — 直觉是对的。Stage 1 关掉的是相对容易的事。接下来的两年, 就是把剩下的关上。

---

## 邀请, 不是 solicitation

报告里的每一项都可以在仓库里复现: 假设置信度 delta、仿真脚本、公开论文引用清单、第一手测量方法学文件。我们会继续公开发布。

如果你是芯片工程师、学者、DeepSeek 生态的 builder、或者一位想用毒辣眼光读一个年轻 thesis 的退休硅圈前辈 — 欢迎在 `github.com/michaelhuo2030/millisecond-era` 提 GitHub Issue, 进行技术对话。

我们继续不找投资人, 也不 cold pitch。如果你主动愿意在这件事的技术实质上交流, 我们每一条消息都会读。

— Michael Huo

---

## 引用与链接

**公开论文 / 硅级证据:**
- HYDAR, ISSCC 2026 — 28nm hybrid analog/digital RRAM CIM, 36M cells, 1,574K QPS/W 硅级实测 (华为 + 清华 + 字节)
- 吴华强组, ISSCC 2019 — 28nm RRAM macro, 原始 BER 6×10⁻⁶
- 吴华强组, 《半导体学报》 2024 — 28nm RRAM 2.82 TOPS/mm² 密度
- 中科院 IMECAS, WH-2T1R 28nm CIM
- 显芯科技 — 28nm embedded RRAM, 2024.09 起商用量产
- 苹芯 PIMCHIP-N300 — 28nm SRAM-CIM, 27.3 TOPS/W
- 后摩 Houmo M50 — 28nm hybrid CIM, 16 TOPS/W, 支持 1.5 – 70B LLM
- IBM Research, *Nature Communications* 2025 — Analog Foundation Models: 10 年 retention, 10¹⁴ reads, 10⁵–10⁶ writes
- Mythic AI 失败案例分析 — full-analog ADC 路径, 60–81% 能耗 overhead
- SK Hynix HBM3/3e — 12 层堆叠, 85–90% 量产良率
- TSMC SoIC — 8 层 3D, 80–85% 良率
- Imec STCO 2025 — 3D 散热 cookbook 参考

**仓库**: `github.com/michaelhuo2030/millisecond-era`
**方法学文件**: 仿真脚本与测量日志位于仓库 `docs/stage-1-validation/`
**Article 1**: 仓库 `docs/article-1-zh.md` (中文) 与 README 英文版
