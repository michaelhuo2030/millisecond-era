#!/usr/bin/env python3
"""Audit public millisecond-era docs for the 2026-07 C1 boundary.

This combines two gates:

1. required anchor checks on key public surfaces;
2. living-impact manifest coverage, so every live text surface is either updated
   or explicitly classified as unaffected/archive.

It also checks stale phrases in local context. A single "2026-07 update" label
near the top of a file is not enough to sanitize a stale claim 400 lines later.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

import living_impact_audit


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_ANCHORS: dict[str, list[str]] = {
    "README.md": [
        "C1 cleanroom update",
        "0.1B / 0.3B / 1B / bounded 3B",
        "C1 is the bridgehead, not the ceiling",
        "resident weights, single-stream, prefix-cache hit 0%",
        "not a 3W claim",
        "not an affiliation, partnership, customer relationship, endorsement, or confirmed delivery commitment",
    ],
    "index.html": [
        "C1 modeled target",
        "100B frontier later",
        "Origin → iteration → current",
        "not affiliation, partnership, endorsement, customer status, or confirmed delivery",
    ],
    "chip/C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md": [
        "Whole picture: C1 bridgehead, 100B frontier",
        "0.1B / 0.3B / 1B / bounded 3B",
        "same-task speed first",
        "resident weights, single-stream, prefix-cache hit 0%",
        "not a 3W claim",
        "not an affiliation, partnership, customer relationship, endorsement, or confirmed delivery",
    ],
    "chip/README.md": [
        "C1 is the bridgehead, not the ceiling",
        "Historical v1 decision now superseded",
    ],
    "chip/ADR-v1-architecture.md": [
        "2026-07 public update",
        "0.1B / 0.3B / 1B / bounded 3B",
    ],
    "article-1.md": ["2026-07 public update / historical record"],
    "docs/article-1-zh.md": ["2026-07 公开更新 / 历史稿标注"],
    "article-2.md": ["2026-07 public update / historical record"],
    "docs/article-2-zh.md": ["2026-07 公开更新 / 历史稿标注"],
    "article-3.md": ["2026-07 public update / frontier label"],
    "fpga/README.md": ["2026-07 C1 framing"],
    "fpga/SILICON-MEASURED-2026-06-13.md": ["2026-07 public update"],
    "data/neurosim_sweep_data/README.md": ["2026-07 archive label"],
    "docs/stage-1-validation/README.md": ["2026-07 archive label"],
    "rwkv-on-chip/README.md": ["2026-07 C1 framing"],
    "rwkv-on-chip/CAPABILITY-MAP.md": ["2026-07 C1 framing"],
    "learn/reram-cim-101.html": ["2026-07 C1 framing"],
    "learn/reram-cim-visual.html": ["2026-07 C1 framing"],
    "learn/reram-architecture.html": ["2026-07 C1 framing"],
    "learn/reram-cim-calculator.html": ["2026-07 C1 framing"],
    "learn/speed-trial.html": ["2026-07 C1 framing"],
    "learn/real-world-speed-proof.html": ["2026-07 C1"],
    "learn/fpga-llm-explainer.html": ["2026-07 C1 framing"],
    "learn/demos/index.html": ["2026-07 C1 framing"],
}


ARCHIVE_GLOBS = [
    "iteration-log-2026-05.md",
    "article-1.md",
    "article-2.md",
    "docs/article-1-zh.md",
    "docs/article-2-zh.md",
    "chip/model-2026-06/**",
    "data/neurosim_sweep_data/**",
    "docs/stage-1-validation/**",
    "specs/**",
    "rwkv-on-chip/models/**",
]


STALE_PATTERNS = [
    r"USB-C box",
    r"USB-C 盒子",
    r"Pro Cloud",
    r"\$850",
    r"\$5K",
    r"\$11,300",
    r"¥6K",
    r"Qwen3\.5-9B",
    r"Mini SKU primary",
    r"Mini SKU later",
    r"HDC on Mini SKU",
    r"The Mini SKU includes",
    r"27[–-]70B",
    r"3D stacked \(dropped\)",
    r"we abandoned it",
    r"Dropped: vertical stack",
    r"我们已弃",
    r"已弃 3D",
    r"4B ternary \(our v1\)",
    r"4B 三元\(我们的 v1\)",
    r"2[–-]5k tok/s",
    r"same silicon runs V4-Flash",
]


CURRENT_PERFORMANCE_SURFACES = [
    "README.md",
    "index.html",
    "chip/C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md",
    "OUTREACH-LOG.md",
    "cheatsheet.md",
]


FORBIDDEN_CURRENT_PATTERNS = [
    r"peak[- ]?reflex",
    r"峰值反应",
    r"巅峰反应",
    r"The first chip goes to antirez",
    r"the very first unit will go to him",
    r"First chip prototype dedicated to",
]


UPDATE_LABELS = [
    "2026-07 C1",
    "2026-07 public update",
    "2026-07 公开更新",
    "2026-07 archive label",
    "2026-07 frontier label",
    "historical record",
    "历史稿标注",
    "Historical only",
    "superseded",
    "取代",
    "archived v1 design record",
    "historical now",
    "C2/C3 frontier",
    "not a current product claim",
    "not a C1 product promise",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_archive(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in ARCHIVE_GLOBS)


def iter_public_text_files() -> list[Path]:
    out: list[Path] = []
    for suffix in ("*.md", "*.html", "*.js"):
        out.extend(ROOT.rglob(suffix))
    return [
        p
        for p in sorted(out)
        if ".git" not in p.parts
        and "node_modules" not in p.parts
        and not rel(p).startswith("scripts/")
    ]


def line_no(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def context_has_update_label(text: str, idx: int, radius: int = 700) -> bool:
    start = max(0, idx - radius)
    end = min(len(text), idx + radius)
    context = text[start:end]
    return any(label in context for label in UPDATE_LABELS)


def main() -> int:
    errors: list[str] = []

    for issue in living_impact_audit.audit_manifest(ROOT / "living-impact-map.json", base=ROOT):
        errors.append(f"living-impact: {issue}")

    for path, anchors in REQUIRED_ANCHORS.items():
        p = ROOT / path
        if not p.exists():
            errors.append(f"missing required surface: {path}")
            continue
        text = p.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor not in text:
                errors.append(f"{path}: missing anchor {anchor!r}")

    stale_res = [re.compile(p) for p in STALE_PATTERNS]
    for p in iter_public_text_files():
        path = rel(p)
        if is_archive(path):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pat in stale_res:
            for m in pat.finditer(text):
                if context_has_update_label(text, m.start()):
                    continue
                errors.append(
                    f"{path}:{line_no(text, m.start())}: stale phrase without nearby C1/archive label: {m.group(0)!r}"
                )

    forbidden_current_res = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_CURRENT_PATTERNS]
    for path in CURRENT_PERFORMANCE_SURFACES:
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for pat in forbidden_current_res:
            match = pat.search(text)
            if match:
                errors.append(
                    f"{path}:{line_no(text, match.start())}: forbidden current performance/origin phrase: {match.group(0)!r}"
                )

    if errors:
        print("PUBLIC_C1_CONSISTENCY_AUDIT FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PUBLIC_C1_CONSISTENCY_AUDIT PASS")
    print(
        f"Checked {len(REQUIRED_ANCHORS)} required public surfaces, "
        f"{len(iter_public_text_files())} text files, and living-impact coverage."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
