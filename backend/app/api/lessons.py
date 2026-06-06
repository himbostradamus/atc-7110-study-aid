"""
api/lessons.py
===============
Lesson session API — the student-facing engagement layer.

Routes:
  POST /lessons/start              — start a session (returns first activity)
  GET  /lessons/{id}/next          — get next activity in session
  POST /lessons/{id}/answer        — submit answer, get result + next activity
  POST /lessons/{id}/complete      — close a session early
  GET  /lessons/{id}/summary       — completed session summary + crown changes
  GET  /lessons/mastery            — user's crown levels across all paragraphs
  GET  /lessons/mastery/{para_id}  — crown detail + next-level requirements
  POST /lessons/admin/generate     — trigger batch activity generation
  GET  /lessons/admin/runs/{id}    — check generation run status
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.orm import User
from ..services.db import get_db
from ..services.auth import get_current_user
from ..services.activity_engine import (
    ActivityRecord, MasteryState, SessionBuilder,
    ActivityScorer, CrownCalculator, CrownChange, ALL_TYPES,
)

router = APIRouter()

_builder  = SessionBuilder()
_scorer   = ActivityScorer()
_crowns   = CrownCalculator()


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    filter_type:  str  = Field("section", description="section|chapter|tag|paragraph_list|weak_areas")
    filter_value: Optional[str]  = None     # section UUID, chapter num, tag name
    para_ids:     Optional[list[UUID]] = None   # explicit paragraph list
    activity_count: int = Field(8, ge=5, le=12)


class AnswerRequest(BaseModel):
    session_activity_id: UUID
    response_json:       dict    # type-specific answer payload
    response_ms:         Optional[int] = None


class GenerateRequest(BaseModel):
    paragraph_ids: list[UUID]
    activity_types: Optional[list[str]] = None    # None = all types
    overwrite:     bool = False


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_paragraphs(
    db: Session,
    req: StartSessionRequest,
    user: User,
) -> list[dict]:
    """Fetch paragraph IDs + metadata matching the session filter."""
    sql = """
        SELECT p.id, p.para_id, p.title, p.section_id
        FROM paragraphs p
        JOIN sections   se ON p.section_id = se.id
        JOIN chapters   c  ON se.chapter_id = c.id
        JOIN order_versions ov ON p.version_id = ov.id AND ov.is_current = TRUE
    """
    params: dict = {}

    if req.filter_type == "section" and req.filter_value:
        sql += " WHERE se.id = :val"
        params["val"] = req.filter_value

    elif req.filter_type == "chapter" and req.filter_value:
        sql += " WHERE c.chapter_number = :val"
        params["val"] = int(req.filter_value)

    elif req.filter_type == "tag" and req.filter_value:
        sql += """
            JOIN paragraph_tags pt ON pt.paragraph_id = p.id
            JOIN tags t ON pt.tag_id = t.id AND t.name = :val
        """
        params["val"] = req.filter_value

    elif req.filter_type == "paragraph_list" and req.para_ids:
        placeholders = ", ".join([f"'{str(p)}'" for p in req.para_ids])
        sql += f" WHERE p.id IN ({placeholders})"

    elif req.filter_type == "weak_areas":
        sql += """
            JOIN user_weak_areas wa ON wa.paragraph_id = p.id
            WHERE wa.user_id = :uid AND wa.resolved = FALSE
        """
        params["uid"] = str(user.id)

    sql += " ORDER BY c.chapter_number, se.sort_order, p.sort_order"
    rows = db.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in rows]


def _load_activities_for_paragraphs(
    db: Session, para_ids: list[str]
) -> list[ActivityRecord]:
    """Load all active activities for the given paragraph IDs."""
    if not para_ids:
        return []
    placeholders = ", ".join([f"'{p}'" for p in para_ids])
    rows = db.execute(text(f"""
        SELECT a.id, a.paragraph_id, a.activity_type, a.content_json,
               a.difficulty, p.para_id, p.title AS para_title
        FROM activities a
        JOIN paragraphs p ON a.paragraph_id = p.id
        WHERE a.paragraph_id IN ({placeholders})
          AND a.is_active = TRUE
    """)).fetchall()

    records = []
    for r in rows:
        rm = dict(r._mapping)
        cj = rm["content_json"]
        if isinstance(cj, str):
            cj = json.loads(cj)
        records.append(ActivityRecord(
            id            = str(rm["id"]),
            paragraph_id  = str(rm["paragraph_id"]),
            para_id       = rm["para_id"],
            para_title    = rm.get("para_title", ""),
            activity_type = rm["activity_type"],
            content_json  = cj,
            difficulty    = rm.get("difficulty") or 2,
        ))
    return records


def _load_mastery_states(
    db: Session, user_id: str, para_ids: list[str]
) -> dict[str, MasteryState]:
    """Load mastery states for user × paragraphs. Returns {para_id: MasteryState}."""
    if not para_ids:
        return {}
    placeholders = ", ".join([f"'{p}'" for p in para_ids])
    rows = db.execute(text(f"""
        SELECT pm.paragraph_id, pm.crown_level, pm.type_counts,
               pm.type_avg_scores, pm.total_activities,
               p.para_id
        FROM paragraph_mastery pm
        JOIN paragraphs p ON pm.paragraph_id = p.id
        WHERE pm.user_id = :uid AND pm.paragraph_id IN ({placeholders})
    """), {"uid": user_id}).fetchall()

    states = {}
    for r in rows:
        rm = dict(r._mapping)
        tc  = rm["type_counts"]    or {}
        tas = rm["type_avg_scores"] or {}
        if isinstance(tc,  str): tc  = json.loads(tc)
        if isinstance(tas, str): tas = json.loads(tas)
        pid = rm["para_id"]
        states[pid] = MasteryState(
            paragraph_id     = str(rm["paragraph_id"]),
            para_id          = pid,
            crown_level      = rm["crown_level"],
            type_counts      = tc,
            type_avg_scores  = tas,
            total_activities = rm["total_activities"],
        )
    return states


def _get_recently_seen_ids(db: Session, user_id: str) -> set[str]:
    """Activity IDs the user has seen in the last 3 days."""
    rows = db.execute(text("""
        SELECT DISTINCT sa.activity_id::text
        FROM session_activities sa
        JOIN lesson_sessions ls ON sa.session_id = ls.id
        WHERE ls.user_id = :uid
          AND sa.answered_at >= NOW() - INTERVAL '3 days'
    """), {"uid": user_id}).fetchall()
    return {r.activity_id for r in rows}


def _serialise_activity(record: ActivityRecord, sa_id: str) -> dict:
    """Build the activity payload sent to the client (no answers exposed)."""
    content = dict(record.content_json)

    # Remove answer keys before sending to client
    for key in ("correct_sequence", "error_index", "correct_token",
                "correct_order", "explanation"):
        content.pop(key, None)

    # For choice-based types: strip is_correct flags
    if "choices" in content:
        content["choices"] = [
            {"text": c["text"], "index": i}
            for i, c in enumerate(content["choices"])
        ]

    # For match_pairs: shuffle both columns independently
    if record.activity_type == "match_pairs" and "pairs" in content:
        terms = [p["term"] for p in content["pairs"]]
        defns = [p["definition"] for p in content["pairs"]]
        import random as _r
        _r.shuffle(terms); _r.shuffle(defns)
        content["shuffled_terms"]       = terms
        content["shuffled_definitions"] = defns
        del content["pairs"]

    return {
        "session_activity_id": sa_id,
        "activity_id":         record.id,
        "activity_type":       record.activity_type,
        "para_id":             record.para_id,
        "para_title":          record.para_title,
        "paragraph_id":        record.paragraph_id,
        "difficulty":          record.difficulty,
        "content":             content,
    }


def _upsert_mastery(
    db:            Session,
    user_id:       str,
    paragraph_id:  str,
    para_id:       str,
    activity_type: str,
    score:         float,
    session_id:    str,
) -> Optional[CrownChange]:
    """
    Update paragraph_mastery and return a CrownChange if the level changed.
    """
    row = db.execute(text("""
        SELECT crown_level, type_counts, type_avg_scores, total_activities
        FROM paragraph_mastery
        WHERE user_id = :uid AND paragraph_id = :pid
    """), {"uid": user_id, "pid": paragraph_id}).fetchone()

    if row:
        rm  = dict(row._mapping)
        tc  = rm["type_counts"]    or {}
        tas = rm["type_avg_scores"] or {}
        if isinstance(tc,  str): tc  = json.loads(tc)
        if isinstance(tas, str): tas = json.loads(tas)
        state = MasteryState(
            paragraph_id     = paragraph_id,
            para_id          = para_id,
            crown_level      = rm["crown_level"],
            type_counts      = tc,
            type_avg_scores  = tas,
            total_activities = rm["total_activities"],
        )
    else:
        state = MasteryState(paragraph_id=paragraph_id, para_id=para_id)

    old_level = state.crown_level
    new_state = _crowns.update_state(state, activity_type, score)
    new_level = _crowns.calculate(new_state)

    db.execute(text("""
        INSERT INTO paragraph_mastery
            (id, user_id, paragraph_id, crown_level, type_counts,
             type_avg_scores, total_activities, last_practiced,
             crown_achieved_at, updated_at)
        VALUES
            (:id, :uid, :pid, :lvl, :tc::jsonb, :tas::jsonb,
             :total, NOW(),
             CASE WHEN :lvl > :old_lvl THEN NOW() ELSE NULL END,
             NOW())
        ON CONFLICT (user_id, paragraph_id) DO UPDATE SET
            crown_level      = :lvl,
            type_counts      = :tc::jsonb,
            type_avg_scores  = :tas::jsonb,
            total_activities = :total,
            last_practiced   = NOW(),
            crown_achieved_at = CASE
                WHEN :lvl > paragraph_mastery.crown_level THEN NOW()
                ELSE paragraph_mastery.crown_achieved_at
            END,
            updated_at = NOW()
    """), {
        "id":      str(uuid.uuid4()),
        "uid":     user_id,
        "pid":     paragraph_id,
        "lvl":     new_level,
        "tc":      json.dumps(new_state.type_counts),
        "tas":     json.dumps(new_state.type_avg_scores),
        "total":   new_state.total_activities,
        "old_lvl": old_level,
    })

    # Log mastery event if level changed
    if new_level != old_level:
        db.execute(text("""
            INSERT INTO mastery_events
                (id, user_id, paragraph_id, session_id, old_level, new_level,
                 trigger_type, trigger_score)
            VALUES (:id, :uid, :pid, :sid, :old, :new, :ttype, :score)
        """), {
            "id":    str(uuid.uuid4()),
            "uid":   user_id,
            "pid":   paragraph_id,
            "sid":   session_id,
            "old":   old_level,
            "new":   new_level,
            "ttype": activity_type,
            "score": score,
        })
        return CrownChange(
            paragraph_id = paragraph_id,
            para_id      = para_id,
            old_level    = old_level,
            new_level    = new_level,
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# START SESSION
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/start", status_code=201)
def start_session(
    body: StartSessionRequest,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """
    Start a new lesson session.

    Returns the session ID, total activity count, and the first activity
    ready for display.
    """
    paragraphs = _resolve_paragraphs(db, body, user)
    if not paragraphs:
        raise HTTPException(422, "No paragraphs found for the given filter")

    para_ids = [str(p["id"]) for p in paragraphs]
    para_id_map = {str(p["id"]): p["para_id"] for p in paragraphs}

    activities    = _load_activities_for_paragraphs(db, para_ids)
    mastery_states = _load_mastery_states(db, str(user.id), para_ids)
    seen_ids      = _get_recently_seen_ids(db, str(user.id))

    if not activities:
        raise HTTPException(422, "No activities available for these paragraphs. "
                                 "An instructor must generate activities first.")

    selected = _builder.build(
        available       = activities,
        mastery_states  = mastery_states,
        target_count    = body.activity_count,
        seen_activity_ids = seen_ids,
    )

    if not selected:
        raise HTTPException(422, "Could not build a session from available activities")

    # Persist session
    session_id = str(uuid.uuid4())
    uuid_para_ids = [UUID(pid) for pid in para_ids]
    db.execute(text("""
        INSERT INTO lesson_sessions
            (id, user_id, filter_type, filter_value, paragraph_ids,
             status, total_activities)
        VALUES (:id, :uid, :ft, :fv, :pids, 'active', :total)
    """), {
        "id":    session_id,
        "uid":   str(user.id),
        "ft":    body.filter_type,
        "fv":    body.filter_value,
        "pids":  uuid_para_ids,
        "total": len(selected),
    })

    # Persist session_activities
    sa_ids = []
    for i, act in enumerate(selected):
        sa_id = str(uuid.uuid4())
        sa_ids.append(sa_id)
        db.execute(text("""
            INSERT INTO session_activities
                (id, session_id, activity_id, sequence_num)
            VALUES (:id, :sid, :aid, :seq)
        """), {"id": sa_id, "sid": session_id, "aid": act.id, "seq": i + 1})

    db.commit()

    first = _serialise_activity(selected[0], sa_ids[0])
    return {
        "session_id":       session_id,
        "total_activities": len(selected),
        "current_index":    1,
        "first_activity":   first,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUBMIT ANSWER
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{session_id}/answer")
def submit_answer(
    session_id: str,
    body:       AnswerRequest,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    """
    Submit an answer for the current activity.

    Returns:
      - Grading result (is_correct, score, feedback, explanation)
      - Crown change if the paragraph levelled up
      - Next activity (or done=True if session complete)
    """
    # Verify session belongs to user
    sess_row = db.execute(text("""
        SELECT id, status, total_activities, completed_count
        FROM lesson_sessions WHERE id = :id AND user_id = :uid
    """), {"id": session_id, "uid": str(user.id)}).fetchone()
    if not sess_row:
        raise HTTPException(404, "Session not found")
    sess = dict(sess_row._mapping)
    if sess["status"] != "active":
        raise HTTPException(409, "Session is no longer active")

    # Load the session_activity being answered
    sa_row = db.execute(text("""
        SELECT sa.id, sa.activity_id, sa.sequence_num, sa.answered_at,
               a.activity_type, a.content_json, a.difficulty,
               p.id AS paragraph_id, p.para_id, p.title AS para_title
        FROM session_activities sa
        JOIN activities a ON sa.activity_id = a.id
        JOIN paragraphs p ON a.paragraph_id = p.id
        WHERE sa.id = :said AND sa.session_id = :sid
    """), {"said": str(body.session_activity_id), "sid": session_id}).fetchone()
    if not sa_row:
        raise HTTPException(404, "Activity not found in this session")
    sa = dict(sa_row._mapping)

    if sa["answered_at"] is not None:
        raise HTTPException(409, "Activity already answered")

    cj = sa["content_json"]
    if isinstance(cj, str):
        cj = json.loads(cj)

    act = ActivityRecord(
        id            = str(sa["activity_id"]),
        paragraph_id  = str(sa["paragraph_id"]),
        para_id       = sa["para_id"],
        para_title    = sa.get("para_title", ""),
        activity_type = sa["activity_type"],
        content_json  = cj,
        difficulty    = sa.get("difficulty") or 2,
    )

    # Score it
    scored = _scorer.score(act, body.response_json, body.response_ms, str(body.session_activity_id))

    # Update session_activity
    db.execute(text("""
        UPDATE session_activities SET
            is_correct    = :correct,
            score         = :score,
            response_json = :resp::jsonb,
            result_json   = :result::jsonb,
            response_ms   = :ms,
            answered_at   = NOW()
        WHERE id = :id
    """), {
        "correct": scored.is_correct,
        "score":   scored.score,
        "resp":    json.dumps(body.response_json),
        "result":  json.dumps(scored.result_json),
        "ms":      body.response_ms,
        "id":      str(body.session_activity_id),
    })

    # Update session counters
    db.execute(text("""
        UPDATE lesson_sessions SET
            completed_count = completed_count + 1,
            correct_count   = correct_count + :c
        WHERE id = :id
    """), {"c": 1 if scored.is_correct else 0, "id": session_id})

    # Update mastery
    crown_change = _upsert_mastery(
        db, str(user.id), str(sa["paragraph_id"]), sa["para_id"],
        sa["activity_type"], scored.score, session_id
    )

    if crown_change:
        # Append crown change to session record
        db.execute(text("""
            UPDATE lesson_sessions SET
                crown_changes = crown_changes || :change::jsonb
            WHERE id = :id
        """), {
            "change": json.dumps([{
                "para_id":   crown_change.para_id,
                "old_level": crown_change.old_level,
                "new_level": crown_change.new_level,
            }]),
            "id": session_id,
        })

    new_completed = sess["completed_count"] + 1
    total         = sess["total_activities"]
    done          = new_completed >= total

    # Get next activity
    next_activity = None
    if not done:
        next_sa = db.execute(text("""
            SELECT sa.id, sa.activity_id, sa.sequence_num,
                   a.activity_type, a.content_json, a.difficulty,
                   p.para_id, p.title AS para_title, p.id AS paragraph_id
            FROM session_activities sa
            JOIN activities a ON sa.activity_id = a.id
            JOIN paragraphs p ON a.paragraph_id = p.id
            WHERE sa.session_id = :sid AND sa.answered_at IS NULL
            ORDER BY sa.sequence_num ASC LIMIT 1
        """), {"sid": session_id}).fetchone()

        if next_sa:
            ns = dict(next_sa._mapping)
            ncj = ns["content_json"]
            if isinstance(ncj, str): ncj = json.loads(ncj)
            next_rec = ActivityRecord(
                id=str(ns["activity_id"]), paragraph_id=str(ns["paragraph_id"]),
                para_id=ns["para_id"], para_title=ns.get("para_title",""),
                activity_type=ns["activity_type"], content_json=ncj, difficulty=ns.get("difficulty",2)
            )
            next_activity = _serialise_activity(next_rec, str(ns["id"]))

    # Mark session complete if done
    if done:
        db.execute(text("""
            UPDATE lesson_sessions SET status = 'completed', completed_at = NOW()
            WHERE id = :id
        """), {"id": session_id})

    db.commit()

    return {
        "result":         scored.result_json,
        "is_correct":     scored.is_correct,
        "score":          scored.score,
        "crown_change":   {"para_id": crown_change.para_id,
                           "old_level": crown_change.old_level,
                           "new_level": crown_change.new_level} if crown_change else None,
        "progress":       {"completed": new_completed, "total": total},
        "done":           done,
        "next_activity":  next_activity,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SESSION SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{session_id}/summary")
def get_session_summary(
    session_id: str,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Full results for a completed session."""
    sess_row = db.execute(text("""
        SELECT * FROM lesson_sessions WHERE id = :id AND user_id = :uid
    """), {"id": session_id, "uid": str(user.id)}).fetchone()
    if not sess_row:
        raise HTTPException(404, "Session not found")
    sess = dict(sess_row._mapping)

    results = db.execute(text("""
        SELECT sa.sequence_num, sa.is_correct, sa.score, sa.result_json,
               sa.response_ms, sa.answered_at,
               a.activity_type, a.difficulty,
               p.para_id, p.title AS para_title
        FROM session_activities sa
        JOIN activities a ON sa.activity_id = a.id
        JOIN paragraphs p ON a.paragraph_id = p.id
        WHERE sa.session_id = :id
        ORDER BY sa.sequence_num
    """), {"id": session_id}).fetchall()

    items = [dict(r._mapping) for r in results]
    completed = [i for i in items if i["answered_at"]]

    total         = sess["total_activities"]
    correct_count = sum(1 for i in completed if i.get("is_correct"))
    score_pct     = round(correct_count / max(len(completed), 1) * 100, 1)

    cc = sess.get("crown_changes") or []
    if isinstance(cc, str):
        cc = json.loads(cc)

    return {
        "session_id":    session_id,
        "status":        sess["status"],
        "total":         total,
        "completed":     len(completed),
        "correct":       correct_count,
        "score_pct":     score_pct,
        "crown_changes": cc,
        "activities":    items,
        "started_at":    sess["started_at"],
        "completed_at":  sess.get("completed_at"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MASTERY / CROWNS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/mastery")
def get_mastery_overview(
    chapter: Optional[int] = Query(None),
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """
    Crown levels for all paragraphs the user has interacted with.
    Grouped by chapter for the curriculum map view.
    """
    sql = """
        SELECT pm.paragraph_id, pm.crown_level, pm.total_activities,
               pm.type_counts, pm.last_practiced,
               p.para_id, p.title AS para_title,
               se.title AS section_title, se.section_number,
               c.chapter_number, c.title AS chapter_title
        FROM paragraph_mastery pm
        JOIN paragraphs p ON pm.paragraph_id = p.id
        JOIN sections se  ON p.section_id = se.id
        JOIN chapters c   ON se.chapter_id = c.id
        WHERE pm.user_id = :uid
    """
    params: dict = {"uid": str(user.id)}
    if chapter:
        sql += " AND c.chapter_number = :ch"
        params["ch"] = chapter
    sql += " ORDER BY c.chapter_number, se.section_number, p.sort_order"

    rows = db.execute(text(sql), params).fetchall()

    # Group by chapter
    chapters: dict = {}
    for r in rows:
        rm = dict(r._mapping)
        ch = rm["chapter_number"]
        if ch not in chapters:
            chapters[ch] = {"chapter_number": ch, "title": rm["chapter_title"], "sections": {}}
        sec = rm["section_number"]
        if sec not in chapters[ch]["sections"]:
            chapters[ch]["sections"][sec] = {"section_number": sec, "title": rm["section_title"], "paragraphs": []}

        tc = rm.get("type_counts") or {}
        if isinstance(tc, str): tc = json.loads(tc)

        chapters[ch]["sections"][sec]["paragraphs"].append({
            "paragraph_id":   str(rm["paragraph_id"]),
            "para_id":        rm["para_id"],
            "title":          rm["para_title"],
            "crown_level":    rm["crown_level"],
            "total_activities": rm["total_activities"],
            "types_practiced": list(tc.keys()),
            "last_practiced": rm.get("last_practiced"),
        })

    return list(chapters.values())


@router.get("/mastery/{para_id_str}")
def get_paragraph_mastery(
    para_id_str: str,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Crown detail + next-level requirements for one paragraph."""
    row = db.execute(text("""
        SELECT pm.*, p.para_id, p.title AS para_title, p.id AS paragraph_id
        FROM paragraph_mastery pm
        JOIN paragraphs p ON pm.paragraph_id = p.id
        WHERE pm.user_id = :uid AND p.para_id = :pid
    """), {"uid": str(user.id), "pid": para_id_str}).fetchone()

    if not row:
        # Never studied — return zeroed state
        para = db.execute(text("""
            SELECT id, para_id, title FROM paragraphs p
            JOIN order_versions ov ON p.version_id = ov.id AND ov.is_current = TRUE
            WHERE p.para_id = :pid LIMIT 1
        """), {"pid": para_id_str}).fetchone()
        if not para:
            raise HTTPException(404, f"Paragraph {para_id_str} not found")
        pm = dict(para._mapping)
        state = MasteryState(paragraph_id=str(pm["id"]), para_id=pm["para_id"])
    else:
        rm = dict(row._mapping)
        tc  = rm.get("type_counts") or {}
        tas = rm.get("type_avg_scores") or {}
        if isinstance(tc,  str): tc  = json.loads(tc)
        if isinstance(tas, str): tas = json.loads(tas)
        state = MasteryState(
            paragraph_id     = str(rm["paragraph_id"]),
            para_id          = rm["para_id"],
            crown_level      = rm["crown_level"],
            type_counts      = tc,
            type_avg_scores  = tas,
            total_activities = rm["total_activities"],
        )

    next_req = _crowns.next_level_requirements(state)
    return {
        "para_id":           state.para_id,
        "crown_level":       state.crown_level,
        "total_activities":  state.total_activities,
        "type_counts":       state.type_counts,
        "type_avg_scores":   state.type_avg_scores,
        "next_level":        next_req,
        "all_types":         ALL_TYPES,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: GENERATE ACTIVITIES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/admin/generate", status_code=202)
async def generate_activities(
    body:       GenerateRequest,
    background: BackgroundTasks,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    if user.role not in ("instructor", "admin"):
        raise HTTPException(403, "Instructor or admin role required")

    placeholders = ", ".join([f"'{str(p)}'" for p in body.paragraph_ids])
    rows = db.execute(text(f"""
        SELECT p.id, p.para_id, p.title,
               json_agg(json_build_object(
                   'block_type', cb.block_type,
                   'content',    cb.content,
                   'label',      cb.label
               ) ORDER BY cb.sequence) AS blocks,
               p.version_id
        FROM paragraphs p
        JOIN content_blocks cb ON cb.paragraph_id = p.id
        WHERE p.id IN ({placeholders})
        GROUP BY p.id
    """)).fetchall()

    if not rows:
        raise HTTPException(404, "No paragraphs found")

    para_dicts = []
    for r in rows:
        rm = dict(r._mapping)
        blocks = rm["blocks"]
        if isinstance(blocks, str): blocks = json.loads(blocks)
        para_dicts.append({
            "db_id":      str(rm["id"]),
            "para_id":    rm["para_id"],
            "title":      rm.get("title",""),
            "blocks":     blocks,
            "version_id": str(rm["version_id"]),
        })

    skip_ids: set[str] = set()
    if not body.overwrite:
        existing = db.execute(text(f"""
            SELECT DISTINCT p.para_id FROM activities a
            JOIN paragraphs p ON a.paragraph_id = p.id
            WHERE a.paragraph_id IN ({placeholders})
        """)).fetchall()
        skip_ids = {r.para_id for r in existing}

    run_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO activity_generation_runs
            (id, triggered_by, paragraph_ids, activity_types_req, status)
        VALUES (:id, :uid, :pids, :types, 'running')
    """), {
        "id":    run_id,
        "uid":   str(user.id),
        "pids":  [str(p) for p in body.paragraph_ids],
        "types": body.activity_types or ALL_TYPES,
    })
    db.commit()

    background.add_task(
        _run_generation_bg, para_dicts, body.activity_types,
        str(user.id), skip_ids, run_id
    )

    return {"run_id": run_id, "status": "queued", "paragraphs": len(para_dicts)}


@router.get("/admin/runs/{run_id}")
def get_generation_run(
    run_id: str,
    db:     Session = Depends(get_db),
    user:   User    = Depends(get_current_user),
):
    row = db.execute(text("""
        SELECT * FROM activity_generation_runs WHERE id = :id
    """), {"id": run_id}).fetchone()
    if not row:
        raise HTTPException(404, "Run not found")
    return dict(row._mapping)


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND: AUTOMATED GENERATION
# ─────────────────────────────────────────────────────────────────────────────

async def _run_generation_bg(
    para_dicts:    list[dict],
    types:         Optional[list[str]],
    created_by:    str,
    skip_para_ids: set[str],
    run_id:        str,
):
    from ..services.activity_generator import generate_activities_for_paragraph
    from ..services.db import SessionLocal
    import asyncio

    total_created = 0
    errors        = []

    for para in para_dicts:
        if para["para_id"] in skip_para_ids:
            continue
        try:
            results = await generate_activities_for_paragraph(
                para_id    = para["para_id"],
                para_title = para["title"],
                blocks     = para["blocks"],
                types      = types,
            )
            with SessionLocal() as db:
                for act_type, content_list in results.items():
                    for content in content_list:
                        db.execute(text("""
                            INSERT INTO activities
                                (id, paragraph_id, version_id, activity_type,
                                 content_json, difficulty, is_active, is_verified,
                                 generation_source, created_by)
                            VALUES
                                (:id, :pid, :ver, :atype,
                                 :cj::jsonb, :diff, TRUE, FALSE,
                                 :generation_source, :uid)
                        """), {
                            "id":    str(uuid.uuid4()),
                            "pid":   para["db_id"],
                            "ver":   para["version_id"],
                            "atype": act_type,
                            "cj":    json.dumps(content),
                            "diff":  content.get("difficulty", 2),
                            "generation_source": content.get("generation_source", "local_auto"),
                            "uid":   created_by,
                        })
                        total_created += 1
                db.commit()
        except Exception as e:
            errors.append(f"{para['para_id']}: {str(e)}")
        await asyncio.sleep(1.0)

    from ..services.db import SessionLocal
    with SessionLocal() as db:
        db.execute(text("""
            UPDATE activity_generation_runs SET
                status = :status, activities_created = :count,
                errors = :errors::jsonb, completed_at = NOW()
            WHERE id = :id
        """), {
            "status": "failed" if errors and not total_created else "complete",
            "count":  total_created,
            "errors": json.dumps(errors),
            "id":     run_id,
        })
        db.commit()

import logging
log = logging.getLogger(__name__)
