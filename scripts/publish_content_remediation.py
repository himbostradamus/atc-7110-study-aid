#!/usr/bin/env python3
"""Publish validated agent remediation manifests as durable tracked operations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "remediation"
)
DEFAULT_OUT = ROOT / "backend" / "app" / "data" / "content_remediation"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_index(packet: dict[str, Any]) -> dict[str, tuple[str, str, dict[str, Any]]]:
    indexed: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for paragraph in packet.get("paragraphs", []):
        para_id = str(paragraph.get("para_id") or "")
        for entity_type, items in paragraph.get("targets", {}).items():
            for item in items:
                indexed[str(item["id"])] = (entity_type, para_id, item)
    return indexed


def build_match(entity_type: str, item: dict[str, Any]) -> dict[str, Any]:
    if entity_type == "question":
        return {
            "question_text": item["question_text"],
            "question_type": item["question_type"],
        }
    if entity_type == "flashcard":
        return {
            "front": item["front"],
            "back": item["back"],
            "card_type": item["card_type"],
        }
    if entity_type == "activity":
        return {
            "activity_type": item["activity_type"],
            "content": item["content"],
        }
    raise ValueError(f"Unsupported entity type: {entity_type}")


def publish_chapter(chapter: int, out_dir: Path) -> tuple[Path, int]:
    packet_path = WORKSPACE / "packets" / f"chapter_{chapter:02d}.json"
    manifest_path = (
        WORKSPACE / "outputs" / f"chapter_{chapter:02d}"
        / f"chapter_{chapter:02d}_pass_01.json"
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    indexed = target_index(packet)
    operations: list[dict[str, Any]] = []

    for decision in manifest.get("decisions", []):
        item_id = str(decision.get("item_id") or "")
        if item_id not in indexed:
            raise ValueError(f"Chapter {chapter:02d}: unknown item_id {item_id}")
        entity_type, para_id, original = indexed[item_id]
        if entity_type != decision.get("entity_type") or para_id != decision.get("para_id"):
            raise ValueError(f"Chapter {chapter:02d}: target metadata mismatch for {item_id}")

        operation = {
            "entity_type": entity_type,
            "para_id": para_id,
            "action": decision["action"],
            "severity": decision["severity"],
            "categories": decision.get("categories", []),
            "problem": decision["problem"],
            "source_basis": decision["source_basis"],
            "match": build_match(entity_type, original),
        }
        if decision["action"] in {"replace", "split"}:
            replacements = decision["replacement"]
            if decision["action"] == "replace":
                replacements = [replacements]
            operation["replacements"] = replacements
        operations.append(operation)

    payload = {
        "version": 1,
        "chapter": chapter,
        "target_generation_source": packet["target_generation_source"],
        "packet_sha256": file_sha256(packet_path),
        "manifest_sha256": file_sha256(manifest_path),
        "summary": manifest.get("summary", {}),
        "operations": operations,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"chapter_{chapter:02d}.json"
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path, len(operations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-14")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    from export_content_remediation_packets import parse_chapters

    for chapter in parse_chapters(args.chapters):
        output_path, count = publish_chapter(chapter, args.out_dir)
        print(f"chapter {chapter:02d}: {count} operations -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
