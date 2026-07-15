#!/usr/bin/env python3
"""Self-tests for the portable living-impact auditor.

Run next to a real living-impact-map.json after copying both scripts into a project folder.
The tests mutate temporary manifest copies only.
"""
import copy
import json
import tempfile
from pathlib import Path

import living_impact_audit


BASE = Path.cwd().resolve()
MANIFEST = BASE / "living-impact-map.json"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def audit_data(data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        tmp = Path(f.name)
    try:
        return living_impact_audit.audit_manifest(tmp, base=BASE)
    finally:
        tmp.unlink(missing_ok=True)


def expect(name, issues, needle=None, should_pass=False):
    if should_pass:
        if issues:
            raise AssertionError(f"{name}: expected pass, got {issues[:5]}")
        print(f"[PASS] {name}: clean")
        return
    if not issues:
        raise AssertionError(f"{name}: expected failure, got clean")
    if needle and not any(needle in issue for issue in issues):
        raise AssertionError(f"{name}: expected issue containing {needle!r}, got {issues[:8]}")
    print(f"[PASS] {name}: caught {needle or 'failure'}")


def first_required_with_anchor(data):
    for item in data["findings"][0].get("required_updates", []):
        if item.get("anchors"):
            return item["path"]
    raise AssertionError("manifest needs at least one required update with anchors")


def main():
    base = load_manifest()
    if not base.get("findings"):
        raise AssertionError("manifest needs at least one finding for self-test")

    expect("baseline real manifest", living_impact_audit.audit_manifest(MANIFEST, base=BASE), should_pass=True)

    missing_anchor = copy.deepcopy(base)
    missing_anchor["findings"][0]["required_updates"][0].setdefault("anchors", []).append("__SELFTEST_IMPOSSIBLE_ANCHOR__")
    expect("missing required anchor", audit_data(missing_anchor), "ANCHOR MISSING")

    uncovered = copy.deepcopy(base)
    victim = first_required_with_anchor(uncovered)
    uncovered["findings"][0]["required_updates"] = [
        item for item in uncovered["findings"][0]["required_updates"] if item["path"] != victim
    ]
    expect("uncovered live file", audit_data(uncovered), "UNCOVERED")

    missing_file = copy.deepcopy(base)
    missing_file["findings"][0]["required_updates"].append(
        {"path": "SELFTEST-DOES-NOT-EXIST.md", "anchors": ["anything"]}
    )
    expect("missing required file", audit_data(missing_file), "MISSING REQUIRED FILE")

    no_unaffected = copy.deepcopy(base)
    no_unaffected["findings"][0]["unaffected_groups"] = []
    expect("unaffected groups are enforced", audit_data(no_unaffected), "UNCOVERED")

    semantic_forbidden = copy.deepcopy(base)
    semantic_forbidden["findings"][0]["semantic_checks"] = [
        {
            "name": "selftest forbidden phrase",
            "paths": ["README.md"],
            "forbidden_patterns": ["C1 cleanroom update"],
        }
    ]
    expect("forbidden live phrase", audit_data(semantic_forbidden), "SEMANTIC FORBIDDEN")

    semantic_required = copy.deepcopy(base)
    semantic_required["findings"][0]["semantic_checks"] = [
        {
            "name": "selftest required phrase",
            "paths": ["README.md"],
            "required_patterns": ["__SELFTEST_IMPOSSIBLE_SEMANTIC_REQUIREMENT__"],
        }
    ]
    expect("required semantic phrase", audit_data(semantic_required), "SEMANTIC REQUIRED MISSING")

    print("[living_impact_selftest] OK - all negative and positive cases behaved as expected.")


if __name__ == "__main__":
    main()
