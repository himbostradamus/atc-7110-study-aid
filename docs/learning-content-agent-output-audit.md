# Learning-Content Agent Output Audit

Sources audited: `curated, question_agent, deepseek, content_expansion_pass_01, content_expansion_pass_02, content_expansion_pass_02_2`

## Corpus Summary

- Questions: 4635 across 688 paragraphs.
- Flashcards: 4641 across 688 paragraphs.
- Activities: 2642 across 687 paragraphs.
- Paragraphs represented by all three formats: 687 of 688.

## Cross-Format Essential-Element Coverage

- Heuristic essential statements in represented paragraphs: 3873.
- Covered by questions: 2598 (67.1%).
- Covered by flashcards: 2517 (65.0%).
- Covered by activities: 1492 (38.5%).
- Covered by at least one format: 2948 (76.1%).
- Reinforced through two or more formats: 2361 (61.0%).
- Reinforced through all three formats: 1298 (33.5%).
- Cross-format near-duplicate pairs: 505.

Coverage is a lexical triage signal, not a legal or semantic determination. Cross-format reinforcement only counts when each format independently overlaps the same controlling source statement.

## Flashcard Findings

- Card types: {"advisory": 1, "authority": 1, "authorization": 1, "basic": 43, "boundary": 5, "capability": 14, "caution": 7, "comparison": 14, "concept": 438, "concept_reverse": 6, "condition": 121, "condition_change": 1, "conditions": 6, "contrast": 18, "definition": 1308, "detail": 5, "directive": 2, "discretion": 1, "discrimination": 7, "document": 3, "effect": 4, "exact_recall": 1, "example": 9, "exception": 239, "expectation": 2, "fact": 2, "focus": 1, "format": 6, "guidance": 1, "hazard": 1, "interval": 4, "judgment": 1, "limit": 2, "limitation": 6, "list": 80, "list_recall": 3, "minima": 21, "minimum": 29, "note": 10, "numeric": 6, "numeric_recall": 2, "order": 2, "phraseology": 216, "preference": 2, "principle": 3, "priority": 3, "procedure": 1215, "prohibition": 12, "purpose": 3, "reason": 1, "reasoning": 49, "recordkeeping": 1, "reference": 31, "requirement": 318, "responsibility": 9, "restriction": 51, "risk": 1, "rule": 74, "scope": 62, "sequence": 3, "source_reference": 1, "standard": 1, "table": 56, "technique": 1, "threshold": 76, "timing": 4, "trigger": 3, "use": 5, "visual": 4, "warning": 2}
- Retrieval modes: {"boundary_recall": 493, "concept_recall": 1145, "definition_recall": 1308, "discrimination": 32, "exact_recall": 222, "list_recall": 80, "numeric_recall": 105, "procedure_recall": 1218, "reverse_recall": 6, "source_navigation": 32}
- 37 cards use context-light label prompts shorter than four words.
- 692 cards have answers shorter than four words.
- 22 cards overload one reveal with more than 50 words or a long list.
- 0 reverse cards do not provide a clear reverse-side prompt.
- 56 non-reference cards use paragraph-location scaffolding.
- 7 cards substantially repeat prompt language in the answer.
- 381 within-paragraph prompt pairs have at least 0.78 token similarity.
- 399 paragraphs have at least three flashcard retrieval modes.

## Activity Findings

- Activity types: {"capability_check": 17, "condition_boundary": 3, "conditional_rule_check": 143, "directive_check": 79, "discrimination": 71, "document_control_check": 4, "format_check": 1, "identification_decision": 1, "knowledge_check": 636, "list_membership": 128, "match_pairs": 2, "minima_rule_check": 48, "ordering": 7, "ordering_or_list": 4, "phraseology_builder": 120, "phraseology_construction": 6, "phraseology_decision": 1, "phraseology_exactness": 1, "readback_check": 90, "requirement_check": 208, "responsibility_check": 1, "scope_check": 103, "sequence_check": 1, "sequence_construction": 1, "sequence_steps": 11, "situation_action": 753, "source_lookup": 17, "source_use": 13, "spot_the_error": 91, "table_lookup": 49, "term_definition_check": 8, "traffic_advisory_decision": 1, "visual_interpretation": 23}
- Learning modes: {"discrimination": 162, "exact_application": 219, "knowledge_check": 1122, "list_or_sequence": 145, "requirement_recall": 208, "scenario_application": 756, "source_use": 30}
- Stored correct-answer position is not scored because the application shuffles choices at runtime.
- 86 activities make the correct answer conspicuously longer than the distractors.
- 0 activities have fewer than two choices or do not have exactly one correct choice.
- 0 activities contain normalized duplicate choices.
- 14 scenario/decision activities provide fewer than twelve words of decision context.
- 16 activities use negative framing.
- 72 non-source-use activities rely on paragraph-location scaffolding.
- 0 within-paragraph activity pairs have at least 0.78 prompt similarity.
- 417 paragraphs have at least three activity modes.

