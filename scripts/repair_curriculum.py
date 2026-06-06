#!/usr/bin/env python3
"""
Repair the generated curriculum database in-place.

Current repairs:
  - Backfill missing True/False answer choices from curated overrides.
  - Sync curated quiz-question overrides.
  - Remove duplicate local-auto question stems within the same paragraph.
  - Regenerate invalid or ambiguous spot_the_error activities.
  - Backfill phraseology_builder, sequence_steps, directive_check, conditional_rule_check, term_definition_check,
    document_control_check, requirement_check, scope_check, capability_check, reference_check,
    minima_rule_check, list_membership, table_lookup, and example_check activities.
  - Backfill knowledge_check activities for paragraphs with thin activity coverage.
  - Sync curated flashcards and remove non-curated flashcards.
  - Backfill missing quiz questions.
"""

from __future__ import annotations

import asyncio
import argparse
import json
import re
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.curated_content import (
    get_curated_activity_override,
    load_curated_overrides,
)
from backend.app.services.curated_flashcards import load_curated_flashcard_overrides
from backend.app.services.activity_generator import (
    generate_activities_for_paragraph,
    normalize_activity_payload,
    validate_activity_payload,
)
from backend.app.services.local_generation import (
    build_action_choices,
    is_generic_action_distractor,
    normalise_ws,
)
from backend.app.services.question_generator import (
    choice_text_errors,
    GeneratedChoice,
    GeneratedQuestion,
    generate_questions_for_paragraph,
    local_auto_question_quality_errors,
    normalize_choice_text,
    normalize_question_text,
    question_text_errors,
    validate_generated_question,
)


SELF_CONTAINED_STATEMENT_TYPES = {
    "scope_check",
    "requirement_check",
    "capability_check",
    "conditional_rule_check",
    "term_definition_check",
    "document_control_check",
    "minima_rule_check",
}
DEPRECATED_ACTIVITY_TYPES = {"reference_check"}
LOCAL_AUTO_TEXT_LIMITS = {
    "conditional_rule_check": ("question_text", 220, 40),
    "minima_rule_check": ("question_text", 220, 42),
    "requirement_check": ("question_text", 220, 34),
    "scope_check": ("question_text", 220, 36),
    "situation_action": ("situation", 260, 42),
}
LIST_INTRO_CUE_RE = re.compile(
    r"\b(?:one of the following|as follows|"
    r"following conditions? (?:is|are) met|"
    r"following actions? (?:are|is) taken|"
    r"the following (?:conditions?|actions?|items?|information|services?|techniques?|procedures?))\b",
    re.IGNORECASE,
)


def _looks_list_dump(text: str) -> bool:
    clean = normalise_ws(text)
    if not clean:
        return False
    marker = re.search(r"\bThe applicable condition is:\s*", clean, re.IGNORECASE)
    if marker:
        tail = clean[marker.end():].strip()
        if tail:
            clean = tail
    if LIST_INTRO_CUE_RE.search(clean):
        return True
    if clean.count(";") >= 2:
        return True
    if ":" in clean:
        head, tail = clean.split(":", 1)
        if len(head.split()) >= 4 and len(tail.split()) >= 5:
            return True
    return False


def _local_auto_quality_errors(activity_type: str, payload: dict, generation_src: str) -> list[str]:
    if generation_src != "local_auto":
        return []

    errors: list[str] = []
    limit = LOCAL_AUTO_TEXT_LIMITS.get(activity_type)
    if limit:
        field, max_chars, max_words = limit
        text = normalise_ws(payload.get(field, ""))
        if len(text) > max_chars:
            errors.append(f"{field} exceeds {max_chars} characters")
        if len(text.split()) > max_words:
            errors.append(f"{field} exceeds {max_words} words")
        if _looks_list_dump(text):
            errors.append(f"{field} is a list dump rather than a focused prompt")

    if activity_type == "situation_action":
        para_context = normalise_ws(payload.get("para_context", ""))
        if para_context and (len(para_context) > 220 or _looks_list_dump(para_context)):
            errors.append("para_context is an overloaded procedural sentence")

    if activity_type == "list_membership":
        errors.append("refresh local-auto list-membership activity")
    if activity_type == "example_check":
        instruction = normalise_ws(payload.get("instruction", ""))
        question_text = normalise_ws(payload.get("question_text", ""))
        if instruction == "Is this an approved example from the section?":
            errors.append("example-check instruction lacks topic context")
        elif instruction in {
            "Is this an approved example?",
            "Is this approved wording?",
            "Is this approved phraseology?",
        }:
            match = re.search(r'"([^"]+)"', question_text)
            if match:
                token_count = len(re.findall(r"[A-Za-z0-9]+", match.group(1)))
                if token_count <= 3:
                    errors.append("example-check instruction lacks topic context")
        if re.search(r'"[^"]*[()/][^"]*"', question_text):
            errors.append("example-check uses placeholder or alternative text")
        if "..." in question_text or "…" in question_text:
            errors.append("example-check uses truncated ellipsis text")

    return errors


def load_true_false_answer_map() -> dict[tuple[str, str], str]:
    payload = load_curated_overrides()
    answer_map: dict[tuple[str, str], str] = {}

    for para_id, override in payload.get("questions", {}).items():
        for item in override.get("items", []):
            if item.get("question_type") != "true_false":
                continue
            answer = item.get("correct_answer")
            if answer is None:
                continue
            key = (para_id, item["question_text"].strip())
            if isinstance(answer, bool):
                answer_map[key] = "true" if answer else "false"
            else:
                answer_map[key] = str(answer).strip().lower()

    return answer_map


def ensure_backup(db_path: Path) -> Path:
    backup_path = db_path.with_suffix(db_path.suffix + ".bak")
    shutil.copy2(db_path, backup_path)
    return backup_path


def build_true_false_choices(correct_answer: str) -> list[tuple[str, int, int]]:
    if correct_answer == "true":
        return [("True", 1, 0), ("False", 0, 1)]
    if correct_answer == "false":
        return [("True", 0, 0), ("False", 1, 1)]
    return []


