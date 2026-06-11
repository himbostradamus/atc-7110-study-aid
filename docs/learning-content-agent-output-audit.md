# Learning-Content Agent Output Audit

Sources audited: `question_agent`

## Corpus Summary

- Questions: 1544 across 614 paragraphs.
- Flashcards: 1343 across 624 paragraphs.
- Activities: 325 across 255 paragraphs.
- Paragraphs represented by all three formats: 224 of 652.

## Cross-Format Essential-Element Coverage

- Heuristic essential statements in represented paragraphs: 3769.
- Covered by questions: 1490 (39.5%).
- Covered by flashcards: 1542 (40.9%).
- Covered by activities: 254 (6.7%).
- Covered by at least one format: 1885 (50.0%).
- Reinforced through two or more formats: 1231 (32.7%).
- Reinforced through all three formats: 170 (4.5%).
- Cross-format near-duplicate pairs: 16.

Coverage is a lexical triage signal, not a legal or semantic determination. Cross-format reinforcement only counts when each format independently overlaps the same controlling source statement.

## Flashcard Findings

- Card types: {"capability": 3, "comparison": 7, "concept": 323, "concept_reverse": 23, "condition": 25, "conditions": 3, "contrast": 14, "definition": 110, "exception": 23, "format": 4, "list": 57, "minimum": 12, "note": 2, "phraseology": 49, "preference": 1, "procedure": 455, "reasoning": 9, "reference": 40, "requirement": 40, "restriction": 6, "reverse": 1, "rule": 63, "scope": 8, "sequence": 3, "source_reference": 1, "table": 3, "threshold": 57, "warning": 1}
- Retrieval modes: {"boundary_recall": 68, "concept_recall": 442, "definition_recall": 110, "discrimination": 21, "exact_recall": 53, "list_recall": 57, "numeric_recall": 69, "procedure_recall": 458, "reverse_recall": 24, "source_navigation": 41}
- 27 cards use context-light label prompts shorter than four words.
- 34 cards have answers shorter than four words.
- 16 cards overload one reveal with more than 50 words or a long list.
- 19 reverse cards do not provide a clear reverse-side prompt.
- 206 non-reference cards use paragraph-location scaffolding.
- 0 cards substantially repeat prompt language in the answer.
- 28 within-paragraph prompt pairs have at least 0.78 token similarity.
- 59 paragraphs have at least three flashcard retrieval modes.

## Activity Findings

- Activity types: {"discrimination": 1, "discrimination_check": 16, "format_check": 1, "identification_decision": 1, "knowledge_check": 111, "list_membership": 4, "phraseology_decision": 1, "readback_check": 9, "requirement_check": 5, "responsibility_check": 1, "scenario": 1, "sequence_check": 1, "situation_action": 160, "source_lookup": 7, "source_use": 3, "spot_the_error": 2, "traffic_advisory_decision": 1}
- Learning modes: {"discrimination": 19, "exact_application": 11, "knowledge_check": 111, "list_or_sequence": 5, "requirement_recall": 5, "scenario_application": 164, "source_use": 10}
- Correct-answer positions: {"0": 195, "1": 79, "2": 35, "3": 14}
- Correct answer is first in 60.4% of valid choice activities.
- 60 activities make the correct answer conspicuously longer than the distractors.
- 0 activities have fewer than two choices or do not have exactly one correct choice.
- 0 activities contain normalized duplicate choices.
- 1 scenario/decision activities provide fewer than twelve words of decision context.
- 85 activities use negative framing.
- 36 non-source-use activities rely on paragraph-location scaffolding.
- 0 within-paragraph activity pairs have at least 0.78 prompt similarity.
- 8 paragraphs have at least three activity modes.

## Highest-Priority Remediation

1. Rebalance activity answer positions and equalize answer/distractor specificity before adding more choice items.
2. Replace flashcard labels with explicit retrieval cues; keep each card focused on one answerable target.
3. Repair reverse cards so the reverse side asks a real question instead of naming a paragraph or topic.
4. Plan coverage by essential source element, then use card recall, question discrimination, and activity application as complementary tasks.
5. Treat same-stem or same-answer paraphrases across formats as duplication, not additional coverage.
6. Reserve source-location prompts for explicit lookup practice and keep citations outside ordinary learner prompts.

