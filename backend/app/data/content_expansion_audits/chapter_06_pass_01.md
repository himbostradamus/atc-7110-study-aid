# Content Expansion Audit — Chapter 6, Pass 1

**Verdict: SAFE WITH FIXES**

One critical answer-key contradiction must be resolved before publication. All other
findings are minor or suggestions that do not block publication.

## Scope

- **Batch:** `chapter_06_pass_01.json`
- **Paragraphs:** 6-5-1, 6-5-4, 6-6-1, 6-6-3, 6-7-1, 6-7-3, 6-7-4, 6-7-6
- **Items reviewed:** 50 (20 questions, 8 activities, 22 flashcards)
- **Source packet:** `packets/chapter_06.json`
- **Remediation context:** No prior remediation entries exist for paragraphs 6-5 through 6-7.

---

## Critical Findings

### 1. `activities.6-6-3.items[0]` — Answer-key contradiction (CRITICAL)

The marked-correct answer choice reads:

> **"No;** Aircraft A is the upper aircraft descending toward Aircraft B — this matches
> the rule's assignment and the authorization is valid."

The question asks: *"May the controller authorize Aircraft A to maintain vertical
separation?"* The answer should be **Yes.** The leading "No" directly contradicts the
rest of the sentence and the explanation, both of which confirm the authorization is valid.

**Source basis:** 6-6-3 authorizes the upper aircraft if descending. Aircraft A is at
FL200 (upper) descending to FL160 through Aircraft B at FL180 (lower). This matches the
rule exactly.

**Fix:** Change "No;" to "Yes;" in the answer choice text.

---

## Major Findings

None.

---

## Minor Findings

### 2. `flashcards.6-5-1.items[0]` — Omitted "or hold at" in method (b) (minor, source_fidelity)

The flashcard back summarizes lateral separation method (b) as:

> "(Below 18,000) Proceed to and report over different geographical locations."

The source reads: *"proceed to and report over **or hold at** different geographical
locations."* Omitting "or hold at" removes an entire permissible alternative. Method (b)
allows holding at geographical locations (distinct from method (c) which covers holding
over different fixes).

**Fix:** Add "or hold at" to the back text.

### 3. `questions.6-6-1.items[1]` — Ambiguous question stem (minor, context)

> "A controller needs to know **when** an aircraft departs an assigned altitude but is
> unsure whether the aircraft is above or below the lowest usable flight level."

The word "when" creates ambiguity: it can be read as "at what time" (suggesting
REPORT LEAVING phraseology) rather than "in a situation where" (intended reading for
SAY ALTITUDE OR FLIGHT LEVEL). A student who recognizes the conditional phraseology
for unknown FL position may still be thrown by the departure wording.

**Fix:** Reword to: *"A controller needs to request an aircraft's current altitude but
is unsure whether the aircraft is above or below the lowest usable flight level. What
phraseology should be used?"*

### 4. `questions.6-6-3.items[1]` — Close paraphrase of items[0] (minor, duplication)

This question asks *"Which aircraft is moving toward the other under the rule's
assignment?"* — testing the same lower-if-climbing / upper-if-descending fact as
`questions.6-6-3.items[0]`. Both are multiple-choice items with substantially
overlapping answer content. Items[0] already establishes the rule assignment; items[1]
re-asks it from a movement-direction angle without adding new operational depth.

### 5. `questions.6-7-1.items[0]` — Answer-length cue (minor, format)

The correct answer (155 characters, restating the full source-note capability) is
roughly 2–3× longer than the three distractors (51–68 characters). This asymmetry
creates a mild visual cue that the longest choice is correct.

### 6. `questions.6-7-4.items[1]` — Answer-length cue (minor, format)

The correct answer (132 characters) is approximately twice the length of the
distractors (51–72 characters), creating a similar length cue.

---

## Suggestions

### 7. `questions.6-6-1.items[1]` — Single-answer fill_blank format (suggestion, format)

Fill-in-the-blank with one provided answer choice gives no distractor discrimination.
Consider converting to multiple-choice with plausible alternatives (SAY ALTITUDE,
SAY FLIGHT LEVEL, REPORT LEAVING) to test discrimination across the three conditional
phraseologies.

### 8. `flashcards.6-7-6.items[0]` and `items[1]` — Over-coverage of a brief rule (suggestion, duplication)

Four items (two questions, two flashcards) test the time-check rule and its single
exception from one brief source sentence. The rule is operationally important, but the
pair could be consolidated to one flashcard capturing both the rule and exception.

---

## Summary Assessment

**Strengths:**

- Zero paragraph-location scaffolding. All stems use operational context. This
  distinguishes the batch from earlier chapter passes that prompted remediation for
  pervasive "Per 6-X-Y" references.
- Distractors are plausible and parallel, reflecting real operational misconceptions.
- Phraseology items faithfully reproduce the conditional tiers from 6-6-1.
- 6-5-4 items cover sub-paragraphs (degree-distance fixes, GNSS random RNAV, impromptu
  transitions) with little or no existing content, filling genuine coverage gaps.
- Flashcards respect the single-target retrieval scope; list cards are reserved for
  required memorized sequences.
- Explanations teach controlling principles, not paragraph locations.
- The 6-7-1 activity correctly applies the integrated ceiling-plus-elevation-vs-MDA
  comparison from the source note.

**Patterns to watch:**

- One critical answer-text contradiction (6-6-3 activity) that appears to be a
  copy-paste error with a wrong leading word.
- Two questions with answer-length cues where the source text's natural verbosity
  inflates the correct choice relative to synthetic distractors.
- Mild conceptual overlap between adjacent questions in the same paragraph group
  (6-6-3 items[0]/[1]).
- One flashcard omission ("or hold at") that slightly narrows a method's scope.

**Publication readiness:** The batch is publication-ready after the single critical fix
to `activities.6-6-3.items[0]`. The minor and suggestion-level findings are quality
improvements that can be addressed in a subsequent pass without blocking release.

---

*Audit conducted 2026-06-11. Validator run pending.*