def repair_missing_true_false_choices(
    db: sqlite3.Connection,
    answer_map: dict[tuple[str, str], str],
) -> tuple[int, list[tuple[str, str]]]:
    repaired = 0
    unresolved: list[tuple[str, str]] = []

    rows = db.execute(
        """
        SELECT q.id, q.para_id, q.question_text
        FROM quiz_questions q
        LEFT JOIN question_choices c ON c.question_id = q.id
        WHERE q.question_type = 'true_false'
          AND c.id IS NULL
        ORDER BY q.para_id, q.question_text
        """
    ).fetchall()

    for question_id, para_id, question_text in rows:
        answer = answer_map.get((para_id, question_text.strip()))
        if not answer:
            unresolved.append((para_id, question_text))
            continue

        for choice_text, is_correct, sort_order in build_true_false_choices(answer):
            db.execute(
                """
                INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), question_id, choice_text, is_correct, sort_order),
            )
        repaired += 1

    return repaired, unresolved


def delete_duplicate_local_auto_questions(db: sqlite3.Connection) -> tuple[int, int]:
    removed_questions = 0
    duplicate_groups = 0

    rows = db.execute(
        """
        SELECT para_id, question_type, question_text, GROUP_CONCAT(id) AS ids
        FROM quiz_questions
        WHERE generation_src = 'local_auto'
        GROUP BY para_id, question_type, question_text
        HAVING COUNT(*) > 1
        ORDER BY para_id, question_type, question_text
        """
    ).fetchall()

    for _, _, _, id_csv in rows:
        ids = sorted(id_csv.split(","))
        keep_id = ids[0]
        drop_ids = ids[1:]
        if not drop_ids:
            continue

        duplicate_groups += 1
        removed_questions += len(drop_ids)

        for question_id in drop_ids:
            db.execute("DELETE FROM question_choices WHERE question_id = ?", (question_id,))
            db.execute("DELETE FROM quiz_questions WHERE id = ?", (question_id,))

    return duplicate_groups, removed_questions


def delete_deprecated_activities(db: sqlite3.Connection) -> int:
    deleted = 0
    for activity_type in sorted(DEPRECATED_ACTIVITY_TYPES):
        before = db.total_changes
        db.execute("DELETE FROM activities WHERE activity_type = ?", (activity_type,))
        deleted += db.total_changes - before
    return deleted


def delete_non_curated_phraseology_builders(db: sqlite3.Connection) -> int:
    before = db.total_changes
    db.execute(
        """
        DELETE FROM activities
        WHERE activity_type = 'phraseology_builder'
          AND generation_src != 'curated'
        """
    )
    return db.total_changes - before


def sync_replace_all_curated_activities(db: sqlite3.Connection) -> tuple[int, int, int]:
    overrides = load_curated_overrides().get("activities", {})
    paragraph_rows = {
        row["para_id"]: row
        for row in db.execute(
            "SELECT id, para_id, title FROM paragraphs ORDER BY chapter, section, para_id"
        ).fetchall()
    }

    synced_paragraphs = 0
    deleted = 0
    inserted = 0

    for para_id, override in overrides.items():
        if not isinstance(override, dict) or not override.get("replace_all"):
            continue

        paragraph = paragraph_rows.get(para_id)
        if paragraph is None:
            raise ValueError(f"Missing paragraph for curated replace_all override: {para_id}")

        items = override.get("items", [])
        normalized_rows: list[tuple[str, dict]] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Curated replace_all activity for {para_id} must be an object")
            activity_type = item.get("activity_type")
            if not activity_type:
                raise ValueError(f"Curated replace_all activity for {para_id} is missing activity_type")
            payload = dict(item)
            payload.pop("activity_type", None)
            normalized = normalize_activity_payload(
                activity_type,
                payload,
                paragraph["title"],
                para_id,
            )
            errors = validate_activity_payload(activity_type, normalized, paragraph["title"])
            if errors:
                joined = "; ".join(errors)
                raise ValueError(f"Invalid curated replace_all activity for {para_id}/{activity_type}: {joined}")
            normalized_rows.append((activity_type, normalized))

        before = db.total_changes
        db.execute("DELETE FROM activities WHERE para_id = ?", (para_id,))
        deleted += db.total_changes - before

        for activity_type, payload in normalized_rows:
            before = db.total_changes
            db.execute(
                """
                INSERT INTO activities
                    (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    paragraph["id"],
                    para_id,
                    activity_type,
                    json.dumps(payload),
                    int(payload.get("difficulty", 1)),
                    payload.get("generation_source", "curated"),
                ),
            )
            inserted += db.total_changes - before

        synced_paragraphs += 1

    return synced_paragraphs, deleted, inserted


def sync_replace_type_curated_activities(db: sqlite3.Connection) -> tuple[int, int, int]:
    overrides = load_curated_overrides().get("activities", {})
    paragraph_rows = {
        row["para_id"]: row
        for row in db.execute(
            "SELECT id, para_id, title FROM paragraphs ORDER BY chapter, section, para_id"
        ).fetchall()
    }

    synced_paragraphs = 0
    deleted = 0
    inserted = 0

    for para_id, override in overrides.items():
        if (
            not isinstance(override, dict)
            or override.get("replace_all")
            or not override.get("sync_replace_types")
        ):
            continue

        replace_types = [
            str(activity_type).strip()
            for activity_type in override.get("replace_types", [])
            if str(activity_type).strip()
        ]
        if not replace_types:
            continue

        paragraph = paragraph_rows.get(para_id)
        if paragraph is None:
            raise ValueError(f"Missing paragraph for curated replace-types override: {para_id}")

        items = override.get("items", [])
        normalized_rows: list[tuple[str, dict]] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Curated replace-types activity for {para_id} must be an object")
            activity_type = item.get("activity_type")
            if not activity_type:
                raise ValueError(f"Curated replace-types activity for {para_id} is missing activity_type")
            payload = dict(item)
            payload.pop("activity_type", None)
            normalized = normalize_activity_payload(
                activity_type,
                payload,
                paragraph["title"],
                para_id,
            )
            errors = validate_activity_payload(activity_type, normalized, paragraph["title"])
            if errors:
                joined = "; ".join(errors)
                raise ValueError(
                    f"Invalid curated replace-types activity for {para_id}/{activity_type}: {joined}"
                )
            normalized_rows.append((activity_type, normalized))

        delete_types = sorted(set(replace_types) | {activity_type for activity_type, _ in normalized_rows})
        placeholders = ",".join("?" for _ in delete_types)
        before = db.total_changes
        db.execute(
            f"DELETE FROM activities WHERE para_id = ? AND activity_type IN ({placeholders})",
            (para_id, *delete_types),
        )
        deleted += db.total_changes - before

        for activity_type, payload in normalized_rows:
            before = db.total_changes
            db.execute(
                """
                INSERT INTO activities
                    (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    paragraph["id"],
                    para_id,
                    activity_type,
                    json.dumps(payload),
                    int(payload.get("difficulty", 1)),
                    payload.get("generation_source", "curated"),
                ),
            )
            inserted += db.total_changes - before

        synced_paragraphs += 1

    return synced_paragraphs, deleted, inserted


def sync_item_type_curated_activities(db: sqlite3.Connection) -> tuple[int, int, int]:
    """Sync only explicitly named activity types from merged curated overrides."""
    overrides = load_curated_overrides().get("activities", {})
    paragraph_rows = {
        row["para_id"]: row
        for row in db.execute(
            "SELECT id, para_id, title FROM paragraphs ORDER BY chapter, section, para_id"
        ).fetchall()
    }

    synced_paragraphs = 0
    deleted = 0
    inserted = 0

    for para_id, override in overrides.items():
        if (
            not isinstance(override, dict)
            or override.get("replace_all")
            or override.get("sync_replace_types")
        ):
            continue

        sync_types = {
            str(activity_type).strip()
            for activity_type in override.get("sync_item_types_only", [])
            if str(activity_type).strip()
        }
        if not sync_types:
            continue

        paragraph = paragraph_rows.get(para_id)
        if paragraph is None:
            raise ValueError(f"Missing paragraph for curated item-type override: {para_id}")

        normalized_rows: list[tuple[str, dict]] = []
        for item in override.get("items", []):
            if not isinstance(item, dict):
                continue
            activity_type = item.get("activity_type")
            if activity_type not in sync_types:
                continue
            payload = dict(item)
            payload.pop("activity_type", None)
            normalized = normalize_activity_payload(
                activity_type,
                payload,
                paragraph["title"],
                para_id,
            )
            errors = validate_activity_payload(activity_type, normalized, paragraph["title"])
            if errors:
                joined = "; ".join(errors)
                raise ValueError(
                    f"Invalid curated item-type activity for {para_id}/{activity_type}: {joined}"
                )
            normalized_rows.append((activity_type, normalized))

        if not normalized_rows:
            continue

        delete_types = sorted({activity_type for activity_type, _ in normalized_rows})
        placeholders = ",".join("?" for _ in delete_types)
        before = db.total_changes
        db.execute(
            f"DELETE FROM activities WHERE para_id = ? AND activity_type IN ({placeholders})",
            (para_id, *delete_types),
        )
        deleted += db.total_changes - before

        for activity_type, payload in normalized_rows:
            before = db.total_changes
            db.execute(
                """
                INSERT INTO activities
                    (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    paragraph["id"],
                    para_id,
                    activity_type,
                    json.dumps(payload),
                    int(payload.get("difficulty", 1)),
                    payload.get("generation_source", "curated"),
                ),
            )
            inserted += db.total_changes - before

        synced_paragraphs += 1

    return synced_paragraphs, deleted, inserted


