# Chapter 10 Content Expansion Audit — Pass 1

**Verdict: SAFE WITH FIXES**

**Scope:** 43 questions, 13 activities, 32 flashcard groups (96 individual items) across all 10-x-x paragraphs covered by `chapter_10_pass_01.json`.

**Date:** 2026-06-11

---

## Critical Findings

*None.*

---

## Major Findings

### 1. `questions.10-2-1.items[0]` — Incorrect source attribution (source_fidelity)

The question about when a controller may begin assistance after partial information is received cites "the note to 10-2-1b" as authority. There is no subparagraph 10-2-1b. The relevant authorities are:

- **10-2-1a body** — "Start assistance as soon as enough information has been obtained upon which to act" (the primary authority for the timing question)
- **Note 1 to 10-2-1** — "Emergency Autoland systems may not provide all of the required information" (supporting authority about system limitation, not controller timing)

The explanation conflates these two distinct authorities and uses a non-existent paragraph reference. The answer is correct and the scenario is well-constructed, but the source citation is materially wrong and could mislead learners about which paragraph element controls.

**Fix:** Revise the explanation to cite 10-2-1a body text as primary authority, reference "Note 1 to 10-2-1" (not "note to 10-2-1b") as supporting authority.

---

### 2. `questions.10-3-6.items[0]` — Underspecified scenario (context_sufficiency)

The scenario asks whether the controller should provide a rough initial position when formal radar data extraction will take "approximately 10 minutes." The rule (10-3-6b) requires using any available method "if necessary to prevent an undue delay." Whether 10 minutes constitutes "undue delay" depends on operational context the stem does not provide — a student who answers "Wait 10 minutes for precise data" has a reasonable argument without additional facts such as imminent SAR launch, passed fuel exhaustion, or an RCC request for immediate coordinates.

**Fix:** Add scenario facts establishing urgency (e.g., "the RCC has requested immediate coordinates to initiate SAR operations" or "the aircraft's estimated fuel exhaustion time passed 15 minutes ago").

---

## Minor Findings

### Source Fidelity

| Item | Issue |
|------|-------|
| `questions.10-2-18.items[0]` | Explanation attributes ash-ingestion risk rationale to "turbine-powered aircraft" generically; the source note to 10-2-4 ties this mechanism specifically to high-bypass turbofan engines. While the literal rule covers turboprops, the explanation's physical rationale creates a minor tension. |
| `flashcards.10-1-1.items[0]` | Card back uses parallel "preferably repeated" language for both Mayday and Pan-Pan. The source uses "preferably" (advisory) for Mayday and "should be used" (stronger) for Pan-Pan — a minor asymmetry the card flattens. |
| `activities.10-4-3.items[0]` | Explanation states "unanimous concurrence is required" but the source says "if the operators or pilots of other aircraft concur." "Unanimous" is a reasonable interpretive reading of the plural wording, not the source's explicit term. |

### Context and Sufficiency

| Item | Issue |
|------|-------|
| `questions.10-1-7.items[0]` | The 1,500 ft scenario creates correct tension between the minimize-transmissions rule and the position-request exception, but the stem could explicitly state this is a "low altitude" situation to make the rule's emphasis clearer. |

### Educational Value and Format

| Item | Issue |
|------|-------|
| `activities.10-2-17.items[0]` | Correct answer length (~250 chars) materially exceeds distractor lengths (87–175 chars), creating a detectable non-content cue. |
| `flashcards.10-2-5.items[0]` | The first-half trigger card (items a-d) does not mention the USAF exception, which is stated before the enumerated triggers in the source. A learner recalling four triggers without the USAF caveat could misapply the rule. |
| `flashcards.10-2-6.items[0]` | Asks for two distinct phraseology strings with different format specifications on a single card, pushing against single-retrieval-target guidance. Consider splitting into two single-phraseology cards. |

### Scope and Loading

| Item | Issue |
|------|-------|
| `flashcards.10-2-9.items[1]` | Groups subparagraphs (e), (f), and (g). Subparagraph (g) has two facility-type subparts (TERMINAL/EN ROUTE), bringing the effective retrievables to 4 items in prose — at the upper edge of scope guidance. |

### Duplication / Cross-Format

| Item | Issue |
|------|-------|
| 8 paragraph groups | Multiple paragraphs (10-1-1, 10-1-2, 10-2-1, 10-2-2, 10-2-4, 10-2-5, 10-2-9, 10-3-5) test the same fact in both a question and a flashcard at the same retrieval depth. For example, 10-2-2's "change frequency only for a valid reason" rule appears as both `questions.10-2-2.items[0]` and `flashcards.10-2-2.items[0]` with near-identical content. The remediation guidance calls for different retrieval modes across formats — a conceptual question and a procedural flashcard should test complementary angles of the same source paragraph, not the same fact. |

---

## Suggestions (Not Blocking Publication)

- `questions.10-4-1.items[0]`: The correct answer embeds the operational rationale ("to ensure traffic protection until the latest reasonable arrival time") while distractors lack comparable rationale clauses. Consider stripping the rationale from the answer and placing it in the explanation, or adding comparable (incorrect) rationale clauses to distractors.
- `questions.10-4-4.items[1]`: The explanation could be strengthened by noting the escalating observability logic of the transponder request sequence — IDENT tests basic response, 7600 tests code-change compliance, stand-by tests target disappearance.
- `activities.10-2-19.items[0]`: Only one item covers 10-2-19 (Public Health Reporting). Consider adding a flashcard or MC question to cover the seven required information items the controller must obtain, complementing the reporting-path activity.
- **IMO vs. IMC terminology**: Two items use "IMC" as shorthand while the source text uses "IFR conditions" or procedural descriptions. Though widely understood, consistent source-aligned terminology is preferable.

---

## Patterns Summary

1. **Remediation compliance is strong.** All format corrections mandated by the chapter-level remediation have been applied: no fill-in-blank items, no paragraph-location scaffolding in stems, passable answer-position randomization.

2. **Cross-format paraphrasing (8 paragraph groups).** The most prevalent quality issue is same-fact coverage across questions and flashcards at the same retrieval depth. This represents a missed opportunity for complementary retrieval modes. In each case, either the question or the flashcard should be adjusted to test a different aspect of the same source paragraph.

3. **Explanation quality is generally good** — explanations cite source paragraphs and explain the rule rather than just restating the answer. Two explanations could be pedagogically strengthened (10-4-4 transponder logic, 10-6-x oceanic framework differences).

4. **Flashcard scope is well-managed.** The remediation's split of overloaded cards was effective. The 32 flashcard groups are predominantly 2-4 items each, with appropriate concept/procedure/phraseology typing. Minor loading concerns affect only 3 cards.

5. **Activity scenarios are operationally rich.** The situation_action activities present concrete ATC situations with specific aircraft types, altitudes, times, and conditions — the scenarios require application rather than recognition.

---

## Item Counts by Severity

| Severity | Count |
|----------|-------|
| Critical | 0 |
| Major | 2 |
| Minor | 12 |
| Suggestion | 4 |

---

## Publication Recommendation

**SAFE WITH FIXES** — The two major findings require resolution before publication. The 12 minor findings are quality improvements that could be addressed in a subsequent pass or accepted as-is with reviewer acknowledgment. All 96 staged items are pedagogically sound, source-faithful at the rule level, and free of the systematic defects identified in the chapter-level remediation.
