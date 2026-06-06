"""
services/quiz_engine.py
========================
Quiz Engine — pure business logic, no DB dependencies.

Responsibilities:
  1. QuestionSelector   — picks questions from a pool given a config + history
  2. AdaptiveController — tracks running difficulty and adjusts question pool
  3. Scorer             — grades an attempt, computes per-question and overall scores
  4. WeakAreaAnalyzer   — identifies paragraphs where a student struggles
  5. ResultBuilder      — assembles the rich result payload shown after completion

Modes:
  standard    — fixed pool, shuffled, shown in order
  adaptive    — starts at configured difficulty, adjusts question-by-question
  weak_areas  — prioritises questions from the student's flagged weak paragraphs
  timed_exam  — like standard but enforces a time budget per question

All functions take plain dicts / dataclasses; the API layer handles DB I/O.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QuestionRecord:
    """Lightweight representation of a question used inside the engine."""
    id:           str
    paragraph_id: Optional[str]
    para_id:      Optional[str]          # human-readable e.g. "2-1-6"
    para_title:   Optional[str]
    question_text: str
    question_type: str                   # multiple_choice | true_false | fill_blank | ordering
    difficulty:   int                    # 1=easy 2=medium 3=hard
    choices:      list[dict]             # [{id, text, is_correct, sort_order}]
    explanation:  Optional[str]
    is_verified:  bool
    correct_rate: float = 0.0            # from question_stats (0–1); 0 = no data


@dataclass
class QuizConfig:
    mode:                     str   = "standard"
    question_count:           int   = 20
    question_types:           list  = field(default_factory=lambda: ["multiple_choice", "true_false"])
    shuffle_questions:        bool  = True
    shuffle_choices:          bool  = True
    show_feedback:            str   = "after_each"   # after_each | end_only | never
    passing_score:            int   = 70
    time_limit_mins:          Optional[int] = None
    verified_only:            bool  = False
    # Adaptive settings
    adaptive_start_difficulty: int  = 2
    adaptive_window:           int  = 3
    adaptive_correct_threshold: float = 0.70
    adaptive_wrong_threshold:   float = 0.40


@dataclass
class AnswerSubmission:
    question_id: str
    choice_id:   Optional[str]    # for multiple_choice / true_false
    free_text:   Optional[str]    # for fill_blank
    response_ms: Optional[int]


@dataclass
class GradedAnswer:
    question_id:    str
    choice_id:      Optional[str]
    free_text:      Optional[str]
    is_correct:     bool
    points_earned:  float
    points_possible: float
    correct_choice_id:   Optional[str]
    correct_choice_text: Optional[str]
    explanation:    Optional[str]
    response_ms:    Optional[int]
    difficulty:     int


@dataclass
class AttemptResult:
    attempt_id:        str
    quiz_id:           str
    user_id:           str
    mode:              str
    score_pct:         float         # 0–100
    points_earned:     float
    points_possible:   float
    passed:            bool
    passing_score:     int
    total_questions:   int
    correct_count:     int
    incorrect_count:   int
    time_used_secs:    Optional[int]
    graded_answers:    list[GradedAnswer]
    weak_paragraphs:   list[dict]    # paragraphs with ≥ 1 wrong answer
    strong_paragraphs: list[dict]    # paragraphs with all correct
    difficulty_breakdown: dict       # {1: {correct, total}, 2: ..., 3: ...}
    completed_at:      datetime


# ─────────────────────────────────────────────────────────────────────────────
# 1. QUESTION SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

class QuestionSelector:
    """
    Selects a question pool from a candidate list according to config rules.

    Key goals:
      - Respect difficulty distribution targets
      - Avoid questions the user answered correctly recently (seen_ids)
      - Ensure paragraph coverage — don't over-sample any single paragraph
      - Fall back gracefully when the pool is too small
    """

    # Default difficulty distribution for standard / adaptive start
    DIFFICULTY_DIST = {1: 0.25, 2: 0.50, 3: 0.25}    # easy / medium / hard

    def select(
        self,
        candidates:    list[QuestionRecord],
        config:        QuizConfig,
        seen_ids:      Optional[set[str]] = None,
        weak_para_ids: Optional[set[str]] = None,
        target_difficulty: Optional[int]  = None,
    ) -> list[QuestionRecord]:
        """
        Build a quiz question list from candidates.

        Args:
            candidates:        full pool of eligible questions
            config:            quiz configuration
            seen_ids:          question IDs the user answered correctly recently
                               (excluded unless pool is too small to fill)
            weak_para_ids:     paragraph IDs flagged as weak (boosted in weak_areas mode)
            target_difficulty: if set, override difficulty distribution (adaptive mode)

        Returns:
            Ordered list of QuestionRecord ready for delivery.
        """
        seen_ids = seen_ids or set()
        pool = [q for q in candidates if q.is_verified or not config.verified_only]

        if config.question_types:
            pool = [q for q in pool if q.question_type in config.question_types]

        # ── Mode-specific pre-filtering ───────────────────────────────────────
        if config.mode == "weak_areas" and weak_para_ids:
            weak_pool   = [q for q in pool if q.paragraph_id in weak_para_ids]
            strong_pool = [q for q in pool if q.paragraph_id not in weak_para_ids]
            # 70 % from weak areas, 30 % from general pool
            weak_n   = min(len(weak_pool),   round(config.question_count * 0.70))
            strong_n = min(len(strong_pool),  config.question_count - weak_n)
            selected = (
                self._select_by_difficulty(weak_pool,   weak_n,   target_difficulty, seen_ids) +
                self._select_by_difficulty(strong_pool, strong_n, target_difficulty, seen_ids)
            )

        elif target_difficulty is not None:
            # Adaptive: pick exclusively from the target difficulty tier
            tier_pool = [q for q in pool if q.difficulty == target_difficulty]
            if len(tier_pool) < config.question_count:
                # spill into adjacent difficulties
                adjacent = abs(target_difficulty - 2) + 1
                spill = [q for q in pool if abs(q.difficulty - target_difficulty) <= 1]
                tier_pool = list(set(tier_pool + spill))
            selected = self._select_by_difficulty(tier_pool, config.question_count, None, seen_ids)

        else:
            selected = self._select_by_difficulty(pool, config.question_count, None, seen_ids)

        # ── Shuffle ───────────────────────────────────────────────────────────
        if config.shuffle_questions:
            random.shuffle(selected)

        if config.shuffle_choices:
            for q in selected:
                q.choices = self._shuffle_choices(q.choices)

        return selected[:config.question_count]

    def _select_by_difficulty(
        self,
        pool:       list[QuestionRecord],
        n:          int,
        target:     Optional[int],
        seen_ids:   set[str],
    ) -> list[QuestionRecord]:
        """Select n questions from pool with difficulty weighting."""
        if not pool:
            return []

        unseen = [q for q in pool if q.id not in seen_ids]
        fallback = pool  # use seen if we run out of unseen

        if target is not None:
            # Single difficulty tier requested
            tier = [q for q in unseen if q.difficulty == target] or \
                   [q for q in fallback if q.difficulty == target]
            return self._unique_para_sample(tier or unseen or fallback, n)

        # Distribute across difficulties per DIFFICULTY_DIST
        by_diff: dict[int, list[QuestionRecord]] = {1: [], 2: [], 3: []}
        for q in unseen:
            by_diff.setdefault(q.difficulty, []).append(q)

        selected: list[QuestionRecord] = []
        for diff, ratio in self.DIFFICULTY_DIST.items():
            want = max(1, round(n * ratio))
            got  = self._unique_para_sample(by_diff.get(diff, []), want)
            selected.extend(got)

        # If we're short, fill from any difficulty
        if len(selected) < n:
            remaining = [q for q in (unseen or fallback) if q.id not in {s.id for s in selected}]
            selected += self._unique_para_sample(remaining, n - len(selected))

        return selected[:n]

    def _unique_para_sample(
        self, pool: list[QuestionRecord], n: int, max_per_para: int = 2
    ) -> list[QuestionRecord]:
        """
        Sample n questions while capping the number drawn from any one paragraph.
        Prevents a quiz being dominated by a single wordy paragraph.
        """
        para_counts: dict[str, int] = {}
        selected: list[QuestionRecord] = []
        shuffled = pool.copy()
        random.shuffle(shuffled)

        for q in shuffled:
            if len(selected) >= n:
                break
            pid = q.paragraph_id or "__none__"
            if para_counts.get(pid, 0) < max_per_para:
                selected.append(q)
                para_counts[pid] = para_counts.get(pid, 0) + 1

        # If still short (e.g. small pool), relax the cap
        if len(selected) < n:
            for q in shuffled:
                if q not in selected:
                    selected.append(q)
                if len(selected) >= n:
                    break

        return selected

    @staticmethod
    def _shuffle_choices(choices: list[dict]) -> list[dict]:
        """Shuffle answer choices while keeping sort_order for DB storage."""
        shuffled = choices.copy()
        random.shuffle(shuffled)
        for i, c in enumerate(shuffled):
            c = dict(c)
            c["display_order"] = i   # client uses this, not sort_order
            shuffled[i] = c
        return shuffled


# ─────────────────────────────────────────────────────────────────────────────
# 2. ADAPTIVE CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────

class AdaptiveController:
    """
    Tracks in-flight quiz performance and emits the next difficulty level.

    The algorithm:
      - Maintains a rolling window of the last N answers (correct/incorrect)
      - If window correct-rate > upper threshold  → raise difficulty
      - If window correct-rate < lower threshold  → lower difficulty
      - Otherwise hold steady
      - Difficulty is clamped to [1, 3]
    """

    def __init__(self, config: QuizConfig):
        self.config     = config
        self.difficulty = config.adaptive_start_difficulty
        self._window:   list[bool] = []   # True=correct, False=wrong

    def record(self, is_correct: bool) -> int:
        """
        Record the result of one answer and return the next difficulty.
        """
        self._window.append(is_correct)
        if len(self._window) > self.config.adaptive_window:
            self._window.pop(0)

        # Only adjust after a full window
        if len(self._window) < self.config.adaptive_window:
            return self.difficulty

        rate = sum(self._window) / len(self._window)

        if rate >= self.config.adaptive_correct_threshold:
            self.difficulty = min(3, self.difficulty + 1)
            self._window.clear()   # reset window after adjustment
        elif rate <= self.config.adaptive_wrong_threshold:
            self.difficulty = max(1, self.difficulty - 1)
            self._window.clear()

        return self.difficulty

    @property
    def current_difficulty(self) -> int:
        return self.difficulty

    @property
    def window_rate(self) -> Optional[float]:
        if not self._window:
            return None
        return sum(self._window) / len(self._window)


# ─────────────────────────────────────────────────────────────────────────────
# 3. SCORER
# ─────────────────────────────────────────────────────────────────────────────

class Scorer:
    """
    Grades a completed attempt.

    Scoring rules:
      - Multiple choice / true-false: 1 point correct, 0 wrong
      - Fill-blank: case-insensitive match against accepted answers;
        partial credit (0.5) for close matches using edit distance
      - Ordering: Kendall tau distance for partial credit
      - Difficulty bonus: hard questions worth 1.5×, easy 0.75× (configurable)
    """

    DIFFICULTY_WEIGHT = {1: 0.75, 2: 1.00, 3: 1.50}

    def grade_attempt(
        self,
        questions:   list[QuestionRecord],
        submissions: list[AnswerSubmission],
        config:      QuizConfig,
        attempt_id:  str,
        quiz_id:     str,
        user_id:     str,
        started_at:  datetime,
    ) -> AttemptResult:
        """
        Grade all submissions and return a complete AttemptResult.
        """
        sub_map = {s.question_id: s for s in submissions}
        graded: list[GradedAnswer] = []

        total_points = 0.0
        earned_points = 0.0
        correct_count = 0

        diff_breakdown: dict[int, dict] = {
            1: {"correct": 0, "total": 0},
            2: {"correct": 0, "total": 0},
            3: {"correct": 0, "total": 0},
        }

        para_results: dict[str, dict] = {}   # para_id → {correct, total, title}

        for q in questions:
            sub = sub_map.get(q.id)
            weight = self.DIFFICULTY_WEIGHT.get(q.difficulty, 1.0)
            possible = 1.0 * weight

            is_correct, earned, correct_cid, correct_ctext = self._grade_question(q, sub)

            graded.append(GradedAnswer(
                question_id          = q.id,
                choice_id            = sub.choice_id if sub else None,
                free_text            = sub.free_text if sub else None,
                is_correct           = is_correct,
                points_earned        = earned * weight,
                points_possible      = possible,
                correct_choice_id    = correct_cid,
                correct_choice_text  = correct_ctext,
                explanation          = q.explanation,
                response_ms          = sub.response_ms if sub else None,
                difficulty           = q.difficulty,
            ))

            total_points  += possible
            earned_points += earned * weight
            if is_correct:
                correct_count += 1

            d = q.difficulty
            diff_breakdown[d]["total"] += 1
            if is_correct:
                diff_breakdown[d]["correct"] += 1

            # Track per-paragraph
            pid = q.para_id or q.paragraph_id or "unknown"
            if pid not in para_results:
                para_results[pid] = {"para_id": pid, "title": q.para_title, "correct": 0, "total": 0}
            para_results[pid]["total"]  += 1
            if is_correct:
                para_results[pid]["correct"] += 1

        score_pct = round((earned_points / total_points * 100) if total_points else 0, 1)
        passed    = score_pct >= config.passing_score
        now       = datetime.now(timezone.utc)
        time_used = int((now - started_at).total_seconds())

        weak_paras   = [p for p in para_results.values() if p["correct"] < p["total"]]
        strong_paras = [p for p in para_results.values() if p["correct"] == p["total"]]

        return AttemptResult(
            attempt_id            = attempt_id,
            quiz_id               = quiz_id,
            user_id               = user_id,
            mode                  = config.mode,
            score_pct             = score_pct,
            points_earned         = round(earned_points, 2),
            points_possible       = round(total_points, 2),
            passed                = passed,
            passing_score         = config.passing_score,
            total_questions       = len(questions),
            correct_count         = correct_count,
            incorrect_count       = len(questions) - correct_count,
            time_used_secs        = time_used,
            graded_answers        = graded,
            weak_paragraphs       = weak_paras,
            strong_paragraphs     = strong_paras,
            difficulty_breakdown  = diff_breakdown,
            completed_at          = now,
        )

    def _grade_question(
        self,
        q:   QuestionRecord,
        sub: Optional[AnswerSubmission],
    ) -> tuple[bool, float, Optional[str], Optional[str]]:
        """
        Returns (is_correct, earned_fraction, correct_choice_id, correct_choice_text)
        earned_fraction is 0.0–1.0 before difficulty weighting.
        """
        correct_choices = [c for c in q.choices if c.get("is_correct")]
        correct_cid  = correct_choices[0]["id"]   if correct_choices else None
        correct_text = correct_choices[0]["text"]  if correct_choices else None

        if not sub:
            return False, 0.0, correct_cid, correct_text

        if q.question_type in ("multiple_choice", "true_false"):
            is_correct = (sub.choice_id == correct_cid)
            return is_correct, 1.0 if is_correct else 0.0, correct_cid, correct_text

        if q.question_type == "fill_blank":
            is_correct, score = self._grade_fill_blank(sub.free_text, correct_choices)
            return is_correct, score, correct_cid, correct_text

        if q.question_type == "ordering":
            score = self._grade_ordering(sub, q.choices)
            return score >= 1.0, score, correct_cid, correct_text

        return False, 0.0, correct_cid, correct_text

    @staticmethod
    def _grade_fill_blank(
        answer: Optional[str],
        correct_choices: list[dict]
    ) -> tuple[bool, float]:
        """Case-insensitive exact match; partial credit for near-misses."""
        if not answer:
            return False, 0.0

        normalised = answer.strip().lower()
        accepted = [c["text"].strip().lower() for c in correct_choices]

        if normalised in accepted:
            return True, 1.0

        # Partial credit: Levenshtein distance ≤ 2 (typo tolerance)
        for acc in accepted:
            if _levenshtein(normalised, acc) <= 2:
                return False, 0.5    # partial credit — close but not exact

        return False, 0.0

    @staticmethod
    def _grade_ordering(sub: AnswerSubmission, choices: list[dict]) -> float:
        """
        Kendall tau partial credit for ordering questions.
        Score = 1 - (inversions / max_inversions), clamped to [0, 1].
        """
        if not sub.free_text:
            return 0.0

        try:
            submitted_order = [c.strip() for c in sub.free_text.split(",")]
            correct_order   = [
                c["id"] for c in sorted(choices, key=lambda x: x["sort_order"])
                if c.get("is_correct")
            ]
            if len(submitted_order) != len(correct_order):
                return 0.0

            inversions     = 0
            n              = len(correct_order)
            correct_pos    = {v: i for i, v in enumerate(correct_order)}
            sub_pos        = [correct_pos.get(v, -1) for v in submitted_order]

            for i in range(n):
                for j in range(i + 1, n):
                    if sub_pos[i] > sub_pos[j]:
                        inversions += 1

            max_inv = n * (n - 1) // 2
            return round(1 - (inversions / max_inv), 2) if max_inv else 1.0
        except Exception:
            return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. WEAK AREA ANALYZER
# ─────────────────────────────────────────────────────────────────────────────

class WeakAreaAnalyzer:
    """
    Identifies which paragraphs a student struggles with by aggregating
    quiz attempt history and optionally cross-referencing SRS lapse data.

    A paragraph is "weak" if:
      - error_rate >= WEAK_THRESHOLD across ≥ MIN_ATTEMPTS attempts, OR
      - it appears in both quiz wrong answers AND SRS lapse_count >= 2

    Results feed the weak_areas quiz mode and the student dashboard.
    """

    WEAK_THRESHOLD  = 0.40   # ≥ 40% wrong rate to flag
    MIN_ATTEMPTS    = 3      # need at least 3 attempts to flag
    STRONG_THRESHOLD = 0.85  # ≥ 85% correct rate to mark as strong

    def analyze(
        self,
        para_results: list[dict],      # [{para_id, title, correct, total}, ...]
        srs_states:   Optional[list[dict]] = None,  # [{para_id, lapse_count}, ...]
    ) -> dict[str, list[dict]]:
        """
        Returns {"weak": [...], "strong": [...], "neutral": [...]}
        where each item is {para_id, title, error_rate, attempts, source}.
        """
        srs_map: dict[str, int] = {}
        if srs_states:
            srs_map = {s["para_id"]: s.get("lapse_count", 0) for s in srs_states}

        weak:    list[dict] = []
        strong:  list[dict] = []
        neutral: list[dict] = []

        for p in para_results:
            total = p.get("total", 0)
            if total == 0:
                continue

            correct    = p.get("correct", 0)
            error_rate = round(1 - (correct / total), 3)
            lapse_count = srs_map.get(p.get("para_id", ""), 0)

            entry = {
                "para_id":    p.get("para_id"),
                "title":      p.get("title"),
                "error_rate": error_rate,
                "attempts":   total,
                "lapse_count": lapse_count,
                "source":     [],
            }

            is_weak   = False
            is_strong = False

            if total >= self.MIN_ATTEMPTS and error_rate >= self.WEAK_THRESHOLD:
                is_weak = True
                entry["source"].append("quiz")

            if lapse_count >= 2:
                is_weak = True
                entry["source"].append("srs")

            if error_rate <= (1 - self.STRONG_THRESHOLD) and total >= self.MIN_ATTEMPTS:
                is_strong = True

            if is_weak:
                weak.append(entry)
            elif is_strong:
                strong.append(entry)
            else:
                neutral.append(entry)

        # Sort weak by error_rate descending (worst first)
        weak.sort(key=lambda x: x["error_rate"], reverse=True)

        return {"weak": weak, "strong": strong, "neutral": neutral}

    def should_surface_for_review(self, entry: dict) -> bool:
        """Quick check: should this weak area be actively shown to the student?"""
        return (
            entry["error_rate"] >= self.WEAK_THRESHOLD
            and entry["attempts"] >= self.MIN_ATTEMPTS
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_result_payload(result: AttemptResult, questions: list[QuestionRecord]) -> dict:
    """
    Build the full result dict sent to the client after quiz completion.
    Merges AttemptResult with the original question text for display.
    """
    q_map = {q.id: q for q in questions}

    answers_out = []
    for ga in result.graded_answers:
        q = q_map.get(ga.question_id)
        answers_out.append({
            "question_id":        ga.question_id,
            "question_text":      q.question_text if q else "",
            "para_id":            q.para_id if q else None,
            "para_title":         q.para_title if q else None,
            "question_type":      q.question_type if q else "",
            "difficulty":         ga.difficulty,
            "submitted_choice_id": ga.choice_id,
            "submitted_text":     ga.free_text,
            "is_correct":         ga.is_correct,
            "points_earned":      ga.points_earned,
            "points_possible":    ga.points_possible,
            "correct_choice_id":  ga.correct_choice_id,
            "correct_choice_text": ga.correct_choice_text,
            "explanation":        ga.explanation,
            "response_ms":        ga.response_ms,
        })

    return {
        "attempt_id":          result.attempt_id,
        "score_pct":           result.score_pct,
        "passed":              result.passed,
        "passing_score":       result.passing_score,
        "points_earned":       result.points_earned,
        "points_possible":     result.points_possible,
        "correct_count":       result.correct_count,
        "incorrect_count":     result.incorrect_count,
        "total_questions":     result.total_questions,
        "time_used_secs":      result.time_used_secs,
        "mode":                result.mode,
        "completed_at":        result.completed_at.isoformat(),
        "answers":             answers_out,
        "weak_paragraphs":     result.weak_paragraphs,
        "strong_paragraphs":   result.strong_paragraphs,
        "difficulty_breakdown": {
            str(k): v for k, v in result.difficulty_breakdown.items()
        },
        "performance_summary": _performance_summary(result),
    }


def _performance_summary(result: AttemptResult) -> str:
    """Generate a short plain-English performance summary."""
    score = result.score_pct
    weak  = len(result.weak_paragraphs)

    if score >= 90:
        grade = "Excellent"
    elif score >= 80:
        grade = "Good"
    elif score >= 70:
        grade = "Satisfactory"
    elif score >= 60:
        grade = "Needs improvement"
    else:
        grade = "Study required"

    parts = [f"{grade} — {score:.1f}% ({result.correct_count}/{result.total_questions} correct)."]

    if result.passed:
        parts.append("PASSED.")
    else:
        parts.append(f"Did not meet the {result.passing_score}% passing threshold.")

    if weak:
        para_list = ", ".join(p["para_id"] for p in result.weak_paragraphs[:3])
        if len(result.weak_paragraphs) > 3:
            para_list += f" +{len(result.weak_paragraphs) - 3} more"
        parts.append(f"Review recommended: {para_list}.")

    if result.time_used_secs:
        avg_secs = result.time_used_secs // max(result.total_questions, 1)
        parts.append(f"Average {avg_secs}s per question.")

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    """Standard Levenshtein edit distance for fill-blank partial credit."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j]     + 1,
                prev[j]     + (0 if ca == cb else 1)
            ))
        prev = curr
    return prev[-1]