def sync_activity_generation_sources(db: sqlite3.Connection) -> tuple[int, int]:
    updated = 0
    deleted = 0

    rows = db.execute(
        """
        SELECT id, para_id, activity_type, generation_src, content_json
        FROM activities
        ORDER BY para_id, activity_type, id
        """
    ).fetchall()

    for row in rows:
        payload = json.loads(row["content_json"])
        payload_src = str(payload.get("generation_source", "")).strip()
        if not payload_src or payload_src == row["generation_src"]:
            continue

        conflict = db.execute(
            """
            SELECT 1
            FROM activities
            WHERE para_id = ? AND activity_type = ? AND generation_src = ? AND id != ?
            """,
            (row["para_id"], row["activity_type"], payload_src, row["id"]),
        ).fetchone()
        if conflict:
            before = db.total_changes
            db.execute("DELETE FROM activities WHERE id = ?", (row["id"],))
            if db.total_changes > before:
                deleted += 1
            continue

        before = db.total_changes
        db.execute(
            "UPDATE activities SET generation_src = ? WHERE id = ?",
            (payload_src, row["id"]),
        )
        if db.total_changes > before:
            updated += 1

    return updated, deleted


def _statement_instruction(title: str) -> str:
    return "Is this statement operationally correct?"


def _contextualize_statement(title: str, question_text: str) -> str:
    title = " ".join(str(title or "").split())
    question_text = " ".join(str(question_text or "").split())
    if not title or not question_text or re.match(r"^This order\b", question_text, re.IGNORECASE):
        return question_text
    match = re.match(r"^(This|These|That|Those)\s+(.+)$", question_text)
    if not match:
        return question_text

    body = match.group(2)
    lower_body = body.lower()
    lower_title = title.lower()

    if lower_title in lower_body:
        return f"{body[:1].upper()}{body[1:]}"

    head_match = re.match(r"^([A-Za-z][A-Za-z/-]*)(?:\s+|$)", body)
    head = head_match.group(1).lower() if head_match else ""
    if head and head in lower_title.split():
        remainder = body[len(head_match.group(1)):].lstrip()
        base = lower_title
        return f"{base[:1].upper()}{base[1:]}{' ' + remainder if remainder else ''}"

    if head in {
        "information",
        "procedure",
        "authorization",
        "method",
        "separation",
        "equipment",
        "action",
        "rule",
        "instruction",
        "concurrence",
        "items",
        "distances",
        "flights",
        "service",
        "responsibility",
    }:
        remainder = body[len(head_match.group(1)):].lstrip() if head_match else body
        if head in lower_title.split() or any(token == head.rstrip("s") for token in lower_title.split()):
            base = lower_title
            return f"{base[:1].upper()}{base[1:]}{' ' + remainder if remainder else ''}"
        return f"For {lower_title}, the {body[:1].lower()}{body[1:]}"

    return f"For {lower_title}, the {body[:1].lower()}{body[1:]}"


def refresh_statement_wording(db: sqlite3.Connection) -> tuple[int, int]:
    rows = db.execute(
        """
        SELECT a.id, a.para_id, a.activity_type, a.content_json, p.title
        FROM activities a
        JOIN paragraphs p ON p.id = a.paragraph_db_id
        ORDER BY a.para_id, a.activity_type, a.id
        """,
    ).fetchall()

    updated_activities = 0
    contextualized_questions = 0

    for row in rows:
        payload = json.loads(row["content_json"])
        normalized = normalize_activity_payload(
            row["activity_type"],
            payload,
            row["title"],
            row["para_id"],
        )
        if normalized == payload:
            continue
        if normalized.get("question_text") != payload.get("question_text"):
            contextualized_questions += 1

        before = db.total_changes
        db.execute(
            "UPDATE activities SET content_json = ? WHERE id = ?",
            (json.dumps(normalized), row["id"]),
        )
        if db.total_changes > before:
            updated_activities += 1

    return updated_activities, contextualized_questions


def refresh_situation_action_choices(db: sqlite3.Connection) -> tuple[int, int]:
    rows = db.execute(
        """
        SELECT a.id, a.para_id, a.content_json, p.title
        FROM activities a
        JOIN paragraphs p ON p.id = a.paragraph_db_id
        WHERE a.activity_type = 'situation_action'
          AND a.generation_src = 'local_auto'
        ORDER BY a.para_id, a.id
        """
    ).fetchall()

    targeted = 0
    updated = 0

    for row in rows:
        payload = json.loads(row["content_json"])
        choices = payload.get("choices", [])
        generic_count = sum(
            1
            for choice in choices
            if not choice.get("is_correct") and is_generic_action_distractor(choice.get("text", ""))
        )
        if generic_count <= 1:
            continue

        correct_choices = [choice for choice in choices if choice.get("is_correct")]
        if len(correct_choices) != 1:
            continue

        targeted += 1
        refreshed = dict(payload)
        refreshed["choices"] = build_action_choices(
            correct_choices[0].get("text", ""),
            f"{row['para_id']}:repair:situation:{row['id']}",
            refreshed.get("situation", ""),
        )
        refreshed = normalize_activity_payload("situation_action", refreshed, row["title"], row["para_id"])
        if validate_activity_payload("situation_action", refreshed, row["title"]):
            continue

        before = db.total_changes
        db.execute(
            "UPDATE activities SET content_json = ?, difficulty = ? WHERE id = ?",
            (json.dumps(refreshed), int(refreshed.get("difficulty", 1)), row["id"]),
        )
        if db.total_changes > before:
            updated += 1

    return targeted, updated


def refresh_quiz_question_wording(db: sqlite3.Connection) -> int:
    rows = db.execute(
        """
        SELECT id, question_type, question_text
        FROM quiz_questions
        ORDER BY para_id, question_type, id
        """
    ).fetchall()

    updated = 0
    for row in rows:
        normalized = normalize_question_text(row["question_type"], row["question_text"])
        if normalized == row["question_text"]:
            continue
        before = db.total_changes
        db.execute(
            "UPDATE quiz_questions SET question_text = ? WHERE id = ?",
            (normalized, row["id"]),
        )
        if db.total_changes > before:
            updated += 1

    return updated


def refresh_quiz_choice_wording(db: sqlite3.Connection) -> int:
    rows = db.execute(
        """
        SELECT id, choice_text
        FROM question_choices
        ORDER BY question_id, sort_order, id
        """
    ).fetchall()

    updated = 0
    for row in rows:
        normalized = normalize_choice_text(row["choice_text"])
        if normalized == row["choice_text"]:
            continue
        before = db.total_changes
        db.execute(
            "UPDATE question_choices SET choice_text = ? WHERE id = ?",
            (normalized, row["id"]),
        )
        if db.total_changes > before:
            updated += 1

    return updated


