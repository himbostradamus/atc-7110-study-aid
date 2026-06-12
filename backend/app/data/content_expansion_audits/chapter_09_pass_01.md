# Chapter 9 Content Expansion Audit — Pass 1

**Verdict: SAFE WITH FIXES**

**Batch:** `backend/app/data/content_expansion_staging/chapter_09_pass_01.json`
**Items reviewed:** 36 (11 questions, 7 activities, 18 flashcards)
**Date:** 2026-06-11

---

## Summary

The Chapter 9 pass-1 staging batch is substantially clean and well-remediated from prior patterns.
Paragraph-location scaffolding has been fully excised — all 36 items now open with operational
scenarios or concept-driven prompts. Source fidelity is accurate across the board: no factual
misrepresentations of minima, trigger conditions, exceptions, prescribed phraseology, or procedural
sequences were found. Correct-answer positions are reasonably distributed. No single-choice
fill-in-the-blank items, regulation-number trivia, or malformed reverse cards appear.

One major finding requires attention before publication. Several minor and suggestion-level findings
address cross-format duplications, interpretive glosses on flashcard backs, and format consistency.

---

## Critical Findings

*None.*

---

## Major Findings

### activities.9-1-2.items[0] — Near-identical answer choices create ambiguity

**Para:** 9-1-2 (Flight inspection — deviation exception)

Two answer choices describe the same operational action:

- **Choice A** (false): "Ask the flight inspection aircraft to deviate from its planned approach to avoid the emergency aircraft."
- **Choice D** (true): "Ask the flight inspection aircraft to deviate from the planned action, because an emergency situation requires it."

Both describe asking the flight inspection aircraft to deviate in an emergency context. The only
distinction is that D appends the emergency-justification language. A student who understands the
emergency exception can rationally select either choice — they describe the same action. The
correct answer is identified by the appended rationale rather than by a different operational
action, creating a wording-pattern cue rather than a knowledge discriminator.

**Source basis:** 9-1-2a: "Do not ask the pilot to deviate from his/her planned action except to
preclude an emergency situation."

**Recommended action:** Rewrite choices to test genuinely different operational actions. The
correct choice should state the action concisely without embedded justification:
"Ask the flight inspection aircraft to deviate because an emergency requires it." Distractors
should describe meaningfully different actions (e.g., continue the run uninterrupted, terminate
the run unilaterally, vector without pilot consultation).

---

## Minor Findings

### flashcards.9-2-14.items[0] — Cross-format duplication with question 9-2-14

Both this flashcard and the question at 9-2-14 test the originating ARTCC's authority to waive the
16-hour advance supersonic flight plan filing requirement. No difference in retrieval direction or
depth. The question already covers this fact; the flashcard should target a different aspect of 9-2-14
(e.g., the advance filing time itself, the route fix requirement, or the vertical separation minimum).

### flashcards.9-2-15.items[0] — Cross-format duplication with activity 9-2-15

Both this flashcard and the activity at 9-2-15 test the prohibition against assigning the special use
frequency when aircraft operate in airspace assigned for special military operations. The retrieval
direction is identical in both formats. The flashcard should be differentiated to test a distinct
aspect of 9-2-15 (e.g., which aircraft types are eligible, when the frequency may serve as backup,
or when receiver aircraft leave the frequency for tanker communications).

### flashcards.9-1-1.items[1] — Source paraphrase: "pre-coordinated" vs "coordinated before departure"

The flashcard back says "pre-coordinated with appropriate facilities." The source text (9-1-1 Note 2)
reads "coordinated with appropriate facilities before departure." The meaning is equivalent but the
back should use exact source language.

### flashcards.9-1-2.items[0] — Interpretive gloss exceeding source

The back adds "The clearance does not need to be instantaneous, but it must be issued as soon as
operational circumstances reasonably permit." The source (9-1-2a) states only "as soon as practicable."
While the interpretation is defensible, it is not source-grounded.

### flashcards.9-2-20.items[0] — Back includes unasked supplementary facts

The front asks only about the altitude block (2,000 feet), but the back appends "at or above FL 250
along a 60 NM segment." These details were not cued by the front and create an unexpected retrieval
target.

### flashcards.9-3-3.items[0] — Back adds unsourced interpretive commentary

The back adds "This informs the pilot that the area is ATC-assigned, not standard special use airspace."
This explanation is not present in the source paragraph (9-3-3), which contains only the prescribed
phraseology.

### flashcards.9-7-3.items[0] — Back adds unsourced cross-airspace comparison

The back adds "This is a more flexible standard than Class A/B/C, where jumping is authorized only
within designated airspace." This comparison is a reasonable pedagogical inference but is not
contained in the source paragraph (9-7-3).

### activities.9-2-14.items[0] — Instruction/question mismatch

The `instruction` field reads "What should you do?" but the `question_text` is "Was the trainee's
vectoring action appropriate?" The generic action-directive instruction does not match the
trainee-judgment question framing.

---

## Suggestions

### questions.9-1-1.items[0] — Specific mechanism may over-index the student

The scenario anchors the "otherwise agreed to" exception on a specific mechanism — relay through the
operations supervisor. The source (9-1-1) uses the broader "unless otherwise agreed to" without
prescribing the channel. A student might incorrectly infer that only operations-supervisor relays
satisfy the exception. Consider adding a clarification to the explanation that any pre-coordinated
alternative method qualifies.

---

## Patterns Observed

1. **Flashcard-back glosses (4 items):** Several flashcards add interpretive or comparative
   commentary to the back that extends beyond strict source text. While these glosses are
   pedagogically reasonable, they are not source-attributed. This pattern appears in
   9-1-2[0], 9-2-20[0], 9-3-3[0], and 9-7-3[0].

2. **Cross-format duplication (2 items):** Two flashcards test the identical fact as their
   corresponding question or activity with no distinct retrieval angle (9-2-14, 9-2-15).
   This is a low rate given 18 flashcards, but still worth noting for batch normalization.

3. **Source fidelity — strong.** All item answers are factually accurate against the source packet.
   No minima, trigger conditions, exceptions, or procedural sequences are misrepresented.
   The prior remediation's heavy structural problems (paragraph-location scaffolding, answer-length
   cues, single-choice fill-in-the-blanks, malformed reverse cards) have been fully resolved.

---

## Strengths

- **No paragraph-location scaffolding:** All stems and flashcard fronts use operational or
  concept-driven framing. Not a single "Under 9-X-Y" opening remains.
- **Distributed answer positions:** Correct answers appear in all four positions — questions
  at 3/3/3/2, activities at 2/2/1/2.
- **Clean formats:** No single-choice fill-in-the-blank items, no regulation-number trivia,
  no malformed reverse cards, no overloaded flashcards (all cards have 1–3 discrete facts).
- **Operational scenarios:** Questions embed the rule trigger in a realistic controller situation
  rather than paraphrasing the paragraph text.
- **Flashcard retrieval scope:** All flashcards target one coherent fact or a tightly-bound
  required list (two-item condition pairs, phraseology snippets, etc.).
