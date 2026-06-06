"""
api/flashcards.py
==================
Flashcard API — study sessions, SRS scheduling, review recording,
deck management, and automated card generation.

Route groups:
  /flashcards/study          — get cards due for a study session
  /flashcards/{id}/review    — record a review and get next schedule
  /flashcards/decks          — create / list decks
  /flashcards/stats          — user stats, forecast, retention
  /flashcards/admin/generate — bulk automated card generation (instructor only)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..models.orm import (
    Flashcard, Paragraph, OrderVersion, User
)
from ..services.srs import (
    CardState, schedule, get_due_counts, forecast_reviews, retention_rate,
    prioritize_due_cards
)
from ..services.db import get_db
from ..services.auth import get_current_user

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    rating:       int = Field(..., ge=1, le=4, description="1=Again 2=Hard 3=Good 4=Easy")
    response_ms:  Optional[int] = Field(None, description="Time taken to respond (ms)")

    @field_validator("rating")
    @classmethod
    def rating_valid(cls, v):
        if v not in (1, 2, 3, 4):
            raise ValueError("Rating must be 1, 2, 3, or 4")
        return v


class ReviewResponse(BaseModel):
    flashcard_id:   UUID
    rating:         int
    new_interval:   int
    new_ease:       float
    new_status:     str
    next_review:    datetime
    message:        str
    interval_change: str


class CardResponse(BaseModel):
    id:          UUID
    para_id:     str
    para_title:  Optional[str]
    front:       str
    back:        str
    card_type:   str
    state:       dict     # current SRS state for this user


class DeckCreate(BaseModel):
    name:        str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    filter_json: Optional[dict] = None   # e.g. {"chapter": 2} or {"tags": ["IFR"]}


class GenerateRequest(BaseModel):
    paragraph_ids: list[UUID] = Field(..., description="Paragraphs to generate cards for")
    overwrite:     bool = Field(False, description="Regenerate even if cards already exist")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: load or create a FlashcardState row
# (Using raw SQL since FlashcardState isn't in orm.py yet — easy to swap)
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_state(db: Session, user_id: UUID, flashcard_id: UUID) -> dict:
    row = db.execute(
        text("""
            SELECT id, ease_factor, interval_days, repetitions,
                   status, lapse_count, total_reviews, next_review, last_reviewed
            FROM flashcard_states
            WHERE user_id = :uid AND flashcard_id = :fid
        """),
        {"uid": str(user_id), "fid": str(flashcard_id)}
    ).fetchone()

    if row:
        return dict(row._mapping)

    # Create new state
    state_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO flashcard_states
                (id, user_id, flashcard_id, ease_factor, interval_days,
                 repetitions, status, lapse_count, total_reviews, next_review)
            VALUES
                (:id, :uid, :fid, 2.50, 0, 0, 'new', 0, 0, NOW())
        """),
        {"id": state_id, "uid": str(user_id), "fid": str(flashcard_id)}
    )
    db.commit()
    return {
        "id": state_id, "ease_factor": 2.50, "interval_days": 0,
        "repetitions": 0, "status": "new", "lapse_count": 0,
        "total_reviews": 0, "next_review": datetime.now(timezone.utc),
        "last_reviewed": None
    }


