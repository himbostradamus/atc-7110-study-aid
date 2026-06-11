#!/usr/bin/env python3
"""Validate complete item coverage and finding references in an expansion audit."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


FAMILIES = ("questions", "activities", "flashcards")
VERDICTS = {
    "safe_to_publish",
    "safe_with_fixes",
    "block_publication_pending_fixes",
}
SEVERITIES = {"critical", "major", "minor", "suggestion"}


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level value must be an object")
    return payload


def batch_paths(batch: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for family in FAMILIES:
        container = batch.get(family)
        if not isinstance(container, dict):
            continue
        for para_id, para_payload in container.items():
            if not isinstance(para_payload, dict):
                continue
            items = para_payload.get("items")
            if not isinstance(items, list):
                continue
            for index in range(len(items)):
                paths.add(f"{family}.{para_id}.items[{index}]")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    batch = load(args.batch)
    report = load(args.report)
    expected = batch_paths(batch)
    reviewed = report.get("reviewed_item_paths")
    errors: list[str] = []

    if report.get("verdict") not in VERDICTS:
        errors.append(f"invalid verdict: {report.get('verdict')!r}")
    if not isinstance(reviewed, list) or not all(isinstance(path, str) for path in reviewed):
        errors.append("reviewed_item_paths must be a list of strings")
        reviewed_paths: list[str] = []
    else:
        reviewed_paths = reviewed
        duplicates = sorted(path for path, count in Counter(reviewed_paths).items() if count > 1)
        if duplicates:
            errors.append(f"duplicate reviewed paths: {', '.join(duplicates)}")
        missing = sorted(expected - set(reviewed_paths))
        extra = sorted(set(reviewed_paths) - expected)
        if missing:
            errors.append(f"missing {len(missing)} item paths: {', '.join(missing[:10])}")
        if extra:
            errors.append(f"unknown {len(extra)} item paths: {', '.join(extra[:10])}")

    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for index, finding in enumerate(findings):
            location = f"findings[{index}]"
            if not isinstance(finding, dict):
                errors.append(f"{location} must be an object")
                continue
            if finding.get("item_path") not in expected:
                errors.append(f"{location}.item_path is not in the staged batch")
            if finding.get("severity") not in SEVERITIES:
                errors.append(f"{location}.severity is invalid")
            for field in ("para_id", "category", "problem", "source_basis", "recommended_action"):
                if not str(finding.get(field) or "").strip():
                    errors.append(f"{location}.{field} is required")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Audit validation failed: {len(errors)} error(s).")
        return 1
    print(
        f"Audit validation passed: {len(expected)} reviewed item(s), "
        f"{len(findings)} finding(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
