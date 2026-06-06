-- =============================================================================
-- ENGAGEMENT ACTIVITIES SCHEMA
-- Append to schema.sql
-- =============================================================================
-- Tables:
--   activity_types     — registry of the supported lesson activity types
--   activities         — generated activity instances linked to paragraphs
--   lesson_sessions    — one row per study session a user starts
--   session_activities — ordered activity list within a session + results
--   paragraph_mastery  — crown level per user × paragraph (the gamification core)
--   mastery_events     — immutable log of every mastery level change
-- =============================================================================

-- ── Activity type registry ────────────────────────────────────────────────────
CREATE TABLE activity_types (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(40) NOT NULL UNIQUE,
    label       VARCHAR(100) NOT NULL,
    description TEXT,
    scoring_fn  VARCHAR(50) NOT NULL    -- name of the scoring function to apply
);

INSERT INTO activity_types (slug, label, description, scoring_fn) VALUES
    ('phraseology_builder', 'Phraseology builder',
     'Tap word tokens in the correct order to construct ATC phraseology.',
     'score_phraseology_builder'),
    ('spot_the_error', 'Spot the error',
     'Identify the incorrect word or phrase in a piece of ATC phraseology.',
     'score_spot_the_error'),
    ('sequence_steps', 'Sequence the steps',
     'Drag procedure steps into the correct operational order.',
     'score_sequence_steps'),
    ('match_pairs', 'Match pairs',
     'Match ATC terms with their definitions.',
     'score_match_pairs'),
    ('readback_check', 'Read-back check',
     'Given a controller clearance, identify the correct pilot read-back.',
     'score_readback_check'),
    ('situation_action', 'Situation → action',
     'Given an ATC scenario, choose the correct controller response.',
     'score_situation_action'),
    ('directive_check', 'Directive check',
     'Evaluate whether a directive statement is operationally correct.',
     'score_choice_activity'),
    ('conditional_rule_check', 'Conditional rule',
     'Evaluate whether a conditional rule is operationally correct.',
     'score_choice_activity'),
    ('term_definition_check', 'Term definition',
     'Evaluate whether a term-definition statement is correct.',
     'score_choice_activity'),
    ('document_control_check', 'Document control',
     'Evaluate document-control or administrative statements.',
     'score_choice_activity'),
    ('requirement_check', 'Requirement check',
     'Evaluate requirement statements drawn from the order.',
     'score_choice_activity'),
    ('scope_check', 'Applicability check',
     'Evaluate whether an applicability statement is correct.',
     'score_choice_activity'),
    ('capability_check', 'System capability',
     'Evaluate system-capability statements.',
     'score_choice_activity'),
    ('reference_check', 'Reference check',
     'Answer questions about supporting references.',
     'score_choice_activity'),
    ('minima_rule_check', 'Minima rule',
     'Evaluate statements about minima and separation rules.',
     'score_choice_activity'),
    ('list_membership', 'List membership',
     'Choose the item that belongs or does not belong in a procedural list.',
     'score_choice_activity'),
    ('table_lookup', 'Table lookup',
     'Use a referenced table to answer the question.',
     'score_choice_activity'),
    ('example_check', 'Example check',
     'Decide whether an example or wording sample is correct.',
     'score_choice_activity'),
    ('knowledge_check', 'Knowledge check',
     'Answer a multiple-choice knowledge question.',
     'score_choice_activity');


