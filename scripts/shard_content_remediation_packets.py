#!/usr/bin/env python3
"""Split chapter remediation packets into bounded, independently valid shards."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from export_content_remediation_packets import parse_chapters


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "remediation"
)
ENTITY_TYPES = ("question", "activity", "flashcard")


def compact_audit_findings(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact = copy.deepcopy(value)
    for key, items in list(compact.items()):
        if not isinstance(items, list):
            continue
        compact[key] = [
            item
            for item in items
            if "answer-position" not in str(item).lower()
            and "answer position" not in str(item).lower()
        ]
    return compact


def compact_source_blocks(blocks: object) -> list[dict[str, Any]]:
    if not isinstance(blocks, list):
        return []
    compact = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or "body")
        content = str(block.get("content") or "").strip()
        if not content:
            continue
        if block_type in {"reference", "interpretation"} and len(content) > 15_000:
            continue
        copied = copy.deepcopy(block)
        if len(content) > 120_000:
            copied["content"] = content[:120_000] + "\n[Source block truncated after 120,000 characters.]"
        compact.append(copied)
    return compact


def compact_references(value: object) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return {entity_type: [] for entity_type in ENTITY_TYPES}
    return {
        entity_type: copy.deepcopy(value.get(entity_type, [])[:8])
        if isinstance(value.get(entity_type), list)
        else []
        for entity_type in ENTITY_TYPES
    }


def target_entries(paragraph: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    targets = paragraph.get("targets")
    if not isinstance(targets, dict):
        return []
    entries = []
    for entity_type in ENTITY_TYPES:
        values = targets.get(entity_type)
        if not isinstance(values, list):
            continue
        entries.extend(
            (entity_type, copy.deepcopy(item))
            for item in values
            if isinstance(item, dict)
        )
    return entries


def paragraph_piece(
    paragraph: dict[str, Any],
    entries: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    piece = {
        key: copy.deepcopy(value)
        for key, value in paragraph.items()
        if key not in {"source_text", "source_blocks", "targets", "reference_items"}
    }
    piece["source_blocks"] = compact_source_blocks(paragraph.get("source_blocks"))
    piece["targets"] = {entity_type: [] for entity_type in ENTITY_TYPES}
    for entity_type, item in entries:
        piece["targets"][entity_type].append(item)
    piece["reference_items"] = compact_references(paragraph.get("reference_items"))
    return piece


def split_entries(
    paragraph: dict[str, Any],
    max_items: int,
    max_target_bytes: int,
) -> list[dict[str, Any]]:
    entries = target_entries(paragraph)
    if not entries:
        return []
    chunks: list[list[tuple[str, dict[str, Any]]]] = []
    current: list[tuple[str, dict[str, Any]]] = []
    current_bytes = 0
    for entry in entries:
        entry_bytes = len(json.dumps(entry[1], ensure_ascii=False).encode("utf-8"))
        if current and (
            len(current) >= max_items
            or current_bytes + entry_bytes > max_target_bytes
        ):
            chunks.append(current)
            current = []
            current_bytes = 0
        current.append(entry)
        current_bytes += entry_bytes
    if current:
        chunks.append(current)
    return [paragraph_piece(paragraph, chunk) for chunk in chunks]


def target_counts(paragraphs: list[dict[str, Any]]) -> dict[str, int]:
    return {
        entity_type: sum(
            len(paragraph.get("targets", {}).get(entity_type, []))
            for paragraph in paragraphs
        )
        for entity_type in ENTITY_TYPES
    }


def build_shards(
    packet: dict[str, Any],
    max_items: int,
    max_target_bytes: int,
    max_packet_bytes: int,
    max_packet_items: int,
) -> list[dict[str, Any]]:
    pieces = [
        piece
        for paragraph in packet.get("paragraphs", [])
        if isinstance(paragraph, dict)
        for piece in split_entries(paragraph, max_items, max_target_bytes)
    ]
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for piece in pieces:
        candidate = current + [piece]
        candidate_bytes = len(json.dumps(candidate, ensure_ascii=False).encode("utf-8"))
        candidate_items = sum(target_counts(candidate).values())
        if current and (
            candidate_bytes > max_packet_bytes
            or candidate_items > max_packet_items
        ):
            groups.append(current)
            current = []
        current.append(piece)
    if current:
        groups.append(current)

    shards = []
    for index, paragraphs in enumerate(groups, start=1):
        shard = {
            key: copy.deepcopy(value)
            for key, value in packet.items()
            if key not in {
                "packet_type",
                "target_counts",
                "automated_flag_counts",
                "audit_findings",
                "paragraphs",
            }
        }
        shard["packet_type"] = "chapter_content_remediation_shard"
        shard["target_counts"] = target_counts(paragraphs)
        shard["audit_findings"] = compact_audit_findings(packet.get("audit_findings"))
        shard["shard"] = {
            "index": index,
            "count": len(groups),
            "paragraph_ids": [paragraph["para_id"] for paragraph in paragraphs],
        }
        shard["paragraphs"] = paragraphs
        shards.append(shard)
    return shards


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-14")
    parser.add_argument("--target-source", default="curated")
    parser.add_argument("--packet-dir", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--max-items", type=int, default=16)
    parser.add_argument("--max-target-bytes", type=int, default=110_000)
    parser.add_argument("--max-packet-bytes", type=int, default=240_000)
    parser.add_argument("--max-packet-items", type=int, default=24)
    args = parser.parse_args()

    packet_dir = args.packet_dir or WORKSPACE / "packets" / args.target_source
    out_dir = args.out_dir or WORKSPACE / "packet_shards" / args.target_source
    out_dir.mkdir(parents=True, exist_ok=True)

    for chapter in parse_chapters(args.chapters):
        packet_path = packet_dir / f"chapter_{chapter:02d}.json"
        if not packet_path.exists():
            parser.error(f"packet not found: {packet_path}")
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        if packet.get("target_generation_source") != args.target_source:
            parser.error(f"source mismatch in {packet_path}")
        chapter_dir = out_dir / f"chapter_{chapter:02d}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        for stale in chapter_dir.glob("chapter_*_shard_*.json"):
            stale.unlink()
        shards = build_shards(
            packet,
            args.max_items,
            args.max_target_bytes,
            args.max_packet_bytes,
            args.max_packet_items,
        )
        for index, shard in enumerate(shards, start=1):
            path = chapter_dir / f"chapter_{chapter:02d}_shard_{index:03d}.json"
            path.write_text(
                json.dumps(shard, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        sizes = [len(json.dumps(shard, ensure_ascii=False).encode("utf-8")) for shard in shards]
        print(
            f"chapter {chapter:02d}: {len(shards)} shard(s), "
            f"largest={max(sizes, default=0):,} bytes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
