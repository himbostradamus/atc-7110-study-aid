#!/usr/bin/env python3
"""Normalize staged remediation manifests without touching live curriculum."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUTS = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "remediation" / "outputs"
)
PARA_ID = r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?"
LEADING_LOCATION_RE = re.compile(
    rf"(?i)(^|(?<=[.!?])\s+)"
    rf"(?:under|according\s+to|per)\s+"
    rf"(?:the\s+)?(?:(?:paragraph|para|section)\s+)?{PARA_ID}"
    rf"(?:[a-z]\d*)?\s*,?\s*"
)
TRAILING_LOCATION_RE = re.compile(
    rf"(?i)\s+(?:under|according\s+to|per)\s+"
    rf"(?:the\s+)?(?:(?:paragraph|para|section)\s+)?{PARA_ID}"
    rf"(?:[a-z]\d*)?(?:\s+note)?(?=[?.!,;:])"
)
CONTENT_REWRITES: dict[str, dict[str, object]] = {
    "b057a0e9-917c-4d4a-98af-34fdb2cde2ca": {
        "question_text": "During nonradar coordination, when must longitudinal separation information be included?",
        "explanation": (
            "Include the longitudinal separation being used when aircraft at the same altitude "
            "will have less than 10 minutes separation at the facilities' boundary, unless an "
            "LOA specifies otherwise."
        ),
    },
    "5767c573-1dca-44f7-a321-649c94e9036a": {
        "question_text": "Which information is NOT required for a scheduled air carrier?",
        "explanation": (
            "The ETA at the destination airport is not required for military or scheduled air "
            "carrier aircraft. Aircraft identification, assigned altitude, and true airspeed "
            "remain required coordination information."
        ),
    },
    "aec34547-fc6b-4bf0-87e4-7a715d7795aa": {
        "front": (
            "During nonradar coordination, what separation triggers mandatory inclusion of "
            "longitudinal separation information?"
        ),
    },
    "455c2674-71e6-406e-8739-e809ccc0aeac": {
        "question_text": "When may a horizontal line be drawn through an altitude being vacated?",
        "explanation": (
            "Draw the horizontal line only after the aircraft reports or valid Mode C shows it "
            "leaving the altitude. Issuing the climb or descent clearance alone is not enough."
        ),
    },
    "474eab7c-c361-4051-9097-59f9076b06d7": {
        "question_text": (
            "When spelling the letter J in radiotelephony, which pronunciation is prescribed?"
        ),
        "explanation": (
            "The ICAO radiotelephony alphabet prescribes JULIETT for the letter J. Exact "
            "phonetic words reduce ambiguity when spelling identifiers and names by radio."
        ),
        "choices": [
            {"text": "Jupiter", "is_correct": False},
            {"text": "Juliett", "is_correct": True},
            {"text": "Juliet", "is_correct": False},
            {"text": "June", "is_correct": False},
        ],
    },
    "dc3977f3-cd66-43a1-9fa9-b8d52f823f00": {
        "question_text": (
            "An NRS waypoint uses the FIR letter, FIR subset letter, latitude increment, and "
            "longitude increment. Which is a correctly spoken example?"
        ),
        "explanation": (
            "An NRS waypoint is spoken as the FIR letter, FIR subset letter, latitude increment, "
            "and longitude increment. 'Kilo Delta Three Four Uniform' follows that format."
        ),
    },
    "eedf7c10-064f-4ed2-aff8-1f1ede4b93dd": {
        "instruction": "Choose the required controller response to the volcanic ash encounter.",
    },
    "ad6935c9-0751-452c-a7dc-0dc5ce617541": {
        "instruction": "Choose the required response to the VFR pilot requesting radar assistance.",
    },
    "764379de-2a81-4237-88a0-670452549355": {
        "front": (
            "For an arriving VFR aircraft using approach control, what landing information "
            "must be issued before the aircraft contacts the tower?"
        ),
        "back": (
            "Issue wind, runway, and altimeter information unless properly covered by ATIS or "
            "the pilot reports having the numbers; traffic information as workload permits; "
            "and the time or place to contact the tower."
        ),
        "card_type": "procedure",
    },
    "e72be373-1a96-4a86-ba9f-c04f1f263acf": {
        "front": (
            "When VFR aircraft must hold at the same visual holding fix, what must the "
            "controller provide?"
        ),
        "back": (
            "Use a prominent, easily recognized geographical fix, preferably a charted VFR "
            "checkpoint, and issue traffic information about the other aircraft holding there."
        ),
        "card_type": "procedure",
    },
    "ce2a34d5-dc9c-4662-b1b1-0ed74185dffc": {
        "front": "What vertical separation rules apply in the North Atlantic ICAO Region?",
        "back": (
            "Apply the standard IFR altitude assignment and verification vertical separation "
            "rules."
        ),
        "card_type": "procedure",
    },
    "3b6d1545-336b-4859-8b58-eafa0cd008c6": {
        "front": "What vertical separation rules apply in the Caribbean ICAO Region?",
        "back": (
            "Apply the standard IFR altitude assignment and verification vertical separation "
            "rules."
        ),
        "card_type": "procedure",
    },
    "76b29633-5ae8-482d-bcb8-92e051324e44": {
        "front": "What vertical separation rules apply in the Pacific ICAO Region?",
        "back": (
            "Apply the standard IFR altitude assignment and verification vertical separation "
            "rules."
        ),
        "card_type": "procedure",
    },
    "5ff559f4-9b28-4d17-9bcb-a33f0fcb14f8": {
        "front": "What vertical separation rules apply in the North American-Arctic CTA?",
        "back": (
            "Apply the standard IFR altitude assignment and verification vertical separation "
            "rules plus facility directives governing transitions between flight levels and "
            "metric altitudes."
        ),
        "card_type": "procedure",
    },
    "727b49bc-d049-4ff8-9fd9-f399021eec5d": {
        "question_text": (
            "A pilot does not say \"Mayday\" or \"Pan-Pan,\" but the report indicates an "
            "emergency or urgent condition. How should the controller respond?"
        ),
        "explanation": (
            "Treat the situation as an emergency when the reported circumstances indicate one, "
            "even if the pilot does not use the formal distress or urgency signal words."
        ),
        "choices": [
            {
                "text": "Wait for the pilot to use the formal signal words before taking action.",
                "is_correct": False,
            },
            {
                "text": "Handle the situation as an emergency based on the reported circumstances.",
                "is_correct": True,
            },
            {
                "text": "Treat it only as an urgency condition unless the pilot repeats Mayday three times.",
                "is_correct": False,
            },
            {
                "text": "Transfer the aircraft to another frequency for an emergency determination.",
                "is_correct": False,
            },
        ],
    },
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_location_scaffold(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = LEADING_LOCATION_RE.sub(lambda match: match.group(1), value)
    cleaned = TRAILING_LOCATION_RE.sub("", cleaned)
    cleaned = normalize_space(cleaned)
    cleaned = re.sub(
        r"(?<=[.!?])\s+([a-z])",
        lambda match: f" {match.group(1).upper()}",
        cleaned,
    )
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def choice_list(entity_type: str, replacement: dict[str, Any]) -> list[dict[str, Any]] | None:
    if entity_type == "question":
        choices = replacement.get("choices")
    elif entity_type == "activity":
        content = replacement.get("content")
        if not isinstance(content, dict):
            return None
        choices = content.get("choices")
        if choices is None:
            choices = content.get("options")
    else:
        return None
    return choices if isinstance(choices, list) else None


def balance_choice_position(
    entity_type: str,
    item_id: str,
    replacement_index: int,
    replacement: dict[str, Any],
) -> bool:
    choices = choice_list(entity_type, replacement)
    if not choices or len(choices) < 2:
        return False
    correct_indexes = [
        index for index, choice in enumerate(choices)
        if isinstance(choice, dict) and choice.get("is_correct") is True
    ]
    if len(correct_indexes) != 1:
        return False
    digest = hashlib.sha256(
        f"{item_id}:{replacement_index}".encode("utf-8")
    ).digest()
    target = digest[0] % len(choices)
    current = correct_indexes[0]
    if current == target:
        return False
    correct_choice = choices.pop(current)
    choices.insert(target, correct_choice)
    for index, choice in enumerate(choices):
        if isinstance(choice, dict) and "sort_order" in choice:
            choice["sort_order"] = index
    return True


def normalize_replacement(entity_type: str, replacement: dict[str, Any]) -> int:
    changes = 0
    if entity_type == "question":
        field = "question_text"
        old = replacement.get(field)
        new = strip_location_scaffold(old)
        if new != old:
            replacement[field] = new
            changes += 1
    elif entity_type == "flashcard":
        field = "front"
        old = replacement.get(field)
        new = strip_location_scaffold(old)
        if new != old:
            replacement[field] = new
            changes += 1
    elif entity_type == "activity":
        content = replacement.get("content")
        if isinstance(content, dict):
            for field in (
                "situation", "clearance", "lookup_context", "para_context",
                "question_text", "task", "instruction",
            ):
                old = content.get(field)
                new = strip_location_scaffold(old)
                if new != old:
                    content[field] = new
                    changes += 1
    return changes


def apply_content_rewrite(
    entity_type: str,
    item_id: str,
    replacement: dict[str, Any],
) -> int:
    rewrite = CONTENT_REWRITES.get(item_id)
    if not rewrite:
        return 0
    changes = 0
    target = replacement
    if entity_type == "activity":
        content = replacement.get("content")
        if not isinstance(content, dict):
            return 0
        target = content
    for key, value in rewrite.items():
        if target.get(key) != value:
            target[key] = value
            changes += 1
    return changes


def normalize_manifest(path: Path) -> tuple[int, int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    text_changes = 0
    order_changes = 0
    removed_payloads = 0
    for decision in payload.get("decisions", []):
        action = decision.get("action")
        if action == "remove":
            if "replacement" in decision:
                decision.pop("replacement")
                removed_payloads += 1
            continue
        if action not in {"replace", "split"}:
            continue
        replacements = decision.get("replacement")
        if action == "replace":
            replacements = [replacements]
        if not isinstance(replacements, list):
            continue
        for index, replacement in enumerate(replacements):
            if not isinstance(replacement, dict):
                continue
            text_changes += normalize_replacement(
                str(decision.get("entity_type") or ""),
                replacement,
            )
            text_changes += apply_content_rewrite(
                str(decision.get("entity_type") or ""),
                str(decision.get("item_id") or ""),
                replacement,
            )
            order_changes += int(balance_choice_position(
                str(decision.get("entity_type") or ""),
                str(decision.get("item_id") or ""),
                index,
                replacement,
            ))
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return text_changes, order_changes, removed_payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--chapters", default="1-14")
    args = parser.parse_args()
    from export_content_remediation_packets import parse_chapters

    for chapter in parse_chapters(args.chapters):
        path = (
            args.outputs_dir / f"chapter_{chapter:02d}"
            / f"chapter_{chapter:02d}_pass_01.json"
        )
        if not path.exists():
            print(f"chapter {chapter:02d}: no final manifest")
            continue
        text, order, removed = normalize_manifest(path)
        print(
            f"chapter {chapter:02d}: {text} prompt cleanup(s), "
            f"{order} choice reorder(s), {removed} stray removal payload(s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
