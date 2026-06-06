"""
api/quizzes.py
===============
Quiz API — covers the full lifecycle:

  Quiz Builder    POST /quizzes/configs          create a reusable config
  Question Bank   GET  /quizzes/questions        browse / search test bank
  Start Attempt   POST /quizzes/{id}/attempt     create an attempt, get questions
  Submit          POST /quizzes/attempts/{id}/submit   submit answers, get results
  Results         GET  /quizzes/attempts/{id}    retrieve scored result
  History         GET  /quizzes/attempts         user's attempt history
  Weak Areas      GET  /quizzes/weak-areas        student's flagged weak paragraphs
  Admin           POST /quizzes/admin/generate   automated question generation
                  PUT  /quizzes/questions/{id}/verify  verify a question
"""

from __future__ import annotations

import uuid
import random
from dataclasses import asdict
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
from ..services.quiz_engine import (
    AdaptiveController, QuizConfig, QuestionRecord, QuestionSelector,
    Scorer, WeakAreaAnalyzer, AnswerSubmission, build_result_payload,
)

router = APIRouter()

# In-memory adaptive state store (production: use Redis)
# key = attempt_id, value = AdaptiveController
_adaptive_sessions: dict[str, AdaptiveController] = {}


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class QuizConfigCreate(BaseModel):
    title:                    str
    description:              Optional[str] = None
    filter_chapter:           Optional[int] = None
    filter_tags:              Optional[list[str]] = None
    filter_para_ids:          Optional[list[UUID]] = None
    filter_difficulty:        Optional[int] = Field(None, ge=1, le=3)
    question_count:           int  = Field(20, ge=1, le=100)
    question_types:           list[str] = ["multiple_choice", "true_false"]
    verified_only:            bool = False
    mode:                     str  = "standard"
    time_limit_mins:          Optional[int] = None
    passing_score:            int  = Field(70, ge=0, le=100)
    shuffle_questions:        bool = True
    shuffle_choices:          bool = True
    show_feedback:            str  = "after_each"
    adaptive_start_difficulty: int  = Field(2, ge=1, le=3)
    adaptive_window:           int  = Field(3, ge=2, le=10)
    adaptive_correct_threshold: float = Field(0.70, ge=0.5, le=1.0)
    adaptive_wrong_threshold:   float = Field(0.40, ge=0.0, le=0.5)


class AnswerIn(BaseModel):
    question_id: UUID
    choice_id:   Optional[UUID] = None
    free_text:   Optional[str]  = None
    response_ms: Optional[int]  = None


class SubmitAttemptBody(BaseModel):
    answers: list[AnswerIn]


class NextQuestionResponse(BaseModel):
    """For adaptive mode — returns the next question after each answer."""
    question:         Optional[dict]
    current_difficulty: int
    questions_remaining: int
    done:             bool


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_questions_from_db(
    db:     Session,
    config: QuizConfig,
    exclude_question_ids: Optional[list[str]] = None,
    para_ids_override:    Optional[list[str]] = None,
) -> list[QuestionRecord]:
    """
    Pull candidate questions from the DB according to config filters.
    Returns raw QuestionRecord objects for the engine to process.
    """
    sql = """
        SELECT
            q.id, q.paragraph_id, q.question_text, q.question_type,
            q.difficulty, q.explanation, q.is_verified,
            p.para_id, p.title AS para_title,
            COALESCE(qs.correct_count::float / NULLIF(qs.total_attempts, 0), 0) AS correct_rate,
            json_agg(
                json_build_object(
                    'id',         qc.id::text,
                    'text',       qc.choice_text,
                    'is_correct', qc.is_correct,
                    'sort_order', qc.sort_order
                ) ORDER BY qc.sort_order
            ) AS choices
        FROM quiz_questions q
        JOIN order_versions ov ON q.version_id = ov.id AND ov.is_current = TRUE
        LEFT JOIN paragraphs p  ON q.paragraph_id = p.id
        LEFT JOIN sections   se ON p.section_id = se.id
        LEFT JOIN chapters   c  ON se.chapter_id = c.id
        LEFT JOIN question_stats qs ON qs.question_id = q.id
        LEFT JOIN question_choices qc ON qc.question_id = q.id
        WHERE q.is_active = TRUE
    """
    params: dict = {}

    if config.verified_only:
        sql += " AND q.is_verified = TRUE"
    if config.filter_chapter:  # accessed via QuizConfig dict — see note below
        sql += " AND c.chapter_number = :chapter"
        params["chapter"] = config.filter_chapter
    if config.filter_difficulty:
        sql += " AND q.difficulty = :diff"
        params["diff"] = config.filter_difficulty
    if config.question_types:
        placeholders = ", ".join([f"'{t}'" for t in config.question_types])
        sql += f" AND q.question_type IN ({placeholders})"
    if para_ids_override:
        placeholders = ", ".join([f"'{p}'" for p in para_ids_override])
        sql += f" AND q.paragraph_id IN ({placeholders})"
    if exclude_question_ids:
        placeholders = ", ".join([f"'{q}'" for q in exclude_question_ids])
        sql += f" AND q.id NOT IN ({placeholders})"

    if config.filter_tags:
        sql += """
            AND EXISTS (
                SELECT 1 FROM paragraph_tags pt
                JOIN tags t ON pt.tag_id = t.id
                WHERE pt.paragraph_id = q.paragraph_id
                  AND t.name = ANY(:tags)
            )
        """
        params["tags"] = config.filter_tags

    sql += " GROUP BY q.id, p.para_id, p.title, qs.correct_count, qs.total_attempts"

    rows = db.execute(text(sql), params).fetchall()
    records = []
    for r in rows:
        rm = dict(r._mapping)
        import json as _json
        choices_raw = rm.get("choices") or []
        if isinstance(choices_raw, str):
            choices_raw = _json.loads(choices_raw)

        records.append(QuestionRecord(
            id            = str(rm["id"]),
            paragraph_id  = str(rm["paragraph_id"]) if rm.get("paragraph_id") else None,
            para_id       = rm.get("para_id"),
            para_title    = rm.get("para_title"),
            question_text = rm["question_text"],
            question_type = rm["question_type"],
            difficulty    = rm.get("difficulty") or 2,
            choices       = choices_raw,
            explanation   = rm.get("explanation"),
            is_verified   = bool(rm.get("is_verified")),
            correct_rate  = float(rm.get("correct_rate") or 0.0),
        ))
    return records


