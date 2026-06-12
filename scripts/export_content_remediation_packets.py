#!/usr/bin/env python3
"""Export stable-ID chapter packets for content remediation agents."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_OUT = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "remediation" / "packets"
)
DEFAULT_TARGET_SOURCE = "question_agent"
LOCATION_RE = re.compile(
    r"\b(?:"
    r"under\s+(?:the\s+)?(?:(?:paragraph|para|section)\s+)?"
    r"|(?:from|in)\s+(?:the\s+)?(?:paragraph|para|section)\s+"
    r"|(?:paragraph|para|section)\s+"
    r")\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
GENERIC_REFERENCE_RE = re.compile(
    r"\b(?:this|the)\s+(?:paragraph|section|rule|material|example)\b",
    re.IGNORECASE,
)
NEGATIVE_RE = re.compile(
    r"\b(?:not|except|false|incorrect|least appropriate|does not|doesn't)\b",
    re.IGNORECASE,
)
QUESTION_LEAD_RE = re.compile(
    r"^(?:what|when|where|who|which|how|why|identify|name|state|list|"
    r"select|choose|determine|give|describe|explain)\b",
    re.IGNORECASE,
)


def parse_json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except json.JSONDecodeError:
        return fallback


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def flatten_blocks(blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    parts = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        content = normalize(block.get("content"))
        if not content:
            continue
        label = normalize(block.get("label"))
        block_type = normalize(block.get("block_type") or "body")
        prefix = f"[{block_type}]"
        if label:
            prefix += f" {label}"
        parts.append(f"{prefix} {content}")
    return "\n\n".join(parts)


def choices_for(db: sqlite3.Connection, question_id: str) -> list[dict[str, Any]]:
    return [
        {
            "text": row["choice_text"],
            "is_correct": bool(row["is_correct"]),
            "sort_order": row["sort_order"],
        }
        for row in db.execute(
            """
            SELECT choice_text, is_correct, sort_order
            FROM question_choices
            WHERE question_id = ?
            ORDER BY sort_order, id
            """,
            (question_id,),
        )
    ]


def question_flags(item: dict[str, Any]) -> list[str]:
    text = normalize(item["question_text"])
    explanation = normalize(item["explanation"])
    choices = item["choices"]
    flags = []
    if LOCATION_RE.search(text):
        flags.append("paragraph_location_scaffold")
    if GENERIC_REFERENCE_RE.search(text):
        flags.append("generic_reference")
    if NEGATIVE_RE.search(text):
        flags.append("negative_stem")
    if len(explanation.split()) < 10:
        flags.append("thin_explanation")
    correct = [choice for choice in choices if choice["is_correct"]]
    if item["question_type"] == "fill_blank":
        if not correct:
            flags.append("invalid_answer_key")
    elif len(correct) != 1:
        flags.append("invalid_answer_key")
    if choices and choices[0]["is_correct"]:
        flags.append("correct_answer_first")
    if len(correct) == 1:
        distractor_lengths = [
            max(1, len(normalize(choice["text"]).split()))
            for choice in choices if not choice["is_correct"]
        ]
        correct_length = len(normalize(correct[0]["text"]).split())
        if (
            distractor_lengths
            and correct_length >= 6
            and correct_length > (sum(distractor_lengths) / len(distractor_lengths)) * 1.8
        ):
            flags.append("answer_length_cue")
    return flags


def card_flags(item: dict[str, Any]) -> list[str]:
    front = normalize(item["front"])
    back = normalize(item["back"])
    card_type = normalize(item["card_type"]).lower()
    flags = []
    if LOCATION_RE.search(front) and card_type not in {"reference", "source_reference"}:
        flags.append("paragraph_location_scaffold")
    if GENERIC_REFERENCE_RE.search(front):
        flags.append("generic_reference")
    if len(front.split()) < 4 and "?" not in front and not QUESTION_LEAD_RE.search(front):
        flags.append("context_light_front")
    if len(back.split()) < 4:
        flags.append("thin_back")
    if len(back.split()) > 50 or len(re.findall(r"(?:^|\s)\d+[.)]\s", back)) > 6:
        flags.append("overloaded_back")
    if "reverse" in card_type and "?" not in back and not QUESTION_LEAD_RE.search(back):
        flags.append("malformed_reverse")
    return flags


def activity_prompt(payload: dict[str, Any]) -> str:
    return normalize(" ".join(
        str(payload.get(key) or "")
        for key in (
            "situation", "clearance", "lookup_context", "para_context",
            "question_text", "task", "instruction",
        )
    ))


def activity_flags(item: dict[str, Any]) -> list[str]:
    payload = item["content"]
    prompt = activity_prompt(payload)
    explanation = normalize(payload.get("explanation"))
    flags = []
    if LOCATION_RE.search(prompt) and item["activity_type"] not in {"source_lookup", "source_use"}:
        flags.append("paragraph_location_scaffold")
    if GENERIC_REFERENCE_RE.search(prompt):
        flags.append("generic_reference")
    if NEGATIVE_RE.search(prompt):
        flags.append("negative_stem")
    if len(explanation.split()) < 10:
        flags.append("thin_explanation")
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        correct = [choice for choice in choices if choice.get("is_correct") is True]
        if len(correct) != 1:
            flags.append("invalid_answer_key")
        elif choices[0].get("is_correct") is True:
            flags.append("correct_answer_first")
        if len(correct) == 1:
            correct_length = len(normalize(correct[0].get("text")).split())
            distractors = [
                max(1, len(normalize(choice.get("text")).split()))
                for choice in choices if choice.get("is_correct") is not True
            ]
            if (
                distractors
                and correct_length >= 6
                and correct_length > (sum(distractors) / len(distractors)) * 1.8
            ):
                flags.append("answer_length_cue")
    return flags


def target_items(
    db: sqlite3.Connection,
    para_id: str,
    target_source: str,
) -> dict[str, list[dict[str, Any]]]:
    questions = []
    for row in db.execute(
        """
        SELECT id, question_text, question_type, explanation, difficulty
        FROM quiz_questions
        WHERE para_id = ? AND generation_src = ?
        ORDER BY question_type, question_text, id
        """,
        (para_id, target_source),
    ):
        item = {
            "id": row["id"],
            "question_text": row["question_text"],
            "question_type": row["question_type"],
            "explanation": row["explanation"],
            "difficulty": row["difficulty"],
            "choices": choices_for(db, row["id"]),
        }
        item["automated_flags"] = question_flags(item)
        questions.append(item)

    activities = []
    for row in db.execute(
        """
        SELECT id, activity_type, content_json, difficulty
        FROM activities
        WHERE para_id = ? AND generation_src = ?
        ORDER BY activity_type, id
        """,
        (para_id, target_source),
    ):
        item = {
            "id": row["id"],
            "activity_type": row["activity_type"],
            "difficulty": row["difficulty"],
            "content": parse_json(row["content_json"], {}),
        }
        item["automated_flags"] = activity_flags(item)
        activities.append(item)

    flashcards = []
    for row in db.execute(
        """
        SELECT id, front, back, card_type
        FROM flashcards
        WHERE para_id = ? AND generation_src = ?
        ORDER BY card_type, front, id
        """,
        (para_id, target_source),
    ):
        item = {
            "id": row["id"],
            "front": row["front"],
            "back": row["back"],
            "card_type": row["card_type"],
        }
        item["automated_flags"] = card_flags(item)
        flashcards.append(item)
    return {
        "question": questions,
        "activity": activities,
        "flashcard": flashcards,
    }


def reference_items(
    db: sqlite3.Connection,
    para_id: str,
    target_source: str,
) -> dict[str, list[dict[str, Any]]]:
    questions = [
        {
            "generation_src": row["generation_src"],
            "question_type": row["question_type"],
            "question_text": row["question_text"],
        }
        for row in db.execute(
            """
            SELECT generation_src, question_type, question_text
            FROM quiz_questions
            WHERE para_id = ? AND generation_src != ?
            ORDER BY generation_src, question_type, question_text
            """,
            (para_id, target_source),
        )
    ]
    activities = []
    for row in db.execute(
        """
        SELECT generation_src, activity_type, content_json
        FROM activities
        WHERE para_id = ? AND generation_src != ?
        ORDER BY generation_src, activity_type
        """,
        (para_id, target_source),
    ):
        payload = parse_json(row["content_json"], {})
        activities.append({
            "generation_src": row["generation_src"],
            "activity_type": row["activity_type"],
            "prompt": activity_prompt(payload) if isinstance(payload, dict) else "",
        })
    flashcards = [
        {
            "generation_src": row["generation_src"],
            "card_type": row["card_type"],
            "front": row["front"],
        }
        for row in db.execute(
            """
            SELECT generation_src, card_type, front
            FROM flashcards
            WHERE para_id = ? AND generation_src != ?
            ORDER BY generation_src, card_type, front
            """,
            (para_id, target_source),
        )
    ]
    return {
        "questions": questions,
        "activities": activities,
        "flashcards": flashcards,
    }


def export_chapter(
    db: sqlite3.Connection,
    chapter: int,
    output_path: Path,
    target_source: str,
    source_db: Path,
) -> dict[str, Any]:
    paragraphs = []
    counts = Counter()
    flag_counts = Counter()
    for row in db.execute(
        """
        SELECT chapter, section, para_id, title, page, has_visual, content_json
        FROM paragraphs
        WHERE chapter = ?
        ORDER BY section, para_id
        """,
        (chapter,),
    ):
        blocks = parse_json(row["content_json"], [])
        targets = target_items(db, row["para_id"], target_source)
        for entity_type, items in targets.items():
            counts[entity_type] += len(items)
            for item in items:
                flag_counts.update(
                    f"{entity_type}:{flag}" for flag in item["automated_flags"]
                )
        paragraphs.append({
            "para_id": row["para_id"],
            "section": row["section"],
            "title": row["title"],
            "page": row["page"],
            "has_visual": bool(row["has_visual"]),
            "source_blocks": blocks,
            "source_text": flatten_blocks(blocks),
            "targets": targets,
            "reference_items": reference_items(db, row["para_id"], target_source),
        })

    packet = {
        "version": 1,
        "packet_type": "chapter_content_remediation",
        "chapter": chapter,
        "target_generation_source": target_source,
        "source_db": str(source_db),
        "target_counts": dict(counts),
        "automated_flag_counts": dict(sorted(flag_counts.items())),
        "audit_findings": {
            "systemwide": [
                "Only about half of represented essential source statements are covered by any learning format.",
                "Cross-format reinforcement is weak; very few source statements are covered by questions, cards, and activities.",
                "Paragraph-location scaffolding substitutes document trivia for substance in many items.",
                "Some cards are context-light, malformed in reverse, overloaded, or near duplicates.",
                "Choice activities show answer-position bias and conspicuous answer-length cues.",
                "Explanations often restate an answer instead of teaching the controlling principle.",
            ],
            "review_priority": [
                "source fidelity and unsafe operational implications",
                "self-contained context and educational coherence",
                "answer defensibility and distractor quality",
                "format fit and explanation quality",
                "retrieval diversity without duplication",
            ],
        },
        "paragraphs": paragraphs,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return packet


def parse_chapters(value: str) -> list[int]:
    chapters = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = (int(item) for item in part.split("-", 1))
            chapters.update(range(start, end + 1))
        else:
            chapters.add(int(part))
    return sorted(chapters)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--chapters", default="1-14")
    parser.add_argument("--target-source", default=DEFAULT_TARGET_SOURCE)
    args = parser.parse_args()
    if not args.db.exists():
        parser.error(f"database not found: {args.db}")

    out_dir = args.out_dir
    if out_dir is None:
        out_dir = (
            DEFAULT_OUT
            if args.target_source == DEFAULT_TARGET_SOURCE
            else DEFAULT_OUT / args.target_source
        )

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    try:
        for chapter in parse_chapters(args.chapters):
            output_path = out_dir / f"chapter_{chapter:02d}.json"
            packet = export_chapter(
                db,
                chapter,
                output_path,
                args.target_source,
                args.db,
            )
            counts = packet["target_counts"]
            print(
                f"chapter {chapter:02d}: "
                f"{counts.get('question', 0)} questions, "
                f"{counts.get('activity', 0)} activities, "
                f"{counts.get('flashcard', 0)} flashcards -> {output_path}"
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
