# HDC 实验执行 OPS 方法论

> 融合三角色系统 + 预 mortem + PoC + 实时监控 + 实时归档
> 2026-05-28 · 从 sweep 死机事件提炼

---

## 核心原则

**不是"这样做对不对"——是"这样做什么时候会死，死之前怎么发现"。**

---

## ⛓️ 永久铁律（默认行为，Michael 不需再强调 · 2026-05-30 锁入）

> 这四条是 standing default。任何 HDC 实验自动适用，无需被提醒。

### 1. 两台机器协作（Main mac ↔ Aux mac）
- **Main mac**(Claude, 24GB, **无 MLX**):审核 / 设计 / 写 spec / 小规模 PoC 验证通路 / 监控 / 归档。**不跑重型全量。**
- **Aux mac**(M4 Max, 128GB, **有 MLX GPU**):所有计算密集全量(高 D、全层、多 seed、7B)。由 Kimi 执行。
- **协作流**:Main mac 出 `AUX-MAC-HANDOFF-YYYY-MM-DD.md`(含每任务 Phase-0 预算 + premortem + 加速方案 + 落盘路径 + 审核备注 + 给 Kimi 的清晰指令)→ Aux mac/Kimi 执行 → 最终结果 CSV/verdict 写回同步目录让 Main mac 看到。
- **Main mac 跑出的"无 MLX numpy fallback"数字必须在 Aux mac 用 MLX 复跑才算合规。**

### 2. 加速强制（差 ~100×）
- 每个脚本启动日志**必须**出现 `MLX=True`（aux）+ `NEON=True`。
- 编码用 MLX GPU `mx.matmul`(分 chunk)；dot 用 `hdc_neon`(NEON Rust)。
- PoC 必须验证加速生效(3 层 D=500K < 180s)。纯 numpy 跑 = 立即停，修好再跑。
- 禁用:`np.argpartition`(用 `torch.topk`)、逐 token Python 循环(用向量化 matmul)、纯 numpy 权重编码。

### 3. 中间数据落盘 = 非同步目录
- **同步目录(禁写大中间态)**:`~/Documents/CC/`、`~/Documents/CC_big_files/`(均 Syncthing 监控)。
- **本机 scratch(所有 checkpoint / 大 npz / 激活 / 中间态)**:`~/hdc_scratch/`(在 ~/Documents 外，Syncthing 不碰)。脚本启动 `mkdir -p ~/hdc_scratch`，`CACHE_DIR = os.path.expanduser('~/hdc_scratch')`。
- 只有最终结果 CSV/JSON + verdict markdown(KB 级)写回同步目录。
- 原因:GB 级中间态写进同步目录 → 堵死两台机器的 Syncthing。

### 4. 先审核再跑
- Kimi-origin 脚本启动前必审:读逻辑 → PoC → 确认无 NaN / 结果合理 / 有进展日志。
- 重点查:argpartition vs topk、down_proj 是否向量化、有无 checkpoint 逻辑、有无逐 token 循环。

### 5. 并发内存预算(2026-05-31 OOM 事件后锁入)
- 并发多任务时:**Σ(各任务峰值 RSS) < 物理内存 − OS 余量(~16GB)**,否则 swap 颠簸 = 比串行还慢。
- **D≥8M(R_v=hidden×D×4B≈29GB+)是内存巨兽,必须独占机器**,不与任何其他重任务并发。大 D 任务用 gate 串行(`while pgrep -f <其他重任务>; do sleep 20; done` 再起)。
- 监控信号:`sysctl vm.swapusage` 的 used 快速增长 → 立即干预(杀低优先级 / 串行化)。
- 事件记录:`logs/EVENT-2026-05-31-0005-aux-d8m-swap-thrash.md`。

---

## Phase 0: 预规划（Pre-Plan）— 动手前 5 分钟

### 必填项
| 项 | 内容 | 示例 |
|---|---|---|
| 目标 | 一句话说清楚要验证什么 | "sparse_ternary D=500K 是否能在 10 分钟内完成" |
| 成功标准 | 量化指标 | "单 cell < 600s，recall@k > 0.90" |
| 失败标准 | 什么情况下放弃 | ">1200s 仍无输出，或内存 > 80GB" |
| 范围 | 跑哪些 config | "仅 L12, D=500K, 3 seeds" |
| **加速方案** | **MLX/NEON/MPS 用哪些** | **"MLX 权重+输入编码，NEON dot，MPS forward"** |