-- ── Generated activity instances ─────────────────────────────────────────────
CREATE TABLE activities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES order_versions(id),
    activity_type   VARCHAR(40) NOT NULL REFERENCES activity_types(slug),
    created_by      UUID REFERENCES users(id),       -- NULL = system-generated

    -- Rendered content (type-specific JSON)
    -- See content_json shapes below per type
    content_json    JSONB NOT NULL,

    difficulty      SMALLINT CHECK (difficulty BETWEEN 1 AND 3) DEFAULT 2,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    generation_source VARCHAR(20) DEFAULT 'local_auto'
        CHECK (generation_source IN ('manual', 'ai_auto', 'ai_assisted', 'local_auto', 'curated')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activities_paragraph ON activities(paragraph_id, activity_type);
CREATE INDEX idx_activities_type      ON activities(activity_type, is_active);

-- content_json shapes by activity_type:
--
-- phraseology_builder:
--   { "instruction": "...", "target_phrase": "...",
--     "word_bank": ["LOW","ALTITUDE",...],   ← correct words + distractors shuffled
--     "correct_sequence": [0,3,1,...] }      ← indices into word_bank in correct order
--
-- spot_the_error:
--   { "instruction": "...", "display_text": "...",
--     "tokens": ["TRAFFIC","ALERT","Cessna","34J",...],
--     "error_index": 8, "correct_token": "LEFT",
--     "explanation": "..." }
--
-- sequence_steps:
--   { "instruction": "...",
--     "steps": [{"id":"a","text":"..."},{"id":"b","text":"..."},...],
--     "correct_order": ["b","a","c"],
--     "explanation": "..." }
--
-- match_pairs:
--   { "instruction": "...",
--     "pairs": [{"term":"...","definition":"..."},...]
--   }   ← client shuffles both columns independently
--
-- readback_check:
--   { "instruction": "...", "clearance": "...",
--     "choices": [{"text":"...","is_correct":bool},...],
--     "explanation": "..." }
--
-- situation_action:
--   { "instruction": "...", "situation": "...",
--     "para_context": "...",        ← relevant excerpt from the paragraph
--     "choices": [{"text":"...","is_correct":bool},...],
--     "explanation": "..." }


-- ── Lesson sessions ───────────────────────────────────────────────────────────
CREATE TABLE lesson_sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- What content this session covers
    filter_type         VARCHAR(20) NOT NULL DEFAULT 'section'
        CHECK (filter_type IN ('section','chapter','tag','paragraph_list','weak_areas')),
    filter_value        TEXT,          -- section UUID, chapter number, tag name, etc.
    paragraph_ids       UUID[],        -- resolved paragraph IDs at session-start time

    -- Session state
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','completed','abandoned')),
    total_activities    INTEGER,
    completed_count     INTEGER DEFAULT 0,
    correct_count       INTEGER DEFAULT 0,

    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,

    -- Crown changes resulting from this session (for the results screen)
    crown_changes       JSONB DEFAULT '[]'
    -- e.g. [{"para_id":"2-1-6","old_level":1,"new_level":2}]
);

CREATE INDEX idx_sessions_user ON lesson_sessions(user_id, started_at DESC);


-- ── Session activities (ordered list of activities in a session) ──────────────
CREATE TABLE session_activities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES lesson_sessions(id) ON DELETE CASCADE,
    activity_id     UUID NOT NULL REFERENCES activities(id),
    sequence_num    INTEGER NOT NULL,        -- display order in session (1-based)

    -- Result (filled after user answers)
    is_correct      BOOLEAN,
    score           NUMERIC(4,3),            -- 0.0–1.0 (partial credit for some types)
    response_json   JSONB,                   -- the user's raw answer submission
    result_json     JSONB,                   -- grading detail (correct token, explanation, etc.)
    response_ms     INTEGER,
    answered_at     TIMESTAMPTZ,

    UNIQUE (session_id, sequence_num)
);

CREATE INDEX idx_session_activities_session ON session_activities(session_id, sequence_num);


-- ── Paragraph mastery (crowns) ────────────────────────────────────────────────
CREATE TABLE paragraph_mastery (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,

    -- Crown level: 0=none 1=introduced 2=familiar 3=proficient 4=gold
    crown_level     SMALLINT NOT NULL DEFAULT 0 CHECK (crown_level BETWEEN 0 AND 4),

    -- Activity coverage: how many activities completed per type
    type_counts     JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- e.g. {"phraseology_builder":3,"spot_the_error":2,"match_pairs":5,...}

    -- Score averages per type (for crown calculation)
    type_avg_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- e.g. {"phraseology_builder":0.87,"spot_the_error":0.92,...}

    -- Aggregate stats
    total_activities    INTEGER NOT NULL DEFAULT 0,
    total_correct       INTEGER NOT NULL DEFAULT 0,
    last_practiced      TIMESTAMPTZ,
    crown_achieved_at   TIMESTAMPTZ,    -- when current level was first reached

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (user_id, paragraph_id)
);

CREATE INDEX idx_mastery_user        ON paragraph_mastery(user_id);
CREATE INDEX idx_mastery_crown       ON paragraph_mastery(user_id, crown_level DESC);
CREATE INDEX idx_mastery_practiced   ON paragraph_mastery(user_id, last_practiced DESC);


-- ── Mastery event log (immutable, for analytics) ──────────────────────────────
CREATE TABLE mastery_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES lesson_sessions(id),
    old_level       SMALLINT NOT NULL,
    new_level       SMALLINT NOT NULL,
    trigger_type    VARCHAR(40),    -- e.g. "phraseology_builder"
    trigger_score   NUMERIC(4,3),
    occurred_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mastery_events_user ON mastery_events(user_id, occurred_at DESC);


-- ── Activity generation run log ───────────────────────────────────────────────
CREATE TABLE activity_generation_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    triggered_by        UUID NOT NULL REFERENCES users(id),
    paragraph_ids       UUID[],
    activity_types_req  TEXT[],     -- which types were requested
    activities_created  INTEGER DEFAULT 0,
    status              VARCHAR(20) CHECK (status IN ('running','complete','failed')),
    errors              JSONB DEFAULT '[]',
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);