def _config_from_row(row: dict) -> QuizConfig:
    """Build a QuizConfig from a quiz_configs DB row."""
    return QuizConfig(
        mode                       = row.get("mode", "standard"),
        question_count             = row.get("question_count", 20),
        question_types             = row.get("question_types") or ["multiple_choice", "true_false"],
        shuffle_questions          = bool(row.get("shuffle_questions", True)),
        shuffle_choices            = bool(row.get("shuffle_choices", True)),
        show_feedback              = row.get("show_feedback", "after_each"),
        passing_score              = row.get("passing_score", 70),
        time_limit_mins            = row.get("time_limit_mins"),
        verified_only              = bool(row.get("verified_only", False)),
        adaptive_start_difficulty  = row.get("adaptive_start_difficulty", 2),
        adaptive_window            = row.get("adaptive_window", 3),
        adaptive_correct_threshold = float(row.get("adaptive_correct_threshold") or 0.70),
        adaptive_wrong_threshold   = float(row.get("adaptive_wrong_threshold") or 0.40),
    )


def _update_question_stats(db: Session, question_id: str, is_correct: bool):
    """Upsert question_stats after a graded answer."""
    db.execute(text("""
        INSERT INTO question_stats (question_id, total_attempts, correct_count, last_seen, updated_at)
        VALUES (:qid, 1, :correct, NOW(), NOW())
        ON CONFLICT (question_id) DO UPDATE SET
            total_attempts = question_stats.total_attempts + 1,
            correct_count  = question_stats.correct_count + :correct,
            difficulty_auto = 1.0 - (
                (question_stats.correct_count + :correct)::float /
                (question_stats.total_attempts + 1)
            ),
            last_seen   = NOW(),
            updated_at  = NOW()
    """), {"qid": question_id, "correct": 1 if is_correct else 0})


