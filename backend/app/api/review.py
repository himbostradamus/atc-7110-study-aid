"""
Curriculum-review state API.

Stores reviewer notes/statuses in a repo-backed JSON file so QA state is
durable and can be versioned with curriculum changes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..services.review_store import (
    clear_review_payload,
    load_review_payload,
    replace_review_payload,
    update_review_record,
)


router = APIRouter()


class ReviewRecordPatch(BaseModel):
    status: str | None = None
    notes: str | None = None


@router.get("/state")
def get_review_state() -> dict[str, Any]:
    return load_review_payload()


@router.put("/state")
def put_review_state(payload: dict[str, Any]) -> dict[str, Any]:
    return replace_review_payload(payload)


@router.put("/paragraphs/{para_id}")
def put_paragraph_review(para_id: str, patch: ReviewRecordPatch) -> dict[str, Any]:
    return update_review_record(
        para_id,
        patch.model_dump(exclude_none=True),
    )


@router.delete("/state")
def delete_review_state() -> dict[str, Any]:
    return clear_review_payload()
