#!/usr/bin/env python3
"""Publish validated expansion staging files as append-only curated content."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "app" / "data"
STAGING = DATA / "content_expansion_staging"
AUDIT_REPORT = DATA / "content_expansion_audits" / "remediation_pass_01.json"
OVERRIDES_OUT = DATA / "curated_overrides_zzzzzzzzz_content_expansion_pass_01.json"
FLASHCARDS_OUT = DATA / "curated_flashcards_zzzzzzzzz_content_expansion_pass_01.json"
PASS_ID = "content-expansion-pass-01"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def assert_audit_ready() -> None:
    report = load_json(AUDIT_REPORT)
    summary = report.get("summary", {})
    if summary.get("critical") != 3 or summary.get("major") != 25:
        raise ValueError("Remediation report does not cover the expected audit findings")
    unresolved = [
        finding
        for finding in report.get("findings", [])
        if finding.get("status") not in {
            "already_satisfied",
            "fixed",
            "moved",
            "moved_and_fixed",
            "removed",
            "retained",
            "split",
        }
    ]
    if unresolved:
        raise ValueError(f"Unresolved critical/major findings remain: {unresolved}")


def append_items(
    target: dict[str, dict[str, Any]],
    family: str,
    chapter: int,
    section: dict[str, Any],
) -> int:
    added = 0
    for para_id, override in section.items():
        if not isinstance(override, dict):
            continue
        items = override.get("items", [])
        if not isinstance(items, list):
            raise ValueError(f"{family}.{para_id}.items must be a list")
        destination = target.setdefault(para_id, {"append_items": True, "items": []})
        for index, raw_item in enumerate(items):
            if not isinstance(raw_item, dict):
                raise ValueError(f"{family}.{para_id}.items[{index}] must be an object")
            published = copy.deepcopy(raw_item)
            published["publication_id"] = (
                f"{PASS_ID}:chapter-{chapter:02d}:{family}:{para_id}:{index}"
            )
            if family == "activities":
                published["generation_source"] = "content_expansion_pass_01"
            destination["items"].append(published)
            added += 1
    return added


def main() -> int:
    assert_audit_ready()
    questions: dict[str, dict[str, Any]] = {}
    activities: dict[str, dict[str, Any]] = {}
    flashcards: dict[str, dict[str, Any]] = {}
    counts = {"questions": 0, "activities": 0, "flashcards": 0}

    batches = sorted(STAGING.glob("chapter_*_pass_01.json"))
    if len(batches) != 14:
        raise ValueError(f"Expected 14 chapter batches, found {len(batches)}")

    for batch in batches:
        payload = load_json(batch)
        chapter = int(batch.stem.split("_")[1])
        counts["questions"] += append_items(
            questions,
            "questions",
            chapter,
            payload.get("questions", {}),
        )
        counts["activities"] += append_items(
            activities,
            "activities",
            chapter,
            payload.get("activities", {}),
        )
        counts["flashcards"] += append_items(
            flashcards,
            "flashcards",
            chapter,
            payload.get("flashcards", {}),
        )

    expected = {"questions": 310, "activities": 116, "flashcards": 283}
    if counts != expected:
        raise ValueError(f"Unexpected publication counts: {counts}; expected {expected}")

    write_json(
        OVERRIDES_OUT,
        {
            "publication_batch": PASS_ID,
            "questions": questions,
            "activities": activities,
        },
    )
    write_json(
        FLASHCARDS_OUT,
        {
            "publication_batch": PASS_ID,
            "default_generation_source": "question_agent",
            "flashcards": flashcards,
        },
    )
    print(
        f"Published staging manifests: {counts['questions']} questions, "
        f"{counts['activities']} activities, {counts['flashcards']} flashcards."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