def _db_question_quality_errors(
    question_type: str,
    question_text: str,
    explanation: str,
    choice_rows: list[sqlite3.Row],
    generation_src: str,
) -> list[str]:
    errors = question_text_errors(question_type, question_text)
    for choice_row in choice_rows:
        errors.extend(choice_text_errors(choice_row["choice_text"]))

    if generation_src == "local_auto":
        question = GeneratedQuestion(
            question_text=question_text,
            question_type=question_type,
            choices=[
                GeneratedChoice(text=choice_row["choice_text"], is_correct=False)
                for choice_row in choice_rows
            ],
            explanation=explanation,
            difficulty=1,
            source_block="body",
            generation_source="local_auto",
        )
        errors.extend(local_auto_question_quality_errors(question))

    return errors


def repair_invalid_local_auto_questions(
    db: sqlite3.Connection,
) -> tuple[int, int, int, list[tuple[str, str]]]:
    rows = db.execute(
        """
        SELECT
            q.id,
            q.para_id,
            q.question_type,
            q.question_text,
            q.explanation,
            p.id AS paragraph_db_id,
            p.title,
            p.content_json
        FROM quiz_questions q
        JOIN paragraphs p ON p.id = q.paragraph_db_id
        WHERE q.generation_src = 'local_auto'
        ORDER BY q.para_id, q.question_type, q.id
        """
    ).fetchall()

    targets: dict[str, sqlite3.Row] = {}
    issues_by_para: dict[str, set[str]] = {}
    paragraph_rows_by_para: dict[str, sqlite3.Row] = {}
    existing_fill_blank_by_para: dict[str, set[tuple[str, str]]] = {}
    for row in rows:
        paragraph_rows_by_para.setdefault(row["para_id"], row)
        if row["question_type"] == "fill_blank":
            existing_fill_blank_by_para.setdefault(row["para_id"], set()).add(
                (row["question_text"], row["explanation"] or "")
            )
        choice_rows = db.execute(
            """
            SELECT choice_text
            FROM question_choices
            WHERE question_id = ?
            ORDER BY sort_order, id
            """,
            (row["id"],),
        ).fetchall()
        errors = _db_question_quality_errors(
            row["question_type"],
            row["question_text"],
            row["explanation"] or "",
            choice_rows,
            "local_auto",
        )
        if not errors:
            continue
        targets[row["para_id"]] = row
        issues_by_para.setdefault(row["para_id"], set()).update(errors)

    if existing_fill_blank_by_para:
        fill_blank_paragraph_rows = [
            {
                "id": row["paragraph_db_id"],
                "para_id": row["para_id"],
                "title": row["title"],
                "content_json": row["content_json"],
            }
            for row in paragraph_rows_by_para.values()
            if row["para_id"] in existing_fill_blank_by_para
        ]
        generated_fill_blank_rows = asyncio.run(
            _generate_missing_question_rows(fill_blank_paragraph_rows)  # type: ignore[arg-type]
        )
        generated_fill_blank_by_para = {
            para_id: {
                (question.question_text, question.explanation)
                for question in questions
                if getattr(question, "generation_source", "local_auto") == "local_auto"
                and question.question_type == "fill_blank"
                and not validate_generated_question(question)
                and not local_auto_question_quality_errors(question)
            }
            for _, para_id, questions in generated_fill_blank_rows
        }
        for para_id, existing_fill_blank in existing_fill_blank_by_para.items():
            if generated_fill_blank_by_para.get(para_id, set()) == existing_fill_blank:
                continue
            row = paragraph_rows_by_para.get(para_id)
            if row is None:
                continue
            targets[para_id] = row
            issues_by_para.setdefault(para_id, set()).add(
                "fill-blank output is stale relative to current generator"
            )

    if not targets:
        return 0, 0, 0, []

    paragraph_rows = [
        {
            "id": row["paragraph_db_id"],
            "para_id": row["para_id"],
            "title": row["title"],
            "content_json": row["content_json"],
        }
        for row in targets.values()
    ]
    generated_rows = asyncio.run(
        _generate_missing_question_rows(paragraph_rows)  # type: ignore[arg-type]
    )
    generated_by_para = {
        para_id: [
            question
            for question in questions
            if getattr(question, "generation_source", "local_auto") == "local_auto"
            and not validate_generated_question(question)
            and not local_auto_question_quality_errors(question)
        ]
        for _, para_id, questions in generated_rows
    }

    deleted = 0
    inserted = 0
    unresolved: list[tuple[str, str]] = []

    for para_id, row in targets.items():
        question_ids = [
            existing["id"]
            for existing in db.execute(
                """
                SELECT id FROM quiz_questions
                WHERE para_id = ? AND generation_src = 'local_auto'
                ORDER BY id
                """,
                (para_id,),
            ).fetchall()
        ]
        for question_id in question_ids:
            db.execute("DELETE FROM question_choices WHERE question_id = ?", (question_id,))
            before = db.total_changes
            db.execute("DELETE FROM quiz_questions WHERE id = ?", (question_id,))
            if db.total_changes > before:
                deleted += 1

        replacements = generated_by_para.get(para_id, [])
        if not replacements:
            unresolved.append((para_id, ", ".join(sorted(issues_by_para.get(para_id, {"no replacement generated"})))))
            continue

        for question in replacements:
            question_id = str(uuid.uuid4())
            before = db.total_changes
            db.execute(
                """
                INSERT INTO quiz_questions
                    (id, paragraph_db_id, para_id, question_text, question_type,
                     explanation, difficulty, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    row["paragraph_db_id"],
                    para_id,
                    question.question_text,
                    question.question_type,
                    question.explanation,
                    int(question.difficulty),
                    getattr(question, "generation_source", "local_auto"),
                ),
            )
            if db.total_changes > before:
                inserted += 1

            for sort_order, choice in enumerate(question.choices):
                db.execute(
                    """
                    INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        question_id,
                        choice.text,
                        int(choice.is_correct),
                        sort_order,
                    ),
                )

    return len(targets), deleted, inserted, unresolved


def delete_remaining_invalid_questions(
    db: sqlite3.Connection,
) -> tuple[int, list[tuple[str, str]]]:
    rows = db.execute(
        """
        SELECT id, para_id, question_type, question_text, explanation, generation_src
        FROM quiz_questions
        ORDER BY para_id, question_type, id
        """
    ).fetchall()

    deleted = 0
    removed: list[tuple[str, str]] = []
    for row in rows:
        if row["generation_src"] != "local_auto":
            continue
        choice_rows = db.execute(
            """
            SELECT choice_text
            FROM question_choices
            WHERE question_id = ?
            ORDER BY sort_order, id
            """,
            (row["id"],),
        ).fetchall()
        errors = _db_question_quality_errors(
            row["question_type"],
            row["question_text"],
            row["explanation"] or "",
            choice_rows,
            row["generation_src"],
        )
        if not errors:
            continue
        db.execute("DELETE FROM question_choices WHERE question_id = ?", (row["id"],))
        before = db.total_changes
        db.execute("DELETE FROM quiz_questions WHERE id = ?", (row["id"],))
        if db.total_changes > before:
            deleted += 1
            removed.append((row["para_id"], f"{row['generation_src']}: {', '.join(errors)}"))

    return deleted, removed


def repair_invalid_spot_the_error_activities(
    db: sqlite3.Connection,
) -> tuple[int, int, int, list[tuple[str, str]]]:
    return repair_invalid_activity_type(db, "spot_the_error")


