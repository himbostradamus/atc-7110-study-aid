"""
services/srs.py
===============
SM-2 Spaced Repetition Scheduling Engine

Pure Python — no database dependencies. All DB interaction happens in
the API layer; this module contains only the scheduling math.

SM-2 algorithm (Wozniak, 1987) with ATC-specific tuning:

  Rating scale:
    1 - Again  : Complete blank / wrong answer. Reset.
    2 - Hard   : Got it but struggled significantly.
    3 - Good   : Correct with modest effort.
    4 - Easy   : Immediate, confident recall.

  State machine:
    new  → learning (first review, any rating)
    learning → review (after graduating: rating ≥ 3 AND interval ≥ GRAD_INTERVAL)
    review → relearning (rating == 1 after graduating)
    relearning → review (rating ≥ 3 again)
    review → graduated (interval ≥ GRADUATE_DAYS after long streak)

  Key differences from vanilla SM-2:
    - Learning steps before a card graduates to "review" (like Anki)
    - Lapse handling: graduating cards that fail drop to relearning, not new
    - Hard penalty applies to ease factor even in learning phase
    - ATC-specific: phraseology cards get a slight ease bonus on Easy
      (muscle memory forms faster than factual recall)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS  (tunable without touching algorithm logic)
# ─────────────────────────────────────────────────────────────────────────────

# Learning steps in minutes before a card can graduate to "review"
LEARNING_STEPS_MINUTES: list[int] = [10, 1440]  # 10 min, then 1 day

# Interval in days at which a "learning" card becomes a "review" card
GRADUATION_INTERVAL_DAYS: int = 1

# Starting ease factor for all new cards
STARTING_EASE: float = 2.50

# Ease factor floor — never drops below this
MIN_EASE: float = 1.30

# Ease factor ceiling
MAX_EASE: float = 3.00

# Ease adjustments per rating
EASY_BONUS: float  = 0.15    # added to EF on Easy
HARD_PENALTY: float = 0.15   # subtracted from EF on Hard
AGAIN_PENALTY: float = 0.20  # subtracted from EF on Again (lapse)

# For "Again" on a graduated card: relearn interval (days)
LAPSE_STARTING_INTERVAL: int = 1

# Interval modifier — multiplied against calculated interval (global difficulty knob)
# 1.0 = standard SM-2, < 1.0 = more reviews, > 1.0 = fewer
INTERVAL_MODIFIER: float = 1.0

# Minimum interval after a "Hard" review (days, for review cards)
HARD_MIN_INTERVAL: int = 1

# Card type ease bonuses (applied on Easy only)
CARD_TYPE_EASY_BONUS: dict[str, float] = {
    "phraseology": 0.05,   # ATC phraseology benefits from muscle memory
    "definition":  0.00,
    "procedure":   0.00,
    "scenario":    0.00,
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CardState:
    """
    Current SRS state for one user × card pair.
    Mirrors the flashcard_states table columns exactly.
    """
    ease_factor:   float = STARTING_EASE
    interval_days: int   = 0
    repetitions:   int   = 0
    status:        str   = "new"          # new | learning | review | relearning | graduated
    lapse_count:   int   = 0
    total_reviews: int   = 0
    next_review:   Optional[datetime] = None
    last_reviewed: Optional[datetime] = None


@dataclass
class ReviewResult:
    """
    Output of schedule() — the new state after a review, plus diagnostics.
    """
    # Updated state fields (write these back to flashcard_states)
    ease_factor:    float
    interval_days:  int
    repetitions:    int
    status:         str
    lapse_count:    int
    total_reviews:  int
    next_review:    datetime

    # Diagnostics (useful for logging / analytics)
    rating:         int
    prev_interval:  int
    prev_ease:      float
    interval_change: str   # e.g. "1 → 6 days", "reset to 1"
    message:        str    # human-readable summary


# ─────────────────────────────────────────────────────────────────────────────
# CORE ALGORITHM
# ─────────────────────────────────────────────────────────────────────────────

def schedule(
    state: CardState,
    rating: int,
    card_type: str = "definition",
    reviewed_at: Optional[datetime] = None,
) -> ReviewResult:
    """
    Apply a review rating to a card state and compute the next review date.

    Args:
        state:       Current SRS state for this user × card.
        rating:      1=Again, 2=Hard, 3=Good, 4=Easy
        card_type:   Card category for type-specific bonuses (phraseology, etc.)
        reviewed_at: When the review happened (defaults to utcnow).

    Returns:
        ReviewResult with the full updated state and the new next_review date.
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"Rating must be 1-4, got {rating}")

    now = reviewed_at or datetime.now(timezone.utc)
    prev_interval = state.interval_days
    prev_ease = state.ease_factor

    # Work on copies
    ease      = state.ease_factor
    interval  = state.interval_days
    reps      = state.repetitions
    status    = state.status
    lapses    = state.lapse_count
    total     = state.total_reviews + 1

    # ── Route by current status ───────────────────────────────────────────────

    if status in ("new", "learning"):
        ease, interval, reps, status, lapses = _schedule_learning(
            ease, interval, reps, lapses, rating, card_type
        )

    elif status == "review":
        ease, interval, reps, status, lapses = _schedule_review(
            ease, interval, reps, lapses, rating, card_type
        )

    elif status == "relearning":
        ease, interval, reps, status, lapses = _schedule_relearning(
            ease, interval, reps, lapses, rating, card_type
        )

    elif status == "graduated":
        # Treat graduated same as review — just logged differently
        ease, interval, reps, status, lapses = _schedule_review(
            ease, interval, reps, lapses, rating, card_type
        )

    # ── Clamp ease ────────────────────────────────────────────────────────────
    ease = round(max(MIN_EASE, min(MAX_EASE, ease)), 2)

    # ── Apply interval modifier ───────────────────────────────────────────────
    if interval > 1:
        interval = max(1, round(interval * INTERVAL_MODIFIER))

    # ── Compute next review datetime ──────────────────────────────────────────
    next_review = now + timedelta(days=interval)

    interval_change = f"{prev_interval} → {interval} day{'s' if interval != 1 else ''}"
    message = _build_message(rating, status, interval)

    return ReviewResult(
        ease_factor    = ease,
        interval_days  = interval,
        repetitions    = reps,
        status         = status,
        lapse_count    = lapses,
        total_reviews  = total,
        next_review    = next_review,
        rating         = rating,
        prev_interval  = prev_interval,
        prev_ease      = prev_ease,
        interval_change = interval_change,
        message        = message,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STATUS-SPECIFIC SCHEDULERS
# ─────────────────────────────────────────────────────────────────────────────

def _schedule_learning(
    ease: float, interval: int, reps: int, lapses: int,
    rating: int, card_type: str
) -> tuple[float, int, int, str, int]:
    """
    Handle new and learning cards.

    Learning cards work through fixed steps before graduating:
      Step 0 (new/again): show in 10 minutes  → interval = 0 (same session)
      Step 1 (good):      show tomorrow        → interval = 1
      Graduate (good again with interval ≥ 1): move to "review"
    """
    if rating == 1:  # Again
        ease = max(MIN_EASE, ease - AGAIN_PENALTY)
        interval = 0   # re-show same session (scheduled by step index, not days)
        reps = 0
        status = "learning"

    elif rating == 2:  # Hard
        ease = max(MIN_EASE, ease - HARD_PENALTY)
        interval = max(HARD_MIN_INTERVAL, interval)
        # Stay in learning, don't advance step
        status = "learning"

    elif rating == 3:  # Good
        if interval == 0:
            interval = 1      # advance to next day step
            status = "learning"
        else:
            # Already at day-1 step — graduate to review
            interval = GRADUATION_INTERVAL_DAYS
            reps = 1
            status = "review"

    elif rating == 4:  # Easy
        type_bonus = CARD_TYPE_EASY_BONUS.get(card_type, 0.0)
        ease = min(MAX_EASE, ease + EASY_BONUS + type_bonus)
        # Skip remaining learning steps, graduate immediately
        interval = max(GRADUATION_INTERVAL_DAYS, 4)
        reps = 1
        status = "review"

    return ease, interval, reps, status, lapses


def _schedule_review(
    ease: float, interval: int, reps: int, lapses: int,
    rating: int, card_type: str
) -> tuple[float, int, int, str, int]:
    """
    Handle cards in active review rotation.

    SM-2 interval formula: I(n+1) = I(n) × EF
    """
    if rating == 1:  # Again — lapse
        ease = max(MIN_EASE, ease - AGAIN_PENALTY)
        interval = LAPSE_STARTING_INTERVAL
        reps = 0
        lapses += 1
        status = "relearning"

    elif rating == 2:  # Hard
        ease = max(MIN_EASE, ease - HARD_PENALTY)
        # Hard: grow interval but less aggressively (1.2 instead of EF)
        interval = max(HARD_MIN_INTERVAL, round(interval * 1.2))
        # reps unchanged — hard doesn't advance the streak
        status = "review"

    elif rating == 3:  # Good
        if reps == 0:
            interval = GRADUATION_INTERVAL_DAYS
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease)
        reps += 1
        # Check for graduation to long-term memory
        status = "graduated" if interval >= 21 and reps >= 5 else "review"

    elif rating == 4:  # Easy
        type_bonus = CARD_TYPE_EASY_BONUS.get(card_type, 0.0)
        ease = min(MAX_EASE, ease + EASY_BONUS + type_bonus)
        if reps == 0:
            interval = max(4, round(interval * ease))
        else:
            interval = round(interval * ease * 1.3)   # Easy bonus multiplier
        reps += 1
        status = "graduated" if interval >= 21 and reps >= 5 else "review"

    return ease, interval, reps, status, lapses


