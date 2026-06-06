"""
Persistent curriculum-review state store.

This is intentionally file-backed rather than browser-backed so review
notes/statuses live in the repo and can be versioned alongside curriculum
changes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REVIEW_EXPORT_VERSION = 1
REVIEW_STATUSES = {"pending", "approved", "weak", "replace"}
REVIEW_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "curriculum_review_state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_review_record() -> dict[str, Any]:
    return {"status": "pending", "notes": "", "updatedAt": None}


def _normalize_review_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        return default_review_record()

    status = record.get("status")
    if status not in REVIEW_STATUSES:
        status = "pending"

    notes = record.get("notes")
    if not isinstance(notes, str):
        notes = ""

    updated_at = record.get("updatedAt")
    if not isinstance(updated_at, str):
        updated_at = None

    return {
        "status": status,
        "notes": notes,
        "updatedAt": updated_at,
    }


def normalize_review_payload(payload: Any) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    reviews = source.get("reviews", source)
    if not isinstance(reviews, dict):
        reviews = {}

    normalized_reviews: dict[str, dict[str, Any]] = {}
    for para_id, record in reviews.items():
        para_key = str(para_id or "").strip()
        if not para_key:
            continue
        normalized_reviews[para_key] = _normalize_review_record(record)

    updated_at = source.get("updatedAt")
    if not isinstance(updated_at, str):
        updated_at = None

    return {
        "type": "atc_review_state",
        "version": REVIEW_EXPORT_VERSION,
        "updatedAt": updated_at,
        "reviewCount": len(normalized_reviews),
        "storagePath": str(REVIEW_STORE_PATH),
        "reviews": normalized_reviews,
    }


def _write_payload(payload: dict[str, Any]) -> dict[str, Any]:
    REVIEW_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = REVIEW_STORE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(REVIEW_STORE_PATH)
    return payload


def load_review_payload() -> dict[str, Any]:
    if not REVIEW_STORE_PATH.exists():
        return normalize_review_payload({})

    try:
        raw = json.loads(REVIEW_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return normalize_review_payload({})

    return normalize_review_payload(raw)


def replace_review_payload(payload: Any) -> dict[str, Any]:
    normalized = normalize_review_payload(payload)
    normalized["updatedAt"] = _now_iso()
    normalized["reviewCount"] = len(normalized["reviews"])
    return _write_payload(normalized)


def update_review_record(para_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    current = load_review_payload()
    existing = current["reviews"].get(para_id, default_review_record())

    merged = {
        **existing,
        **{key: value for key, value in patch.items() if key in {"status", "notes"}},
        "updatedAt": _now_iso(),
    }
    current["reviews"][para_id] = _normalize_review_record(merged)
    current["reviews"][para_id]["updatedAt"] = merged["updatedAt"]
    current["updatedAt"] = merged["updatedAt"]
    current["reviewCount"] = len(current["reviews"])
    return _write_payload(current)


def clear_review_payload() -> dict[str, Any]:
    cleared = normalize_review_payload({})
    cleared["updatedAt"] = _now_iso()
    return _write_payload(cleared)