def repair_invalid_activity_type(
    db: sqlite3.Connection,
    activity_type: str,
) -> tuple[int, int, int, list[tuple[str, str]]]:
    rows = db.execute(
        """
        SELECT
            a.id,
            a.para_id,
            a.content_json,
            a.generation_src,
            p.title,
            p.content_json AS paragraph_content_json
        FROM activities a
        JOIN paragraphs p ON p.id = a.paragraph_db_id
        WHERE a.activity_type = ?
        ORDER BY a.para_id, a.id
        """
        ,
        (activity_type,),
    ).fetchall()

    invalid_rows: list[sqlite3.Row] = []
    invalid_ids: set[str] = set()
    for row in rows:
        payload = json.loads(row["content_json"])
        errors = validate_activity_payload(activity_type, payload, row["title"])
        errors.extend(_local_auto_quality_errors(activity_type, payload, row["generation_src"]))
        if errors:
            invalid_rows.append(row)
            invalid_ids.add(row["id"])

    if activity_type == "example_check":
        local_auto_rows = [row for row in rows if row["generation_src"] == "local_auto"]
        generated_rows, unresolved_rows = asyncio.run(
            _generate_replacement_activity_rows(local_auto_rows, activity_type)
        )
        generated_by_id = {
            activity_id: activity
            for activity_id, _generation_src, activity in generated_rows
        }
        unresolved_by_id = {
            activity_id: errors
            for activity_id, _para_id, errors in unresolved_rows
        }
        for row in local_auto_rows:
            if row["id"] in invalid_ids:
                continue
            current_payload = json.loads(row["content_json"])
            generated_payload = generated_by_id.get(row["id"])
            if row["id"] in unresolved_by_id:
                invalid_rows.append(row)
                invalid_ids.add(row["id"])
                continue
            if not generated_payload:
                continue
            if json.dumps(current_payload, sort_keys=True) != json.dumps(generated_payload, sort_keys=True):
                invalid_rows.append(row)
                invalid_ids.add(row["id"])

    if not invalid_rows:
        return 0, 0, 0, []

    replacements, unresolved_rows = asyncio.run(
        _generate_replacement_activity_rows(invalid_rows, activity_type)
    )

    updated = 0
    for activity_id, generation_src, activity in replacements:
        before = db.total_changes
        db.execute(
            """
            UPDATE activities
            SET content_json = ?, difficulty = ?, generation_src = ?
            WHERE id = ?
            """,
            (
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                generation_src,
                activity_id,
            ),
        )
        if db.total_changes > before:
            updated += 1

    deleted = 0
    unresolved: list[tuple[str, str]] = []
    for activity_id, para_id, errors in unresolved_rows:
        before = db.total_changes
        db.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        if db.total_changes > before:
            deleted += 1
        unresolved.append((para_id, ", ".join(errors)))

    return len(invalid_rows), updated, deleted, unresolved


async def _generate_activity_rows(
    rows: list[sqlite3.Row],
    activity_type: str,
) -> list[tuple[str, str, dict]]:
    generated_rows: list[tuple[str, str, dict]] = []

    for row in rows:
        generated = await generate_activities_for_paragraph(
            para_id=row["para_id"],
            para_title=row["title"],
            blocks=json.loads(row["content_json"]),
            types=[activity_type],
        )
        items = generated.get(activity_type, [])
        if items:
            candidate = items[0]
            generation_src = candidate.get("generation_source", "local_auto")
            if _local_auto_quality_errors(activity_type, candidate, generation_src):
                continue
            generated_rows.append((row["id"], row["para_id"], candidate))

    return generated_rows


async def _generate_replacement_activity_rows(
    rows: list[sqlite3.Row],
    activity_type: str,
) -> tuple[list[tuple[str, str, dict]], list[tuple[str, str, list[str]]]]:
    replacements: list[tuple[str, str, dict]] = []
    unresolved: list[tuple[str, str, list[str]]] = []

    for row in rows:
        generated = await generate_activities_for_paragraph(
            para_id=row["para_id"],
            para_title=row["title"],
            blocks=json.loads(row["paragraph_content_json"]),
            types=[activity_type],
        )
        items = generated.get(activity_type, [])
        if not items:
            unresolved.append((row["id"], row["para_id"], ["no replacement generated"]))
            continue

        replacement = items[0]
        errors = validate_activity_payload(activity_type, replacement, row["title"])
        generation_src = replacement.get("generation_source", row["generation_src"])
        errors.extend(_local_auto_quality_errors(activity_type, replacement, generation_src))
        if errors:
            unresolved.append((row["id"], row["para_id"], errors))
            continue

        replacements.append((row["id"], generation_src, replacement))

    return replacements, unresolved


async def _generate_missing_question_rows(rows: list[sqlite3.Row]) -> list[tuple[str, str, list]]:
    generated_rows: list[tuple[str, str, list]] = []

    for row in rows:
        questions = await generate_questions_for_paragraph(
            para_id=row["para_id"],
            para_title=row["title"],
            blocks=json.loads(row["content_json"]),
        )
        if questions:
            generated_rows.append((row["id"], row["para_id"], questions))

    return generated_rows


def _has_curated_activity_type(para_id: str, activity_type: str) -> bool:
    override = get_curated_activity_override(para_id)
    if not override:
        return False
    if activity_type in override.get("replace_types", []):
        return True
    return any(
        item.get("activity_type") == activity_type
        for item in override.get("items", [])
    )


def backfill_activity_type(
    db: sqlite3.Connection,
    activity_type: str,
    target_sql: str,
) -> tuple[int, int]:
    target_rows = db.execute(target_sql).fetchall()
    generated_rows = asyncio.run(_generate_activity_rows(target_rows, activity_type))
    inserted = 0

    for paragraph_id, para_id, activity in generated_rows:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO activities
                (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                paragraph_id,
                para_id,
                activity_type,
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                activity.get("generation_source", "local_auto"),
            ),
        )
        if db.total_changes > before:
            inserted += 1

    return len(target_rows), inserted


def backfill_directive_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "directive_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'directive_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_situation_action_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "situation_action",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'situation_action'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_phraseology_builder_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "phraseology_builder",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE (
              p.content_json LIKE '%"block_type": "phraseology"%'
           OR p.content_json LIKE '%"block_type": "example"%'
        )
          AND NOT EXISTS (
              SELECT 1 FROM activities a
              WHERE a.para_id = p.para_id AND a.activity_type = 'phraseology_builder'
          )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_sequence_steps_activities(db: sqlite3.Connection) -> tuple[int, int]:
    rows = db.execute(
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        ORDER BY p.chapter, p.section, p.para_id
        """
    ).fetchall()
    target_rows = [
        row
        for row in rows
        if _has_curated_activity_type(row["para_id"], "sequence_steps")
        and not db.execute(
            "SELECT 1 FROM activities WHERE para_id = ? AND activity_type = 'sequence_steps'",
            (row["para_id"],),
        ).fetchone()
    ]
    generated_rows = asyncio.run(_generate_activity_rows(target_rows, "sequence_steps"))
    inserted = 0

    for paragraph_id, para_id, activity in generated_rows:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO activities
                (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                paragraph_id,
                para_id,
                "sequence_steps",
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                activity.get("generation_source", "local_auto"),
            ),
        )
        if db.total_changes > before:
            inserted += 1

    return len(target_rows), inserted


def backfill_conditional_rule_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "conditional_rule_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'conditional_rule_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_term_definition_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "term_definition_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'term_definition_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_document_control_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "document_control_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'document_control_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_requirement_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "requirement_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'requirement_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_scope_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "scope_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'scope_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_capability_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "capability_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'capability_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_reference_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    if "reference_check" in DEPRECATED_ACTIVITY_TYPES:
        return 0, 0

    rows = db.execute(
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        ORDER BY p.chapter, p.section, p.para_id
        """
    ).fetchall()
    target_rows = [
        row
        for row in rows
        if (
            "Order JO" in row["content_json"]
            or _has_curated_activity_type(row["para_id"], "reference_check")
        )
        and not db.execute(
            "SELECT 1 FROM activities WHERE para_id = ? AND activity_type = 'reference_check'",
            (row["para_id"],),
        ).fetchone()
    ]
    generated_rows = asyncio.run(_generate_activity_rows(target_rows, "reference_check"))
    inserted = 0

    for paragraph_id, para_id, activity in generated_rows:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO activities
                (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                paragraph_id,
                para_id,
                "reference_check",
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                activity.get("generation_source", "local_auto"),
            ),
        )
        if db.total_changes > before:
            inserted += 1

    return len(target_rows), inserted


