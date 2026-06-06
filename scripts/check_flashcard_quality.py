#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "curriculum.db"

GENERIC_FRONT_PATTERNS = (
    re.compile(r"^§\d", re.IGNORECASE),
    re.compile(r"What is the rule\?$", re.IGNORECASE),
    re.compile(r"^When does .+ apply\?$", re.IGNORECASE),
    re.compile(r"^State the phraseology for", re.IGNORECASE),
)

WEAK_BACK_PATTERNS = (
    re.compile(r"(?:take the following actions|includes the following|the following actions|the following information|the following procedures):\s*1\.?$", re.IGNORECASE),
    re.compile(r":\s*1\.?$"),
)

REQUIRED_FLASHCARDS = (
    ("1-2-6", "What does APREQ stand for?", "Approval Request"),
    ("1-2-6", "Which abbreviation stands for Approval Request?", "APREQ"),
    ("1-2-6", "What can AAR stand for in FAA Order JO 7110.65?", "Adapted arrival route; Airport arrival rate"),
    ("1-2-6", "Which abbreviation is used for the MEARTS interfacility handoff Ambiguity-A disparity condition?", "AM"),
    ("1-2-6", "Which abbreviation is used for the STARS interfacility handoff Ambiguity-A disparity condition?", "AMB"),
)


def main() -> int:
    db = sqlite3.connect(DB_PATH)
    rows = db.execute(
        "SELECT para_id, front, back, generation_src FROM flashcards ORDER BY para_id, front"
    ).fetchall()
    row_keys = {(para_id, (front or "").strip(), (back or "").strip()) for para_id, front, back, _ in rows}

    failures: list[str] = []
    for para_id, front, back, generation_src in rows:
        front = (front or "").strip()
        back = (back or "").strip()

        if generation_src != "curated":
            failures.append(f"{para_id}: non-curated flashcard remains ({generation_src})")
            continue
        if not front or not back:
            failures.append(f"{para_id}: front/back must be non-empty")
            continue
        if len(front) > 180:
            failures.append(f"{para_id}: front exceeds 180 characters")
        if len(back) > 220:
            failures.append(f"{para_id}: back exceeds 220 characters")
        for pattern in GENERIC_FRONT_PATTERNS:
            if pattern.search(front):
                failures.append(f"{para_id}: generic front matches {pattern.pattern!r}")
                break
        for pattern in WEAK_BACK_PATTERNS:
            if pattern.search(back):
                failures.append(f"{para_id}: weak back matches {pattern.pattern!r}")
                break

    for required in REQUIRED_FLASHCARDS:
        if required not in row_keys:
            failures.append(f"missing required flashcard: {required[0]} | {required[1]} => {required[2]}")

    if failures:
        print("Flashcard quality failures:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print(f"All {len(rows)} flashcard quality checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