## Chapter Pattern

| Chapter | Cards | Context-light cards | Card location scaffold | Activities | Activity location scaffold | First-answer rate | Length cues |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 45 | 0 | 3 | 22 | 0 | 77% | 4 |
| 2 | 161 | 14 | 110 | 19 | 7 | 58% | 1 |
| 3 | 146 | 0 | 16 | 10 | 1 | 20% | 0 |
| 4 | 200 | 7 | 4 | 34 | 0 | 41% | 5 |
| 5 | 225 | 3 | 3 | 35 | 0 | 86% | 18 |
| 6 | 86 | 0 | 0 | 5 | 1 | 40% | 0 |
| 7 | 67 | 2 | 1 | 41 | 1 | 49% | 4 |
| 8 | 82 | 0 | 0 | 37 | 17 | 41% | 6 |
| 9 | 106 | 0 | 0 | 37 | 2 | 94% | 8 |
| 10 | 86 | 0 | 68 | 33 | 6 | 100% | 6 |
| 11 | 24 | 0 | 0 | 6 | 0 | 17% | 0 |
| 12 | 26 | 0 | 0 | 5 | 0 | 80% | 2 |
| 13 | 46 | 0 | 1 | 26 | 1 | 27% | 5 |
| 14 | 43 | 1 | 0 | 15 | 0 | 40% | 1 |

## Example Context-Light Flashcards

- `14-2-4` `procedure`: “CPDLC: holding restrictions” → “Must NOT use CPDLC to clear aircraft out of holding (route uplink lacks clearance limit). Must NOT use CPDLC for holding instructions if aircraft has climb/descend via. Cancel vertical nav portion first. Per 14-2-4(c).”
- `2-1-11` `concept`: “MARSA authority” → “Military command prerogative; not invoked indiscriminately by individual units or pilots.”
- `2-1-11` `concept`: “MARSA operations” → “May only be applied to specified military IFR operations documented in an LOA or other appropriate FAA/military document.”
- `2-1-2` `concept`: “First duty priority” → “Separate aircraft and issue safety alerts as required.”
- `2-1-21` `procedure`: “Traffic advisory trigger” → “Issue to aircraft on your frequency when proximity may diminish to less than applicable separation minima; where no minima apply, issue when proximity warrants.”
- `2-1-27` `procedure`: “Brasher notification trigger” → “When it appears pilot actions constitute a pilot deviation, notify the pilot workload permitting.”
- `2-1-29` `concept`: “RVSM vertical separation” → “Eligible aircraft are separated vertically by 1,000 feet in RVSM airspace.”
- `2-1-3` `concept`: “Procedural preference: automation” → “Use automation procedures over nonautomation procedures when workload, communications, and equipment capabilities permit.”
- `2-1-4` `concept`: “Operational priority baseline” → “First come, first served as circumstances permit, except listed priority situations and without compromising safety.”
- `2-1-5` `phraseology`: “Use of EXPEDITE” → “Only when prompt compliance is required to avoid development of an imminent situation; a later non-expedite altitude restatement cancels the expedite instruction.”
- `2-1-5` `phraseology`: “Use of IMMEDIATELY” → “Only when expeditious compliance is required to avoid an imminent situation.”
- `2-1-6` `procedure`: “Safety alert trigger” → “Issue when aware an aircraft is in unsafe proximity to terrain, obstructions, or other aircraft.”

## Example Malformed Reverse Cards

