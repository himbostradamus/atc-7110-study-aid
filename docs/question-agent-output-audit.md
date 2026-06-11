# Question-Agent Output Audit

Sources audited: `question_agent`

## Corpus Summary

- Questions: 1544
- Paragraphs represented: 614
- Question types: {"fill_blank": 397, "multiple_choice": 1115, "true_false": 32}
- Retrieval modes: {"cloze": 397, "condition": 367, "direct_recall": 72, "discrimination": 1, "numeric": 397, "responsibility": 2, "scenario": 276, "verification": 32}
- Correct-answer positions: {"0": 402, "1": 482, "2": 170, "3": 61}
- Retrieval modes per paragraph: {"1": 296, "2": 167, "3": 111, "4": 37, "5": 3}

## Recurring Pitfalls

- 1063 questions include unnecessary paragraph or note-location scaffolding.
- 17 questions use context-light references such as “this paragraph” or “this rule.”
- 195 use negative framing (`NOT`, `EXCEPT`, or equivalent).
- 22 have explanations shorter than ten words.
- 5 within-paragraph pairs have at least 0.78 token similarity.

## Essential-Element Coverage

- Heuristic essential statements found: 3873
- Statements matched by agent questions: 1490
- Estimated coverage: 38.5%

This extracts imperative, conditional, and numeric source statements and checks overlap with each question, correct answer, and explanation. It is a triage signal, not a legal determination.

## Repetition Versus Variety

- Repeated concept groups: 10
- Repeated groups using only one retrieval mode: 6
- Paragraphs with at least three retrieval modes: 151

Healthy reinforcement asks the same concept through different cognitive operations. Rewording a direct-recall stem without changing the retrieval task is duplication.

## Chapter Pattern

| Chapter | Questions | Paragraphs | Location scaffold | Negative stems |
| --- | ---: | ---: | ---: | ---: |
| 1 | 51 | 17 | 43 | 6 |
| 2 | 202 | 99 | 173 | 27 |
| 3 | 178 | 94 | 86 | 23 |
| 4 | 195 | 62 | 8 | 21 |
| 5 | 213 | 115 | 84 | 25 |
| 6 | 85 | 22 | 67 | 14 |
| 7 | 94 | 45 | 92 | 15 |
| 8 | 109 | 45 | 108 | 12 |
| 9 | 163 | 41 | 162 | 14 |
| 10 | 78 | 30 | 72 | 10 |
| 11 | 33 | 3 | 27 | 5 |
| 12 | 29 | 7 | 27 | 2 |
| 13 | 70 | 24 | 70 | 17 |
| 14 | 44 | 10 | 44 | 4 |

## Common Stem Openings

- `under <para>, what is the`: 50
- `under <para>, which of the`: 25
- `under <para>, how does the`: 9
- `under <para>, what must the`: 9
- `under <para>, what must be`: 8
- `which of the following is`: 8
- `under <para>, what must a`: 7
- `under <para>, what are the`: 6
- `under <para>, who is responsible`: 5
- `what is the difference between`: 4
- `under <para>, when a pilot`: 4
- `under <para>, what type of`: 4

## Highest-Priority Remediation

1. Remove paragraph-number scaffolding unless the task is explicitly source navigation.
2. Define each paragraph’s essential obligations, conditions, exceptions, minima, and prescribed wording before writing.
3. Build concept families deliberately: recall, condition/exception discrimination, scenario, and exact recall only where fidelity matters.
4. Prefer positive operational decisions over `NOT/EXCEPT` stems.
5. Require explanations to state the controlling principle and why the strongest distractor fails.

## Example Location-Dependent Questions

- `1-1-1`: Under 1-1-1, what are controllers required to do if they encounter situations not covered by this order?
- `1-1-1`: Under 1-1-1, which provisions of this order are controllers required to be familiar with?
- `1-1-10`: Under 1-1-10, which of the following correctly describes the relationship between an LOA and FAA Order JO 7110.65 minima?
- `1-1-10`: Under 1-1-10, which procedures or minima trigger the requirement for a letter of agreement?
- `1-1-11`: Under 1-1-11, a waiver request involves military operations. The facility supervisor obtains FAA regional approval first, then notifies the military headquarters after the waiver is approved. Is this the correct sequence?
- `1-1-11`: Under the Terminal note in 1-1-11, who approves USAF procedures or minima differing from the order and involving military aircraft only?
- `1-1-12`: Under 1-1-12, what are all ATO employees expected to do beyond simply maintaining safety in the NAS?
- `1-1-12`: Under 1-1-12, which of the following is NOT listed as a way to obtain additional ATO SMS information?
- `1-1-13`: Under 1-1-13, a facility is physically located in the Eastern region but its service area office is in the Central region. The facility needs to contact a non-ATO FAA office. Which region is correct?
- `1-1-13`: Under 1-1-13, when contacting a non-ATO FAA regional office, which region determines the correct contact?
- `1-1-13`: Under 1-1-13, which examples are given of FAA regional office organizations that are not part of the Air Traffic Organization?
- `1-1-14`: Under 1-1-14a, which of the following is listed as a recipient of this order distribution?

## Example Near-Duplicates

- `4-1-1` (1.00): “For a T-class VOR, VORTAC, or TACAN, the normal usable altitude band is _____ with a usable radius distance of _____ miles.” / “For an L-class VOR, VORTAC, or TACAN, the normal usable radius distance is 40 miles. What is the altitude band?”
- `6-5-4` (0.92): “Under 6-5-4b, when a course change is 16 through 90 degrees, what overflown-side protection applies at FL180 to FL230 inclusive?” / “Under 6-5-4c, when a course change is 91 through 180 degrees at FL180 to FL230 inclusive, what overflown-side protection applies?”
- `5-9-2` (0.86): “If deviations from the final approach course are observed after initial course interception and the aircraft is INSIDE the approach gate, what should the controller do?” / “If deviations from the final approach course are observed after initial course interception and the aircraft is OUTSIDE the approach gate, what should the controller do?”
- `4-1-5` (0.81): “When an unpublished fix is located beyond 45 NM from the NAVAID generating the off-course radial, the minimum divergence angle must increase at what rate?” / “When an unpublished fix is located over 30 NM from the NAVAID generating the off-course radial, the minimum divergence angle must increase at _____ up to 45 NM.”
- `4-1-5` (0.79): “When an unpublished fix is located over 30 NM from the NAVAID generating the off-course radial, the minimum divergence angle must increase at _____ up to 45 NM.” / “An unpublished fix is located 40 NM from the NAVAID generating the off-course radial. What is the minimum divergence angle?”

## Lowest Estimated Essential-Element Coverage

- `8-9-3`: 0/30 (0%), 1 questions
- `8-10-3`: 0/28 (0%), 1 questions
- `8-7-3`: 0/26 (0%), 1 questions
- `2-10-1`: 0/20 (0%), 2 questions
- `2-9-3`: 0/17 (0%), 1 questions
- `3-10-5`: 0/14 (0%), 1 questions
- `2-9-2`: 0/13 (0%), 1 questions
- `2-10-3`: 0/10 (0%), 1 questions
- `3-10-12`: 0/9 (0%), 1 questions
- `3-10-13`: 0/8 (0%), 1 questions
- `3-12-3`: 0/8 (0%), 1 questions
- `3-9-10`: 0/8 (0%), 1 questions
- `4-2-8`: 0/8 (0%), 1 questions
- `8-7-4`: 0/8 (0%), 1 questions
- `2-3-3`: 0/7 (0%), 3 questions