### 预 mortem（必做）
**假设这个实验已经死了，死因是什么？**

| 死因 | 概率 | 预防 | 检测信号 |
|------|------|------|---------|
| 内存踩踏 | 高 | 按 D 值限制并行度 | RSS > 30GB/进程 |
| GPU 超时 | 中 | MLX matmul 分 chunk | CPU 满载但 log 无输出 > 5min |
| 缓存失效 | 中 | 启动前检查 /tmp/hdc_cache | "Using shared weights" 未出现 |
| 死锁 | 低 | 避免 multiprocessing 嵌套 | CPU=0% 但进程未退出 |
| 结果丢失 | 低 | CSV append 模式 + flush | 日志文件大小不增长 |

---

## Phase 1: 探索与设计（Explore）— 三角色之 Explorer

- 读代码确认瓶颈位置
- **写技术 spec 时必须包含加速方案**（参考 AGENTS.md 6 项检查清单）
- 新脚本必须从 `TEMPLATE-flywheel-perplexity.py` 拷贝，不是从零写
- **无 spec 不编码**

---

## Phase 2: 小规模验证（PoC）— 先跑 1 个 cell

### PoC 原则
- 永远先跑 **1 个最小 config** 验证通路
- 确认 log 输出正常、CSV 写入正常、内存曲线健康
- **PoC 通过后才启动全量**

### PoC 检查清单
- [ ] 进程启动后 30s 内有 log 输出
- [ ] 内存占用在预期范围内（参考 Phase 0 内存预算表）
- [ ] CSV 文件有新增行
- [ ] 结果值在合理区间（无 NaN、无 0.000）
- [ ] **加速生效验证**：log 中出现 `MLX=True` 或 `Rust NEON=True`
- [ ] **速度验证**：PoC 的 3 层耗时 < 180s（D=500K）

---

## Phase 3: 全量执行（Execute）— 三角色之 Coder

### 启动前必做
```bash
# 1. 检查缓存
ls /tmp/hdc_cache/weights_L*.npz

# 2. 设置环境
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=3
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONUNBUFFERED=1

# 3. 根据 D 值限制并行度
if grep -q "1300000" ffn_hdc_sweep.py; then MAX_PROC=1
elif grep -q "500000" ffn_hdc_sweep.py; then MAX_PROC=4
else MAX_PROC=8; fi

# 4. 检查加速依赖
python3 -c "import mlx.core as mx; print('MLX OK')"
python3 -c "import sys; sys.path.insert(0,'08-infrastructure/hdc_speed_and_variants/hdc_neon_rs'); from hdc_neon import int8_dot_and_nnz_batch; print('NEON OK')"
```

### 启动后必做
- 启动后台监控脚本（每 60s 更新 STATUS.md）
- 保留 `launch_L6_12_18.sh` 级别的启动脚本供恢复
- **启动 experiment_monitor.py 实时监控**

---

## Phase 3.5: Checkpoint 与回滚机制（Checkpoint & Rollback）

> **核心原则：死机不是最可怕的，最可怕的是死机后从头再来。**

### 为什么需要 Checkpoint

从 sweep 死机事件和今晚的因果验证实验（v1-v3 全部失败，每次都从头提取激活）提炼出的教训：
- 激活提取占 80% 时间，但脚本一旦崩溃就全部丢失
- 没有 checkpoint = 没有容错能力
- 没有实时监控 = 崩溃后 N 小时才发现

### Checkpoint 设计规范

**何时保存 checkpoint**：
| 阶段 | 触发条件 | 保存内容 | 预估大小 |
|------|---------|---------|---------|
| 激活提取 | 每完成 500 chunks | `acts_checkpoint_N.pkl` | ~2GB |
| HDC 编码 | 完成后 | `hv_checkpoint.pkl` | ~0.6GB |
| Monosemantic | 完成后 | `dims_checkpoint.pkl` | ~10MB |
| Classifier | 完成后 | `proto_checkpoint.pkl` | ~1MB |
| Ablation | 每完成 1 个剂量 | `ablation_checkpoint_ratio_X.pkl` | ~1MB |

**Checkpoint 文件命名**：
```
{experiment_name}_checkpoint_{stage}_{timestamp}.pkl

例：
  hdc_causal_ablation_checkpoint_acts_1500_20260528_231200.pkl
  hdc_causal_ablation_checkpoint_hv_20260528_231500.pkl
  hdc_causal_ablation_checkpoint_ablation_50pct_20260528_232000.pkl
```

