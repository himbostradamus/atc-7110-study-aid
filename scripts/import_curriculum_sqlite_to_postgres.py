#!/usr/bin/env python3
"""
Import the generated browser SQLite curriculum into the Postgres API schema.

This is a pragmatic bridge for the extracted snapshot: the folder ships with a
complete `curriculum.db`, but not with a ready-to-import Postgres source dump.
The script seeds enough structure and learning content for the FastAPI routes
to run against a local Postgres instance.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2.extras import Json


CHAPTER_TITLES = {
    1: "General",
    2: "General Control",
    3: "Airport Traffic Control - Terminal",
    4: "IFR",
    5: "Radar",
    6: "Nonradar",
    7: "Visual",
    8: "Offshore/Oceanic Procedures",
    9: "Special Flights",
    10: "Emergencies",
    11: "Traffic Management Procedures",
    12: "Canadian Airspace Procedures",
    13: "Decision Support Tools",
    14: "Data Link Communications",
}

SECTION_LABELS = {
    "2-1": "General",
    "2-2": "Flight Data",
    "2-3": "Strip Marking",
    "2-4": "Radar",
    "2-5": "ATS Routes",
    "2-6": "Weather",
    "2-7": "Preflight",
    "2-8": "Flight Plans",
    "2-9": "Position Reports",
    "2-10": "Nonradar",
    "3-1": "General Terminal",
    "3-2": "Light Signals",
    "3-3": "Local Control",
    "3-4": "Ground Control",
    "3-5": "Clearance Delivery",
    "3-6": "ATIS",
    "3-7": "Transfer of Control",
    "3-8": "TRACON",
    "3-9": "Departure",
    "3-10": "Arrival",
    "3-11": "Approach Control",
    "3-12": "Radar Approach",
    "4-1": "General IFR",
    "4-2": "Clearances",
    "4-3": "Altitude Assignment",
    "4-4": "Route Assignment",
    "4-5": "Speed Adjustments",
    "4-6": "Holding",
    "4-7": "Approach",
    "4-8": "Approach Clearances",
}

BACKEND_ACTIVITY_TYPES = {
    "phraseology_builder",
    "spot_the_error",
    "sequence_steps",
    "match_pairs",
    "readback_check",
    "situation_action",
    "directive_check",
    "conditional_rule_check",
    "term_definition_check",
    "document_control_check",
    "requirement_check",
    "scope_check",
    "capability_check",
    "reference_check",
    "minima_rule_check",
    "list_membership",
    "table_lookup",
    "visual_interpretation",
    "example_check",
    "knowledge_check",
}

GENERATION_SOURCE_MAP = {
    "rule_based": "local_auto",
    "local_auto": "local_auto",
    "curated": "curated",
}


@dataclass
class ImportStats:
    chapters: int = 0
    sections: int = 0
    paragraphs: int = 0
    content_blocks: int = 0
    activities: int = 0
    flashcards: int = 0
    quiz_questions: int = 0
    question_choices: int = 0


def para_sort_key(para_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in str(para_id).split("-"))


def load_section_fallbacks(sqlite_db: sqlite3.Connection) -> dict[tuple[int, int], str]:
    rows = sqlite_db.execute(
        """
        SELECT p.chapter, p.section, p.title
        FROM paragraphs p
        JOIN (
          SELECT chapter, section, MIN(para_id) AS first_para
          FROM paragraphs
          GROUP BY chapter, section
        ) firsts
          ON firsts.chapter = p.chapter
         AND firsts.section = p.section
         AND firsts.first_para = p.para_id
        ORDER BY p.chapter, p.section
        """
    ).fetchall()
    return {(int(row[0]), int(row[1])): row[2] for row in rows}


def ensure_version(pg, edition: str, effective_date: date) -> str:
    with pg.cursor() as cur:
        cur.execute("UPDATE order_versions SET is_current = FALSE WHERE is_current = TRUE")
        cur.execute(
            """
            INSERT INTO order_versions (edition, effective_date, is_current)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (edition) DO UPDATE
              SET effective_date = EXCLUDED.effective_date,
                  is_current = EXCLUDED.is_current
            RETURNING id::text
            """,
            (edition, effective_date),
        )
        return cur.fetchone()[0]


def ensure_dev_user(pg, email: str) -> None:
    with pg.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return
        cur.execute(
            """
            INSERT INTO users (email, password_hash, first_name, last_name, role, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            """,
            (email, "dev-auth-bypass", "Dev", "User", "admin"),
        )


def import_structure(sqlite_db: sqlite3.Connection, pg, version_id: str) -> tuple[dict[int, str], dict[tuple[int, int], str], ImportStats]:
    stats = ImportStats()
    section_fallbacks = load_section_fallbacks(sqlite_db)

    chapter_ids: dict[int, str] = {}
    section_ids: dict[tuple[int, int], str] = {}

    with pg.cursor() as cur:
        chapter_rows = sqlite_db.execute(
            "SELECT DISTINCT chapter FROM paragraphs ORDER BY chapter"
        ).fetchall()
        for (chapter_number,) in chapter_rows:
            chapter_number = int(chapter_number)
            cur.execute(
                """
                INSERT INTO chapters (version_id, chapter_number, title, sort_order)
                VALUES (%s, %s, %s, %s)
                RETURNING id::text
                """,
                (
                    version_id,
                    chapter_number,
                    CHAPTER_TITLES.get(chapter_number, f"Chapter {chapter_number}"),
                    chapter_number,
                ),
            )
            chapter_ids[chapter_number] = cur.fetchone()[0]
            stats.chapters += 1

        section_rows = sqlite_db.execute(
            """
            SELECT DISTINCT chapter, section
            FROM paragraphs
            ORDER BY chapter, section
            """
        ).fetchall()
        for chapter_number, section_number in section_rows:
            chapter_number = int(chapter_number)
            section_number = int(section_number)
            key = (chapter_number, section_number)
            label_key = f"{chapter_number}-{section_number}"
            section_title = (
                SECTION_LABELS.get(label_key)
                or section_fallbacks.get(key)
                or f"Section {section_number}"
            )
            cur.execute(
                """
                INSERT INTO sections (chapter_id, version_id, section_number, title, sort_order)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id::text
                """,
                (
                    chapter_ids[chapter_number],
                    version_id,
                    section_number,
                    section_title,
                    section_number,
                ),
            )
            section_ids[key] = cur.fetchone()[0]
            stats.sections += 1

        para_rows = sqlite_db.execute(
            """
            SELECT id, chapter, section, para_id, title, page, has_visual, content_json
            FROM paragraphs
            """
        ).fetchall()
        para_rows = sorted(
            para_rows,
            key=lambda row: (int(row[1]), int(row[2]), para_sort_key(row[3])),
        )
        for row in para_rows:
            para_db_id, chapter_number, section_number, para_id, title, page, has_visual, content_json = row
            blocks = json.loads(content_json)
            cur.execute(
                """
                INSERT INTO paragraphs (
                    id, section_id, version_id, para_id, title,
                    page_number, has_visual, sort_order, change_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    para_db_id,
                    section_ids[(int(chapter_number), int(section_number))],
                    version_id,
                    para_id,
                    title,
                    int(page or 0) or None,
                    bool(has_visual),
                    stats.paragraphs + 1,
                    "unchanged",
                ),
            )
            stats.paragraphs += 1

            for block in blocks:
                cur.execute(
                    """
                    INSERT INTO content_blocks (
                        id, paragraph_id, version_id, block_type, sequence, label, content
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid4()),
                        para_db_id,
                        version_id,
                        block.get("block_type", "body"),
                        int(block.get("sequence", 0)),
                        block.get("label") or "",
                        block.get("content") or "",
                    ),
                )
                stats.content_blocks += 1

    return chapter_ids, section_ids, stats


def import_learning_content(sqlite_db: sqlite3.Connection, pg, version_id: str, stats: ImportStats) -> None:
    with pg.cursor() as cur:
        activity_rows = sqlite_db.execute(
            """
            SELECT id, paragraph_db_id, activity_type, content_json, difficulty, generation_src, is_verified
            FROM activities
            ORDER BY para_id, activity_type, id
            """
        ).fetchall()
        for row in activity_rows:
            activity_id, paragraph_id, activity_type, content_json, difficulty, generation_src, is_verified = row
            if activity_type not in BACKEND_ACTIVITY_TYPES:
                continue
            cur.execute(
                """
                INSERT INTO activities (
                    id, paragraph_id, version_id, activity_type, content_json,
                    difficulty, is_active, is_verified, generation_source
                )
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s)
                """,
                (
                    activity_id,
                    paragraph_id,
                    version_id,
                    activity_type,
                    Json(json.loads(content_json)),
                    int(difficulty or 2),
                    bool(is_verified),
                    GENERATION_SOURCE_MAP.get(generation_src, "local_auto"),
                ),
            )
            stats.activities += 1

        flashcard_rows = sqlite_db.execute(
            """
            SELECT id, paragraph_db_id, front, back, card_type, generation_src
            FROM flashcards
            ORDER BY para_id, card_type, id
            """
        ).fetchall()
        for row in flashcard_rows:
            flashcard_id, paragraph_id, front, back, card_type, generation_src = row
            cur.execute(
                """
                INSERT INTO flashcards (
                    id, paragraph_id, version_id, front, back, card_type,
                    is_active, generation_source
                )
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
                """,
                (
                    flashcard_id,
                    paragraph_id,
                    version_id,
                    front,
                    back,
                    card_type or "definition",
                    GENERATION_SOURCE_MAP.get(generation_src, "local_auto"),
                ),
            )
            stats.flashcards += 1

        question_rows = sqlite_db.execute(
            """
            SELECT id, paragraph_db_id, question_text, question_type, explanation, difficulty, is_verified
            FROM quiz_questions
            ORDER BY para_id, question_type, id
            """
        ).fetchall()
        for row in question_rows:
            question_id, paragraph_id, question_text, question_type, explanation, difficulty, is_verified = row
            cur.execute(
                """
                INSERT INTO quiz_questions (
                    id, paragraph_id, version_id, question_text, question_type,
                    explanation, difficulty, is_active, is_verified
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                """,
                (
                    question_id,
                    paragraph_id,
                    version_id,
                    question_text,
                    question_type,
                    explanation,
                    int(difficulty or 2),
                    bool(is_verified),
                ),
            )
            stats.quiz_questions += 1

        choice_rows = sqlite_db.execute(
            """
            SELECT id, question_id, choice_text, is_correct, sort_order
            FROM question_choices
            ORDER BY question_id, sort_order, id
            """
        ).fetchall()
        for row in choice_rows:
            choice_id, question_id, choice_text, is_correct, sort_order = row
            cur.execute(
                """
                INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    choice_id,
                    question_id,
                    choice_text,
                    bool(is_correct),
                    int(sort_order or 0),
                ),
            )
            stats.question_choices += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Import curriculum.db into the Postgres API schema")
    parser.add_argument("--sqlite", default="curriculum.db", help="Path to the generated curriculum SQLite DB")
    parser.add_argument(
        "--db-url",
        default="postgresql://postgres@127.0.0.1:55432/atc_platform",
        help="Postgres connection URL",
    )
    parser.add_argument("--edition", default="7110.65BB CHG 2")
    parser.add_argument("--effective-date", default="2026-01-22")
    parser.add_argument("--dev-user-email", default="dev@local")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    sqlite_db = sqlite3.connect(sqlite_path)
    try:
        pg = psycopg2.connect(args.db_url)
        try:
            pg.autocommit = False
            version_id = ensure_version(pg, args.edition, date.fromisoformat(args.effective_date))
            ensure_dev_user(pg, args.dev_user_email)
            _, _, stats = import_structure(sqlite_db, pg, version_id)
            import_learning_content(sqlite_db, pg, version_id, stats)
            pg.commit()
        except Exception:
            pg.rollback()
            raise
        finally:
            pg.close()
    finally:
        sqlite_db.close()

    print(f"Imported edition:      {args.edition}")
    print(f"Effective date:        {args.effective_date}")
    print(f"Paragraphs:            {stats.paragraphs}")
    print(f"Content blocks:        {stats.content_blocks}")
    print(f"Backend lesson acts:   {stats.activities}")
    print(f"Flashcards:            {stats.flashcards}")
    print(f"Quiz questions:        {stats.quiz_questions}")
    print(f"Question choices:      {stats.question_choices}")
    print(f"Dev auth user:         {args.dev_user_email}")


if __name__ == "__main__":
    main()
