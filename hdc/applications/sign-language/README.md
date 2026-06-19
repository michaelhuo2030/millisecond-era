# HDC Sign Language Recognition — Case Study
# HDC手语识别实验报告

> **Language / 语言**: [English](#english) | [中文](#chinese)

---

<a name="english"></a>
## Sign Language Recognition with HDC + Supervised Contrastive Learning

**One enrollment example. 95% accuracy. On-device. Private.**

### What We Built

A sign language recognition pipeline that:
- Learns from **one example per sign** (K=1 enrollment)
- Runs entirely **on-device** — no server, no cloud, no data leaving the device
- Achieves **95%+ accuracy** on a 10-sign vocabulary
- Scales to **25 signs at 86.8%** with the same single-enrollment approach

The core architecture: **vocabulary-aware SupCon encoder → HDC sparse-ternary readout**

### Key Discovery: The Vocabulary Confusion Problem

The most common 25 signs in any sign language dataset are **not** the most recognizable 25 signs.

We found that in AUTSL (43 signers, 218 Turkish Sign Language signs), the popular top-25 vocabulary contains sign pairs with cosine similarity **0.999** in feature space — nearly identical prototypes. **77% of all 218 signs have at least one near-identical twin** (sim ≥ 0.99).

Standard ML treats vocabulary as fixed and fights the confusion. We asked: **what if you choose the vocabulary to minimize confusion?**

### The Method

**Step 1 — Vocabulary Selection (Greedy Max-Min-Distance)**

Select N signs that maximize pairwise distinguishability:

```python
def greedy_distinct(protos, eligible, n):
    selected = [random_start]
    while len(selected) < n:
        # Add the sign with maximum minimum distance to all selected
        best = argmax([min_dist_to_selected(c) for c in remaining])
        selected.append(best)
    return selected
```

**Step 2 — SupCon Encoder (Signer-Invariant Mapping)**

Train a small neural network (3-layer MLP, 64-dim output) with supervised contrastive loss:
- Pull: same sign, different signers → close in embedding space
- Push: different signs → far in embedding space

Key insight: **SupCon only converges when signs are genuinely distinct**. With a popular-25 vocabulary (worst pair sim = 0.999), SupCon training collapses — the loss cannot simultaneously separate near-identical signs. With dist-10 (worst pair sim = 0.943), SupCon learns excellent representations.

**Step 3 — HDC Sparse-Ternary Readout**

Encode SupCon embeddings into D=30,000-dimensional sparse ternary hypervectors, kernel ridge readout for K-shot classification.

### Results

#### Vocabulary Size vs. K=1 Accuracy (AUTSL, dist selection + SupCon)

| Signs | Chance | Raw Bone | + SupCon | SupCon Gain |
|-------|--------|----------|----------|-------------|
| 5     | 20.0%  | 89.6%    | **97.3%** | +7.7pp |
| 8     | 12.5%  | 83.2%    | **96.0%** | +12.7pp |
| 10    | 10.0%  | 81.1%    | **94.2%** | +13.1pp |
| 15    | 6.7%   | 80.0%    | **92.5%** | +12.5pp |
| 20    | 5.0%   | 78.3%    | **88.8%** | +10.5pp |
| 25    | 4.0%   | 75.8%    | **86.8%** | +11.0pp |
| 30    | 3.3%   | 73.2%    | **84.2%** | +11.0pp |
| 40    | 2.5%   | 71.7%    | **81.1%** | +9.4pp  |

#### K-Shot Enrollment Curve (dist-10 + SupCon)

| Enrollment Examples | Accuracy |
|--------------------|----------|
| K=1 (one shot)     | **95.0%** |
| K=2                | 95.3% |
| K=3                | 95.5% |
| K=ALL              | 95.5% |

**The encoder is saturated at K=1.** More enrollment examples provide negligible gain — one example per class already captures the class centroid precisely enough.

#### Abstention / Confidence Thresholding (K=1)

| Abstain Bottom | Accuracy | Coverage |
|----------------|----------|---------|
| 0% (none)      | 95.0%    | 100%    |
| 10%            | **98.5%** | 90%    |
| 20%            | **99.4%** | 80%    |
| 30%            | **99.5%** | 70%    |

At 20% abstention rate (system says "I'm not sure, show me again" for the 20% least-confident predictions), accuracy reaches **99.4%** while still serving 80% of recognition requests.

#### The Critical Compound Effect

| Vocabulary | SupCon | K=1 Accuracy |
|-----------|--------|-------------|
| Popular-25 (worst sim = 0.999) | No  | 76.2% |
| Popular-25 | **Yes** | 62.9% ← SupCon **hurts** |
| Dist-10 (worst sim = 0.943)   | No  | 78.6% |
| Dist-10 | **Yes** | **94.9%** ← +14.5pp CONFIRM |

SupCon with a confused vocabulary actively degrades performance. SupCon with a curated vocabulary achieves near-human accuracy. **Vocabulary selection is the prerequisite, not an optimization.**

### Dataset

- **AUTSL**: 43 signers, 226 Turkish Sign Language signs (Sincan et al., 2020)
- **ASL-Signs**: 21 signers, 250 American Sign Language signs (Google, 2023)
- Features: MediaPipe skeleton keypoints, dominant hand (21 joints × 3D × 32 frames)

### Interactive Demo

See [demo.html](https://michaelhuo2030.github.io/millisecond-era/hdc/applications/sign-language/demo.html) for a browser-based visualization of all results.

### About This Research

Independent research by [Michael Huo](https://github.com/michaelhuo2030), Shanghai.

Focus: Hyperdimensional Computing (HDC/VSA) for private, on-device perception — sign language recognition as a testbed for the core thesis: **deterministic, reversible, private memory algebra as an alternative to black-box neural networks**.

Related work in this repository: [HDC Laws Registry] · [Weapons Arsenal]

---

<a name="chinese"></a>
## 手语识别实验报告（HDC + 监督对比学习）

**一次录入，95% 准确率，端侧运行，完全私有。**

### 我们做了什么

一套手语识别流水线，特点：
- **只需录一次**每个手势（K=1 录入）
- **完全端侧运行** — 无需服务器、云端，数据不离开设备
- 10个手势词汇下达到 **95%+ 准确率**
- 用相同的单次录入方式，25个手势仍有 **86.8%** 准确率

核心架构：**词汇感知 SupCon 编码器 → HDC 稀疏三值读出**

### 关键发现：词汇混淆问题

最常用的25个手势，并不是最容易被识别的25个手势。

在 AUTSL 数据集（43人，218个土耳其手势）中，最常用的25个手势里，有些配对的余弦相似度高达 **0.999** ——在特征空间中几乎完全相同。**218个手势中77%至少有一个"近似双胞胎"**（相似度 ≥ 0.99）。

传统机器学习接受固定词汇、努力区分混淆对。我们问的问题是：**如果主动选择词汇来最小化混淆呢？**

### 方法

**步骤1 — 词汇选择（贪心最大-最小距离）**

选N个手势，最大化两两之间的可区分性：从一个随机起点出发，每次加入与已选手势集最远的那个手势。

**步骤2 — SupCon 编码器（跨人不变映射）**

训练一个小神经网络（3层MLP，64维输出），目标：
- 拉近：同一手势、不同人 → 在嵌入空间靠近
- 推远：不同手势 → 在嵌入空间推开

关键洞察：**SupCon 只有在手势本身有差异时才能收敛**。popular-25词汇（最差配对相似度0.999）让SupCon训练崩溃——损失函数无法同时分开"双胞胎"手势。dist-10（最差配对相似度0.943）让SupCon学到优秀的表征。

**步骤3 — HDC 稀疏三值读出**

将SupCon嵌入编码为D=30,000维稀疏三值超向量，核岭回归做K次录入分类。

### 实验结果

#### 词汇量 vs K=1 准确率（AUTSL，dist选词 + SupCon）

| 手势数 | 基线 | 骨骼特征 | +SupCon | SupCon增益 |
|-------|------|---------|---------|----------|
| 5     | 20.0% | 89.6%  | **97.3%** | +7.7pp |
| 8     | 12.5% | 83.2%  | **96.0%** | +12.7pp |
| 10    | 10.0% | 81.1%  | **94.2%** | +13.1pp |
| 15    | 6.7%  | 80.0%  | **92.5%** | +12.5pp |
| 20    | 5.0%  | 78.3%  | **88.8%** | +10.5pp |
| 25    | 4.0%  | 75.8%  | **86.8%** | +11.0pp |
| 30    | 3.3%  | 73.2%  | **84.2%** | +11.0pp |
| 40    | 2.5%  | 71.7%  | **81.1%** | +9.4pp  |

#### K次录入曲线（dist-10 + SupCon）

| 录入次数 | 准确率 |
|--------|-------|
| K=1（一次）| **95.0%** |
| K=2    | 95.3% |
| K=3    | 95.5% |
| K=全部  | 95.5% |

编码器在K=1时已饱和。更多录入几乎没有额外收益。

#### 置信拒识（K=1）

| 拒识比例 | 准确率 | 覆盖率 |
|--------|-------|-------|
| 0%（不拒识）| 95.0% | 100% |
| 10%   | **98.5%** | 90% |
| 20%   | **99.4%** | 80% |
| 30%   | **99.5%** | 70% |

拒识最不确定的20%预测，准确率达到 **99.4%**，同时覆盖80%的识别请求。

### 关于这项研究

独立研究，研究者：Michael Huo，上海。

研究方向：超维计算（HDC/VSA）在私有端侧感知中的应用——以手语识别为测试床，验证核心命题：**确定性、可逆、私有的记忆代数，作为黑盒神经网络的替代方案**。