- `1-1-1`: “Exercise best judgment when a situation is not covered by the order.” → “Catch-all rule for controllers from 1-1-1.”
- `1-1-6`: “AIRAC dates for order publication.” → “The schedule to which JO 7110.65 and its changes are published; listed in TBL 1-1-1.”
- `12-1-2`: “Above 12,500 feet ASL or MEA (whichever higher) up to but not including 18,000 feet ASL. Only IFR and CVFR flights. IFR procedures applied to CVFR.” → “Canadian Class B airspace.”
- `12-1-2`: “Base of all controlled high level airspace up to and including FL 600. Only IFR flights permitted.” → “Canadian Class A airspace.”
- `12-1-2`: “Uncontrolled airspace where ATC has neither the authority nor responsibility for exercising control over air traffic.” → “Canadian Class G airspace.”
- `12-1-3`: “Pilot must ensure at least 1,000 feet above all cloud, haze, smoke, or other formation, with 3 miles or more flight visibility. Pilot's request = confirmation conditions are adequate.” → “Pilot's weather responsibility for the 1,000-feet-on-top clearance in Canada.”
- `12-1-4`: “Does good weather eliminate the separation requirement between IFR and CVFR aircraft in Canadian airspace?” → “No. The separation minimum applies regardless of the weather conditions. CVFR aircraft receive IFR-equivalent separation treatment.”
- `12-1-6`: “Written authority from the Ministry of Transport is required before ATC may authorize parachute jumping.” → “Canadian parachute jumping rule, per 12-1-6 and its note.”
- `12-1-7`: “1 mile flight visibility (ground visibility when reported) for SVFR.” → “Canadian SVFR weather minimum for aircraft other than helicopters.”
- `12-1-7`: “1/2 mile flight visibility (ground visibility when available) for SVFR.” → “Canadian SVFR weather minimum for helicopters.”
- `5-3-1`: “Establish and maintain radar identification of the aircraft involved before providing radar service.” → “5-3-1. Exceptions: 5-5-1 subparagraphs b2, b3 and 8-5-5 Radar Identification Application.”
- `7-1-1`: “Do not apply visual separation or issue VFR or VFR-on-top clearances in Class A airspace.” → “7-1-1: Class A airspace restrictions — three prohibitions.”

## Example Activity Answer-Length Cues

- `1-1-11` `knowledge_check`: correct answer “Waiver approval is governed by FAA Order JO 7210.3, Chapter 19, Section 7, which is a different order and chapter from the 1-1-8 change process.” (distractor average: 11.3 words)
- `1-1-11` `situation_action`: correct answer “No; military operations require prior approval by the appropriate military headquarters, and for USAF procedures involving military aircraft only, HQ Air Force Flight Standards Agency is the approval authority.” (distractor average: 14.0 words)
- `1-1-3` `source_lookup`: correct answer “The FAA Air Traffic Plans and Publications website, and the FAA Orders and Notices website.” (distractor average: 5.3 words)
- `1-2-1` `situation_action`: correct answer “No; 'will' means futurity, not a requirement for the application of a procedure. 'Must' is the term that means mandatory.” (distractor average: 8.7 words)
- `10-1-6` `situation_action`: correct answer “No — control the traffic to avoid conflicts in the area where the emergency is being handled and along routes needed by emergency equipment.” (distractor average: 11.7 words)
- `10-4-2` `knowledge_check`: correct answer “From at least 30 minutes before the ETA until the aircraft is located or for 30 minutes after fuel is estimated exhausted.” (distractor average: 11.7 words)
- `10-5-1` `list_membership`: correct answer “The emergency equipment crew, the airport management, and the appropriate military agencies when requested by the pilot.” (distractor average: 9.3 words)
- `10-6-3` `knowledge_check`: correct answer “All aircraft receiving ATC service, all other aircraft with a filed flight plan or otherwise known to the ATC unit, and any aircraft known or believed to be subject to unlawful interference.” (distractor average: 10.7 words)
- `10-6-4` `knowledge_check`: correct answer “The RCC determines the airspace required for SAR operations, the ACC blocks that airspace until the RCC releases it, and an International NOTAM is issued describing the affected airspace.” (distractor average: 12.0 words)
- `10-7-1` `knowledge_check`: correct answer “En route: notify air carrier company radio stations for VFR company aircraft in the vicinity and FSSs adjacent to the emergency. Terminal: relay all information to the ARTCC where the emergency exists and disseminate as a NOTAM.” (distractor average: 13.7 words)
- `12-1-3` `situation_action`: correct answer “Approve it if the pilot has requested it and will not operate in Class A or B. The pilot's request serves as confirmation that weather conditions are adequate.” (distractor average: 15.0 words)
- `12-1-5` `situation_action`: correct answer “Plan for the aircraft to maintain the last assigned altitude or MEA (whichever is higher) until 10 minutes beyond the clearance limit, then proceed at filed altitude(s) or flight level(s). Because U.S. airspace is within 10 minutes of the clearance limit (50 NM in a turbojet), the climb to border-crossing altitude will commence at the estimated time of crossing the Canada/U.S. boundary.” (distractor average: 24.0 words)