**Checkpoint 保存示例**（在实验脚本中嵌入）：
```python
import pickle
from pathlib import Path

def save_checkpoint(stage: str, data: dict, experiment_name: str):
    """Save intermediate results for rollback."""
    checkpoint_dir = Path("02-experiments/results/checkpoints")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = checkpoint_dir / f"{experiment_name}_checkpoint_{stage}_{ts}.pkl"
    with open(path, 'wb') as f:
        pickle.dump(data, f)
    print(f"[CHECKPOINT] Saved: {path} ({path.stat().st_size/1024/1024:.1f} MB)")
    return path

# 在激活提取循环中：
if chunk_idx > 0 and chunk_idx % 500 == 0:
    save_checkpoint(f"acts_{chunk_idx}", {
        'acts_partial': all_acts_so_far,
        'chunk_idx': chunk_idx,
    }, experiment_name="hdc_causal_ablation")
```

### 回滚机制

**自动检测失败**：
```bash
# experiment_monitor.py 检测到 Traceback/Error/Timeout
# → 自动列出可用 checkpoints
# → 建议回滚命令
```

**手动回滚**：
```bash
# 查看可用 checkpoints
ls -lt 02-experiments/results/checkpoints/hdc_causal_ablation_checkpoint_*

# 从 checkpoint 恢复并继续
python3 hdc_causal_ablation.py --resume-from \
  02-experiments/results/checkpoints/hdc_causal_ablation_checkpoint_acts_1500_20260528_231200.pkl
```

**脚本中的恢复逻辑**：
```python
def load_latest_checkpoint(experiment_name: str, stage_prefix: str):
    """Find and load the most recent checkpoint matching stage_prefix."""
    checkpoint_dir = Path("02-experiments/results/checkpoints")
    checkpoints = sorted(
        checkpoint_dir.glob(f"{experiment_name}_checkpoint_{stage_prefix}_*.pkl"),
        key=lambda p: p.stat().st_mtime
    )
    if not checkpoints:
        return None
    latest = checkpoints[-1]
    with open(latest, 'rb') as f:
        data = pickle.load(f)
    print(f"[ROLLBACK] Loaded checkpoint: {latest.name}")
    return data
```

---

## Phase 4: 实时监控（Monitor）— 三角色之 COO

### 监控频率
| 时间 | 动作 |
|------|------|
| T+0s | 确认所有进程启动，log 有输出 |
| T+60s | 检查 CSV 是否有新增 |
| T+300s | 检查内存是否超标 |
| 每 60s | 更新 STATUS.md |
| **每 30s** | **experiment_monitor.py 扫描 log** |
| **每 500 chunks** | **自动保存 checkpoint** |

### 监控工具：experiment_monitor.py

```bash
# 基础监控（显示进度、ETA、错误检测）
python3 02-experiments/scripts/experiment_monitor.py \
  --log logs/hdc_causal_ablation_v4_2327.log \
  --experiment-name hdc_causal_ablation \
  --check-interval 30 \
  --stall-threshold 300 \
  --notify-on-error

# 高级监控（检测到错误时自动退出，便于自动化回滚）
python3 02-experiments/scripts/experiment_monitor.py \
  --log logs/hdc_causal_ablation_v4_2327.log \
  --experiment-name hdc_causal_ablation \
  --check-interval 30 \
  --notify-on-error \
  --exit-on-error \
  --auto-rollback
```

**监控输出示例**：
```
[23:30:15] PROGRESS: 1600/3096 (51.7%) @ 2.8 chunks/s | ETA: 8.9min
[23:30:45] PROGRESS: 1728/3096 (55.8%) @ 2.9 chunks/s | ETA: 7.8min
[23:31:15] PROGRESS: 1856/3096 (60.0%) @ 2.9 chunks/s | ETA: 7.1min
[23:32:15] ⚠️  STALL DETECTED: No progress for 300s
  🔔 Process may be hung or crashed.
[23:32:15] 🚨 ERROR DETECTED!
  Traceback (most recent call last):
    File "hdc_causal_ablation.py", line 350...

📦 Available checkpoints for rollback:
  hdc_causal_ablation_checkpoint_acts_1500_20260528_231200.pkl (1.8 GB)
  hdc_causal_ablation_checkpoint_hv_20260528_231500.pkl (0.6 GB)

💡 To rollback: Restart experiment with --resume-from {checkpoint_path}
```

