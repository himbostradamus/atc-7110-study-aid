#!/usr/bin/env python3
"""Validate a chapter remediation manifest against its stable-ID packet."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ACTIONS = {"replace", "remove", "split"}
ENTITY_TYPES = {"question", "activity", "flashcard"}
SEVERITIES = {"critical", "major", "minor", "suggestion"}
NON_CONTENT_CATEGORIES = {
    "answer_order",
    "answer_position",
    "answer_position_bias",
    "correct_answer_first",
}
QUESTION_TYPES = {"multiple_choice", "true_false", "fill_blank"}
LOCATION_RE = re.compile(
    r"\b(?:"
    r"under\s+(?:the\s+)?(?:(?:paragraph|para|section)\s+)?"
    r"|(?:from|in)\s+(?:the\s+)?(?:paragraph|para|section)\s+"
    r"|(?:paragraph|para|section)\s+"
    r")\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
PARAGRAPH_ID_RE = re.compile(
    r"\b(?:\u00a7\s*)?\d{1,2}(?:[-\u2212]\d+){2,}(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
GENERIC_REFERENCE_RE = re.compile(
    r"\b(?:this|the)\s+(?:paragraph|section|rule|material|example)\b",
    re.IGNORECASE,
)
DOCUMENT_TRIVIA_RE = re.compile(
    r"^\s*item\s+\d+\b"
    r"|\bwhich\s+(?:table|paragraph|section|item)\b"
    r"|\bapply\s+\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
REFERENCE_RETRIEVAL_RE = re.compile(
    r"\bwhere\s+does\s+\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\s+direct\b"
    r"|\bwhere\s+(?:is|are)\s+.+\s+(?:standards|definitions)\s+found\b",
    re.IGNORECASE,
)
RATIONALE_CLAIM_RE = re.compile(
    r"\b(?:"
    r"because|therefore|thus|so\s+that|in\s+order\s+to|"
    r"designed\s+(?:to|with)|ensur(?:e|es|ing)|prevent(?:s|ing)?|"
    r"maintain(?:s|ing)?\s+situational\s+awareness|"
    r"safety\s+and\s+.+?\s+(?:always\s+)?take\s+priority|"
    r"sector\s+stability"
    r")\b",
    re.IGNORECASE,
)


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: {message}")

    def warn(self, location: str, message: str) -> None:
        self.warnings.append(f"{location}: {message}")


def load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"Top-level JSON in {path} must be an object.")
    return payload


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def has_paragraph_location(value: object) -> bool:
    text = normalize(value)
    return bool(LOCATION_RE.search(text) or PARAGRAPH_ID_RE.search(text))


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalized_choices(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    choices = []
    for choice in value:
        if not isinstance(choice, dict):
            continue
        choices.append({
            "text": normalize(choice.get("text") or choice.get("choice_text")),
            "is_correct": choice.get("is_correct") is True,
        })
    return sorted(choices, key=lambda choice: (choice["text"], choice["is_correct"]))


def normalized_activity_content(value: object) -> object:
    if not isinstance(value, dict):
        return value
    content = {
        key: child
        for key, child in value.items()
        if key not in {"generation_source", "generation_src"}
    }
    for key in ("choices", "options"):
        if key in content:
            content[key] = normalized_choices(content[key])
    return content


def replacement_only_reorders_choices(
    entity_type: str,
    original: dict[str, Any],
    replacement: object,
) -> bool:
    if not isinstance(replacement, dict):
        return False
    if entity_type == "question":
        original_shape = {
            "question_text": normalize(original.get("question_text")),
            "question_type": normalize(original.get("question_type")),
            "explanation": normalize(original.get("explanation")),
            "difficulty": int(original.get("difficulty") or 2),
            "choices": normalized_choices(original.get("choices")),
        }
        replacement_shape = {
            "question_text": normalize(replacement.get("question_text")),
            "question_type": normalize(replacement.get("question_type")),
            "explanation": normalize(replacement.get("explanation")),
            "difficulty": int(replacement.get("difficulty") or 2),
            "choices": normalized_choices(replacement.get("choices")),
        }
        return canonical_json(original_shape) == canonical_json(replacement_shape)
    if entity_type == "activity":
        original_shape = {
            "activity_type": normalize(original.get("activity_type")),
            "difficulty": int(original.get("difficulty") or 2),
            "content": normalized_activity_content(original.get("content")),
        }
        replacement_shape = {
            "activity_type": normalize(replacement.get("activity_type")),
            "difficulty": int(replacement.get("difficulty") or 2),
            "content": normalized_activity_content(replacement.get("content")),
        }
        return canonical_json(original_shape) == canonical_json(replacement_shape)
    return False


def packet_inventory(
    packet: dict[str, Any],
) -> tuple[
    dict[str, set[str]],
    dict[str, tuple[str, str]],
    dict[str, dict[str, Any]],
]:
    inventory = {entity_type: set() for entity_type in ENTITY_TYPES}
    lookup: dict[str, tuple[str, str]] = {}
    originals: dict[str, dict[str, Any]] = {}
    for paragraph in packet.get("paragraphs", []):
        para_id = str(paragraph.get("para_id") or "")
        targets = paragraph.get("targets") or {}
        for entity_type in ENTITY_TYPES:
            for item in targets.get(entity_type, []):
                item_id = str(item.get("id") or "")
                if item_id:
                    inventory[entity_type].add(item_id)
                    lookup[item_id] = (entity_type, para_id)
                    originals[item_id] = item
    return inventory, lookup, originals


def validate_choices(
    reporter: Reporter,
    location: str,
    choices: object,
    question_type: str,
) -> None:
    if not isinstance(choices, list) or not choices:
        reporter.error(location, "replacement requires a non-empty choices array")
        return
    normalized = []
    correct = 0
    for index, choice in enumerate(choices):
        choice_location = f"{location}.choices[{index}]"
        if not isinstance(choice, dict):
            reporter.error(choice_location, "choice must be an object")
            continue
        text = normalize(choice.get("text"))
        if not text:
            reporter.error(choice_location, "choice text is required")
        normalized.append(text.lower())
        correct += int(choice.get("is_correct") is True)
    if len(normalized) != len(set(normalized)):
        reporter.error(location, "replacement choices contain duplicate text")
    if question_type == "fill_blank":
        if correct < 1:
            reporter.error(location, "fill_blank requires at least one accepted answer")
    elif correct != 1:
        reporter.error(location, f"expected exactly one correct answer, found {correct}")
    if question_type == "true_false" and len(choices) != 2:
        reporter.error(location, "true_false requires exactly two choices")
    if question_type == "multiple_choice" and len(choices) < 3:
        reporter.error(location, "multiple_choice requires at least three choices")


def reject_unsupported_rationale(
    reporter: Reporter,
    location: str,
    explanation: str,
    source_basis: str,
) -> None:
    if (
        RATIONALE_CLAIM_RE.search(explanation)
        and not RATIONALE_CLAIM_RE.search(source_basis)
    ):
        reporter.error(
            location,
            "explanation adds a purpose, consequence, safety rationale, or "
            "system-design claim not stated in source_basis",
        )


def validate_question(
    reporter: Reporter,
    location: str,
    item: object,
    source_basis: str,
) -> None:
    if not isinstance(item, dict):
        reporter.error(location, "question replacement must be an object")
        return
    text = normalize(item.get("question_text"))
    question_type = normalize(item.get("question_type") or "multiple_choice")
    explanation = normalize(item.get("explanation"))
    if not text:
        reporter.error(location, "question_text is required")
    if question_type not in QUESTION_TYPES:
        reporter.error(location, f"unsupported question_type '{question_type}'")
    if not isinstance(item.get("difficulty"), int) or not 1 <= item["difficulty"] <= 5:
        reporter.error(location, "difficulty must be an integer from 1 to 5")
    if len(explanation.split()) < 10:
        reporter.error(location, "explanation must teach the controlling principle")
    if has_paragraph_location(text):
        reporter.error(location, "replacement still uses paragraph-location scaffolding")
    if has_paragraph_location(explanation):
        reporter.error(location, "explanation exposes paragraph-location scaffolding")
    if GENERIC_REFERENCE_RE.search(text):
        reporter.warn(location, "replacement still uses a generic document reference")
    if DOCUMENT_TRIVIA_RE.search(text):
        reporter.error(location, "replacement still tests document structure instead of operational substance")
    if REFERENCE_RETRIEVAL_RE.search(text):
        reporter.error(location, "replacement asks for a reference location instead of applying the rule")
    reject_unsupported_rationale(reporter, location, explanation, source_basis)
    validate_choices(reporter, location, item.get("choices"), question_type)


def validate_flashcard(reporter: Reporter, location: str, item: object) -> None:
    if not isinstance(item, dict):
        reporter.error(location, "flashcard replacement must be an object")
        return
    front = normalize(item.get("front"))
    back = normalize(item.get("back"))
    card_type = normalize(item.get("card_type"))
    if not front or not back or not card_type:
        reporter.error(location, "front, back, and card_type are required")
    is_reference = card_type in {"reference", "source_reference"}
    if has_paragraph_location(front) and not is_reference:
        reporter.error(location, "replacement still uses paragraph-location scaffolding")
    if has_paragraph_location(back) and not is_reference:
        reporter.error(location, "replacement back exposes paragraph-location scaffolding")
    if DOCUMENT_TRIVIA_RE.search(front):
        reporter.error(location, "replacement still tests document structure instead of operational substance")
    if REFERENCE_RETRIEVAL_RE.search(front):
        reporter.error(location, "replacement asks for a reference location instead of recalling the rule")
    if len(back.split()) > 60:
        reporter.warn(location, "replacement back may contain too many retrieval targets")
    if "reverse" in card_type.lower() and "?" not in back:
        reporter.warn(location, "reverse card back may not function as a reverse prompt")


def activity_choices(payload: dict[str, Any]) -> object:
    return payload.get("choices") if "choices" in payload else payload.get("options")


def activity_choice_type(choices: object) -> str:
    if not isinstance(choices, list):
        return "multiple_choice"
    labels = {
        normalize(choice.get("text")).lower()
        for choice in choices
        if isinstance(choice, dict)
    }
    return "true_false" if labels == {"true", "false"} else "multiple_choice"


def validate_activity(
    reporter: Reporter,
    location: str,
    item: object,
    source_basis: str,
) -> None:
    if not isinstance(item, dict):
        reporter.error(location, "activity replacement must be an object")
        return
    activity_type = normalize(item.get("activity_type"))
    content = item.get("content")
    if not activity_type:
        reporter.error(location, "activity_type is required")
    if not isinstance(item.get("difficulty"), int) or not 1 <= item["difficulty"] <= 5:
        reporter.error(location, "difficulty must be an integer from 1 to 5")
    if not isinstance(content, dict) or not content:
        reporter.error(location, "content must be a non-empty object")
        return
    explanation = normalize(content.get("explanation"))
    if len(explanation.split()) < 10:
        reporter.error(location, "activity explanation must teach the controlling principle")
    prompt = normalize(" ".join(
        str(content.get(key) or "")
        for key in (
            "situation", "clearance", "lookup_context", "para_context",
            "question_text", "task", "instruction",
        )
    ))
    if has_paragraph_location(prompt):
        reporter.error(location, "replacement still uses paragraph-location scaffolding")
    if has_paragraph_location(explanation):
        reporter.error(location, "activity explanation exposes paragraph-location scaffolding")
    if DOCUMENT_TRIVIA_RE.search(prompt):
        reporter.error(location, "replacement still tests document structure instead of operational substance")
    reject_unsupported_rationale(reporter, location, explanation, source_basis)
    choices = activity_choices(content)
    if choices is not None:
        validate_choices(
            reporter,
            location,
            choices,
            activity_choice_type(choices),
        )


def validate_replacement(
    reporter: Reporter,
    location: str,
    entity_type: str,
    replacement: object,
    action: str,
    source_basis: str,
) -> None:
    replacements = replacement if action == "split" else [replacement]
    if action == "split" and (not isinstance(replacements, list) or len(replacements) < 2):
        reporter.error(location, "split requires an array of at least two replacements")
        return
    if not isinstance(replacements, list):
        reporter.error(location, "replacement shape is invalid")
        return
    for index, item in enumerate(replacements):
        item_location = f"{location}[{index}]" if action == "split" else location
        if entity_type == "question":
            validate_question(reporter, item_location, item, source_basis)
        elif entity_type == "activity":
            validate_activity(reporter, item_location, item, source_basis)
        elif entity_type == "flashcard":
            validate_flashcard(reporter, item_location, item)


def validate(packet: dict[str, Any], manifest: dict[str, Any]) -> Reporter:
    reporter = Reporter()
    inventory, lookup, originals = packet_inventory(packet)
    chapter = packet.get("chapter")
    if manifest.get("version") != 1:
        reporter.error("version", "expected version 1")
    if manifest.get("audit_type") != "chapter_content_remediation":
        reporter.error("audit_type", "expected chapter_content_remediation")
    if manifest.get("chapter") != chapter:
        reporter.error("chapter", f"expected chapter {chapter}")
    if manifest.get("status") != "complete":
        reporter.error("status", "manifest must be complete")

    reviewed = manifest.get("reviewed_item_ids")
    if not isinstance(reviewed, dict):
        reporter.error("reviewed_item_ids", "must be an object grouped by entity type")
        reviewed = {}
    for entity_type in ENTITY_TYPES:
        values = reviewed.get(entity_type)
        if not isinstance(values, list):
            reporter.error(f"reviewed_item_ids.{entity_type}", "must be an array")
            values = []
        value_set = {str(value) for value in values}
        if len(values) != len(value_set):
            reporter.error(f"reviewed_item_ids.{entity_type}", "contains duplicate IDs")
        missing = inventory[entity_type] - value_set
        foreign = value_set - inventory[entity_type]
        if missing:
            reporter.error(
                f"reviewed_item_ids.{entity_type}",
                f"missing {len(missing)} target IDs",
            )
        if foreign:
            reporter.error(
                f"reviewed_item_ids.{entity_type}",
                f"contains {len(foreign)} foreign IDs",
            )

    decisions = manifest.get("decisions")
    if not isinstance(decisions, list):
        reporter.error("decisions", "must be an array")
        decisions = []
    seen = set()
    action_counts = Counter()
    removal_counts = Counter()
    for index, decision in enumerate(decisions):
        location = f"decisions[{index}]"
        if not isinstance(decision, dict):
            reporter.error(location, "decision must be an object")
            continue
        item_id = str(decision.get("item_id") or "")
        entity_type = str(decision.get("entity_type") or "")
        para_id = str(decision.get("para_id") or "")
        action = str(decision.get("action") or "")
        if item_id in seen:
            reporter.error(location, "duplicate decision for item_id")
        seen.add(item_id)
        expected = lookup.get(item_id)
        if not expected:
            reporter.error(location, "item_id is not a target in the assigned packet")
        elif expected != (entity_type, para_id):
            reporter.error(
                location,
                f"item identity mismatch; expected {expected[0]} in {expected[1]}",
            )
        if entity_type not in ENTITY_TYPES:
            reporter.error(location, f"unsupported entity_type '{entity_type}'")
        if action not in ACTIONS:
            reporter.error(location, f"unsupported action '{action}'")
        else:
            action_counts[action] += 1
            if action == "remove":
                removal_counts[entity_type] += 1
        if decision.get("severity") not in SEVERITIES:
            reporter.error(location, "invalid severity")
        categories = decision.get("categories")
        if not isinstance(categories, list) or not categories:
            reporter.error(location, "categories must be a non-empty array")
        elif (
            action == "replace"
            and set(categories).issubset(NON_CONTENT_CATEGORIES)
        ):
            reporter.error(
                location,
                "answer position alone is not a content defect; runtime already shuffles choices",
            )
        if len(normalize(decision.get("problem")).split()) < 5:
            reporter.error(location, "problem must explain the defect")
        if len(normalize(decision.get("source_basis")).split()) < 5:
            reporter.error(location, "source_basis must state the controlling source idea")
        if action in {"replace", "split"}:
            if "replacement" not in decision:
                reporter.error(location, f"{action} requires replacement")
            else:
                validate_replacement(
                    reporter,
                    f"{location}.replacement",
                    entity_type,
                    decision["replacement"],
                    action,
                    normalize(decision.get("source_basis")),
                )
                if (
                    action == "replace"
                    and item_id in originals
                    and replacement_only_reorders_choices(
                        entity_type,
                        originals[item_id],
                        decision["replacement"],
                    )
                ):
                    reporter.error(
                        location,
                        "replacement changes only stored choice order; runtime already shuffles choices",
                    )
        elif action == "remove" and "replacement" in decision:
            reporter.warn(location, "remove decision ignores replacement")

    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        reporter.error("summary", "must be an object")
    else:
        guidance = summary.get("generation_guidance")
        if not isinstance(guidance, list) or not guidance:
            reporter.error("summary.generation_guidance", "must contain guidance for the next generation pass")

    if decisions and action_counts["replace"] + action_counts["split"] == 0:
        reporter.warn("decisions", "all interventions are removals; verify useful content was not discarded")
    for entity_type, target_ids in inventory.items():
        target_count = len(target_ids)
        removed = removal_counts[entity_type]
        if target_count >= 10 and removed > max(5, target_count * 0.25):
            reporter.error(
                f"decisions.{entity_type}",
                f"removes {removed} of {target_count} targets; bulk deletion requires manual review",
            )
    return reporter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    packet = load_object(args.packet)
    manifest = load_object(args.manifest)
    reporter = validate(packet, manifest)
    for warning in reporter.warnings:
        print(f"WARNING: {warning}")
    for error in reporter.errors:
        print(f"ERROR: {error}")
    print(
        f"Validation: {len(reporter.errors)} error(s), "
        f"{len(reporter.warnings)} warning(s)"
    )
    return 1 if reporter.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
