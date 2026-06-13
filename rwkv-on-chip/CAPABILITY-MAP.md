# RWKV Capability Map — third-party survey · RWKV 能力全景图（全 [EXTERNAL]）

> ⚠️ **这是一份关于 RWKV 生态的第三方调研。表里所有数字/结论都是别人的工作（论文 / 产品 / 官方），不是我们的实测。**
> 我们只做三件事：分级（[SHIPPED]/[RESEARCH]/[EARLY]/[ABSENT]）+ 每条标出处 + 把吹的部分标 [UNVERIFIED]。
>
> **This is a third-party survey of the RWKV ecosystem — every figure below is someone else's work (papers/products/official), NOT our measurement.** Our own *measured* work is kept strictly separate: see the four measured gates in [`README.md`](README.md) and our own ternary RTL running on real silicon in [`../fpga/SILICON-MEASURED-2026-06-13.md`](../fpga/SILICON-MEASURED-2026-06-13.md). Don't conflate "ours, measured" with "theirs, claimed."
>
> **Sources link-checked 2026-06-14** — every paper/page was opened and its title, key number, and venue confirmed against the primary source; all references resolve (no fabrications). A handful of upstream over-statements were corrected or softened in this version.

---

## 为什么发这张表（定位）· Why this map

我们押 RWKV，**不是**因为它单点最强（它不是——前沿规模、代码、基因领域它落后）。是因为**同一个轻量线性时间引擎被移植到了几乎所有模态，而每个领域的赢点都是同一组物理：效率 / 恒定内存 / 流式 / 端侧 / 高并发**——正是我们三值芯片放大的那几条。

**这张表是"为什么一块端侧芯片值得押 RWKV"的证据，不是"RWKV 打败了谁"的炫耀。** 我们诚实地保留它弱的、缺席的行——那本身就是可信度。（同样提醒：我们的芯片是**通用三值推理底座**，能跑各类三值化模型；RWKV 是契合度最高的研究案例，不是芯片只能跑 RWKV。）

---

## 能力地图（每行带成熟度 + 出处）· Capability map

| 领域 | 最强证据（[EXTERNAL]） | 成熟度 | 出处 |
|---|---|---|---|
| 高并发多 agent | 单流 ~145 tok/s → batch960 ~10,250 tok/s（RWKV7 7.2B fp16，单 RTX 5090，厂商基准） | [EARLY]·厂商单源 | [R1] |
| 视觉骨干 | Vision-RWKV 平/超 ViT 同参；高分辨率(2048²)下显著更快/更省内存（倍数为论文近似）；ImageNet VRWKV-T 75.1 vs DeiT-T 72.2（实证） | [RESEARCH]·ICLR'25 Spotlight | [R2] |
| 时间序列 | BlackGoose Rimer ~1/23 参数、4.5× 快；FRWKV 8 数据集平均第一；RWKV-TS 全任务≈SOTA | [RESEARCH] | [R3][R4][R5] |
| 嵌入/检索 | EmbeddingRWKV 1.4B 近 top 嵌入器（MTEB-EN 均值）；可复用状态 5.4–44.8× 重排加速 | [RESEARCH] | [R6] |
| 端侧语音/音乐 | RWKV Music（离线作曲，已上架）、RWKV App（Chat+TTS+图像理解，全离线/on-device，已上架；README 未列 ASR/OCR）；流式 ASR(研究)低延迟、精度≈conformer | [SHIPPED]+[RESEARCH] | [R7][R8][R9] |
| 数学/推理 | RWKV7 **g0b-13.3b**（基座系列）：GSM8K 0.923、MMLU 0.765、MATH500 0.768（同尺寸有竞争力；**评测协议未注明 pass@1/maj@k**） | [SHIPPED] | [R10] |
| 语音 ASR | WorldRWKV LibriSpeech test-clean 2.43% WER（近 Whisper-large 区） | [RESEARCH] | [R11] |
| TTS | RWKVTTS（RWKV-7 替换 Fish-Speech/CosyVoice 的 LM）；无硬 MOS/WER | [RESEARCH/EARLY] | [R12] |
| 音乐(研究) | MIDI-RWKV ~38M 参数、无限上下文 infilling（内部 base/LoRA/state-tuned 听测，**未对比 Transformer 基线**） | [RESEARCH] | [R13] |
| 医学影像 | Restore-RWKV 1.16M 参数追平 SOTA（PET/CT/MRI） | [RESEARCH]·IEEE JBHI | [R14] |
| 点云 3D | PointRWKV 超 Transformer+Mamba 同类（ModelNet40/ShapeNetPart） | [RESEARCH] | [R15] |
| 视觉-语言 VLM | VisualRWKV/ModRWKV ≈ LLaVA-1.5；**OCR/文字弱**，落后 Qwen-VL/InternVL | [RESEARCH]·落后前沿 | [R16][R17] |
| 图像生成 | Diffusion-RWKV ≈ DiT 质量、~30–40% 省 FLOPs（近似） | [RESEARCH]·跟随 | [R18] |
| CLIP/嵌入(图) | RWKV-CLIP 论文称同尺度 SOTA（linear-probe / zero-shot 检索） | [RESEARCH]·EMNLP'24 | [R19] |
| **代码** | 有 HTML 生成 demo；**无专门 coder 模型、无 HumanEval/MBPP benchmark** | [EARLY]·**落后** | [R20] |
| **RL/机器人** | Decision-RWKV 等 ~2 篇；主流 Decision-Transformer-vs-Mamba 研究**不带 RWKV**；领域站队 Mamba | [RESEARCH]·**落后** | [R21][R22] |
| **基因/DNA/蛋白/化学** | **基本缺席，或只是被 Mamba/HyenaDNA/Caduceus 打败的 baseline**；恒定内存的教科书用例没吃到 | **[ABSENT]/落后** | [R23] |
| 视频理解 | 基本无专门、有 benchmark 的工作 | **[ABSENT]** | — |