def _state_dict_to_cardstate(s: dict) -> CardState:
    return CardState(
        ease_factor   = float(s["ease_factor"]),
        interval_days = int(s["interval_days"]),
        repetitions   = int(s["repetitions"]),
        status        = s["status"],
        lapse_count   = int(s["lapse_count"]),
        total_reviews = int(s["total_reviews"]),
        next_review   = s.get("next_review"),
        last_reviewed = s.get("last_reviewed"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# STUDY SESSION
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/study", response_model=list[CardResponse])
def get_study_cards(
    limit:      int  = Query(20, ge=1, le=100, description="Max cards to return"),
    chapter:    Optional[int]  = Query(None, description="Filter to a specific chapter"),
    section:    Optional[UUID] = Query(None, description="Filter to a specific section"),
    tag:        Optional[str]  = Query(None, description="Filter by tag name"),
    new_only:   bool = Query(False, description="Return only unseen cards"),
    due_only:   bool = Query(True,  description="Return only cards due for review"),
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    """
    Returns a prioritized set of flashcards for a study session.

    Priority order:
      1. Overdue review cards (most overdue first)
      2. Learning / relearning cards due now
      3. New cards (if not due_only)
    """
    # Base query: join flashcards → paragraphs → sections → chapters
    # and left join to the user's state
    sql = """
        SELECT
            f.id            AS flashcard_id,
            f.front,
            f.back,
            f.card_type,
            p.para_id,
            p.title         AS para_title,
            COALESCE(s.ease_factor,   2.50)  AS ease_factor,
            COALESCE(s.interval_days, 0)     AS interval_days,
            COALESCE(s.repetitions,   0)     AS repetitions,
            COALESCE(s.status,        'new') AS status,
            COALESCE(s.lapse_count,   0)     AS lapse_count,
            COALESCE(s.total_reviews, 0)     AS total_reviews,
            COALESCE(s.next_review,   NOW()) AS next_review,
            s.last_reviewed
        FROM flashcards f
        JOIN paragraphs p  ON f.paragraph_id = p.id
        JOIN sections   se ON p.section_id   = se.id
        JOIN chapters   c  ON se.chapter_id  = c.id
        LEFT JOIN flashcard_states s
            ON s.flashcard_id = f.id AND s.user_id = :user_id
        JOIN order_versions ov ON f.version_id = ov.id
        WHERE f.is_active = TRUE
          AND ov.is_current = TRUE
    """
    params: dict = {"user_id": str(user.id)}

    if chapter:
        sql += " AND c.chapter_number = :chapter"
        params["chapter"] = chapter
    if section:
        sql += " AND se.id = :section"
        params["section"] = str(section)
    if tag:
        sql += """
            AND EXISTS (
                SELECT 1 FROM paragraph_tags pt
                JOIN tags t ON pt.tag_id = t.id
                WHERE pt.paragraph_id = p.id AND t.name = :tag
            )
        """
        params["tag"] = tag
    if new_only:
        sql += " AND (s.status IS NULL OR s.status = 'new')"
    if due_only:
        sql += """
            AND (
                s.status IS NULL          -- never reviewed (new)
                OR s.status IN ('learning', 'relearning')
                OR (s.status IN ('review', 'graduated') AND s.next_review <= NOW())
            )
        """

    rows = db.execute(text(sql), params).fetchall()

    # Build CardState objects and prioritize
    card_states = []
    for row in rows:
        r = dict(row._mapping)
        cs = CardState(
            ease_factor   = float(r["ease_factor"]),
            interval_days = int(r["interval_days"]),
            repetitions   = int(r["repetitions"]),
            status        = r["status"],
            lapse_count   = int(r["lapse_count"]),
            total_reviews = int(r["total_reviews"]),
            next_review   = r["next_review"],
            last_reviewed = r.get("last_reviewed"),
        )
        card_states.append((r, cs))

    # Sort by SRS priority
    card_states.sort(
        key=lambda x: prioritize_due_cards([x[1]])[0].status
        if card_states else 0
    )

    # Build response
    results = []
    for (r, cs) in card_states[:limit]:
        results.append(CardResponse(
            id         = r["flashcard_id"],
            para_id    = r["para_id"],
            para_title = r["para_title"],
            front      = r["front"],
            back       = r["back"],
            card_type  = r["card_type"],
            state      = {
                "status":        cs.status,
                "interval_days": cs.interval_days,
                "ease_factor":   cs.ease_factor,
                "repetitions":   cs.repetitions,
                "next_review":   cs.next_review.isoformat() if cs.next_review else None,
                "lapse_count":   cs.lapse_count,
                "total_reviews": cs.total_reviews,
            }
        ))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# RECORD A REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{flashcard_id}/review", response_model=ReviewResponse)
def record_review(
    flashcard_id: UUID,
    body: ReviewRequest,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """
    Record a flashcard review and compute the next scheduled review date.

    Returns the updated schedule so the client can immediately update its UI.
    """
    card = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.is_active == True
    ).first()
    if not card:
        raise HTTPException(404, "Flashcard not found")

    # Load current state
    state_row = _get_or_create_state(db, user.id, flashcard_id)
    current_state = _state_dict_to_cardstate(state_row)

    # Run SM-2
    result = schedule(
        state     = current_state,
        rating    = body.rating,
        card_type = card.card_type or "definition",
    )

    now = datetime.now(timezone.utc)

    # Persist updated state
    db.execute(
        text("""
            UPDATE flashcard_states SET
                ease_factor   = :ease,
                interval_days = :interval,
                repetitions   = :reps,
                status        = :status,
                lapse_count   = :lapses,
                total_reviews = :total,
                next_review   = :next_review,
                last_reviewed = :now,
                updated_at    = :now
            WHERE user_id = :uid AND flashcard_id = :fid
        """),
        {
            "ease":        result.ease_factor,
            "interval":    result.interval_days,
            "reps":        result.repetitions,
            "status":      result.status,
            "lapses":      result.lapse_count,
            "total":       result.total_reviews,
            "next_review": result.next_review,
            "now":         now,
            "uid":         str(user.id),
            "fid":         str(flashcard_id),
        }
    )

    # Append to audit log
    db.execute(
        text("""
            INSERT INTO flashcard_reviews
                (id, state_id, user_id, flashcard_id,
                 rating, pre_ease, pre_interval, pre_reps,
                 post_ease, post_interval, post_next_review,
                 response_ms, reviewed_at)
            VALUES
                (:id, :state_id, :uid, :fid,
                 :rating, :pre_ease, :pre_interval, :pre_reps,
                 :post_ease, :post_interval, :post_next,
                 :ms, :now)
        """),
        {
            "id":           str(uuid.uuid4()),
            "state_id":     str(state_row["id"]),
            "uid":          str(user.id),
            "fid":          str(flashcard_id),
            "rating":       body.rating,
            "pre_ease":     result.prev_ease,
            "pre_interval": result.prev_interval,
            "pre_reps":     current_state.repetitions,
            "post_ease":    result.ease_factor,
            "post_interval": result.interval_days,
            "post_next":    result.next_review,
            "ms":           body.response_ms,
            "now":          now,
        }
    )

    db.commit()

    return ReviewResponse(
        flashcard_id    = flashcard_id,
        rating          = body.rating,
        new_interval    = result.interval_days,
        new_ease        = result.ease_factor,
        new_status      = result.status,
        next_review     = result.next_review,
        message         = result.message,
        interval_change = result.interval_change,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STATS & FORECAST
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """
    Returns a summary of the user's flashcard progress including:
    - Due counts (new / learning / review)
    - 14-day review forecast
    - 30-day retention rate
    - Total cards in rotation
    """
    # Fetch all states for this user
    rows = db.execute(
        text("""
            SELECT ease_factor, interval_days, repetitions,
                   status, lapse_count, total_reviews, next_review, last_reviewed
            FROM flashcard_states
            WHERE user_id = :uid
        """),
        {"uid": str(user.id)}
    ).fetchall()

    states = [_state_dict_to_cardstate(dict(r._mapping)) for r in rows]

    # Fetch recent reviews for retention
    review_rows = db.execute(
        text("""
            SELECT rating, reviewed_at
            FROM flashcard_reviews
            WHERE user_id = :uid
            ORDER BY reviewed_at DESC
            LIMIT 500
        """),
        {"uid": str(user.id)}
    ).fetchall()

    reviews = [
        {"rating": r.rating, "reviewed_at": r.reviewed_at.replace(tzinfo=timezone.utc)}
        for r in review_rows
    ]

    due = get_due_counts(states)
    forecast = forecast_reviews(states, days=14)
    retention = retention_rate(reviews, window_days=30)

    # Total cards available in current version
    total_cards = db.execute(
        text("""
            SELECT COUNT(*) FROM flashcards f
            JOIN order_versions ov ON f.version_id = ov.id
            WHERE f.is_active = TRUE AND ov.is_current = TRUE
        """)
    ).scalar()

    graduated = sum(1 for s in states if s.status == "graduated")
    mature = sum(1 for s in states if s.interval_days >= 21)

    return {
        "due":            due,
        "forecast_14d":   forecast,
        "retention_30d":  retention,
        "total_cards":    total_cards,
        "cards_seen":     len(states),
        "cards_graduated": graduated,
        "cards_mature":   mature,
        "cards_unseen":   max(0, total_cards - len(states)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DECKS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/decks")
def list_decks(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    rows = db.execute(
        text("""
            SELECT d.id, d.name, d.description, d.is_system, d.filter_json,
                   COUNT(dc.flashcard_id) AS card_count
            FROM decks d
            LEFT JOIN deck_cards dc ON dc.deck_id = d.id
            WHERE d.user_id = :uid OR d.is_system = TRUE
            GROUP BY d.id
            ORDER BY d.is_system DESC, d.name
        """),
        {"uid": str(user.id)}
    ).fetchall()

    return [dict(r._mapping) for r in rows]


@router.post("/decks", status_code=201)
def create_deck(
    body: DeckCreate,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Create a personal deck with an optional content filter."""
    import json as _json
    deck_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO decks (id, user_id, name, description, is_system, filter_json)
            VALUES (:id, :uid, :name, :desc, FALSE, :filter)
        """),
        {
            "id":     deck_id,
            "uid":    str(user.id),
            "name":   body.name,
            "desc":   body.description,
            "filter": _json.dumps(body.filter_json) if body.filter_json else None,
        }
    )
    db.commit()
    return {"id": deck_id, "name": body.name}


@router.post("/decks/{deck_id}/cards/{flashcard_id}", status_code=204)
def add_card_to_deck(
    deck_id:     UUID,
    flashcard_id: UUID,
    db:          Session = Depends(get_db),
    user:        User    = Depends(get_current_user),
):
    # Verify user owns deck
    row = db.execute(
        text("SELECT user_id FROM decks WHERE id = :did"),
        {"did": str(deck_id)}
    ).fetchone()
    if not row or str(row.user_id) != str(user.id):
        raise HTTPException(403, "Not your deck")

    db.execute(
        text("""
            INSERT INTO deck_cards (deck_id, flashcard_id)
            VALUES (:did, :fid)
            ON CONFLICT DO NOTHING
        """),
        {"did": str(deck_id), "fid": str(flashcard_id)}
    )
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: AI CARD GENERATION
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/admin/generate", status_code=202)
async def generate_cards(
    body:       GenerateRequest,
    background: BackgroundTasks,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    """
    Trigger automated generation of flashcards for a set of paragraphs.
    Runs in the background; check /admin/generation-status for progress.
    Requires instructor or admin role.
    """
    if user.role not in ("instructor", "admin"):
        raise HTTPException(403, "Instructor or admin role required")

    # Fetch paragraph data
    placeholders = ", ".join([f"'{str(pid)}'" for pid in body.paragraph_ids])
    rows = db.execute(
        text(f"""
            SELECT p.id, p.para_id, p.title,
                   json_agg(
                       json_build_object(
                           'block_type', cb.block_type,
                           'label',      cb.label,
                           'content',    cb.content
                       ) ORDER BY cb.sequence
                   ) AS blocks
            FROM paragraphs p
            JOIN content_blocks cb ON cb.paragraph_id = p.id
            WHERE p.id IN ({placeholders})
            GROUP BY p.id
        """)
    ).fetchall()

    if not rows:
        raise HTTPException(404, "No paragraphs found for given IDs")

    para_dicts = []
    for r in rows:
        import json as _json
        para_dicts.append({
            "db_id":   str(r.id),
            "para_id": r.para_id,
            "title":   r.title or "",
            "blocks":  _json.loads(r.blocks) if isinstance(r.blocks, str) else r.blocks,
        })

    # Determine version_id from first paragraph
    version_row = db.execute(
        text("""
            SELECT p.version_id FROM paragraphs p
            JOIN order_versions ov ON p.version_id = ov.id
            WHERE p.id = :pid AND ov.is_current = TRUE
            LIMIT 1
        """),
        {"pid": para_dicts[0]["db_id"]}
    ).fetchone()
    version_id = str(version_row.version_id) if version_row else None

    skip_ids: set[str] = set()
    if not body.overwrite:
        existing = db.execute(
            text(f"""
                SELECT DISTINCT p.para_id
                FROM flashcards f
                JOIN paragraphs p ON f.paragraph_id = p.id
                WHERE f.paragraph_id IN ({placeholders})
                  AND f.generation_source IN ('ai_auto', 'ai_assisted', 'local_auto')
            """)
        ).fetchall()
        skip_ids = {r.para_id for r in existing}

    background.add_task(
        _run_generation_background,
        para_dicts, version_id, str(user.id), skip_ids
    )

    return {
        "status":    "queued",
        "paragraphs": len(para_dicts),
        "skipping":   len(skip_ids),
        "message":   "Card generation started in background"
    }


async def _run_generation_background(
    para_dicts: list[dict],
    version_id: Optional[str],
    created_by: str,
    skip_para_ids: set[str],
):
    """Background task: generate and persist cards for a batch of paragraphs."""
    from ..services.card_generator import generate_cards_for_paragraph
    from ..services.db import SessionLocal
    import asyncio

    log.info(f"Background generation: {len(para_dicts)} paragraphs, {len(skip_para_ids)} skipped")

    for para in para_dicts:
        if para["para_id"] in skip_para_ids:
            continue

        cards = await generate_cards_for_paragraph(
            para_id    = para["para_id"],
            para_title = para["title"],
            blocks     = para["blocks"],
        )

        if not cards:
            continue

        with SessionLocal() as db:
            for card in cards:
                db.execute(
                    text("""
                        INSERT INTO flashcards
                            (id, paragraph_id, version_id, created_by,
                             front, back, card_type, generation_source,
                             source_block_type, is_active)
                        VALUES
                            (:id, :para_id, :ver, :created_by,
                             :front, :back, :card_type, :generation_source,
                             :src_block, TRUE)
                    """),
                    {
                        "id":         str(uuid.uuid4()),
                        "para_id":    para["db_id"],
                        "ver":        version_id,
                        "created_by": created_by,
                        "front":      card.front,
                        "back":       card.back,
                        "card_type":  card.card_type,
                        "generation_source": card.generation_source,
                        "src_block":  card.source_block_type,
                    }
                )
            db.commit()
            log.info(f"  {para['para_id']}: {len(cards)} cards saved")

        await asyncio.sleep(0.5)   # rate limiting


import logging
log = logging.getLogger(__name__)