def backfill_minima_rule_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "minima_rule_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        WHERE NOT EXISTS (
            SELECT 1 FROM activities a
            WHERE a.para_id = p.para_id AND a.activity_type = 'minima_rule_check'
        )
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def backfill_list_membership_activities(db: sqlite3.Connection) -> tuple[int, int]:
    rows = db.execute(
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        ORDER BY p.chapter, p.section, p.para_id
        """
    ).fetchall()
    target_rows = [
        row
        for row in rows
        if _has_curated_activity_type(row["para_id"], "list_membership")
        and not db.execute(
            "SELECT 1 FROM activities WHERE para_id = ? AND activity_type = 'list_membership'",
            (row["para_id"],),
        ).fetchone()
    ]
    generated_rows = asyncio.run(_generate_activity_rows(target_rows, "list_membership"))
    inserted = 0

    for paragraph_id, para_id, activity in generated_rows:
        if activity.get("generation_source", "local_auto") != "curated":
            continue
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO activities
                (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                paragraph_id,
                para_id,
                "list_membership",
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                activity.get("generation_source", "local_auto"),
            ),
        )
        if db.total_changes > before:
            inserted += 1

    return len(target_rows), inserted


def backfill_table_lookup_activities(db: sqlite3.Connection) -> tuple[int, int]:
    rows = db.execute(
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        ORDER BY p.chapter, p.section, p.para_id
        """
    ).fetchall()
    target_rows = [
        row
        for row in rows
        if (
            "TBL" in row["content_json"]
            or _has_curated_activity_type(row["para_id"], "table_lookup")
        )
        and not db.execute(
            "SELECT 1 FROM activities WHERE para_id = ? AND activity_type = 'table_lookup'",
            (row["para_id"],),
        ).fetchone()
    ]
    generated_rows = asyncio.run(_generate_activity_rows(target_rows, "table_lookup"))
    inserted = 0

    for paragraph_id, para_id, activity in generated_rows:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO activities
                (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                paragraph_id,
                para_id,
                "table_lookup",
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                activity.get("generation_source", "local_auto"),
            ),
        )
        if db.total_changes > before:
            inserted += 1

    return len(target_rows), inserted


def backfill_example_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    rows = db.execute(
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        ORDER BY p.chapter, p.section, p.para_id
        """
    ).fetchall()
    target_rows = [
        row
        for row in rows
        if (
            '"' in row["content_json"]
            or _has_curated_activity_type(row["para_id"], "example_check")
        )
        and not db.execute(
            "SELECT 1 FROM activities WHERE para_id = ? AND activity_type = 'example_check'",
            (row["para_id"],),
        ).fetchone()
    ]
    generated_rows = asyncio.run(_generate_activity_rows(target_rows, "example_check"))
    inserted = 0

    for paragraph_id, para_id, activity in generated_rows:
        before = db.total_changes
        db.execute(
            """
            INSERT OR IGNORE INTO activities
                (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                paragraph_id,
                para_id,
                "example_check",
                json.dumps(activity),
                int(activity.get("difficulty", 1)),
                activity.get("generation_source", "local_auto"),
            ),
        )
        if db.total_changes > before:
            inserted += 1

    return len(target_rows), inserted


def backfill_knowledge_check_activities(db: sqlite3.Connection) -> tuple[int, int]:
    return backfill_activity_type(
        db,
        "knowledge_check",
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        LEFT JOIN activities a ON a.para_id = p.para_id
        GROUP BY p.id, p.para_id, p.title, p.content_json
        HAVING COUNT(DISTINCT a.activity_type) < 2
        ORDER BY p.chapter, p.section, p.para_id
        """,
    )


def flashcard_generation_source(item: dict, override: dict) -> str:
    return (
        normalise_ws(
            item.get("generation_source")
            or item.get("generation_src")
            or override.get("generation_source")
            or override.get("generation_src")
            or "curated"
        )
        or "curated"
    )


def managed_flashcard_generation_sources() -> set[str]:
    sources = {"curated"}
    for override in load_curated_flashcard_overrides().values():
        for item in override.get("items", []):
            sources.add(flashcard_generation_source(item, override))
    return sources


def delete_unmanaged_flashcards(db: sqlite3.Connection) -> int:
    managed_sources = sorted(managed_flashcard_generation_sources())
    placeholders = ",".join("?" for _ in managed_sources)
    before = db.total_changes
    db.execute(
        f"DELETE FROM flashcards WHERE generation_src NOT IN ({placeholders})",
        managed_sources,
    )
    return db.total_changes - before


def sync_curated_flashcards(db: sqlite3.Connection) -> tuple[int, int, int]:
    overrides = load_curated_flashcard_overrides()
    synced = 0
    deleted = 0
    inserted = 0

    for para_id, override in overrides.items():
        paragraph_row = db.execute(
            "SELECT id FROM paragraphs WHERE para_id = ?",
            (para_id,),
        ).fetchone()
        if paragraph_row is None:
            continue

        paragraph_db_id = paragraph_row["id"]
        synced += 1

        before_delete = db.total_changes
        db.execute("DELETE FROM flashcards WHERE para_id = ?", (para_id,))
        deleted += db.total_changes - before_delete

        for item in override.get("items", []):
            before_insert = db.total_changes
            db.execute(
                """
                INSERT INTO flashcards
                    (id, paragraph_db_id, para_id, front, back, card_type, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    paragraph_db_id,
                    para_id,
                    normalise_ws(item["front"]),
                    normalise_ws(item["back"]),
                    normalise_ws(item.get("card_type", "definition")) or "definition",
                    flashcard_generation_source(item, override),
                ),
            )
            inserted += db.total_changes - before_insert

    return synced, deleted, inserted


