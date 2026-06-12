#!/usr/bin/env python3
"""Apply an exact, reviewable prune manifest to staged expansion batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "backend"
    / "app"
    / "data"
    / "content_expansion_staging"
    / "pass_02_prune_manifest.json"
)
DEFAULT_STAGING = ROOT / "backend" / "app" / "data" / "content_expansion_staging"


def item_prompt(family: str, item: dict[str, Any]) -> str:
    if family == "questions":
        return str(item.get("question_text") or "")
    if family == "flashcards":
        return str(item.get("front") or "")
    if family == "activities":
        content = item.get("content", {})
        if isinstance(content, dict):
            for key in ("prompt", "question", "question_text", "scenario", "statement"):
                value = content.get(key)
                if isinstance(value, str) and value:
                    return value
        return ""
    raise ValueError(f"Unsupported family: {family}")


def prune_batch(path: Path, instructions: dict[str, Any]) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    removed = 0
    for family, paragraphs in instructions.items():
        family_payload = payload.get(family, {})
        for para_id, prefixes in paragraphs.items():
            if para_id not in family_payload:
                raise ValueError(f"{path.name}: missing {family}.{para_id}")
            items = family_payload[para_id].get("items", [])
            for prefix in prefixes:
                matches = [
                    index
                    for index, item in enumerate(items)
                    if item_prompt(family, item).startswith(prefix)
                ]
                if len(matches) != 1:
                    raise ValueError(
                        f"{path.name}: expected one match for "
                        f"{family}.{para_id} prefix {prefix!r}; found {len(matches)}"
                    )
                del items[matches[0]]
                removed += 1
            if not items:
                del family_payload[para_id]
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    total = 0
    for filename, instructions in manifest.get("remove", {}).items():
        path = args.staging_dir / filename
        count = prune_batch(path, instructions)
        total += count
        print(f"{filename}: removed {count}")
    print(f"removed_total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
