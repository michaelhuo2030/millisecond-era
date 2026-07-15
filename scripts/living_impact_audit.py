#!/usr/bin/env python3
"""Portable living-impact manifest auditor.

Run in a project folder that has living-impact-map.json:
  python3 living_impact_audit.py
"""
import argparse
import fnmatch
import glob
import json
import pathlib
import re
import sys


def _norm(path, base):
    path = pathlib.Path(path).resolve()
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        try:
            return "../" + path.relative_to(base.parent).as_posix()
        except ValueError:
            return path.as_posix()


def _path(rel, base):
    return (base / rel).resolve()


def _expand(patterns, base):
    out = set()
    for pat in patterns:
        for hit in glob.glob(str(base / pat), recursive=True):
            p = pathlib.Path(hit)
            if p.is_file():
                out.add(_norm(p, base))
    return out


def audit_manifest(manifest_path="living-impact-map.json", base=None):
    manifest_path = pathlib.Path(manifest_path).resolve()
    base = pathlib.Path(base).resolve() if base else manifest_path.parent
    issues = []
    if not manifest_path.exists():
        return [f"MISSING MANIFEST - {manifest_path}"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"BAD MANIFEST JSON - {manifest_path}: {exc}"]

    live = _expand(data.get("live_surface_globs", []), base)
    excluded = _expand(data.get("exclude_globs", []), base)
    live = sorted(live - excluded)

    for finding in data.get("findings", []):
        fid = finding.get("id", "<missing-id>")
        required = {item["path"]: item for item in finding.get("required_updates", [])}

        covered = set(required)
        for group in finding.get("unaffected_groups", []):
            covered |= _expand(group.get("globs", []), base)

        for path in live:
            if path not in covered:
                issues.append(f"UNCOVERED - [{fid}] {path} is in the live surface but has no required update or unaffected reason.")

        for rel, item in required.items():
            p = _path(rel, base)
            if not p.exists():
                issues.append(f"MISSING REQUIRED FILE - [{fid}] {rel}")
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for anchor in item.get("anchors", []):
                if anchor not in txt:
                    issues.append(f"ANCHOR MISSING - [{fid}] {rel} lacks {anchor!r}")

        for check in finding.get("semantic_checks", []):
            name = check.get("name", "unnamed semantic check")
            texts = []
            for rel in check.get("paths", []):
                p = _path(rel, base)
                if not p.exists():
                    issues.append(f"SEMANTIC FILE MISSING - [{fid}] [{name}] {rel}")
                    continue
                txt = p.read_text(encoding="utf-8", errors="ignore")
                texts.append(txt)
                for pattern in check.get("forbidden_patterns", []):
                    if re.search(pattern, txt, flags=re.IGNORECASE | re.MULTILINE):
                        issues.append(
                            f"SEMANTIC FORBIDDEN - [{fid}] [{name}] {rel} matches /{pattern}/"
                        )

            aggregate = "\n".join(texts)
            for pattern in check.get("required_patterns", []):
                if not re.search(pattern, aggregate, flags=re.IGNORECASE | re.MULTILINE):
                    issues.append(
                        f"SEMANTIC REQUIRED MISSING - [{fid}] [{name}] no checked file matches /{pattern}/"
                    )

    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="living-impact-map.json")
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    issues = audit_manifest(args.manifest, args.base)
    if issues:
        print("=== [living_impact_audit] DRIFT DETECTED ===")
        for issue in issues:
            print(f"  - {issue}")
        print(f"  ({len(issues)} issue(s). Update the manifest or affected surfaces.)")
        return 1
    print("[living_impact_audit] OK - every live surface is covered; required anchors and semantic checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
