#!/usr/bin/env python3
"""LLM-Class NetWork.csv Generator for NeuroSim V1.3 (Phase 47.7.10 W1).

Generates NeuroSim-compatible NetWork.csv files for LLM transformer blocks.
Each Linear layer is encoded as 1×1 convolution with degenerate spatial dims:
    1, 1, in_features, 1, 1, out_features, novel_mapping_flag, stride

A transformer block becomes 7 "fake conv layers":
    Q proj, K proj, V proj, O proj, FFN gate, FFN up, FFN down

NeuroSim sim 1 block, then post-process × num_blocks for full model.

Per Phase 47.7.10 plan §W1.
"""

from typing import Dict
from pathlib import Path

# LLM architecture specs (verified against Hugging Face Qwen team + DeepSeek team releases)
# Source: model-families-spec-reference-2026-05-19.md
LLM_ARCHS: Dict[str, dict] = {
    "Qwen35_4B": {
        "d_model": 2048,
        "num_kv_heads": 4,
        "head_dim": 128,  # d_kv per head
        "d_ff": 6144,
        "num_blocks": 36,  # estimate, Qwen3.5-4B
        "params_b": 4.0,
        "quant_size_q4_gb": 2.4,
        "notes": "Mini SKU primary baseline candidate"
    },
    "Qwen35_9B": {
        "d_model": 4096,
        "num_kv_heads": 4,
        "head_dim": 256,  # Phase 47.7 measured (NOT 128)
        "d_ff": 11008,
        "num_blocks": 32,  # Phase 47.7 measured (NOT 36)
        "params_b": 9.0,
        "quant_size_q4_gb": 5.5,
        "notes": "Mini SKU stretch / Mid SKU baseline"
    },
    "Qwen3VL_30B_A3B": {
        # Qwen3-VL-30B-A3B MoE: 30B total / 3B active (per Qwen3-VL Oct 2025 release)
        "d_model": 2048,  # smaller than dense, MoE has more experts
        "num_kv_heads": 4,
        "head_dim": 128,
        "d_ff": 5632,  # per active expert
        "num_blocks": 28,  # estimate
        "num_experts": 64,  # MoE
        "top_k_experts": 6,
        "params_b": 30.0,
        "active_params_b": 3.0,
        "quant_size_q4_gb": 16.0,
        "notes": "Mid SKU MoE proxy (real Qwen3-VL Oct 2025)"
    },
    "Qwen35_35B_A3B": {
        # Speculative — Qwen3.5-35B-A3B MoE Feb 2026
        "d_model": 2560,
        "num_kv_heads": 4,
        "head_dim": 128,
        "d_ff": 6912,
        "num_blocks": 32,
        "num_experts": 64,
        "top_k_experts": 6,
        "params_b": 35.0,
        "active_params_b": 3.0,
        "quant_size_q4_gb": 18.0,
        "notes": "Mid SKU stretch / Pro SKU baseline (MoE)"
    },
    "Qwen35_27B": {
        # Qwen3.5-27B Dense Feb 2026
        "d_model": 5120,
        "num_kv_heads": 8,
        "head_dim": 128,  # GQA 8 heads × 128 = 1024 kv channels
        "d_ff": 13824,
        "num_blocks": 48,
        "params_b": 27.0,
        "quant_size_q4_gb": 14.0,
        "notes": "Pro SKU primary dense candidate"
    },
}


def build_block_csv(model_key: str, output_dir: str = ".") -> str:
    """Generate NeuroSim NetWork.csv for a single transformer block of given model.

    Format per row: IFM_H, IFM_W, IFM_C, K_H, K_W, OFM_C, novel_mapping_flag, stride
    Linear layer = 1x1 conv: 1, 1, in, 1, 1, out, 0, 1

    Returns: path to written CSV.
    """
    if model_key not in LLM_ARCHS:
        raise KeyError(f"Unknown model: {model_key}. Available: {list(LLM_ARCHS.keys())}")
    arch = LLM_ARCHS[model_key]

    d_model = arch["d_model"]
    kv_channels = arch["num_kv_heads"] * arch["head_dim"]
    d_ff = arch["d_ff"]

    # 7 "fake conv" layers per transformer block
    layers = [
        # Q projection: d_model → d_model
        (1, 1, d_model, 1, 1, d_model, 0, 1),
        # K projection: d_model → num_kv_heads * head_dim (GQA shrinks K size)
        (1, 1, d_model, 1, 1, kv_channels, 0, 1),
        # V projection: d_model → num_kv_heads * head_dim
        (1, 1, d_model, 1, 1, kv_channels, 0, 1),
        # O projection: d_model → d_model
        (1, 1, d_model, 1, 1, d_model, 0, 1),
        # FFN gate (SwiGLU): d_model → d_ff
        (1, 1, d_model, 1, 1, d_ff, 0, 1),
        # FFN up: d_model → d_ff
        (1, 1, d_model, 1, 1, d_ff, 0, 1),
        # FFN down: d_ff → d_model
        (1, 1, d_ff, 1, 1, d_model, 0, 1),
    ]

    output_path = Path(output_dir) / f"NetWork_{model_key}_block.csv"
    with open(output_path, "w") as f:
        for row in layers:
            f.write(",".join(str(v) for v in row) + "\n")
    return str(output_path)


def compute_block_params(model_key: str) -> float:
    """Compute weights count in one transformer block (in millions of params)."""
    arch = LLM_ARCHS[model_key]
    d_model = arch["d_model"]
    kv_channels = arch["num_kv_heads"] * arch["head_dim"]
    d_ff = arch["d_ff"]
    # Q + K + V + O + FFN_gate + FFN_up + FFN_down
    params = (
        d_model * d_model  # Q
        + d_model * kv_channels  # K
        + d_model * kv_channels  # V
        + d_model * d_model  # O
        + d_model * d_ff  # FFN gate
        + d_model * d_ff  # FFN up
        + d_ff * d_model  # FFN down
    )
    return params / 1e6  # in millions


if __name__ == "__main__":
    import sys
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Writing LLM NetWork.csv files to: {out_dir}")
    print()
    print(f"{'Model':<22} {'d_model':>8} {'kv_ch':>6} {'d_ff':>6} {'blocks':>7} {'block_MP':>10} {'full_BP':>9}")
    print("-" * 75)
    for model_key in LLM_ARCHS:
        arch = LLM_ARCHS[model_key]
        path = build_block_csv(model_key, out_dir)
        block_mp = compute_block_params(model_key)
        full_bp = block_mp * arch["num_blocks"] / 1000
        print(f"{model_key:<22} {arch['d_model']:>8} {arch['num_kv_heads']*arch['head_dim']:>6} {arch['d_ff']:>6} {arch['num_blocks']:>7} {block_mp:>10.1f} {full_bp:>9.2f}")
    print()
    print(f"Files written to {out_dir}/")
