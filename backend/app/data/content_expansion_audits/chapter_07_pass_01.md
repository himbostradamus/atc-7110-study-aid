# Chapter 7 Pass 01 — Content Expansion Audit Report

**Verdict: SAFE WITH FIXES**

Two major findings must be addressed before publication. No critical findings. Seven
minor/suggestion items identified for continuous improvement.

---

## Major Findings

### 1. `questions.7-6-7.items[0]` — Source Fidelity: Overtaking Restriction Missing Wake-Turbulence Trigger

The question describes parallel runways 2,000 feet apart with a faster trailing
aircraft closing on a slower lead. The correct answer states "The trailing aircraft
must not overtake the aircraft on the adjacent final approach course" as an absolute
rule.

Per 7-6-7c2, the overtaking prohibition is **conditional on wake turbulence**:

> "When parallel runways are less than 2,500 feet apart, do not permit an aircraft to
> overtake another aircraft established on final within the facility's area of
> responsibility **when wake turbulence separation is required.**"

The question and its explanation omit this trigger condition. The scenario does not
establish that wake turbulence separation is required (no aircraft types or weight
categories are given). Without wake turbulence requiring separation, overtaking may
be permitted by the source rule. The correct answer overstates the restriction.

**Recommended action:** Add wake turbulence context to the scenario (e.g., "a Small
category aircraft trailing a Heavy Boeing 757") so the condition is met, or change
the correct answer to state the full conditional rule.

---

### 2. `flashcards.7-4-5.items[0]` — Overloaded Retrieval Target

The card asks the student to recall ALL four CVFP authorization conditions in a single
flashcard. The back lists:

1. Operating control tower
2. Published name and runway, ceiling ≥ 500 ft above MVA/MIA, visibility ≥ 3 miles
3. Parallel/intersecting runway criteria per 7-4-4
4. Visual reference requirements (charted landmark or preceding aircraft)

Four multi-part conditions exceed the single-target retrieval scope expected of a
flashcard. Controllers do not need to recall this entire checklist as a unit — they
reference it procedurally.

**Recommended action:** Split into two cards:
- "What weather minima are required for a CVFP?"
- "What visual reference must a pilot report for a CVFP when not following another
  aircraft?"

---

## Minor Findings

### 3. `questions.7-5-3.items[0]` — Explanation Scope Too Narrow

The explanation says radar separation for SVFR helicopters applies "when the facility
has certified tower radar displays." Per 7-5-3 note 2, radar separation may be applied
by any facility authorized to provide radar separation services, not just CTRD-equipped
towers. Broaden the explanation.

### 4. `flashcards.7-3-2.items[0]` — Redundant Paired Card

This card (odd altitudes + 500) and `flashcards.7-3-2.items[1]` (even altitudes + 500)
are near-mirror images. They could be merged into one contrast card to reduce review
overhead while improving the learner's ability to discriminate eastbound vs. westbound
rules.

### 5. `questions.7-4-2.items[0]` — Context Ambiguity with 7-4-3

The question tests the 7-4-2 note about pilot requests at airports without weather
reporting, but does not distinguish whether it's asking about *vector initiation*
(7-4-2) vs. *approach clearance* (7-4-3). Adding "for purposes of initiating a
vector" to the stem would clarify scope.

---

## Suggestions

### 6. `flashcards.7-4-2.items[0]` — Mixed-Context Retrieval

The card back covers both weather-reporting-airport and no-weather-reporting-airport
conditions. This is a valid summary card but mixes two operationally distinct
scenarios. Consider splitting if students report difficulty with partial recall.

### 7. `questions.7-9-2.items[0]` — Minor Distractor Parallelism

The third distractor ("Deviate from the clearance as needed...") uses an imperative
form while the other distractors use declarative propositions. Slight rephrasing
would improve parallelism.

### 8. `activities.7-4-7.items[0]` — Explanation Could Emphasize Judgment Trigger

The scenario is well constructed (ground visibility exactly 1 mile, controller
concerned about fog), but the explanation could explicitly note that the alternative
clearance under 7-4-7e is triggered by controller judgment, not a below-minimum
visibility report. This nuance distinguishes contact approaches from other approach
types.

---

## Patterns Noted

- **Paragraph scaffolding eliminated.** All staged items use operationally framed
  stems. Prior remediation guidance was fully applied.
- **Answer position distribution is healthy.** Correct answers appear in positions
  0–3 without detectable bias.
- **Distractor quality is high.** No answer-length cuing observed. Distractors are
  plausible and parallel.
- **Cross-format differentiation holds.** Questions test rule recognition/application,
  activities test procedural decision-making, flashcards test rapid recall. Items
  across formats for the same paragraph cover distinct retrieval layers.
- **Existing-content overlap is minimal and expected.** The batch adds sentence-level
  granularity to paragraphs already covered by earlier passes.

---

## Items Reviewed

All 71 staged items across questions, activities, and flashcards were individually
verified against the source packet. Every item path appears exactly once in the JSON
report's `reviewed_item_paths`.

---

## Publication Readiness

This batch is **safe to publish after the two major findings are resolved**:

1. Fix the 7-6-7 overtaking question to correctly reflect the wake-turbulence
   conditional trigger.
2. Split the overloaded 7-4-5 CVFP flashcard.

The minor and suggestion items may be addressed at the author's discretion in the
next pass.