### 干预阈值
| 信号 | 动作 |
|------|------|
| 内存 > 35GB/进程 | 杀掉超标的，降低并行度 |
| CPU 满载但 log 无输出 > 5min | 检查是否卡在 encode_weights |
| CSV 30min 无新增 | 检查进程是否还活着 |
| 出现 "leaked semaphore" | 进程已崩溃，立即重启 |
| **experiment_monitor 报告 ERROR** | **立即检查 checkpoint，决定回滚或修复** |
| **experiment_monitor 报告 STALL > 10min** | **进程可能死锁，kill + 从 checkpoint 恢复** |

---

## Phase 5: 实时归档（Live Archive）— 执行中不丢经验

### 边跑边写
- **任何异常** → 立刻记入 `logs/EVENT-YYYYMMDD-HHMM.md`
- **任何发现** → 立刻记入 `09-archive/YYYY-MM-DD/`
- **任何配置** → 立刻更新 `RECOVERY.md`

### 模板
```markdown
# EVENT-2026-05-28-1100 — 6 进程并行导致 swap thrashing

## 现象
6 个 D=500K 进程并行，RSS 33-35GB/进程，~200GB 总内存，128GB 物理内存溢出。

## 根因
D=500K h_gate_f32 ≈ 10GB，gate+up ≈ 20GB。6×20GB = 120GB + 开销 → swap。

## fix
并行度降至 4。mao L6/12/18 + wikitext L6 先跑，完成后换 wikitext L12/18。

## 教训
- D≥500K 时 max_proc = 4
- D≥1.3M 时 max_proc = 1-2
```

---

## Phase 6: 复盘与更新（Reflect）— 三角色之 COO Gate

### 复盘模板
1. **目标达成？** 是/否，偏差多少
2. **预 mortem 命中了哪些？** 哪些死因被预测到了
3. **新出现的死因？** 加入方法论
4. **可复用模式？** 加入 `cheatsheet.md`
5. **哪些文档需要更新？** AGENTS.md / RECOVERY.md / 本方法论

### 定义完成
- [ ] verification note 存在
- [ ] cheatsheet.md 更新
- [ ] 本方法论文档更新（如果有新教训）

---

## 与三角色系统的映射

| 本方法论 | 三角色 |
|---------|--------|
| Phase 0 预规划 | Explorer 的 mission note |
| Phase 1 探索设计 | Explorer 的 spec |
| Phase 2 PoC | Coder 的首次实现 + COO 的首次验证 |
| Phase 3 全量执行 | Coder 的全量部署 |
| Phase 4 实时监控 | COO 的持续验证 |
| Phase 5 实时归档 | COO 的 live documentation |
| Phase 6 复盘 | COO 的 verification note + cheatsheet 更新 |

---

## Phase 0 补充: Performance Budget（性能预算）

> 2026-05-28 补充。任何脚本写代码前必须先填此表。

| 项 | 必填 |
|---|---|
| 总时间预算 | 例如: "30 分钟" |
| 单层耗时预算 | 例如: "< 30s" |
| 内存预算 | 例如: "< 20GB" |
| 如果超预算的 Plan B | 例如: "用 torch.topk 替代 argpartition" |

**规则**: 答不上来 = 不准写代码。

## Phase 2 补充: PoC Profiling（性能验证）

PoC 不是只验证"对不对"，必须验证"快不快"。

### PoC 性能检查清单
- [ ] 跑 3 层 D=500K，总耗时 < 180s
- [ ] 单层 hook（如有）耗时 < 30s
- [ ] 内存峰值 < 20GB
- [ ] log 中有进展追踪输出（每层/每步）

**不通过 = 不准进全量。**

## Session 启动仪式

每次新 session 开始时，Agent 必须：
1. 读 `02-experiments/flywheel/LESSONS-LEARNED.md`
2. 读 `AGENTS.md` 检查清单
3. 确认当前任务是否符合 Performance Budget


---

## Phase 6: 认识论纪律 — How Not To Fool Yourself (added 2026-06-10, from the sign-language sprint)

> Phase 0–5 keep the experiment from CRASHING. Phase 6 keeps the RESULT from LYING.
> Every item below was learned by violating it during the 2026-06-10 sign-language session.