def sync_curated_questions(db: sqlite3.Connection) -> tuple[int, int, int]:
    overrides = load_curated_overrides().get("questions", {})
    synced = 0
    deleted = 0
    inserted = 0

    for para_id, override in overrides.items():
        if not isinstance(override, dict):
            continue

        items = override.get("items", [])
        replace_all = bool(override.get("replace_all"))
        target_types = set(override.get("replace_types", []))
        for item in items:
            if isinstance(item, dict) and item.get("question_type"):
                target_types.add(item["question_type"])

        if not replace_all and not target_types:
            continue

        paragraph = db.execute(
            "SELECT id FROM paragraphs WHERE para_id = ?",
            (para_id,),
        ).fetchone()
        if paragraph is None:
            raise ValueError(f"Missing paragraph for curated question override: {para_id}")

        if replace_all:
            question_rows = db.execute(
                "SELECT id FROM quiz_questions WHERE para_id = ? ORDER BY id",
                (para_id,),
            ).fetchall()
        else:
            placeholders = ", ".join("?" for _ in target_types)
            question_rows = db.execute(
                f"""
                SELECT id FROM quiz_questions
                WHERE para_id = ? AND question_type IN ({placeholders})
                ORDER BY id
                """,
                (para_id, *sorted(target_types)),
            ).fetchall()

        if not question_rows and not items:
            continue

        synced += 1

        for row in question_rows:
            db.execute("DELETE FROM question_choices WHERE question_id = ?", (row["id"],))
            before_delete = db.total_changes
            db.execute("DELETE FROM quiz_questions WHERE id = ?", (row["id"],))
            deleted += db.total_changes - before_delete

        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Curated question for {para_id} must be an object")

            question_text = normalise_ws(item.get("question_text", ""))
            question_type = normalise_ws(item.get("question_type", ""))
            explanation = normalise_ws(item.get("explanation", ""))
            generation_source = normalise_ws(item.get("generation_source", "curated")) or "curated"
            difficulty = int(item.get("difficulty", 2))
            choices = item.get("choices", [])
            if question_type == "true_false" and not choices and "correct_answer" in item:
                correct_answer = bool(item.get("correct_answer"))
                choices = [
                    {"text": "True", "is_correct": correct_answer},
                    {"text": "False", "is_correct": not correct_answer},
                ]

            if not question_text or not question_type:
                raise ValueError(f"Curated question for {para_id} is missing question_text/question_type")

            if question_type in {"multiple_choice", "true_false"} and not choices:
                raise ValueError(f"Curated {question_type} question for {para_id} requires choices")
            if question_type == "fill_blank" and not choices:
                raise ValueError(f"Curated fill_blank question for {para_id} requires at least one accepted answer")

            question_id = str(uuid.uuid4())
            before_insert = db.total_changes
            db.execute(
                """
                INSERT INTO quiz_questions
                    (id, paragraph_db_id, para_id, question_text, question_type,
                     explanation, difficulty, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    paragraph["id"],
                    para_id,
                    question_text,
                    question_type,
                    explanation,
                    difficulty,
                    generation_source,
                ),
            )
            inserted += db.total_changes - before_insert

            for sort_order, choice in enumerate(choices):
                if not isinstance(choice, dict):
                    raise ValueError(f"Curated choice for {para_id} must be an object")
                db.execute(
                    """
                    INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        question_id,
                        normalise_ws(choice["text"]),
                        int(bool(choice.get("is_correct"))),
                        sort_order,
                    ),
                )

    return synced, deleted, inserted


def backfill_missing_questions(db: sqlite3.Connection) -> tuple[int, int]:
    target_rows = db.execute(
        """
        SELECT p.id, p.para_id, p.title, p.content_json
        FROM paragraphs p
        LEFT JOIN quiz_questions q ON q.para_id = p.para_id
        WHERE q.id IS NULL
        ORDER BY p.chapter, p.section, p.para_id
        """
    ).fetchall()

    generated_rows = asyncio.run(_generate_missing_question_rows(target_rows))
    inserted = 0

    for paragraph_id, para_id, questions in generated_rows:
        for question in questions:
            if not question.choices:
                continue

            question_id = str(uuid.uuid4())
            before = db.total_changes
            db.execute(
                """
                INSERT INTO quiz_questions
                    (id, paragraph_db_id, para_id, question_text, question_type,
                     explanation, difficulty, generation_src)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    paragraph_id,
                    para_id,
                    question.question_text,
                    question.question_type,
                    question.explanation,
                    int(question.difficulty),
                    getattr(question, "generation_source", "local_auto"),
                ),
            )
            if db.total_changes > before:
                inserted += 1

            for sort_order, choice in enumerate(question.choices):
                db.execute(
                    """
                    INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        question_id,
                        choice.text,
                        int(choice.is_correct),
                        sort_order,
                    ),
                )

    return len(target_rows), inserted


