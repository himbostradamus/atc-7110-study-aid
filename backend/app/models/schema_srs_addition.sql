-- =============================================================================
-- SRS ADDITIONS  — append to schema.sql
-- =============================================================================
-- Replaces the simple flashcard_reviews table with a proper per-user
-- SRS state store implementing SM-2 scheduling.
--
-- Design: FlashcardState is the single source of truth for where a user
-- stands on a given card. FlashcardReview is the immutable audit log of
-- every individual review event. The scheduler reads State; analytics
-- read Reviews.
-- =============================================================================

-- Drop the basic reviews table from the original schema if present
-- (safe to run on fresh DB — the original schema didn't create it yet)
DROP TABLE IF EXISTS flashcard_reviews;

-- ── Per-user SRS state (one row per user × card) ─────────────────────────────
CREATE TABLE flashcard_states (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flashcard_id    UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,

    -- SM-2 core fields
    ease_factor     NUMERIC(4,2) NOT NULL DEFAULT 2.50,  -- min 1.30
    interval_days   INTEGER NOT NULL DEFAULT 0,          -- 0 = new, 1 = learning
    repetitions     INTEGER NOT NULL DEFAULT 0,          -- consecutive correct reviews
    next_review     TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- when this card is due
    last_reviewed   TIMESTAMPTZ,

    -- Extended state
    status          VARCHAR(20) NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'learning', 'review', 'relearning', 'graduated')),
    lapse_count     INTEGER NOT NULL DEFAULT 0,          -- how many times "Again" after graduating
    total_reviews   INTEGER NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (user_id, flashcard_id)
);

CREATE INDEX idx_flashcard_states_due
    ON flashcard_states (user_id, next_review)
    WHERE status != 'graduated';

CREATE INDEX idx_flashcard_states_user
    ON flashcard_states (user_id);

-- ── Immutable review log ──────────────────────────────────────────────────────
CREATE TABLE flashcard_reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state_id        UUID NOT NULL REFERENCES flashcard_states(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flashcard_id    UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,

    -- What the user rated
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4),
    -- 1 = Again   (complete blackout / wrong)
    -- 2 = Hard    (significant difficulty)
    -- 3 = Good    (correct with some effort)
    -- 4 = Easy    (perfect, immediate recall)

    -- State snapshot BEFORE this review (for analytics / undo)
    pre_ease        NUMERIC(4,2),
    pre_interval    INTEGER,
    pre_reps        INTEGER,

    -- State snapshot AFTER this review (computed by SRS engine)
    post_ease       NUMERIC(4,2),
    post_interval   INTEGER,
    post_next_review TIMESTAMPTZ,

    -- Timing
    response_ms     INTEGER,  -- how long the user took to answer (ms)
    reviewed_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_flashcard_reviews_user  ON flashcard_reviews(user_id, reviewed_at DESC);
CREATE INDEX idx_flashcard_reviews_card  ON flashcard_reviews(flashcard_id);

-- ── Deck / collection grouping (optional, for structured study) ───────────────
CREATE TABLE decks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL = system deck
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    is_system   BOOLEAN DEFAULT FALSE,  -- TRUE = auto-generated from a chapter/section/tag
    filter_json JSONB,   -- e.g. {"chapter": 2} or {"tags": ["IFR", "TRACON"]}
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE deck_cards (
    deck_id      UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    added_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (deck_id, flashcard_id)
);

-- ── Add card_type constraint and generation_source to flashcards ──────────────
ALTER TABLE flashcards
    ADD COLUMN IF NOT EXISTS generation_source VARCHAR(20) DEFAULT 'manual'
        CHECK (generation_source IN ('manual', 'ai_auto', 'ai_assisted', 'imported', 'local_auto', 'curated')),
    ADD COLUMN IF NOT EXISTS source_block_type VARCHAR(30);
    -- tracks which content block type was used to generate the card
    -- (body, phraseology, note, example — drives card variety)
