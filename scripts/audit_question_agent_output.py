#!/usr/bin/env python3
"""Audit authored question output for educational focus and prompt diversity."""

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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_REPORT = ROOT / "docs" / "question-agent-output-audit.md"
DEFAULT_JSON = ROOT / "docs" / "question-agent-output-audit.json"
DEFAULT_BASELINE = ROOT / "docs" / "question-agent-audit-baseline.json"

DOCUMENT_LOCATION_RE = re.compile(
    r"\b(?:under|from|in|paragraph|para|section)\s+(?:the\s+)?"
    r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
NOTE_LOCATION_RE = re.compile(
    r"\b(?:according to|under)\s+(?:the\s+)?note\s+in\s+"
    r"\d+(?:[-\u2212]\d+)+(?:[a-z]\d*)?\b",
    re.IGNORECASE,
)
GENERIC_REFERENCE_RE = re.compile(
    r"\b(?:this|the)\s+(?:paragraph|section|rule|material|example)\b",
    re.IGNORECASE,
)
NEGATIVE_STEM_RE = re.compile(
    r"\b(?:not|except|false|incorrect|least appropriate|doesn't|does not)\b",
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
NUMERIC_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\b|\b(?:mile|miles|feet|foot|minutes?|seconds?|knots?|"
    r"degrees?|percent|frequency|altitude)\b",
    re.IGNORECASE,
)
OPERATIONAL_NUMERIC_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:nautical\s+miles?|nm|feet|foot|minutes?|seconds?|"
    r"knots?|degrees?|percent|mhz|inches?|miles?|hours?)\b",
    re.IGNORECASE,
)
OBLIGATION_RE = re.compile(
    r"\b(?:must|shall|required|do not|may not|only|ensure|issue|provide|"
    r"advise|instruct|coordinate|separate|maintain|terminate)\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "do",
    "does", "for", "from", "has", "have", "how", "if", "in", "is", "it", "its",
    "of", "on", "or", "that", "the", "their", "then", "this", "to", "under",
    "what", "when", "which", "who", "with", "would",
}


@dataclass(frozen=True)
class Question:
    question_id: str
    para_id: str
    question_type: str
    text: str
    explanation: str
    source: str
    correct_answers: tuple[str, ...]

    @property
    def learning_text(self) -> str:
        return f"{self.text} {' '.join(self.correct_answers)} {self.explanation}".strip()


def normalize_space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def tokens(value: object) -> set[str]:
    return {
        token for token in WORD_RE.findall(normalize_space(value).lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def load_questions(db: sqlite3.Connection, sources: tuple[str, ...]) -> list[Question]:
    placeholders = ",".join("?" for _ in sources)
    rows = db.execute(
        f"""
        SELECT q.id, q.para_id, q.question_type, q.question_text,
               q.explanation, q.generation_src,
               GROUP_CONCAT(CASE WHEN c.is_correct = 1 THEN c.choice_text END, '\u241f')
        FROM quiz_questions q
        LEFT JOIN question_choices c ON c.question_id = q.id
        WHERE q.generation_src IN ({placeholders})
        GROUP BY q.id
        ORDER BY q.para_id, q.question_type, q.question_text
        """,
        sources,
    ).fetchall()
    questions = []
    for row in rows:
        correct_answers = tuple(
            answer for answer in normalize_space(row[6]).split("\u241f") if answer
        )
        questions.append(Question(
            question_id=row[0],
            para_id=row[1],
            question_type=row[2],
            text=normalize_space(row[3]),
            explanation=normalize_space(row[4]),
            source=row[5],
            correct_answers=correct_answers,
        ))
    return questions


def prompt_mode(question: Question) -> str:
    text = question.text
    if question.question_type == "fill_blank":
        return "cloze"
    if question.question_type == "true_false":
        return "verification"
    if SCENARIO_RE.search(text) and len(text.split()) >= 22:
        return "scenario"
    if CONDITION_RE.search(text):
        return "condition"
    if NUMERIC_RE.search(text):
        return "numeric"
    if re.search(r"\b(?:sequence|order|first|next|before|after)\b", text, re.I):
        return "sequence"
    if re.search(r"\b(?:which of the following|which option|which action)\b", text, re.I):
        return "discrimination"
    if text.lower().startswith(("who ", "who is", "who must")):
        return "responsibility"
    return "direct_recall"


def concept_signature(question: Question) -> str:
    basis = question.text if question.question_type == "true_false" else (
        " ".join(question.correct_answers) or question.text
    )
    signature_tokens = sorted(tokens(basis))
    return " ".join(signature_tokens[:18]) or normalize_space(basis).lower()


def stem_opening(question: Question) -> str:
    words = normalize_space(question.text).lower().split()[:5]
    return " ".join(re.sub(r"\d+(?:[-\u2212]\d+)+[a-z]?", "<para>", word) for word in words)


def split_source_statements(content_json: str) -> list[str]:
    try:
        blocks = json.loads(content_json)
    except (TypeError, json.JSONDecodeError):
        return []
    statements: list[str] = []
    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict) or block.get("block_type") in {"reference", "interpretation"}:
            continue
        content = normalize_space(block.get("content"))
        if not content:
            continue
        for piece in re.split(r"(?<=[.;:])\s+(?=[A-Z0-9(])|\s+(?=[a-z]\.\s|\d+\.\s)", content):
            piece = normalize_space(piece)
            if len(piece.split()) < 5:
                continue
            if re.search(
                r"\b(?:JO\s+7110|Terms of Reference|Introduction)\b|"
                r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\.{3,}",
                piece,
                re.IGNORECASE,
            ):
                continue
            if (
                OBLIGATION_RE.search(piece)
                or CONDITION_RE.search(piece)
                or OPERATIONAL_NUMERIC_RE.search(piece)
            ):
                statements.append(piece)
    return statements


def source_coverage(
    db: sqlite3.Connection,
    questions_by_para: dict[str, list[Question]],
) -> tuple[dict[str, dict], list[dict]]:
    rows = db.execute("SELECT para_id, content_json FROM paragraphs ORDER BY para_id").fetchall()
    paragraph_metrics: dict[str, dict] = {}
    uncovered: list[dict] = []
    for para_id, content_json in rows:
        essential = split_source_statements(content_json)
        if not essential:
            continue
        question_token_sets = [tokens(question.learning_text) for question in questions_by_para.get(para_id, [])]
        covered = 0
        for statement in essential:
            statement_tokens = tokens(statement)
            best = max((jaccard(statement_tokens, candidate) for candidate in question_token_sets), default=0.0)
            shared = max((len(statement_tokens & candidate) for candidate in question_token_sets), default=0)
            is_covered = best >= 0.16 and shared >= 2
            covered += int(is_covered)
            if not is_covered:
                uncovered.append({
                    "para_id": para_id,
                    "statement": statement,
                    "best_overlap": round(best, 3),
                })
        paragraph_metrics[para_id] = {
            "essential_statements": len(essential),
            "covered_statements": covered,
            "coverage_rate": round(covered / len(essential), 4),
            "question_count": len(questions_by_para.get(para_id, [])),
        }
    return paragraph_metrics, uncovered


def analyze(db_path: Path, sources: tuple[str, ...]) -> dict:
    db = sqlite3.connect(db_path)
    try:
        questions = load_questions(db, sources)
        questions_by_para: dict[str, list[Question]] = defaultdict(list)
        for question in questions:
            questions_by_para[question.para_id].append(question)

        location_dependent = [
            question for question in questions
            if DOCUMENT_LOCATION_RE.search(question.text) or NOTE_LOCATION_RE.search(question.text)
        ]
        generic_reference = [
            question for question in questions if GENERIC_REFERENCE_RE.search(question.text)
        ]
        negative_stems = [question for question in questions if NEGATIVE_STEM_RE.search(question.text)]
        thin_explanations = [question for question in questions if len(question.explanation.split()) < 10]

        near_duplicates: list[dict] = []
        for para_id, para_questions in questions_by_para.items():
            for left, right in combinations(para_questions, 2):
                similarity = jaccard(tokens(left.text), tokens(right.text))
                if similarity >= 0.78:
                    near_duplicates.append({
                        "para_id": para_id,
                        "similarity": round(similarity, 3),
                        "left": left.text,
                        "right": right.text,
                    })

        concept_groups: dict[tuple[str, str], list[Question]] = defaultdict(list)
        for question in questions:
            concept_groups[(question.para_id, concept_signature(question))].append(question)

        repeated_concepts = []
        low_diversity_groups = []
        for (para_id, signature), group in concept_groups.items():
            if len(group) < 2:
                continue
            modes = sorted({prompt_mode(question) for question in group})
            record = {
                "para_id": para_id,
                "concept_signature": signature,
                "question_count": len(group),
                "modes": modes,
                "stems": [question.text for question in group],
            }
            repeated_concepts.append(record)
            if len(modes) == 1:
                low_diversity_groups.append(record)

        paragraph_coverage, uncovered_statements = source_coverage(db, questions_by_para)
        covered_total = sum(item["covered_statements"] for item in paragraph_coverage.values())
        essential_total = sum(item["essential_statements"] for item in paragraph_coverage.values())
        paragraphs_with_multi_mode = sum(
            len({prompt_mode(question) for question in group}) >= 3
            for group in questions_by_para.values()
        )
        paragraph_mode_distribution = Counter(
            len({prompt_mode(question) for question in group})
            for group in questions_by_para.values()
        )
        chapter_breakdown = {}
        for chapter in sorted(
            {question.para_id.split("-", 1)[0] for question in questions},
            key=int,
        ):
            chapter_questions = [
                question for question in questions
                if question.para_id.split("-", 1)[0] == chapter
            ]
            chapter_paragraphs = {
                question.para_id for question in chapter_questions
            }
            chapter_breakdown[chapter] = {
                "questions": len(chapter_questions),
                "paragraphs": len(chapter_paragraphs),
                "location_scaffolded": sum(
                    bool(
                        DOCUMENT_LOCATION_RE.search(question.text)
                        or NOTE_LOCATION_RE.search(question.text)
                    )
                    for question in chapter_questions
                ),
                "negative_stems": sum(
                    bool(NEGATIVE_STEM_RE.search(question.text))
                    for question in chapter_questions
                ),
                "retrieval_modes": dict(
                    Counter(prompt_mode(question) for question in chapter_questions)
                ),
            }

        answer_position_rows = db.execute(
            """
            SELECT c.sort_order, COUNT(*)
            FROM quiz_questions q
            JOIN question_choices c ON c.question_id = q.id
            WHERE q.generation_src IN ({})
              AND q.question_type = 'multiple_choice'
              AND c.is_correct = 1
            GROUP BY c.sort_order
            """.format(",".join("?" for _ in sources)),
            sources,
        ).fetchall()

        metrics = {
            "question_count": len(questions),
            "paragraph_count": len(questions_by_para),
            "source_counts": dict(Counter(question.source for question in questions)),
            "type_counts": dict(Counter(question.question_type for question in questions)),
            "mode_counts": dict(Counter(prompt_mode(question) for question in questions)),
            "location_dependent_count": len(location_dependent),
            "generic_reference_count": len(generic_reference),
            "negative_stem_count": len(negative_stems),
            "thin_explanation_count": len(thin_explanations),
            "near_duplicate_pair_count": len(near_duplicates),
            "repeated_concept_group_count": len(repeated_concepts),
            "low_diversity_concept_group_count": len(low_diversity_groups),
            "paragraphs_with_three_modes": paragraphs_with_multi_mode,
            "paragraph_mode_count_distribution": {
                str(count): paragraphs
                for count, paragraphs in sorted(paragraph_mode_distribution.items())
            },
            "essential_statement_count": essential_total,
            "covered_essential_statement_count": covered_total,
            "essential_statement_coverage_rate": round(
                covered_total / essential_total if essential_total else 1.0,
                4,
            ),
            "correct_answer_positions": {
                str(position): count for position, count in answer_position_rows
            },
            "chapter_breakdown": chapter_breakdown,
            "common_stem_openings": dict(
                Counter(stem_opening(question) for question in questions).most_common(20)
            ),
        }
        return {
            "metrics": metrics,
            "examples": {
                "location_dependent": [
                    {"para_id": item.para_id, "text": item.text, "source": item.source}
                    for item in location_dependent[:40]
                ],
                "generic_reference": [
                    {"para_id": item.para_id, "text": item.text, "source": item.source}
                    for item in generic_reference[:30]
                ],
                "near_duplicates": sorted(
                    near_duplicates, key=lambda item: item["similarity"], reverse=True
                )[:40],
                "low_diversity_concepts": sorted(
                    low_diversity_groups,
                    key=lambda item: item["question_count"],
                    reverse=True,
                )[:40],
                "uncovered_essential_statements": sorted(
                    uncovered_statements,
                    key=lambda item: (item["best_overlap"], item["para_id"]),
                )[:80],
                "lowest_coverage_paragraphs": sorted(
                    (
                        {"para_id": para_id, **values}
                        for para_id, values in paragraph_coverage.items()
                        if values["question_count"] > 0
                    ),
                    key=lambda item: (item["coverage_rate"], -item["essential_statements"]),
                )[:50],
            },
        }
    finally:
        db.close()


def render_markdown(result: dict, sources: tuple[str, ...]) -> str:
    metrics = result["metrics"]
    examples = result["examples"]
    lines = [
        "# Question-Agent Output Audit",
        "",
        f"Sources audited: `{', '.join(sources)}`",
        "",
        "## Corpus Summary",
        "",
        f"- Questions: {metrics['question_count']}",
        f"- Paragraphs represented: {metrics['paragraph_count']}",
        f"- Question types: {json.dumps(metrics['type_counts'], sort_keys=True)}",
        f"- Retrieval modes: {json.dumps(metrics['mode_counts'], sort_keys=True)}",
        f"- Correct-answer positions: {json.dumps(metrics['correct_answer_positions'], sort_keys=True)}",
        f"- Retrieval modes per paragraph: {json.dumps(metrics['paragraph_mode_count_distribution'], sort_keys=True)}",
        "",
        "## Recurring Pitfalls",
        "",
        f"- {metrics['location_dependent_count']} questions include unnecessary paragraph or note-location scaffolding.",
        f"- {metrics['generic_reference_count']} questions use context-light references such as “this paragraph” or “this rule.”",
        f"- {metrics['negative_stem_count']} use negative framing (`NOT`, `EXCEPT`, or equivalent).",
        f"- {metrics['thin_explanation_count']} have explanations shorter than ten words.",
        f"- {metrics['near_duplicate_pair_count']} within-paragraph pairs have at least 0.78 token similarity.",
        "",
        "## Essential-Element Coverage",
        "",
        f"- Heuristic essential statements found: {metrics['essential_statement_count']}",
        f"- Statements matched by agent questions: {metrics['covered_essential_statement_count']}",
        f"- Estimated coverage: {metrics['essential_statement_coverage_rate']:.1%}",
        "",
        "This extracts imperative, conditional, and numeric source statements and checks overlap with each question, correct answer, and explanation. It is a triage signal, not a legal determination.",
        "",
        "## Repetition Versus Variety",
        "",
        f"- Repeated concept groups: {metrics['repeated_concept_group_count']}",
        f"- Repeated groups using only one retrieval mode: {metrics['low_diversity_concept_group_count']}",
        f"- Paragraphs with at least three retrieval modes: {metrics['paragraphs_with_three_modes']}",
        "",
        "Healthy reinforcement asks the same concept through different cognitive operations. Rewording a direct-recall stem without changing the retrieval task is duplication.",
        "",
        "## Chapter Pattern",
        "",
        "| Chapter | Questions | Paragraphs | Location scaffold | Negative stems |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for chapter, values in metrics["chapter_breakdown"].items():
        lines.append(
            f"| {chapter} | {values['questions']} | {values['paragraphs']} | "
            f"{values['location_scaffolded']} | {values['negative_stems']} |"
        )
    lines.extend([
        "",
        "## Common Stem Openings",
        "",
    ])
    for opening, count in list(metrics["common_stem_openings"].items())[:12]:
        lines.append(f"- `{opening}`: {count}")
    lines.extend([
        "",
        "## Highest-Priority Remediation",
        "",
        "1. Remove paragraph-number scaffolding unless the task is explicitly source navigation.",
        "2. Define each paragraph’s essential obligations, conditions, exceptions, minima, and prescribed wording before writing.",
        "3. Build concept families deliberately: recall, condition/exception discrimination, scenario, and exact recall only where fidelity matters.",
        "4. Prefer positive operational decisions over `NOT/EXCEPT` stems.",
        "5. Require explanations to state the controlling principle and why the strongest distractor fails.",
        "",
        "## Example Location-Dependent Questions",
        "",
    ])
    for item in examples["location_dependent"][:12]:
        lines.append(f"- `{item['para_id']}`: {item['text']}")
    lines.extend(["", "## Example Near-Duplicates", ""])
    for item in examples["near_duplicates"][:10]:
        lines.append(
            f"- `{item['para_id']}` ({item['similarity']:.2f}): "
            f"“{item['left']}” / “{item['right']}”"
        )
    lines.extend(["", "## Lowest Estimated Essential-Element Coverage", ""])
    for item in examples["lowest_coverage_paragraphs"][:15]:
        lines.append(
            f"- `{item['para_id']}`: {item['covered_statements']}/"
            f"{item['essential_statements']} ({item['coverage_rate']:.0%}), "
            f"{item['question_count']} questions"
        )
    return "\n".join(lines) + "\n"


def regression_failures(current: dict, baseline: dict) -> list[str]:
    failures = []
    for key in (
        "location_dependent_count",
        "generic_reference_count",
        "thin_explanation_count",
        "near_duplicate_pair_count",
        "low_diversity_concept_group_count",
    ):
        if current.get(key, 0) > baseline.get(key, 0):
            failures.append(f"{key} increased: {current.get(key)} > {baseline.get(key)}")
    if current.get("essential_statement_coverage_rate", 0) < baseline.get(
        "essential_statement_coverage_rate", 0
    ):
        failures.append(
            "essential_statement_coverage_rate decreased: "
            f"{current.get('essential_statement_coverage_rate')} < "
            f"{baseline.get('essential_statement_coverage_rate')}"
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

    sources = tuple(source.strip() for source in args.sources.split(",") if source.strip())
    result = analyze(args.db, sources)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(result, sources), encoding="utf-8")
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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
