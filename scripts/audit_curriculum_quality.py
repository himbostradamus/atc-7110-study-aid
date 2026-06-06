#!/usr/bin/env python3
"""
Audit curriculum.db for activity and quiz quality issues.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.activity_generator import validate_activity_payload  # noqa: E402
from backend.app.services.question_generator import choice_text_errors, question_text_errors  # noqa: E402


CHOICE_QUESTION_TYPES = {"multiple_choice", "true_false"}


@dataclass(frozen=True)
class AuditIssue:
    kind: str
    para_id: str
    entity: str
    detail: str


def audit_activities(db: sqlite3.Connection) -> tuple[int, list[AuditIssue]]:
    rows = db.execute(
        """
        SELECT a.para_id, a.activity_type, a.generation_src, a.content_json, p.title
        FROM activities a
        JOIN paragraphs p ON p.id = a.paragraph_db_id
        ORDER BY a.para_id, a.activity_type, a.id
        """
    ).fetchall()

    issues: list[AuditIssue] = []
    for row in rows:
        payload = json.loads(row["content_json"])
        errors = validate_activity_payload(row["activity_type"], payload, row["title"])
        if errors:
            issues.append(
                AuditIssue(
                    kind="activity",
                    para_id=row["para_id"],
                    entity=row["activity_type"],
                    detail=f"{row['generation_src']}: {', '.join(errors)}",
                )
            )

    return len(rows), issues


def audit_questions(db: sqlite3.Connection) -> tuple[int, list[AuditIssue]]:
    issues: list[AuditIssue] = []
    question_rows = db.execute(
        """
        SELECT
            q.id,
            q.para_id,
            q.question_text,
            q.question_type,
            q.generation_src,
            COUNT(c.id) AS choice_count,
            COALESCE(SUM(CASE WHEN c.is_correct THEN 1 ELSE 0 END), 0) AS correct_count
        FROM quiz_questions q
        LEFT JOIN question_choices c ON c.question_id = q.id
        GROUP BY q.id, q.para_id, q.question_text, q.question_type, q.generation_src
        ORDER BY q.para_id, q.question_type, q.id
        """
    ).fetchall()

    for row in question_rows:
        text_errors = question_text_errors(row["question_type"], row["question_text"])
        for error in text_errors:
            issues.append(
                AuditIssue(
                    kind="question",
                    para_id=row["para_id"],
                    entity=row["question_type"],
                    detail=f"{row['generation_src']}: {error} in '{row['question_text']}'",
                )
            )
        if row["question_type"] not in CHOICE_QUESTION_TYPES:
            continue
        if row["choice_count"] == 0:
            issues.append(
                AuditIssue(
                    kind="question",
                    para_id=row["para_id"],
                    entity=row["question_type"],
                    detail=f"{row['generation_src']}: missing choices for '{row['question_text']}'",
                )
            )
        elif row["correct_count"] != 1:
            issues.append(
                AuditIssue(
                    kind="question",
                    para_id=row["para_id"],
                    entity=row["question_type"],
                    detail=(
                        f"{row['generation_src']}: expected 1 correct choice, found "
                        f"{row['correct_count']} for '{row['question_text']}'"
                    ),
                )
            )

    duplicate_choice_rows = db.execute(
        """
        SELECT
            q.para_id,
            q.question_type,
            q.question_text,
            q.generation_src,
            LOWER(TRIM(c.choice_text)) AS choice_key,
            COUNT(*) AS duplicate_count
        FROM question_choices c
        JOIN quiz_questions q ON q.id = c.question_id
        GROUP BY q.id, LOWER(TRIM(c.choice_text))
        HAVING COUNT(*) > 1
        ORDER BY q.para_id, q.question_type, q.id
        """
    ).fetchall()
    for row in duplicate_choice_rows:
        issues.append(
            AuditIssue(
                kind="question",
                para_id=row["para_id"],
                entity=row["question_type"],
                detail=(
                    f"{row['generation_src']}: duplicate choice text '{row['choice_key']}' "
                    f"in '{row['question_text']}'"
                ),
            )
        )

    choice_rows = db.execute(
        """
        SELECT q.para_id, q.question_type, q.question_text, q.generation_src, c.choice_text
        FROM question_choices c
        JOIN quiz_questions q ON q.id = c.question_id
        ORDER BY q.para_id, q.question_type, q.id, c.sort_order, c.id
        """
    ).fetchall()
    for row in choice_rows:
        text_errors = choice_text_errors(row["choice_text"])
        for error in text_errors:
            issues.append(
                AuditIssue(
                    kind="question",
                    para_id=row["para_id"],
                    entity=row["question_type"],
                    detail=f"{row['generation_src']}: {error} in choice '{row['choice_text']}' for '{row['question_text']}'",
                )
            )

    duplicate_stem_rows = db.execute(
        """
        SELECT para_id, question_type, question_text, COUNT(*) AS duplicate_count
        FROM quiz_questions
        GROUP BY para_id, question_type, question_text
        HAVING COUNT(*) > 1
        ORDER BY para_id, question_type, question_text
        """
    ).fetchall()
    for row in duplicate_stem_rows:
        issues.append(
            AuditIssue(
                kind="question",
                para_id=row["para_id"],
                entity=row["question_type"],
                detail=(
                    f"duplicate question stem appears {row['duplicate_count']} times: "
                    f"'{row['question_text']}'"
                ),
            )
        )

    return len(question_rows), issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="curriculum.db", help="Path to the SQLite curriculum DB")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of example issues to print",
    )
    args = parser.parse_args()

    db = sqlite3.connect(Path(args.db).resolve())
    db.row_factory = sqlite3.Row
    try:
        activity_count, activity_issues = audit_activities(db)
        question_count, question_issues = audit_questions(db)
    finally:
        db.close()

    issues = activity_issues + question_issues
    print(f"Activities audited: {activity_count}")
    print(f"Questions audited:  {question_count}")
    print(f"Issues found:       {len(issues)}")

    if not issues:
        print("No activity or quiz quality issues detected.")
        return 0

    print("\nIssue counts:")
    counts = Counter((issue.kind, issue.entity) for issue in issues)
    for (kind, entity), count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {kind}/{entity}: {count}")

    print("\nExamples:")
    for issue in issues[: max(args.limit, 0)]:
        print(f"  {issue.kind} {issue.para_id} {issue.entity}: {issue.detail}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
