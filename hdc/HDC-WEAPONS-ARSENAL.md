# HDC 武器库 v2 — 计算机栈架构（审计修正版）

> 2026-05-28 重构 → 审计 → 修正  
> 审计发现: 微码层术语对齐 + 缺少评估层 + 缺少文件映射 + 缺少编排层

---

## 栈全景（修正后）

```
╔══════════════════════════════════════════════════════════╗
║                    应用层 APPLICATIONS                   ║
║  一堂 AI · Second Brain · Narrative HDC · Motion · FPGA ║
╠══════════════════════════════════════════════════════════╣
║                系统科学层 SYSTEM SCIENCE (OS)            ║
║  SystemBundle · MetaSynthesis · SpiralLearner            ║
║  RippleTracer · OpenSystem · MIRROR · E_YITANG           ║
╠══════════════════════════════════════════════════════════╣
║             编排层 ORCHESTRATION                         ║
║  Golden Standard #1 · Pre-mortem Gate · Sweep Runner     ║
║  Pipeline: encode → store → query → diagnose             ║
╠══════════════════════════════════════════════════════════╣
║              标准库层 STANDARD LIBRARY                   ║
║  HVSet · HVMap · HVSequence · HVGraph · PagedHVStore     ║
║  Query Templates (10)  ·  search · sequence · compare    ║
║  VSA Diagnostics (5 metrics)                             ║
╠══════════════════════════════════════════════════════════╣
║                 微码层 MICROCODE (cos 盲区)              ║
║  negation · temporality · scale · certainty · causality  ║
║  keyword突破 · 5修饰器                                  ║
╠══════════════════════════════════════════════════════════╣
║                 ISA 层 — 6 条指令                        ║
║  cos  bind  bundle  permute  unbind  weighted_bundle     ║
╠══════════════════════════════════════════════════════════╣
║                 编码层 ENCODING (I/O)                     ║
║  simhash · sparse_ternary · fourier · multi_bit           ║
║  walsh_hadamard · fractional_bind · qFHRR · RFF · MAP    ║
║  bge-zh · Qwen hidden state · (any)                      ║
╠══════════════════════════════════════════════════════════╣
║              物理层 HARDWARE (可替换)                     ║
║  numpy · Rust NEON · MLX GPU · K510 FPGA · WASM          ║
╚══════════════════════════════════════════════════════════╝
```

---

## 审计结果

### ✅ 通过项
- ISA 6 指令: 全部验证。cos=dot/D, bind=multiply=XOR, unbind inverts bind, bundle=sign(sum), weighted_bundle 权重正确
- 编码层: 13 种编码 + 2 种 embedding 模型，全部在栈中
- 标准库: HVSet/HVMap/HVSequence/HVGraph/PagedHVStore + Query Templates + Diagnostics
- 物理层: 5 个后端，全部可替换

### ⚠️ 修正项
1. **微码层术语不统一** — "规模/确定性/因果" 对应 scale/certainty/causality
2. **缺少编排层** — Golden Standard #1、Pre-mortem Gate、实验 sweep 没有归属
3. **缺少文件映射** — 抽象名字 (HVSet) 对应哪个代码文件 (structures.py)
4. **ISA 层多列了 soft_bind/normalize/threshold** — 这些是编码层的工具，不是 ISA

---

## 文件映射

| 栈层级 | 概念 | 代码文件 |
|--------|------|---------|
| ISA 层 | bind/bundle/permute/cos/unbind/weighted_bundle | `hdc_ops/__init__.py` |
| 编码层 | 6 种补充编码 ± fractional_bind | `hdc_ops/encoding_extra.py` |
| 编码层 | 7 种核心编码 | `hdc_ops/encoding.py` |
| 编码层 | bge-zh embedding | `_case_study_v3.py` (引用) |
| 编码层 | Qwen hidden state | `ffn_hdc_sweep.py` (引用) |
| 标准库 | HVSet/HVMap/HVSequence/HVGraph | `hdc_ops/structures.py` |
| 标准库 | Query Templates | `hdc_ops/queries.py` |
| 标准库 | VSA Diagnostics | `hdc_ops/diagnostics.py` |
| 标准库 | Paged HV Store | `hdc_ops/paged_store.py` |
| 标准库 | Time HDC | `hdc_ops/time_hdc.py` |
| 物理层 | MLX GPU | `hdc_ops/hdc_mlx.py` |
| 编排层 | Golden Standard | `07-methodology/HDC-EXPERIMENT-LESSONS.md` |
| 系统科学 | 5 工具 | `11-systems-science/src/` |
| 系统科学 | MIRROR | `11-systems-science/MIRROR.md` |
| 系统科学 | E_YITANG | `11-systems-science/CIVILIZATION-SIM.md` |

