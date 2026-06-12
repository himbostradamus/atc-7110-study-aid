# Content Expansion Audit — Chapter 11, Pass 1

**Verdict: SAFE TO PUBLISH**

No critical or major findings were identified. The batch contains 8 items across
three format families, all of which are source-faithful and test genuine
operational concepts. Seven minor findings and three suggestions are recorded
below for quality improvement before future passes.

---

## Scope

- **Batch:** `chapter_11_pass_01.json`
- **Paragraphs covered:** 11-1-2 (Duties and Responsibilities), 11-1-3 (Time Based Flow Management)
- **Items reviewed:** 8 (3 questions, 2 activities, 2 flashcards)

---

## Critical / Major Findings

None.

---

## Minor Findings

### 1. Cross-format duplication: 11-1-2b1 tested twice (question + activity)

- **questions.11-1-2.items[0]** — OS/CIC duty to keep TMU and sectors apprised (weather forecast trigger)
- **activities.11-1-2.items[0]** — Same rule (equipment outage trigger)

Both items test paragraph 11-1-2b1 with nearly identical correct-answer text
("Keep the TMU and affected sectors apprised, because the situation may cause
congestion or delays even though delays are not yet present"). While the
scenarios differ, the rule application and answer formulation are substantively
the same. The situation_action activity is the stronger format for this
operational rule — it provides richer decision-making context. The question
could be replaced with coverage of a different 11-1-2 sub-paragraph (e.g., b3
continuous review, or c2 personnel notification duties).

### 2. Cross-format duplication: note to 11-1-3 tested twice (question + activity)

- **questions.11-1-3.items[0]** — Caution when TBFM accuracy affected (general factors)
- **activities.11-1-3.items[0]** — Same rule (resequencing scenario)

Both items test the note at 11-1-3 with correct answers sharing the same core
instruction: use caution to minimize impact on surrounding sector traffic,
complexity, flight efficiency, and user preferences. As with finding 1, the
activity format provides stronger operational context. The question could be
replaced with coverage of a different 11-1-3 sub-paragraph (e.g., 11-1-3c
coordination parties when compliance is not possible).

### 3. Positional cue: answers placed first in 2 of 6 question/activity items

- **questions.11-1-2.items[0]** — correct answer at index 0; also ~60% longer than distractors
- **activities.11-1-2.items[0]** — correct answer at index 0

First-position placement teaches learners to expect the first option is correct.
Combined with answer-length difference in the question item, this creates a dual
cue that reduces assessment validity.

### 4. Flashcard front wording: "in place of TBFM metering" overstates scope

- **flashcards.11-1-3.items[0]**

The card front says "in place of TBFM metering," implying MIT or MINIT replaces
TBFM metering wholesale during DCT instability. Per 11-1-3b1, MIT or MINIT is
applied "between those aircraft" — only the specific aircraft affected by DCT
instability — as a supplementary delay-absorption measure, not a replacement for
metering across the sector. The back correctly clarifies this scope, but the
front's wording overstates the replacement scope.

---

## Suggestions

### 1. Stem wording: "must cover" vs "should include"

- **questions.11-1-2.items[2]**

The stem states "The STMCIC operational briefing must cover..." but the source
(11-1-2a1) says discussions "should include" the listed topics — "must" applies
to the briefing's occurrence, not to each topic's inclusion. The question tests
exactly this distinction, so the stem is presenting the misconception that the
answers examine. Consider softening to "The STMCIC operational briefing
addresses..." to avoid momentarily misleading learners who have not yet
internalized the must/should distinction.

### 2. Answer-length cue in activity 11-1-3.items[0]

The correct answer is 38 words while distractors range from 14 to 21 words.
The correct answer incorporates the full source-language list of impacts
("surrounding sector traffic, complexity, flight efficiency, and user
preferences"). Length alone provides a cue independent of knowledge. Consider
trimming the correct answer or lengthening distractors to balance.

### 3. Dual retrieval target in flashcard 11-1-2.items[0]

The card asks two separate questions: enforcement group under STMCIC and under
OS/CIC. Each targets a different source sub-paragraph (11-1-2a3 and 11-1-2b4).
While the two groups are operationally paired — confusing them is a specific
error — a learner who recalls one but not the other cannot cleanly self-grade.
Splitting into two single-target cards would improve retrieval focus, but the
dual-target risk is acceptable given the operational pairing.

---

## Strengths Observed

- **No paragraph-number stems.** All 8 items use self-contained stems without
  embedding paragraph references — a clear improvement applying prior
  remediation guidance.

- **All distractors represent plausible operational errors.** None are obviously
  wrong; each has a discernible misconception a learner might hold. The ATCT vs
  ARTCC/TRACON question (11-1-2 items[1]) is particularly well-constructed with
  balanced, parallel distractors.

- **Explanations address the strongest misconception.** Each explanation cites
  the controlling source paragraph and explains why the most attractive
  distractor is wrong, not merely why the correct answer is right.

- **Situation-action activities use realistic scenarios.** Both activities
  (equipment outage advisory, resequencing during TBFM metering) present
  operational dilemmas that require rule application rather than recall. This
  continues a pattern identified as a strength in prior reviews.

- **The enforcement-group distinction flashcard (11-1-2 items[0]) correctly
  resolves a previously identified error.** Prior remediation flagged content
  that conflated the STMCIC enforcement group (personnel providing traffic
  management services) with the OS/CIC enforcement group (personnel providing
  air traffic services). This flashcard teaches the distinction correctly.

- **The DCT instability flashcard (11-1-3 items[0]) tests a distinct retrieval
  target.** It asks about duration ("how long") rather than the action itself,
  which is already covered by an existing flashcard. This is good retrieval
  diversity.

---

## Background: Prior Remediation Applied

This batch shows clear application of prior remediation guidance for Chapter 11:

- All fill-in-the-blank items have been converted to multiple-choice or
  situation_action formats. No single-choice or near-identical-choice
  fill_blank items appear.

- Paragraph-number scaffolding ("Under 11-1-2...") has been removed from all
  stems. The underlying operational knowledge is tested without document
  navigation cues.

- The enforcement-group conflation error previously identified has been
  corrected in new content that explicitly distinguishes the STMCIC and OS/CIC
  enforcement groups.

- Format-appropriate item types are used: multiple-choice for assessment,
  situation_action for scenario-based decision-making, concept/procedure
  flashcards for retrieval practice.

---

## Publication Readiness

The batch meets the quality bar for publication. All items are source-faithful,
educationally substantive, and free of critical or major defects. The seven
minor findings (cross-format duplication, positional cues, one phrasing
imprecision) and three suggestions can be addressed in a future quality pass
without blocking publication.

**Verdict: SAFE TO PUBLISH**
