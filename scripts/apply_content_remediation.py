#!/usr/bin/env python3
"""Apply durable content remediation operations to a curriculum SQLite database."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_DATA = ROOT / "backend" / "app" / "data" / "content_remediation"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def activity_content_signature(value: object) -> str:
    if not isinstance(value, dict):
        return canonical_json(value)
    content = dict(value)
    content.pop("generation_source", None)
    content.pop("generation_src", None)
    for key in ("choices", "options"):
        choices = content.get(key)
        if isinstance(choices, list) and all(isinstance(choice, dict) for choice in choices):
            content[key] = sorted(
                choices,
                key=lambda choice: (
                    str(choice.get("text") or choice.get("choice_text") or ""),
                    bool(choice.get("is_correct")),
                ),
            )
    return canonical_json(content)


@dataclass
class ApplyStats:
    operations: int = 0
    removed: int = 0
    inserted: int = 0
    updated: int = 0
    already_applied: int = 0


def ensure_remediation_log(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS content_remediation_log (
            operation_hash TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now'))
        )
        """
    )


def reset_content_remediation_log(db: sqlite3.Connection) -> None:
    ensure_remediation_log(db)
    db.execute("DELETE FROM content_remediation_log")


def operation_hash(generation_source: str, operation: dict[str, Any]) -> str:
    payload = canonical_json({
        "generation_source": generation_source,
        "operation": operation,
    })
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_operations(data_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    loaded: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(data_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = str(payload.get("target_generation_source") or "question_agent")
        for operation in payload.get("operations", []):
            loaded.append((source, operation))
    return loaded


def paragraph_db_id(db: sqlite3.Connection, para_id: str) -> str:
    row = db.execute(
        "SELECT id FROM paragraphs WHERE para_id = ?",
        (para_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Missing paragraph: {para_id}")
    return str(row[0])


def find_questions(
    db: sqlite3.Connection,
    para_id: str,
    generation_source: str,
    match: dict[str, Any],
) -> list[str]:
    matches: list[str] = []
    for row in db.execute(
        """
        SELECT id, explanation, difficulty FROM quiz_questions
        WHERE para_id = ? AND generation_src = ?
          AND question_type = ? AND question_text = ?
        ORDER BY id
        """,
        (
            para_id,
            generation_source,
            match["question_type"],
            match["question_text"],
        ),
    ):
        if "explanation" in match and str(row[1] or "") != str(match["explanation"] or ""):
            continue
        if "difficulty" in match and int(row[2] or 2) != int(match["difficulty"]):
            continue
        if "choices" in match:
            choices = [
                {
                    "text": choice[0],
                    "is_correct": bool(choice[1]),
                }
                for choice in db.execute(
                    """
                    SELECT choice_text, is_correct FROM question_choices
                    WHERE question_id = ? ORDER BY sort_order, id
                    """,
                    (row[0],),
                )
            ]
            expected = [
                {
                    "text": choice["text"],
                    "is_correct": bool(choice.get("is_correct")),
                }
                for choice in match["choices"]
            ]
            choice_key = lambda choice: (choice["text"], choice["is_correct"])
            if sorted(choices, key=choice_key) != sorted(expected, key=choice_key):
                continue
        matches.append(str(row[0]))
    return matches


def find_flashcards(
    db: sqlite3.Connection,
    para_id: str,
    generation_source: str,
    match: dict[str, Any],
) -> list[str]:
    return [
        str(row[0])
        for row in db.execute(
            """
            SELECT id FROM flashcards
            WHERE para_id = ? AND generation_src = ?
              AND card_type = ? AND front = ? AND back = ?
            ORDER BY id
            """,
            (
                para_id,
                generation_source,
                match["card_type"],
                match["front"],
                match["back"],
            ),
        )
    ]


def find_activities(
    db: sqlite3.Connection,
    para_id: str,
    generation_source: str,
    match: dict[str, Any],
) -> list[str]:
    expected = activity_content_signature(match["content"])
    matches: list[str] = []
    for row in db.execute(
        """
        SELECT id, content_json FROM activities
        WHERE para_id = ? AND generation_src = ? AND activity_type = ?
        ORDER BY id
        """,
        (para_id, generation_source, match["activity_type"]),
    ):
        if activity_content_signature(json.loads(row[1])) == expected:
            matches.append(str(row[0]))
    return matches


def find_targets(
    db: sqlite3.Connection,
    entity_type: str,
    para_id: str,
    generation_source: str,
    match: dict[str, Any],
) -> list[str]:
    if entity_type == "question":
        return find_questions(db, para_id, generation_source, match)
    if entity_type == "flashcard":
        return find_flashcards(db, para_id, generation_source, match)
    if entity_type == "activity":
        return find_activities(db, para_id, generation_source, match)
    raise ValueError(f"Unsupported entity type: {entity_type}")


def delete_target(db: sqlite3.Connection, entity_type: str, target_id: str) -> None:
    if entity_type == "question":
        db.execute("DELETE FROM question_choices WHERE question_id = ?", (target_id,))
        db.execute("DELETE FROM quiz_questions WHERE id = ?", (target_id,))
    elif entity_type == "flashcard":
        db.execute("DELETE FROM flashcards WHERE id = ?", (target_id,))
    elif entity_type == "activity":
        db.execute("DELETE FROM activities WHERE id = ?", (target_id,))
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")


def replacement_match(entity_type: str, replacement: dict[str, Any]) -> dict[str, Any]:
    if entity_type == "question":
        return {
            "question_text": replacement["question_text"],
            "question_type": replacement["question_type"],
            "explanation": replacement.get("explanation", ""),
            "difficulty": int(replacement.get("difficulty", 2)),
            "choices": replacement.get("choices", []),
        }
    if entity_type == "flashcard":
        return {
            "front": replacement["front"],
            "back": replacement["back"],
            "card_type": replacement.get("card_type", "definition"),
        }
    if entity_type == "activity":
        return {
            "activity_type": replacement["activity_type"],
            "content": replacement["content"],
        }
    raise ValueError(f"Unsupported entity type: {entity_type}")


def insert_question(
    db: sqlite3.Connection,
    paragraph_id: str,
    para_id: str,
    generation_source: str,
    item: dict[str, Any],
) -> None:
    question_id = str(uuid.uuid4())
    db.execute(
        """
        INSERT INTO quiz_questions
            (id, paragraph_db_id, para_id, question_text, question_type,
             explanation, difficulty, generation_src, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            question_id,
            paragraph_id,
            para_id,
            item["question_text"],
            item["question_type"],
            item.get("explanation", ""),
            int(item.get("difficulty", 2)),
            generation_source,
        ),
    )
    for sort_order, choice in enumerate(item.get("choices", [])):
        db.execute(
            """
            INSERT INTO question_choices
                (id, question_id, choice_text, is_correct, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                question_id,
                choice["text"],
                int(bool(choice.get("is_correct"))),
                sort_order,
            ),
        )


def insert_flashcard(
    db: sqlite3.Connection,
    paragraph_id: str,
    para_id: str,
    generation_source: str,
    item: dict[str, Any],
) -> None:
    db.execute(
        """
        INSERT INTO flashcards
            (id, paragraph_db_id, para_id, front, back, card_type, generation_src)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            paragraph_id,
            para_id,
            item["front"],
            item["back"],
            item.get("card_type", "definition"),
            generation_source,
        ),
    )


def update_flashcard(
    db: sqlite3.Connection,
    flashcard_id: str,
    generation_source: str,
    item: dict[str, Any],
) -> None:
    db.execute(
        """
        UPDATE flashcards
        SET back = ?, generation_src = ?
        WHERE id = ?
        """,
        (
            item["back"],
            generation_source,
            flashcard_id,
        ),
    )


def find_flashcard_slot(
    db: sqlite3.Connection,
    para_id: str,
    card_type: str,
    front: str,
) -> str | None:
    row = db.execute(
        """
        SELECT id FROM flashcards
        WHERE para_id = ? AND card_type = ? AND front = ?
        ORDER BY id LIMIT 1
        """,
        (para_id, card_type, front),
    ).fetchone()
    return None if row is None else str(row[0])


def insert_activity(
    db: sqlite3.Connection,
    paragraph_id: str,
    para_id: str,
    generation_source: str,
    item: dict[str, Any],
) -> None:
    content = dict(item["content"])
    content["generation_source"] = generation_source
    db.execute(
        """
        INSERT INTO activities
            (id, paragraph_db_id, para_id, activity_type, content_json,
             difficulty, generation_src, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            str(uuid.uuid4()),
            paragraph_id,
            para_id,
            item["activity_type"],
            json.dumps(content, ensure_ascii=False),
            int(item.get("difficulty", content.get("difficulty", 2))),
            generation_source,
        ),
    )


def update_activity(
    db: sqlite3.Connection,
    activity_id: str,
    generation_source: str,
    item: dict[str, Any],
) -> None:
    content = dict(item["content"])
    content["generation_source"] = generation_source
    db.execute(
        """
        UPDATE activities
        SET content_json = ?, difficulty = ?, is_verified = 1
        WHERE id = ?
        """,
        (
            json.dumps(content, ensure_ascii=False),
            int(item.get("difficulty", content.get("difficulty", 2))),
            activity_id,
        ),
    )


def find_activity_slot(
    db: sqlite3.Connection,
    para_id: str,
    generation_source: str,
    activity_type: str,
) -> str | None:
    row = db.execute(
        """
        SELECT id FROM activities
        WHERE para_id = ? AND generation_src = ? AND activity_type = ?
        ORDER BY id LIMIT 1
        """,
        (para_id, generation_source, activity_type),
    ).fetchone()
    return None if row is None else str(row[0])


def insert_replacement(
    db: sqlite3.Connection,
    entity_type: str,
    paragraph_id: str,
    para_id: str,
    generation_source: str,
    item: dict[str, Any],
) -> None:
    if entity_type == "question":
        insert_question(db, paragraph_id, para_id, generation_source, item)
    elif entity_type == "flashcard":
        insert_flashcard(db, paragraph_id, para_id, generation_source, item)
    elif entity_type == "activity":
        insert_activity(db, paragraph_id, para_id, generation_source, item)
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")


def apply_content_remediation(
    db: sqlite3.Connection,
    data_dir: Path = DEFAULT_DATA,
) -> ApplyStats:
    stats = ApplyStats()
    ensure_remediation_log(db)
    for generation_source, operation in load_operations(data_dir):
        stats.operations += 1
        fingerprint = operation_hash(generation_source, operation)
        if db.execute(
            "SELECT 1 FROM content_remediation_log WHERE operation_hash = ?",
            (fingerprint,),
        ).fetchone():
            stats.already_applied += 1
            continue
        entity_type = operation["entity_type"]
        para_id = operation["para_id"]
        targets = find_targets(
            db,
            entity_type,
            para_id,
            generation_source,
            operation["match"],
        )
        if len(targets) > 1:
            raise ValueError(
                f"Ambiguous {entity_type} remediation target in {para_id}: "
                f"{operation['match']}"
            )

        replacements = operation.get("replacements", [])
        replacement_targets = [
            find_targets(
                db,
                entity_type,
                para_id,
                generation_source,
                replacement_match(entity_type, replacement),
            )
            for replacement in replacements
        ]
        replacement_exists = all(replacement_targets)
        if not targets:
            if operation["action"] == "remove" or replacement_exists:
                stats.already_applied += 1
                db.execute(
                    "INSERT INTO content_remediation_log (operation_hash) VALUES (?)",
                    (fingerprint,),
                )
                continue
            if entity_type == "activity" and operation["action"] == "replace" and replacements:
                updated_any = False
                for replacement in replacements:
                    existing_activity_id = find_activity_slot(
                        db,
                        para_id,
                        generation_source,
                        replacement["activity_type"],
                    )
                    if existing_activity_id is None:
                        continue
                    update_activity(db, existing_activity_id, generation_source, replacement)
                    stats.updated += 1
                    updated_any = True
                if updated_any:
                    db.execute(
                        "INSERT INTO content_remediation_log (operation_hash) VALUES (?)",
                        (fingerprint,),
                    )
                    continue
            if entity_type == "flashcard" and operation["action"] == "replace" and replacements:
                updated_any = False
                for replacement in replacements:
                    existing_flashcard_id = find_flashcard_slot(
                        db,
                        para_id,
                        replacement.get("card_type", "definition"),
                        replacement["front"],
                    )
                    if existing_flashcard_id is None:
                        continue
                    update_flashcard(db, existing_flashcard_id, generation_source, replacement)
                    stats.updated += 1
                    updated_any = True
                if updated_any:
                    db.execute(
                        "INSERT INTO content_remediation_log (operation_hash) VALUES (?)",
                        (fingerprint,),
                    )
                    continue
            raise ValueError(
                f"Missing {entity_type} remediation target in {para_id}: "
                f"{operation['match']}"
            )

        if replacements and replacement_exists and all(
            target_id in replacement_targets[index]
            for index, target_id in enumerate(targets[:len(replacement_targets)])
        ):
            stats.already_applied += 1
            db.execute(
                "INSERT INTO content_remediation_log (operation_hash) VALUES (?)",
                (fingerprint,),
            )
            continue

        delete_target(db, entity_type, targets[0])
        stats.removed += 1
        paragraph_id = paragraph_db_id(db, para_id)
        for replacement in replacements:
            if find_targets(
                db,
                entity_type,
                para_id,
                generation_source,
                replacement_match(entity_type, replacement),
            ):
                continue
            if entity_type == "activity":
                existing_activity_id = find_activity_slot(
                    db,
                    para_id,
                    generation_source,
                    replacement["activity_type"],
                )
                if existing_activity_id is not None:
                    update_activity(db, existing_activity_id, generation_source, replacement)
                    stats.updated += 1
                    continue
            if entity_type == "flashcard":
                existing_flashcard_id = find_flashcard_slot(
                    db,
                    para_id,
                    replacement.get("card_type", "definition"),
                    replacement["front"],
                )
                if existing_flashcard_id is not None:
                    update_flashcard(db, existing_flashcard_id, generation_source, replacement)
                    stats.updated += 1
                    continue
            insert_replacement(
                db,
                entity_type,
                paragraph_id,
                para_id,
                generation_source,
                replacement,
            )
            stats.inserted += 1
        db.execute(
            "INSERT INTO content_remediation_log (operation_hash) VALUES (?)",
            (fingerprint,),
        )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    if not args.no_backup:
        shutil.copy2(args.db, args.db.with_suffix(args.db.suffix + ".remediation.bak"))

    db = sqlite3.connect(args.db)
    try:
        db.execute("PRAGMA foreign_keys = ON")
        stats = apply_content_remediation(db, args.data_dir)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        f"operations={stats.operations} removed={stats.removed} "
        f"inserted={stats.inserted} updated={stats.updated} "
        f"already_applied={stats.already_applied}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