def _schedule_relearning(
    ease: float, interval: int, reps: int, lapses: int,
    rating: int, card_type: str
) -> tuple[float, int, int, str, int]:
    """
    Handle lapsed cards working their way back into review rotation.
    Simpler than full learning — one step back to review.
    """
    if rating == 1:  # Again
        ease = max(MIN_EASE, ease - AGAIN_PENALTY)
        interval = LAPSE_STARTING_INTERVAL
        reps = 0
        lapses += 1
        status = "relearning"

    elif rating == 2:  # Hard
        ease = max(MIN_EASE, ease - HARD_PENALTY)
        interval = max(1, interval)
        status = "relearning"

    elif rating == 3:  # Good — back to review
        reps = 1
        interval = max(GRADUATION_INTERVAL_DAYS, round(interval * 1.5))
        status = "review"

    elif rating == 4:  # Easy — back to review with bonus
        type_bonus = CARD_TYPE_EASY_BONUS.get(card_type, 0.0)
        ease = min(MAX_EASE, ease + EASY_BONUS + type_bonus)
        reps = 1
        interval = max(4, round(interval * ease))
        status = "review"

    return ease, interval, reps, status, lapses


# ─────────────────────────────────────────────────────────────────────────────
# DECK UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def get_due_counts(states: list[CardState], now: Optional[datetime] = None) -> dict:
    """
    Given a list of card states, return counts broken down by category.
    Useful for the dashboard "X cards due today" display.
    """
    now = now or datetime.now(timezone.utc)

    new_count      = sum(1 for s in states if s.status == "new")
    learning_count = sum(1 for s in states if s.status in ("learning", "relearning"))
    due_count      = sum(
        1 for s in states
        if s.status in ("review", "graduated")
        and s.next_review is not None
        and s.next_review <= now
    )
    total_due = new_count + learning_count + due_count

    return {
        "new":       new_count,
        "learning":  learning_count,
        "due":       due_count,
        "total_due": total_due,
    }


