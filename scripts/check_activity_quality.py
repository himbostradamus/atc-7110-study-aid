#!/usr/bin/env python3
"""
Regression checks for activity-generation quality on known tricky paragraphs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.activity_generator import (  # noqa: E402
    generate_activities_for_paragraph,
    validate_activity_payload,
)
from backend.app.services.local_generation import extract_list_items, normalise_ws  # noqa: E402
from scripts.generate_curriculum import load_paragraphs  # noqa: E402


DEFAULT_SOURCE = ROOT.parent / "Student" / "7110.65BB_1-22-26.pdf"


CHAPTER_4_MANUAL_PARAS: tuple[str, ...] = (
    "4-1-1", "4-1-2", "4-1-3", "4-1-4", "4-1-5",
    "4-2-1", "4-2-2", "4-2-3", "4-2-4", "4-2-5", "4-2-6", "4-2-7", "4-2-8", "4-2-9", "4-2-10",
    "4-3-1", "4-3-2", "4-3-3", "4-3-4", "4-3-5", "4-3-6", "4-3-7", "4-3-8", "4-3-9", "4-3-10",
    "4-4-1", "4-4-2", "4-4-3", "4-4-4", "4-4-5", "4-4-6",
    "4-5-1", "4-5-2", "4-5-3", "4-5-4", "4-5-5", "4-5-6", "4-5-7", "4-5-8", "4-5-9",
    "4-6-1", "4-6-2", "4-6-3", "4-6-4", "4-6-5", "4-6-6", "4-6-7", "4-6-8",
    "4-7-1", "4-7-2", "4-7-3", "4-7-4", "4-7-5", "4-7-6", "4-7-7", "4-7-8", "4-7-9", "4-7-10", "4-7-11", "4-7-12", "4-7-13",
    "4-8-1", "4-8-2", "4-8-3", "4-8-4", "4-8-5", "4-8-6", "4-8-7", "4-8-8", "4-8-9", "4-8-10", "4-8-11", "4-8-12",
)

CHAPTER_2_MANUAL_PARAS: tuple[str, ...] = tuple(
    f"2-{section}-{index}"
    for section, count in (
        (1, 31),
        (2, 15),
        (3, 10),
        (4, 22),
        (5, 3),
        (6, 6),
        (7, 3),
        (8, 3),
        (9, 3),
        (10, 3),
    )
    for index in range(1, count + 1)
)

CHAPTER_4_REPLACE_ALL_CASES: tuple[tuple[str, str], ...] = (
    ("4-3-1", "directive_check"),
    ("4-3-1", "reference_check"),
    ("4-4-3", "requirement_check"),
    ("4-4-4", "directive_check"),
    ("4-6-3", "directive_check"),
    ("4-7-2", "list_membership"),
    ("4-7-3", "list_membership"),
    ("4-7-3", "reference_check"),
    ("4-7-3", "situation_action"),
)

CHAPTER_3_MANUAL_PARAS: tuple[str, ...] = tuple(
    f"3-{section}-{index}"
    for section, count in (
        (1, 15),
        (2, 3),
        (3, 7),
        (4, 19),
        (5, 3),
        (6, 4),
        (7, 6),
        (8, 4),
        (9, 11),
        (10, 13),
        (11, 6),
        (12, 3),
    )
    for index in range(1, count + 1)
)

CHAPTER_5_MANUAL_PARAS: tuple[str, ...] = tuple(
    f"5-{section}-{index}"
    for section, count in (
        (1, 9),
        (2, 24),
        (3, 9),
        (4, 10),
        (5, 12),
        (6, 3),
        (7, 4),
        (8, 5),
        (9, 11),
        (10, 15),
        (11, 6),
        (12, 11),
        (13, 10),
        (14, 9),
    )
    for index in range(1, count + 1)
)

CHAPTER_5_REPLACE_ALL_CASES: tuple[tuple[str, str], ...] = (
    ("5-1-2", "directive_check"),
    ("5-1-3", "requirement_check"),
    ("5-1-5", "situation_action"),
    ("5-2-1", "directive_check"),
    ("5-2-4", "example_check"),
    ("5-2-5", "example_check"),
    ("5-2-12", "reference_check"),
    ("5-3-1", "conditional_rule_check"),
    ("5-5-2", "requirement_check"),
    ("5-5-6", "directive_check"),
    ("5-8-1", "requirement_check"),
    ("5-8-2", "example_check"),
    ("5-8-5", "reference_check"),
    ("5-9-7", "example_check"),
    ("5-9-9", "example_check"),
    ("5-10-2", "directive_check"),
    ("5-10-9", "reference_check"),
    ("5-11-5", "example_check"),
    ("5-12-7", "list_membership"),
    ("5-12-11", "reference_check"),
    ("5-13-1", "reference_check"),
    ("5-13-3", "requirement_check"),
    ("5-13-4", "list_membership"),
    ("5-14-4", "requirement_check"),
)


@dataclass(frozen=True)
class RegressionCase:
    para_id: str
    activity_type: str
    banned_fragments: tuple[str, ...] = ()
    expect_missing: bool = False
    expect_correct: str | None = None


CASES: tuple[RegressionCase, ...] = (
    RegressionCase("1-1-1", "document_control_check", expect_missing=True),
    RegressionCase("1-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("1-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("1-1-4", "document_control_check", expect_missing=True),
    RegressionCase("1-1-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("1-1-5", "document_control_check", expect_missing=True),
    RegressionCase("1-1-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("1-1-6", "conditional_rule_check", expect_missing=True),
    RegressionCase("1-1-6", "directive_check", expect_missing=True),
    RegressionCase("1-1-6", "requirement_check", expect_missing=True),
    RegressionCase("1-1-6", "scope_check", expect_missing=True),
    RegressionCase("1-1-6", "term_definition_check", expect_missing=True),
    RegressionCase("1-1-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("1-1-14", "document_control_check", expect_missing=True),
    RegressionCase("1-1-14", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("1-1-10", "conditional_rule_check", expect_missing=True),
    RegressionCase("1-1-10", "document_control_check", expect_missing=True),
    RegressionCase("1-1-10", "requirement_check", expect_missing=True),
    RegressionCase("1-1-10", "scope_check", expect_missing=True),
    RegressionCase("1-2-3", "scope_check", expect_missing=True),
    RegressionCase("1-2-4", "requirement_check", expect_missing=True),
    RegressionCase("1-2-4", "scope_check", expect_missing=True),
    RegressionCase("1-2-5", "conditional_rule_check", expect_missing=True),
    RegressionCase("1-2-5", "requirement_check", expect_missing=True),
    RegressionCase("1-2-5", "scope_check", expect_missing=True),
    RegressionCase("1-2-5", "sequence_steps", expect_missing=True),
    RegressionCase("1-2-6", "directive_check", expect_missing=True),
    RegressionCase("1-2-6", "minima_rule_check", expect_missing=True),
    RegressionCase("1-2-6", "requirement_check", expect_missing=True),
    RegressionCase("1-2-6", "situation_action", expect_missing=True),
    RegressionCase("2-1-10", "example_check", expect_missing=True),
    RegressionCase("2-1-17", "phraseology_builder", ("Build the phraseology for:", "radio communications")),
    RegressionCase("2-1-5", "directive_check"),
    RegressionCase("2-1-5", "list_membership", expect_missing=True),
    RegressionCase("2-1-5", "requirement_check", expect_missing=True),
    RegressionCase("2-1-5", "scope_check"),
    RegressionCase("2-1-17", "spot_the_error", expect_missing=True),
    RegressionCase("2-1-22", "situation_action", expect_missing=True),
    RegressionCase("2-2-11", "term_definition_check", expect_missing=True),
    RegressionCase("2-4-12", "phraseology_builder", ("Build the phraseology for:", "interphone message format")),
    RegressionCase("2-8-1", "requirement_check"),
    RegressionCase("2-8-1", "minima_rule_check", expect_missing=True),
    RegressionCase("2-8-3", "phraseology_builder", ("Build the phraseology for:", "\"LESS THAN\"")),
    RegressionCase("2-9-3", "phraseology_builder", ("Build the phraseology for:", "content")),
    RegressionCase("2-6-4", "phraseology_builder", ("Build the phraseology for:", "issuing weather and chaff areas")),
    RegressionCase("2-8-3", "situation_action"),
    *(
        RegressionCase(para_id, "example_check", expect_missing=True)
        for para_id in (
            "2-1-6",
            "2-1-17",
            "2-1-21",
            "2-1-22",
            "2-1-23",
            "2-2-11",
            "2-3-5",
            "2-3-8",
            "2-4-3",
            "2-4-7",
            "2-4-12",
            "2-4-15",
            "2-4-17",
            "2-4-19",
            "2-4-20",
            "2-4-21",
            "2-4-22",
            "2-5-1",
            "2-5-2",
            "2-5-3",
            "2-6-4",
            "2-8-3",
            "2-9-2",
            "2-9-3",
        )
    ),
    *(
        RegressionCase(
            para_id,
            "knowledge_check",
            ("Which statement is correct?", "Is this statement correct?", f"Under {para_id}"),
        )
        for para_id in CHAPTER_2_MANUAL_PARAS
    ),
    RegressionCase("3-1-1", "situation_action", ("Delay the action until workload permits",)),
    RegressionCase("3-1-14", "list_membership", ("not one of the listed items",), expect_missing=True),
    RegressionCase("3-1-14", "directive_check"),
    RegressionCase("3-2-2", "list_membership", ("not one of the listed items",)),
    RegressionCase("3-2-3", "requirement_check", ("do not turn the helicopter", "while on the tower")),
    RegressionCase("3-3-4", "phraseology_builder", ("Build the phraseology for:", "to describe the braking action in terms easily understood by other pilots")),
    RegressionCase("3-4-2", "list_membership", ("not one of the listed items",)),
    RegressionCase("3-4-3", "reference_check", ("10-6-6", "do not use include"), expect_missing=True),
    RegressionCase("3-4-4", "requirement_check", ("do not use include",)),
    RegressionCase("3-4-7", "list_membership"),
    RegressionCase("3-4-8", "requirement_check"),
    RegressionCase("3-4-9", "list_membership", ("Under 3-4-9",)),
    RegressionCase("3-4-11", "table_lookup", ("in accordance with Where a facility directive",)),
    RegressionCase("3-4-12", "requirement_check"),
    RegressionCase("3-4-13", "directive_check", ("center controller",)),
    RegressionCase("3-4-14", "reference_check", ("3-4-13",), expect_missing=True),
    RegressionCase("3-4-15", "situation_action"),
    RegressionCase("3-4-16", "list_membership", ("not one of the listed items",)),
    RegressionCase("3-4-17", "directive_check"),
    RegressionCase("3-4-18", "list_membership"),
    RegressionCase("3-5-2", "requirement_check", ("do not use STOL runways",)),
    RegressionCase("3-6-1", "list_membership", ("not one of the listed items",)),
    RegressionCase("3-6-3", "spot_the_error"),
    RegressionCase("3-7-2", "phraseology_builder", ("Build the phraseology for:", "3-7-2 taxi and ground movement procedures")),
    RegressionCase("3-7-2", "spot_the_error", expect_missing=True),
    RegressionCase("3-7-3", "requirement_check", ("do not use caution", "use attention")),
    RegressionCase("3-7-3", "phraseology_builder", ("Build the phraseology for:", "ground operations")),
    RegressionCase("3-8-4", "table_lookup"),
    RegressionCase("3-9-7", "spot_the_error"),
    RegressionCase("3-9-10", "document_control_check", expect_missing=True),
    RegressionCase("3-10-2", "reference_check", expect_missing=True),
    RegressionCase("3-10-9", "spot_the_error", expect_missing=True),
    RegressionCase("3-10-11", "spot_the_error"),
    RegressionCase("3-10-12", "spot_the_error"),
    RegressionCase("3-11-2", "spot_the_error"),
    RegressionCase("3-11-4", "list_membership", ("right the landing area",)),
    RegressionCase("3-11-5", "minima_rule_check", ("Under 3-11-5",)),
    RegressionCase("3-11-6", "spot_the_error"),
    *(
        RegressionCase(
            para_id,
            "knowledge_check",
            ("Which statement is correct?", "Is this statement correct?", f"Under {para_id}"),
        )
        for para_id in CHAPTER_3_MANUAL_PARAS
    ),
    *(
        RegressionCase(para_id, "example_check", expect_missing=True)
        for para_id in (
            "3-1-6",
            "3-1-9",
            "3-1-10",
            "3-3-1",
            "3-3-4",
            "3-7-1",
            "3-7-2",
            "3-7-3",
            "3-7-6",
            "3-9-4",
            "3-9-10",
            "3-10-4",
            "3-10-5",
            "3-10-6",
            "3-10-9",
            "3-10-12",
        )
    ),
    RegressionCase("4-7-3", "reference_check", expect_missing=True),
    RegressionCase("4-7-4", "conditional_rule_check", ("must be authorized",)),
    RegressionCase("4-1-1", "table_lookup"),
    RegressionCase("4-1-2", "list_membership", ("not one of the listed items",)),
    RegressionCase("4-2-6", "readback_check"),
    RegressionCase("4-2-5", "example_check", expect_missing=True),
    RegressionCase("4-2-5", "example_check", expect_missing=True),
    RegressionCase("4-2-10", "example_check", expect_missing=True),
    RegressionCase("4-4-3", "example_check", expect_missing=True),
    RegressionCase("4-4-3", "requirement_check", expect_missing=True),
    RegressionCase("4-4-4", "directive_check", expect_missing=True),
    RegressionCase("4-3-2", "example_check", expect_missing=True),
    RegressionCase("4-3-3", "example_check", expect_missing=True),
    RegressionCase("4-6-1", "example_check", expect_missing=True),
    RegressionCase("4-6-1", "example_check", expect_missing=True),
    RegressionCase("4-6-1", "example_check", expect_missing=True),
    RegressionCase("4-3-1", "reference_check", expect_missing=True),
    RegressionCase("4-3-3", "example_check", expect_missing=True),
    RegressionCase("4-5-7", "example_check", expect_missing=True),
    RegressionCase("4-7-1", "example_check", expect_missing=True),
    RegressionCase("4-7-10", "scope_check", expect_missing=True),
    RegressionCase("4-7-10", "example_check", expect_missing=True),
    RegressionCase("4-7-10", "example_check", expect_missing=True),
    RegressionCase("4-8-1", "example_check", expect_missing=True),
    RegressionCase("4-8-1", "example_check", expect_missing=True),
    RegressionCase("4-8-12", "example_check", expect_missing=True),
    RegressionCase("4-8-12", "example_check", expect_missing=True),
    RegressionCase("4-7-5", "example_check", expect_missing=True),
    RegressionCase("4-7-5", "example_check", expect_missing=True),
    RegressionCase("4-7-5", "example_check", expect_missing=True),
    RegressionCase("4-7-5", "example_check", expect_missing=True),
    RegressionCase("4-8-1", "phraseology_builder"),
    RegressionCase("4-6-1", "phraseology_builder", ("Build the phraseology for:", "clearance to holding fix")),
    RegressionCase("4-8-12", "phraseology_builder", ("Build the phraseology for:", "low approach and touch-and-go")),
    RegressionCase("4-8-7", "example_check", expect_missing=True),
    RegressionCase("4-8-3", "requirement_check", ("optional and available",)),
    *(
        RegressionCase(
            para_id,
            "knowledge_check",
            ("Which statement is correct?", "Is this statement correct?", f"Under {para_id}"),
        )
        for para_id in CHAPTER_4_MANUAL_PARAS
    ),
    *(
        RegressionCase(para_id, activity_type, expect_missing=True)
        for para_id, activity_type in CHAPTER_4_REPLACE_ALL_CASES
    ),
    RegressionCase("5-1-1", "requirement_check", ("provide radar services all if",)),
    RegressionCase("5-1-7", "requirement_check", ("at most once",)),
    RegressionCase("5-2-14", "requirement_check", expect_missing=True),
    RegressionCase("5-2-15", "minima_rule_check", ("pilot reported altitude, or",)),
    RegressionCase("5-3-4", "reference_check", ("3-1-10",)),
    RegressionCase("5-4-3", "sequence_steps"),
    RegressionCase("5-4-3", "example_check", expect_missing=True),
    RegressionCase("5-4-4", "scope_check"),
    RegressionCase("5-4-7", "scope_check"),
    RegressionCase("5-5-7", "example_check", expect_missing=True),
    RegressionCase("5-6-2", "example_check", expect_missing=True),
    RegressionCase("5-7-1", "minima_rule_check", ("optional or desired spacing",)),
    RegressionCase("5-7-2", "example_check", expect_missing=True),
    RegressionCase("5-7-3", "minima_rule_check"),
    RegressionCase("5-8-3", "list_membership", ("not one of the listed items",)),
    RegressionCase("5-9-3", "example_check", expect_missing=True),
    RegressionCase("5-9-4", "example_check", expect_missing=True),
    RegressionCase("5-9-5", "scope_check", ("center control function", "different final approach course", "Under 5-9-5")),
    RegressionCase("5-9-11", "requirement_check"),
    RegressionCase("5-10-1", "scope_check"),
    RegressionCase("5-10-5", "reference_check", ("5-9-3",)),
    RegressionCase("5-10-7", "directive_check"),
    RegressionCase("5-10-14", "example_check", expect_missing=True),
    RegressionCase("5-10-15", "list_membership", ("before the approach has begun",)),
    RegressionCase("5-11-1", "minima_rule_check", ("withheld mda",)),
    RegressionCase("5-11-3", "spot_the_error"),
    RegressionCase("5-12-1", "directive_check", ("after final descent",)),
    RegressionCase("5-12-2", "directive_check"),
    RegressionCase("5-12-3", "directive_check"),
    RegressionCase("5-12-4", "example_check", expect_missing=True),
    RegressionCase("5-12-5", "directive_check"),
    RegressionCase("5-12-6", "directive_check"),
    RegressionCase("5-12-9", "requirement_check"),
    RegressionCase("5-12-10", "example_check", expect_missing=True),
    RegressionCase("5-13-7", "situation_action", ("Apply the rule only after another controller confirms the need for it",)),
    RegressionCase("5-13-8", "scope_check", ("must be used as a reminder",)),
    RegressionCase("5-14-2", "scope_check"),
    RegressionCase("5-14-3", "list_membership", ("not one of the listed items",)),
    RegressionCase("5-14-5", "reference_check", ("3-1-10",)),
    RegressionCase("5-14-6", "list_membership", ("not one of the listed items",)),
    RegressionCase("5-2-3", "phraseology_builder", ("Build the phraseology for:", "emergency code assignment")),
    RegressionCase("5-9-4", "phraseology_builder", ("Build the phraseology for:", "arrival instructions")),
    RegressionCase("5-12-10", "phraseology_builder", ("Build the phraseology for:", "elevation failure")),
    RegressionCase("5-14-1", "situation_action", ("What action best complies with APPLICATION?",), expect_missing=True),
    *(
        RegressionCase(
            para_id,
            "knowledge_check",
            ("Which statement is correct?", "Is this statement correct?", f"Under {para_id}"),
        )
        for para_id in CHAPTER_5_MANUAL_PARAS
    ),
    *(
        RegressionCase(para_id, activity_type, expect_missing=True)
        for para_id, activity_type in CHAPTER_5_REPLACE_ALL_CASES
    ),
    RegressionCase("2-5-1", "example_check", expect_missing=True),
    RegressionCase("2-5-2", "example_check", expect_missing=True),
    RegressionCase("2-5-3", "example_check", expect_missing=True),
    RegressionCase("6-7-1", "list_membership", ("if all one missed approach procedure",)),
    RegressionCase("6-1-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("6-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?")),
    RegressionCase("6-4-5", "directive_check", expect_missing=True),
    RegressionCase("6-5-3", "minima_rule_check", expect_missing=True),
    RegressionCase("6-6-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("6-7-2", "reference_check", ("5-9-6",)),
    RegressionCase("6-7-3", "directive_check", expect_missing=True),
    RegressionCase("6-7-4", "requirement_check", expect_missing=True),
    RegressionCase("6-7-5", "reference_check", ("5-9-6",)),
    RegressionCase("6-7-6", "directive_check", expect_missing=True),
    RegressionCase("6-7-6", "situation_action", ("The applicable condition is:",)),
    RegressionCase("6-7-7", "situation_action", ("center procedure", "continue the center")),
    RegressionCase("6-1-1", "directive_check", ("Do not use mileage-based",)),
    RegressionCase("6-4-1", "requirement_check"),
    RegressionCase("8-1-1", "conditional_rule_check", expect_missing=True),
    RegressionCase("8-1-2", "scope_check", expect_missing=True),
    RegressionCase("8-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 8-1-3")),
    RegressionCase("8-1-10", "requirement_check", expect_missing=True),
    RegressionCase("8-3-3", "example_check", expect_missing=True),
    RegressionCase("8-3-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 8-3-3")),
    RegressionCase("8-4-1", "term_definition_check", expect_missing=True),
    RegressionCase("8-5-4", "minima_rule_check", expect_missing=True),
    RegressionCase("8-5-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 8-5-5")),
    RegressionCase("8-7-3", "scope_check", expect_missing=True),
    RegressionCase("8-7-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 8-7-3")),
    RegressionCase("8-8-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("8-9-3", "requirement_check", expect_missing=True),
    RegressionCase("8-10-3", "example_check", expect_missing=True),
    RegressionCase("8-10-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 8-10-3")),
    RegressionCase("7-1-1", "requirement_check", expect_missing=True),
    RegressionCase("7-1-1", "scope_check", expect_missing=True),
    RegressionCase("7-1-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-1-1")),
    RegressionCase("7-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-1-2")),
    RegressionCase("7-1-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-1-3", "requirement_check", expect_missing=True),
    RegressionCase("7-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-1-3")),
    RegressionCase("7-1-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-1-4")),
    RegressionCase("7-2-1", "directive_check", expect_missing=True),
    RegressionCase("7-2-1", "document_control_check", expect_missing=True),
    RegressionCase("7-2-1", "example_check", expect_missing=True),
    RegressionCase("7-2-1", "minima_rule_check", expect_missing=True),
    RegressionCase("7-2-1", "requirement_check", expect_missing=True),
    RegressionCase("7-2-1", "scope_check", expect_missing=True),
    RegressionCase("7-2-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-2-1")),
    RegressionCase("7-3-1", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-3-1", "example_check", expect_missing=True),
    RegressionCase("7-3-1", "requirement_check", expect_missing=True),
    RegressionCase("7-3-1", "scope_check", expect_missing=True),
    RegressionCase("7-3-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-3-1")),
    RegressionCase("7-3-2", "directive_check", expect_missing=True),
    RegressionCase("7-3-2", "requirement_check", expect_missing=True),
    RegressionCase("7-3-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-3-2")),
    RegressionCase("7-4-1", "scope_check"),
    RegressionCase("7-4-1", "sequence_steps", expect_missing=True),
    RegressionCase("7-4-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-1")),
    RegressionCase("7-4-2", "minima_rule_check", expect_missing=True),
    RegressionCase("7-4-2", "requirement_check", expect_missing=True),
    RegressionCase("7-4-2", "scope_check", expect_missing=True),
    RegressionCase("7-4-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-2")),
    RegressionCase("7-4-3", "capability_check", expect_missing=True),
    RegressionCase("7-4-3", "directive_check", expect_missing=True),
    RegressionCase("7-4-3", "example_check", expect_missing=True),
    RegressionCase("7-4-3", "requirement_check", expect_missing=True),
    RegressionCase("7-4-3", "scope_check", expect_missing=True),
    RegressionCase("7-4-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-3")),
    RegressionCase("7-4-4", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-4-4", "directive_check", expect_missing=True),
    RegressionCase("7-4-4", "minima_rule_check", expect_missing=True),
    RegressionCase("7-4-4", "requirement_check", expect_missing=True),
    RegressionCase("7-4-4", "scope_check", expect_missing=True),
    RegressionCase("7-4-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-4")),
    RegressionCase("7-4-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-5")),
    RegressionCase("7-4-6", "directive_check", expect_missing=True),
    RegressionCase("7-4-6", "minima_rule_check", expect_missing=True),
    RegressionCase("7-4-6", "requirement_check", expect_missing=True),
    RegressionCase("7-4-6", "scope_check", expect_missing=True),
    RegressionCase("7-4-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-6")),
    RegressionCase("7-4-7", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-4-7", "directive_check", expect_missing=True),
    RegressionCase("7-4-7", "minima_rule_check", expect_missing=True),
    RegressionCase("7-4-7", "scope_check", expect_missing=True),
    RegressionCase("7-4-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-4-7")),
    RegressionCase("7-5-1", "minima_rule_check", expect_missing=True),
    RegressionCase("7-5-1", "requirement_check", expect_missing=True),
    RegressionCase("7-5-1", "scope_check", expect_missing=True),
    RegressionCase("7-5-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-1")),
    RegressionCase("7-5-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-5-2", "directive_check", expect_missing=True),
    RegressionCase("7-5-2", "scope_check", expect_missing=True),
    RegressionCase("7-5-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-2")),
    RegressionCase("7-5-3", "directive_check", expect_missing=True),
    RegressionCase("7-5-3", "minima_rule_check", expect_missing=True),
    RegressionCase("7-5-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-3")),
    RegressionCase("7-5-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-4")),
    RegressionCase("7-5-5", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-5-5", "scope_check", expect_missing=True),
    RegressionCase("7-5-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-5")),
    RegressionCase("7-5-6", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-5-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-6")),
    RegressionCase("7-5-7", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-5-7", "directive_check", expect_missing=True),
    RegressionCase("7-5-7", "minima_rule_check", expect_missing=True),
    RegressionCase("7-5-7", "requirement_check", expect_missing=True),
    RegressionCase("7-5-7", "scope_check", expect_missing=True),
    RegressionCase("7-5-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-7")),
    RegressionCase("7-5-8", "directive_check", expect_missing=True),
    RegressionCase("7-5-8", "minima_rule_check", expect_missing=True),
    RegressionCase("7-5-8", "requirement_check", expect_missing=True),
    RegressionCase("7-5-8", "scope_check", expect_missing=True),
    RegressionCase("7-5-8", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-5-8")),
    RegressionCase("7-6-1", "requirement_check", expect_missing=True),
    RegressionCase("7-6-1", "scope_check", expect_missing=True),
    RegressionCase("7-6-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-1")),
    RegressionCase("7-6-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-6-2", "directive_check", expect_missing=True),
    RegressionCase("7-6-2", "requirement_check", expect_missing=True),
    RegressionCase("7-6-2", "scope_check", expect_missing=True),
    RegressionCase("7-6-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-2")),
    RegressionCase("7-6-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-6-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-3")),
    RegressionCase("7-6-4", "directive_check", expect_missing=True),
    RegressionCase("7-6-4", "requirement_check", expect_missing=True),
    RegressionCase("7-6-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-4")),
    RegressionCase("7-6-5", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-6-5", "requirement_check", expect_missing=True),
    RegressionCase("7-6-5", "scope_check", expect_missing=True),
    RegressionCase("7-6-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-5")),
    RegressionCase("7-6-6", "directive_check", expect_missing=True),
    RegressionCase("7-6-6", "requirement_check", expect_missing=True),
    RegressionCase("7-6-6", "scope_check", expect_missing=True),
    RegressionCase("7-6-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-6")),
    RegressionCase("7-6-7", "directive_check", expect_missing=True),
    RegressionCase("7-6-7", "requirement_check", expect_missing=True),
    RegressionCase("7-6-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-7")),
    RegressionCase("7-6-8", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-6-8", "directive_check", expect_missing=True),
    RegressionCase("7-6-8", "minima_rule_check", expect_missing=True),
    RegressionCase("7-6-8", "requirement_check", expect_missing=True),
    RegressionCase("7-6-8", "scope_check", expect_missing=True),
    RegressionCase("7-6-8", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-8")),
    RegressionCase("7-6-9", "directive_check", expect_missing=True),
    RegressionCase("7-6-9", "requirement_check", expect_missing=True),
    RegressionCase("7-6-9", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-9")),
    RegressionCase("7-6-10", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-10")),
    RegressionCase("7-6-11", "directive_check", expect_missing=True),
    RegressionCase("7-6-11", "requirement_check", expect_missing=True),
    RegressionCase("7-6-11", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-11")),
    RegressionCase("7-6-12", "directive_check", expect_missing=True),
    RegressionCase("7-6-12", "requirement_check", expect_missing=True),
    RegressionCase("7-6-12", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-6-12")),
    RegressionCase("7-7-1", "requirement_check", expect_missing=True),
    RegressionCase("7-7-1", "scope_check", expect_missing=True),
    RegressionCase("7-7-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-1")),
    RegressionCase("7-7-2", "directive_check", expect_missing=True),
    RegressionCase("7-7-2", "requirement_check", expect_missing=True),
    RegressionCase("7-7-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-2")),
    RegressionCase("7-7-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-3")),
    RegressionCase("7-7-4", "requirement_check", expect_missing=True),
    RegressionCase("7-7-4", "scope_check", expect_missing=True),
    RegressionCase("7-7-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-4")),
    RegressionCase("7-7-5", "scope_check", expect_missing=True),
    RegressionCase("7-7-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-5")),
    RegressionCase("7-7-6", "requirement_check", expect_missing=True),
    RegressionCase("7-7-6", "scope_check", expect_missing=True),
    RegressionCase("7-7-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-6")),
    RegressionCase("7-7-7", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-7-7", "directive_check", expect_missing=True),
    RegressionCase("7-7-7", "requirement_check", expect_missing=True),
    RegressionCase("7-7-7", "scope_check", expect_missing=True),
    RegressionCase("7-7-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-7-7")),
    RegressionCase("7-8-1", "directive_check", ("do not apply",)),
    RegressionCase("7-8-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-1")),
    RegressionCase("7-8-2", "list_membership", ("Class C services include the following is one of the listed items",)),
    RegressionCase("7-8-2", "sequence_steps", expect_missing=True),
    RegressionCase("7-8-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-2")),
    RegressionCase("7-8-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-3")),
    RegressionCase("7-8-4", "directive_check"),
    RegressionCase("7-8-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-4")),
    RegressionCase("7-8-5", "requirement_check"),
    RegressionCase("7-8-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-5")),
    RegressionCase("7-8-6", "list_membership", ("not one of the listed items",)),
    RegressionCase("7-8-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-6")),
    RegressionCase("7-8-7", "requirement_check"),
    RegressionCase("7-8-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-7")),
    RegressionCase("7-8-8", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-8-8", "directive_check", expect_missing=True),
    RegressionCase("7-8-8", "requirement_check", expect_missing=True),
    RegressionCase("7-8-8", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-8-8")),
    RegressionCase("7-9-1", "directive_check", expect_missing=True),
    RegressionCase("7-9-1", "requirement_check", expect_missing=True),
    RegressionCase("7-9-1", "scope_check", expect_missing=True),
    RegressionCase("7-9-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-1")),
    RegressionCase("7-9-2", "capability_check", expect_missing=True),
    RegressionCase("7-9-2", "directive_check", expect_missing=True),
    RegressionCase("7-9-2", "requirement_check", expect_missing=True),
    RegressionCase("7-9-2", "scope_check", expect_missing=True),
    RegressionCase("7-9-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-2")),
    RegressionCase("7-9-3", "directive_check", expect_missing=True),
    RegressionCase("7-9-3", "requirement_check", expect_missing=True),
    RegressionCase("7-9-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-3")),
    RegressionCase("7-9-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-4")),
    RegressionCase("7-9-5", "directive_check", expect_missing=True),
    RegressionCase("7-9-5", "requirement_check", expect_missing=True),
    RegressionCase("7-9-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-5")),
    RegressionCase("7-9-6", "requirement_check", expect_missing=True),
    RegressionCase("7-9-6", "scope_check", expect_missing=True),
    RegressionCase("7-9-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-6")),
    RegressionCase("7-9-7", "conditional_rule_check", expect_missing=True),
    RegressionCase("7-9-7", "directive_check", expect_missing=True),
    RegressionCase("7-9-7", "requirement_check", expect_missing=True),
    RegressionCase("7-9-7", "scope_check", expect_missing=True),
    RegressionCase("7-9-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-7")),
    RegressionCase("7-9-8", "requirement_check", expect_missing=True),
    RegressionCase("7-9-8", "scope_check", expect_missing=True),
    RegressionCase("7-9-8", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 7-9-8")),
    RegressionCase("9-1-1", "conditional_rule_check", expect_missing=True),
    RegressionCase("9-1-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-1-1")),
    RegressionCase("9-1-2", "directive_check", expect_missing=True),
    RegressionCase("9-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-1-2")),
    RegressionCase("9-2-5", "example_check", expect_missing=True),
    RegressionCase("9-2-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-2-5")),
    RegressionCase("9-2-10", "requirement_check", expect_missing=True),
    RegressionCase("9-2-10", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-2-10")),
    RegressionCase("9-2-13", "minima_rule_check", expect_missing=True),
    RegressionCase("9-2-13", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-2-13")),
    RegressionCase("9-2-15", "term_definition_check", expect_missing=True),
    RegressionCase("9-2-15", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-2-15")),
    RegressionCase("9-3-1", "scope_check", expect_missing=True),
    RegressionCase("9-3-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-3-1")),
    RegressionCase("9-3-3", "minima_rule_check", expect_missing=True),
    RegressionCase("9-3-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-3-3")),
    RegressionCase("9-4-1", "conditional_rule_check", expect_missing=True),
    RegressionCase("9-4-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-4-1")),
    RegressionCase("9-4-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-4-4")),
    RegressionCase("9-4-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-4-5")),
    RegressionCase("9-5-1", "requirement_check", expect_missing=True),
    RegressionCase("9-5-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-5-1")),
    RegressionCase("9-6-1", "scope_check", expect_missing=True),
    RegressionCase("9-6-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-6-1")),
    RegressionCase("9-6-2", "directive_check", expect_missing=True),
    RegressionCase("9-6-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-6-2")),
    RegressionCase("9-7-2", "directive_check", expect_missing=True),
    RegressionCase("9-7-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-7-2")),
    RegressionCase("9-8-1", "requirement_check", expect_missing=True),
    RegressionCase("9-8-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 9-8-1")),
    RegressionCase("10-1-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("10-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 10-1-2")),
    RegressionCase("10-1-6", "requirement_check", expect_missing=True),
    RegressionCase("10-1-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 10-1-6")),
    RegressionCase("10-2-9", "list_membership", ("not one of the listed items",)),
    RegressionCase("10-2-9", "sequence_steps", expect_missing=True),
    RegressionCase("10-2-10", "directive_check"),
    RegressionCase("10-2-10", "requirement_check", expect_missing=True),
    RegressionCase("10-2-10", "scope_check", expect_missing=True),
    RegressionCase("10-2-10", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 10-2-10")),
    RegressionCase("10-2-16", "requirement_check", expect_missing=True),
    RegressionCase("10-2-16", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 10-2-16")),
    RegressionCase("10-2-6", "spot_the_error"),
    RegressionCase("10-4-4", "document_control_check", expect_missing=True),
    RegressionCase("10-5-2", "example_check", expect_missing=True),
    RegressionCase("10-6-2", "requirement_check", expect_missing=True),
    RegressionCase("10-6-4", "scope_check", expect_missing=True),
    RegressionCase("10-7-2", "minima_rule_check", expect_missing=True),
    RegressionCase("10-4-3", "requirement_check", expect_missing=True),
    RegressionCase("10-4-3", "scope_check", expect_missing=True),
    RegressionCase("11-1-1", "requirement_check", expect_missing=True),
    RegressionCase("11-1-1", "scope_check", expect_missing=True),
    RegressionCase("11-1-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 11-1-1")),
    RegressionCase("11-1-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("11-1-2", "directive_check", expect_missing=True),
    RegressionCase("11-1-2", "requirement_check", expect_missing=True),
    RegressionCase("11-1-2", "scope_check", expect_missing=True),
    RegressionCase("11-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 11-1-2")),
    RegressionCase("11-1-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("11-1-3", "directive_check", expect_missing=True),
    RegressionCase("11-1-3", "minima_rule_check", expect_missing=True),
    RegressionCase("11-1-3", "requirement_check", expect_missing=True),
    RegressionCase("11-1-3", "scope_check", expect_missing=True),
    RegressionCase("11-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 11-1-3")),
    RegressionCase("12-1-1", "requirement_check", expect_missing=True),
    RegressionCase("12-1-1", "scope_check", expect_missing=True),
    RegressionCase("12-1-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-1")),
    RegressionCase("12-1-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("12-1-2", "minima_rule_check", expect_missing=True),
    RegressionCase("12-1-2", "requirement_check", expect_missing=True),
    RegressionCase("12-1-2", "scope_check", expect_missing=True),
    RegressionCase("12-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-2")),
    RegressionCase("12-1-3", "directive_check", expect_missing=True),
    RegressionCase("12-1-3", "minima_rule_check", expect_missing=True),
    RegressionCase("12-1-3", "requirement_check", expect_missing=True),
    RegressionCase("12-1-3", "scope_check", expect_missing=True),
    RegressionCase("12-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-3")),
    RegressionCase("12-1-4", "directive_check", expect_missing=True),
    RegressionCase("12-1-4", "requirement_check", expect_missing=True),
    RegressionCase("12-1-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-4")),
    RegressionCase("12-1-5", "requirement_check", expect_missing=True),
    RegressionCase("12-1-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-5")),
    RegressionCase("12-1-6", "requirement_check", expect_missing=True),
    RegressionCase("12-1-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-6")),
    RegressionCase("12-1-7", "directive_check", expect_missing=True),
    RegressionCase("12-1-7", "minima_rule_check", expect_missing=True),
    RegressionCase("12-1-7", "requirement_check", expect_missing=True),
    RegressionCase("12-1-7", "scope_check", expect_missing=True),
    RegressionCase("12-1-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 12-1-7")),
    RegressionCase("13-1-1", "capability_check", expect_missing=True),
    RegressionCase("13-1-1", "requirement_check", expect_missing=True),
    RegressionCase("13-1-1", "scope_check", expect_missing=True),
    RegressionCase("13-1-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-1")),
    RegressionCase("13-1-2", "capability_check", expect_missing=True),
    RegressionCase("13-1-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-2", "minima_rule_check", expect_missing=True),
    RegressionCase("13-1-2", "requirement_check", expect_missing=True),
    RegressionCase("13-1-2", "scope_check", expect_missing=True),
    RegressionCase("13-1-2", "sequence_steps", expect_missing=True),
    RegressionCase("13-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-2")),
    RegressionCase("13-1-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-3", "directive_check", expect_missing=True),
    RegressionCase("13-1-3", "requirement_check", expect_missing=True),
    RegressionCase("13-1-3", "scope_check", expect_missing=True),
    RegressionCase("13-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-3")),
    RegressionCase("13-1-4", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-4", "requirement_check", expect_missing=True),
    RegressionCase("13-1-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-4")),
    RegressionCase("13-1-5", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-5", "requirement_check", expect_missing=True),
    RegressionCase("13-1-5", "scope_check", expect_missing=True),
    RegressionCase("13-1-5", "sequence_steps", expect_missing=True),
    RegressionCase("13-1-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-5")),
    RegressionCase("13-1-6", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-6", "directive_check", expect_missing=True),
    RegressionCase("13-1-6", "requirement_check", expect_missing=True),
    RegressionCase("13-1-6", "scope_check", expect_missing=True),
    RegressionCase("13-1-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-6")),
    RegressionCase("13-1-7", "directive_check", expect_missing=True),
    RegressionCase("13-1-7", "requirement_check", expect_missing=True),
    RegressionCase("13-1-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-7")),
    RegressionCase("13-1-8", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-8", "minima_rule_check", expect_missing=True),
    RegressionCase("13-1-8", "requirement_check", expect_missing=True),
    RegressionCase("13-1-8", "scope_check", expect_missing=True),
    RegressionCase("13-1-8", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-8")),
    RegressionCase("13-1-9", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-9", "requirement_check", expect_missing=True),
    RegressionCase("13-1-9", "scope_check", expect_missing=True),
    RegressionCase("13-1-9", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-9")),
    RegressionCase("13-1-10", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-10", "requirement_check", expect_missing=True),
    RegressionCase("13-1-10", "scope_check", expect_missing=True),
    RegressionCase("13-1-10", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-10")),
    RegressionCase("13-1-11", "requirement_check", expect_missing=True),
    RegressionCase("13-1-11", "scope_check", expect_missing=True),
    RegressionCase("13-1-11", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-11")),
    RegressionCase("13-1-12", "capability_check", expect_missing=True),
    RegressionCase("13-1-12", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-12", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-12")),
    RegressionCase("13-1-13", "directive_check", expect_missing=True),
    RegressionCase("13-1-13", "requirement_check", expect_missing=True),
    RegressionCase("13-1-13", "scope_check", expect_missing=True),
    RegressionCase("13-1-13", "sequence_steps", expect_missing=True),
    RegressionCase("13-1-13", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-13")),
    RegressionCase("13-1-14", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-14", "requirement_check", expect_missing=True),
    RegressionCase("13-1-14", "scope_check", expect_missing=True),
    RegressionCase("13-1-14", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-14")),
    RegressionCase("13-1-15", "capability_check", expect_missing=True),
    RegressionCase("13-1-15", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-15", "requirement_check", expect_missing=True),
    RegressionCase("13-1-15", "scope_check", expect_missing=True),
    RegressionCase("13-1-15", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-15")),
    RegressionCase("13-1-16", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-16", "scope_check", expect_missing=True),
    RegressionCase("13-1-16", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-16")),
    RegressionCase("13-1-17", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-1-17", "directive_check", expect_missing=True),
    RegressionCase("13-1-17", "requirement_check", expect_missing=True),
    RegressionCase("13-1-17", "scope_check", expect_missing=True),
    RegressionCase("13-1-17", "sequence_steps", expect_missing=True),
    RegressionCase("13-1-17", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-1-17")),
    RegressionCase("13-2-1", "capability_check", expect_missing=True),
    RegressionCase("13-2-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-2-1")),
    RegressionCase("13-2-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-2-2", "directive_check", expect_missing=True),
    RegressionCase("13-2-2", "requirement_check", expect_missing=True),
    RegressionCase("13-2-2", "scope_check", expect_missing=True),
    RegressionCase("13-2-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-2-2")),
    RegressionCase("13-2-3", "directive_check", expect_missing=True),
    RegressionCase("13-2-3", "minima_rule_check", expect_missing=True),
    RegressionCase("13-2-3", "requirement_check", expect_missing=True),
    RegressionCase("13-2-3", "scope_check", expect_missing=True),
    RegressionCase("13-2-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-2-3")),
    RegressionCase("13-2-4", "conditional_rule_check", expect_missing=True),
    RegressionCase("13-2-4", "requirement_check", expect_missing=True),
    RegressionCase("13-2-4", "scope_check", expect_missing=True),
    RegressionCase("13-2-4", "term_definition_check", expect_missing=True),
    RegressionCase("13-2-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-2-4")),
    RegressionCase("13-2-5", "requirement_check", expect_missing=True),
    RegressionCase("13-2-5", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-2-5")),
    RegressionCase("13-2-6", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Select the correct statement.")),
    RegressionCase("13-2-7", "directive_check", expect_missing=True),
    RegressionCase("13-2-7", "requirement_check", expect_missing=True),
    RegressionCase("13-2-7", "scope_check", expect_missing=True),
    RegressionCase("13-2-7", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 13-2-7")),
    RegressionCase("14-1-1", "directive_check", expect_missing=True),
    RegressionCase("14-1-1", "document_control_check", expect_missing=True),
    RegressionCase("14-1-1", "scope_check", expect_missing=True),
    RegressionCase("14-1-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-1-1")),
    RegressionCase("14-1-2", "document_control_check", expect_missing=True),
    RegressionCase("14-1-2", "requirement_check", expect_missing=True),
    RegressionCase("14-1-2", "scope_check", expect_missing=True),
    RegressionCase("14-1-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-1-2")),
    RegressionCase("14-1-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("14-1-3", "directive_check", expect_missing=True),
    RegressionCase("14-1-3", "requirement_check", expect_missing=True),
    RegressionCase("14-1-3", "scope_check", expect_missing=True),
    RegressionCase("14-1-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-1-3")),
    RegressionCase("14-2-1", "document_control_check", expect_missing=True),
    RegressionCase("14-2-1", "requirement_check", expect_missing=True),
    RegressionCase("14-2-1", "scope_check", expect_missing=True),
    RegressionCase("14-2-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-2-1")),
    RegressionCase("14-2-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("14-2-2", "directive_check", expect_missing=True),
    RegressionCase("14-2-2", "readback_check", expect_missing=True),
    RegressionCase("14-2-2", "requirement_check", expect_missing=True),
    RegressionCase("14-2-2", "scope_check", expect_missing=True),
    RegressionCase("14-2-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-2-2")),
    RegressionCase("14-2-3", "example_check", expect_missing=True),
    RegressionCase("14-2-3", "minima_rule_check", expect_missing=True),
    RegressionCase("14-2-3", "requirement_check", expect_missing=True),
    RegressionCase("14-2-3", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-2-3")),
    RegressionCase("14-2-4", "match_pairs", expect_missing=True),
    RegressionCase("14-2-4", "conditional_rule_check", expect_missing=True),
    RegressionCase("14-2-4", "scope_check", expect_missing=True),
    RegressionCase("14-2-4", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-2-4")),
    RegressionCase("14-3-1", "conditional_rule_check", expect_missing=True),
    RegressionCase("14-3-1", "requirement_check", expect_missing=True),
    RegressionCase("14-3-1", "scope_check", expect_missing=True),
    RegressionCase("14-3-1", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-3-1")),
    RegressionCase("14-3-2", "conditional_rule_check", expect_missing=True),
    RegressionCase("14-3-2", "requirement_check", expect_missing=True),
    RegressionCase("14-3-2", "scope_check", expect_missing=True),
    RegressionCase("14-3-2", "knowledge_check", ("Which statement is correct?", "Is this statement correct?", "Under 14-3-2")),
    RegressionCase("14-3-3", "conditional_rule_check", expect_missing=True),
    RegressionCase("14-3-3", "directive_check", expect_missing=True),
    RegressionCase("14-3-3", "document_control_check", expect_missing=True),
    RegressionCase("14-3-3", "minima_rule_check", expect_missing=True),
    RegressionCase("14-3-3", "requirement_check", expect_missing=True),
    RegressionCase("14-3-3", "scope_check", expect_missing=True),
    RegressionCase("8-4-4", "minima_rule_check", expect_missing=True),
)

GLOBAL_BANNED_FRAGMENTS = (
    "not not",
    "only who",
    "only aircraft",
    "for reference by",
    "paragraph's approved examples",
    "'s approved examples",
    "this paragraph governs the situation",
    "this section governs the situation",
    "What action best complies with ",
    "supported by the section",
    "section's list",
    "position verify",
    "the decimal where",
    "less than one facility",
    "less than one aircraft",
    "alert information",
    "Do not submit a landing clearance",
    "where final descent is not to start",
    "unavailable to the FAA",
    "unavailable to FSSs",
    "do not transfer this responsibility to another facility only when",
    "the do not use of the ok function",
    "14 cfr section is no longer",
    "need not strive not only",
)
QUALITY_TEXT_LIMITS = {
    "conditional_rule_check": ("question_text", 220),
    "minima_rule_check": ("question_text", 220),
    "requirement_check": ("question_text", 220),
    "scope_check": ("question_text", 220),
    "situation_action": ("situation", 260),
}
LIST_INTRO_CUE_RE = re.compile(
    r"\b(?:one of the following|as follows|"
    r"following conditions? (?:is|are) met|"
    r"following actions? (?:are|is) taken|"
    r"the following (?:conditions?|actions?|items?|information|services?|techniques?|procedures?))\b",
    re.IGNORECASE,
)


def _looks_list_dump(text: str) -> bool:
    clean = normalise_ws(text)
    if not clean:
        return False
    marker = re.search(r"\bThe applicable condition is:\s*", clean, re.IGNORECASE)
    if marker:
        tail = clean[marker.end():].strip()
        if tail:
            clean = tail
    if LIST_INTRO_CUE_RE.search(clean):
        return True
    if clean.count(";") >= 2:
        return True
    if ":" in clean:
        head, tail = clean.split(":", 1)
        if len(head.split()) >= 4 and len(tail.split()) >= 5:
            return True
    return False


def _block_content(block: object) -> str:
    if isinstance(block, dict):
        return str(block.get("content", ""))
    return str(getattr(block, "content", ""))


def _list_item_key(text: str) -> str:
    return normalise_ws(text).rstrip(".").lower()


async def run_checks(source_path: Path) -> int:
    chapters = list(range(1, 15))
    paragraphs = load_paragraphs(source_path, chapters)
    lookup = {para.para_id: para for para in paragraphs}

    failures: list[str] = []
    passes = 0

    for case in CASES:
        para = lookup.get(case.para_id)
        if not para:
            failures.append(f"{case.para_id}: paragraph missing from parsed source")
            continue

        generated = await generate_activities_for_paragraph(
            para.para_id,
            para.title,
            para.blocks,
            types=[case.activity_type],
        )
        activities = generated.get(case.activity_type, [])
        if not activities:
            if case.expect_missing:
                passes += 1
                continue
            failures.append(f"{case.para_id} {case.activity_type}: activity missing")
            continue
        if case.expect_missing:
            failures.append(f"{case.para_id} {case.activity_type}: activity should be suppressed")
            continue

        for idx, activity in enumerate(activities, start=1):
            errors = validate_activity_payload(case.activity_type, activity, para.title)
            if errors:
                failures.append(
                    f"{case.para_id} {case.activity_type} #{idx}: validation failed: {', '.join(errors)}"
                )
                continue

            generation_source = str(activity.get("generation_source", "local_auto"))
            if case.activity_type == "phraseology_builder" and generation_source != "curated":
                failures.append(
                    f"{case.para_id} {case.activity_type} #{idx}: expected curated generation source, got {generation_source}"
                )
                continue
            correct_choice = next(
                (str(choice.get("text", "")) for choice in activity.get("choices", []) if choice.get("is_correct")),
                "",
            ).lower()
            if case.expect_correct and correct_choice != case.expect_correct:
                failures.append(
                    f"{case.para_id} {case.activity_type} #{idx}: expected correct answer '{case.expect_correct}', got '{correct_choice or 'missing'}'"
                )
                continue
            limit = QUALITY_TEXT_LIMITS.get(case.activity_type)
            if limit and generation_source == "local_auto":
                field, max_chars = limit
                text = str(activity.get(field, ""))
                if len(text) > max_chars:
                    failures.append(
                        f"{case.para_id} {case.activity_type} #{idx}: {field} exceeds {max_chars} characters"
                    )
                    continue
                if _looks_list_dump(text):
                    failures.append(
                        f"{case.para_id} {case.activity_type} #{idx}: {field} is a list dump rather than a focused prompt"
                    )
                    continue

            if case.activity_type == "list_membership" and generation_source == "local_auto":
                if len(str(activity.get("explanation", ""))) > 220:
                    failures.append(
                        f"{case.para_id} {case.activity_type} #{idx}: explanation exceeds 220 characters"
                    )
                    continue
                if correct_choice == "false":
                    source_text = "\n\n".join(_block_content(block) for block in para.blocks)
                    listed_items = {_list_item_key(item) for item in extract_list_items(source_text)}
                    question_key = _list_item_key(str(activity.get("question_text", "")))
                    if question_key in listed_items:
                        failures.append(
                            f"{case.para_id} {case.activity_type} #{idx}: false answer still uses an included list item"
                        )
                        continue

            text_fields = [
                activity.get("instruction", ""),
                activity.get("question_text", ""),
                activity.get("display_text", ""),
                activity.get("situation", ""),
                activity.get("para_context", ""),
                activity.get("clearance", ""),
            ]
            for choice in activity.get("choices", []):
                text_fields.append(choice.get("text", ""))
            payload_text = json.dumps(text_fields, sort_keys=True).lower()
            for fragment in GLOBAL_BANNED_FRAGMENTS + case.banned_fragments:
                if fragment.lower() in payload_text:
                    failures.append(
                        f"{case.para_id} {case.activity_type} #{idx}: contains banned fragment '{fragment}'"
                    )
                    break
            else:
                passes += 1

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"\n{len(failures)} regression issue(s) detected; {passes} check(s) passed.")
        return 1

    print(f"All {passes} quality regression checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the source PDF or ZIP used for paragraph parsing.",
    )
    args = parser.parse_args()

    if not args.source.exists():
        parser.error(f"source file not found: {args.source}")

    return asyncio.run(run_checks(args.source))


if __name__ == "__main__":
    raise SystemExit(main())
