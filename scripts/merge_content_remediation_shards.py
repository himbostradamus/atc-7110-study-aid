#!/usr/bin/env python3
"""Merge validated remediation shard manifests into a full chapter manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_content_remediation_manifest import ENTITY_TYPES, load_object, validate


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--shard-dir", type=Path, required=True)
    parser.add_argument("--manifest-dir", type=Path, required=True)
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-markdown", type=Path, required=True)
    args = parser.parse_args()

    packet = load_object(args.packet)
    shard_paths = sorted(args.shard_dir.glob("chapter_*_shard_*.json"))
    if not shard_paths:
        parser.error(f"no shard packets found in {args.shard_dir}")

    reviewed = {entity_type: [] for entity_type in ENTITY_TYPES}
    decisions: list[dict[str, Any]] = []
    patterns: list[str] = []
    guidance: list[str] = []
    overviews: list[str] = []
    action_counts = Counter()

    for shard_path in shard_paths:
        stem = shard_path.stem
        manifest_path = args.manifest_dir / f"{stem}_pass_{args.pass_number:02d}.json"
        if not manifest_path.exists():
            parser.error(f"missing shard manifest: {manifest_path}")
        shard = load_object(shard_path)
        manifest = load_object(manifest_path)
        reporter = validate(shard, manifest)
        if reporter.errors:
            for error in reporter.errors:
                print(f"ERROR {manifest_path.name}: {error}")
            return 1
        for entity_type in ENTITY_TYPES:
            reviewed[entity_type].extend(manifest["reviewed_item_ids"][entity_type])
        decisions.extend(manifest.get("decisions", []))
        summary = manifest.get("summary", {})
        overviews.append(str(summary.get("overall") or ""))
        patterns.extend(str(value) for value in summary.get("patterns", []))
        guidance.extend(str(value) for value in summary.get("generation_guidance", []))
        action_counts.update(
            decision.get("action")
            for decision in manifest.get("decisions", [])
            if isinstance(decision, dict)
        )

    merged = {
        "version": 1,
        "audit_type": "chapter_content_remediation",
        "chapter": packet["chapter"],
        "pass": args.pass_number,
        "status": "complete",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_item_ids": {
            entity_type: dedupe(reviewed[entity_type])
            for entity_type in ENTITY_TYPES
        },
        "summary": {
            "overall": (
                f"Chapter {packet['chapter']} was reviewed in {len(shard_paths)} "
                f"bounded source-grounded shards. Proposed changes: "
                f"{action_counts['replace']} replacements, "
                f"{action_counts['split']} splits, and "
                f"{action_counts['remove']} removals."
            ),
            "patterns": dedupe(patterns),
            "generation_guidance": dedupe(guidance),
            "shard_overviews": [value for value in overviews if value],
        },
        "decisions": decisions,
    }
    reporter = validate(packet, merged)
    if reporter.errors:
        for error in reporter.errors:
            print(f"ERROR merged: {error}")
        return 1

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.out_markdown.write_text(
        "\n".join([
            f"# Chapter {packet['chapter']} Content Remediation",
            "",
            merged["summary"]["overall"],
            "",
            "## Recurring Patterns",
            "",
            *[f"- {value}" for value in merged["summary"]["patterns"]],
            "",
            "## Generation Guidance",
            "",
            *[f"- {value}" for value in merged["summary"]["generation_guidance"]],
            "",
        ]),
        encoding="utf-8",
    )
    print(f"merged {len(shard_paths)} shard(s) -> {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