## Highest-Priority Remediation

1. Equalize answer/distractor specificity before adding more choice items.
2. Replace flashcard labels with explicit retrieval cues; keep each card focused on one answerable target.
3. Repair reverse cards so the reverse side asks a real question instead of naming a paragraph or topic.
4. Plan coverage by essential source element, then use card recall, question discrimination, and activity application as complementary tasks.
5. Treat same-stem or same-answer paraphrases across formats as duplication, not additional coverage.
6. Reserve source-location prompts for explicit lookup practice and keep citations outside ordinary learner prompts.

## Chapter Pattern

| Chapter | Cards | Context-light cards | Card location scaffold | Activities | Activity location scaffold | Length cues |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 650 | 0 | 2 | 58 | 2 | 1 |
| 2 | 793 | 14 | 18 | 442 | 37 | 23 |
| 3 | 789 | 0 | 10 | 547 | 6 | 4 |
| 4 | 651 | 7 | 15 | 336 | 0 | 6 |
| 5 | 605 | 0 | 0 | 446 | 3 | 25 |
| 6 | 157 | 0 | 0 | 105 | 5 | 0 |
| 7 | 177 | 15 | 5 | 188 | 3 | 6 |
| 8 | 174 | 0 | 0 | 147 | 5 | 7 |
| 9 | 186 | 0 | 0 | 107 | 3 | 2 |
| 10 | 216 | 0 | 4 | 138 | 2 | 6 |
| 11 | 34 | 0 | 0 | 9 | 1 | 0 |
| 12 | 39 | 0 | 0 | 24 | 1 | 2 |
| 13 | 89 | 0 | 2 | 56 | 3 | 4 |
| 14 | 81 | 1 | 0 | 39 | 1 | 0 |

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


## Example Activity Answer-Length Cues

- `1-1-3` `source_lookup`: correct answer “The FAA Air Traffic Plans and Publications website, and the FAA Orders and Notices website.” (distractor average: 5.3 words)
- `10-1-6` `situation_action`: correct answer “No — control the traffic to avoid conflicts in the area where the emergency is being handled and along routes needed by emergency equipment.” (distractor average: 11.7 words)
- `10-4-2` `knowledge_check`: correct answer “From at least 30 minutes before the ETA until the aircraft is located or for 30 minutes after fuel is estimated exhausted.” (distractor average: 11.7 words)
- `10-5-1` `list_membership`: correct answer “The emergency equipment crew, the airport management, and the appropriate military agencies when requested by the pilot.” (distractor average: 9.3 words)
- `10-6-3` `knowledge_check`: correct answer “All aircraft receiving ATC service, all other aircraft with a filed flight plan or otherwise known to the ATC unit, and any aircraft known or believed to be subject to unlawful interference.” (distractor average: 10.7 words)
- `10-6-4` `knowledge_check`: correct answer “The RCC determines the airspace required for SAR operations, the ACC blocks that airspace until the RCC releases it, and an International NOTAM is issued describing the affected airspace.” (distractor average: 12.0 words)
- `10-7-1` `knowledge_check`: correct answer “En route: notify air carrier company radio stations for VFR company aircraft in the vicinity and FSSs adjacent to the emergency. Terminal: relay all information to the ARTCC where the emergency exists and disseminate as a NOTAM.” (distractor average: 13.7 words)
- `12-1-3` `situation_action`: correct answer “Approve it if the pilot has requested it and will not operate in Class A or B. The pilot's request serves as confirmation that weather conditions are adequate.” (distractor average: 15.0 words)
- `12-1-5` `situation_action`: correct answer “Plan for the aircraft to maintain the last assigned altitude or MEA (whichever higher) until 10 minutes beyond the clearance limit, then proceed at filed altitudes. Because U.S. airspace is within 10 minutes of the clearance limit, the climb to the border-crossing altitude will commence at the estimated time of crossing the Canada/U.S. boundary.” (distractor average: 24.0 words)
- `13-1-1` `situation_action`: correct answer “Use EDST for strategic planning and conflict prediction, but maintain radar separation using actual radar track data. EDST is a strategic planning tool that uses current plans which may include unissued clearances.” (distractor average: 16.7 words)
- `13-1-15` `knowledge_check`: correct answer “Both require continued use of the affected tools with recognition that certain data may be affected—but the specific data that may be affected differs between the two situations.” (distractor average: 13.3 words)
- `13-1-7` `knowledge_check`: correct answer “Yes, if used in accordance with facility directives. Hold View is one of the five approved annotation methods, and no method requires supplementation by another.” (distractor average: 12.7 words)