---

## ISA 层 — 完备性证明

**6 条指令是完备的。** 任何 HDC 程序最终分解为这 6 条。

| 指令 | 数学 | 物理 | 复杂度 |
|------|------|------|--------|
| **cos** | dot(h1, h2) / D | XOR + popcount | O(D) |
| **bind** | h1 · h2 (element-wise) | XOR gate | O(D) |
| **bundle** | sign(Σ hi) | majority voter | O(N·D) |
| **permute** | roll(h, k) | shifter | O(D) |
| **unbind** | h_bound · h_role | XOR gate | O(D) |
| **weighted_bundle** | sign(Σ wi·hi) | weighted majority | O(N·D) |

**不在 ISA 中的是高阶复合指令** — 由 ISA 组合而成:
- `search(query, db)` = cos + argsort
- `sequence(h_list)` = permute + bundle
- `compare_all(h, db)` = cos × N
- `set_membership(h, hvset)` = cos > τ

---

## 微码层 — 六个修饰器

**cos 只回答 WHAT。六个修饰器补充其他维度。**

| 修饰器 | 中文 | 解决的问题 | 实现 | 来源 |
|--------|------|----------|------|------|
| **negation** | 否定 | "客户需要" vs "客户不需要" | 否定词检测 → +0.05/-0.03 | 根因分析发现 |
| **temporality** | 时间 | "正在做" vs "已经做了" vs "还没做" | bind(概念, 时间态) → 三态匹配 | time_hdc |
| **scale** | 规模 | "1个客户" vs "500个客户" | 数量词检测 → 缩放紧迫性 | 根因分析发现 |
| **certainty** | 确定性 | "可能是" vs "一定是" | 确信度检测 → 调整匹配阈值 | 根因分析发现 |
| **causality** | 因果 | "A→B" vs "B→A" | bind(原因, 结果) → 方向编码 | 根因分析发现 |
| **keyword** | 关键词 | 语义对立打破 | 对立词检测 → +0.03 boost | 验证通过(3/3) |

---

## 编排层 — 实验怎么跑

| 组件 | 做什么 | 位置 |
|------|--------|------|
| **Golden Standard #1** | 任何 HDC 实验必跑 ≥4 编码 × ≥3 D × ≥2 sparsity × ≥3 seeds | `HDC-EXPERIMENT-LESSONS.md` |
| **Pre-mortem Gate** | 实验设计锁定前强制运行死亡清单 | `PRE-MORTEM-GATE.md` |
| **Sweep Runner** | ffn_hdc_sweep 框架 — 自动并行 + 结果汇总 | `ffn_hdc_sweep.py` |
| **Pipeline** | encode → store → query → diagnose → report | 本栈的纵向路径 |

---

## 栈的纵向路径

一个完整的 HDC 查询经过的路径:

```
用户问题
  ↓ 编码层: bge-zh → 512d float → SimHash → ±1 HV
  ↓ ISA 层: cos(h_problem, h_node_1) ... cos(h_problem, h_node_N)
  ↓ 微码层: negation_boost + temporality_align + scale_weight + certainty_adjust + causal_align
  ↓ 标准库: query_template → search → HVMap.unbind → diagnostics.vsa_likeness
  ↓ 编排层: Golden Standard gate check → pre-mortem passed?
  ↓ 系统科学: RippleTracer(root_cause) → SystemBundle(整体视角) → MIRROR(世界镜像对比)
  ↓ 应用层: 一堂教练界面 → "你的根因在需求验证不足"
```
