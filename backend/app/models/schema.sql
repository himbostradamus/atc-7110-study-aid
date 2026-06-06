-- =============================================================================
-- ATC 7110.65 Learning Platform - Database Schema
-- PostgreSQL
-- =============================================================================
-- Design philosophy:
--   Content is versioned at the order_version level. Every paragraph,
--   section, and content block is linked to a specific version so that
--   when 7110.65BC (or a new change) is released, only the delta needs
--   to be imported and existing user progress / quiz banks remain valid.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- full-text search on content


-- ─────────────────────────────────────────────────────────────────────────────
-- CONTENT VERSIONING
-- Tracks each edition/change of the 7110.65
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE order_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    edition         VARCHAR(20) NOT NULL UNIQUE,   -- e.g. "7110.65BB", "7110.65BB CHG 1"
    effective_date  DATE NOT NULL,
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    supersedes_id   UUID REFERENCES order_versions(id),
    notes           TEXT,
    imported_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Only one version can be current at a time
CREATE UNIQUE INDEX idx_one_current_version
    ON order_versions (is_current)
    WHERE is_current = TRUE;


-- ─────────────────────────────────────────────────────────────────────────────
-- DOCUMENT STRUCTURE  (Chapter → Section → Paragraph → ContentBlock)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE chapters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id      UUID NOT NULL REFERENCES order_versions(id) ON DELETE CASCADE,
    chapter_number  INTEGER NOT NULL,              -- e.g. 2
    title           VARCHAR(255) NOT NULL,         -- e.g. "General Control"
    sort_order      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (version_id, chapter_number)
);

CREATE TABLE sections (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id      UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES order_versions(id) ON DELETE CASCADE,
    section_number  INTEGER NOT NULL,              -- e.g. 1 (within chapter)
    title           VARCHAR(255) NOT NULL,         -- e.g. "General"
    sort_order      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (chapter_id, section_number)
);

-- Core content unit — a single numbered paragraph like 2-1-6
CREATE TABLE paragraphs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    section_id      UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES order_versions(id) ON DELETE CASCADE,
    para_id         VARCHAR(30) NOT NULL,          -- e.g. "2-1-6" (canonical key)
    title           VARCHAR(500),                  -- e.g. "SAFETY ALERT"
    page_number     INTEGER,                       -- source page in the original doc
    page_uuid       VARCHAR(50),                   -- uuid from manifest for image ref
    has_visual      BOOLEAN DEFAULT FALSE,
    sort_order      INTEGER NOT NULL,
    -- Version tracking: was this paragraph changed in this version?
    change_type     VARCHAR(20) CHECK (change_type IN ('new','modified','unchanged','deleted')),
    prior_para_id   UUID REFERENCES paragraphs(id), -- links to same para in prev version
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (version_id, para_id)
);

CREATE INDEX idx_paragraphs_para_id ON paragraphs(para_id);
CREATE INDEX idx_paragraphs_version ON paragraphs(version_id);

-- Sub-elements within a paragraph
CREATE TYPE block_type AS ENUM (
    'body',          -- main paragraph text
    'note',          -- NOTE− blocks
    'phraseology',   -- PHRASEOLOGY− blocks
    'example',       -- EXAMPLE− blocks
    'reference',     -- REFERENCE− blocks
    'exception',     -- EXCEPTION. blocks
    'interpretation' -- INTERPRETATION− blocks
);

CREATE TABLE content_blocks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES order_versions(id) ON DELETE CASCADE,
    block_type      block_type NOT NULL,
    sequence        INTEGER NOT NULL,              -- order within the paragraph
    label           VARCHAR(100),                  -- e.g. "NOTE 1", "a.", "1."
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_blocks_paragraph ON content_blocks(paragraph_id);
CREATE INDEX idx_content_blocks_search ON content_blocks USING gin(content gin_trgm_ops);


-- ─────────────────────────────────────────────────────────────────────────────
-- TAGGING SYSTEM
-- Flexible many-to-many tags on paragraphs for curriculum mapping
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE tags (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    category    VARCHAR(50),      -- e.g. "facility_type", "topic", "difficulty", "equipment"
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-populate expected tag categories:
-- facility_type: TRACON, ARTCC, Tower, FSS, ATCT
-- topic: separation, radar, IFR, VFR, phraseology, weather, emergencies, ...
-- difficulty: basic, intermediate, advanced
-- content_type: procedural, definitional, phraseology, regulatory

CREATE TABLE paragraph_tags (
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    tag_id          UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    auto_tagged     BOOLEAN DEFAULT FALSE,   -- TRUE = system applied, FALSE = human reviewed
    tagged_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (paragraph_id, tag_id)
);

CREATE INDEX idx_paragraph_tags_tag ON paragraph_tags(tag_id);


-- ─────────────────────────────────────────────────────────────────────────────
-- CROSS-REFERENCES
-- When paragraph A references paragraph B, we store it here so the platform
-- can auto-link content and build relationship graphs
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE cross_references (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_para_id  UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    target_para_id  UUID REFERENCES paragraphs(id) ON DELETE SET NULL,
    target_para_str VARCHAR(30),   -- raw string like "2-1-6" before resolution
    reference_text  TEXT,          -- full reference line as it appears in doc
    resolved        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- USERS  (Students, Instructors, Admins)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TYPE user_role AS ENUM ('student', 'instructor', 'admin');

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    role            user_role NOT NULL DEFAULT 'student',
    facility_type   VARCHAR(50),    -- TRACON, ARTCC, Tower, etc.
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);


-- ─────────────────────────────────────────────────────────────────────────────
-- CURRICULUM  (Instructors build courses from ordered paragraph sets)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE courses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id      UUID NOT NULL REFERENCES order_versions(id),
    created_by      UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    is_published    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE course_modules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id       UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    sort_order      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Links specific paragraphs into a module in order
CREATE TABLE module_paragraphs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id       UUID NOT NULL REFERENCES course_modules(id) ON DELETE CASCADE,
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL,
    UNIQUE (module_id, paragraph_id)
);


