# Chapter 2 Content Expansion Audit — Pass 1

**Verdict: SAFE WITH FIXES**

**Batch:** `backend/app/data/content_expansion_staging/chapter_02_pass_01.json`
**Items reviewed:** 103 (41 questions, 22 activities, 40 flashcards)
**Report:** `backend/app/data/content_expansion_audits/chapter_02_pass_01.json`

---

## Summary

Chapter 2 pass 1 is a well-constructed expansion batch. The questions present realistic, multi-factor operational scenarios (converging aircraft + advisory request, altitude conflict + fuel leak, clip-sector coordination). Flashcard fronts generally provide adequate operational context. The batch demonstrates strong source fidelity — all verified answer keys align with FAA JO 7110.65 source text.

One critical defect (garbled activity situation text) and seven major findings (pedantic trivia, strip-marking trivia, cross-format duplication, low-value list-comparison tasks) require resolution before publication. An additional pattern of minor explanation scaffolding affects ~12 items but does not block publication.

**Strengths:**
- Operational scenario design consistently tests decision-making, not paragraph-location recall
- No "Under 2-X-X" scaffolding in question stems or flashcard fronts (unlike existing curriculum)
- TCAS/TAWS content (2-1-28, 2-1-30) has strong cross-format coverage
- Distractors are plausible, parallel, and free of obvious answer-length cues
- MARSA content (2-1-11) correctly emphasizes ATC's limited role and military command prerogative

---

## Critical Findings

### 1. activities.2-4-19.items[0] — Broken Situation Text

**Category:** content_integrity

The situation field contains an unresolved editorial aside embedded mid-sentence:

> "Columbus, Mississippi has both a civil airport (Columbus AFB — actually Columbus AFB is a military installation) and the city of Columbus has both the Air Force Base and Golden Triangle Regional Airport."

The parenthetical remark reads as an author's working note that was never resolved. The sentence is also redundant and confusing. Learners cannot parse the intended scenario from this text.

**Recommended fix:** Rewrite the situation field with clean, unambiguous text. The underlying facility-naming rule tested (military service name precedes facility name when similar-named airports exist in the same area) is correct per 2-4-19a.

---

## Major Findings

### 2. activities.2-4-16.items[0] — Tests Orthographic Spelling, Not Operational Phonetics

**Category:** educational_value

The activity discriminates correct from incorrect based on the written spelling of "Juliett" (double-t) vs. "Juliet" (single-t), citing TBL 2-4-1. ICAO phonetic spelling is an orthographic convention from a reference table, not an operational ATC skill — controllers pronounce phonetics, they do not spell them. Testing spelling recall violates the remediation directive to de-emphasize "abbreviation recall from reference tables."

**Recommended fix:** Replace with an activity that tests operational phonetic pronunciation or application (e.g., distinguishing similar-sounding ICAO letters on a noisy frequency).

### 3. flashcards.2-3-2.items[0] — Strip-Marking Trivia

**Category:** educational_value

The card asks "What information is recorded in block 26 of the en route flight progress strip?" Answer: "Sector/position number." This tests which numbered block holds which datum — pure strip-marking trivia. The remediation guidance explicitly directs: "De-emphasize strip-marking trivia." A controller needs to know *what* to record and *why*, not which numbered block.

**Recommended fix:** Rephrase to test the operational purpose: "What entry supports identification of the controlling position for recorded transmissions?" with the answer referencing both the purpose and the block number as secondary information.

### 4. activities.2-9-2.items[0] + flashcards.2-9-2.items[0] — Cross-Format Duplication

**Category:** duplication

The activity and flashcard for 2-9-2 test the identical ATIS recoding rule: a new recording must be made upon receipt of any new official weather regardless of value changes. Both present substantially overlapping answer text. The existing curriculum also contains a fill_blank question covering the same rule. Three items testing one fact across formats is unnecessary duplication that reduces per-item learning value.

**Recommended fix:** Retain one item (the flashcard is the better format for this single-fact retrieval). Remove or rewrite the activity to test a different ATIS operating procedure from 2-9-2 (e.g., pilot ATIS-code confirmation procedures, or "new ATIS current" broadcast requirements).

### 5. activities.2-2-14.items[0] — List-Comparison Trivia

**Category:** educational_value

The question asks which message category appears in the Canadian ACC transmission list but not in the U.S. list. Answer: "Departure messages." This tests the learner's ability to compare two administrative lists — a document-structure task with no transferable operational skill. The answer is factually correct per 2-2-14 but educationally empty.

**Recommended fix:** Replace with an operational scenario testing the same Canada-US coordination concept (e.g., "A flight departs Toronto entering U.S. airspace. Who forwards the flight plan data to the receiving U.S. ARTCC?" — testing the 2-2-13 rule).

### 6. flashcards.2-2-10.items[0] — Infrastructure Trivia

**Category:** educational_value

The card tests the specific NADIN forwarding threshold: "when the route exceeds 20 elements external to the originating ARTCC's area." The 20-element threshold is a system-implementation artifact — controllers do not count route elements; automation handles NADIN routing. Testing this numeric threshold tests infrastructure trivia rather than operational decision-making.

**Recommended fix:** Reframe around the operational principle: "Under what condition must NADIN be used to forward flight plan data regardless of Computer B network status?" The 20-element detail becomes part of an operational concept rather than the sole retrieval target.

