#!/usr/bin/env python3
"""Validate staged expansion activities against the frontend runtime contract."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.activity_generator import (
    normalize_activity_payload,
    validate_activity_payload,
)


DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"


def load_titles(db_path: Path) -> dict[str, str]:
    with sqlite3.connect(db_path) as db:
        return {
            str(para_id): str(title or "")
            for para_id, title in db.execute("SELECT para_id, title FROM paragraphs")
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", nargs="+", type=Path)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    titles = load_titles(args.db)
    failures: list[str] = []
    checked = 0
    for raw_path in args.batches:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        payload = json.loads(path.read_text(encoding="utf-8"))
        for para_id, override in payload.get("activities", {}).items():
            for index, item in enumerate(override.get("items", [])):
                checked += 1
                activity_type = str(item.get("activity_type") or "")
                content = dict(item)
                content.pop("activity_type", None)
                normalized = normalize_activity_payload(
                    activity_type,
                    content,
                    titles.get(para_id, ""),
                    para_id,
                )
                errors = validate_activity_payload(
                    activity_type,
                    normalized,
                    titles.get(para_id, ""),
                )
                if errors:
                    failures.append(
                        f"{path.name}: activities.{para_id}.items[{index}] "
                        f"({activity_type}): {'; '.join(errors)}"
                    )

    for failure in failures:
        print(f"ERROR: {failure}")
    if failures:
        print(f"Runtime validation failed: {len(failures)} of {checked} activities")
        return 1
    print(f"Runtime validation passed: {checked} activities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
