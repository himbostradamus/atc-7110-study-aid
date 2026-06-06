#!/usr/bin/env python3
"""
Audit table, figure, visual, and minima learning activities in curriculum.db.

This is intentionally read-only. It checks whether activities tagged as
table/figure/minima practice contain enough source context to behave like
source-use exercises instead of ordinary recall questions.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


TARGET_TYPES = {"table_lookup", "visual_interpretation", "minima_rule_check"}
STRUCTURED_SOURCE_KEYS = {
    "source_kind",
    "source_label",
    "source_ref",
    "table_ref",
    "figure_ref",
    "visual_ref",
    "lookup_context",
    "given",
    "task",
    "source_excerpt",
    "image_asset",
    "page",
    "bbox",
}
TABLE_RE = re.compile(r"\b(?:table|tbl\.?|row|column)\b", re.I)
FIGURE_RE = re.compile(r"\b(?:fig\.?|figure|diagram|depict|shown|visual|geometry|layout)\b", re.I)
LOOSE_TABLE_FIGURE_CUE_RE = re.compile(
    r"\b(?:table|tbl\.?|figure|fig\.?|diagram|appendix|illustrat|depict|shown below|chart)\b",
    re.I,
)
STRICT_TABLE_FIGURE_CUE_RE = re.compile(r"\b(?:TBL|FIG)\s*\d", re.I)
TRUE_FALSE = {"true", "false"}


@dataclass(frozen=True)
class ActivityIssue:
    para_id: str
    activity_type: str
    issue: str
    question: str


def load_json(value: str | None) -> object:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def content_blocks(content: object) -> list[dict]:
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    if isinstance(content, dict):
        blocks = content.get("blocks")
        if isinstance(blocks, list):
            return [block for block in blocks if isinstance(block, dict)]
    return []


def collapse(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def payload_text(payload: dict) -> str:
    return collapse(json.dumps(payload, ensure_ascii=False))


def prompt_text(payload: dict) -> str:
    return collapse(
        " ".join(
            str(payload.get(key) or "")
            for key in (
                "source_label",
                "source_kind",
                "table_ref",
                "figure_ref",
                "visual_ref",
                "instruction",
                "question_text",
                "prompt",
                "situation",
                "clearance",
            )
        )
    )


def choice_labels(payload: dict) -> list[str]:
    choices = payload.get("choices") or payload.get("options") or []
    if not isinstance(choices, list):
        return []
    labels: list[str] = []
    for choice in choices:
        if isinstance(choice, dict):
            labels.append(collapse(choice.get("text") or choice.get("label") or choice.get("answer")).lower())
        else:
            labels.append(collapse(choice).lower())
    return labels


def has_structured_source(payload: dict) -> bool:
    return any(key in payload and payload.get(key) not in (None, "", []) for key in STRUCTURED_SOURCE_KEYS)


def paragraph_text(row: sqlite3.Row) -> str:
    blocks = content_blocks(load_json(row["content_json"]))
    return " ".join(collapse(block.get("content")) for block in blocks)


def paragraph_has_loose_cue(row: sqlite3.Row) -> bool:
    if int(row["has_visual"] or 0):
        return True
    return bool(LOOSE_TABLE_FIGURE_CUE_RE.search(paragraph_text(row)))


def paragraph_has_strict_cue(row: sqlite3.Row) -> bool:
    return bool(STRICT_TABLE_FIGURE_CUE_RE.search(paragraph_text(row)))


def audit(db: sqlite3.Connection) -> tuple[dict, list[ActivityIssue], list[sqlite3.Row]]:
    activities = db.execute(
        """
        SELECT a.id, a.para_id, a.activity_type, a.generation_src, a.content_json, p.chapter, p.section, p.title
        FROM activities a
        JOIN paragraphs p ON p.id = a.paragraph_db_id
        WHERE a.activity_type IN ('table_lookup', 'visual_interpretation', 'minima_rule_check')
        ORDER BY p.chapter, p.section, a.para_id, a.activity_type, a.id
        """
    ).fetchall()
    paragraphs = db.execute(
        """
        SELECT id, chapter, section, para_id, title, has_visual, content_json
        FROM paragraphs
        ORDER BY chapter, section, para_id
        """
    ).fetchall()

    activity_paras = {row["para_id"] for row in activities}
    loose_candidate_paragraphs = [row for row in paragraphs if paragraph_has_loose_cue(row)]
    loose_missing_candidates = [row for row in loose_candidate_paragraphs if row["para_id"] not in activity_paras]
    strict_candidate_paragraphs = [row for row in paragraphs if paragraph_has_strict_cue(row)]
    strict_missing_candidates = [row for row in strict_candidate_paragraphs if row["para_id"] not in activity_paras]

    counts_by_type = Counter(row["activity_type"] for row in activities)
    counts_by_src = Counter((row["activity_type"], row["generation_src"]) for row in activities)
    counts_by_chapter = Counter((row["chapter"], row["activity_type"]) for row in activities)
    payload_keys: dict[str, Counter] = defaultdict(Counter)
    issue_counts: Counter = Counter()
    issues: list[ActivityIssue] = []

    for row in activities:
        payload_obj = load_json(row["content_json"])
        payload = payload_obj if isinstance(payload_obj, dict) else {}
        for key in payload:
            payload_keys[row["activity_type"]][key] += 1

        all_text = payload_text(payload)
        visible_text = prompt_text(payload)
        labels = choice_labels(payload)
        question = collapse(payload.get("question_text") or payload.get("prompt") or payload.get("instruction"))

        checks: list[tuple[bool, str]] = [
            (not has_structured_source(payload), "missing structured table/figure/source metadata"),
            (set(labels) == TRUE_FALSE and len(labels) == 2, "true/false format weak for lookup practice"),
        ]
        if row["activity_type"] == "table_lookup":
            checks.extend(
                [
                    (not TABLE_RE.search(all_text), "no table language anywhere in payload"),
                    (not TABLE_RE.search(visible_text), "table source not visible before answer"),
                ]
            )
        elif row["activity_type"] == "visual_interpretation":
            checks.extend(
                [
                    (not FIGURE_RE.search(all_text), "no figure/diagram language anywhere in payload"),
                    (not FIGURE_RE.search(visible_text), "figure/diagram source not visible before answer"),
                ]
            )
        elif row["activity_type"] == "minima_rule_check":
            checks.append((not re.search(r"\b(?:NM|mile|feet|degree|minute|second|FL|altitude|distance|minim)", all_text, re.I), "no numeric/minima language"))

        for failed, issue in checks:
            if not failed:
                continue
            issue_counts[(row["activity_type"], issue)] += 1
            issues.append(ActivityIssue(row["para_id"], row["activity_type"], issue, question))

    summary = {
        "activity_count": len(activities),
        "loose_candidate_paragraph_count": len(loose_candidate_paragraphs),
        "loose_missing_candidate_count": len(loose_missing_candidates),
        "strict_candidate_paragraph_count": len(strict_candidate_paragraphs),
        "strict_missing_candidate_count": len(strict_missing_candidates),
        "counts_by_type": counts_by_type,
        "counts_by_src": counts_by_src,
        "counts_by_chapter": counts_by_chapter,
        "payload_keys": payload_keys,
        "issue_counts": issue_counts,
    }
    return summary, issues, loose_missing_candidates, strict_missing_candidates


def print_counter(title: str, counter: Counter, limit: int | None = None) -> None:
    print(f"\n{title}")
    rows = sorted(counter.items(), key=lambda item: (item[0] if not isinstance(item[0], tuple) else item[0]))
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        print("  none")
        return
    for key, value in rows:
        if isinstance(key, tuple):
            key = " / ".join(str(part) for part in key)
        print(f"  {key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="curriculum.db", help="Path to SQLite curriculum DB")
    parser.add_argument("--limit", type=int, default=30, help="Maximum example rows to print per issue section")
    args = parser.parse_args()

    db = sqlite3.connect(Path(args.db).resolve())
    db.row_factory = sqlite3.Row
    try:
        summary, issues, loose_missing_candidates, strict_missing_candidates = audit(db)
    finally:
        db.close()

    print("Table/Figure Learning Audit")
    print(f"Activities tagged table/visual/minima: {summary['activity_count']}")
    print(f"Paragraphs explicitly citing TBL/FIG:  {summary['strict_candidate_paragraph_count']}")
    print(f"TBL/FIG paragraphs without these types:{summary['strict_missing_candidate_count']}")
    print(f"Loose/general source cues:             {summary['loose_candidate_paragraph_count']}")
    print(f"Loose cues without these types:        {summary['loose_missing_candidate_count']}")

    print_counter("Counts by type", summary["counts_by_type"])
    print_counter("Counts by type/source", summary["counts_by_src"])
    print_counter("Counts by chapter/type", summary["counts_by_chapter"])

    print("\nPayload keys by type")
    for activity_type in sorted(summary["payload_keys"]):
        keys = ", ".join(f"{key}={count}" for key, count in summary["payload_keys"][activity_type].most_common())
        print(f"  {activity_type}: {keys or 'none'}")

    print_counter("Issue counts", summary["issue_counts"])

    print("\nIssue examples")
    for issue in issues[: max(args.limit, 0)]:
        print(f"  {issue.para_id} {issue.activity_type}: {issue.issue} :: {issue.question[:180]}")

    print("\nLoose/general source-cue paragraphs without table/visual/minima activity")
    print("  Informational only: often external charts, appendices, Chart Supplement, AIP, or non-7110 source references.")
    for row in loose_missing_candidates[: max(args.limit, 0)]:
        print(f"  {row['para_id']} {row['title']}")

    print("\nExplicit TBL/FIG paragraphs missing table/visual/minima activity")
    for row in strict_missing_candidates[: max(args.limit, 0)]:
        print(f"  {row['para_id']} {row['title']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