---

## Minor Findings (Pattern: Explanation Scaffolding)

Twelve items use "the source paragraph" / "the source paragraph requires" / "the source paragraph(5)" in their explanations. While less harmful than question-stem paragraph references, this phrasing anchors learner understanding to document structure rather than operational rules. Affected items:

| Item | Explanation Issue |
|------|------------------|
| questions.2-1-6.items[0] | "the source paragraph permits discontinuation..." |
| questions.2-1-10.items[0] | "the source paragraph(5) requires..." |
| questions.2-1-14.items[0] | "the source paragraph requires..." |
| questions.2-1-15.items[0] | "the source paragraph requires..." |
| questions.2-1-17.items[0] | "the source paragraph lists..." |
| questions.2-1-20.items[0] | "the source paragraph(3) specifically requires..." |
| questions.2-1-22.items[0] | "the source paragraph states..." |
| questions.2-1-24.items[0] | "the source paragraph states..." |
| questions.2-1-27.items[0] | "the source paragraph states..." |
| activities.2-1-5.items[0] | "the source paragraph requires...the source paragraph says..." |
| activities.2-1-7.items[0] | "the source paragraph requires..." |
| activities.2-1-21.items[0] | "the source paragraph specifies..." |

**Recommended fix:** Remove "the source paragraph" preamble from all affected explanations. State the rule directly: "Per paragraph 2-1-6..." or better, "When a pilot confirms corrective action is underway..." — operational framing without document anchoring.

### Other Minor Findings

**questions.2-1-25.items[0]** — Tests military-branch scope (USAF exclusion from 2-1-25) rather than the operational triggers for the wheels-down check. Factually correct (source heading is "USA/USN") but the educational value lies in the timing rule, not the branch exclusion.

**flashcards.2-4-17.items[0]** — Tests heading 090 pronunciation ("Zero Niner Zero"). The existing 2-4-17 curriculum already covers number pronunciation extensively. This specific heading example is close duplication with existing content.

---

## Suggestions (Not Publication-Blocking)

**flashcards.2-1-29.items[0]** — Lists 5 non-RVSM aircraft categories. The retrieval scope is large but defensible since the complete set is operationally meaningful. Optional: group by category type to aid memory encoding.

**flashcards.2-1-30.items[0]** — Lists 3 TAWS resumption conditions. Consider clarifying the "OR" relationship on the card back: "Any ONE of these three conditions resumes responsibility."

**flashcards.2-6-2.items[0]** — Wind shear PIREP classification threshold. Consider adding a brief rationale on the back explaining why 10 knots is the UUA threshold.

---

## Items Passed Without Findings

The following 83 items were reviewed and found free of defects at the minor severity level or above:

**Questions (28):** 2-1-1, 2-1-2, 2-2-2, 2-2-4, 2-2-6, 2-2-9, 2-2-13, 2-2-15, 2-3-3, 2-3-5, 2-3-7, 2-4-1, 2-4-3, 2-4-5, 2-4-6, 2-4-8, 2-4-12, 2-4-14, 2-4-18, 2-4-20, 2-4-22, 2-5-1, 2-5-3, 2-6-1, 2-6-4, 2-6-5, 2-7-1, 2-7-3, 2-8-1, 2-9-1, 2-9-3, 2-10-1, 2-10-3

**Activities (13):** 2-1-1, 2-1-3, 2-1-11, 2-1-23, 2-1-26, 2-1-28, 2-1-30, 2-2-7, 2-2-11, 2-3-9, 2-4-9, 2-4-11, 2-6-3, 2-6-6, 2-8-2

**Flashcards (30):** 2-1-1, 2-1-2, 2-1-4, 2-1-8, 2-1-9, 2-1-12, 2-1-13, 2-1-16, 2-1-18, 2-1-19, 2-1-23, 2-1-31, 2-2-1, 2-2-3, 2-2-5, 2-2-8, 2-2-12, 2-3-1, 2-3-4, 2-3-8, 2-4-2, 2-4-4, 2-4-7, 2-4-10, 2-4-13, 2-4-15, 2-4-21, 2-5-2, 2-7-2, 2-8-3, 2-10-1, 2-10-2, 2-10-3

---

## Publication Checklist

- [ ] **Critical:** Fix garbled situation text in activities.2-4-19.items[0]
- [ ] **Major:** Replace pedantic ICAO spelling activity (activities.2-4-16.items[0])
- [ ] **Major:** Reframe strip-marking flashcard (flashcards.2-3-2.items[0])
- [ ] **Major:** Resolve ATIS recoding duplication (activities.2-9-2.items[0] or flashcards.2-9-2.items[0])
- [ ] **Major:** Replace list-comparison activity (activities.2-2-14.items[0])
- [ ] **Major:** Reframe NADIN trivia flashcard (flashcards.2-2-10.items[0])
- [ ] **Minor:** Remove "the source paragraph" scaffolding from 12 explanations
- [ ] **Minor:** Consider reframing questions.2-1-25 for operational value
- [ ] **Minor:** Review flashcards.2-4-17 for duplication with existing content

After these fixes, revalidate with `scripts/validate_content_expansion_audit.py` before publication.
