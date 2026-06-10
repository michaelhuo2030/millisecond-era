# ADR-v1 — What chip do we build first, and how

> **Architecture Decision Record · 2026-06-05 · status: ACCEPTED (provisional — 3 blockers flagged below)**
>
> Synthesizes the whole program into ONE concrete first-chip decision. Built on:
> `CHIP-FEASIBILITY-LEDGER-2026-06-03.md` (6-dim verdict) · `reram-kb/reram_world.json` (belief graph + cap formula) ·
> `digital-speed-estimate/VERDICT-cross-validation.md` (digital 1B ≈ 1–4k tok/s) ·
> `ternary-foundation/results/D2-FAIR-READOUT-VERDICT-2026-06-03.md` (ternary edge = density 7× + no-ADC + ~3–5× tail noise) ·
> `CHIP-FAMILY-MASTER-DIGEST-2026-06-01.md` (SKU history; Path-1 hybrid) · industry expert consultation (MPW economics, 3D access).
>
> Calibration discipline (Michael): hold ranges, never false-precise; flag every load-bearing number we don't have;
> ">2× magnitude = bug"; measured ≠ expected; the binding constraint has already moved from device physics to **market + 3 specific numbers**.

> **Public version:** private expert-consultation attributions and specific partner-engagement details have been removed; the technical analysis is unchanged.

---

## TL;DR — the v1 decision in 5 lines

