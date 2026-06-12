#!/usr/bin/env python3
"""
Validate append-only question authoring batches before handoff.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"

QUESTION_TYPES = {"multiple_choice", "true_false", "fill_blank"}
ACTIVITY_CHOICE_KEYS = ("choices", "options")
UNDERSPECIFIED_PATTERNS = (
    re.compile(r"^\s*What is the rule\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*Is this an approved example\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*Is this approved(?: wording| phraseology)?\??\s*$", re.IGNORECASE),
    re.compile(r"scope or responsibility statement", re.IGNORECASE),
    re.compile(r"match(?:es)? the paragraph", re.IGNORECASE),
    re.compile(r"what is correct about\b", re.IGNORECASE),
    re.compile(r"\bthis paragraph\b", re.IGNORECASE),
    re.compile(
        r"^\s*(?:under|from|in)\s+(?:the\s+)?(?:paragraph\s+)?"
        r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
        re.IGNORECASE,
    ),
)
ARBITRARY_VALUE_PATTERNS = (
    re.compile(r"\bone word\b.*\bincorrect\b", re.IGNORECASE),
    re.compile(r"\bspot the error\b", re.IGNORECASE),
    re.compile(r"\bapproved example\b", re.IGNORECASE),
)
NEGATIVE_STEM_PATTERN = re.compile(
    r"\b(?:not|except|false|incorrect|least appropriate|does not|doesn't)\b",
    re.IGNORECASE,
)
QUESTION_LEAD_PATTERN = re.compile(
    r"^(?:what|when|where|who|which|how|why|identify|name|state|list|"
    r"select|choose|determine|give|describe|explain)\b",
    re.IGNORECASE,
)
DOCUMENT_LOCATION_PATTERN = re.compile(
    r"\b(?:under|from|in|paragraph|para|section)\s+(?:the\s+)?"
    r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
DOCUMENT_CROSS_REFERENCE_PATTERN = re.compile(
    r"\b(?:under|per|according to|apply|see|refer to|in accordance with)\s+"
    r"(?:the\s+)?(?:paragraph|para|section|chapter|note)?\s*"
    r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
PARAGRAPH_STRUCTURE_PATTERN = re.compile(
    r"\b(?:the|this)\s+(?:paragraph|section|rule)\s+"
    r"(?:provides|requires|states|says|permits|lists|does not provide)\b",
    re.IGNORECASE,
)
SPACING_BEFORE_PUNCTUATION_PATTERN = re.compile(r"\s+[,.?!;:]")
BROKEN_SCENARIO_TRANSITION_PATTERN = re.compile(r"[.?!]\s*,\s*(?:which|what|who|when|how)\b", re.IGNORECASE)


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: {message}")

    def warn(self, location: str, message: str) -> None:
        self.warnings.append(f"{location}: {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Top-level payload must be a JSON object.")
    return payload


def normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def load_existing_question_stems(db_path: Path) -> dict[str, set[str]]:
    if not db_path.exists():
        return {}
    db = sqlite3.connect(db_path)
    try:
        rows = db.execute("SELECT para_id, question_text FROM quiz_questions").fetchall()
    finally:
        db.close()
    existing: dict[str, set[str]] = defaultdict(set)
    for para_id, text in rows:
        existing[str(para_id)].add(normalize_text(text).lower())
    return existing


def validate_choices(
    reporter: Reporter,
    location: str,
    choices: Any,
    *,
    require_choices: bool,
    allow_single_correct_only: bool,
) -> tuple[int, int | None]:
    if not isinstance(choices, list) or not choices:
        if require_choices:
            reporter.error(location, "missing non-empty choices list")
        return 0, None

    seen: set[str] = set()
    correct_count = 0
    first_correct_index: int | None = None
    for idx, choice in enumerate(choices):
        choice_location = f"{location}.choices[{idx}]"
        if not isinstance(choice, dict):
            reporter.error(choice_location, "choice must be an object")
            continue
        text = normalize_text(choice.get("text") or choice.get("choice_text"))
        if not text:
            reporter.error(choice_location, "choice text is empty")
        if SPACING_BEFORE_PUNCTUATION_PATTERN.search(text):
            reporter.warn(choice_location, "choice text contains spacing before punctuation")
        if DOCUMENT_CROSS_REFERENCE_PATTERN.search(text):
            reporter.warn(
                choice_location,
                "choice text depends on a document cross-reference instead of stating the operational rule",
            )
        if PARAGRAPH_STRUCTURE_PATTERN.search(text):
            reporter.warn(
                choice_location,
                "choice text uses paragraph-structure wording instead of operational substance",
            )
        key = text.lower()
        if key in seen:
            reporter.error(choice_location, "duplicate choice text")
        seen.add(key)
        if bool(choice.get("is_correct")):
            correct_count += 1
            if first_correct_index is None:
                first_correct_index = idx

    if allow_single_correct_only and correct_count != 1:
        reporter.error(location, f"expected exactly one correct choice, found {correct_count}")
    elif not allow_single_correct_only and correct_count < 1:
        reporter.error(location, "expected at least one correct choice")
    return correct_count, first_correct_index


def validate_question(
    reporter: Reporter,
    para_id: str,
    idx: int,
    item: Any,
    existing_stems: dict[str, set[str]],
    seen_stems: set[str],
    first_correct_positions: list[int],
) -> None:
    location = f"questions.{para_id}.items[{idx}]"
    if not isinstance(item, dict):
        reporter.error(location, "question item must be an object")
        return

    text = normalize_text(item.get("question_text"))
    question_type = normalize_text(item.get("question_type") or "multiple_choice")
    explanation = normalize_text(item.get("explanation"))
    generation_source = normalize_text(item.get("generation_source"))

    if not text:
        reporter.error(location, "question_text is required")
    elif len(text) < 18:
        reporter.warn(location, "question_text is very short; check for missing context")
    if SPACING_BEFORE_PUNCTUATION_PATTERN.search(text):
        reporter.warn(location, "question text contains spacing before punctuation")
    if BROKEN_SCENARIO_TRANSITION_PATTERN.search(text):
        reporter.warn(location, "question text contains a broken scenario-to-question transition")
    if DOCUMENT_CROSS_REFERENCE_PATTERN.search(text):
        reporter.warn(
            location,
            "question text depends on a document cross-reference instead of operational context",
        )
    if PARAGRAPH_STRUCTURE_PATTERN.search(text):
        reporter.warn(
            location,
            "question text uses paragraph-structure wording instead of operational substance",
        )

    if question_type not in QUESTION_TYPES:
        reporter.error(location, f"unsupported question_type '{question_type}'")

    if not generation_source:
        reporter.warn(location, "generation_source missing; use question_agent")
    elif generation_source not in {"question_agent", "deepseek", "curated"}:
        reporter.warn(location, f"unexpected generation_source '{generation_source}'")

    difficulty = item.get("difficulty")
    if not isinstance(difficulty, int) or not 1 <= difficulty <= 5:
        reporter.error(location, "difficulty must be an integer from 1 to 5")

    if not explanation:
        reporter.error(location, "explanation is required")
    elif len(explanation.split()) < 8:
        reporter.warn(location, "explanation is too thin to teach the rule")
    elif question_type == "multiple_choice" and len(explanation.split()) < 16:
        reporter.warn(
            location,
            "multiple-choice explanation may not identify the controlling principle and strongest distractor",
        )

    stem_key = text.lower()
    if stem_key:
        if stem_key in seen_stems:
            reporter.error(location, "duplicate question_text within this batch")
        seen_stems.add(stem_key)
        if stem_key in existing_stems.get(para_id, set()):
            reporter.warn(location, "question_text already exists in the database")

    for pattern in UNDERSPECIFIED_PATTERNS:
        if pattern.search(text):
            reporter.warn(location, f"possibly underspecified stem: {pattern.pattern}")
            break

    for pattern in ARBITRARY_VALUE_PATTERNS:
        if pattern.search(text):
            reporter.warn(location, "check that this is not manufacturing an error from arbitrary example values")
            break

    if NEGATIVE_STEM_PATTERN.search(text):
        reporter.warn(
            location,
            "negative stem; use NOT/EXCEPT only when recognizing the exclusion is the intended skill",
        )

    choices = item.get("choices")
    if question_type == "fill_blank":
        validate_choices(
            reporter,
            location,
            choices,
            require_choices=True,
            allow_single_correct_only=False,
        )
        if isinstance(choices, list) and len(choices) > 4:
            reporter.warn(location, "fill_blank has many accepted answers; check ambiguity")
    elif question_type == "true_false":
        correct_count, first_correct = validate_choices(
            reporter,
            location,
            choices,
            require_choices=True,
            allow_single_correct_only=True,
        )
        if isinstance(choices, list) and len(choices) != 2:
            reporter.error(location, "true_false should have exactly two choices")
        if correct_count == 1 and first_correct is not None:
            first_correct_positions.append(first_correct)
    else:
        correct_count, first_correct = validate_choices(
            reporter,
            location,
            choices,
            require_choices=True,
            allow_single_correct_only=True,
        )
        if isinstance(choices, list) and len(choices) < 3:
            reporter.warn(location, "multiple_choice should usually have at least three choices")
        if correct_count == 1 and first_correct is not None:
            first_correct_positions.append(first_correct)


def validate_activity(
    reporter: Reporter,
    para_id: str,
    idx: int,
    item: Any,
    first_correct_positions: list[int],
) -> None:
    location = f"activities.{para_id}.items[{idx}]"
    if not isinstance(item, dict):
        reporter.error(location, "activity item must be an object")
        return

    activity_type = normalize_text(item.get("activity_type"))
    if not activity_type:
        reporter.error(location, "activity_type is required")

    generation_source = normalize_text(item.get("generation_source"))
    if not generation_source:
        reporter.warn(location, "generation_source missing; use question_agent")

    difficulty = item.get("difficulty")
    if not isinstance(difficulty, int) or not 1 <= difficulty <= 5:
        reporter.error(location, "difficulty must be an integer from 1 to 5")

    prompt_text = " ".join(
        normalize_text(item.get(key))
        for key in ("instruction", "question_text", "situation", "prompt")
        if item.get(key)
    )
    if len(prompt_text.split()) < 8:
        reporter.warn(location, "activity prompt may be too thin or underspecified")
    if SPACING_BEFORE_PUNCTUATION_PATTERN.search(prompt_text):
        reporter.warn(location, "activity prompt contains spacing before punctuation")
    if PARAGRAPH_STRUCTURE_PATTERN.search(prompt_text):
        reporter.warn(
            location,
            "activity prompt uses paragraph-structure wording instead of operational substance",
        )
    if DOCUMENT_CROSS_REFERENCE_PATTERN.search(prompt_text):
        reporter.warn(
            location,
            "activity prompt depends on a document cross-reference instead of operational context",
        )

    for key in ACTIVITY_CHOICE_KEYS:
        choices = item.get(key)
        if isinstance(choices, list):
            _, first_correct = validate_choices(
                reporter,
                f"{location}.{key}",
                choices,
                require_choices=False,
                allow_single_correct_only=True,
            )
            if first_correct is not None:
                first_correct_positions.append(first_correct)
                correct_text = normalize_text(
                    choices[first_correct].get("text")
                    or choices[first_correct].get("choice_text")
                )
                distractor_lengths = [
                    max(
                        1,
                        len(normalize_text(
                            choice.get("text") or choice.get("choice_text")
                        ).split()),
                    )
                    for choice_idx, choice in enumerate(choices)
                    if isinstance(choice, dict) and choice_idx != first_correct
                ]
                if distractor_lengths:
                    correct_words = len(correct_text.split())
                    distractor_average = (
                        sum(distractor_lengths) / len(distractor_lengths)
                    )
                    if correct_words >= 6 and correct_words > distractor_average * 1.8:
                        reporter.warn(
                            location,
                            "correct choice is much longer than the distractors and may reveal itself",
                        )

    explanation = normalize_text(item.get("explanation") or item.get("feedback"))
    if not explanation:
        reporter.warn(location, "activity has no explanation or feedback")

    if activity_type not in {"source_lookup", "source_use"}:
        if DOCUMENT_LOCATION_PATTERN.search(prompt_text):
            reporter.warn(
                location,
                "activity relies on paragraph-number scaffolding outside an explicit source-use task",
            )

    if re.search(r"(?:situation|scenario|decision)", activity_type, re.IGNORECASE):
        context = " ".join(
            normalize_text(item.get(key))
            for key in ("situation", "clearance", "lookup_context", "question_text")
            if item.get(key)
        )
        if len(context.split()) < 12:
            reporter.warn(
                location,
                "scenario/decision activity may not provide enough operational facts",
            )


def validate_flashcard(reporter: Reporter, para_id: str, idx: int, item: Any, seen_cards: set[tuple[str, str, str]]) -> None:
    location = f"flashcards.{para_id}.items[{idx}]"
    if not isinstance(item, dict):
        reporter.error(location, "flashcard item must be an object")
        return

    front = normalize_text(item.get("front"))
    back = normalize_text(item.get("back"))
    card_type = normalize_text(item.get("card_type") or "concept")

    if not front:
        reporter.error(location, "front is required")
    if not back:
        reporter.error(location, "back is required")
    if SPACING_BEFORE_PUNCTUATION_PATTERN.search(front):
        reporter.warn(location, "flashcard cue contains spacing before punctuation")
    if SPACING_BEFORE_PUNCTUATION_PATTERN.search(back):
        reporter.warn(location, "flashcard answer contains spacing before punctuation")
    if PARAGRAPH_STRUCTURE_PATTERN.search(front):
        reporter.warn(
            location,
            "flashcard cue uses paragraph-structure wording instead of operational substance",
        )
    if DOCUMENT_CROSS_REFERENCE_PATTERN.search(front):
        reporter.warn(
            location,
            "flashcard cue depends on a document cross-reference instead of operational context",
        )
    if front and back and front.lower() == back.lower():
        reporter.warn(location, "front and back are identical")
    if front and len(front.split()) < 4 and not (
        "?" in front or QUESTION_LEAD_PATTERN.search(front)
    ):
        reporter.warn(
            location,
            "flashcard front is a context-light label rather than an explicit retrieval cue",
        )
    if back and len(back.split()) < 4:
        reporter.warn(location, "flashcard answer is very short; check whether the cue is unambiguous")
    if back and len(back.split()) > 50:
        reporter.warn(location, "flashcard answer may overload a single retrieval target")
    if "reverse" in card_type.lower() and back and not (
        "?" in back or QUESTION_LEAD_PATTERN.search(back)
    ):
        reporter.warn(
            location,
            "reverse card does not provide a clear question on the reverse side",
        )
    if card_type.lower() not in {"reference", "source_reference"}:
        if DOCUMENT_LOCATION_PATTERN.search(front):
            reporter.warn(
                location,
                "flashcard cue relies on paragraph-number scaffolding",
            )

    key = (para_id, card_type.lower(), front.lower())
    if key in seen_cards:
        reporter.error(location, "duplicate flashcard key within this batch")
    seen_cards.add(key)

    if not normalize_text(item.get("generation_source")):
        reporter.warn(location, "generation_source missing; use question_agent")


def validate_para_map(
    reporter: Reporter,
    payload: dict[str, Any],
    key: str,
    item_validator,
    *validator_args,
) -> None:
    section = payload.get(key, {})
    if section is None:
        return
    if not isinstance(section, dict):
        reporter.error(key, "must be an object keyed by para_id")
        return
    for para_id, override in section.items():
        location = f"{key}.{para_id}"
        if not isinstance(override, dict):
            reporter.error(location, "override must be an object")
            continue
        items = override.get("items", [])
        if not isinstance(items, list):
            reporter.error(location, "items must be a list")
            continue
        if not items:
            reporter.warn(location, "items list is empty")
        for idx, item in enumerate(items):
            item_validator(reporter, str(para_id), idx, item, *validator_args)


def report_answer_position_bias(reporter: Reporter, positions: list[int]) -> None:
    if len(positions) < 4:
        return
    counts = Counter(positions)
    first_rate = counts.get(0, 0) / len(positions)
    if first_rate == 1:
        reporter.error("answer_order", "all correct answers are first; vary answer order")
    elif first_rate >= 0.7:
        reporter.warn("answer_order", f"{first_rate:.0%} of correct answers are first; check answer-order bias")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat quality warnings as validation failures.",
    )
    args = parser.parse_args()

    payload = load_json(args.path)
    reporter = Reporter()
    existing_stems = load_existing_question_stems(args.db)
    seen_stems: set[str] = set()
    seen_cards: set[tuple[str, str, str]] = set()
    first_correct_positions: list[int] = []

    allowed_top_level = {"questions", "activities", "flashcards"}
    for key in payload:
        if key not in allowed_top_level:
            reporter.warn(key, "unexpected top-level key")

    validate_para_map(
        reporter,
        payload,
        "questions",
        validate_question,
        existing_stems,
        seen_stems,
        first_correct_positions,
    )
    validate_para_map(
        reporter,
        payload,
        "activities",
        validate_activity,
        first_correct_positions,
    )
    validate_para_map(
        reporter,
        payload,
        "flashcards",
        validate_flashcard,
        seen_cards,
    )
    report_answer_position_bias(reporter, first_correct_positions)

    for warning in reporter.warnings:
        print(f"WARN: {warning}")
    for error in reporter.errors:
        print(f"ERROR: {error}")

    if reporter.errors or (args.strict and reporter.warnings):
        print(f"\nValidation failed: {len(reporter.errors)} error(s), {len(reporter.warnings)} warning(s).")
        return 1

    print(f"Validation passed: {len(reporter.warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
