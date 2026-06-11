#!/usr/bin/env python3
"""Validate the browser curriculum database and current-source release invariants."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
MINIMUM_COUNTS = {
    "paragraphs": 680,
    "activities": 2_500,
    "quiz_questions": 4_000,
    "flashcards": 4_900,
}


def scalar(db: sqlite3.Connection, sql: str, params: tuple = ()) -> int | str:
    return db.execute(sql, params).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    failures: list[str] = []

    db = sqlite3.connect(args.db)
    try:
        integrity = scalar(db, "PRAGMA quick_check")
        if integrity != "ok":
            failures.append(f"SQLite quick_check: {integrity}")

        tables = {
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        required = {
            "paragraphs", "activities", "quiz_questions",
            "question_choices", "flashcards",
        }
        missing_tables = sorted(required - tables)
        if missing_tables:
            failures.append("missing tables: " + ", ".join(missing_tables))
        else:
            for table, minimum in MINIMUM_COUNTS.items():
                count = scalar(db, f"SELECT COUNT(*) FROM {table}")
                if count < minimum:
                    failures.append(f"{table} count {count} is below {minimum}")

            empty_checks = {
                "paragraphs": "para_id = '' OR content_json = ''",
                "activities": "para_id = '' OR activity_type = '' OR content_json = ''",
                "quiz_questions": "para_id = '' OR question_text = ''",
                "flashcards": "para_id = '' OR front = '' OR back = ''",
            }
            for table, predicate in empty_checks.items():
                count = scalar(
                    db,
                    f"SELECT COUNT(*) FROM {table} WHERE {predicate}",
                )
                if count:
                    failures.append(f"{table} has {count} empty required records")

            orphan_choices = scalar(
                db,
                """
                SELECT COUNT(*) FROM question_choices c
                LEFT JOIN quiz_questions q ON q.id = c.question_id
                WHERE q.id IS NULL
                """,
            )
            if orphan_choices:
                failures.append(f"{orphan_choices} orphan question choices")

            invalid_answers = list(db.execute(
                """
                SELECT q.id, q.question_type, COUNT(c.id), SUM(c.is_correct)
                FROM quiz_questions q
                LEFT JOIN question_choices c ON c.question_id = q.id
                GROUP BY q.id
                HAVING
                    (q.question_type IN ('multiple_choice', 'true_false') AND SUM(c.is_correct) != 1)
                    OR (q.question_type = 'true_false' AND COUNT(c.id) != 2)
                    OR (q.question_type = 'multiple_choice' AND COUNT(c.id) < 3)
                    OR (q.question_type = 'fill_blank' AND SUM(c.is_correct) < 1)
                LIMIT 20
                """
            ))
            if invalid_answers:
                failures.append(
                    f"{len(invalid_answers)} sampled questions have invalid answer structures"
                )

            for activity_id, content_json in db.execute(
                "SELECT id, content_json FROM activities"
            ):
                try:
                    content = json.loads(content_json)
                except json.JSONDecodeError:
                    failures.append(f"activity {activity_id} has invalid JSON")
                    break
                if not isinstance(content, dict):
                    failures.append(f"activity {activity_id} content is not an object")
                    break

            stale_aircraft = scalar(
                db,
                """
                SELECT COUNT(*) FROM flashcards
                WHERE generation_src = 'aircraft_jo7360'
                  AND (front LIKE '%7360.1J%' OR back LIKE '%7360.1J%')
                """,
            )
            if stale_aircraft:
                failures.append(f"{stale_aircraft} aircraft cards still cite JO 7360.1J")
    finally:
        db.close()

    stale_files = []
    for relative in (
        "frontend/src/App.jsx",
        "frontend/src/faaSource.js",
        "backend/app/services/curated_flashcards.py",
        "README.md",
        "NOTICE.md",
    ):
        if "7360.1J" in (ROOT / relative).read_text(encoding="utf-8"):
            stale_files.append(relative)
    if stale_files:
        failures.append("stale JO 7360.1J references: " + ", ".join(stale_files))

    pwa_files = (
        "frontend/public/manifest.webmanifest",
        "frontend/public/sw.js",
        "frontend/public/icons/atc-study-192.png",
        "frontend/public/icons/atc-study-512.png",
        "frontend/public/icons/apple-touch-icon.png",
    )
    missing_pwa = [relative for relative in pwa_files if not (ROOT / relative).exists()]
    if missing_pwa:
        failures.append("missing mobile install assets: " + ", ".join(missing_pwa))
    else:
        try:
            manifest = json.loads(
                (ROOT / pwa_files[0]).read_text(encoding="utf-8")
            )
            if manifest.get("display") != "standalone" or not manifest.get("icons"):
                failures.append("manifest is missing standalone display or icons")
        except json.JSONDecodeError as exc:
            failures.append(f"invalid web manifest: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Static release validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