1. **v1 product target** = a **4B train-time-ternary text LLM (~1 GB), weights resident on-chip**, digital SPIKA binary-cell CIM (2-state cells, ± adjacent columns, 5-bit counter, **NO ADC, bit-exact digital readout**) — NOT 8B, NOT 9B-Q4, NOT analog.
2. **Capacity path** = **(a) N single-layer planar dies side-by-side (2.5D, compute-near-data)** as the v1 baseline; hybrid-bonded 3D **deferred to v2** (small-team access + cost not yet real — blocker #3).
3. **But we do NOT tape out the product first.** v1 first silicon = a **single-die MPW test-tile of one ternary SPIKA macro** (~1–5 mm², modest size, e.g. a 64×128 → scaled tile), to prove the core thesis (digital-readout ternary CIM works at node) **cheaply** before committing multi-die money.
4. **Tape-out path** = **MPW shuttle via broker → SMIC/Huahong 28nm** (~¥50万, ±20% sim-vs-silicon, ~3-month return, 1–2yr iteration loop); **free open-PDK shuttle** (Hangzhou/Zhejiang, TinyTapeout-class) as the **¥0 warm-up** for the digital-only logic.
5. **The chip is the easy half.** The hard half is **market/survival** (market validation is the binding constraint — demand unproven, buyer/price not yet defined) — and **3 missing numbers** gate the architecture (domestic-ReRAM single-layer density = the 60× open question; FPGA P×util; hybrid-bonding access/cost). Build the test-tile AND chase a paying pre-silicon revenue path in parallel.

---

## 1. The v1 chip

### 1.1 Model — DECISION: **4B train-time-ternary (text), ~1 GB resident**

**Decision.** The v1 product runs a **4B-parameter train-time-ternary {−1,0,+1} text model (~1 GB on-chip)** as the *fitting + useful* primary. 8B (~1.8 GB) is the **stretch** (one density notch up); 9B-Q4 (5.5 GB) is **rejected**.

**Rationale.**
- **It fits, robustly.** cap_mini honest range = **0.4–2.4 GB** (an industry CIM-integrated reading 1.63 Mb/mm², not NeuroSim's optimistic 5.58). 1 GB fits across *most* density scenarios with a couple of dies; 9B-Q4 (5.5 GB) **never fits** (formula `fit_9B = cap − 5.5` = −5.4…−1.6 GB → always negative). Picking 4B means capacity stops being a coin-flip.
- **Quality is MEASURED, not borrowed.** Train-time ternary ≈ fp16 is now in-repo: BitCPM-CANN-8B ppl **8.80 vs fp16 sibling 9.50** (−7.4%, on-par; claim A, 2026-06-03). The keystone graduated from literature to measurement. Honest framing: **near-lossless / on-par, NOT "beats fp"** — and gate-1 lit says ternary quality is SOLID ≤8B (BitNet b1.58 2B4T within 1–2 pts of fp16 SOTA), so a 4B ternary is squarely in the proven-useful zone.
- **8B is the same architecture, one density notch up** → no re-design to scale v1→v1.5 once density resolves. That's why we keep it as the named stretch rather than a different model.

**Alternatives rejected.**
- **9B-Q4 (5.5 GB, the old Mini headline).** Rejected: physically never fits the honest cap; was a coin-flip at +1.5% margin even under the *optimistic* NeuroSim density that has since been down-revised. Don't ship a model that needs the best-case of every unverified knob to simultaneously hold.
- **Post-training-quantized ternary.** Rejected: measured garbage (post-hoc ternary = junk output, repeatedly). Near-lossless **requires train-time** ternary. Non-negotiable.
- **30–70B ternary (Pro-class).** Rejected for v1: no released+benchmarked ternary model >8B exists yet; needs multi-die + 3D we're deferring. Later SKU once first silicon proves out (合抱之木生于毫末).
- **Multimodal / 9B dense headline.** Rejected: the noise-validated model (ternary text) ≠ the advertised model (9B multimodal). Don't fuse two models into one claim.

### 1.2 Compute path — DECISION: **digital SPIKA binary-cell CIM, no ADC**

**Decision.** Weights map onto **2-state (binary) ReRAM cells**, positive/negative weights in **adjacent columns**, every 2 columns share a **5-bit up/down counter** → subtraction is natural, readout is a **threshold comparator + counter, NO dedicated ADC block**. (SPIKA, Frontiers Electronics 2025 — demonstrated at 180 nm, 195 TOPS/W.) **⚠️ CORRECTED 2026-06-09 (peripheral pressure-test, `CHIP-STRUCTURE-1B-SKU.md` §C / `reram-kb/SPIKA-PERIPHERAL-READOUT-SCALING-2026-06-09.md`): the counter is NOT "bit-exact" — it is a COARSE (~5-bit) charge-domain quantization of the partial sum (a counting-ADC without a dedicated ADC block). Counter bits must scale with accumulation depth (+1 bit per row-doubling → 256-row tile = 7-bit). The earlier 8B-clean-8.733 ppl modeled IDEAL accumulate; a partial-sum-quantization ppl sweep is now DONE — **D5 (2026-06-09, real 8B ternary, POC): 7-bit counter @256-accumulation = +0.7% ppl (within the +3.2% stuck-at budget), but the nominal 5-bit counter BREAKS (+4.0%) → v1 peripheral spec = ≥7-bit UP/DOWN counter** (mild area cost; the no-ADC area win survives). Binding axis = counter bits, not accumulation depth. "No dedicated ADC block / digital readout / counter-subtraction is exact" all stay true; "bit-exact accumulate" does not.**

**Rationale.**
- **Digital readout beats analog — settled.** Bit-exact, no ADC, fast-enough, and it reclaims ~half the die (ADC = 20–45% area + ≈ adder-tree power). The "digital vs analog" speed question is *closed*: digital 1B ≈ 1–4k tok/s (§1.4) is already 20–400× past the interactive line, and analog's ADC is itself a latency bottleneck — no reason to pay analog's precision/area/cost/risk for speed we don't need.
- **Binary cells sidestep the #1 device pain.** A 3-level single cell is hard to read — multilevel read errors are a well-known, months-long failure mode. The SPIKA differential-column scheme keeps **cells binary** (easiest, most robust) and gets ternary at the *encoding* level — resolving the `ternary_cell_path` GAP from OPEN → lit-demonstrated.
- **Ternary's real edge on THIS substrate is geometry, stated honestly.** Per D2's fair re-audit: the headline edge is **DENSITY (2 cells/weight vs honest bit-sliced INT8 ~14 ≈ 7×) + NO ADC (net 13% smaller tile)**. The noise advantage is **real but modest (~3–5×, NOT the retracted 10–20×)** and lives in the **tail / aging / stuck-at** regime — at the device-realistic operating point (σ_rel 0.1–0.2) the 75× binary margin makes BOTH arms noise-immune. So: R1 analog-precision risk is mitigated **primarily by binary-cell + exact-digital readout**; ternary adds a modest tail/SAF bonus. **Stop selling "ternary shrugs off noise that kills INT8."** The moat is density + no-ADC + train-time near-lossless.

**Alternatives rejected.**
- **Analog multilevel CIM (ADC sense).** Rejected: ADC area/power/latency, conductance drift on 16 close levels (4-bit MLC retention ~2h@125C — risky), and the noise margin we'd be buying it for evaporates under fair test. Net 13% *worse* tile area than the SPIKA differential path.
- **3-level single cell.** Rejected: the known multilevel hazard (noise margin cut into thirds; a months-long read-error swamp) + we don't need it — differential binary columns give ternary for free.

### 1.3 Capacity path — DECISION: **(a) 2.5D N single-layer planar dies side-by-side for v1; (b) hybrid-bonded 3D deferred to v2**

**Decision.** v1 baseline = **N single-layer planar dies, side-by-side in one package (2.5D), compute-near-data** (each die = SPIKA CIM, weights resident, no streaming). Hybrid-bonded dense-memory-die-under-compute-die (3D) is the **right long-term escape from the iron tradeoff** but is **deferred to v2**.

**Rationale.**
- **Single-layer planar is the only thing you can actually buy/tape-out today.** Verified by two web passes + expert input: NO multi-layer ReRAM has ever been mass-produced anywhere; monolithic 6-layer 3D-CIM is lab-only (best CIM stack = 128 Kbit). Real, purchasable ReRAM (Fujitsu/RAMXEED MB85AS, domestic 28nm ReRAM) is **single-layer**. So v1 capacity = single-layer density × **die count**, packaged 2.5D.
- **The iron tradeoff (reram-kb L625) is unavoidable but survivable at 4B.** More density = fewer ADC = lower peak speed; we're already ADC-free (sense-amp/counter) which *relaxes* it toward the dense end. Die count = 8192 Mbit ÷ density: **~2–3 dies at the optimistic 6 Mb/mm², but ~6–15 single-layer dies at the pessimistic 1.6** (1 GB @ 1.6 ≈ **~5,000 mm²**, and a single die can't exceed ~one reticle ≈ 800 mm²). ⚠️ **Corrected 2026-06-08 (Michael caught it):** the earlier "~2–4 dies even at pessimistic" was WRONG — it only holds at the optimistic density. The honest spread matches ledger #9 ("1 die dense-storage-but-slow → ~15 dies CIM-1.6-fast"). This is *exactly why* density is blocker #1 and why we picked 4B over 8B (halves the die count). The 1.63 itself is **a second-hand ISSCC'26 reading (Huawei-ByteDance HYDAR 36 Mb), with an admitted SRAM-CIM bias — NOT our silicon**; ground truth = the M2 test-tile.
- **Hybrid bonding is the correct v2 move, not a v1 dependency.** Stacking a dense memory die under the compute die (Cu-Cu, a foundry service — AMD/Fujitsu/d-Matrix precedent) solves density + speed + vertical TB/s bandwidth *simultaneously* and is the real escape from the iron tradeoff. But domestically only 紫光 does 3D (DRAM); ReRAM 3D access for a small fabless is **vague, custom 2-die, and likely expensive** (blocker #3). We do **not** make v1 hostage to it. Stanford N3XT (HDC-on-3D-ReRAM) validates the *direction* for v2.

**Alternatives rejected.**
- **Monolithic 6-layer 3D-CIM (the old Mini headline).** Rejected: the process does not exist (academia is ~10,000× short of GB-scale). Don't invent a 3D stack.
- **(b) hybrid-bonded 3D as the v1 capacity path.** Rejected *for v1 only*: access/cost unproven for a small team (blocker #3); a custom 2-die bonded part is the wrong thing to de-risk *first*. Promoted to v2 once the single-die tile proves the macro and bonding access is priced.
- **Storage-mode + streaming (high density, 1–2 dies).** Rejected as the primary path: density 14.8–90 but **slow (~40–200 tok/s, bandwidth-bound)** — gives up the speed that is our whole point. We are **in-place CIM**, not streaming. (Kept only as a fallback if density proves catastrophic.)

### 1.4 Target envelope (honest ranges)

| Axis | v1 (4B ternary, ~1 GB, 2.5D N-die) | Basis / confidence |
|---|---|---|
| **Capacity** | ~1 GB resident (4B); **~2–3 dies @ 6 Mb/mm² → ~6–15 dies @ 1.6** (single-layer planar, 2.5D) | reram-kb cap formula; HONEST — rides HARD on the 60× density blocker. 1 GB @ 1.6 ≈ ~5,000 mm² = many reticle-dies (⚠️ corrected 2026-06-08; prior "2–4 even at pessimistic" was optimistic-only) |
| **Speed** | **~1–4k tok/s** (1B-class digital, 3-method cross-validated); 4B ~¼ of that → **~250–1,000 tok/s/die**, multi-die pipelined recovers toward 1k+ | digital-speed VERDICT; **🟢 FPGA-ANCHORED 2026-06-05**: real Vivado synth on EBAZ → max **P=512**, **~25 LUT/lane**, **0 DSP(无乘法器实测确认)**, Fmax 194–266MHz(**84% 是布线延迟→ASIC 没这惩罚,600MHz–1GHz 假设站得住**);把 EBAZ 地板按面积×时钟差放大 50–320× → 1B ~600–6,400 → **产品 1–4k 经得起真硬件缩放**。**util(每周期能否喂满 P 条 lane)仍欠 —— 需接板**(blocker #2 的剩余半条) |
| **Power** | **25–35 W** package (7–10 W/cm², ΔT 8–11 K with heatsink — SAFE for ternary, drift 3–4× below the ternary knee) | thermal model claim F (POC-MODELED) |
| **Energy moat** | ~3–7× vs GPU realistic (whole-chip); 10–1000× claimed only for HDC ops | ASSUMED; honest 100× headline |
| **Noise margin** | binary-cell + digital readout = primary; ternary +~3–5× in tail/SAF | D2 fair re-audit |

> Speed is **not** the constraint (we're already 20–400× past interactive even at the conservative end; even a 9B single-die ~85–520 tok/s clears the interaction line). The binding axes are **capacity (density-blocked)** and **market**.

### 1.5 Memory & periphery — DECISION: KV + glue on a side-by-side SRAM/logic die; programmable ternary-transformer-FAMILY engine (added 2026-06-08)

**Decision.** The dynamic state (KV cache + activations) and the non-matmul "glue" do **NOT** live on the ReRAM weight array — they live on a **dedicated SRAM/logic companion die, side-by-side in the 2.5D package.**
- **KV cache = on-chip SRAM at int4-KIVI** (per-channel-K grouped + per-token-V + recent-128 fp window). **MEASURED lossless**: GSM8K 75.0→76.0, C-Eval 66.1→66.1 (the earlier −12.5pp "reasoning tax" was a per-token-K apparatus artifact). ~4× smaller than fp16. **No ReRAM** (per-token writes would burn endurance), **no ADC**. Working-window sized per scenario (voice ~4–16 MB, chat/RAG ~16–64 MB-equiv; ≤~16 MB int4 fits on-die). KVarN/CommVQ not needed for v1; XQuant = optional sub-int4 shrink; int2 breaks (4-bit floor).
- **Periphery = a programmable vector/SIMD + special-function unit** (LUT softmax/RMSNorm/SiLU, RoPE, attention orchestration) sized for the **ternary-transformer FAMILY, not one checkpoint** — its natural home is the **20–45% die area reclaimed by going no-ADC**. ⇒ the chip is a **reflashable engine** (firmware-class weight reload: a library of train-time-ternary models, one live at a time; per-request hot-swap = no), **not one-chip-per-model**. **Downward-compatible for free** (4B/1B run faster, unused arrays power-gate ~0). "Suits all 8B" = NO — two filters: must be train-time-ternary (excludes all fp16) + architecture must fit the periphery.

**Rationale.** Decode moves weights (killed by CIM); the only remaining per-token data movement is the **KV read** → keeping KV in in-package SRAM (≫ off-package LPDDR bandwidth) preserves the all-on-chip speed moat. The weight↔KV split is by substrate-fit (density/non-volatility for weights vs write-endurance/low-latency for KV), **not by area** (28nm SRAM ~3 Mb/mm² is denser per bit than our CIM-ReRAM ~1.6).

**v2 (the model we train):** **MLA** (−93% KV, *shifts cost from KV-bandwidth → matmul = our CIM strength*) + **DSA** (FP8 no-multiply top-k indexer = matches no-ADC digital). Train-time-ternary + MLA **de-risked 2026-06-08** (probe: ternary penalty identical on MLA & MHA, no collapse; scale-up owed).

**Open (load-bearing):** in-package interconnect bandwidth vs target tok/s; SFU area budget after weight dies; ternary+MLA at real scale. Detail: `research-notes/2026-06-08-KV-CACHE-SYNTHESIS-AND-NEXT-STEPS.md` · `…-chip-model-generality.md`.

---

## 2. v1 SCOPE — the smallest thing to tape out FIRST (most important section)

### DECISION: tape out a **single-die MPW test-tile of ONE ternary SPIKA macro at modest size** — NOT the multi-die product.

The core thesis to prove cheaply is: **"a digital-readout (no-ADC) ternary SPIKA binary-cell CIM macro works on a real 28 nm ReRAM process, at the density and noise behavior we modeled."** Everything else (multi-die packaging, full 4B model, 3D bonding) is *capacity scaling* layered on top of a macro that must first exist in silicon. Prove the macro; don't prove the product.

**Test-tile spec (v1 first silicon):**
- **One SPIKA macro**: 2-state cells, ± adjacent columns, 5-bit up/down counter, threshold-comparator digital readout, **no ADC**. Start ~64×128 (SPIKA's demonstrated size) → scale to whatever fills ~1–5 mm² MPW reticle budget at the chosen node.
- **What it measures (the de-risking payload):** real single-layer **density** (Mb/mm² at node — directly attacks the 60× blocker), **bit-exactness** of the counter/comparator readout, **stuck-at-fault rate** + tail-noise behavior (does the modeled ~3–5× ternary tail edge show?), **power/MAC**, and the area ledger (is the 13%-smaller-than-ADC, 7×-cells claim real on silicon?).
- **What it does NOT include:** the full 4B model, multi-die packaging, hybrid bonding, attention/softmax serial path. Those are scaling, not thesis.

### De-risking milestone ladder

| Milestone | What it is | What it RESOLVES | Vehicle / cost |
|---|---|---|---|
| **M0 — FPGA twin** (P🟢 + 时钟🟢 实测 2026-06-05;util🟡 待接板) | 三值 MAC 阵列真综合上 EBAZ:max P=512、~25 LUT/lane、**0 DSP(无乘法器确认)**、Fmax 194–266MHz(布线限,ASIC 更快) | **P × clock 已测**(blocker #2 半条解);kills the multiplier ✅;util 仍需接板+喂数通路 | aux Vivado VM;**¥0**;`02-fpga-rtl/ternary-mac-array/`(RTL+综合报告全在) |
| **M1 — digital logic shuttle** | Ternary MAC + counter datapath as pure digital, no ReRAM | logic correctness, cell-library timing, the ASIC P×util anchor | **Open-PDK free shuttle** (Hangzhou TinyTapeout-class) — **¥0** |
| **M2 — ternary SPIKA test-tile** | Single-die ReRAM macro, the thesis tile above | **single-layer density** (the 60× blocker), digital-readout bit-exactness, SAF/tail noise on real cells, area ledger | **MPW 28 nm via broker → SMIC/Huahong, ~¥50万**, ~3-mo return |
| **M3 — single-die 4B-fraction** | One full die holding a usable fraction of the 4B model, in-place CIM | per-die capacity + speed at product scale; the iron-tradeoff operating point | MPW, costed after M2 density is known |
| **M4 — multi-die 2.5D / bonded** | N dies side-by-side (2.5D) → then hybrid-bonded (3D, v2) | full-model capacity; bonding access/cost (blocker #3) | package NRE; 3D only after bonding is priced |

**Why this ladder.** Each rung buys exactly one missing number before spending the next 10×. M0/M1 are **¥0** and de-risk the speed + logic *before any ReRAM money*. M2 (~¥50万) is the first real spend and it resolves the single most load-bearing unknown in the whole graph (density → die count → fits → useful → buyer). We refuse to order multi-die or bonding (M4, the expensive custom path) until M2 has turned the 60× density range into a point — that's the "don't run on a number two methods disagree on by 14×" discipline made executable.

---

## 2.5 流片去险硬规矩(HARD RULE — 逐级绿灯,才准花下一笔钱)

> 入库 2026-06-05(Michael)。回应"¥50万 流片回来一块死片"的真实恐惧。**钱按风险倒序花:最贵的 M2(¥50万)留到最后,前面的免费台阶必须先全绿。绝不在"两法不一致 / 未验证"的数上往下砸钱。**

**成功判据(先定义清楚什么叫"没白花"):**
- 测试片的活是**测出真数**,不是"demo 完美"。
- ✅ **成功 = 拿回真实的密度 / 噪声 / 保持 / 读出对错数据**(哪怕数字难看 = 学到真相)。
- ❌ **唯一的真失败 = 啥都不工作、零数据回来。** 下面的规矩就是把这个概率压到 <~10%。

**M2(¥50万)放行前,必须全绿(B-失败防护五条):**
1. ☐ 数字逻辑已在 FPGA(M0)上功能验证通过 —— 逻辑 bug 不会整片带走。
2. ☐ 用**已量产的 ReRAM cell**,**不自己发明器件**。
3. ☐ 片上含**兜底表征测试块**(简单 cell 阵 + retention/SAF/噪声)—— 哪怕 HDC 主阵列挂了,也能出密度/保持数 → 部分失败 ≠ 零数据。
4. ☐ DRC/LVS 干净 + 流片前仿真覆盖到位(模拟优先)。
5. ☐ M1(免费 shuttle)已验证数字部分在真硅上工作 + 时序收敛。

**逐级绿灯门(gate — 上一级不全绿,不准花下一笔):**
| 门 | 放行条件 |
|---|---|
| M0 → M1 | FPGA 上 bind/bundle/cleanup/MAC 功能正确 + P×util 测到 |
| M1 → ReRAM-fab 对话 | 免费 shuttle 数字块在真硅上工作 + 时序收敛 |
| ReRAM-fab 对话 → **M2(¥50万)** | 拿到真单层密度(纸面)+ cell PDK 确认 + 上面"五条"全绿 |
| M2 → M3/M4(最贵定制路) | **M2 回片把 60× 密度变成一个点 + 读出位级正确 + 兜底数据齐** —— 没拿到 M2 真数据,**不准订多 die / bonding** |

**一句话规矩:¥50万 是阶梯的最后一级,只在"只剩'真 ReRAM 在我们尺度下对不对'这一个未知"时才花;前面每一级免费台阶不全绿,不准花下一笔。** 模拟优先 · 便宜验证在前 · 合抱之木生于毫末。

**→ 极度省钱上硅阶梯(2026-06-09,详 `CHEAP-SILICON-PATH.md`):** 核心招=**拆数字半 / ReRAM 器件半,分开在最便宜载体验**。新增便宜级:**M1a 数字真硅**(Tiny Tapeout sky130 **$150** / 国内高校 shuttle 可能 ¥0,证 SPIKA 数字逻辑+计数器+无ADC读出上真硅)· **M1b 器件真数**(分立 ReRAM MB85AS 实测 **~$10–50**)→ 两半上真硅 **<$300** · **M1.5 集成宏@130nm**(IHP SG13G2 €2,240/mm² 学术 / SMIC 130nm ~¥30–100K → **~¥22–50K** 把整个差分cell+计数器宏在真 ReRAM 上证,= 28nm 的 **1/10**)。M2(¥50万 28nm)留最后,且可**流片补贴 / ReRAM-fab 合作 / 拼 reticle / 裸片不封装**再砍。

---

## 3. Tape-out path

**DECISION: MPW shuttle via broker, SMIC/Huahong 28 nm, for the M2 test-tile; free open-PDK shuttle for M1.**

| Item | Number | Source / confidence |
|---|---|---|
| **MPW 28 nm, 5–10 mm², via broker → TSMC** | **~¥50万 RMB** | industry MPW broker quote. SMIC/Huahong **cheaper**. |
| **Sim-vs-silicon variance** | **±20%** (area/yield) | industry |
| **Return time** | **~3 months** per shuttle | industry |
| **Iteration loop (this class of hard chip)** | **1–2 years** to working part | industry |
| **IP licensing (if process IP needed)** | 8万–20+万/use or buy-out | industry |
| **ReRAM process partner** | a domestic 28 nm ReRAM player (ByteDance-backed) — a candidate process partner | industry |
| **M1 digital-logic shuttle** | **~¥0** (open-PDK, Hangzhou/Zhejiang, TinyTapeout-class; good projects tape out free) | industry |
| **Cheapest possible de-risk** | buy real Fujitsu/RAMXEED MB85AS ReRAM (a few USD) to characterize real device noise | ledger #9 |

**Realistic v1 (M2 test-tile) budget + timeline:** ~¥50万 + ReRAM-fab process-IP engagement, ~3-month silicon return, plan for 1–2 shuttle iterations → **realistic working test-tile in ~12–24 months** *if* funded and *if* a domestic ReRAM fab will do a custom MPW for a small team (open — part of blocker #3). Full Stage-4 product NRE (¥1,200–2,500万) is **not** v1 and **not** funded — explicitly out of scope here.

**Sequencing:** M0 (now, ¥0) → M1 (¥0 open-PDK, validates logic + P×util ASIC anchor) → a domestic ReRAM-fab density conversation (¥0, info-gather — resolves blocker #1 on paper before spending) → **M2 MPW ¥50万** only once density says how many dies the product needs.

---

## 4. Open risks + blockers

### The 3 top blockers (each = a decision blocked on a number we don't have)

1. **🔴 Domestic-ReRAM single-layer real density — the 60× open question.** CIM-integrated ~1.6 (industry reading 1.63) / 1T2R storage ~14.8 (lit) / cross-point ~90 (Toshiba's *abandoned* 2013 research die — **not bankable**) Mb/mm². This 60× spread **decides whether v1 is ~2 dies or ~15 dies** → decides cap_mini → fits → useful → buyer → survival. **Blocks:** final die-count, package design, the 4B-vs-8B stretch call. **Resolved by:** a fab density conversation (¥0) on paper, then **M2 test-tile** in silicon (the ground truth). *This is the single most load-bearing unverified number in the entire graph.*

2. **🟠 FPGA P × utilization — the absolute-speed anchor.** Digital speed (1–4k tok/s) is 3-method cross-validated but the **absolute value still rides on on-chip parallelism (lane count P × real utilization)** — the one variable all three methods independently flagged. Software can't pin it. **Blocks:** the committed speed number (and therefore the speed-tier marketing claim). **Resolved by:** **M0 (TALOS-V3 FPGA)** — bitstream queued, measures realizable lanes + batch=1 utilization. Cheapest, already in motion. **✅ RESOLVED-AT-SIM 2026-06-09 (`02-fpga-rtl/ternary-mac-array/THROUGHPUT-UTIL-2026-06-09.md`):** a cycle-accurate iverilog throughput TB measures **datapath util ≈ 99.5% (II=1, 0 stalls, 509.5/512 MACs/cycle)** — the feed-forward array fills its lanes, so "real utilization" of the DATAPATH ≈ 1.0, NOT the old assumed 0.25–0.4. **The 1–4k tok/s GEMM-bound ceiling HOLDS** at ASIC P×Fmax (1 GHz × P=8192 ≈ 4076 tok/s @1B; 600 MHz ≈ 2445). Binding knob = **Fmax × P (already synthesized), not II**. NO board / NO Vivado VM needed (util is a cycle-count property; Fmax came from synth). ⚠️ The REALIZED fraction of that ceiling now hinges on **system feeding bandwidth** (~5,120 stim bits/cycle @P=512 from BRAM/SRAM) + SFU/attention bubbles + weight reloads — un-modeled here = the genuine remaining throughput risk (= the on-chip-read-bandwidth gap, ledger #9; physical EBAZ-with-memory is where it's worth running). **So blocker #2's DATAPATH half closes; the FEEDING half moves to that separate gap.**

3. **🟠 Hybrid-bonding access + cost for a small team.** The v2 escape (dense-memory-die-under-compute-die) is a real foundry service (AMD/Fujitsu/d-Matrix) but domestically only 紫光 does 3D (DRAM); ReRAM 3D for a small fabless is unpriced, custom 2-die, and possibly closed (Samsung/Hynix/Micron won't partner). **Blocks:** the v2 capacity path (and whether the iron-tradeoff escape is even available to us). **Resolved by:** **M4 costing**, gated behind M2 — we don't need the answer until single-die works. Deliberately deferred so it can't block v1. **⚠️ DOWNGRADED 2026-06-09 → NON-ISSUE (economics + competitive sweep; `CHIP-STRUCTURE-1B-SKU.md` §8–9):** hybrid-bonding is the **WRONG tool**, not merely deferred. In-place CIM moves only **activations** between dies (~0.1–0.3 GB/s), not weights → that's ~10⁶× under the cheapest **organic** 2.5D interposer (>3.5 Tbps/mm). We never needed hybrid-bonding's vertical TB/s; capacity scales by adding dies on a cheap organic substrate. Hybrid-bonding capacity is also booked out by NVIDIA/AMD at premium NRE (small-team-hostile) and buys nothing for an activations-only link. **Action: drop hybrid-bonding from the v2 plan; use organic 2.5D for v1 AND capacity scaling.** Blocker #3 is retired.

### Other honest open risks (NOT v1-blocking, but tracked)

- **🟠 Market validation (the now-binding constraint).** The binding constraint is market, not the physics: demand is still unproven and the buyer / price-segment is not yet defined. The program's own ranked gap says *this* — not device physics — is the real wall. **Mitigation = run in parallel with the test-tile:** pick 1–2 privacy verticals (legal SaulLM / medical Meditron / fusion-control agent), validate willingness-to-pay using the FPGA/HDC demo that can bill *now*. This is the highest-leverage non-engineering action and it de-risks the only constraint that can kill the program even if the silicon is perfect.
- **🟡 KV-cache / context memory path — v1 RESOLVED (int4-KIVI); v2 (MLA+DSA) gated by a ternary+MLA probe (raised 2026-06-08, Michael).** This ADR specifies only the **weight** path (static ternary, resident on ReRAM-CIM). The **KV cache is dynamic — written every token — so it CANNOT live on ReRAM** (endurance 10⁸–10¹¹; consistent with `project_control_chip_landscape_update_cadence`: high-frequency writes belong on SRAM, not ReRAM). It must sit on **volatile high-endurance memory (on-chip SRAM or off-chip LPDDR)**, and per our own `SPEED-SCENARIO-LADDER` it is the **prefill/context bottleneck** ("decode moves weights; prefill moves the KV-cache/context"). Scale for the test model (32 layers, GQA 2 KV heads, head_dim 128): **~32 KB/token fp16 (16 KB int8)** → 8K ctx ≈ 256 MB, 32K ctx ≈ **~1 GB ≈ the entire 4B weight budget**. **Blocks (eventually):** the speed claim at non-trivial context + the on-chip-vs-off-chip memory design. **Being researched 2026-06-08** on 4 axes — (1) KV/attention quantization & compression, (2) HDC-hippocampus as KV substrate, (3) context-length-per-scenario (we pursue speed → minimum viable context), (4) SRAM-vs-LPDDR placement & bandwidth. **Recommended placement (Michael 2026-06-08): a dedicated KV-SRAM/logic die side-by-side in the 2.5D package — does NOT consume ReRAM weight-die area.** KV working window (int4) ≈ 8–43 mm² ≈ <1% of silicon; the weight↔KV split is about write-endurance + dynamics, NOT area (28nm SRAM ~3 Mb/mm² is actually denser per bit than our CIM-ReRAM ~1.6). Core lens: *does it keep us fast?* See feasibility-ledger (器件&容量 · item 9b) + `ternary-foundation/` follow-ups.
  **UPDATE 2026-06-08 (v1 resolved):** measured — **int4-KIVI KV** (per-channel-K grouped + per-token-V + recent-128 fp window) is **lossless** on reasoning (GSM8K fp16 75.0 → int4-KIVI 76.0, n=100) AND knowledge (C-Eval 66.1 → 66.1); the earlier −12.5pp drop was a per-token-K apparatus artifact. **v1 KV decision = int4-KIVI on a dedicated side-by-side SRAM/logic die (no ReRAM, no ADC), ~4× smaller than fp16.** KVarN/CommVQ not needed for v1; XQuant = optional further shrink (sub-int4); int2 breaks (4-bit floor). **v2 (bigger prize): train our own ternary model with MLA (−93% KV, *shifts cost to matmul = our CIM strength*) + DSA (FP8 no-multiply top-k indexer = matches no-ADC digital) — gated by the one unpublished unknown: a train-time-ternary + MLA feasibility probe.** **PROBE RESULT 2026-06-08 = GREEN (signal): ternary penalty identical on MLA (+0.325) and MHA (+0.323) → ternary does NOT break MLA** (`ternary_mla_probe.py`, char-level 4-arm QAT; caveat: 3.4M toy model + simplified MLA = de-risks the "collapse" fear, NOT proof at 4B; scale-up next). Research: `research-notes/2026-06-08-deepseek-kv-lineage.md` · `…-kv-sota-frontier.md` · `…-KV-CACHE-SYNTHESIS-AND-NEXT-STEPS.md`. **→ CONVERGING 2026-06-08 (parallel KV session, Michael): int4 KIVI-proper @ 2K context, fully on-chip SRAM = the speed-optimal v1 point.** int4 (not KIVI's aggressive 2-bit) = quality-safe; per-token KV (32L/2KV-head/128) = 8 KB int4 → 2K ctx ≈ 16 MB payload (+ KIVI residual window + group scales ≈ **~18–20 MB**) → **~35–45 mm² of 28nm SRAM** (~3–4 Mb/mm²) on the control/KV die ≈ **~2–3% of the ~1600 mm² CIM silicon** → weights (ReRAM-CIM) + KV (int4 SRAM) BOTH resident → prefill+decode never leave the package → no LPDDR → stays 1–4k tok/s. Write rate 8 KB × 1–4k tok/s = 8–32 MB/s (trivial for SRAM; this is *why* KV ≠ ReRAM — per-token writes). **Honest bound: 2K fits voice/companion/short-RAG; agent/long-doc (128K–1M) = LPDDR (slower) or v2/HDC-hippocampus.** This closes the KV prefill/context bottleneck for the SHORT-context v1 SKU. Owner of record = the parallel KV session + `project_kv_cache_chip_strategy_2026_06_08` memory.
- **🟢 Chip = a PROGRAMMABLE ternary engine, NOT one-chip-per-model (researched 2026-06-08, Michael's Q; `research-notes/2026-06-08-chip-model-generality.md`).** A CIM array is a *generic* matmul fabric; every real CIM/ReRAM accelerator is reprogrammable (NeuRRAM ran 4 model classes on ONE RRAM chip; Mythic/Axelera/d-Matrix all programmable multi-model). "Fixed single-network" = only academic test macros (= our M2 tile, correctly — but NOT the product). **Two filters on which models run:** (1) **must be train-time-ternary** (post-hoc ternary = garbage → excludes all fp16 models; restricted to the BitNet/BitCPM/Falcon-Edge ternary set ≈ a dozen, multi-lab, growing); (2) **architecture must fit the PERIPHERY** — the array does generic matmul, but attention/RoPE/RMSNorm/SwiGLU/MoE/softmax vary by model and live in a programmable vector/SIMD + special-function unit; sizing that SFU for a ternary-transformer FAMILY (not one checkpoint) is the tax — **partly free for us since the reclaimed no-ADC area (20–45%) is its natural home.** **Weight reload = firmware-class** (write-verify >10× read; re-flash ~1 GB = seconds-to-minutes; endurance 10⁶–10¹⁰ → occasional model-swap ~free; per-request hot-swap = NO). **Downward-compatible for free** (4B/1B on an 8B chip run *faster*, unused arrays power-gate ~0; just wastes silicon economically). **DECISION: build v1 periphery for the ternary-transformer FAMILY (reflashable, one model live); v2 = train our OWN chip-consistent ternary family (ternary + MLA + no-multiply indexer) = the model nobody else runs as fast because nobody has the matching silicon.**
- **🟢 8B-under-SPIKA end-to-end ppl — MEASURED 2026-06-07** (`ternary-foundation/experiments/chip_path_eval.py`): digital path (int8 act + bit-exact no-ADC accumulate) clean=8.733; +int8 act +0.5%; +1% stuck-at = **9.07 (+3.8% vs ceiling, still < fp sibling 9.62)**; 5% SAF = +25% (graceful). Confirms 8B holds under the SPIKA readout; only承重 knob = device SAF rate (ECC/redundant-column mitigable).
- **🟡→🟢 Device model is NeuroSim-grade, not NeuroSim — retention/temp half CLOSED 2026-06-09.** ~~Missing IR-drop, retention drift over time, conductance relaxation, write endurance, temp×conductance coupling.~~ **IR-drop MEASURED** (CIM-Explorer parasitics 2026-06-09, sparse-ternary @256-accum = 0.3–1.0%). **Retention drift over lifetime + temp×conductance coupling CLOSED** (`ternary-foundation/device-retention-drift-2026-06-09.{md,py}`, tests=[L1], kit-ledgered): first-order literature model (Ea **swept 0.38–1.55 eV**, drift ν **swept 1–10 %/decade** per the GUARD) on the burned-once-resident binary-differential cell. **VERDICT SAFE-over-product-life** — over 1–10 yr @55–125 °C (incl. F1 +11 K hotspot) the differential on/off margin stays **≥9× (worst realistic) / ~56–62× (central)** vs the **75×** start; the ≥7-bit digital-counter readout stays **bit-exact, no level flips**. Only MARGINAL (never flips) in the fully-compounded pessimistic corner (Ea≤0.5 **AND** ν≥10 % **AND** ρ_cm≈0 **AND** ≥125 °C+hotspot). **KEY protective mechanism = differential common-mode cancellation** (same-stack/same-Tj retention drift is common-mode → cancels in G_A−G_B; only the (1−ρ_cm) σ-spread residual moves the bit — **ρ_cm is the load-bearing assumption, silicon must measure it**). Verdict does **not** hinge on Ea (sweeps ~flat); hinges on ρ_cm + ν. Re-flash availability resets the clock (free extra net). **Still owed to VERIFIED:** real M2 28nm silicon (true Ea/σ of the production ReRAM stack, measured ρ_cm, spatial clustering) + **write endurance** (10⁶–10¹² lit; burned-once means ~0 re-write stress). Real silicon could still move the noise/density magnitude either way.
- **🟡 Thermal model is analytical R-stack, not FEM** — misses local hotspots (would need ~+50 K local rise to threaten ternary; modeled ~11 K). Owed: FEM coupled run aimed at hotspots.
- **🟢 Open-source / open-tape-out culture is counter to a closed chip industry** — could be differentiation *or* friction; unresolved strategy question, not a v1 gate.

---

## Decision summary table

| # | Decision | Confidence | Top alternative rejected |
|---|---|---|---|
| Model | **4B train-time-ternary text, ~1 GB resident** (8B = stretch) | High (fits + measured near-lossless) | 9B-Q4 (never fits) |
| Compute | **digital SPIKA binary-cell CIM, no ADC, bit-exact** | High (digital>analog settled) | analog multilevel + ADC |
| Capacity | **2.5D N single-layer planar dies (v1); hybrid-bond 3D (v2)** | Medium (rides on density blocker) | monolithic 6-layer 3D-CIM (doesn't exist) |
| **Scope** | **single-die MPW test-tile of ONE ternary SPIKA macro** | High (right thing to de-risk first) | tape out the multi-die product |
| Tape-out | **MPW broker → SMIC/Huahong 28 nm, ~¥50万**; open-PDK ¥0 for logic | Medium (rides on a domestic-ReRAM-fab willingness) | full Stage-4 product NRE (¥1,200–2,500万) |

---

*Built on: `CHIP-FEASIBILITY-LEDGER-2026-06-03.md` · `reram-kb/reram_world.json` · `digital-speed-estimate/VERDICT-cross-validation.md` · `ternary-foundation/results/D2-FAIR-READOUT-VERDICT-2026-06-03.md` · `CHIP-FAMILY-MASTER-DIGEST-2026-06-01.md` . Provisional pending the 3 blockers. 合抱之木生于毫末 — prove the macro, then grow the product.*
