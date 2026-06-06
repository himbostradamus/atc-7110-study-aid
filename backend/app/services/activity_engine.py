"""
services/activity_engine.py
============================
Three responsibilities, zero DB dependencies:

  SessionBuilder    — picks and orders activities for a lesson session
  ActivityScorer    — grades a submitted answer for each supported activity type
  CrownCalculator   — determines a paragraph's crown level from mastery state
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

ALL_TYPES = [
    "phraseology_builder",
    "spot_the_error",
    "sequence_steps",
    "match_pairs",
    "readback_check",
    "situation_action",
    "directive_check",
    "conditional_rule_check",
    "term_definition_check",
    "document_control_check",
    "requirement_check",
    "scope_check",
    "capability_check",
    "reference_check",
    "minima_rule_check",
    "list_membership",
    "table_lookup",
    "visual_interpretation",
    "example_check",
    "knowledge_check",
]

CHOICE_ACTIVITY_TYPES = {
    "readback_check",
    "situation_action",
    "directive_check",
    "conditional_rule_check",
    "term_definition_check",
    "document_control_check",
    "requirement_check",
    "scope_check",
    "capability_check",
    "reference_check",
    "minima_rule_check",
    "list_membership",
    "table_lookup",
    "visual_interpretation",
    "example_check",
    "knowledge_check",
}

# Crown thresholds — (min_activities, min_types, min_avg_score)
CROWN_THRESHOLDS = {
    1: (1,  1, 0.50),   # Introduced
    2: (3,  2, 0.70),   # Familiar
    3: (6,  4, 0.85),   # Proficient
    4: (10, 6, 0.90),   # Gold — 6 distinct types required
}

# Target activities per session
SESSION_TARGET = 8
SESSION_MIN    = 5
SESSION_MAX    = 12

# Never show the same type twice in a row
SAME_TYPE_BACK_TO_BACK = False


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActivityRecord:
    id:            str
    paragraph_id:  str
    para_id:       str       # human-readable "2-1-6"
    para_title:    str
    activity_type: str
    content_json:  dict
    difficulty:    int


@dataclass
class MasteryState:
    """Current mastery state for one user × paragraph."""
    paragraph_id:    str
    para_id:         str
    crown_level:     int                       = 0
    type_counts:     dict[str, int]            = field(default_factory=dict)
    type_avg_scores: dict[str, float]          = field(default_factory=dict)
    total_activities: int                      = 0


@dataclass
class ScoredActivity:
    session_activity_id: str
    activity_id:         str
    activity_type:       str
    paragraph_id:        str
    is_correct:          bool
    score:               float              # 0.0–1.0
    response_json:       dict
    result_json:         dict               # feedback, correct answer, explanation
    response_ms:         Optional[int]


@dataclass
class CrownChange:
    paragraph_id: str
    para_id:      str
    old_level:    int
    new_level:    int


# ─────────────────────────────────────────────────────────────────────────────
# 1. SESSION BUILDER
# ─────────────────────────────────────────────────────────────────────────────

class SessionBuilder:
    """
    Builds a lesson session from a pool of available activities.

    Selection strategy:
      1. Collect all available activities for the target paragraphs.
      2. For each paragraph, weight activity types by how under-practiced
         they are (least-practiced type gets highest weight).
      3. Sample activities, enforcing no same-type back-to-back.
      4. Aim for SESSION_TARGET activities; clamp to [SESSION_MIN, SESSION_MAX].
      5. Prefer unseen activities over repeats.
    """

    def build(
        self,
        available:          list[ActivityRecord],
        mastery_states:     dict[str, MasteryState],   # para_id → MasteryState
        target_count:       int = SESSION_TARGET,
        seen_activity_ids:  Optional[set[str]] = None,
    ) -> list[ActivityRecord]:
        """
        Returns an ordered list of ActivityRecord for the session.
        """
        seen = seen_activity_ids or set()
        target_count = max(SESSION_MIN, min(SESSION_MAX, target_count))

        # Separate unseen and seen activities
        unseen = [a for a in available if a.id not in seen]
        repeat = [a for a in available if a.id in seen]
        pool   = unseen + repeat    # prefer unseen but fall back

        if not pool:
            return []

        # Score each activity by how much it's needed
        scored_pool = self._score_pool(pool, mastery_states)
        scored_pool.sort(key=lambda x: x[1], reverse=True)   # highest need first

        # Sample with no-consecutive-same-type constraint
        selected: list[ActivityRecord] = []
        last_type: Optional[str] = None

        for act, _ in scored_pool:
            if len(selected) >= target_count:
                break
            if SAME_TYPE_BACK_TO_BACK and act.activity_type == last_type:
                continue
            selected.append(act)
            last_type = act.activity_type

        # If we didn't hit target due to type constraint, relax it
        if len(selected) < SESSION_MIN:
            for act, _ in scored_pool:
                if act not in selected:
                    selected.append(act)
                if len(selected) >= SESSION_MIN:
                    break

        # Shuffle slightly (maintain rough priority but add variety)
        self._soft_shuffle(selected)
        return selected

    def _score_pool(
        self,
        pool:           list[ActivityRecord],
        mastery_states: dict[str, MasteryState],
    ) -> list[tuple[ActivityRecord, float]]:
        """
        Assign a priority score to each activity.
        Higher score = more beneficial to practice right now.

        Factors:
          - type_deficit: how many fewer times this type was practiced vs the mean
          - crown_gap:    how far the paragraph is from the next crown level
          - difficulty:   medium difficulty preferred unless near crown threshold
        """
        scores = []
        for act in pool:
            ms = mastery_states.get(act.para_id) or MasteryState(
                paragraph_id=act.paragraph_id, para_id=act.para_id
            )

            # Type deficit: prefer least-practiced type
            type_count  = ms.type_counts.get(act.activity_type, 0)
            mean_count  = (ms.total_activities / max(len(ALL_TYPES), 1))
            type_deficit = max(0.0, mean_count - type_count) + (1.0 if type_count == 0 else 0.0)

            # Crown gap: boost activities for paragraphs close to levelling up
            next_lvl = ms.crown_level + 1
            if next_lvl in CROWN_THRESHOLDS:
                min_acts, min_types, _ = CROWN_THRESHOLDS[next_lvl]
                acts_needed  = max(0, min_acts  - ms.total_activities)
                types_needed = max(0, min_types - len([t for t, c in ms.type_counts.items() if c > 0]))
                crown_gap = (acts_needed + types_needed * 2) * 0.5
            else:
                crown_gap = 0.0

            # Slight penalty for repeated activities (already in seen pool)
            repeat_penalty = 0.3 if act.id in (getattr(act, '_seen_flag', set())) else 0.0

            score = type_deficit * 1.5 + crown_gap * 1.0 - repeat_penalty
            scores.append((act, score))

        return scores

    @staticmethod
    def _soft_shuffle(items: list) -> None:
        """
        Shuffle while keeping rough priority order:
        split into thirds, shuffle each third, then interleave.
        """
        if len(items) <= 3:
            return
        third = len(items) // 3
        a, b, c = items[:third], items[third:2*third], items[2*third:]
        random.shuffle(a)
        random.shuffle(b)
        random.shuffle(c)
        items[:] = a + b + c


# ─────────────────────────────────────────────────────────────────────────────
# 2. ACTIVITY SCORER
# ─────────────────────────────────────────────────────────────────────────────

class ActivityScorer:
    """
    Grades a user's answer for any activity type.
    Returns a ScoredActivity with is_correct, score (0.0–1.0), and
    result_json containing feedback details for the UI.
    """

    def score(
        self,
        activity:     ActivityRecord,
        response:     dict,
        response_ms:  Optional[int],
        sa_id:        str,
    ) -> ScoredActivity:
        fn_name = f"_score_{activity.activity_type}"
        fn = getattr(self, fn_name, self._score_unknown)
        if fn is self._score_unknown and activity.activity_type in CHOICE_ACTIVITY_TYPES:
            fn = self._score_choice_activity
        is_correct, score, result_json = fn(activity.content_json, response)
        return ScoredActivity(
            session_activity_id = sa_id,
            activity_id         = activity.id,
            activity_type       = activity.activity_type,
            paragraph_id        = activity.paragraph_id,
            is_correct          = is_correct,
            score               = round(score, 3),
            response_json       = response,
            result_json         = result_json,
            response_ms         = response_ms,
        )

    # ── Phraseology Builder ──────────────────────────────────────────────────
    # response: {"sequence": [int, ...]}  — indices into word_bank

    def _score_phraseology_builder(self, content: dict, response: dict):
        submitted  = response.get("sequence", [])
        correct    = content.get("correct_sequence", [])
        target     = content.get("target_phrase", "")
        word_bank  = content.get("word_bank", [])
        built_words = [word_bank[i] for i in submitted if 0 <= i < len(word_bank)]
        target_words = str(target).split()

        if built_words == target_words:
            return True, 1.0, {
                "correct": True,
                "built_phrase": " ".join(built_words),
                "target_phrase": target,
                "explanation": content.get("explanation", ""),
            }

        # Partial credit: Kendall tau on position matches
        n = len(correct)
        if n == 0:
            return False, 0.0, {"correct": False, "target_phrase": target}

        # Count positional matches
        matches = sum(1 for built, expected in zip(built_words, target_words) if built == expected)
        partial = matches / n

        built = " ".join(built_words)
        return False, partial, {
            "correct": False,
            "built_phrase": built,
            "target_phrase": target,
            "correct_sequence": correct,
            "partial_score": round(partial, 2),
            "explanation": content.get("explanation", ""),
        }

    # ── Spot the Error ───────────────────────────────────────────────────────
    # response: {"token_index": int}

    def _score_spot_the_error(self, content: dict, response: dict):
        submitted  = response.get("token_index")
        correct    = content.get("error_index")
        tokens     = content.get("tokens", [])
        correct_tk = content.get("correct_token", "")
        wrong_tk   = tokens[correct] if correct is not None and correct < len(tokens) else ""

        is_correct = (submitted == correct)
        return is_correct, 1.0 if is_correct else 0.0, {
            "correct":        is_correct,
            "error_index":    correct,
            "wrong_token":    wrong_tk,
            "correct_token":  correct_tk,
            "explanation":    content.get("explanation", ""),
        }

    # ── Sequence Steps ───────────────────────────────────────────────────────
    # response: {"order": ["b", "a", "c"]}  — step IDs in submitted order

    def _score_sequence_steps(self, content: dict, response: dict):
        submitted    = response.get("order", [])
        correct_order = content.get("correct_order", [])

        if submitted == correct_order:
            return True, 1.0, {
                "correct": True,
                "explanation": content.get("explanation", ""),
            }

        # Kendall tau partial credit
        score = _kendall_tau_score(submitted, correct_order)
        return False, score, {
            "correct":        False,
            "submitted_order": submitted,
            "correct_order":   correct_order,
            "partial_score":   round(score, 2),
            "explanation":     content.get("explanation", ""),
        }

    # ── Match Pairs ──────────────────────────────────────────────────────────
    # response: {"matches": [{"term": "...", "definition": "..."}]}

    def _score_match_pairs(self, content: dict, response: dict):
        pairs     = {p["term"]: p["definition"] for p in content.get("pairs", [])}
        submitted = {m["term"]: m["definition"] for m in response.get("matches", [])}

        if not pairs:
            return False, 0.0, {"correct": False}

        correct_count = sum(1 for term, defn in submitted.items() if pairs.get(term) == defn)
        total         = len(pairs)
        score         = correct_count / total

        return score == 1.0, score, {
            "correct":       score == 1.0,
            "correct_count": correct_count,
            "total":         total,
            "correct_pairs": pairs,
            "partial_score": round(score, 2),
        }

    # ── Read-back Check ──────────────────────────────────────────────────────
    # response: {"choice_index": int}

    def _score_readback_check(self, content: dict, response: dict):
        choices    = content.get("choices", [])
        submitted  = response.get("choice_index")

        if submitted is None or submitted >= len(choices):
            return False, 0.0, {"correct": False, "explanation": content.get("explanation","")}

        is_correct = choices[submitted].get("is_correct", False)
        correct_idx = next((i for i, c in enumerate(choices) if c.get("is_correct")), None)

        return is_correct, 1.0 if is_correct else 0.0, {
            "correct":       is_correct,
            "submitted_idx": submitted,
            "correct_idx":   correct_idx,
            "correct_text":  choices[correct_idx]["text"] if correct_idx is not None else "",
            "explanation":   content.get("explanation", ""),
        }

    # ── Situation → Action ───────────────────────────────────────────────────
    # response: {"choice_index": int}

    def _score_situation_action(self, content: dict, response: dict):
        # Same structure as readback_check
        return self._score_readback_check(content, response)

    def _score_choice_activity(self, content: dict, response: dict):
        return self._score_readback_check(content, response)

    # ── Fallback ─────────────────────────────────────────────────────────────

    def _score_unknown(self, content: dict, response: dict):
        return False, 0.0, {"correct": False, "error": "Unknown activity type"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. CROWN CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

class CrownCalculator:
    """
    Determines the crown level for a paragraph given a MasteryState.

    Crown levels:
      0  — Not started
      1  — Introduced:  ≥ 1 activity, any type, score ≥ 50%
      2  — Familiar:    ≥ 3 activities, ≥ 2 types, avg score ≥ 70%
      3  — Proficient:  ≥ 6 activities, ≥ 4 types, avg score ≥ 85%
      4  — Gold:        ≥ 10 activities, ≥ 6 types attempted, avg score ≥ 90%
    """

    def calculate(self, state: MasteryState) -> int:
        """Return the crown level (0–4) for the given mastery state."""
        if state.total_activities == 0:
            return 0

        types_done     = [t for t, c in state.type_counts.items() if c >= 1]
        types_with_avg = {t: s for t, s in state.type_avg_scores.items() if s is not None}

        overall_avg = (
            sum(types_with_avg.values()) / len(types_with_avg)
            if types_with_avg else 0.0
        )

        achieved = 0
        for level in [4, 3, 2, 1]:
            min_acts, min_types, min_score = CROWN_THRESHOLDS[level]
            if level == 4:
                # Gold requires at least the configured number of distinct types.
                if (state.total_activities >= min_acts
                        and len(types_done) >= min_types
                        and overall_avg >= min_score):
                    achieved = 4
                    break
            else:
                if (state.total_activities >= min_acts
                        and len(types_done) >= min_types
                        and overall_avg >= min_score):
                    achieved = level
                    break

        return achieved

    def next_level_requirements(self, state: MasteryState) -> Optional[dict]:
        """
        Returns a dict describing what's needed to reach the next crown level,
        or None if already Gold.
        """
        current = self.calculate(state)
        if current >= 4:
            return None

        next_lvl = current + 1
        min_acts, min_types, min_score = CROWN_THRESHOLDS[next_lvl]

        types_done   = [t for t, c in state.type_counts.items() if c >= 1]
        types_with_avg = {t: s for t, s in state.type_avg_scores.items() if s is not None}
        overall_avg    = sum(types_with_avg.values()) / max(len(types_with_avg), 1)

        acts_needed  = max(0, min_acts  - state.total_activities)
        types_needed = max(0, min_types - len(types_done))
        score_gap    = max(0.0, min_score - overall_avg)
        untried_types = [t for t in ALL_TYPES if t not in types_done]

        return {
            "target_level":      next_lvl,
            "activities_needed": acts_needed,
            "types_needed":      types_needed,
            "score_target":      min_score,
            "current_avg_score": round(overall_avg, 3),
            "score_gap":         round(score_gap, 3),
            "untried_types":     untried_types[:types_needed],
            "summary":           _crown_summary(acts_needed, types_needed, score_gap, untried_types),
        }

    def update_state(
        self,
        state:         MasteryState,
        activity_type: str,
        score:         float,
    ) -> MasteryState:
        """
        Return a new MasteryState after recording one activity result.
        (Pure function — does not touch the DB.)
        """
        import copy
        new = copy.deepcopy(state)

        new.type_counts[activity_type] = new.type_counts.get(activity_type, 0) + 1
        new.total_activities += 1
        if score >= 0.5:
            new.total_correct += 1 if hasattr(new, 'total_correct') else 0

        # Rolling average per type
        prev_avg   = new.type_avg_scores.get(activity_type, score)
        prev_count = new.type_counts[activity_type] - 1
        if prev_count == 0:
            new.type_avg_scores[activity_type] = score
        else:
            new.type_avg_scores[activity_type] = round(
                (prev_avg * prev_count + score) / (prev_count + 1), 4
            )

        return new


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _kendall_tau_score(submitted: list, correct: list) -> float:
    """
    Partial credit for ordering tasks using Kendall tau distance.
    Returns 0.0–1.0 (1.0 = perfect order).
    """
    if not correct or submitted == correct:
        return 1.0 if submitted == correct else 0.0

    # Build position map from correct order
    pos = {v: i for i, v in enumerate(correct)}
    n   = len(correct)

    # Count inversions in submitted sequence
    sub_positions = [pos.get(v, -1) for v in submitted if v in pos]
    inversions = 0
    for i in range(len(sub_positions)):
        for j in range(i + 1, len(sub_positions)):
            if sub_positions[i] > sub_positions[j]:
                inversions += 1

    max_inv = n * (n - 1) // 2
    return round(1 - (inversions / max_inv), 3) if max_inv else 1.0


def _crown_summary(
    acts: int, types: int, score_gap: float, untried: list[str]
) -> str:
    parts = []
    if acts > 0:
        parts.append(f"{acts} more activit{'y' if acts == 1 else 'ies'}")
    if types > 0:
        type_labels = {
            "phraseology_builder": "phraseology builder",
            "spot_the_error":      "spot the error",
            "sequence_steps":      "sequence steps",
            "match_pairs":         "match pairs",
            "readback_check":      "read-back check",
            "situation_action":    "situation → action",
        }
        names = [type_labels.get(t, t) for t in untried[:types]]
        parts.append(f"try {', '.join(names)}")
    if score_gap > 0.01:
        parts.append(f"score {round((1 - score_gap) * 100):.0f}%+ avg")
    return "To level up: " + "; ".join(parts) + "." if parts else "Almost there!"
