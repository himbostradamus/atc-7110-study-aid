#!/usr/bin/env python3
"""Remove empty paragraph branches from a content-expansion staging batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FAMILIES = ("questions", "activities", "flashcards")


def has_items(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("items"), list)
        and bool(payload["items"])
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.batch.read_text(encoding="utf-8"))
    removed = 0
    for family in FAMILIES:
        container = payload.get(family)
        if not isinstance(container, dict):
            continue
        retained = {
            para_id: para_payload
            for para_id, para_payload in container.items()
            if has_items(para_payload)
        }
        removed += len(container) - len(retained)
        payload[family] = retained

    args.batch.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"Normalized {args.batch}: removed {removed} empty paragraph branches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