---

## 必须标 [UNVERIFIED] 的两条（旗舰仓库尤其谨慎）· Explicitly [UNVERIFIED]

- **"rwkv.cpp 随 Windows+Office 分发到 ~15 亿（1.5 billion）系统"** — `[UNVERIFIED]`。来源是 **RWKV 团队自己反编译 Windows/Office 二进制发现**，**微软从未公开确认用途**；"二进制随分发"≠"活跃 RWKV 推理量"。措辞用"据 RWKV 团队反编译，rwkv.cpp 出现在 Windows/Office 分发中（微软未确认用途）"，**不要写成"微软在用 RWKV"**。[R24]
- **RWKV-8 "ROSA"**（永不遗忘 / 无限上下文 / 替代注意力）— `[UNVERIFIED]`。截至本表**只有公告 + 概念，无收敛的公开模型/同行评审定论**；现有 ROSA-Tuning 原型是**架在 Qwen3 上、未训练到收敛**。写"路线图方向，权重未发布前不作能力证据"。[R25][R26]

（对照：**真的** — RWKV 2023/09 成为 **Generative AI Commons（Linux Foundation / LF AI & Data 旗下）下首个 AI 模型**，孵化阶段。[R27]）

---

## References（link-checked 2026-06-14）

- [R1] Albatross 高并发推理（厂商基准；145 / 10,250 tok/s 的 verbatim 源）— https://github.com/BlinkDL/Albatross （+ RWKV-LM README）
- [R2] Vision-RWKV（ICLR 2025 Spotlight）— arXiv 2403.02308 · https://github.com/OpenGVLab/Vision-RWKV
- [R3] BlackGoose Rimer — arXiv 2503.06121
- [R4] FRWKV — arXiv 2512.07539
- [R5] RWKV-TS — arXiv 2401.09093 · https://github.com/howard-hou/RWKV-TS
- [R6] EmbeddingRWKV — arXiv 2601.07861 · https://github.com/howard-hou/EmbeddingRWKV
- [R7] RWKV Music app — https://apps.apple.com/gb/app/rwkv-music/id6739768807
- [R8] RWKV App（端侧 Chat/TTS/图像理解）— https://github.com/RWKV-APP/RWKV_APP
- [R9] 流式 RWKV transducer ASR — arXiv 2309.14758
- [R10] 评测数字来源 — https://wiki.rwkv.com/basic/RWKV-Evals （评分行 = RWKV7-g0b-13.3b；HF https://huggingface.co/BlinkDL/rwkv7-g1 本身不含 benchmark 数字）
- [R11] WorldRWKV — https://github.com/Joluck/WorldRWKV
- [R12] RWKVTTS — arXiv 2504.03289 · https://github.com/yynil/RWKVTTS
- [R13] MIDI-RWKV — arXiv 2506.13001
- [R14] Restore-RWKV — arXiv 2407.11087（IEEE JBHI 生物医学与健康信息学）· https://github.com/Yaziwel/Restore-RWKV
- [R15] PointRWKV — arXiv 2405.15214 · https://github.com/hithqd/PointRWKV
- [R16] VisualRWKV — arXiv 2406.13362（COLING 2025）
- [R17] ModRWKV — arXiv 2505.14505（EMNLP 2025 Main，ACL Anthology 2025.emnlp-main.204）
- [R18] Diffusion-RWKV — arXiv 2404.04478
- [R19] RWKV-CLIP — arXiv 2406.06973（EMNLP 2024）· https://github.com/deepglint/RWKV-CLIP
- [R20] RWKV-7 G1g HTML 生成 demo — https://huggingface.co/spaces/BlinkDL/RWKV-Gradio-2
- [R21] Decision-RWKV — arXiv 2407.16306 · https://github.com/ancorasir/DecisionRWKV
- [R22] KAN We Flow?（RWKV 视觉运动策略，ICRA 2026）— arXiv 2602.01115
- [R23] 基因组 SSM 背景（RWKV 缺席/仅作被超 baseline）— arXiv 2403.03234（Caduceus）+ HyenaDNA + Mamba
- [R24] rwkv.cpp 出现在 Windows 分发（团队反编译，微软未确认）— https://blog.rwkv.com/p/rwkvcpp-shipping-to-half-a-billion
- [R25] RWKV-8 / ROSA 架构说明 — https://wiki.rwkv.com/basic/architecture.html
- [R26] ROSA-Tuning 原型（架在 Qwen3）— https://github.com/zyaaa-ux/ROSA-Tuning
- [R27] RWKV 加入 Linux Foundation（Generative AI Commons 下首个 AI 模型，2023/09）— https://lfaidata.foundation/projects/rwkv/
- [R28] RWKV-7 "Goose"（超 TC⁰ / state-tracking）— arXiv 2503.14456
- [R29] A Survey of RWKV — arXiv 2412.14847
- [R30] Awesome-RWKV-in-Vision — https://github.com/Yaziwel/Awesome-RWKV-in-Vision
- [R31] RWKV 社区项目链接 — https://wiki.rwkv.com/community/links.html

*分级与出处是我们的；数字与结论是各来源的。发现任何对不上的，请开 issue，我们当场改。*