def prioritize_due_cards(states: list[CardState], now: Optional[datetime] = None) -> list[CardState]:
    """
    Sort a list of card states into optimal study order:
      1. Overdue review cards (most overdue first — highest urgency)
      2. Learning / relearning cards due now
      3. New cards
    """
    now = now or datetime.now(timezone.utc)

    def sort_key(s: CardState) -> tuple:
        if s.status == "new":
            return (2, 0)
        if s.status in ("learning", "relearning"):
            nr = s.next_review or now
            return (1, (now - nr).total_seconds())
        # review / graduated
        nr = s.next_review or now
        overdue_seconds = (now - nr).total_seconds()
        return (0, -overdue_seconds)  # most overdue first

    return sorted(states, key=sort_key)


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def forecast_reviews(states: list[CardState], days: int = 14) -> dict[str, int]:
    """
    Estimate how many reviews will come due on each of the next `days` days.
    Used to render the upcoming-reviews histogram on the dashboard.
    """
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    forecast: dict[str, int] = {}

    for i in range(days):
        day = now + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        forecast[key] = 0

    for state in states:
        if state.next_review is None:
            continue
        nr = state.next_review.replace(tzinfo=timezone.utc) if state.next_review.tzinfo is None else state.next_review
        for i in range(days):
            day_start = now + timedelta(days=i)
            day_end   = day_start + timedelta(days=1)
            if day_start <= nr < day_end:
                key = day_start.strftime("%Y-%m-%d")
                forecast[key] = forecast.get(key, 0) + 1
                break

    return forecast


def retention_rate(reviews: list[dict], window_days: int = 30) -> float:
    """
    Calculate retention rate over a time window.
    reviews: list of dicts with {"rating": int, "reviewed_at": datetime}
    Returns: 0.0–1.0
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    recent = [r for r in reviews if r["reviewed_at"] >= cutoff]
    if not recent:
        return 0.0
    correct = sum(1 for r in recent if r["rating"] >= 3)
    return round(correct / len(recent), 3)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_message(rating: int, new_status: str, interval: int) -> str:
    labels = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
    rating_label = labels.get(rating, "?")

    if interval == 0:
        when = "again soon (same session)"
    elif interval == 1:
        when = "tomorrow"
    else:
        when = f"in {interval} days"

    return f"{rating_label} — next review {when} [{new_status}]"
