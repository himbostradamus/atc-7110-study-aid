-- =============================================================================
-- QUIZ ENGINE SCHEMA ADDITIONS  — append to schema.sql
-- =============================================================================
-- Adds:
--   question_stats       — aggregate performance per question (for adaptive selection)
--   quiz_configs         — reusable quiz configurations (filters, mode, adaptive settings)
--   question_tags        — many-to-many tags on questions (separate from paragraph tags)
--   attempt_question_log — richer per-question timing within an attempt
--   user_weak_areas      — materialized view of where a student struggles most
-- =============================================================================

-- ── Per-question aggregate stats (updated after every attempt) ───────────────
-- Avoids scanning quiz_attempt_answers for every adaptive selection query.
CREATE TABLE question_stats (
    question_id     UUID PRIMARY KEY REFERENCES quiz_questions(id) ON DELETE CASCADE,
    total_attempts  INTEGER NOT NULL DEFAULT 0,
    correct_count   INTEGER NOT NULL DEFAULT 0,
    avg_response_ms INTEGER,                      -- average time to answer
    difficulty_auto NUMERIC(4,3),                 -- computed: 1 - (correct / total), 0–1
    last_seen       TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Reusable quiz configuration (instructors save these, students can run them) 
CREATE TABLE quiz_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by      UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,

    -- Source filters (any combination)
    filter_chapter  INTEGER,                      -- e.g. 2 = Chapter 2 only
    filter_section  UUID REFERENCES sections(id),
    filter_tags     TEXT[],                       -- e.g. ARRAY['IFR','separation']
    filter_para_ids UUID[],                       -- specific paragraphs
    filter_difficulty SMALLINT,                   -- 1 | 2 | 3 | NULL = all

    -- Question composition
    question_count      INTEGER NOT NULL DEFAULT 20,
    question_types      TEXT[] DEFAULT ARRAY['multiple_choice','true_false'],
    verified_only       BOOLEAN DEFAULT FALSE,    -- only instructor-verified questions

    -- Delivery mode
    mode                VARCHAR(20) NOT NULL DEFAULT 'standard'
                        CHECK (mode IN ('standard','adaptive','weak_areas','timed_exam')),
    time_limit_mins     INTEGER,
    passing_score       SMALLINT DEFAULT 70,
    shuffle_questions   BOOLEAN DEFAULT TRUE,
    shuffle_choices     BOOLEAN DEFAULT TRUE,
    show_feedback       VARCHAR(20) DEFAULT 'after_each'
                        CHECK (show_feedback IN ('after_each','end_only','never')),

    -- Adaptive settings (used when mode = 'adaptive')
    adaptive_start_difficulty SMALLINT DEFAULT 2,     -- 1=easy 2=medium 3=hard
    adaptive_window           INTEGER DEFAULT 3,      -- look at last N answers to adjust
    adaptive_correct_threshold NUMERIC(3,2) DEFAULT 0.70, -- raise difficulty above this
    adaptive_wrong_threshold   NUMERIC(3,2) DEFAULT 0.40, -- lower difficulty below this

    is_published    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Richer per-question log within an attempt ────────────────────────────────
-- Extends quiz_attempt_answers with timing and adaptive context.
ALTER TABLE quiz_attempt_answers
    ADD COLUMN IF NOT EXISTS response_ms      INTEGER,
    ADD COLUMN IF NOT EXISTS difficulty_at_time SMALLINT,   -- difficulty when shown
    ADD COLUMN IF NOT EXISTS sequence_number  INTEGER;      -- order shown in this attempt

-- ── Attempt metadata extensions ──────────────────────────────────────────────
ALTER TABLE quiz_attempts
    ADD COLUMN IF NOT EXISTS config_id      UUID REFERENCES quiz_configs(id),
    ADD COLUMN IF NOT EXISTS mode           VARCHAR(20) DEFAULT 'standard',
    ADD COLUMN IF NOT EXISTS question_count INTEGER,
    ADD COLUMN IF NOT EXISTS time_used_secs INTEGER;

-- ── User weak areas: paragraphs where a student consistently gets wrong ───────
-- Populated by a background job / on-demand after each quiz completion.
CREATE TABLE user_weak_areas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    wrong_count     INTEGER NOT NULL DEFAULT 0,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    error_rate      NUMERIC(4,3),    -- wrong / attempt, 0–1
    last_wrong      TIMESTAMPTZ,
    flagged_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved        BOOLEAN DEFAULT FALSE,    -- instructor or student can clear
    UNIQUE (user_id, paragraph_id)
);

CREATE INDEX idx_weak_areas_user ON user_weak_areas(user_id, error_rate DESC);

-- ── Question generation audit ─────────────────────────────────────────────────
-- Tracks AI-generated question batches for admin review workflow.
CREATE TABLE question_generation_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    triggered_by    UUID NOT NULL REFERENCES users(id),
    paragraph_ids   UUID[],
    questions_created INTEGER DEFAULT 0,
    status          VARCHAR(20) CHECK (status IN ('running','complete','failed')),
    errors          JSONB DEFAULT '[]',
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- ── Indexes for adaptive selection ───────────────────────────────────────────
CREATE INDEX idx_quiz_questions_difficulty
    ON quiz_questions(difficulty, is_active, is_verified);

CREATE INDEX idx_quiz_questions_paragraph
    ON quiz_questions(paragraph_id)
    WHERE is_active = TRUE;

CREATE INDEX idx_question_stats_difficulty
    ON question_stats(difficulty_auto);
