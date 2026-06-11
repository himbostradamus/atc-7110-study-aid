#!/usr/bin/env python3
"""Distribute correct-choice positions without changing authored choice text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FAMILIES = ("questions", "activities")


def choice_list(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    for key in ("choices", "options"):
        value = item.get(key)
        if isinstance(value, list):
            return value
    return None


def rebalance(payload: dict[str, Any]) -> tuple[int, dict[int, int]]:
    changed = 0
    positions: dict[int, int] = {}
    sequence = 0
    for family in FAMILIES:
        container = payload.get(family)
        if not isinstance(container, dict):
            continue
        for para_id in sorted(container):
            para_payload = container[para_id]
            if not isinstance(para_payload, dict):
                continue
            items = para_payload.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                choices = choice_list(item)
                if not choices or len(choices) < 2:
                    continue
                correct = [
                    index
                    for index, choice in enumerate(choices)
                    if isinstance(choice, dict) and bool(choice.get("is_correct"))
                ]
                if len(correct) != 1:
                    continue

                target = sequence % len(choices)
                sequence += 1
                current = correct[0]
                if current != target:
                    answer = choices.pop(current)
                    choices.insert(target, answer)
                    changed += 1
                for index, choice in enumerate(choices):
                    if isinstance(choice, dict) and "sort_order" in choice:
                        choice["sort_order"] = index
                positions[target] = positions.get(target, 0) + 1
    return changed, positions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", nargs="+", type=Path)
    args = parser.parse_args()

    for batch in args.batches:
        payload = json.loads(batch.read_text(encoding="utf-8"))
        changed, positions = rebalance(payload)
        batch.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        distribution = ", ".join(
            f"{position}:{count}" for position, count in sorted(positions.items())
        )
        print(
            f"Rebalanced {batch}: moved {changed} correct choices; "
            f"positions={{{distribution}}}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
