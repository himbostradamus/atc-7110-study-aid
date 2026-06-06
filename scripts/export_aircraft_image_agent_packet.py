#!/usr/bin/env python3
"""Export aircraft image target packets for asynchronous search agents."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_AIRCRAFT_ROWS = Path("backend/app/data/curated_aircraft_jo7360_weighted_rows.csv")
DEFAULT_MANIFEST = Path("frontend/public/aircraft-images/manifest.jsonl")
DEFAULT_OUT_DIR = Path("backend/app/data/aircraft_image_search_workspace/packets")


def clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {key: clean(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
            if clean(row.get("type_designator"))
        ]


def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def read_review_decisions(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    decisions = raw.get("decisions", raw if isinstance(raw, dict) else {})
    out = {}
    for key, value in decisions.items():
        if isinstance(value, dict):
            status = clean(value.get("identity_status"))
        else:
            status = clean(value)
        if key and status:
            out[str(key)] = status
    return out


def manifest_counts(records: list[dict], review_decisions: dict[str, str]) -> dict[str, Counter]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        designator = clean(record.get("type_designator")).upper()
        if not designator:
            continue
        key = clean(record.get("sha256"))
        status = review_decisions.get(key) or clean(record.get("identity_status")) or "not_reviewed"
        counts[designator][status] += 1
        counts[designator]["total"] += 1
    return counts


def row_matches_group(row: dict, group: str) -> bool:
    if not group or group == "all":
        return True
    return clean(row.get("group")).lower() == group.lower()


def chunked(rows: list[dict], size: int) -> list[list[dict]]:
    if size <= 0:
        return [rows]
    return [rows[index:index + size] for index in range(0, len(rows), size)]


def packet_row(row: dict, counts: dict[str, Counter], target_approved: int) -> dict:
    designator = clean(row.get("type_designator")).upper()
    type_counts = counts.get(designator, Counter())
    approved = int(type_counts.get("approved", 0))
    return {
        "type_designator": designator,
        "group": clean(row.get("group")),
        "description": clean(row.get("description")),
        "engine_aircraft_class": clean(row.get("engine_aircraft_class")),
        "wake_turbulence": clean(row.get("wtc")),
        "consolidated_wake_turbulence": clean(row.get("cwt")),
        "same_runway_separation": clean(row.get("srs")),
        "lahso": clean(row.get("lahso")),
        "manufacturer_model": clean(row.get("manufacturer_model")),
        "existing_manifest_count": int(type_counts.get("total", 0)),
        "existing_approved_count": approved,
        "needed_approved_count": max(0, target_approved - approved),
    }


def write_packets(args: argparse.Namespace) -> list[Path]:
    rows = read_rows(args.input)
    type_filter = {value.strip().upper() for value in args.types.split(",") if value.strip()}
    rows = [
        row for row in rows
        if row_matches_group(row, args.group)
        and (not type_filter or clean(row.get("type_designator")).upper() in type_filter)
    ]
    records = read_manifest(args.manifest)
    decisions = read_review_decisions(args.review_json)
    counts = manifest_counts(records, decisions)

    rows = sorted(
        rows,
        key=lambda row: (
            packet_row(row, counts, args.target_approved)["existing_approved_count"],
            int(clean(row.get("rank")) or 999999),
            clean(row.get("type_designator")),
        ),
    )
    if args.only_needing_images:
        rows = [
            row for row in rows
            if packet_row(row, counts, args.target_approved)["needed_approved_count"] > 0
        ]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    generated_at = datetime.now(timezone.utc).isoformat()
    for index, batch in enumerate(chunked(rows, args.batch_size), 1):
        packet = {
            "generated_at": generated_at,
            "packet_kind": "aircraft_image_search_targets",
            "group": args.group,
            "batch_index": index,
            "target_approved_per_type": args.target_approved,
            "source_files": {
                "aircraft_rows": args.input.as_posix(),
                "current_manifest": args.manifest.as_posix(),
                "review_json": args.review_json.as_posix() if args.review_json else "",
            },
            "agent_output_contract": {
                "write_only_under": "backend/app/data/aircraft_image_search_workspace/outputs/<agent_slug>/",
                "do_not_edit": [
                    "frontend/**",
                    "frontend/public/aircraft-images/**",
                    "frontend/dist/**",
                    "backend/app/data/curated_*",
                    "database files",
                ],
            },
            "rows": [packet_row(row, counts, args.target_approved) for row in batch],
        }
        path = args.out_dir / f"aircraft_image_targets_{args.group}_{index:03d}.json"
        path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_AIRCRAFT_ROWS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--review-json", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--group", default="all", help="CSV group to export: cessna, beechcraft, piper, secondary, or all.")
    parser.add_argument("--types", default="", help="Comma-separated type designators. Overrides group breadth.")
    parser.add_argument("--batch-size", type=int, default=18)
    parser.add_argument("--target-approved", type=int, default=3)
    parser.add_argument("--only-needing-images", action="store_true", default=True)
    parser.add_argument("--include-covered", dest="only_needing_images", action="store_false")
    args = parser.parse_args()

    paths = write_packets(args)
    for path in paths:
        print(path)
    print(f"Wrote {len(paths)} packet(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

