#!/usr/bin/env python3
"""Build audit-guided packets for a numbered content-expansion pass."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from export_content_remediation_packets import parse_chapters
from export_question_authoring_packet import fetch_paragraphs


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    ROOT
    / "backend"
    / "app"
    / "data"
    / "question_authoring_workspace"
    / "expansion"
)
STAGING = ROOT / "backend" / "app" / "data" / "content_expansion_staging"
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
PRIORITY_CHAPTERS = {4, 7, 8, 9, 13, 14}

LOCATION_RE = re.compile(
    r"\b(?:under|from|in|per|according to)\s+(?:the\s+)?"
    r"(?:paragraph|para|section|chapter|note)?\s*"
    r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
GENERIC_REFERENCE_RE = re.compile(
    r"\b(?:this|the)\s+(?:paragraph|section|rule|material|example)\b",
    re.IGNORECASE,
)
SPACING_RE = re.compile(r"\s+[,.?!;:]")
QUESTION_LEAD_RE = re.compile(
    r"^(?:what|when|where|who|which|how|why|identify|name|state|list|"
    r"select|choose|determine|give|describe|explain)\b",
    re.IGNORECASE,
)
SCENARIO_RE = re.compile(
    r"\b(?:aircraft|pilot|controller|traffic|runway|flight|facility|sector|"
    r"approach|departure|arrival|reports?|requests?|observed|you are|you have)\b",
    re.IGNORECASE,
)
CONDITION_RE = re.compile(
    r"\b(?:when|unless|until|if|before|after|while|provided|except)\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\b|\b(?:mile|miles|feet|foot|minutes?|seconds?|knots?|"
    r"degrees?|percent|frequency|altitude|flight level|radius|distance)\b",
    re.IGNORECASE,
)
SEQUENCE_RE = re.compile(
    r"\b(?:sequence|order|first|next|before|after|then|followed by|steps?|items?)\b",
    re.IGNORECASE,
)
PHRASEOLOGY_RE = re.compile(
    r"\b(?:phraseology|say|state|transmit|advise|issue|clearance|read back|"
    r"approved words|use the following)\b",
    re.IGNORECASE,
)
SOURCE_USE_RE = re.compile(
    r"\b(?:TBL|TABLE|FIG|FIGURE|chart|matrix|lookup|minimum|minima|distance|"
    r"category|classification)\b",
    re.IGNORECASE,
)


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def flatten(value: object) -> str:
    parts: list[str] = []

    def visit(item: object, key: str = "") -> None:
        if key in {"generation_source", "generation_src", "source_block"}:
            return
        if isinstance(item, dict):
            for child_key, child in item.items():
                visit(child, str(child_key))
        elif isinstance(item, list):
            for child in item:
                visit(child, key)
        elif isinstance(item, (str, int, float)):
            parts.append(str(item))

    visit(value)
    return normalize(" ".join(parts))


def question_mode(item: dict[str, Any]) -> str:
    text = normalize(item.get("question_text"))
    question_type = normalize(item.get("question_type")).lower()
    if question_type == "fill_blank":
        return "cloze"
    if question_type == "true_false":
        return "verification"
    if SCENARIO_RE.search(text) and len(text.split()) >= 22:
        return "scenario_application"
    if CONDITION_RE.search(text):
        return "condition_boundary"
    if NUMBER_RE.search(text):
        return "numeric_or_minimum"
    if SEQUENCE_RE.search(text):
        return "ordering_or_sequence"
    if re.search(r"\b(?:which of the following|which option|which action)\b", text, re.I):
        return "discrimination"
    return "direct_recall"


def activity_mode(item: dict[str, Any]) -> str:
    activity_type = normalize(item.get("activity_type")).lower()
    if activity_type in {"source_lookup", "source_use", "table_lookup", "figure_lookup"}:
        return "source_use"
    if any(word in activity_type for word in ("phraseology", "readback", "format")):
        return "phraseology_exactness"
    if any(word in activity_type for word in ("list", "sequence", "ordering")):
        return "ordering_or_list"
    if any(word in activity_type for word in ("discrimination", "spot_the_error")):
        return "discrimination"
    if any(word in activity_type for word in ("situation", "scenario", "decision", "responsibility")):
        return "scenario_application"
    if "requirement" in activity_type:
        return "requirement_recall"
    return "knowledge_check"


def card_mode(item: dict[str, Any]) -> str:
    card_type = normalize(item.get("card_type")).lower()
    if "reverse" in card_type:
        return "reverse_recall"
    if card_type in {"phraseology", "format"}:
        return "exact_recall"
    if card_type in {"threshold", "minimum"}:
        return "numeric_recall"
    if card_type in {"condition", "conditions", "exception", "restriction", "scope", "capability"}:
        return "boundary_recall"
    if card_type in {"contrast", "comparison"}:
        return "discrimination"
    if card_type in {"procedure", "sequence"}:
        return "procedure_recall"
    if card_type == "list":
        return "list_recall"
    if card_type in {"reference", "source_reference"}:
        return "source_navigation"
    if card_type == "definition":
        return "definition_recall"
    return "concept_recall"


def question_flags(item: dict[str, Any]) -> list[str]:
    text = normalize(item.get("question_text"))
    explanation = normalize(item.get("explanation"))
    flags: list[str] = []
    if LOCATION_RE.search(text):
        flags.append("document_location_scaffold")
    if GENERIC_REFERENCE_RE.search(text):
        flags.append("generic_reference")
    if SPACING_RE.search(text):
        flags.append("punctuation_spacing")
    if len(explanation.split()) < 10:
        flags.append("thin_explanation")
    choices = item.get("choices")
    if isinstance(choices, list):
        if len([choice for choice in choices if choice.get("is_correct") is True]) != 1:
            flags.append("invalid_answer_key")
        choice_text = " ".join(normalize(choice.get("text")) for choice in choices)
        if LOCATION_RE.search(choice_text):
            flags.append("choice_document_location_scaffold")
        if GENERIC_REFERENCE_RE.search(choice_text):
            flags.append("choice_generic_reference")
    return flags


def activity_flags(item: dict[str, Any]) -> list[str]:
    payload = item.get("content") if isinstance(item.get("content"), dict) else item
    prompt = normalize(
        " ".join(
            str(payload.get(key) or "")
            for key in (
                "situation",
                "clearance",
                "lookup_context",
                "para_context",
                "question_text",
                "task",
                "instruction",
            )
        )
    )
    explanation = normalize(payload.get("explanation"))
    flags: list[str] = []
    if LOCATION_RE.search(prompt) and activity_mode(item) != "source_use":
        flags.append("document_location_scaffold")
    if GENERIC_REFERENCE_RE.search(prompt):
        flags.append("generic_reference")
    if SPACING_RE.search(prompt):
        flags.append("punctuation_spacing")
    if len(prompt.split()) < 8:
        flags.append("thin_prompt")
    if len(explanation.split()) < 10:
        flags.append("thin_explanation")
    return flags


def card_flags(item: dict[str, Any]) -> list[str]:
    front = normalize(item.get("front"))
    back = normalize(item.get("back"))
    flags: list[str] = []
    if LOCATION_RE.search(front) and card_mode(item) != "source_navigation":
        flags.append("document_location_scaffold")
    if GENERIC_REFERENCE_RE.search(front):
        flags.append("generic_reference")
    if SPACING_RE.search(front) or SPACING_RE.search(back):
        flags.append("punctuation_spacing")
    if len(front.split()) < 4 and "?" not in front and not QUESTION_LEAD_RE.search(front):
        flags.append("context_light_front")
    if len(back.split()) < 4:
        flags.append("thin_back")
    if len(back.split()) > 50 or len(re.findall(r"(?:^|\s)\d+[.)]\s", back)) > 6:
        flags.append("overloaded_back")
    return flags


def load_prior_pass(chapter: int, pass_number: int) -> dict[str, Any]:
    path = STAGING / f"chapter_{chapter:02d}_pass_{pass_number:02d}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def staged_items(payload: dict[str, Any], family: str, para_id: str) -> list[dict[str, Any]]:
    container = payload.get(family)
    if not isinstance(container, dict):
        return []
    paragraph = container.get(para_id)
    if not isinstance(paragraph, dict) or not isinstance(paragraph.get("items"), list):
        return []
    return paragraph["items"]


def additions_for_paragraph(
    paragraph: dict[str, Any],
    question_modes: set[str],
    activity_modes: set[str],
    card_modes: set[str],
    quality_flags: Counter[str],
) -> list[str]:
    source = normalize(paragraph.get("source_text"))
    additions: list[str] = []
    if SOURCE_USE_RE.search(source) or paragraph.get("has_visual"):
        if "source_use" not in activity_modes:
            additions.append("source_use")
    if PHRASEOLOGY_RE.search(source):
        if "exact_recall" not in card_modes and "phraseology_exactness" not in activity_modes:
            additions.append("phraseology_exactness")
    if SEQUENCE_RE.search(source):
        if (
            "ordering_or_sequence" not in question_modes
            and "ordering_or_list" not in activity_modes
            and "procedure_recall" not in card_modes
        ):
            additions.append("ordering_or_list")
    if NUMBER_RE.search(source):
        if "numeric_or_minimum" not in question_modes and "numeric_recall" not in card_modes:
            additions.append("numeric_or_minimum")
    if "discrimination" not in question_modes | activity_modes | card_modes:
        additions.append("discrimination")
    if "scenario_application" not in question_modes | activity_modes:
        additions.append("scenario_application")
    if not ({"boundary_recall", "condition_boundary"} & (card_modes | question_modes)):
        if CONDITION_RE.search(source):
            additions.append("condition_or_exception_boundary")
    if quality_flags:
        additions.append("replacement_candidate")
    if len(question_modes | activity_modes | card_modes) < 4:
        additions.append("complementary_retrieval_mode")
    return list(dict.fromkeys(additions))


def build_packet(
    db: sqlite3.Connection,
    chapter: int,
    pass_number: int,
    source_db: Path,
) -> dict[str, Any]:
    packet = {
        "version": 2,
        "source_db": str(source_db),
        "scope": {"para_id": None, "chapter": chapter, "section": None},
        "authoring_rules": {
            "storage": "Write only the assigned numbered staging file.",
            "quality": (
                "Write substantive, self-contained, source-grounded items that add a distinct "
                "retrieval mode or replace a documented weak item."
            ),
            "avoid": [
                "paragraph-title trivia",
                "underspecified example checks",
                "manufactured phraseology errors from arbitrary values",
                "answer-position cues",
                "repeating an existing scenario in different words",
            ],
        },
        "paragraphs": fetch_paragraphs(
            db,
            para_id=None,
            chapter=chapter,
            section=None,
        ),
    }
    prior_payloads = [
        load_prior_pass(chapter, previous_pass)
        for previous_pass in range(1, pass_number)
    ]

    chapter_flags: Counter[str] = Counter()
    chapter_modes = {
        "questions": Counter(),
        "activities": Counter(),
        "flashcards": Counter(),
    }
    ranked: list[tuple[int, str]] = []
    for paragraph in packet.get("paragraphs", []):
        para_id = str(paragraph.get("para_id") or "")
        existing = paragraph.get("existing") if isinstance(paragraph.get("existing"), dict) else {}
        questions = list(existing.get("questions") or [])
        activities = list(existing.get("activities") or [])
        flashcards = list(existing.get("flashcards") or [])
        prior_counts = {"questions": 0, "activities": 0, "flashcards": 0}
        for prior_payload in prior_payloads:
            additions = staged_items(prior_payload, "questions", para_id)
            prior_counts["questions"] += len(additions)
            additions = staged_items(prior_payload, "activities", para_id)
            prior_counts["activities"] += len(additions)
            additions = staged_items(prior_payload, "flashcards", para_id)
            prior_counts["flashcards"] += len(additions)

        question_modes = Counter(question_mode(item) for item in questions)
        activity_modes = Counter(activity_mode(item) for item in activities)
        card_modes = Counter(card_mode(item) for item in flashcards)
        chapter_modes["questions"].update(question_modes)
        chapter_modes["activities"].update(activity_modes)
        chapter_modes["flashcards"].update(card_modes)

        flags: Counter[str] = Counter()
        for item in questions:
            flags.update(f"question:{flag}" for flag in question_flags(item))
        for item in activities:
            flags.update(f"activity:{flag}" for flag in activity_flags(item))
        for item in flashcards:
            flags.update(f"flashcard:{flag}" for flag in card_flags(item))
        chapter_flags.update(flags)

        preferred = additions_for_paragraph(
            paragraph,
            set(question_modes),
            set(activity_modes),
            set(card_modes),
            flags,
        )
        mode_diversity = len(set(question_modes) | set(activity_modes) | set(card_modes))
        score = 2 * len(preferred) + 3 * sum(flags.values()) + max(0, 6 - mode_diversity)
        if chapter in PRIORITY_CHAPTERS:
            score += 5
        if paragraph.get("has_visual") or SOURCE_USE_RE.search(normalize(paragraph.get("source_text"))):
            score += 4
        ranked.append((score, para_id))

        paragraph["pass_analysis"] = {
            "prior_pass_additions": prior_counts,
            "mode_counts": {
                "questions": dict(question_modes),
                "activities": dict(activity_modes),
                "flashcards": dict(card_modes),
            },
            "mode_diversity": mode_diversity,
            "legacy_quality_flags": dict(flags),
            "preferred_additions": preferred,
            "priority_score": score,
            "instruction": (
                "Review the complete source and all existing content. Add only a distinct, "
                "source-supported retrieval target or a clearly stronger replacement candidate."
            ),
        }

    ranked.sort(key=lambda item: (-item[0], item[1]))
    packet["pass_number"] = pass_number
    packet["pass_plan"] = {
        "objective": (
            "Increase source coverage and retrieval-mode diversity while repairing weak legacy "
            "patterns across all generation sources."
        ),
        "chapter_priority": "high" if chapter in PRIORITY_CHAPTERS else "standard",
        "portfolio_limits": {
            "maximum_question_scenario_share": 0.5,
            "maximum_activity_situation_action_share": 0.5,
            "strict_validator_warnings_allowed": 0,
        },
        "required_review": "Every paragraph in chapter order, including paragraphs receiving no additions.",
        "priority_paragraphs": [para_id for _, para_id in ranked[:25]],
        "chapter_mode_counts_before_pass": {
            family: dict(counts) for family, counts in chapter_modes.items()
        },
        "chapter_legacy_quality_flags": dict(chapter_flags),
        "long_term_scope": (
            "The same analysis is intended to cover the complete curriculum, including older "
            "curated and generated content; generation source is not a quality exemption."
        ),
    }
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pass-number", type=int, default=2)
    parser.add_argument("--chapters", default="1-14")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    if args.pass_number < 2:
        parser.error("pass-specific audit packets begin at pass 2")
    if not args.db.exists():
        parser.error(f"database not found: {args.db}")

    out_dir = args.out_dir or WORKSPACE / f"pass_{args.pass_number:02d}_packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    try:
        for chapter in parse_chapters(args.chapters):
            packet = build_packet(db, chapter, args.pass_number, args.db)
            output = out_dir / f"chapter_{chapter:02d}.json"
            output.write_text(
                json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(
                f"chapter {chapter:02d}: paragraphs={len(packet.get('paragraphs', []))} "
                f"priority={packet['pass_plan']['chapter_priority']} output={output}"
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
