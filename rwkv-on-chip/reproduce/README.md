# 如何复现（方法即护城河 · doers not talkers）

四道闸的脚本都在这里，CSV 在 [`../results/`](https://github.com/michaelhuo2030/millisecond-era/tree/main/rwkv-on-chip/results)。**这些是小规模 PoC——目的是亮出趋势 + 让你能自己跑一遍，不是发表级 scaling law。** 全部 CPU 可跑（我们就是在一台 mac 上跑的）。

## 依赖
```bash
pip install torch numpy        # 四闸里有三闸只要这两个
pip install rwkv tokenizers    # 仅 rwkv_legit_test.py 需要（加载官方 checkpoint）
```

## 语料（闸 1/2/3）
QAT 实验用 `CORPUS_DIR` 指向的一堆 UTF-8 文本（我们用的是自己本地的研究 markdown，约 1MB）。换成**任意** UTF-8 文本都行——这是 PoC 语料，不是 benchmark，绝对 CE 会随语料变，但**趋势**（QAT 救活三值、gap 随规模塌缩、int8 状态免费）是稳的。
```bash
export CORPUS_DIR=/path/to/some/utf8/text   # 默认 ./corpus
```

## 脚本 → 闸 → 产物

| 脚本 | 验的闸 | 输出 CSV | 一句话 |
|---|---|---|---|
| `rwkv_qat_lm.py` | 闸 1 量化生存性 | `qat_lm_ce.csv` | fp32 vs 三值-QAT vs 三值-post-hoc 的 byte-LM CE（QAT 修回 94%）|
| `rwkv_qat_scale.py` | 闸 2 规模化 | `qat_scale_ce.csv` | 三值 gap 沿参数阶梯单调塌缩（×11→−85%）|
| `rwkv_state_prec.py` | 闸 3 状态精度 | `state_prec.csv` | int8 状态≈免费、零长度漂移；int4 不值 |
| `rwkv_legit_test.py` | 靠谱性 | （打印）| 状态恒定 62× / 透明 numpy vs 官方 logit 偏差 1.16e-5 |

```bash
python3 rwkv_qat_lm.py        # ~分钟级，CPU，2 seeds
python3 rwkv_qat_scale.py     # 参数阶梯，单 seed
python3 rwkv_state_prec.py    # 部署配置，状态量化扫长度
python3 rwkv_legit_test.py    # 需先下官方 checkpoint（见下）
```

### `rwkv_legit_test.py` 需要官方 checkpoint
它加载一个**公开的** RWKV-7 0.1B checkpoint（BlinkDL 官方，HuggingFace），做两件事：① 实测状态跨 ctx 恒定；② 拿一份透明 200 行 numpy 实现对照官方包逐位核对。把 `*0.1b*.pth` 放进脚本里 `SCRATCH` 指向的目录即可。checkpoint 自 RWKV 官方 HF org 下载（我们**不**重分发它）。

## 诚实边界（再说一遍，because it matters）
- 训练实验 ≤1.66M 参数、~1MB 语料、1200 步、多为单 seed → **PoC 趋势，不是发表级 scaling law**。
- 忠实 DPLR-class RWKV-7（含 r_k bonus），但**不是**官方完整 cell；A/B 受控，结论是相对趋势。
- 闸 4（WKV 数据通路的硅上 RTL）+ 真规模验证（>1.66M、多 seed）还没做——是公开的 TODO。
- 芯片为**综合 + 仿真 + 设计**阶段，未流片；适配账（[`../sizing.py`](https://github.com/michaelhuo2030/millisecond-era/blob/main/rwkv-on-chip/sizing.py)）是算术估算。

发现任何越界声明，开 issue，我们当场改。
