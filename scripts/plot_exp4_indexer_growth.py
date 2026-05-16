#!/usr/bin/env python3
"""Plot Exp 4 incremental indexer RSS growth vs antirez linear prediction.

Usage:
    python3 plot_exp4_indexer_growth.py <harness.jsonl> [--out exp4.png]

Output: dual-panel publication-grade chart
    LEFT  — absolute RSS (shows plateau)
    RIGHT — Δ RSS vs antirez README's 22 KB/token linear extrapolation
"""
import json
import sys
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


def load_exp4(jsonl_path: Path):
    tokens, rss = [], []
    for line in jsonl_path.read_text().splitlines():
        if not line.strip():
            continue
        evt = json.loads(line)
        if evt.get("type") == "exp_4_datapoint":
            tokens.append(evt["tokens"])
            rss.append(evt["rss_gb"])
    return tokens, rss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--out", type=Path, default=Path("exp4_indexer_growth.png"))
    args = ap.parse_args()

    tokens, rss = load_exp4(args.jsonl)
    if not tokens:
        print("No exp_4_datapoint events found", file=sys.stderr)
        sys.exit(1)

    baseline_tokens = tokens[0]
    baseline_rss = rss[0]
    delta_mb = [(r - baseline_rss) * 1024 for r in rss]

    KB_PER_TOKEN_LINEAR = 22.0
    linear_mb = [(t - baseline_tokens) * KB_PER_TOKEN_LINEAR / 1024 for t in tokens]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ax1.plot(tokens, rss, "o-", color="#1f77b4", linewidth=2, markersize=7,
             label="Measured RSS (ds4-server, --ctx 300K, 2-bit quant)")
    ax1.set_xlabel("Context tokens loaded", fontsize=11)
    ax1.set_ylabel("Process RSS (GB)", fontsize=11)
    ax1.set_title("Absolute RSS — basically flat across the context delta",
                  fontsize=12, fontweight="bold")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x/1000)}K"))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="lower right", fontsize=9)
    rss_span = max(rss) - min(rss)
    ax1.set_ylim(min(rss) - max(rss_span, 0.05) * 0.5,
                 max(rss) + max(rss_span, 0.05) * 1.0)

    ax2.plot(tokens, delta_mb, "o-", color="#2ca02c", linewidth=2, markersize=7,
             label="Measured Δ RSS from baseline")
    ax2.plot(tokens, linear_mb, "--", color="#d62728", linewidth=2,
             label="antirez README linear extrapolation\n(22 GB / 1M = 22 KB/token)")
    ax2.set_xlabel("Context tokens loaded", fontsize=11)
    ax2.set_ylabel("Δ RSS from baseline (MB)", fontsize=11)
    ratio = linear_mb[-1] / max(delta_mb[-1], 1)
    ax2.set_title(f"Measured Δ RSS is ~{ratio:.0f}× smaller than linear prediction",
                  fontsize=12, fontweight="bold")
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x/1000)}K"))
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", fontsize=9)

    fig.suptitle(
        "ds4-server incremental indexer growth — M4 Max 128 GB, ds4flash.gguf 2-bit (antirez Q2-K)",
        fontsize=13, fontweight="bold", y=1.02
    )
    fig.tight_layout()
    fig.savefig(args.out, dpi=180, bbox_inches="tight")
    print(f"Saved {args.out}")

    print(f"\nSummary:")
    print(f"  Datapoints: {len(tokens)}")
    print(f"  Range: {tokens[0]:,} -> {tokens[-1]:,} tokens (Δ {tokens[-1]-tokens[0]:,})")
    print(f"  RSS Δ measured: {delta_mb[-1]:.1f} MB")
    print(f"  RSS Δ linear-predicted: {linear_mb[-1]:.1f} MB")
    if linear_mb[-1] > 0:
        print(f"  Suppression: {(1 - delta_mb[-1]/linear_mb[-1])*100:.1f}%")
    span = tokens[-1] - tokens[0]
    if span > 0:
        print(f"  Effective KB/token: {delta_mb[-1] * 1024 / span:.2f}")


if __name__ == "__main__":
    main()
