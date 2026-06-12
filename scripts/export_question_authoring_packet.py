#!/usr/bin/env python3
"""
Export source/context packets for asynchronous question authoring.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_OUT_DIR = ROOT / "backend" / "app" / "data" / "question_authoring_workspace" / "packets"


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def flatten_blocks(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        label = str(block.get("label") or "").strip()
        block_type = str(block.get("block_type") or "body").strip()
        content = str(block.get("content") or "").strip()
        if not content:
            continue
        prefix = f"[{block_type}]"
        if label:
            prefix = f"{prefix} {label}"
        parts.append(f"{prefix} {content}")
    return "\n\n".join(parts)


def fetch_choices(db: sqlite3.Connection, question_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        SELECT choice_text, is_correct, sort_order
        FROM question_choices
        WHERE question_id = ?
        ORDER BY sort_order, choice_text
        """,
        (question_id,),
    ).fetchall()
    return [
        {
            "text": row["choice_text"],
            "is_correct": bool(row["is_correct"]),
            "sort_order": row["sort_order"],
        }
        for row in rows
    ]


def fetch_existing_items(db: sqlite3.Connection, para_id: str) -> dict[str, Any]:
    question_rows = db.execute(
        """
        SELECT id, question_text, question_type, explanation, difficulty, generation_src
        FROM quiz_questions
        WHERE para_id = ?
        ORDER BY question_type, question_text
        """,
        (para_id,),
    ).fetchall()
    questions = [
        {
            "question_text": row["question_text"],
            "question_type": row["question_type"],
            "difficulty": row["difficulty"],
            "generation_src": row["generation_src"],
            "explanation": row["explanation"],
            "choices": fetch_choices(db, row["id"]),
        }
        for row in question_rows
    ]

    activity_rows = db.execute(
        """
        SELECT activity_type, content_json, difficulty, generation_src
        FROM activities
        WHERE para_id = ?
        ORDER BY activity_type, generation_src
        """,
        (para_id,),
    ).fetchall()
    activities = [
        {
            "activity_type": row["activity_type"],
            "difficulty": row["difficulty"],
            "generation_src": row["generation_src"],
            "content": parse_json(row["content_json"], {}),
        }
        for row in activity_rows
    ]

    flashcard_rows = db.execute(
        """
        SELECT front, back, card_type, generation_src
        FROM flashcards
        WHERE para_id = ?
        ORDER BY card_type, front
        """,
        (para_id,),
    ).fetchall()
    flashcards = [
        {
            "front": row["front"],
            "back": row["back"],
            "card_type": row["card_type"],
            "generation_src": row["generation_src"],
        }
        for row in flashcard_rows
    ]

    return {
        "counts": {
            "questions": len(questions),
            "activities": len(activities),
            "flashcards": len(flashcards),
        },
        "questions": questions,
        "activities": activities,
        "flashcards": flashcards,
    }


def fetch_paragraphs(
    db: sqlite3.Connection,
    *,
    para_id: str | None,
    chapter: int | None,
    section: int | None,
) -> list[dict[str, Any]]:
    if para_id:
        rows = db.execute(
            """
            SELECT id, chapter, section, para_id, title, page, has_visual, content_json
            FROM paragraphs
            WHERE para_id = ?
            ORDER BY chapter, section, para_id
            """,
            (para_id,),
        ).fetchall()
    elif chapter is not None and section is not None:
        rows = db.execute(
            """
            SELECT id, chapter, section, para_id, title, page, has_visual, content_json
            FROM paragraphs
            WHERE chapter = ? AND section = ?
            ORDER BY chapter, section, para_id
            """,
            (chapter, section),
        ).fetchall()
    elif chapter is not None:
        rows = db.execute(
            """
            SELECT id, chapter, section, para_id, title, page, has_visual, content_json
            FROM paragraphs
            WHERE chapter = ?
            ORDER BY chapter, section, para_id
            """,
            (chapter,),
        ).fetchall()
    else:
        raise ValueError("Provide --para-id, --chapter, or --chapter with --section.")

    packets: list[dict[str, Any]] = []
    for row in rows:
        blocks = parse_json(row["content_json"], [])
        if not isinstance(blocks, list):
            blocks = []
        existing = fetch_existing_items(db, row["para_id"])
        packets.append(
            {
                "para_id": row["para_id"],
                "chapter": row["chapter"],
                "section": row["section"],
                "title": row["title"],
                "page": row["page"],
                "has_visual": bool(row["has_visual"]),
                "blocks": blocks,
                "source_text": flatten_blocks(blocks),
                "existing": existing,
            }
        )
    return packets


def default_output_path(args: argparse.Namespace) -> Path:
    if args.out:
        return args.out
    if args.para_id:
        stem = f"paragraph_{args.para_id.replace('-', '_')}.json"
    elif args.chapter is not None and args.section is not None:
        stem = f"chapter_{args.chapter:02d}_section_{args.section:02d}.json"
    elif args.chapter is not None:
        stem = f"chapter_{args.chapter:02d}.json"
    else:
        stem = "authoring_packet.json"
    return DEFAULT_OUT_DIR / stem


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--para-id")
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--section", type=int)
    args = parser.parse_args()

    if not args.db.exists():
        parser.error(f"database not found: {args.db}")

    output_path = default_output_path(args)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    try:
        paragraphs = fetch_paragraphs(
            db,
            para_id=args.para_id,
            chapter=args.chapter,
            section=args.section,
        )
    finally:
        db.close()

    if not paragraphs:
        parser.error("no paragraphs matched the requested scope")

    packet = {
        "version": 1,
        "source_db": str(args.db),
        "scope": {
            "para_id": args.para_id,
            "chapter": args.chapter,
            "section": args.section,
        },
        "authoring_rules": {
            "storage": "Create new append-only curated_overrides_zzzzzzzz_question_agent_*.json files only.",
            "quality": "Write substantive, self-contained items with plausible distractors and grounded explanations.",
            "avoid": [
                "paragraph-title trivia",
                "underspecified example checks",
                "manufactured phraseology errors from arbitrary values",
                "rewriting otherwise unchanged choices solely to alter stored answer position",
            ],
        },
        "paragraphs": paragraphs,
    }

    output_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(paragraphs)} paragraph packet(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