def _upsert_weak_area(db: Session, user_id: str, paragraph_id: str, is_correct: bool):
    """Update or create a weak area record after each wrong answer."""
    if not paragraph_id:
        return
    if is_correct:
        # Correct: reduce error weight (don't delete, may resolve over time)
        db.execute(text("""
            UPDATE user_weak_areas
            SET attempt_count = attempt_count + 1,
                error_rate    = wrong_count::float / (attempt_count + 1),
                resolved      = (wrong_count::float / (attempt_count + 1)) < 0.30
            WHERE user_id = :uid AND paragraph_id = :pid
        """), {"uid": user_id, "pid": paragraph_id})
    else:
        db.execute(text("""
            INSERT INTO user_weak_areas
                (id, user_id, paragraph_id, wrong_count, attempt_count, error_rate, last_wrong)
            VALUES
                (:id, :uid, :pid, 1, 1, 1.0, NOW())
            ON CONFLICT (user_id, paragraph_id) DO UPDATE SET
                wrong_count   = user_weak_areas.wrong_count + 1,
                attempt_count = user_weak_areas.attempt_count + 1,
                error_rate    = (user_weak_areas.wrong_count + 1)::float / (user_weak_areas.attempt_count + 1),
                last_wrong    = NOW(),
                resolved      = FALSE
        """), {"id": str(uuid.uuid4()), "uid": user_id, "pid": paragraph_id})


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ CONFIGS (builder)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/configs")
def list_configs(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """List all available quiz configs (own + published)."""
    rows = db.execute(text("""
        SELECT id, title, description, mode, question_count, passing_score,
               is_published, created_at,
               (SELECT COUNT(*) FROM quiz_questions qq
                JOIN order_versions ov ON qq.version_id = ov.id AND ov.is_current = TRUE
                WHERE qq.is_active = TRUE) AS available_questions
        FROM quiz_configs
        WHERE created_by = :uid OR is_published = TRUE
        ORDER BY is_published DESC, created_at DESC
    """), {"uid": str(user.id)}).fetchall()
    return [dict(r._mapping) for r in rows]


@router.post("/configs", status_code=201)
def create_config(
    body: QuizConfigCreate,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    config_id = str(uuid.uuid4())
    import json as _json
    db.execute(text("""
        INSERT INTO quiz_configs (
            id, created_by, title, description,
            filter_chapter, filter_tags, filter_difficulty,
            question_count, question_types, verified_only,
            mode, time_limit_mins, passing_score,
            shuffle_questions, shuffle_choices, show_feedback,
            adaptive_start_difficulty, adaptive_window,
            adaptive_correct_threshold, adaptive_wrong_threshold,
            is_published
        ) VALUES (
            :id, :uid, :title, :desc,
            :chapter, :tags, :diff,
            :count, :types, :verified,
            :mode, :time_limit, :passing,
            :shuffle_q, :shuffle_c, :feedback,
            :adap_start, :adap_window,
            :adap_correct, :adap_wrong,
            FALSE
        )
    """), {
        "id":          config_id,
        "uid":         str(user.id),
        "title":       body.title,
        "desc":        body.description,
        "chapter":     body.filter_chapter,
        "tags":        body.filter_tags,
        "diff":        body.filter_difficulty,
        "count":       body.question_count,
        "types":       body.question_types,
        "verified":    body.verified_only,
        "mode":        body.mode,
        "time_limit":  body.time_limit_mins,
        "passing":     body.passing_score,
        "shuffle_q":   body.shuffle_questions,
        "shuffle_c":   body.shuffle_choices,
        "feedback":    body.show_feedback,
        "adap_start":  body.adaptive_start_difficulty,
        "adap_window": body.adaptive_window,
        "adap_correct": body.adaptive_correct_threshold,
        "adap_wrong":   body.adaptive_wrong_threshold,
    })
    db.commit()
    return {"id": config_id, "title": body.title}


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION BANK
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/questions")
def list_questions(
    chapter:    Optional[int]  = Query(None),
    para_id:    Optional[str]  = Query(None),
    qtype:      Optional[str]  = Query(None),
    difficulty: Optional[int]  = Query(None, ge=1, le=3),
    verified:   Optional[bool] = Query(None),
    skip:       int = Query(0, ge=0),
    limit:      int = Query(50, ge=1, le=200),
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    sql = """
        SELECT q.id, q.question_text, q.question_type,
               q.difficulty, q.is_verified, q.is_active, q.created_at,
               p.para_id, p.title AS para_title,
               COALESCE(qs.total_attempts, 0) AS total_attempts,
               COALESCE(qs.correct_count, 0)  AS correct_count
        FROM quiz_questions q
        LEFT JOIN paragraphs p ON q.paragraph_id = p.id
        LEFT JOIN sections se  ON p.section_id = se.id
        LEFT JOIN chapters c   ON se.chapter_id = c.id
        LEFT JOIN question_stats qs ON qs.question_id = q.id
        JOIN order_versions ov ON q.version_id = ov.id AND ov.is_current = TRUE
        WHERE q.is_active = TRUE
    """
    params: dict = {}
    if chapter:
        sql += " AND c.chapter_number = :ch"; params["ch"] = chapter
    if para_id:
        sql += " AND p.para_id = :pid"; params["pid"] = para_id
    if qtype:
        sql += " AND q.question_type = :qt"; params["qt"] = qtype
    if difficulty:
        sql += " AND q.difficulty = :diff"; params["diff"] = difficulty
    if verified is not None:
        sql += " AND q.is_verified = :ver"; params["ver"] = verified

    sql += " ORDER BY q.created_at DESC LIMIT :lim OFFSET :skip"
    params["lim"] = limit; params["skip"] = skip

    rows = db.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# START AN ATTEMPT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/configs/{config_id}/attempt", status_code=201)
def start_attempt(
    config_id: UUID,
    db:        Session = Depends(get_db),
    user:      User    = Depends(get_current_user),
):
    """
    Start a new quiz attempt from a saved config.
    Returns the full question list for standard/timed modes,
    or the first question for adaptive mode.
    """
    config_row = db.execute(
        text("SELECT * FROM quiz_configs WHERE id = :id"),
        {"id": str(config_id)}
    ).fetchone()
    if not config_row:
        raise HTTPException(404, "Quiz config not found")

    config_dict = dict(config_row._mapping)
    config      = _config_from_row(config_dict)

    # Get recently-correct question IDs to deprioritize (last 7 days)
    seen_rows = db.execute(text("""
        SELECT DISTINCT question_id
        FROM quiz_attempt_answers qaa
        JOIN quiz_attempts qa ON qaa.attempt_id = qa.id
        WHERE qa.user_id = :uid
          AND qaa.is_correct = TRUE
          AND qa.completed_at >= NOW() - INTERVAL '7 days'
    """), {"uid": str(user.id)}).fetchall()
    seen_ids = {str(r.question_id) for r in seen_rows}

    # Get weak para IDs for weak_areas mode
    weak_para_ids = None
    if config.mode == "weak_areas":
        weak_rows = db.execute(text("""
            SELECT paragraph_id FROM user_weak_areas
            WHERE user_id = :uid AND resolved = FALSE
              AND error_rate >= 0.40
        """), {"uid": str(user.id)}).fetchall()
        weak_para_ids = {str(r.paragraph_id) for r in weak_rows}

    # Attach filter_chapter from config dict (QuizConfig doesn't hold it directly)
    config.filter_chapter = config_dict.get("filter_chapter")
    config.filter_tags    = config_dict.get("filter_tags")
    config.filter_difficulty = config_dict.get("filter_difficulty")

    candidates = _load_questions_from_db(db, config)
    selector   = QuestionSelector()
    questions  = selector.select(
        candidates     = candidates,
        config         = config,
        seen_ids       = seen_ids,
        weak_para_ids  = weak_para_ids,
    )

    if not questions:
        raise HTTPException(422, "No questions available for the given filters")

    # Create attempt record
    attempt_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO quiz_attempts (id, quiz_id, user_id, config_id, mode, question_count, started_at)
        VALUES (:id, :qid, :uid, :cid, :mode, :qcount, NOW())
    """), {
        "id":     attempt_id,
        "qid":    str(config_id),  # using config_id as quiz_id
        "uid":    str(user.id),
        "cid":    str(config_id),
        "mode":   config.mode,
        "qcount": len(questions),
    })
    db.commit()

    # For adaptive mode, initialise controller and return only first question
    if config.mode == "adaptive":
        ctrl = AdaptiveController(config)
        _adaptive_sessions[attempt_id] = ctrl
        first_q = _serialise_question(questions[0], config, reveal_answer=False)

        # Store question order in DB (serialised)
        _store_question_order(db, attempt_id, questions)

        return {
            "attempt_id":   attempt_id,
            "mode":         config.mode,
            "total":        len(questions),
            "show_feedback": config.show_feedback,
            "question":     first_q,
            "current_index": 0,
        }

    # Standard / timed_exam / weak_areas — return all questions at once
    serialised = [_serialise_question(q, config, reveal_answer=False) for q in questions]
    _store_question_order(db, attempt_id, questions)

    return {
        "attempt_id":    attempt_id,
        "mode":          config.mode,
        "total":         len(questions),
        "time_limit_mins": config.time_limit_mins,
        "show_feedback": config.show_feedback,
        "passing_score": config.passing_score,
        "questions":     serialised,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTIVE: SUBMIT ONE ANSWER, GET NEXT QUESTION
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/attempts/{attempt_id}/answer")
def submit_adaptive_answer(
    attempt_id: str,
    body:       AnswerIn,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    """
    Adaptive mode: submit one answer and receive the next question.
    Also returns immediate feedback if config.show_feedback == 'after_each'.
    """
    attempt = db.execute(
        text("SELECT * FROM quiz_attempts WHERE id = :id AND user_id = :uid"),
        {"id": attempt_id, "uid": str(user.id)}
    ).fetchone()
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    if dict(attempt._mapping).get("completed_at"):
        raise HTTPException(409, "Attempt already completed")

    ctrl = _adaptive_sessions.get(attempt_id)
    if not ctrl:
        raise HTTPException(410, "Adaptive session expired — reload attempt")

    # Grade this answer
    question_row = db.execute(
        text("""
            SELECT q.*, qc.id AS correct_choice_id
            FROM quiz_questions q
            JOIN question_choices qc ON qc.question_id = q.id AND qc.is_correct = TRUE
            WHERE q.id = :qid
            LIMIT 1
        """),
        {"qid": str(body.question_id)}
    ).fetchone()
    if not question_row:
        raise HTTPException(404, "Question not found")

    qr = dict(question_row._mapping)
    is_correct = str(body.choice_id) == str(qr["correct_choice_id"]) if body.choice_id else False

    # Record answer
    db.execute(text("""
        INSERT INTO quiz_attempt_answers
            (id, attempt_id, question_id, choice_id, is_correct, response_ms, answered_at)
        VALUES (:id, :aid, :qid, :cid, :correct, :ms, NOW())
    """), {
        "id":      str(uuid.uuid4()),
        "aid":     attempt_id,
        "qid":     str(body.question_id),
        "cid":     str(body.choice_id) if body.choice_id else None,
        "correct": is_correct,
        "ms":      body.response_ms,
    })

    _update_question_stats(db, str(body.question_id), is_correct)
    _upsert_weak_area(db, str(user.id), str(qr.get("paragraph_id", "")), is_correct)
    db.commit()

    # Advance adaptive controller
    next_difficulty = ctrl.record(is_correct)

    # Count answered so far
    answered_count = db.execute(text("""
        SELECT COUNT(*) FROM quiz_attempt_answers WHERE attempt_id = :aid
    """), {"aid": attempt_id}).scalar()

    total_q = dict(attempt._mapping)["question_count"]
    done = answered_count >= total_q

    if done:
        del _adaptive_sessions[attempt_id]

    # Feedback payload (shown if show_feedback == 'after_each')
    feedback = None
    config_row = db.execute(
        text("SELECT * FROM quiz_configs WHERE id = :id"),
        {"id": str(dict(attempt._mapping)["config_id"])}
    ).fetchone()
    attempt_config = _config_from_row(dict(config_row._mapping)) if config_row else QuizConfig()
    show_fb = attempt_config.show_feedback

    if show_fb == "after_each":
        correct_text = db.execute(
            text("SELECT choice_text FROM question_choices WHERE id = :id"),
            {"id": str(qr["correct_choice_id"])}
        ).scalar()
        feedback = {
            "is_correct":        is_correct,
            "correct_choice_id": str(qr["correct_choice_id"]),
            "correct_text":      correct_text,
            "explanation":       qr.get("explanation"),
        }

    # Get next question if not done
    next_q = None
    if not done:
        answered_ids = {
            str(r.question_id)
            for r in db.execute(
                text("SELECT question_id FROM quiz_attempt_answers WHERE attempt_id = :aid"),
                {"aid": attempt_id}
            ).fetchall()
        }
        next_row = db.execute(text("""
            SELECT aqo.question_id, aqo.sequence_number
            FROM attempt_question_order aqo
            WHERE aqo.attempt_id = :aid
              AND aqo.question_id::text NOT IN :answered
            ORDER BY aqo.sequence_number ASC
            LIMIT 1
        """), {"aid": attempt_id, "answered": tuple(answered_ids) or ('__none__',)}).fetchone()

        if next_row:
            next_q_full = _load_single_question(db, str(next_row.question_id))
            if next_q_full:
                next_q = _serialise_question(next_q_full, attempt_config, reveal_answer=False)

    return {
        "feedback":            feedback,
        "next_question":       next_q,
        "current_difficulty":  next_difficulty,
        "answered":            answered_count,
        "total":               total_q,
        "done":                done,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUBMIT COMPLETE ATTEMPT (standard / timed modes)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/attempts/{attempt_id}/submit")
def submit_attempt(
    attempt_id: str,
    body:       SubmitAttemptBody,
    db:         Session = Depends(get_db),
    user:       User    = Depends(get_current_user),
):
    """Submit all answers at once and receive the full scored result."""
    attempt_row = db.execute(
        text("SELECT * FROM quiz_attempts WHERE id = :id AND user_id = :uid"),
        {"id": attempt_id, "uid": str(user.id)}
    ).fetchone()
    if not attempt_row:
        raise HTTPException(404, "Attempt not found")
    attempt = dict(attempt_row._mapping)
    if attempt.get("completed_at"):
        raise HTTPException(409, "Attempt already submitted")

    # Load questions for this attempt (in order)
    q_order_rows = db.execute(text("""
        SELECT question_id FROM attempt_question_order
        WHERE attempt_id = :aid ORDER BY sequence_number
    """), {"aid": attempt_id}).fetchall()
    q_ids = [str(r.question_id) for r in q_order_rows]

    questions = [q for qid in q_ids if (q := _load_single_question(db, qid))]
    if not questions:
        raise HTTPException(422, "No questions found for this attempt")

    # Load config
    config_row = db.execute(
        text("SELECT * FROM quiz_configs WHERE id = :id"),
        {"id": str(attempt.get("config_id"))}
    ).fetchone()
    config = _config_from_row(dict(config_row._mapping)) if config_row else QuizConfig()

    # Grade
    subs = [
        AnswerSubmission(
            question_id = str(a.question_id),
            choice_id   = str(a.choice_id) if a.choice_id else None,
            free_text   = a.free_text,
            response_ms = a.response_ms,
        )
        for a in body.answers
    ]

    started_at = attempt["started_at"]
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    scorer = Scorer()
    result = scorer.grade_attempt(
        questions   = questions,
        submissions = subs,
        config      = config,
        attempt_id  = attempt_id,
        quiz_id     = str(attempt.get("config_id", "")),
        user_id     = str(user.id),
        started_at  = started_at,
    )

    # Persist answers + stats
    for ga in result.graded_answers:
        db.execute(text("""
            INSERT INTO quiz_attempt_answers
                (id, attempt_id, question_id, choice_id, free_text,
                 is_correct, response_ms, answered_at)
            VALUES (:id, :aid, :qid, :cid, :ft, :correct, :ms, NOW())
            ON CONFLICT DO NOTHING
        """), {
            "id":      str(uuid.uuid4()),
            "aid":     attempt_id,
            "qid":     ga.question_id,
            "cid":     ga.choice_id,
            "ft":      ga.free_text,
            "correct": ga.is_correct,
            "ms":      ga.response_ms,
        })
        _update_question_stats(db, ga.question_id, ga.is_correct)

        # Find paragraph_id for weak area update
        para_id_row = db.execute(
            text("SELECT paragraph_id FROM quiz_questions WHERE id = :qid"),
            {"qid": ga.question_id}
        ).fetchone()
        if para_id_row and para_id_row.paragraph_id:
            _upsert_weak_area(db, str(user.id), str(para_id_row.paragraph_id), ga.is_correct)

    # Close the attempt
    db.execute(text("""
        UPDATE quiz_attempts SET
            score        = :score,
            passed       = :passed,
            completed_at = NOW(),
            time_used_secs = :time_secs
        WHERE id = :id
    """), {
        "score":     result.score_pct,
        "passed":    result.passed,
        "time_secs": result.time_used_secs,
        "id":        attempt_id,
    })
    db.commit()

    return build_result_payload(result, questions)


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS & HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/attempts/{attempt_id}")
def get_attempt_result(
    attempt_id: str,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Retrieve a completed attempt result."""
    attempt_row = db.execute(
        text("SELECT * FROM quiz_attempts WHERE id = :id AND user_id = :uid"),
        {"id": attempt_id, "uid": str(user.id)}
    ).fetchone()
    if not attempt_row:
        raise HTTPException(404, "Attempt not found")
    attempt = dict(attempt_row._mapping)
    if not attempt.get("completed_at"):
        raise HTTPException(409, "Attempt not yet completed")

    answers = db.execute(text("""
        SELECT qaa.*, q.question_text, q.question_type, q.difficulty, q.explanation,
               p.para_id, p.title AS para_title,
               cc.choice_text AS correct_text,
               (SELECT id FROM question_choices WHERE question_id = q.id AND is_correct LIMIT 1) AS correct_choice_id
        FROM quiz_attempt_answers qaa
        JOIN quiz_questions q ON qaa.question_id = q.id
        LEFT JOIN paragraphs p ON q.paragraph_id = p.id
        LEFT JOIN question_choices cc ON cc.question_id = q.id AND cc.is_correct = TRUE
        WHERE qaa.attempt_id = :aid
        ORDER BY qaa.answered_at
    """), {"aid": attempt_id}).fetchall()

    return {
        "attempt":  attempt,
        "answers":  [dict(r._mapping) for r in answers],
    }


@router.get("/attempts")
def list_attempts(
    limit: int = Query(20, ge=1, le=100),
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    rows = db.execute(text("""
        SELECT qa.id, qa.mode, qa.score, qa.passed, qa.question_count,
               qa.started_at, qa.completed_at, qa.time_used_secs,
               qc.title AS config_title
        FROM quiz_attempts qa
        LEFT JOIN quiz_configs qc ON qa.config_id = qc.id
        WHERE qa.user_id = :uid AND qa.completed_at IS NOT NULL
        ORDER BY qa.completed_at DESC
        LIMIT :lim
    """), {"uid": str(user.id), "lim": limit}).fetchall()
    return [dict(r._mapping) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# WEAK AREAS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/weak-areas")
def get_weak_areas(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Return the student's current weak area paragraphs with error rates."""
    rows = db.execute(text("""
        SELECT wa.paragraph_id, wa.wrong_count, wa.attempt_count,
               wa.error_rate, wa.last_wrong, wa.resolved,
               p.para_id, p.title AS para_title,
               se.title AS section_title,
               c.chapter_number, c.title AS chapter_title
        FROM user_weak_areas wa
        JOIN paragraphs p ON wa.paragraph_id = p.id
        JOIN sections se  ON p.section_id = se.id
        JOIN chapters c   ON se.chapter_id = c.id
        WHERE wa.user_id = :uid AND wa.resolved = FALSE
        ORDER BY wa.error_rate DESC, wa.wrong_count DESC
    """), {"uid": str(user.id)}).fetchall()
    return [dict(r._mapping) for r in rows]


@router.delete("/weak-areas/{paragraph_id}", status_code=204)
def dismiss_weak_area(
    paragraph_id: UUID,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Mark a weak area as resolved (student or instructor action)."""
    db.execute(text("""
        UPDATE user_weak_areas SET resolved = TRUE
        WHERE user_id = :uid AND paragraph_id = :pid
    """), {"uid": str(user.id), "pid": str(paragraph_id)})
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: AI QUESTION GENERATION
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/admin/generate", status_code=202)
async def generate_questions(
    body:       QuizConfigCreate,   # reuse config schema for filter params
    background: BackgroundTasks,
    para_ids:   list[UUID] = Query(..., description="Paragraph IDs to generate for"),
    overwrite:  bool       = Query(False),
    db:         Session    = Depends(get_db),
    user:       User       = Depends(get_current_user),
):
    if user.role not in ("instructor", "admin"):
        raise HTTPException(403, "Instructor or admin role required")

    # Load paragraph content
    placeholders = ", ".join([f"'{str(p)}'" for p in para_ids])
    rows = db.execute(text(f"""
        SELECT p.id, p.para_id, p.title,
               json_agg(json_build_object(
                   'block_type', cb.block_type,
                   'label',      cb.label,
                   'content',    cb.content
               ) ORDER BY cb.sequence) AS blocks
        FROM paragraphs p
        JOIN content_blocks cb ON cb.paragraph_id = p.id
        WHERE p.id IN ({placeholders})
        GROUP BY p.id
    """)).fetchall()

    if not rows:
        raise HTTPException(404, "No paragraphs found")

    import json as _json
    para_dicts = []
    for r in rows:
        rm = dict(r._mapping)
        para_dicts.append({
            "db_id":   str(rm["id"]),
            "para_id": rm["para_id"],
            "title":   rm.get("title", ""),
            "blocks":  _json.loads(rm["blocks"]) if isinstance(rm["blocks"], str) else rm["blocks"],
        })

    # version_id
    ver_row = db.execute(text(
        "SELECT id FROM order_versions WHERE is_current = TRUE LIMIT 1"
    )).fetchone()
    version_id = str(ver_row.id) if ver_row else None

    skip_ids: set[str] = set()
    if not overwrite:
        existing = db.execute(text(f"""
            SELECT DISTINCT p.para_id FROM quiz_questions q
            JOIN paragraphs p ON q.paragraph_id = p.id
            WHERE q.paragraph_id IN ({placeholders}) AND q.generation_source IN ('ai_auto', 'local_auto', 'curated')
        """)).fetchall()
        skip_ids = {r.para_id for r in existing}

    run_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO question_generation_runs
            (id, triggered_by, paragraph_ids, status)
        VALUES (:id, :uid, :pids, 'running')
    """), {"id": run_id, "uid": str(user.id), "pids": [str(p) for p in para_ids]})
    db.commit()

    background.add_task(
        _run_generation_background, para_dicts, version_id, str(user.id), skip_ids, run_id
    )

    return {"run_id": run_id, "status": "queued", "paragraphs": len(para_dicts)}


@router.put("/questions/{question_id}/verify", status_code=204)
def verify_question(
    question_id: UUID,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user),
):
    """Mark a question as instructor-verified."""
    if user.role not in ("instructor", "admin"):
        raise HTTPException(403, "Instructor or admin role required")
    db.execute(text("""
        UPDATE quiz_questions SET is_verified = TRUE WHERE id = :id
    """), {"id": str(question_id)})
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND: AI GENERATION
# ─────────────────────────────────────────────────────────────────────────────

async def _run_generation_background(
    para_dicts:    list[dict],
    version_id:    Optional[str],
    created_by:    str,
    skip_para_ids: set[str],
    run_id:        str,
):
    from ..services.question_generator import generate_questions_for_paragraph
    from ..services.db import SessionLocal
    import asyncio

    total_created = 0
    errors = []

    for para in para_dicts:
        if para["para_id"] in skip_para_ids:
            continue
        try:
            questions = await generate_questions_for_paragraph(
                para_id    = para["para_id"],
                para_title = para["title"],
                blocks     = para["blocks"],
            )

            with SessionLocal() as db:
                for q in questions:
                    q_id = str(uuid.uuid4())
                    db.execute(text("""
                        INSERT INTO quiz_questions
                            (id, paragraph_id, version_id, created_by,
                             question_text, question_type, explanation,
                             difficulty, is_active, is_verified, generation_source)
                        VALUES
                            (:id, :pid, :ver, :uid,
                             :qtext, :qtype, :exp,
                             :diff, TRUE, FALSE, :generation_source)
                    """), {
                        "id":    q_id,
                        "pid":   para["db_id"],
                        "ver":   version_id,
                        "uid":   created_by,
                        "qtext": q.question_text,
                        "qtype": q.question_type,
                        "exp":   q.explanation,
                        "diff":  q.difficulty,
                        "generation_source": q.generation_source,
                    })
                    for i, c in enumerate(q.choices):
                        db.execute(text("""
                            INSERT INTO question_choices
                                (id, question_id, choice_text, is_correct, sort_order)
                            VALUES (:id, :qid, :text, :correct, :order)
                        """), {
                            "id":      str(uuid.uuid4()),
                            "qid":     q_id,
                            "text":    c.text,
                            "correct": c.is_correct,
                            "order":   i,
                        })
                    total_created += 1
                db.commit()

        except Exception as e:
            errors.append(f"{para['para_id']}: {str(e)}")

        await asyncio.sleep(0.75)

    # Mark run complete
    from ..services.db import SessionLocal
    with SessionLocal() as db:
        import json as _json
        db.execute(text("""
            UPDATE question_generation_runs SET
                status = :status, questions_created = :count,
                errors = :errors, completed_at = NOW()
            WHERE id = :id
        """), {
            "status": "failed" if errors and not total_created else "complete",
            "count":  total_created,
            "errors": _json.dumps(errors),
            "id":     run_id,
        })
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _serialise_question(q: QuestionRecord, config: QuizConfig, reveal_answer: bool) -> dict:
    source_choices = [dict(c) for c in q.choices]
    if config.shuffle_choices and len(source_choices) > 1:
        random.shuffle(source_choices)

    choices = []
    for display_order, c in enumerate(source_choices):
        entry = {
            "id":            c["id"],
            "text":          c["text"],
            "display_order": display_order,
        }
        if reveal_answer:
            entry["is_correct"] = c.get("is_correct", False)
        choices.append(entry)

    return {
        "id":            q.id,
        "para_id":       q.para_id,
        "para_title":    q.para_title,
        "question_text": q.question_text,
        "question_type": q.question_type,
        "difficulty":    q.difficulty,
        "choices":       choices,
        # Explanation only revealed after answer (handled client-side)
    }


def _load_single_question(db: Session, question_id: str) -> Optional[QuestionRecord]:
    row = db.execute(text("""
        SELECT q.id, q.paragraph_id, q.question_text, q.question_type,
               q.difficulty, q.explanation, q.is_verified,
               p.para_id, p.title AS para_title
        FROM quiz_questions q
        LEFT JOIN paragraphs p ON q.paragraph_id = p.id
        WHERE q.id = :id
    """), {"id": question_id}).fetchone()
    if not row:
        return None
    rm = dict(row._mapping)

    choices_rows = db.execute(text("""
        SELECT id::text, choice_text AS text, is_correct, sort_order
        FROM question_choices WHERE question_id = :id ORDER BY sort_order
    """), {"id": question_id}).fetchall()

    return QuestionRecord(
        id            = str(rm["id"]),
        paragraph_id  = str(rm["paragraph_id"]) if rm.get("paragraph_id") else None,
        para_id       = rm.get("para_id"),
        para_title    = rm.get("para_title"),
        question_text = rm["question_text"],
        question_type = rm["question_type"],
        difficulty    = rm.get("difficulty") or 2,
        choices       = [dict(r._mapping) for r in choices_rows],
        explanation   = rm.get("explanation"),
        is_verified   = bool(rm.get("is_verified")),
    )


def _store_question_order(db: Session, attempt_id: str, questions: list[QuestionRecord]):
    """Persist question order for an attempt so we can resume/score it."""
    # Create the table if it doesn't exist (light migration guard)
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS attempt_question_order (
            attempt_id  UUID NOT NULL,
            question_id UUID NOT NULL,
            sequence_number INTEGER NOT NULL,
            PRIMARY KEY (attempt_id, question_id)
        )
    """))
    for i, q in enumerate(questions):
        db.execute(text("""
            INSERT INTO attempt_question_order (attempt_id, question_id, sequence_number)
            VALUES (:aid, :qid, :seq)
            ON CONFLICT DO NOTHING
        """), {"aid": attempt_id, "qid": q.id, "seq": i})
    db.commit()
