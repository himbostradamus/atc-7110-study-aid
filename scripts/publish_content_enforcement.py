#!/usr/bin/env python3
"""Publish deterministic prompt and choice-order enforcement operations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_OUT = (
    ROOT / "backend" / "app" / "data" / "content_remediation"
    / "zz_content_enforcement.json"
)
SOURCE = "question_agent"
PARA_ID = r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?"
LEADING_LOCATION_RE = re.compile(
    rf"(?i)^(?P<prefix>(?:fill\s+in\s+the\s+blank|complete):\s*)?"
    rf"(?:under|according\s+to|per)\s+(?:the\s+)?"
    rf"(?:(?:paragraph|para|section|tbl|table)\s+|"
    rf"note(?:\s+\d+)?\s+(?:to|in|of)\s+)?"
    rf"{PARA_ID}(?:\([^)]+\))?(?:\s+note)?\s*[:,]?\s*"
)
TRAILING_LOCATION_RE = re.compile(
    rf"(?i)\s+(?:under|according\s+to|per|in)\s+(?:the\s+)?"
    rf"(?:(?:paragraph|para|section|tbl|table)\s+|"
    rf"note(?:\s+\d+)?\s+(?:to|in|of)\s+)?"
    rf"{PARA_ID}(?:\([^)]+\))?(?:\s+note)?(?=[?.!,;:]|$)"
)
REMOVE_QUESTIONS = {
    (
        "8-1-9",
        "Under 8-1-9, in addition to the oceanic non-RVSM exceptions listed in "
        "8-1-9b, where else are excepted aircraft listed for RVSM operations?",
    ),
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_location(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = LEADING_LOCATION_RE.sub(
        lambda match: match.group("prefix") or "",
        value,
    )
    cleaned = TRAILING_LOCATION_RE.sub("", cleaned)
    cleaned = normalize_space(cleaned)
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def target_position(stable_key: str, choice_count: int) -> int:
    return hashlib.sha256(stable_key.encode("utf-8")).digest()[0] % choice_count


def reorder_choices(choices: list[dict[str, Any]], stable_key: str) -> bool:
    if len(choices) < 3:
        return False
    correct = [
        index for index, choice in enumerate(choices)
        if bool(choice.get("is_correct"))
    ]
    if len(correct) != 1:
        return False
    target = target_position(stable_key, len(choices))
    current = correct[0]
    if current == target:
        return False
    selected = choices.pop(current)
    choices.insert(target, selected)
    for index, choice in enumerate(choices):
        if "sort_order" in choice:
            choice["sort_order"] = index
    return True


def question_operations(db: sqlite3.Connection) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    rows = db.execute(
        """
        SELECT id, para_id, question_text, question_type, explanation, difficulty
        FROM quiz_questions
        WHERE generation_src = ?
        ORDER BY para_id, question_text, id
        """,
        (SOURCE,),
    ).fetchall()
    for row in rows:
        if (row[1], row[2]) in REMOVE_QUESTIONS:
            operations.append({
                "entity_type": "question",
                "para_id": row[1],
                "action": "remove",
                "severity": "minor",
                "categories": ["document_trivia"],
                "problem": (
                    "The item asks where another exception list is located instead of testing "
                    "which aircraft qualify or how the exception is applied."
                ),
                "source_basis": (
                    "Other retained items test supervisor approval, geographic limits, and "
                    "workload-permitting accommodation of oceanic non-RVSM exceptions."
                ),
                "match": {
                    "question_text": row[2],
                    "question_type": row[3],
                },
            })
            continue
        choices = [
            {"text": choice[0], "is_correct": bool(choice[1])}
            for choice in db.execute(
                """
                SELECT choice_text, is_correct FROM question_choices
                WHERE question_id = ? ORDER BY sort_order, id
                """,
                (row[0],),
            )
        ]
        cleaned = strip_location(row[2])
        changed = cleaned != row[2]
        if row[3] == "multiple_choice":
            changed = reorder_choices(
                choices,
                f"question:{row[1]}:{cleaned}",
            ) or changed
        if not changed:
            continue
        replacement = {
            "question_text": cleaned,
            "question_type": row[3],
            "explanation": row[4] or "",
            "difficulty": int(row[5] or 2),
            "choices": choices,
        }
        operations.append({
            "entity_type": "question",
            "para_id": row[1],
            "action": "replace",
            "severity": "minor",
            "categories": ["prompt_context", "answer_position"],
            "problem": (
                "Enforce a self-contained learner prompt and answer ordering that does not "
                "depend on source-object position."
            ),
            "source_basis": "The operational content and answer set are unchanged.",
            "match": {
                "question_text": row[2],
                "question_type": row[3],
            },
            "replacements": [replacement],
        })
    return operations


def flashcard_operations(db: sqlite3.Connection) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for row in db.execute(
        """
        SELECT para_id, front, back, card_type
        FROM flashcards
        WHERE generation_src = ?
          AND card_type NOT IN ('reference', 'source_reference')
        ORDER BY para_id, front
        """,
        (SOURCE,),
    ):
        cleaned = strip_location(row[1])
        if cleaned == row[1]:
            continue
        replacement = {
            "front": cleaned,
            "back": row[2],
            "card_type": row[3],
        }
        operations.append({
            "entity_type": "flashcard",
            "para_id": row[0],
            "action": "replace",
            "severity": "minor",
            "categories": ["prompt_context"],
            "problem": "Remove paragraph-location scaffolding from the retrieval cue.",
            "source_basis": "The card answer and controlling concept are unchanged.",
            "match": {
                "front": row[1],
                "back": row[2],
                "card_type": row[3],
            },
            "replacements": [replacement],
        })
    return operations


def activity_operations(db: sqlite3.Connection) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for row in db.execute(
        """
        SELECT para_id, activity_type, content_json, difficulty
        FROM activities
        WHERE generation_src = ?
        ORDER BY para_id, activity_type
        """,
        (SOURCE,),
    ):
        content = json.loads(row[2])
        replacement_content = json.loads(row[2])
        changed = False
        if row[1] not in {"source_lookup", "source_use"}:
            for field in (
                "situation", "clearance", "lookup_context", "para_context",
                "question_text", "task", "instruction",
            ):
                old = replacement_content.get(field)
                new = strip_location(old)
                if new != old:
                    replacement_content[field] = new
                    changed = True
        choices = replacement_content.get("choices")
        if isinstance(choices, list):
            changed = reorder_choices(
                choices,
                f"activity:{row[0]}:{row[1]}:"
                f"{replacement_content.get('question_text') or replacement_content.get('situation') or ''}",
            ) or changed
        if not changed:
            continue
        replacement = {
            "activity_type": row[1],
            "difficulty": int(row[3] or replacement_content.get("difficulty", 2)),
            "content": replacement_content,
        }
        operations.append({
            "entity_type": "activity",
            "para_id": row[0],
            "action": "replace",
            "severity": "minor",
            "categories": ["prompt_context", "answer_position"],
            "problem": (
                "Enforce a self-contained activity prompt and answer ordering that does not "
                "depend on source-object position."
            ),
            "source_basis": "The scenario, controlling rule, and answer set are unchanged.",
            "match": {
                "activity_type": row[1],
                "content": content,
            },
            "replacements": [replacement],
        })
    return operations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    db = sqlite3.connect(args.db)
    try:
        operations = (
            question_operations(db)
            + flashcard_operations(db)
            + activity_operations(db)
        )
    finally:
        db.close()

    payload = {
        "version": 1,
        "target_generation_source": SOURCE,
        "summary": {
            "purpose": (
                "Mechanical enforcement after semantic chapter review: remove learner-facing "
                "paragraph scaffolding and balance multiple-choice answer positions."
            ),
            "operation_count": len(operations),
        },
        "operations": operations,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for operation in operations:
        entity_type = operation["entity_type"]
        counts[entity_type] = counts.get(entity_type, 0) + 1
    print(f"operations={len(operations)} by_type={counts} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