## Example Cross-Format Near-Duplicates

- `3-9-10` `question/flashcard` (1.00): “When is FULL LENGTH included in a takeoff clearance?” / “When is full length included in the takeoff clearance?”
- `3-9-10` `question/flashcard` (1.00): “When must the runway intersection be stated in the takeoff clearance?” / “When must the runway intersection be stated in the takeoff clearance?”
- `2-1-7` `question/flashcard` (1.00): “When a pilot reports an inflight equipment malfunction, what should the controller determine first?” / “What should a controller determine first when a pilot reports an inflight equipment malfunction?”
- `3-4-9` `question/flashcard` (1.00): “When is the ALSF-2 system operated?” / “When is the ALSF-2 system operated?”
- `3-10-8` `question/flashcard` (1.00): “When must a landing clearance be withheld?” / “When must a landing clearance be withheld?”
- `5-1-4` `question/flashcard` (1.00): “Which aircraft receive merging target procedures, except while established in a holding pattern?” / “Which aircraft receive merging target procedures, except while established in a holding pattern?”
- `5-9-9` `question/flashcard` (1.00): “What is SOIA?” / “What is SOIA?”
- `3-10-1` `question/flashcard` (1.00): “What kind of fixes should be used for additional position reports?” / “What kind of fixes should be used for additional position reports?”
- `2-4-12` `question/flashcard` (1.00): “When may gate or fix names be substituted for interphone position identification?” / “When may gate or fix names be substituted for interphone position identification?”
- `11-1-1` `question/flashcard` (1.00): “What is the mission of the traffic management system?” / “What is the mission of the traffic management system?”
- `2-1-1` `question/flashcard` (1.00): “What is the primary purpose of the ATC system?” / “ATC system: primary purpose”
- `2-1-1` `question/flashcard` (1.00): “What is the primary purpose of the ATC system?” / “What is the primary purpose of the ATC system?”

## Lowest Multi-Format Reinforcement

- `7-6-12`: 0/3 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `1-2-6`: 0/2 essential statements covered by two or more formats; Q 0, cards 2, activities 0.
- `10-2-16`: 0/2 essential statements covered by two or more formats; Q 2, cards 0, activities 0.
- `7-9-7`: 0/2 essential statements covered by two or more formats; Q 2, cards 0, activities 0.
- `2-2-14`: 0/1 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `7-7-6`: 0/1 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `8-10-2`: 0/1 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `14-3-3`: 7/127 essential statements covered by two or more formats; Q 8, cards 7, activities 5.
- `13-2-3`: 1/13 essential statements covered by two or more formats; Q 5, cards 2, activities 0.
- `8-8-3`: 3/29 essential statements covered by two or more formats; Q 11, cards 3, activities 2.
- `8-10-3`: 3/28 essential statements covered by two or more formats; Q 7, cards 4, activities 4.
- `2-1-13`: 1/7 essential statements covered by two or more formats; Q 1, cards 3, activities 1.
- `14-2-4`: 7/48 essential statements covered by two or more formats; Q 8, cards 7, activities 6.
- `5-7-1`: 3/19 essential statements covered by two or more formats; Q 4, cards 3, activities 5.
- `8-9-3`: 5/30 essential statements covered by two or more formats; Q 7, cards 2, activities 6.