-- ─────────────────────────────────────────────────────────────────────────────
-- PROGRESS TRACKING
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE user_paragraph_progress (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    read_at         TIMESTAMPTZ,
    confidence      SMALLINT CHECK (confidence BETWEEN 1 AND 5),
    review_count    INTEGER DEFAULT 0,
    last_reviewed   TIMESTAMPTZ,
    UNIQUE (user_id, paragraph_id)
);

CREATE INDEX idx_progress_user ON user_paragraph_progress(user_id);


-- ─────────────────────────────────────────────────────────────────────────────
-- FLASHCARDS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE flashcards (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    version_id      UUID NOT NULL REFERENCES order_versions(id),
    created_by      UUID REFERENCES users(id),   -- NULL = system-generated
    front           TEXT NOT NULL,               -- question / prompt
    back            TEXT NOT NULL,               -- answer
    card_type       VARCHAR(30) DEFAULT 'definition',  -- definition, phraseology, procedure
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE flashcard_reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flashcard_id    UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4),  -- 1=again 2=hard 3=good 4=easy
    reviewed_at     TIMESTAMPTZ DEFAULT NOW(),
    next_review     TIMESTAMPTZ    -- SRS scheduling
);

CREATE INDEX idx_flashcard_reviews_user_next ON flashcard_reviews(user_id, next_review);


-- ─────────────────────────────────────────────────────────────────────────────
-- QUIZ / TEST BANK
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TYPE question_type AS ENUM ('multiple_choice', 'true_false', 'fill_blank', 'ordering');

CREATE TABLE quiz_questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paragraph_id    UUID REFERENCES paragraphs(id) ON DELETE SET NULL,
    version_id      UUID NOT NULL REFERENCES order_versions(id),
    created_by      UUID REFERENCES users(id),
    question_text   TEXT NOT NULL,
    question_type   question_type NOT NULL DEFAULT 'multiple_choice',
    explanation     TEXT,          -- shown after answer
    difficulty      SMALLINT CHECK (difficulty BETWEEN 1 AND 3),  -- 1=easy 2=med 3=hard
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,   -- instructor-reviewed
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE question_choices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id     UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    choice_text     TEXT NOT NULL,
    is_correct      BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INTEGER NOT NULL
);

CREATE TABLE quizzes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id       UUID REFERENCES courses(id),
    created_by      UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    time_limit_mins INTEGER,
    passing_score   SMALLINT DEFAULT 80,
    is_published    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE quiz_question_sets (
    quiz_id         UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_id     UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL,
    PRIMARY KEY (quiz_id, question_id)
);

CREATE TABLE quiz_attempts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    score           NUMERIC(5,2),
    passed          BOOLEAN,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE TABLE quiz_attempt_answers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attempt_id      UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id     UUID NOT NULL REFERENCES quiz_questions(id),
    choice_id       UUID REFERENCES question_choices(id),
    free_text       TEXT,         -- for fill_blank questions
    is_correct      BOOLEAN,
    answered_at     TIMESTAMPTZ DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- SCENARIOS  (Scenario-based practice)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE scenarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id      UUID NOT NULL REFERENCES order_versions(id),
    created_by      UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL,       -- sets up the situation
    facility_type   VARCHAR(50),
    difficulty      SMALLINT CHECK (difficulty BETWEEN 1 AND 3),
    is_published    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Which paragraphs does this scenario test?
CREATE TABLE scenario_paragraphs (
    scenario_id     UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    paragraph_id    UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    PRIMARY KEY (scenario_id, paragraph_id)
);

CREATE TABLE scenario_steps (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id     UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL,
    prompt          TEXT NOT NULL,       -- what happens / what do you do?
    correct_action  TEXT NOT NULL,       -- the right answer
    reference_para  UUID REFERENCES paragraphs(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scenario_attempts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id     UUID NOT NULL REFERENCES scenarios(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    ai_feedback     TEXT,                -- stored automated feedback text
    score           NUMERIC(5,2),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);


-- ─────────────────────────────────────────────────────────────────────────────
-- VERSION CHANGE LOG
-- When a new 7110.65 edition/change is imported, this table records what moved
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE version_changes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_version_id UUID REFERENCES order_versions(id),
    to_version_id   UUID NOT NULL REFERENCES order_versions(id),
    para_id         VARCHAR(30) NOT NULL,
    change_type     VARCHAR(20) CHECK (change_type IN ('added','modified','deleted','renumbered')),
    summary         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- INGESTION LOG  (audit trail for pipeline runs)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE ingestion_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id      UUID NOT NULL REFERENCES order_versions(id),
    source_file     VARCHAR(500),
    status          VARCHAR(20) CHECK (status IN ('running','complete','failed')),
    chapters_parsed INTEGER DEFAULT 0,
    paragraphs_parsed INTEGER DEFAULT 0,
    errors          JSONB DEFAULT '[]',
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