## Example Cross-Format Near-Duplicates

- `9-8-1` `question/flashcard` (1.00): “Under 9-8-1, what does 'UAP' stand for?” / “9-8-1: What does UAP stand for?”
- `2-1-1` `question/flashcard` (1.00): “What is the primary purpose of the ATC system?” / “ATC system: primary purpose”
- `5-9-4` `question/flashcard` (1.00): “When may approach clearance be issued?” / “When approach clearance may be issued (5-9-4c)”
- `3-4-7` `question/flashcard` (1.00): “Under 3-4-7, when must SFL be operated?” / “When must SFL be operated?”
- `9-1-3` `question/flashcard` (1.00): “Under 9-1-3, what is the altitude range for a preplanned automatic flight check?” / “9-1-3: Altitude range for preplanned automatic flight check”
- `3-4-6` `question/flashcard` (1.00): “What table controls ALS intensity settings under 3-4-6?” / “What table controls ALS intensity settings?”
- `3-10-8` `question/flashcard` (1.00): “Under 3-10-8, when must a landing clearance be withheld?” / “When must a landing clearance be withheld?”
- `2-2-12` `question/flashcard` (1.00): “Under 2-2-12, what two categories of information from airborne military aircraft must be forwarded to FSSs?” / “Under 2-2-12, what two categories of information from airborne military aircraft must be forwarded to FSSs?”
- `3-10-2` `question/flashcard` (1.00): “Under 3-10-2, nonapproach control towers must forward what to arriving aircraft?” / “What must nonapproach control towers forward to arriving aircraft?”
- `7-1-1` `question/flashcard` (0.91): “Complete: Do not apply visual separation or issue _____ or VFR-on-top clearances in Class A airspace.” / “Do not apply visual separation or issue VFR or VFR-on-top clearances in Class A airspace.”
- `4-8-4` `question/flashcard` (0.90): “What altitudes may be specified for military high altitude instrument approaches when required for separation?” / “What altitudes may be specified for military high altitude instrument approaches for separation?”
- `11-1-2` `question/flashcard` (0.90): “Under 11-1-2, when departure scheduling is in effect and an ATCT is equipped, how must the ATCT obtain a departure release time?” / “How must an ATCT obtain a departure release time when departure scheduling is in effect and the tower is equipped?”

## Lowest Multi-Format Reinforcement

- `2-6-4`: 0/34 essential statements covered by two or more formats; Q 1, cards 0, activities 0.
- `8-9-3`: 0/30 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `8-8-3`: 0/29 essential statements covered by two or more formats; Q 1, cards 0, activities 0.
- `8-10-3`: 0/28 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `8-7-3`: 0/26 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `2-10-1`: 0/20 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `2-9-3`: 0/17 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `5-8-3`: 0/17 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `3-10-5`: 0/14 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `3-9-7`: 0/14 essential statements covered by two or more formats; Q 1, cards 1, activities 0.
- `10-6-4`: 0/13 essential statements covered by two or more formats; Q 0, cards 5, activities 2.
- `2-10-3`: 0/10 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `10-4-4`: 0/9 essential statements covered by two or more formats; Q 0, cards 2, activities 0.
- `2-4-3`: 0/9 essential statements covered by two or more formats; Q 3, cards 2, activities 0.
- `3-10-12`: 0/9 essential statements covered by two or more formats; Q 0, cards 4, activities 0.
