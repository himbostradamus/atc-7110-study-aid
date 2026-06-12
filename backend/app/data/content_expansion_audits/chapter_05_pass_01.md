# Chapter 5 — Content Expansion Audit (Pass 1)

**Verdict: SAFE WITH FIXES**

No critical safety or rule errors found. Seven major cross-format duplication findings and
ten minor issues require attention before publication. All staged items are source-faithful
to FAA JO 7110.65BB.

---

## Audit Scope

- **Batch**: `chapter_05_pass_01.json`
- **Items reviewed**: 130 (71 questions, 18 activities, 41 flashcards)
- **Source packet**: `chapter_05.json` (paragraphs 5-1-1 through 5-14-9)
- **Prior remediation**: Addressed — paragraph-location scaffolding removed, answer
  position bias randomized (position distribution: 26%/25%/25%/25%)

---

## Major Findings

### 1. Direct duplication with existing curated content — 5-5-1 question
`questions.5-5-1.items[0]`

The staged question asks "To which aircraft must radar separation be applied according
to the application paragraph?" This is a near-verbatim restatement of an existing curated
question: "To which RNAV aircraft must radar separation be applied under 5-5-1?" Both
correct answers are textually identical. The scenario wrapper ("according to the
application paragraph") adds no assessment depth beyond the existing item.

**Action**: Replace with a question testing a different dimension of 5-5-1 — e.g.,
the point-to-point impromptu route exception, or the conditions in subparagraph b for
applying radar separation between identified and non-identified aircraft.

### 2. Cross-format duplication — question↔flashcard pairs

Six paragraph groups have questions and flashcards that test identical operational
facts with only wrapper-format differences:

| Paragraph | Duplicated Content |
|-----------|-------------------|
| 5-2-12 | Transponder malfunction downstream notification |
| 5-2-22 | ADS-B inoperative OS/CIC notification elements |
| 5-4-8 | Three required conditions for AIT |
| 5-13-7 | Prohibition on coast tracks for separation |
| 5-3-2 | Two requirements for departing aircraft identification |
| 5-5-3 | Mandatory traffic advisories and safety alerts during target resolution |

In each case, the question and flashcard test the same fact, reducing the marginal
learning value of the second format. Cross-format coverage is valuable only when
each format tests a distinct retrieval dimension of the paragraph.

**Action**: For each pair, retain the more effective format and redesign the other
to test a different aspect of the same paragraph.

### 3. Flashcard overload — 5-5-9
`flashcards.5-5-9.items[0]`

The flashcard back encodes **five independent retrieval targets**:
- 3 miles (<40 NM from antenna)
- 5 miles (≥40 NM from antenna)
- 3 miles (single sensor MSSR <60 NM)
- 3 miles (FUSION target symbol)
- 5 miles (FUSION with ISR displayed)

A flashcard should target one coherent fact or a short required-list sequence. Five
independent minima invite partial-recall errors and defeat the purpose of single-target
retrieval practice.

**Action**: Split into separate cards per sensor-mode/range combination, or collapse
to a card testing only the primary <40 NM / ≥40 NM distinction.

---

## Minor Findings

### Source Fidelity

1. **5-9-1 question** (`questions.5-9-1.items[0]`): Scenario uses "visibility is
   unrestricted" instead of the source threshold "visibility is at least 3 miles."
   Replace with exact source language.

2. **5-12-10 question** (`questions.5-12-10.items[0]`): Correct answer says "tell the
   aircraft to execute a missed approach" but the prescribed procedure is to "tell the
   aircraft to take over visually *or if unable*, to execute a missed approach." The
   conditional structure of the prescribed transmission is lost.

### Answer Cues

3. **5-1-1 question** (`questions.5-1-1.items[0]`): Correct answer is substantially
   longer (~180 chars) than distractors (~75 chars avg).

4. **5-2-15 question** (`questions.5-2-15.items[0]`): Correct answer (~160 chars) is
   more qualified than shorter single-clause distractors.

5. **5-5-10 question** (`questions.5-5-10.items[0]`): Correct answer is the only
   choice with a two-clause if/but structure, creating a structural cue independent
   of content.

### Educational Value

6. **5-2-1 flashcard** (`flashcards.5-2-1.items[0]`): Tests a terminology label
   ("common military/civil mode") rather than operational decision-making knowledge.

7. **5-14-5 flashcard** (`flashcards.5-14-5.items[0]`): Tests obscure format
   specification (two-letter vs. three-letter ICAO designators) with no operational
   controller action.

### Context Sufficiency

8. **5-4-9 flashcard** (`flashcards.5-4-9.items[0]`): Back conflates the operational
   rule with an external FAA Order reference and a prohibitive restatement, making
   the retrieval target ambiguous.

9. **5-2-11 activity** (`activities.5-2-11.items[0]`): Scenario describes VFR
   targets visible in "Class A airspace only," which is operationally contradictory
   (VFR is prohibited in Class A). Clarify or restructure.

10. **5-9-7 activity** (`activities.5-9-7.items[0]`): Scenario omits runway
    centerline spacing, which is a key fact affecting applicable separation minima
    for simultaneous independent approaches.

---

## Patterns Observed

### Resolved (from prior remediation)
- **Paragraph-location scaffolding**: No staged items reference paragraph numbers in
  learner-facing text. ✓
- **Answer-position bias**: Correct answers are evenly distributed across all four
  positions (26%/25%/25%/25%). ✓
- **Negative stems**: None found in staged questions. ✓

### Persistent (needs attention)
- **Answer-length cues**: Approximately 15% of correct answers remain
  conspicuously longer or more qualified than distractors. This is inherent to
  operational nuance but should be mitigated by expanding distractor specificity.
- **Cross-format paraphrasing**: When a paragraph has both a question and a
  flashcard, they often test the same content. A systematic review of
  question↔flashcard pairs across all chapters would identify this at scale.

### New (not in prior remediation)
- **Existing-content overlap**: The staging generator produced at least one item
  (5-5-1) that directly mirrors an existing curated question. The expansion
  generation should cross-check against existing item banks to avoid re-creating
  already-covered items.

---

## Source Fidelity Summary

All 130 items were reviewed against source text from the chapter_05 packet. Key
operational minima, phraseology, exception conditions, and procedural sequences
were verified for:

- 5-1-1: Personal satisfaction requirement, OS/CIC vs. adjacent notification ✓
- 5-1-2: Three secondary-radar sole-source conditions, terminal ASR restriction ✓
- 5-1-4: Merging target criteria, vertical separation exception ✓
- 5-1-5: Outer fix surveillance trigger ✓
- 5-1-8: Position report request authority, compulsory reporting triggers ✓
- 5-2-1: Beacon code assignment criteria, transponder requirement ✓
- 5-2-10: Standby instruction conditions ✓
- 5-2-11: VFR code monitoring exceptions ✓
- 5-2-14: Withdrawal of transponder failure approval ✓
- 5-2-15: Mode C validation triggers, ERAM exception, 300-ft threshold ✓
- 5-2-16: Mode C altitude confirmation exceptions ✓
- 5-2-17: Non-Mode C altitude confirmation exceptions, USA reconfirmation ✓
- 5-3-4: Auto-acquired aircraft identification conditions ✓
- 5-4-8: AIT three conditions ✓
- 5-5-1: Radar separation application scope ✓
- 5-5-10: Adjacent airspace boundary minima ✓
- 5-5-11: EAS edge-of-scope minima ✓
- 5-8-4: Departure-arrival separation, 40NM threshold ✓
- 5-9-1: Approach gate intercept minima, weather exception ✓
- 5-12-10: PAR elevation failure procedure ✓
- 5-13-2: E-MSAW caution about adjacent MIA areas ✓
- 5-13-7: Coast track separation prohibition ✓

No factual errors were found.

---

## Publication Recommendation

**Verdict: SAFE WITH FIXES**

The content is safe to publish after addressing the seven major findings (one
existing-content duplication and six cross-format duplications) and the ten minor
findings. The critical remediation gate — source fidelity — is fully met. The major
findings affect educational efficiency (duplicated items waste learner time) but
do not introduce unsafe content.

Priority order for fixes:
1. Resolve 5-5-1 existing-content duplication (replace question)
2. Resolve six cross-format duplications (redesign one format per pair)
3. Split 5-5-9 flashcard into individual retrieval targets
4. Address answer-length cues in 5-1-1, 5-2-15, 5-5-10
5. Fix imprecise language in 5-9-1 and 5-12-10
6. Replace or remove low-educational-value flashcards (5-2-1, 5-14-5)
7. Clarify contradictory scenarios (5-2-11, 5-9-7 activities)
8. Simplify ambiguous flashcard backs (5-4-9)
