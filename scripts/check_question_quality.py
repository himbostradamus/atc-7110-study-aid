#!/usr/bin/env python3
"""
Regression checks for quiz-question generation quality on known tricky paragraphs.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.question_generator import (  # noqa: E402
    generate_questions_for_paragraph,
    local_auto_question_quality_errors,
    question_text_errors,
)
from scripts.generate_curriculum import load_paragraphs  # noqa: E402


DEFAULT_SOURCE = ROOT.parent / "Student" / "7110.65BB_1-22-26.pdf"


@dataclass(frozen=True)
class QuestionRegressionCase:
    para_id: str
    question_type: str | None = None
    banned_fragments: tuple[str, ...] = ()
    required_fragments: tuple[str, ...] = ()
    expect_missing: bool = False


CASES: tuple[QuestionRegressionCase, ...] = (
    QuestionRegressionCase("1-1-1", "multiple_choice", ("matches 1-1-1",), expect_missing=True),
    QuestionRegressionCase("1-1-12", "multiple_choice", ("What is correct about Safety?", "What is correct about safety management system (sms)?")),
    QuestionRegressionCase("1-1-11", "multiple_choice", ("supported by the section",)),
    QuestionRegressionCase("1-1-14", None, ("All organizations are not responsible",)),
    QuestionRegressionCase("1-1-8", None, ("Under 1-1-8",)),
    QuestionRegressionCase("1-1-10", None, ("Under 1-1-10", "under 1-1-10")),
    QuestionRegressionCase("1-2-3", "multiple_choice", ("What is correct about notes?",)),
    QuestionRegressionCase("2-1-9", "multiple_choice", ("What is correct about FSSs?",)),
    QuestionRegressionCase("2-1-16", "multiple_choice", ("What is correct about The pilot?",)),
    QuestionRegressionCase("2-1-22", None, ("alert information",)),
    QuestionRegressionCase("2-1-13", "fill_blank", ("from 2-1-13",)),
    QuestionRegressionCase("2-2-15", "multiple_choice", ("What is correct about \"NRP\"?", "What is correct about Every effort?")),
    QuestionRegressionCase("2-4-1", "multiple_choice", ("What is correct about The ATIS?",)),
    QuestionRegressionCase("2-2-9", None, ("explicitly included",)),
    QuestionRegressionCase("2-8-1", None, ("According to the note in 2-8-1",)),
    QuestionRegressionCase(
        "4-7-10",
        "fill_blank",
        required_fragments=("Complete the prescribed phraseology", "FREQUENCY"),
    ),
    QuestionRegressionCase(
        "5-9-9",
        "fill_blank",
        required_fragments=("ALTITUDE",),
    ),
    QuestionRegressionCase("5-12-3", None, ("the decimal where", "where final descent is not to start")),
    QuestionRegressionCase("5-12-9", None, ("According to the note in 5-12-9",)),
    QuestionRegressionCase("6-1-3", None, ("position verify", "less than one facility")),
    QuestionRegressionCase("7-6-6", None, ("According to the note in 7-6-6",)),
    QuestionRegressionCase("5-2-24", None, ("Under 5-2-24", "under 5-2-24")),
    QuestionRegressionCase("5-14-1", "multiple_choice", ("What is correct about STARS?",)),
)

GLOBAL_BANNED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^What is correct about\b", re.IGNORECASE),
    re.compile(r"\b(?:under|from|in)\s+\d+(?:-\d+)+(?:[a-z]\d*)?\b", re.IGNORECASE),
    re.compile(r"\b(?:According to|Under) (?:the )?note in\s+\d+(?:-\d+)+(?:[a-z]\d*)?\b", re.IGNORECASE),
    re.compile(r"\b(?:paragraph|para|section)\s+\d+(?:-\d+)+(?:[a-z]\d*)?\b", re.IGNORECASE),
    re.compile(r"\bsupported by the section\b", re.IGNORECASE),
    re.compile(r"\bexplicitly included\b", re.IGNORECASE),
)


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

        questions = await generate_questions_for_paragraph(
            para_id=para.para_id,
            para_title=para.title,
            blocks=para.blocks,
        )
        if case.question_type:
            questions = [question for question in questions if question.question_type == case.question_type]
        if not questions:
            if case.expect_missing:
                passes += 1
                continue
            failures.append(f"{case.para_id} {case.question_type or 'any'}: question missing")
            continue
        if case.expect_missing:
            failures.append(f"{case.para_id} {case.question_type or 'any'}: question should be suppressed")
            continue

        for idx, question in enumerate(questions, start=1):
            errors = question_text_errors(question.question_type, question.question_text)
            errors.extend(local_auto_question_quality_errors(question))
            if errors:
                failures.append(
                    f"{case.para_id} {question.question_type} #{idx}: validation failed: {', '.join(errors)}"
                )
                continue

            payload_text = " | ".join(
                [question.question_text, *(choice.text for choice in question.choices)]
            ).lower()
            doc_ref_failed = False
            for pattern in GLOBAL_BANNED_PATTERNS:
                if pattern.search(payload_text):
                    failures.append(
                        f"{case.para_id} {question.question_type} #{idx}: contains document-location reference '{pattern.pattern}'"
                    )
                    doc_ref_failed = True
                    break
            if doc_ref_failed:
                continue
            for fragment in case.banned_fragments:
                if fragment.lower() in payload_text:
                    failures.append(
                        f"{case.para_id} {question.question_type} #{idx}: contains banned fragment '{fragment}'"
                    )
                    break
            else:
                missing_required = [
                    fragment for fragment in case.required_fragments
                    if fragment.lower() not in payload_text
                ]
                if missing_required:
                    failures.append(
                        f"{case.para_id} {question.question_type} #{idx}: missing required fragment(s) {missing_required}"
                    )
                    continue
                passes += 1

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"\n{len(failures)} regression issue(s) detected; {passes} check(s) passed.")
        return 1

    print(f"All {passes} question quality regression checks passed.")
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
