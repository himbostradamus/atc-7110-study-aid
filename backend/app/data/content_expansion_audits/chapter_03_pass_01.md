# Chapter 3 Content Expansion Audit — Pass 1

**Verdict: SAFE WITH FIXES**

Three major source-attribution errors must be corrected before publication:
two items tagged to the wrong paragraph (3-7-5 and 3-10-3) and one
flashcard carrying the same misattribution. The content in all three is
operationally correct — only the `para_id` metadata is wrong.

---

## Major Findings

### 1. `questions.3-10-3.items[0]` — Wrong paragraph attribution

**Severity:** major | **Category:** source_fidelity

The question asks _"What is a nonapproach control tower's obligation regarding approach
information for arriving aircraft?"_ and is tagged to **3-10-3 (Same Runway Separation)**.

Paragraph 3-10-3 covers same-runway separation minima (3,000 ft, 4,500 ft, 6,000 ft)
and wake turbulence — it contains nothing about nonapproach control towers. The tested
rule actually belongs to **3-10-2 (Forwarding Approach Information by Nonapproach Control)**,
whose source text states: _"Nonapproach control towers must forward approach information
to arriving aircraft."_

**Action:** Change `para_id` from `3-10-3` to `3-10-2`. The question stem, choices,
and answer key are operationally correct and can remain unchanged.

---

### 2. `questions.3-7-5.items[0]` — Wrong paragraph attribution

**Severity:** major | **Category:** source_fidelity

The question asks about converging aircraft on taxiways and tags it to **3-7-5
(Precision Approach Critical Area)**. Paragraph 3-7-5 covers ILS critical area
protection — localizer critical area, glideslope critical area, weather thresholds
(ceiling < 800 ft or visibility < 2 miles) — not general taxiway convergence.

The tested rule (positive control when aircraft on different taxiways converge toward
the same intersection) is a general ground-traffic-management principle, most closely
associated with **3-7-1 (Ground Traffic Movement)**.

**Action:** Reattribute the question to `3-7-1`. Check for overlap with existing
3-7-1 items to avoid duplication.

---

### 3. `flashcards.3-7-5.items[0]` — Same paragraph misattribution as item #2

**Severity:** major | **Category:** source_fidelity

The flashcard front asks _"When two aircraft are taxiing on converging taxiways
toward the same intersection, what is the controller's responsibility?"_ and is
tagged to 3-7-5. Same issue as the parallel question: 3-7-5 covers ILS critical
area protection, not taxiway intersection control.

**Action:** Reattribute to `3-7-1` to match the corrected question. Card content is
operationally correct.

---

## Minor Findings

### 4. `questions.3-3-2.items[0]` and `flashcards.3-3-2.items[0]` — Missing alternative exception

**Severity:** minor | **Category:** source_fidelity

Both the question and its parallel flashcard test the efficiency-impact exception for
using a closed runway's ILS, but omit the side-step maneuver exception in 4-8-7.
Source 3-3-2c reads: _"Except as permitted by paragraph 4-8-7, Side-Step Maneuver...
the ILS associated with the closed runway should not be used for approaches unless
not using the ILS would have an adverse impact on the operational efficiency of the airport."_

The question's correct answer is still valid (efficiency is a valid condition), but
the omission creates a completeness gap. The flashcard back is similarly incomplete.

**Action:** For the question, refine the stem to exclude the side-step scenario or
add the side-step reference to the explanation. For the flashcard, add a brief
side-step mention to the back.

---

### 5. `activities.3-7-1.items[0]` — Dense triple-rule activity

**Severity:** minor | **Category:** educational_value

This activity tests three distinct 3-7-1 rules simultaneously: (a) prohibition of
"cleared" for surface movement, (b) prohibition of unconditional instructions like
"the field is yours," and (c) mandatory issuance of measured intersection-departure
distance to military aircraft. Each distractor combines correct and incorrect handling
across all three dimensions. All three rules are from 3-7-1, so paragraph cohesion
is maintained, but the cognitive load is higher than typical single-rule activities.

**Action:** Consider splitting into two activities if learner performance data shows
confusion. The current format is defensible as an integrative challenge.

---

### 6. `flashcards.3-1-6.items[0]` — Paragraph reference in flashcard back

**Severity:** minor | **Category:** educational_value

The flashcard back includes _"prescribed in paragraph 2-1-21"_ — a cross-paragraph
reference in the answer text. The operational answer stands without the citation:
_"The standard radar traffic-advisory phraseology — the same phraseology used by
radar approach control facilities."_

**Action:** Remove the `paragraph 2-1-21` reference; retain the operational description.

---

## Suggestions

### 7. `questions.3-1-3.items[0]` — Mild answer-length cue

**Severity:** suggestion | **Category:** distractor_quality

The correct answer is approximately 45% longer than the longest distractor due to
the specific citation references it contains. While the tested rule genuinely requires
specificity, the length difference is a mild cue.

---

### 8. `questions.3-9-4.items[0]` — Para attribution is a loose fit

**Severity:** suggestion | **Category:** educational_value

The question uses an "emergency aircraft" scenario tagged to 3-9-4 (LUAW), but the
specific rule about not issuing a landing clearance with a LUAW aircraft on the runway
is in 3-10-5e. The 3-9-4 attribution is defensible since LUAW procedures span both
paragraphs, but consider confirming the tagging or tightening to 3-10-5.

---

## Summary Statistics

| Category | Critical | Major | Minor | Suggestion |
|----------|----------|-------|-------|------------|
| Source fidelity | 0 | 3 | 2 | 0 |
| Educational value | 0 | 0 | 2 | 1 |
| Distractor quality | 0 | 0 | 0 | 1 |
| **Total** | **0** | **3** | **4** | **2** |

- **44 items** reviewed (15 questions, 11 activities, 18 flashcards)
- **41 items** (93%) pass without any findings
- **3 items** require para_id reattribution before publication
- **0 items** have unsafe or incorrect operational content

---

## Patterns Observed

- **No paragraph-location scaffolding in stems** — all questions are self-contained
  scenarios; the remediation guidance was successfully followed.
- **No answer-position bias** — correct answers are evenly distributed across
  positions 0–3 across both questions and activities.
- **No table-reference or 'which paragraph' trivia** — all items test operational
  knowledge.
- **All distractors are plausible and parallel** — no obviously wrong or joke
  distractors detected.
- **Explanations teach the operational principle** — they address the controlling
  condition or the strongest misconception rather than restating the answer.
