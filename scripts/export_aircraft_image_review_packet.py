#!/usr/bin/env python3
"""Export aircraft image review packets for asynchronous review agents."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PACKET_DIR = Path("backend/app/data/aircraft_image_search_workspace/packets")
DEFAULT_MANIFESTS = [
    Path("frontend/public/aircraft-images/manifest.jsonl"),
]
SEARCH_OUTPUT_GLOB = "backend/app/data/aircraft_image_search_workspace/outputs/*/aircraft-images/manifest.jsonl"


def clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw["_manifest_path"] = path.as_posix()
        records.append(raw)
    return records


def stable_key(record: dict) -> str:
    return clean(record.get("sha256")) or clean(record.get("image_url")) or clean(record.get("source_page")) or clean(record.get("public_path"))


def candidate_record(record: dict) -> dict:
    return {
        "key": stable_key(record),
        "type_designator": clean(record.get("type_designator")).upper(),
        "aircraft_group": clean(record.get("aircraft_group")),
        "manufacturer_model": clean(record.get("manufacturer_model")),
        "file_title": clean(record.get("file_title")),
        "source_page": clean(record.get("source_page")),
        "public_path": clean(record.get("public_path")),
        "image_url": clean(record.get("image_url")),
        "license_short_name": clean(record.get("license_short_name")),
        "artist": clean(record.get("artist")),
        "credit": clean(record.get("credit")),
        "width": record.get("width") or 0,
        "height": record.get("height") or 0,
        "current_identity_status": clean(record.get("identity_status")) or "not_reviewed",
        "collector_status": clean(record.get("status")),
        "manifest_path": clean(record.get("_manifest_path")),
    }


def collect_records(manifests: list[Path], include_search_outputs: bool) -> list[dict]:
    records = []
    for path in manifests:
        records.extend(read_manifest(path))
    if include_search_outputs:
        for path in sorted(Path(".").glob(SEARCH_OUTPUT_GLOB)):
            records.extend(read_manifest(path))

    deduped = []
    seen = set()
    for record in records:
        key = stable_key(record)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def chunked(records: list[dict], size: int) -> list[list[dict]]:
    if size <= 0:
        return [records]
    return [records[index:index + size] for index in range(0, len(records), size)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    parser.add_argument("--include-search-outputs", action="store_true", default=True)
    parser.add_argument("--live-only", dest="include_search_outputs", action="store_false")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_PACKET_DIR)
    parser.add_argument("--focus", choices=["wrong_aircraft", "not_recognition_image", "bad_angle"], required=True)
    parser.add_argument("--batch-size", type=int, default=35)
    parser.add_argument("--statuses", default="not_reviewed,bad_angle,bad_crop,wrong_aircraft,not_recognition_image,license_hold")
    args = parser.parse_args()

    manifests = args.manifest or DEFAULT_MANIFESTS
    wanted_statuses = {status.strip() for status in args.statuses.split(",") if status.strip()}
    records = collect_records(manifests, args.include_search_outputs)
    candidates = [
        candidate_record(record)
        for record in records
        if (clean(record.get("identity_status")) or "not_reviewed") in wanted_statuses
    ]
    candidates = sorted(candidates, key=lambda item: (item["type_designator"], item["file_title"], item["key"]))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    paths = []
    for index, batch in enumerate(chunked(candidates, args.batch_size), 1):
        packet = {
            "generated_at": generated_at,
            "packet_kind": "aircraft_image_review",
            "focus": args.focus,
            "batch_index": index,
            "review_statuses": [
                "approved",
                "wrong_aircraft",
                "not_recognition_image",
                "bad_angle",
                "bad_crop",
                "license_hold",
                "not_reviewed",
            ],
            "agent_output_contract": {
                "write_decisions_to": "backend/app/data/aircraft_image_search_workspace/outputs/<review_slug>/review_decisions.json",
                "do_not_edit": [
                    "frontend/**",
                    "frontend/public/aircraft-images/**",
                    "frontend/dist/**",
                    "backend/app/data/curated_*",
                    "database files",
                    "search-agent manifests",
                ],
            },
            "candidates": batch,
        }
        path = args.out_dir / f"aircraft_image_review_{args.focus}_{index:03d}.json"
        path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        paths.append(path)

    for path in paths:
        print(path)
    print(f"Wrote {len(paths)} review packet(s) for focus={args.focus}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

