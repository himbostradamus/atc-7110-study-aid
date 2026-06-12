#!/usr/bin/env python3
"""Publish a validated, overlap-reviewed content-expansion pass."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "app" / "data"
STAGING = DATA / "content_expansion_staging"


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


def finding_key(batch: str, finding: dict[str, Any]) -> str:
    return "|".join((
        batch,
        str(finding["entity_type"]),
        str(finding["para_id"]),
        str(finding["index"]),
    ))


def assert_overlap_reviewed(audit_path: Path, disposition_path: Path) -> None:
    audit = load_json(audit_path)
    disposition = load_json(disposition_path)
    accepted = disposition.get("accepted", {})
    if not isinstance(accepted, dict):
        raise ValueError("Overlap disposition accepted field must be an object")

    findings = [
        finding_key(report["batch"], finding)
        for report in audit.get("reports", [])
        for finding in report.get("findings", [])
    ]
    missing = sorted(set(findings) - set(accepted))
    stale = sorted(set(accepted) - set(findings))
    if missing or stale:
        raise ValueError(
            f"Overlap disposition mismatch; missing={missing}, stale={stale}"
        )


def validate_batches(
    batches: list[Path],
    db_path: Path,
    generation_source: str,
) -> None:
    validator = ROOT / "scripts" / "validate_question_authoring_batch.py"
    for batch in batches:
        subprocess.run(
            [
                "python",
                str(validator),
                str(batch),
                "--db",
                str(db_path),
                "--strict",
                "--ignore-existing-generation-source",
                generation_source,
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
    subprocess.run(
        [
            "python",
            str(ROOT / "scripts" / "validate_content_expansion_runtime.py"),
            *[str(batch) for batch in batches],
            "--db",
            str(db_path),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def append_items(
    target: dict[str, dict[str, Any]],
    family: str,
    chapter: int,
    section: dict[str, Any],
    publication_id: str,
    generation_source: str,
) -> int:
    added = 0
    for para_id, override in section.items():
        if not isinstance(override, dict):
            continue
        items = override.get("items", [])
        if not isinstance(items, list):
            raise ValueError(f"{family}.{para_id}.items must be a list")
        destination = target.setdefault(para_id, {"append_items": True, "items": []})
        activity_type_counts: Counter[str] = Counter()
        for index, raw_item in enumerate(items):
            if not isinstance(raw_item, dict):
                raise ValueError(f"{family}.{para_id}.items[{index}] must be an object")
            published = copy.deepcopy(raw_item)
            published["publication_id"] = (
                f"{publication_id}:chapter-{chapter:02d}:{family}:{para_id}:{index}"
            )
            item_generation_source = generation_source
            if family == "activities":
                activity_type = str(published.get("activity_type") or "")
                activity_type_counts[activity_type] += 1
                if activity_type_counts[activity_type] > 1:
                    item_generation_source = (
                        f"{generation_source}_{activity_type_counts[activity_type]}"
                    )
            published["generation_source"] = item_generation_source
            destination["items"].append(published)
            added += 1
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT / "frontend" / "public" / "curriculum.db",
    )
    parser.add_argument("--expected-questions", type=int)
    parser.add_argument("--expected-activities", type=int)
    parser.add_argument("--expected-flashcards", type=int)
    args = parser.parse_args()

    pass_tag = f"{args.pass_number:02d}"
    publication_id = f"content-expansion-pass-{pass_tag}"
    generation_source = f"content_expansion_pass_{pass_tag}"
    batches = sorted(STAGING.glob(f"chapter_*_pass_{pass_tag}.json"))
    if len(batches) != 14:
        raise ValueError(f"Expected 14 chapter batches, found {len(batches)}")

    audit_path = STAGING / f"pass_{pass_tag}_overlap_audit_final.json"
    disposition_path = STAGING / f"pass_{pass_tag}_overlap_disposition.json"
    assert_overlap_reviewed(audit_path, disposition_path)
    validate_batches(batches, args.db, generation_source)

    questions: dict[str, dict[str, Any]] = {}
    activities: dict[str, dict[str, Any]] = {}
    flashcards: dict[str, dict[str, Any]] = {}
    counts = {"questions": 0, "activities": 0, "flashcards": 0}

    for batch in batches:
        payload = load_json(batch)
        chapter = int(batch.stem.split("_")[1])
        for family, target in (
            ("questions", questions),
            ("activities", activities),
            ("flashcards", flashcards),
        ):
            counts[family] += append_items(
                target,
                family,
                chapter,
                payload.get(family, {}),
                publication_id,
                generation_source,
            )

    expected = {
        "questions": args.expected_questions,
        "activities": args.expected_activities,
        "flashcards": args.expected_flashcards,
    }
    for family, expected_count in expected.items():
        if expected_count is not None and counts[family] != expected_count:
            raise ValueError(
                f"Unexpected {family} count: {counts[family]}; expected {expected_count}"
            )

    overrides_out = DATA / f"curated_overrides_zzzzzzzzz_content_expansion_pass_{pass_tag}.json"
    flashcards_out = DATA / f"curated_flashcards_zzzzzzzzz_content_expansion_pass_{pass_tag}.json"
    write_json(
        overrides_out,
        {
            "publication_batch": publication_id,
            "questions": questions,
            "activities": activities,
        },
    )
    write_json(
        flashcards_out,
        {
            "publication_batch": publication_id,
            "generation_source": generation_source,
            "flashcards": flashcards,
        },
    )
    print(
        f"Published {publication_id}: {counts['questions']} questions, "
        f"{counts['activities']} activities, {counts['flashcards']} flashcards."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