def count_query(db: sqlite3.Connection, sql: str) -> int:
    return int(db.execute(sql).fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair curriculum.db in-place")
    parser.add_argument(
        "--db",
        default="curriculum.db",
        help="Path to the SQLite curriculum database",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    backup_path = ensure_backup(db_path)
    answer_map = load_true_false_answer_map()

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        replace_all_paragraphs, replace_all_deleted, replace_all_inserted = sync_replace_all_curated_activities(db)
        replace_type_paragraphs, replace_type_deleted, replace_type_inserted = sync_replace_type_curated_activities(db)
        item_type_paragraphs, item_type_deleted, item_type_inserted = sync_item_type_curated_activities(db)
        synced_activity_sources, removed_shadowed_activities = sync_activity_generation_sources(db)
        refreshed_statement_activities, contextualized_questions = refresh_statement_wording(db)
        situation_choice_targets, situation_choices_refreshed = refresh_situation_action_choices(db)
        repaired_true_false, unresolved = repair_missing_true_false_choices(db, answer_map)
        deprecated_activities_deleted = delete_deprecated_activities(db)
        non_curated_phraseology_deleted = delete_non_curated_phraseology_builders(db)
        refreshed_quiz_questions = refresh_quiz_question_wording(db)
        refreshed_quiz_choices = refresh_quiz_choice_wording(db)
        (
            invalid_question_paragraphs,
            invalid_questions_deleted,
            invalid_questions_inserted,
            unresolved_questions,
        ) = repair_invalid_local_auto_questions(db)
        deleted_invalid_questions, removed_invalid_questions = delete_remaining_invalid_questions(db)
        duplicate_groups, removed_questions = delete_duplicate_local_auto_questions(db)
        (
            invalid_phraseology_targets,
            invalid_phraseology_repaired,
            invalid_phraseology_deleted,
            unresolved_phraseology,
        ) = repair_invalid_activity_type(db, "phraseology_builder")
        (
            invalid_spot_targets,
            invalid_spot_repaired,
            invalid_spot_deleted,
            unresolved_spot,
        ) = repair_invalid_spot_the_error_activities(db)
        quality_repairs = {
            activity_type: repair_invalid_activity_type(db, activity_type)
            for activity_type in (
                "situation_action",
                "directive_check",
                "document_control_check",
                "requirement_check",
                "scope_check",
                "capability_check",
                "conditional_rule_check",
                "term_definition_check",
                "minima_rule_check",
                "example_check",
                "list_membership",
                "knowledge_check",
            )
        }
        phraseology_targets, phraseology_inserted = backfill_phraseology_builder_activities(db)
        sequence_targets, sequence_inserted = backfill_sequence_steps_activities(db)
        situation_targets, situation_inserted = backfill_situation_action_activities(db)
        directive_targets, directive_inserted = backfill_directive_check_activities(db)
        conditional_targets, conditional_inserted = backfill_conditional_rule_check_activities(db)
        definition_targets, definition_inserted = backfill_term_definition_check_activities(db)
        document_targets, document_inserted = backfill_document_control_check_activities(db)
        requirement_targets, requirement_inserted = backfill_requirement_check_activities(db)
        scope_targets, scope_inserted = backfill_scope_check_activities(db)
        capability_targets, capability_inserted = backfill_capability_check_activities(db)
        reference_targets, reference_inserted = backfill_reference_check_activities(db)
        minima_targets, minima_inserted = backfill_minima_rule_check_activities(db)
        list_targets, list_inserted = backfill_list_membership_activities(db)
        table_targets, table_inserted = backfill_table_lookup_activities(db)
        example_targets, example_inserted = backfill_example_check_activities(db)
        knowledge_targets, knowledge_inserted = backfill_knowledge_check_activities(db)
        unmanaged_flashcards_deleted = delete_unmanaged_flashcards(db)
        flashcard_targets, flashcards_deleted, flashcards_inserted = sync_curated_flashcards(db)
        question_targets, questions_inserted = backfill_missing_questions(db)
        curated_question_targets, curated_questions_deleted, curated_questions_inserted = sync_curated_questions(db)
        db.commit()
        unresolved_questions = [
            (para_id, message)
            for para_id, message in unresolved_questions
            if db.execute(
                """
                SELECT 1
                FROM quiz_questions
                WHERE para_id = ? AND generation_src = 'local_auto'
                LIMIT 1
                """,
                (para_id,),
            ).fetchone()
        ]

        remaining_missing_true_false = count_query(
            db,
            """
            SELECT COUNT(*)
            FROM quiz_questions q
            LEFT JOIN question_choices c ON c.question_id = q.id
            WHERE q.question_type = 'true_false' AND c.id IS NULL
            """,
        )
        remaining_duplicate_stems = count_query(
            db,
            """
            SELECT COUNT(*) FROM (
              SELECT para_id, question_type, question_text
              FROM quiz_questions
              WHERE generation_src = 'local_auto'
              GROUP BY para_id, question_type, question_text
              HAVING COUNT(*) > 1
            )
            """,
        )

        print(f"Backup: {backup_path}")
        print(f"Curated replace-all paragraphs synced: {replace_all_paragraphs}")
        print(f"Curated replace-all activities deleted: {replace_all_deleted}")
        print(f"Curated replace-all activities inserted: {replace_all_inserted}")
        print(f"Curated replace-types paragraphs synced: {replace_type_paragraphs}")
        print(f"Curated replace-types activities deleted: {replace_type_deleted}")
        print(f"Curated replace-types activities inserted: {replace_type_inserted}")
        print(f"Curated item-types paragraphs synced: {item_type_paragraphs}")
        print(f"Curated item-types activities deleted: {item_type_deleted}")
        print(f"Curated item-types activities inserted: {item_type_inserted}")
        print(f"Activity generation sources synced: {synced_activity_sources}")
        print(f"Shadowed activities deleted: {removed_shadowed_activities}")
        print(f"Statement activities refreshed: {refreshed_statement_activities}")
        print(f"Question texts contextualized: {contextualized_questions}")
        print(f"Situation-action choice targets: {situation_choice_targets}")
        print(f"Situation-action choices refreshed: {situation_choices_refreshed}")
        print(f"True/False questions repaired: {repaired_true_false}")
        print(f"Deprecated activities deleted: {deprecated_activities_deleted}")
        print(f"Non-curated phraseology builders deleted: {non_curated_phraseology_deleted}")
        print(f"Quiz questions refreshed: {refreshed_quiz_questions}")
        print(f"Quiz choices refreshed: {refreshed_quiz_choices}")
        print(f"Invalid local-auto question paragraphs found: {invalid_question_paragraphs}")
        print(f"Invalid local-auto questions deleted: {invalid_questions_deleted}")
        print(f"Invalid local-auto questions inserted: {invalid_questions_inserted}")
        print(f"Remaining invalid questions deleted: {deleted_invalid_questions}")
        print(f"Duplicate local-auto question groups removed: {duplicate_groups}")
        print(f"Duplicate local-auto questions deleted: {removed_questions}")
        print(f"Invalid phraseology-builder activities found: {invalid_phraseology_targets}")
        print(f"Invalid phraseology-builder activities repaired: {invalid_phraseology_repaired}")
        print(f"Invalid phraseology-builder activities deleted: {invalid_phraseology_deleted}")
        print(f"Invalid spot-the-error activities found: {invalid_spot_targets}")
        print(f"Invalid spot-the-error activities repaired: {invalid_spot_repaired}")
        print(f"Invalid spot-the-error activities deleted: {invalid_spot_deleted}")
        for activity_type, (targets, repaired, deleted, _) in quality_repairs.items():
            label = activity_type.replace("_", "-")
            print(f"Invalid {label} activities found: {targets}")
            print(f"Invalid {label} activities repaired: {repaired}")
            print(f"Invalid {label} activities deleted: {deleted}")
        print(f"Phraseology-builder target paragraphs: {phraseology_targets}")
        print(f"Phraseology-builder activities inserted: {phraseology_inserted}")
        print(f"Sequence-steps target paragraphs: {sequence_targets}")
        print(f"Sequence-steps activities inserted: {sequence_inserted}")
        print(f"Situation-action target paragraphs: {situation_targets}")
        print(f"Situation-action activities inserted: {situation_inserted}")
        print(f"Directive-check target paragraphs: {directive_targets}")
        print(f"Directive-check activities inserted: {directive_inserted}")
        print(f"Conditional-rule target paragraphs: {conditional_targets}")
        print(f"Conditional-rule activities inserted: {conditional_inserted}")
        print(f"Term-definition target paragraphs: {definition_targets}")
        print(f"Term-definition activities inserted: {definition_inserted}")
        print(f"Document-control target paragraphs: {document_targets}")
        print(f"Document-control activities inserted: {document_inserted}")
        print(f"Requirement-check target paragraphs: {requirement_targets}")
        print(f"Requirement-check activities inserted: {requirement_inserted}")
        print(f"Scope-check target paragraphs: {scope_targets}")
        print(f"Scope-check activities inserted: {scope_inserted}")
        print(f"Capability-check target paragraphs: {capability_targets}")
        print(f"Capability-check activities inserted: {capability_inserted}")
        print(f"Reference-check target paragraphs: {reference_targets}")
        print(f"Reference-check activities inserted: {reference_inserted}")
        print(f"Minima-rule target paragraphs: {minima_targets}")
        print(f"Minima-rule activities inserted: {minima_inserted}")
        print(f"List-membership target paragraphs: {list_targets}")
        print(f"List-membership activities inserted: {list_inserted}")
        print(f"Table-lookup target paragraphs: {table_targets}")
        print(f"Table-lookup activities inserted: {table_inserted}")
        print(f"Example-check target paragraphs: {example_targets}")
        print(f"Example-check activities inserted: {example_inserted}")
        print(f"Knowledge-check target paragraphs: {knowledge_targets}")
        print(f"Knowledge-check activities inserted: {knowledge_inserted}")
        print(f"Unmanaged flashcards deleted: {unmanaged_flashcards_deleted}")
        print(f"Curated question paragraphs synced: {curated_question_targets}")
        print(f"Curated questions deleted: {curated_questions_deleted}")
        print(f"Curated questions inserted: {curated_questions_inserted}")
        print(f"Curated flashcard paragraphs synced: {flashcard_targets}")
        print(f"Curated flashcards deleted: {flashcards_deleted}")
        print(f"Curated flashcards inserted: {flashcards_inserted}")
        print(f"Question target paragraphs: {question_targets}")
        print(f"Questions inserted: {questions_inserted}")
        print(f"Remaining True/False questions without choices: {remaining_missing_true_false}")
        print(f"Remaining duplicate local-auto stems: {remaining_duplicate_stems}")
        if unresolved:
            print("Unresolved True/False questions:")
            for para_id, question_text in unresolved:
                print(f"  {para_id}: {question_text}")
        if unresolved_questions:
            print("Unresolved local-auto question paragraphs:")
            for para_id, message in unresolved_questions:
                print(f"  {para_id}: {message}")
        if removed_invalid_questions:
            print("Deleted remaining invalid questions:")
            for para_id, message in removed_invalid_questions:
                print(f"  {para_id}: {message}")
        if unresolved_phraseology:
            print("Unresolved phraseology-builder activities:")
            for para_id, message in unresolved_phraseology:
                print(f"  {para_id}: {message}")
        if unresolved_spot:
            print("Unresolved spot-the-error activities:")
            for para_id, message in unresolved_spot:
                print(f"  {para_id}: {message}")
        for activity_type, (_, _, _, unresolved_items) in quality_repairs.items():
            if not unresolved_items:
                continue
            label = activity_type.replace("_", "-")
            print(f"Unresolved {label} activities:")
            for para_id, message in unresolved_items:
                print(f"  {para_id}: {message}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
