# RWKV 能力全景图 — 第三方调研

> ⚠️ **整张表是关于 [RWKV](https://github.com/BlinkDL/RWKV-LM) 生态的第三方调研——下面每一个数字、每一条结论，都是别人的工作（论文 / 产品 / 官方），不是我们的实测。** 我们自己实测的东西严格分开放：四道实测闸在 [`README.md`](README.md)，我们自己的三值 RTL 在真硅上跑的结果在 [`../fpga/SILICON-MEASURED-2026-06-13.md`](../fpga/SILICON-MEASURED-2026-06-13.md)。别把「我们实测的」和「别人声称的」混在一起。
>
> **出处全部做成了可点的链接**（论文 / 代码 / App，直接点表格里的链接就能跳到原始来源）。**已于 2026-06-14 逐条核对**——每篇论文 / 每个页面都打开过，标题、关键数字、发表场所都对着原始来源确认过，全部能打开（无杜撰）。

---

## 这张表的成熟度怎么标（一眼看清「能信几分」）

| 标记 | 含义 |
|---|---|
| **已上架** | 实际产品 / 已发布模型，能直接用 |
| **研究** | 有论文 / 有结果，但未必有现成产品 |
| **早期** | 只有 demo，或只有单一来源的数据，待更多验证 |
| **缺席 / 落后** | RWKV 在这块基本没人做，或明显输给别的架构（Mamba / Transformer）|

---

## 为什么发这张表（定位）

我们押 RWKV，**不是**因为它单点最强（它不是——前沿规模、代码、基因领域它都落后）。是因为**同一个轻量线性时间引擎，被移植到了几乎所有模态，而每个领域的赢点都是同一组物理：效率 / 恒定内存 / 流式 / 端侧 / 高并发**——正是我们三值芯片放大的那几条。

**这张表是「为什么一块端侧芯片值得押 RWKV」的证据，不是「RWKV 打败了谁」的炫耀。** 我们诚实地保留它弱的、缺席的行——那本身就是可信度。（提醒：我们的芯片是**通用三值推理底座**，能跑各类三值化模型；RWKV 只是契合度最高的研究案例，不是芯片只能跑 RWKV。）

---

## 能力地图（每行带成熟度 + 可点出处）

| 领域 | 最强证据（第三方） | 成熟度 | 出处（可点）|
|---|---|---|---|
| 高并发多 agent | 单流 ~145 tok/s → batch960 ~10,250 tok/s（RWKV7 7.2B fp16，单 RTX 5090，厂商基准）| 早期·厂商单源 | [Albatross](https://github.com/BlinkDL/Albatross) |
| 视觉骨干 | Vision-RWKV 平 / 超 ViT 同参；高分辨率（2048²）下显著更快 / 更省内存；ImageNet VRWKV-T 75.1 vs DeiT-T 72.2 | 研究·ICLR'25 Spotlight | [论文](https://arxiv.org/abs/2403.02308) · [代码](https://github.com/OpenGVLab/Vision-RWKV) |
| 时间序列 | BlackGoose Rimer ~1/23 参数、4.5× 快；FRWKV 8 数据集平均第一；RWKV-TS 全任务 ≈ SOTA | 研究 | [Rimer](https://arxiv.org/abs/2503.06121) · [FRWKV](https://arxiv.org/abs/2512.07539) · [RWKV-TS](https://arxiv.org/abs/2401.09093) |
| 嵌入 / 检索 | EmbeddingRWKV 1.4B 近 top 嵌入器（MTEB-EN 均值）；可复用状态 5.4–44.8× 重排加速 | 研究 | [论文](https://arxiv.org/abs/2601.07861) · [代码](https://github.com/howard-hou/EmbeddingRWKV) |
| 端侧语音 / 音乐 | RWKV Music（离线作曲，已上架）、RWKV App（Chat+TTS+图像理解，全离线 on-device，已上架；README 未列 ASR/OCR）；流式 ASR（研究）低延迟、精度 ≈ conformer | 已上架 + 研究 | [Music App](https://apps.apple.com/gb/app/rwkv-music/id6739768807) · [RWKV App](https://github.com/RWKV-APP/RWKV_APP) · [流式 ASR](https://arxiv.org/abs/2309.14758) |
| 数学 / 推理 | RWKV7 **g0b-13.3b**（基座系列）：GSM8K 0.923、MMLU 0.765、MATH500 0.768（同尺寸有竞争力；**评测协议未注明 pass@1 / maj@k**）| 已发布 | [RWKV-Evals](https://wiki.rwkv.com/basic/RWKV-Evals) |
| 语音 ASR | WorldRWKV LibriSpeech test-clean 2.43% WER（近 Whisper-large 区）| 研究 | [WorldRWKV](https://github.com/Joluck/WorldRWKV) |
| TTS | RWKVTTS（用 RWKV-7 替换 Fish-Speech / CosyVoice 的语言模型）；无硬 MOS / WER | 研究·早期 | [论文](https://arxiv.org/abs/2504.03289) · [代码](https://github.com/yynil/RWKVTTS) |
| 音乐（研究）| MIDI-RWKV ~38M 参数、无限上下文 infilling（内部 base / LoRA / state-tuned 听测，**未对比 Transformer 基线**）| 研究 | [论文](https://arxiv.org/abs/2506.13001) |
| 医学影像 | Restore-RWKV 1.16M 参数追平 SOTA（PET / CT / MRI）| 研究·IEEE JBHI | [论文](https://arxiv.org/abs/2407.11087) · [代码](https://github.com/Yaziwel/Restore-RWKV) |
| 点云 3D | PointRWKV 超 Transformer + Mamba 同类（ModelNet40 / ShapeNetPart）| 研究 | [论文](https://arxiv.org/abs/2405.15214) · [代码](https://github.com/hithqd/PointRWKV) |
| 视觉-语言 VLM | VisualRWKV / ModRWKV ≈ LLaVA-1.5；**OCR / 文字弱**，落后 Qwen-VL / InternVL | 研究·落后前沿 | [VisualRWKV](https://arxiv.org/abs/2406.13362) · [ModRWKV](https://arxiv.org/abs/2505.14505) |
| 图像生成 | Diffusion-RWKV ≈ DiT 质量、~30–40% 省 FLOPs（近似）| 研究·跟随 | [论文](https://arxiv.org/abs/2404.04478) |
| 图文检索 CLIP | RWKV-CLIP 论文称同尺度 SOTA（linear-probe / zero-shot 检索）| 研究·EMNLP'24 | [论文](https://arxiv.org/abs/2406.06973) · [代码](https://github.com/deepglint/RWKV-CLIP) |
| **代码** | 有 HTML 生成 demo；**无专门 coder 模型、无 HumanEval / MBPP benchmark** | 早期·**落后** | [demo](https://huggingface.co/spaces/BlinkDL/RWKV-Gradio-2) |
| **强化学习 / 机器人** | Decision-RWKV 等 ~2 篇；主流 Decision-Transformer-vs-Mamba 研究**不带 RWKV**；领域站队 Mamba | 研究·**落后** | [Decision-RWKV](https://arxiv.org/abs/2407.16306) · [KAN We Flow](https://arxiv.org/abs/2602.01115) |
| **基因 / DNA / 蛋白 / 化学** | **基本缺席，或只是被 Mamba / HyenaDNA / Caduceus 打败的 baseline**；恒定内存的教科书用例没吃到 | **缺席 / 落后** | [Caduceus 背景](https://arxiv.org/abs/2403.03234) |
| 视频理解 | 基本无专门、有 benchmark 的工作 | **缺席** | — |

---

## 两条必须点名「未经证实」的（旗舰仓库尤其谨慎）

- **「rwkv.cpp 随 Windows + Office 分发到 ~15 亿（1.5 billion）系统」** — **未经证实**。来源是 [RWKV 团队自己反编译 Windows / Office 二进制发现](https://blog.rwkv.com/p/rwkvcpp-shipping-to-half-a-billion)，**微软从未公开确认用途**；「二进制随分发」≠「活跃 RWKV 推理量」。准确说法是「据 RWKV 团队反编译，rwkv.cpp 出现在 Windows / Office 分发中（微软未确认用途）」，**不能写成「微软在用 RWKV」**。
- **RWKV-8「ROSA」**（永不遗忘 / 无限上下文 / 替代注意力）— **未经证实**。截至本表[只有公告 + 概念](https://wiki.rwkv.com/basic/architecture.html)，无收敛的公开模型 / 同行评审定论；现有 [ROSA-Tuning 原型](https://github.com/zyaaa-ux/ROSA-Tuning)是**架在 Qwen3 上、未训练到收敛**。只能写「路线图方向，权重未发布前不作能力证据」。

> 对照——这条是**真的**：RWKV 在 2023/09 成为 [Generative AI Commons（Linux Foundation / LF AI & Data 旗下）下首个 AI 模型](https://lfaidata.foundation/projects/rwkv/)，孵化阶段。

---

## 想深挖的延伸链接

- RWKV-7「Goose」论文（超 TC⁰ / state-tracking）：[arXiv 2503.14456](https://arxiv.org/abs/2503.14456)
- RWKV 综述：[A Survey of RWKV（arXiv 2412.14847）](https://arxiv.org/abs/2412.14847)
- 视觉方向聚合清单：[Awesome-RWKV-in-Vision](https://github.com/Yaziwel/Awesome-RWKV-in-Vision)
- 社区项目大全（~90 个）：[RWKV community links](https://wiki.rwkv.com/community/links.html)

*成熟度分级与「该信几分」的判断是我们的；具体数字与结论属于各来源（链接里可自行核对）。发现任何对不上的，请[开 issue](https://github.com/michaelhuo2030/millisecond-era/issues)，我们当场改。*
