> *Note: absolute capacity numbers are the corrected/reconciled NeuroSim envelopes (a magnitude-audit caught an earlier ~10x Mini disagreement). Paths genericized to /path/to/neurosim.*

# NeuroSim V1.3 ARM64 Mac Sweep Data — Phase 47.7.10 Empirical Deliverables

> **2026-07 archive label:** this is the May-2026 sweep-data archive. It is useful provenance for how earlier Mini/Mid/Pro
> assumptions were tested and corrected. It is **not** the current C1 product boundary. Current public C1 starts at
> 0.1B / 0.3B / 1B / bounded 3B; rows mentioning 9B / 27B / 30B are historical inputs or C2/C3 frontier coordinates.

**Source**: Phase 47.7.10 NeuroSim V1.3 ARM64 native compile + 45+ data point sweeps (2026-05-19)

**Note**: This folder contains the **empirical sweep outputs + replication artifacts**. The full NeuroSim source tree was cloned into `../neurosim_v13_arm64_build/` (which has its own .git, gitignored — not tracked in main repo). To replicate the experiments, re-clone NeuroSim V1.3 + apply the patches shown in `*.patched` files below.

---

## Files

### Empirical sweep CSVs (45+ data points)

| File | Configs | Data |
|------|---------|------|
| `sweep_results.csv` | 7 Mini SKU configs × ResNet18 | A baseline through G 32nm 4-bit |
| `mid_sku_sweep_results.csv` | 4 Mid SKU × 2 networks (Qwen3.5-9B + Qwen3-VL-30B-A3B) = 8 | M1-M4 storage proxy + parallel CIM |
| `pro_sku_sweep_results.csv` | 5 Pro SKU × 2 networks (Qwen3.5-27B + 35B-A3B) = 10 | P1-P5 6L/8L/14nm |
| `cellbit_sweep_results.csv` | 20 conservative cellBit configs (Mini 4 + Mid 8 + Pro 8) | 2-bit + 3-bit MLC variants |
| `blackmagic_sweep_results.csv` | 8 black-magic empirical (pipeline + SRAM buffer) | Qwen3.5-9B block |

### LLM-class NetWork.csv adapters (W1 deliverables)

In `networks/`:
- `build_llm_netcsv.py` — Python generator (transformer block → 1×1 conv 7-layer NetWork.csv)
- `NetWork_Qwen35_4B_block.csv` (48.2M params per block)
- `NetWork_Qwen35_9B_block.csv` (177.2M params per block)
- `NetWork_Qwen35_27B_block.csv` (275.3M params per block)
- `NetWork_Qwen3VL_30B_A3B_block.csv` (45.1M params per active expert)
- `NetWork_Qwen35_35B_A3B_block.csv` (68.8M params per active expert)

### Sweep driver scripts (W2/W3/W3.5/W6)

In `networks/`:
- `sku_sweep.sh` — Mid + Pro SKU sweep (4-bit baseline)
- `cellbit_sweep.sh` — cellBit conservative sweep (2-bit + 3-bit)
- `blackmagic_sweep.sh` — pipeline + SRAM buffer sweep

### Replication artifacts (apply to fresh NeuroSim V1.3 clone)

- `makefile.patched` — Apple clang + libomp via Homebrew (`-Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -L/opt/homebrew/opt/libomp/lib -lomp`)
- `main.cpp.patched` — Standalone exit after `ChipCalculateArea` (no PyTorch wrapper needed for area sim)
- `Param.cpp.patched` — Default config (will be overwritten by sweep scripts)

---

## Replication Recipe (Mac M4 Max ARM64)

```bash
# Install libomp
brew install libomp

# Clone NeuroSim V1.3 fresh
cd /tmp && git clone https://github.com/neurosim/DNN_NeuroSim_V1.3.git neurosim_v13
cd neurosim_v13/Inference_pytorch/NeuroSIM

# Apply patches
cp /path/to/neurosim_sweep_data/makefile.patched ./makefile
cp /path/to/neurosim_sweep_data/main.cpp.patched ./main.cpp
cp /path/to/neurosim_sweep_data/Param.cpp.patched ./Param.cpp

# Build
make

# Smoke test
./main NetWork_VGG8.csv 8 8

# Run sweeps using scripts in this folder's networks/ subfolder
cp /path/to/neurosim_sweep_data/networks/*.sh ./
bash sku_sweep.sh
bash cellbit_sweep.sh
bash blackmagic_sweep.sh
```

---

## Key Empirical Findings (per `neurosim-verification-data-extended-2026-05-19.md`)

**Post-self-audit honest envelopes** (4-die × 350 mm², 22nm 4-bit MLC, 0.55 sim-to-silicon haircut):

| SKU × cellBit | 2-bit | 3-bit | 4-bit |
|---------------|-------|-------|-------|
| Mini SKU 6L Pure CIM (M3) | 3.07 GB | 3.74 GB | **5.58 GB** |
| Mid SKU CIM-storage (M1) | 1.19 GB | 1.44 GB | 2.16 GB |
| Pro SKU 6L (P1 academic) | 1.77 GB | 2.16 GB | 3.22 GB |
| Pro SKU 6L (P3 storage-lean) | 3.45 GB | 4.20 GB | **6.27 GB** |
| Pro SKU 8L Year 5+ | 1.91 GB | 2.33 GB | 3.48 GB |

**Critical finding**: Mid SKU NeuroSim CIM-mode ≠ NAND-storage target (20 GB requires Toshiba-style crossbar, NeuroSim cannot model). See `neurosim-verification-data-extended-2026-05-19.md` §1.

---

## Cross-References

- `../neurosim-verification-data-extended-2026-05-19.md` — Full 3-SKU × 3-cellBit analysis using this data
- `../neurosim-self-audit-attack-2026-05-19.md` — Self-audit caught Mb/1024 8× bug before ship
- `../neurosim-verification-data-2026-05-19.md` — Mini SKU baseline (W7 Phase 47.7.9)
- `../models/chip_model_adapter.py` — D18 NeuroSimCalibration class consuming this data
