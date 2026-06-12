# Chapter 4 — Content Expansion Audit, Pass 01

**Verdict: BLOCK PUBLICATION PENDING FIXES**

**Date:** 2026-06-11
**Batch:** `chapter_04_pass_01.json` (30 items across 4 questions, 5 activities, 21 flashcards)
**Reviewer:** Independent QA (not the author)

---

## Verdict Summary

Pass 01 is a substantial quality improvement over pass 00: all empty-shell activities have been replaced with fully authored content, paragraph-location scaffolding is absent from stems and fronts, flashcard backs contain operational context instead of bare values, and correct answers are distributed across positions. Three blocking defects — one critical phraseology error and two major source-fidelity errors — prevent publication. The remaining 27 items are publication-ready; the three flagged items require targeted text edits only, not structural rework.

---

## Blocking Findings (Critical and Major)

### CRITICAL — Flashcard 4-7-10: Wrong AWOS/ASOS Phraseology

**Item:** `flashcards.4-7-10.items[0]`

The card back states:

> AIRPORT AWOS/ASOS WEATHER (frequency) ON FREQUENCY

The prescribed phraseology at 4-7-10b is:

> (Airport) AWOS/ASOS WEATHER **AVAILABLE ON** (frequency)

The card drops the required word `AVAILABLE` and reconstructs the phraseology as `(frequency) ON FREQUENCY`. The example — "AIRPORT AWOS WEATHER ONE TWO EIGHT POINT THREE TWO ON FREQUENCY" — would be non-standard if spoken. Controllers must use `AVAILABLE ON`, not `ON FREQUENCY`.

**Fix:** Correct the back to `AIRPORT AWOS/ASOS WEATHER AVAILABLE ON (frequency)` with a matching example.

---

### MAJOR — Question 4-5-6: MEA Crossing Requirement Misstated

**Item:** `questions.4-5-6.items[0]`

The correct answer states the aircraft "must be at or above the higher MEA upon crossing RIGEL" and "climb must begin early enough to be level by the fix." This contradicts paragraph 4-5-6c1:

> If no MCA is specified, prior to or immediately after passing the fix where the higher MEA is designated.

The source permits the climb to begin **immediately after** passing the fix — the aircraft does not need to already be at the higher MEA when crossing. The choice between "prior to" or "immediately after" is available; the staged answer eliminates the "immediately after" option and imposes a stricter requirement. This is a material misstatement of an operational rule.

**Fix:** Revise answer to: "The climb must begin prior to or immediately after crossing RIGEL." Distinguish clearly from the MCA case (4-5-6c2) where crossing at or above the MCA is required. Update the explanation to contrast the two subparagraphs.

---

### MAJOR — Question 4-6-4: Charted Pattern Requirements Conflated

**Item:** `questions.4-6-4.items[0]`

The question asks what must still be specified when a published holding pattern is charted. The correct answer says "The holding fix and direction of holding from the fix." But paragraph 4-6-1b2 states:

> When the assigned procedure or route being flown includes a charted pattern, you may omit all holding instructions except the charted holding direction and the statement "as published."

The holding fix is among the elements that **may be omitted** from holding instructions for charted patterns. The staged answer incorrectly requires both fix and direction, contradicting the charted-pattern exception. The question conflates 4-6-4's general holding-instruction content (which lists direction and fix) with 4-6-1b2's charted-pattern override (which reduces requirements to direction and "as published").

**Fix:** Either change the scenario to a non-charted holding pattern (keeping the current answer and dropping the charted-pattern framing from the stem), or update the correct answer to reflect 4-6-1b2: the charted holding direction and "as published." Clarify that the fix is the clearance limit, not part of holding instructions, for charted patterns.

---

## Minor Findings

### Flashcard 4-7-4 Item 0 — Extrapolated Restrictions

The back adds restrictions not in the source text ("turn to final, descent, and landing rollout"). Source 4-7-4a3 only addresses turns generally, and 4-7-4f addresses high-altitude approaches. Restrict the back to sourced provisions.

### Flashcard 4-6-4 — Incomplete Trigger Conditions

The back lists only "left turns" as a trigger for specifying turn direction, but 4-6-4e has three triggers: left turns, pilot request, or controller considers it necessary. Expand the back to cover all three.

### Activity 4-5-6 — Conservative Minimum Altitude

The correct answer uses 6,800 feet MSL as the lowest assignable altitude when the absolute regulatory minimum is the MOCA at 6,500 feet MSL. While operationally safe, the answer does not match the question's request for the "lowest assignable altitude." Align the answer with the MOCA or rephrase the question.

### Flashcard 4-5-1 — Overloaded Retrieval Target

The single card attempts to cover five distinct vertical-separation minima bands. Split into at least two cards: standard minima and exceptions.

### Flashcard 4-5-8 — Phraseology Order Inverted

The back presents "AT (fix)" before the distance/time forms, but the source lists distance/time first. Reorder to match the source.

### Flashcard 4-8-10 — Imprecise Item Count

The front states "five items" but item (e) is conditional ("if considered necessary"). Remove the count from the front or note the conditional status.

---

## Suggestions

- **Flashcard 4-5-6:** The back is operationally accurate but could be restructured to lead with the direct operational requirement before the terrain-clearance rationale.
- **Flashcard 4-2-5:** The front asks "what effort must be made" but the back describes the desired outcome. Minor front-back alignment improvement.
- **Flashcard 4-7-11:** The "six items" label masks the conditional structure (items 4/5/6 are alternatives depending on operation type). Restructure to reflect the universal-plus-alternative organization.

---

## Clean Items (No Defects Found)

The following 19 items passed all eight review criteria with no findings:

| Entity | Items |
|--------|-------|
| Questions | 4-5-2 (hemispheric rule), 4-6-1 (holding fix factors) |
| Activities | 4-6-4 (DME leg length), 4-6-7 (unmonitored NAVAID), 4-7-9 (transfer timing), 4-8-5 (approach altitude) |
| Flashcards | 4-1-1 (non-established route), 4-2-5 (NRP return), 4-5-7 (MAINTAIN cancels), 4-6-1 (holding factors), 4-6-6 (deviation conditions), 4-6-7 (protected course), 4-7-4[1] (change timing), 4-7-8 (weather adequacy), 4-7-9 (late transfer), 4-7-13 (ILS switch), 4-8-4 (military max altitudes), 4-8-7 (side-step), 4-8-8 (advisory frequency) |

These items exhibit strong operational framing, source-faithful content, plausible distractors, and context-sufficient explanations.

---

## Duplication Analysis

Cross-format reinforcement is benign. Flashcard 4-6-1 reinforces the same list as Question 4-6-1 in a different retrieval format — this is justified educational redundancy. Flashcard 4-7-9 correctly supersedes the earlier paragraph-scaffolded version per remediation guidance. No harmful duplication with existing content was found.

---

## Resolution Required

1. Fix flashcard 4-7-10 phraseology (critical).
2. Revise question 4-5-6 answer to match source 4-5-6c1 (major).
3. Align question 4-6-4 with charted-pattern rule in 4-6-1b2 (major).

After these three edits, the batch is safe to publish.
