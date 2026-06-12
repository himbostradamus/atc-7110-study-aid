# Chapter 12 Content Expansion Audit — Pass 01

**Verdict: SAFE WITH FIXES**

One major finding (grammatically forced fill_blank in 12-1-6) must be addressed
before publication. Four minor findings cover answer-length cueing, ambiguous
distractor labeling, and internal duplication. No critical (false/unsafe) issues
found. All 25 items were reviewed.

---

## Major Findings

### 1. `questions.12-1-6.items[0]` — Grammatically forced fill_blank does not test operational knowledge

**Severity:** major | **Category:** educational_value

The stem reads:

> In Canadian airspace, do _____ authorize parachute jumping without prior
> permission from the appropriate Canadian authority.

The answer is `not`. This is the only word that completes `do _____ authorize`
as a grammatical English sentence. A student who has never read Chapter 12 can
fill this blank from English grammar alone. The item tests syntactic
pattern-matching, not the absolute prohibition against authorizing parachute
jumping without Canadian permission.

**Recommendation:** Rewrite as a multiple_choice question. For example: *"A pilot
requests parachute-jumping approval in delegated Canadian airspace. No prior
permission from any Canadian authority exists. What must the controller do?"*
with distractors representing plausible-but-incorrect local-authorization
responses.

---

## Minor Findings

### 2. `questions.12-1-2.items[2]` — Answer-length cue on Class F definition

The correct answer is the verbatim Class F definition (~36 words) while
distractors range from 12 to 21 words. The correct answer is approximately 1.7×
longer than the longest distractor and 3× longer than the shortest, creating a
conspicuous answer-length cue.

**Recommendation:** Trim the correct answer to distractor parity, or expand the
three shorter distractors.

### 3. `activities.12-1-4.items[0]` — Two choices share the label "Vertical separation"

Choices 1 and 4 both begin "Vertical separation —" and are distinguished only
by their implementation clauses. Choice 1's implementation (deny the climb)
does not actually exercise vertical separation to resolve the request. The
identical lead labels create ambiguity about what the item tests.

**Recommendation:** Rename the two choices by action: e.g., *"Deny the climb and
maintain existing vertical separation"* versus *"Manage the climb while ensuring
1,000 ft vertical separation throughout."*

### 4. `flashcards.12-1-7.items[0]` — Duplicates `questions.12-1-7.items[0]` within the same batch

Both items test the SVFR time-period specification requirement (`period of
time`). The flashcard front is a near-paraphrase of the fill_blank stem. Having
both in the same pass means the learner encounters two nearly identical prompts
targeting the same atomic fact.

**Recommendation:** Retain the fill_blank and rescope the flashcard to test a
different SVFR concept (e.g., the dual-factor criterion when no controller is on
duty, or the helicopter 1/2-mile minimum).

---

## Suggestions

### 5. `questions.12-1-2.items[1]` — Single-preposition fill_blank (`prior`)

The fill_blank tests the word `prior` in the Class D two-way communications
rule. While the timing requirement is operationally significant, a single
grammatical-function-word blank provides minimal retrieval depth. Consider
converting to an MC question contrasting Class C/D/E VFR entry requirements.

### 6. `questions.12-1-1.items[0]` — Single-adverb fill_blank (`formally`)

Tests the qualifier `formally` on the delegation prerequisite. Narrow but the
explanation justifies its operational significance well. Acceptable as-is if a
low-difficulty item is needed for this paragraph.

### 7. `flashcards.12-1-1.items[0]` — Duplicates existing database question on entity name

The flashcard front asks for the Transport Canada Aviation Group — the same
entity name already tested by an existing fill_blank question in the database.
Consider replacing with a flashcard targeting a less-redundant retrieval concept
from 12-1-1.

---

## Summary of Patterns

### Strengths

- **No paragraph-location scaffolding.** All 25 stems establish operational
  context without referencing paragraph or note numbers — the remediation
  guidance was followed completely.
- **Source fidelity is consistently correct.** No item teaches a false
  procedure, incorrect minimum, or wrong phraseology.
- **MC answer positions are well distributed** across positions 1–4 in the
  question set.
- **Explanations address misconceptions.** Most explanations name and correct
  the strongest wrong assumption rather than restating the right answer.
- **Canada-U.S. differences are highlighted** where applicable (night SVFR
  qualification, Class F airspace, 1,000-on-top vs. VFR-on-top).
- **Activities test multi-condition decisions.** The 1,000-on-top scenario tests
  both conditions simultaneously (pilot request + airspace restriction); the
  helicopter SVFR scenario integrates the 1/2-mile minimum with the
  controller-on-duty criterion.

### Recurring Issues

- **Narrow single-word fill_blanks.** Five fill_blank items test single words
  (`formally`, `IFR`, `prior`, `higher`, `10`). Most are defensible because
  the tested word carries operational weight — the exception is `not` in 12-1-6
  (see major finding above).
- **One answer-length cue** in `questions.12-1-2.items[2]` where the correct
  answer is verbatim source text and 1.7–3× longer than distractors.
- **One internal cross-format duplication** within the batch (12-1-7 time-period
  specification appears as both fill_blank and flashcard).

---

## Item Coverage Summary

| Paragraph | Questions | Activities | Flashcards | Total |
|-----------|-----------|------------|------------|-------|
| 12-1-1    | 1         | 1          | 1          | 3     |
| 12-1-2    | 4         | 1          | 2          | 7     |
| 12-1-3    | 1         | 1          | 1          | 3     |
| 12-1-4    | 1         | 1          | 0          | 2     |
| 12-1-5    | 2         | 1          | 1          | 4     |
| 12-1-6    | 1         | 0          | 1          | 2     |
| 12-1-7    | 2         | 1          | 1          | 4     |
| **Total** | **12**    | **6**       | **7**       | **25** |

All 25 items were reviewed — no sampling. Every item path appears exactly once
in the JSON report's `reviewed_item_paths`.