### 6.1 Baseline-audit gate (violated 3×) — THE most expensive trap
A result is only as honest as what it's compared against. Three times a verdict said
"X beats HDC / breaks the wall" — each against a **crippled baseline**:
- flatten+simhash HDC (14.5%) instead of the real per-frame+bigram pipeline (41%)
- bigram+10-signer HDC (20.9%) instead of permute+12-signer best (41%)
- a single-signer PoC (86%) instead of the 5-signer mean (52% ±20)

**Rule:** the baseline in a comparison MUST be the strongest config you have, run in the
SAME script on the SAME folds. "Beats baseline" against a weaker-than-your-best config is an
artifact, not a finding. Before reporting any Δ, ask: "is this baseline my actual best?"

### 6.2 A PoC is a smoke test, not a result — and report the variance
1-seed/1-fold/1-signer numbers are for "does the pipeline run + are values sane," NOT for
conclusions. The 86%→52% collapse was because the PoC drew the easiest signer. **Always report
std across the held-out UNIT (signer/cut), not just the mean.** Huge std (±20) = the headline mean
is meaningless; the real story is the distribution.

### 6.3 Surprise → suspect the TOOL first (the faith principle, operationalized)
When a result contradicts a strong prior ("rich features should help", "within-signer should be
high"), the first hypothesis is a BUG/encoding flaw, not a discovery. Cheap checks before believing:
collapse-to-chance? (training broke), wrong baseline? (6.1), degenerate inputs? (NaN/zeros),
single-cell fluke? (6.2). Only after these survive is it territory.

### 6.4 Import the weapon, don't reinvent it
Reimplementing simhash/walsh/RFF inline = unaudited + silently wrong (the "walsh" was a fake FWHT).
ALWAYS `from hdc_ops import ...` the canonical encoder. A reinvented weapon is not the weapon.

### 6.5 Completeness honesty (no silent partial sweeps)
"Swept the arsenal" must mean ALL of it, or state exactly which N of M were run and why. Claiming a
sweep while testing 6 of 11 encoders (and faking one) is the same sin as a 1-config null.

### 6.6 Monitors are session-scoped; cross-session needs cron
A persistent in-session Monitor DIES on session restart — it cannot track across sessions. For
"always know what's running," a cron/launchd job writing a STATUS file that the SessionStart hook
surfaces is the only durable mechanism. Don't promise cross-session tracking from an in-session tool.

### 6.7 Soft rules fail under task pressure; gate with the harness
Memory/CLAUDE.md/skills are deprioritized when chasing a sub-goal (this whole discipline kept getting
skipped). Only a harness HOOK (PreToolUse / UserPromptSubmit injecting the checklist + invoking
science-method) reliably fires at the decision point, every session. Enforcement > intention.

## Phase 7: Strategic meta-disciplines (added 2026-06-13, from a boundary-scan session)

> 6.3 keeps a *result* from lying. These four keep a *program* from lying — they were distilled after a
> session that caught two of its own over-claims and corrected them.

### 7.1 Suspect-the-tool includes your OWN theory
6.3 says a surprising result is a tool bug first. Stronger: an elegant theory *you proposed* is also a
hypothesis until a breaking-point test survives. In one session we caught two over-claims — a recall
disambiguator that mislabeled representational confusion as a search-branching limit, and a hierarchical
router whose "exponential (D/20)·G^depth" capacity law had the mechanism backwards (the real lever was
hash-WIDTH, not tree-depth). **No claim is real until a kit emit at the breaking point survives.** Elegance
is an alarm, not a medal.

### 7.2 Simplest mechanism beats elegant (枯れた技術)
Hash-buckets beat a router-tree; two binary cells in differential columns beat a multilevel cell. Default to
the dumb-cheap-robust solution — it is usually also the deployable (µW / deterministic) one.

### 7.3 Negative results are half the map
Where a lever FAILS (a learned map on pure identity tokens; tree-depth adding no router capacity) is as
valuable as where it works. Log each failure as a boundary on the spot — it saves future rounds.

### 7.4 Push to the breaking point (anti-touch-and-go, quantified)
Shallow tests flatter wrong theories (8× load looked fine; 128× exposed a placebo). Before "CONFIRM," sweep
load/scale to **≥100× the suspected wall**; close a thread only at LEVERS-EXHAUSTED.
