#!/usr/bin/env python3
"""Audit staged expansion content for overlap with the live curriculum."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_STAGING = ROOT / "backend" / "app" / "data" / "content_expansion_staging"

TOKEN_RE = re.compile(r"[a-z0-9]+")
QUESTION_KEYS = ("question_text",)
FLASHCARD_KEYS = ("front", "back")


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def lexical_similarity(left: str, right: str) -> float:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    left_tokens = Counter(left_norm.split())
    right_tokens = Counter(right_norm.split())
    overlap = sum((left_tokens & right_tokens).values())
    token_score = (2 * overlap) / (sum(left_tokens.values()) + sum(right_tokens.values()))
    return round(max(sequence, token_score), 4)


def staged_text(entity_type: str, item: dict[str, Any]) -> str:
    if entity_type == "question":
        return str(item.get("question_text") or "")
    if entity_type == "flashcard":
        return f"{item.get('front', '')} {item.get('back', '')}".strip()
    if entity_type == "activity":
        content = item.get("content", {})
        if not isinstance(content, dict):
            return ""
        parts: list[str] = []
        for key in ("prompt", "question", "question_text", "scenario", "statement"):
            value = content.get(key)
            if isinstance(value, str):
                parts.append(value)
        for key in ("choices", "options"):
            values = content.get(key)
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, dict):
                        text = value.get("text") or value.get("choice_text")
                        if isinstance(text, str):
                            parts.append(text)
        return " ".join(parts)
    raise ValueError(f"Unsupported entity type: {entity_type}")


def load_live(
    db: sqlite3.Connection,
    ignored_generation_sources: set[str],
) -> dict[str, list[dict[str, Any]]]:
    live: dict[str, list[dict[str, Any]]] = {
        "question": [],
        "flashcard": [],
        "activity": [],
    }
    for row in db.execute(
        """
        SELECT id, para_id, question_text, generation_src
        FROM quiz_questions
        ORDER BY para_id, id
        """
    ):
        generation_source = str(row[3] or "")
        if generation_source in ignored_generation_sources:
            continue
        live["question"].append({
            "id": str(row[0]),
            "para_id": str(row[1]),
            "text": str(row[2] or ""),
            "generation_source": generation_source,
        })
    for row in db.execute(
        """
        SELECT id, para_id, front, back, generation_src
        FROM flashcards
        ORDER BY para_id, id
        """
    ):
        generation_source = str(row[4] or "")
        if generation_source in ignored_generation_sources:
            continue
        live["flashcard"].append({
            "id": str(row[0]),
            "para_id": str(row[1]),
            "text": f"{row[2] or ''} {row[3] or ''}".strip(),
            "front": str(row[2] or ""),
            "back": str(row[3] or ""),
            "generation_source": generation_source,
        })
    for row in db.execute(
        """
        SELECT id, para_id, activity_type, content_json, generation_src
        FROM activities
        ORDER BY para_id, id
        """
    ):
        generation_source = str(row[4] or "")
        if generation_source in ignored_generation_sources:
            continue
        content = json.loads(row[3])
        live["activity"].append({
            "id": str(row[0]),
            "para_id": str(row[1]),
            "text": staged_text("activity", {"content": content}),
            "activity_type": str(row[2] or ""),
            "generation_source": generation_source,
        })
    return live


def iter_staged(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    staged: list[dict[str, Any]] = []
    family_to_type = {
        "questions": "question",
        "activities": "activity",
        "flashcards": "flashcard",
    }
    for family, entity_type in family_to_type.items():
        for para_id, group in payload.get(family, {}).items():
            for index, item in enumerate(group.get("items", [])):
                staged.append({
                    "entity_type": entity_type,
                    "family": family,
                    "para_id": para_id,
                    "index": index,
                    "text": staged_text(entity_type, item),
                    "item": item,
                })
    return staged


def best_matches(
    staged: dict[str, Any],
    live: dict[str, list[dict[str, Any]]],
    threshold: float,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    comparison_types = [staged["entity_type"]]
    if staged["entity_type"] in {"question", "flashcard"}:
        comparison_types.extend(
            entity_type
            for entity_type in ("question", "flashcard")
            if entity_type != staged["entity_type"]
        )
    for live_type in comparison_types:
        candidates = [
            item for item in live[live_type]
            if item["para_id"] == staged["para_id"]
        ]
        ranked = sorted(
            (
                (lexical_similarity(staged["text"], item["text"]), item)
                for item in candidates
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        if ranked and ranked[0][0] >= threshold:
            score, item = ranked[0]
            matches.append({
                "live_entity_type": live_type,
                "same_format": live_type == staged["entity_type"],
                "score": score,
                **item,
            })
    return matches


def audit_file(
    path: Path,
    live: dict[str, list[dict[str, Any]]],
    threshold: float,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for staged in iter_staged(path):
        matches = best_matches(staged, live, threshold)
        if not matches:
            continue
        findings.append({
            key: staged[key]
            for key in ("entity_type", "family", "para_id", "index", "text")
        } | {"matches": matches})
    return {
        "batch": path.name,
        "threshold": threshold,
        "finding_count": len(findings),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", nargs="+", type=Path)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--threshold", type=float, default=0.72)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--ignore-generation-source",
        action="append",
        default=[],
        help="Exclude a live generation source; may be supplied more than once.",
    )
    args = parser.parse_args()

    with sqlite3.connect(args.db) as db:
        live = load_live(db, set(args.ignore_generation_source))
    reports = [
        audit_file(
            batch if batch.is_absolute() else ROOT / batch,
            live,
            args.threshold,
        )
        for batch in args.batches
    ]
    payload = {
        "version": 1,
        "database": str(args.db),
        "threshold": args.threshold,
        "ignored_generation_sources": args.ignore_generation_source,
        "summary": {
            "batches": len(reports),
            "findings": sum(report["finding_count"] for report in reports),
        },
        "reports": reports,
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if args.out:
        output = args.out if args.out.is_absolute() else ROOT / args.out
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"Wrote {payload['summary']['findings']} findings to {output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
