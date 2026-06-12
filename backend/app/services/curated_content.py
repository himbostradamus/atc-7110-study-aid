"""
Curated activity/question overrides for high-value paragraphs.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_PATH = DATA_DIR / "curated_overrides.json"


def _empty_override_map() -> dict:
    return {"activities": {}, "questions": {}}


def _append_item_key(top_level_key: str, item: object) -> tuple[str, ...]:
    if not isinstance(item, dict):
        return ("raw", json.dumps(item, sort_keys=True, ensure_ascii=True))
    publication_id = str(item.get("publication_id") or "").strip()
    if publication_id:
        return ("publication_id", publication_id)
    if top_level_key == "questions":
        return (
            "question",
            str(item.get("question_type") or "").strip().lower(),
            str(item.get("question_text") or "").strip().lower(),
        )
    return (
        "activity",
        str(item.get("activity_type") or "").strip().lower(),
        json.dumps(item, sort_keys=True, ensure_ascii=True),
    )


def _merge_append_items(
    top_level_key: str,
    existing: dict,
    override: dict,
) -> dict:
    combined = copy.deepcopy(existing)

    merged_items: list[object] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in [
        *existing.get("appended_items", []),
        *override.get("items", []),
    ]:
        key = _append_item_key(top_level_key, candidate)
        if key in seen:
            continue
        seen.add(key)
        merged_items.append(copy.deepcopy(candidate))
    combined["appended_items"] = merged_items
    return combined


def _merge_override_file(merged: dict, path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for top_level_key in ("activities", "questions"):
        section = payload.get(top_level_key, {})
        if not isinstance(section, dict):
            continue
        merged_section = merged[top_level_key]
        for para_id, override in section.items():
            if not isinstance(override, dict):
                merged_section[para_id] = override
                continue

            if override.get("replace_all"):
                merged_section[para_id] = copy.deepcopy(override)
                continue

            if override.get("append_items"):
                merged_section[para_id] = _merge_append_items(
                    top_level_key,
                    merged_section.get(para_id, {}),
                    override,
                )
                continue

            existing = merged_section.get(para_id)
            if not isinstance(existing, dict):
                merged_section[para_id] = copy.deepcopy(override)
                continue

            combined = copy.deepcopy(existing)

            if "replace_all" in override:
                combined["replace_all"] = bool(override.get("replace_all"))
            elif "replace_all" in existing:
                combined["replace_all"] = bool(existing.get("replace_all"))

            if "sync_replace_types" in override:
                combined["sync_replace_types"] = bool(override.get("sync_replace_types"))
            elif "sync_replace_types" in existing:
                combined["sync_replace_types"] = bool(existing.get("sync_replace_types"))

            if "sync_item_types_only" in override:
                combined["sync_item_types_only"] = [
                    str(activity_type).strip()
                    for activity_type in override.get("sync_item_types_only", [])
                    if str(activity_type).strip()
                ]
            elif "sync_item_types_only" in existing:
                combined["sync_item_types_only"] = [
                    str(activity_type).strip()
                    for activity_type in existing.get("sync_item_types_only", [])
                    if str(activity_type).strip()
                ]

            replace_types: list[str] = []
            for activity_type in existing.get("replace_types", []):
                if activity_type not in replace_types:
                    replace_types.append(activity_type)
            for activity_type in override.get("replace_types", []):
                if activity_type not in replace_types:
                    replace_types.append(activity_type)
            if replace_types:
                combined["replace_types"] = replace_types

            existing_items = copy.deepcopy(existing.get("items", []))
            items_by_type = {
                item.get("activity_type"): item
                for item in existing_items
                if isinstance(item, dict) and item.get("activity_type")
            }
            merged_items: list[dict] = [
                item for item in existing_items
                if not isinstance(item, dict) or not item.get("activity_type")
            ]
            merged_items.extend(items_by_type.values())

            for item in override.get("items", []):
                if not isinstance(item, dict):
                    merged_items.append(copy.deepcopy(item))
                    continue
                activity_type = item.get("activity_type")
                if not activity_type:
                    merged_items.append(copy.deepcopy(item))
                    continue
                replaced = False
                for idx, existing_item in enumerate(merged_items):
                    if (
                        isinstance(existing_item, dict)
                        and existing_item.get("activity_type") == activity_type
                    ):
                        merged_items[idx] = copy.deepcopy(item)
                        replaced = True
                        break
                if not replaced:
                    merged_items.append(copy.deepcopy(item))
            if merged_items:
                combined["items"] = merged_items

            merged_section[para_id] = combined


@lru_cache(maxsize=1)
def load_curated_overrides() -> dict:
    merged = _empty_override_map()

    paths: list[Path] = []
    if DATA_PATH.exists():
        paths.append(DATA_PATH)

    paths.extend(
        path
        for path in sorted(DATA_DIR.glob("curated_overrides_*.json"))
        if path != DATA_PATH
    )

    for path in paths:
        _merge_override_file(merged, path)

    return merged


def get_curated_activity_override(para_id: str) -> Optional[dict]:
    override = load_curated_overrides().get("activities", {}).get(para_id)
    return copy.deepcopy(override) if override else None


def get_curated_question_override(para_id: str) -> Optional[dict]:
    override = load_curated_overrides().get("questions", {}).get(para_id)
    return copy.deepcopy(override) if override else None


def merge_curated_activities(
    para_id: str,
    generated: dict[str, list[dict]],
    requested_types: Optional[list[str]] = None,
) -> dict[str, list[dict]]:
    override = get_curated_activity_override(para_id)
    if not override:
        return generated

    requested = set(requested_types) if requested_types else None
    if override.get("replace_all") or override.get("sync_replace_types"):
        merged: dict[str, list[dict]] = {}
    else:
        merged = {
            slug: [copy.deepcopy(item) for item in items]
            for slug, items in generated.items()
        }

    if not override.get("replace_all") and not override.get("sync_replace_types"):
        for slug in override.get("replace_types", []):
            if requested is not None and slug not in requested:
                continue
            merged.pop(slug, None)

    for item in [*override.get("items", []), *override.get("appended_items", [])]:
        slug = item.get("activity_type")
        if not slug:
            continue
        if requested is not None and slug not in requested:
            continue
        payload = copy.deepcopy(item)
        payload.pop("activity_type", None)
        merged.setdefault(slug, []).append(payload)

    return merged
