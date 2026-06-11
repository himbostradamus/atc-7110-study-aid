#!/usr/bin/env python3
"""Audit authored questions, flashcards, and activities as one learning system."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable

import audit_question_agent_output as question_audit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_REPORT = ROOT / "docs" / "learning-content-agent-output-audit.md"
DEFAULT_JSON = ROOT / "docs" / "learning-content-agent-output-audit.json"
DEFAULT_BASELINE = ROOT / "docs" / "learning-content-agent-audit-baseline.json"

QUESTION_LEAD_RE = re.compile(
    r"^(?:what|when|where|who|which|how|why|identify|name|state|list|"
    r"select|choose|determine|give|describe|explain)\b",
    re.IGNORECASE,
)
SCENARIO_ACTIVITY_RE = re.compile(
    r"(?:situation|scenario|decision|responsibility|sequence|format)",
    re.IGNORECASE,
)
SOURCE_ACTIVITY_TYPES = {"source_lookup", "source_use"}
REFERENCE_CARD_TYPES = {"reference", "source_reference"}


@dataclass(frozen=True)
class Flashcard:
    card_id: str
    para_id: str
    card_type: str
    front: str
    back: str
    source: str

    @property
    def learning_text(self) -> str:
        return f"{self.front} {self.back}".strip()


@dataclass(frozen=True)
class Activity:
    activity_id: str
    para_id: str
    activity_type: str
    payload: dict
    source: str

    @property
    def prompt(self) -> str:
        fields = (
            "situation", "clearance", "lookup_context", "para_context",
            "question_text", "task", "instruction",
        )
        return question_audit.normalize_space(
            " ".join(str(self.payload.get(field) or "") for field in fields)
        )

    @property
    def explanation(self) -> str:
        return question_audit.normalize_space(self.payload.get("explanation"))

    @property
    def choices(self) -> list[dict]:
        choices = self.payload.get("choices")
        return choices if isinstance(choices, list) else []

    @property
    def learning_text(self) -> str:
        return flatten_payload_text(self.payload)


def flatten_payload_text(value: object) -> str:
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
    return question_audit.normalize_space(" ".join(parts))


def load_flashcards(db: sqlite3.Connection, sources: tuple[str, ...]) -> list[Flashcard]:
    placeholders = ",".join("?" for _ in sources)
    rows = db.execute(
        f"""
        SELECT id, para_id, card_type, front, back, generation_src
        FROM flashcards
        WHERE generation_src IN ({placeholders})
        ORDER BY para_id, card_type, front
        """,
        sources,
    ).fetchall()
    return [
        Flashcard(
            card_id=row[0],
            para_id=row[1],
            card_type=question_audit.normalize_space(row[2]),
            front=question_audit.normalize_space(row[3]),
            back=question_audit.normalize_space(row[4]),
            source=row[5],
        )
        for row in rows
    ]


def load_activities(db: sqlite3.Connection, sources: tuple[str, ...]) -> tuple[list[Activity], list[dict]]:
    placeholders = ",".join("?" for _ in sources)
    rows = db.execute(
        f"""
        SELECT id, para_id, activity_type, content_json, generation_src
        FROM activities
        WHERE generation_src IN ({placeholders})
        ORDER BY para_id, activity_type
        """,
        sources,
    ).fetchall()
    activities: list[Activity] = []
    invalid: list[dict] = []
    for row in rows:
        try:
            payload = json.loads(row[3])
        except (TypeError, json.JSONDecodeError) as error:
            invalid.append({
                "activity_id": row[0],
                "para_id": row[1],
                "activity_type": row[2],
                "error": str(error),
            })
            continue
        if not isinstance(payload, dict):
            invalid.append({
                "activity_id": row[0],
                "para_id": row[1],
                "activity_type": row[2],
                "error": "content_json is not an object",
            })
            continue
        activities.append(Activity(
            activity_id=row[0],
            para_id=row[1],
            activity_type=row[2],
            payload=payload,
            source=row[4],
        ))
    return activities, invalid


def card_mode(card: Flashcard) -> str:
    card_type = card.card_type.lower()
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
    if card_type in REFERENCE_CARD_TYPES:
        return "source_navigation"
    if card_type in {"definition"}:
        return "definition_recall"
    return "concept_recall"


def activity_mode(activity: Activity) -> str:
    activity_type = activity.activity_type.lower()
    if activity_type in SOURCE_ACTIVITY_TYPES:
        return "source_use"
    if "phraseology" in activity_type or "readback" in activity_type or "format" in activity_type:
        return "exact_application"
    if "list" in activity_type or "sequence" in activity_type:
        return "list_or_sequence"
    if "discrimination" in activity_type or "spot_the_error" in activity_type:
        return "discrimination"
    if SCENARIO_ACTIVITY_RE.search(activity_type):
        return "scenario_application"
    if "requirement" in activity_type:
        return "requirement_recall"
    return "knowledge_check"


def is_prompt_like(value: str) -> bool:
    clean = question_audit.normalize_space(value)
    return bool("?" in clean or QUESTION_LEAD_RE.search(clean))


def normalized_choice(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def near_duplicate_pairs(items_by_para: dict[str, list], text_getter) -> list[dict]:
    duplicates: list[dict] = []
    for para_id, items in items_by_para.items():
        for left, right in combinations(items, 2):
            left_text = text_getter(left)
            right_text = text_getter(right)
            similarity = question_audit.jaccard(
                question_audit.tokens(left_text),
                question_audit.tokens(right_text),
            )
            if similarity >= 0.78:
                duplicates.append({
                    "para_id": para_id,
                    "similarity": round(similarity, 3),
                    "left": left_text,
                    "right": right_text,
                })
    return duplicates


def coverage_by_modality(
    db: sqlite3.Connection,
    modality_texts: dict[str, dict[str, list[str]]],
) -> tuple[dict, list[dict]]:
    represented = set().union(*(
        set(by_para) for by_para in modality_texts.values()
    ))
    rows = db.execute(
        "SELECT para_id, content_json FROM paragraphs ORDER BY para_id"
    ).fetchall()
    totals = Counter()
    paragraph_rows: list[dict] = []
    for para_id, content_json in rows:
        if para_id not in represented:
            continue
        statements = question_audit.split_source_statements(content_json)
        if not statements:
            continue
        covered_by_modality = Counter()
        multi_covered = 0
        for statement in statements:
            statement_tokens = question_audit.tokens(statement)
            matched_modalities = 0
            for modality, by_para in modality_texts.items():
                candidates = [
                    question_audit.tokens(text)
                    for text in by_para.get(para_id, [])
                ]
                best = max((
                    question_audit.jaccard(statement_tokens, candidate)
                    for candidate in candidates
                ), default=0.0)
                shared = max((
                    len(statement_tokens & candidate)
                    for candidate in candidates
                ), default=0)
                matched = best >= 0.16 and shared >= 2
                covered_by_modality[modality] += int(matched)
                matched_modalities += int(matched)
            totals["essential"] += 1
            totals["any"] += int(matched_modalities > 0)
            totals["two_plus"] += int(matched_modalities >= 2)
            totals["all_three"] += int(matched_modalities == len(modality_texts))
            multi_covered += int(matched_modalities >= 2)
        for modality, count in covered_by_modality.items():
            totals[modality] += count
        paragraph_rows.append({
            "para_id": para_id,
            "essential_statements": len(statements),
            "questions": covered_by_modality["questions"],
            "flashcards": covered_by_modality["flashcards"],
            "activities": covered_by_modality["activities"],
            "two_plus": multi_covered,
        })
    essential = totals["essential"]
    metrics = {
        "essential_statement_count": essential,
        "covered_by_questions": totals["questions"],
        "covered_by_flashcards": totals["flashcards"],
        "covered_by_activities": totals["activities"],
        "covered_by_any": totals["any"],
        "covered_by_two_or_more": totals["two_plus"],
        "covered_by_all_three": totals["all_three"],
    }
    for key in list(metrics):
        if key == "essential_statement_count":
            continue
        metrics[f"{key}_rate"] = round(metrics[key] / essential if essential else 1.0, 4)
    return metrics, paragraph_rows


def modality_counts_by_paragraph(
    questions: list[question_audit.Question],
    cards: list[Flashcard],
    activities: list[Activity],
) -> dict:
    modalities: dict[str, set[str]] = defaultdict(set)
    for question in questions:
        modalities[question.para_id].add("questions")
    for card in cards:
        modalities[card.para_id].add("flashcards")
    for activity in activities:
        modalities[activity.para_id].add("activities")
    distribution = Counter(len(value) for value in modalities.values())
    return {
        "paragraph_count": len(modalities),
        "modality_count_distribution": {
            str(count): total for count, total in sorted(distribution.items())
        },
        "paragraphs_with_all_three": sum(len(value) == 3 for value in modalities.values()),
    }


def cross_format_duplicates(
    questions_by_para: dict[str, list[question_audit.Question]],
    cards_by_para: dict[str, list[Flashcard]],
    activities_by_para: dict[str, list[Activity]],
) -> list[dict]:
    duplicates: list[dict] = []
    pairings = (
        ("question", questions_by_para, lambda item: item.text,
         "flashcard", cards_by_para, lambda item: item.front),
        ("question", questions_by_para, lambda item: item.text,
         "activity", activities_by_para, lambda item: item.prompt),
        ("flashcard", cards_by_para, lambda item: item.front,
         "activity", activities_by_para, lambda item: item.prompt),
    )
    for left_name, left_map, left_text, right_name, right_map, right_text in pairings:
        for para_id in set(left_map) & set(right_map):
            for left in left_map[para_id]:
                for right in right_map[para_id]:
                    left_value = left_text(left)
                    right_value = right_text(right)
                    similarity = question_audit.jaccard(
                        question_audit.tokens(left_value),
                        question_audit.tokens(right_value),
                    )
                    if similarity >= 0.82:
                        duplicates.append({
                            "para_id": para_id,
                            "formats": f"{left_name}/{right_name}",
                            "similarity": round(similarity, 3),
                            "left": left_value,
                            "right": right_value,
                        })
    return duplicates


def analyze(db_path: Path, sources: tuple[str, ...]) -> dict:
    db = sqlite3.connect(db_path)
    try:
        questions = question_audit.load_questions(db, sources)
        cards = load_flashcards(db, sources)
        activities, invalid_activities = load_activities(db, sources)

        questions_by_para: dict[str, list[question_audit.Question]] = defaultdict(list)
        cards_by_para: dict[str, list[Flashcard]] = defaultdict(list)
        activities_by_para: dict[str, list[Activity]] = defaultdict(list)
        for question in questions:
            questions_by_para[question.para_id].append(question)
        for card in cards:
            cards_by_para[card.para_id].append(card)
        for activity in activities:
            activities_by_para[activity.para_id].append(activity)

        card_location = [
            card for card in cards
            if card.card_type.lower() not in REFERENCE_CARD_TYPES
            and (
                question_audit.DOCUMENT_LOCATION_RE.search(card.front)
                or question_audit.NOTE_LOCATION_RE.search(card.front)
            )
        ]
        card_generic = [
            card for card in cards
            if question_audit.GENERIC_REFERENCE_RE.search(card.front)
        ]
        context_light_cards = [
            card for card in cards
            if len(card.front.split()) < 4 and not is_prompt_like(card.front)
        ]
        thin_card_backs = [card for card in cards if len(card.back.split()) < 4]
        overloaded_cards = [
            card for card in cards
            if len(card.back.split()) > 50
            or len(re.findall(r"(?:^|\s)\d+[.)]\s", card.back)) > 6
        ]
        malformed_reverse_cards = [
            card for card in cards
            if "reverse" in card.card_type.lower() and not is_prompt_like(card.back)
        ]
        answer_restatement_cards = [
            card for card in cards
            if question_audit.jaccard(
                question_audit.tokens(card.front),
                question_audit.tokens(card.back),
            ) >= 0.72
        ]
        card_duplicates = near_duplicate_pairs(cards_by_para, lambda card: card.front)
        card_mode_distribution = Counter(
            len({card_mode(card) for card in group})
            for group in cards_by_para.values()
        )

        activity_location = [
            activity for activity in activities
            if activity.activity_type not in SOURCE_ACTIVITY_TYPES
            and (
                question_audit.DOCUMENT_LOCATION_RE.search(activity.prompt)
                or question_audit.NOTE_LOCATION_RE.search(activity.prompt)
            )
        ]
        activity_generic = [
            activity for activity in activities
            if question_audit.GENERIC_REFERENCE_RE.search(activity.prompt)
        ]
        negative_activities = [
            activity for activity in activities
            if question_audit.NEGATIVE_STEM_RE.search(activity.prompt)
        ]
        thin_activity_explanations = [
            activity for activity in activities
            if len(activity.explanation.split()) < 10
        ]
        thin_scenario_context = [
            activity for activity in activities
            if SCENARIO_ACTIVITY_RE.search(activity.activity_type)
            and len(question_audit.normalize_space(
                f"{activity.payload.get('situation', '')} "
                f"{activity.payload.get('clearance', '')} "
                f"{activity.payload.get('lookup_context', '')} "
                f"{activity.payload.get('question_text', '')}"
            ).split()) < 12
        ]
        invalid_choice_sets: list[dict] = []
        duplicate_choice_sets: list[dict] = []
        answer_length_cues: list[dict] = []
        correct_positions = Counter()
        for activity in activities:
            if not activity.choices:
                continue
            correct = [
                (index, choice)
                for index, choice in enumerate(activity.choices)
                if choice.get("is_correct") is True
            ]
            if len(activity.choices) < 2 or len(correct) != 1:
                invalid_choice_sets.append({
                    "para_id": activity.para_id,
                    "activity_type": activity.activity_type,
                    "choice_count": len(activity.choices),
                    "correct_count": len(correct),
                })
                continue
            correct_positions[correct[0][0]] += 1
            normalized = [
                normalized_choice(choice.get("text"))
                for choice in activity.choices
            ]
            if len(set(normalized)) != len(normalized):
                duplicate_choice_sets.append({
                    "para_id": activity.para_id,
                    "activity_type": activity.activity_type,
                    "choices": [choice.get("text", "") for choice in activity.choices],
                })
            correct_text = question_audit.normalize_space(correct[0][1].get("text"))
            distractor_words = [
                max(1, len(question_audit.normalize_space(choice.get("text")).split()))
                for index, choice in enumerate(activity.choices)
                if index != correct[0][0]
            ]
            correct_words = len(correct_text.split())
            distractor_average = sum(distractor_words) / len(distractor_words)
            if correct_words >= 6 and correct_words > distractor_average * 1.8:
                answer_length_cues.append({
                    "para_id": activity.para_id,
                    "activity_type": activity.activity_type,
                    "correct": correct_text,
                    "distractor_average_words": round(distractor_average, 1),
                })
        valid_choice_activity_count = sum(correct_positions.values())
        activity_duplicates = near_duplicate_pairs(
            activities_by_para, lambda activity: activity.prompt
        )
        activity_mode_distribution = Counter(
            len({activity_mode(activity) for activity in group})
            for group in activities_by_para.values()
        )

        chapter_breakdown = {}
        chapters = sorted({
            item.para_id.split("-", 1)[0]
            for item in [*cards, *activities]
            if item.para_id.split("-", 1)[0].isdigit()
        }, key=int)
        for chapter in chapters:
            chapter_cards = [
                card for card in cards
                if card.para_id.split("-", 1)[0] == chapter
            ]
            chapter_activities = [
                activity for activity in activities
                if activity.para_id.split("-", 1)[0] == chapter
            ]
            chapter_choice_activities = [
                activity for activity in chapter_activities
                if len(activity.choices) >= 2
                and sum(
                    choice.get("is_correct") is True
                    for choice in activity.choices
                ) == 1
            ]
            chapter_breakdown[chapter] = {
                "flashcards": len(chapter_cards),
                "context_light_cards": sum(
                    card in context_light_cards for card in chapter_cards
                ),
                "location_scaffolded_cards": sum(
                    card in card_location for card in chapter_cards
                ),
                "malformed_reverse_cards": sum(
                    card in malformed_reverse_cards for card in chapter_cards
                ),
                "activities": len(chapter_activities),
                "location_scaffolded_activities": sum(
                    activity in activity_location
                    for activity in chapter_activities
                ),
                "answer_length_cues": sum(
                    item["para_id"].split("-", 1)[0] == chapter
                    for item in answer_length_cues
                ),
                "first_correct_rate": round(
                    sum(
                        activity.choices[0].get("is_correct") is True
                        for activity in chapter_choice_activities
                    ) / len(chapter_choice_activities)
                    if chapter_choice_activities else 0,
                    4,
                ),
            }

        modality_texts = {
            "questions": {
                para_id: [question.learning_text for question in group]
                for para_id, group in questions_by_para.items()
            },
            "flashcards": {
                para_id: [card.learning_text for card in group]
                for para_id, group in cards_by_para.items()
            },
            "activities": {
                para_id: [activity.learning_text for activity in group]
                for para_id, group in activities_by_para.items()
            },
        }
        coverage, coverage_by_para = coverage_by_modality(db, modality_texts)
        cross_duplicates = cross_format_duplicates(
            questions_by_para, cards_by_para, activities_by_para
        )

        question_result = question_audit.analyze(db_path, sources)
        metrics = {
            "sources": list(sources),
            "questions": question_result["metrics"],
            "flashcards": {
                "count": len(cards),
                "paragraph_count": len(cards_by_para),
                "type_counts": dict(Counter(card.card_type for card in cards)),
                "mode_counts": dict(Counter(card_mode(card) for card in cards)),
                "location_scaffolded_count": len(card_location),
                "generic_reference_count": len(card_generic),
                "context_light_prompt_count": len(context_light_cards),
                "thin_back_count": len(thin_card_backs),
                "overloaded_back_count": len(overloaded_cards),
                "malformed_reverse_count": len(malformed_reverse_cards),
                "answer_restatement_count": len(answer_restatement_cards),
                "near_duplicate_pair_count": len(card_duplicates),
                "paragraph_mode_count_distribution": {
                    str(count): total
                    for count, total in sorted(card_mode_distribution.items())
                },
                "paragraphs_with_three_modes": sum(
                    count for modes, count in card_mode_distribution.items()
                    if modes >= 3
                ),
            },
            "activities": {
                "count": len(activities) + len(invalid_activities),
                "paragraph_count": len(activities_by_para),
                "type_counts": dict(Counter(
                    activity.activity_type for activity in activities
                )),
                "mode_counts": dict(Counter(
                    activity_mode(activity) for activity in activities
                )),
                "invalid_json_count": len(invalid_activities),
                "location_scaffolded_count": len(activity_location),
                "generic_reference_count": len(activity_generic),
                "negative_prompt_count": len(negative_activities),
                "thin_explanation_count": len(thin_activity_explanations),
                "thin_scenario_context_count": len(thin_scenario_context),
                "invalid_choice_set_count": len(invalid_choice_sets),
                "duplicate_choice_set_count": len(duplicate_choice_sets),
                "answer_length_cue_count": len(answer_length_cues),
                "near_duplicate_pair_count": len(activity_duplicates),
                "correct_answer_positions": {
                    str(position): count
                    for position, count in sorted(correct_positions.items())
                },
                "first_correct_rate": round(
                    correct_positions[0] / valid_choice_activity_count
                    if valid_choice_activity_count else 0,
                    4,
                ),
                "paragraph_mode_count_distribution": {
                    str(count): total
                    for count, total in sorted(activity_mode_distribution.items())
                },
                "paragraphs_with_three_modes": sum(
                    count for modes, count in activity_mode_distribution.items()
                    if modes >= 3
                ),
            },
            "combined": {
                **modality_counts_by_paragraph(questions, cards, activities),
                **coverage,
                "cross_format_near_duplicate_count": len(cross_duplicates),
                "chapter_breakdown": chapter_breakdown,
            },
        }
        return {
            "metrics": metrics,
            "examples": {
                "flashcards": {
                    "location_scaffolded": [
                        vars(card) for card in card_location[:20]
                    ],
                    "context_light_prompts": [
                        vars(card) for card in context_light_cards[:30]
                    ],
                    "thin_backs": [vars(card) for card in thin_card_backs[:20]],
                    "overloaded_backs": [
                        vars(card) for card in overloaded_cards[:20]
                    ],
                    "malformed_reverse": [
                        vars(card) for card in malformed_reverse_cards[:30]
                    ],
                    "near_duplicates": sorted(
                        card_duplicates,
                        key=lambda item: item["similarity"],
                        reverse=True,
                    )[:30],
                },
                "activities": {
                    "invalid_json": invalid_activities[:20],
                    "location_scaffolded": [
                        {
                            "para_id": activity.para_id,
                            "activity_type": activity.activity_type,
                            "prompt": activity.prompt,
                        }
                        for activity in activity_location[:20]
                    ],
                    "thin_scenario_context": [
                        {
                            "para_id": activity.para_id,
                            "activity_type": activity.activity_type,
                            "prompt": activity.prompt,
                        }
                        for activity in thin_scenario_context[:20]
                    ],
                    "invalid_choice_sets": invalid_choice_sets[:20],
                    "duplicate_choice_sets": duplicate_choice_sets[:20],
                    "answer_length_cues": answer_length_cues[:30],
                    "near_duplicates": sorted(
                        activity_duplicates,
                        key=lambda item: item["similarity"],
                        reverse=True,
                    )[:30],
                },
                "combined": {
                    "cross_format_near_duplicates": sorted(
                        cross_duplicates,
                        key=lambda item: item["similarity"],
                        reverse=True,
                    )[:40],
                    "lowest_multi_format_coverage": sorted(
                        coverage_by_para,
                        key=lambda item: (
                            item["two_plus"] / item["essential_statements"],
                            -item["essential_statements"],
                        ),
                    )[:50],
                },
            },
        }
    finally:
        db.close()


def render_markdown(result: dict) -> str:
    metrics = result["metrics"]
    cards = metrics["flashcards"]
    activities = metrics["activities"]
    combined = metrics["combined"]
    examples = result["examples"]
    question_metrics = metrics["questions"]
    lines = [
        "# Learning-Content Agent Output Audit",
        "",
        f"Sources audited: `{', '.join(metrics['sources'])}`",
        "",
        "## Corpus Summary",
        "",
        f"- Questions: {question_metrics['question_count']} across {question_metrics['paragraph_count']} paragraphs.",
        f"- Flashcards: {cards['count']} across {cards['paragraph_count']} paragraphs.",
        f"- Activities: {activities['count']} across {activities['paragraph_count']} paragraphs.",
        f"- Paragraphs represented by all three formats: {combined['paragraphs_with_all_three']} of {combined['paragraph_count']}.",
        "",
        "## Cross-Format Essential-Element Coverage",
        "",
        f"- Heuristic essential statements in represented paragraphs: {combined['essential_statement_count']}.",
        f"- Covered by questions: {combined['covered_by_questions']} ({combined['covered_by_questions_rate']:.1%}).",
        f"- Covered by flashcards: {combined['covered_by_flashcards']} ({combined['covered_by_flashcards_rate']:.1%}).",
        f"- Covered by activities: {combined['covered_by_activities']} ({combined['covered_by_activities_rate']:.1%}).",
        f"- Covered by at least one format: {combined['covered_by_any']} ({combined['covered_by_any_rate']:.1%}).",
        f"- Reinforced through two or more formats: {combined['covered_by_two_or_more']} ({combined['covered_by_two_or_more_rate']:.1%}).",
        f"- Reinforced through all three formats: {combined['covered_by_all_three']} ({combined['covered_by_all_three_rate']:.1%}).",
        f"- Cross-format near-duplicate pairs: {combined['cross_format_near_duplicate_count']}.",
        "",
        "Coverage is a lexical triage signal, not a legal or semantic determination. Cross-format reinforcement only counts when each format independently overlaps the same controlling source statement.",
        "",
        "## Flashcard Findings",
        "",
        f"- Card types: {json.dumps(cards['type_counts'], sort_keys=True)}",
        f"- Retrieval modes: {json.dumps(cards['mode_counts'], sort_keys=True)}",
        f"- {cards['context_light_prompt_count']} cards use context-light label prompts shorter than four words.",
        f"- {cards['thin_back_count']} cards have answers shorter than four words.",
        f"- {cards['overloaded_back_count']} cards overload one reveal with more than 50 words or a long list.",
        f"- {cards['malformed_reverse_count']} reverse cards do not provide a clear reverse-side prompt.",
        f"- {cards['location_scaffolded_count']} non-reference cards use paragraph-location scaffolding.",
        f"- {cards['answer_restatement_count']} cards substantially repeat prompt language in the answer.",
        f"- {cards['near_duplicate_pair_count']} within-paragraph prompt pairs have at least 0.78 token similarity.",
        f"- {cards['paragraphs_with_three_modes']} paragraphs have at least three flashcard retrieval modes.",
        "",
        "## Activity Findings",
        "",
        f"- Activity types: {json.dumps(activities['type_counts'], sort_keys=True)}",
        f"- Learning modes: {json.dumps(activities['mode_counts'], sort_keys=True)}",
        f"- Correct-answer positions: {json.dumps(activities['correct_answer_positions'], sort_keys=True)}",
        f"- Correct answer is first in {activities['first_correct_rate']:.1%} of valid choice activities.",
        f"- {activities['answer_length_cue_count']} activities make the correct answer conspicuously longer than the distractors.",
        f"- {activities['invalid_choice_set_count']} activities have fewer than two choices or do not have exactly one correct choice.",
        f"- {activities['duplicate_choice_set_count']} activities contain normalized duplicate choices.",
        f"- {activities['thin_scenario_context_count']} scenario/decision activities provide fewer than twelve words of decision context.",
        f"- {activities['negative_prompt_count']} activities use negative framing.",
        f"- {activities['location_scaffolded_count']} non-source-use activities rely on paragraph-location scaffolding.",
        f"- {activities['near_duplicate_pair_count']} within-paragraph activity pairs have at least 0.78 prompt similarity.",
        f"- {activities['paragraphs_with_three_modes']} paragraphs have at least three activity modes.",
        "",
        "## Highest-Priority Remediation",
        "",
        "1. Rebalance activity answer positions and equalize answer/distractor specificity before adding more choice items.",
        "2. Replace flashcard labels with explicit retrieval cues; keep each card focused on one answerable target.",
        "3. Repair reverse cards so the reverse side asks a real question instead of naming a paragraph or topic.",
        "4. Plan coverage by essential source element, then use card recall, question discrimination, and activity application as complementary tasks.",
        "5. Treat same-stem or same-answer paraphrases across formats as duplication, not additional coverage.",
        "6. Reserve source-location prompts for explicit lookup practice and keep citations outside ordinary learner prompts.",
        "",
        "## Chapter Pattern",
        "",
        "| Chapter | Cards | Context-light cards | Card location scaffold | Activities | Activity location scaffold | First-answer rate | Length cues |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for chapter, values in combined["chapter_breakdown"].items():
        lines.append(
            f"| {chapter} | {values['flashcards']} | "
            f"{values['context_light_cards']} | "
            f"{values['location_scaffolded_cards']} | "
            f"{values['activities']} | "
            f"{values['location_scaffolded_activities']} | "
            f"{values['first_correct_rate']:.0%} | "
            f"{values['answer_length_cues']} |"
        )
    lines.extend([
        "",
        "## Example Context-Light Flashcards",
        "",
    ])
    for card in examples["flashcards"]["context_light_prompts"][:12]:
        lines.append(
            f"- `{card['para_id']}` `{card['card_type']}`: "
            f"“{card['front']}” → “{card['back']}”"
        )
    lines.extend(["", "## Example Malformed Reverse Cards", ""])
    for card in examples["flashcards"]["malformed_reverse"][:12]:
        lines.append(
            f"- `{card['para_id']}`: “{card['front']}” → “{card['back']}”"
        )
    lines.extend(["", "## Example Activity Answer-Length Cues", ""])
    for item in examples["activities"]["answer_length_cues"][:12]:
        lines.append(
            f"- `{item['para_id']}` `{item['activity_type']}`: correct answer "
            f"“{item['correct']}” (distractor average: "
            f"{item['distractor_average_words']} words)"
        )
    lines.extend(["", "## Example Cross-Format Near-Duplicates", ""])
    for item in examples["combined"]["cross_format_near_duplicates"][:12]:
        lines.append(
            f"- `{item['para_id']}` `{item['formats']}` ({item['similarity']:.2f}): "
            f"“{item['left']}” / “{item['right']}”"
        )
    lines.extend(["", "## Lowest Multi-Format Reinforcement", ""])
    for item in examples["combined"]["lowest_multi_format_coverage"][:15]:
        lines.append(
            f"- `{item['para_id']}`: {item['two_plus']}/"
            f"{item['essential_statements']} essential statements covered by "
            f"two or more formats; Q {item['questions']}, "
            f"cards {item['flashcards']}, activities {item['activities']}."
        )
    return "\n".join(lines) + "\n"


def regression_failures(current: dict, baseline: dict) -> list[str]:
    failures: list[str] = []
    bad_count_paths = (
        ("flashcards", "location_scaffolded_count"),
        ("flashcards", "generic_reference_count"),
        ("flashcards", "thin_back_count"),
        ("flashcards", "overloaded_back_count"),
        ("flashcards", "malformed_reverse_count"),
        ("flashcards", "near_duplicate_pair_count"),
        ("activities", "invalid_json_count"),
        ("activities", "location_scaffolded_count"),
        ("activities", "generic_reference_count"),
        ("activities", "thin_explanation_count"),
        ("activities", "thin_scenario_context_count"),
        ("activities", "invalid_choice_set_count"),
        ("activities", "duplicate_choice_set_count"),
        ("activities", "answer_length_cue_count"),
        ("activities", "near_duplicate_pair_count"),
        ("combined", "cross_format_near_duplicate_count"),
    )
    for group, key in bad_count_paths:
        current_value = current.get(group, {}).get(key, 0)
        baseline_value = baseline.get(group, {}).get(key, 0)
        if current_value > baseline_value:
            failures.append(
                f"{group}.{key} increased: {current_value} > {baseline_value}"
            )
    if current.get("activities", {}).get("first_correct_rate", 0) > (
        baseline.get("activities", {}).get("first_correct_rate", 0) + 0.001
    ):
        failures.append(
            "activities.first_correct_rate increased: "
            f"{current['activities']['first_correct_rate']} > "
            f"{baseline['activities']['first_correct_rate']}"
        )
    for key in (
        "covered_by_any_rate",
        "covered_by_two_or_more_rate",
        "covered_by_all_three_rate",
    ):
        current_value = current.get("combined", {}).get(key, 0)
        baseline_value = baseline.get("combined", {}).get(key, 0)
        if current_value < baseline_value:
            failures.append(
                f"combined.{key} decreased: {current_value} < {baseline_value}"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sources", default="question_agent")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args()

    sources = tuple(
        source.strip() for source in args.sources.split(",") if source.strip()
    )
    result = analyze(args.db, sources)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(result), encoding="utf-8")
    args.json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.write_baseline:
        args.baseline.write_text(
            json.dumps(result["metrics"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result["metrics"], indent=2, sort_keys=True))
    if args.fail_on_regression:
        if not args.baseline.exists():
            print(f"Baseline not found: {args.baseline}")
            return 2
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        failures = regression_failures(result["metrics"], baseline)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
