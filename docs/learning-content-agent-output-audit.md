# Learning-Content Agent Output Audit

Sources audited: `question_agent`

## Corpus Summary

- Questions: 1838 across 653 paragraphs.
- Flashcards: 1642 across 643 paragraphs.
- Activities: 287 across 234 paragraphs.
- Paragraphs represented by all three formats: 220 of 672.

## Cross-Format Essential-Element Coverage

- Heuristic essential statements in represented paragraphs: 3839.
- Covered by questions: 1618 (42.1%).
- Covered by flashcards: 1698 (44.2%).
- Covered by activities: 219 (5.7%).
- Covered by at least one format: 2054 (53.5%).
- Reinforced through two or more formats: 1326 (34.5%).
- Reinforced through all three formats: 155 (4.0%).
- Cross-format near-duplicate pairs: 37.

Coverage is a lexical triage signal, not a legal or semantic determination. Cross-format reinforcement only counts when each format independently overlaps the same controlling source statement.

## Flashcard Findings

- Card types: {"authorization": 1, "basic": 43, "capability": 3, "comparison": 8, "concept": 388, "concept_reverse": 6, "condition": 28, "condition_change": 1, "conditions": 6, "contrast": 17, "definition": 121, "exception": 34, "fact": 2, "format": 6, "limitation": 1, "list": 69, "minimum": 12, "note": 2, "phraseology": 60, "preference": 1, "principle": 3, "priority": 1, "procedure": 564, "prohibition": 2, "reasoning": 10, "reference": 28, "requirement": 57, "responsibility": 1, "restriction": 6, "rule": 71, "scope": 12, "sequence": 3, "source_reference": 1, "table": 3, "threshold": 69, "trigger": 1, "warning": 1}
- Retrieval modes: {"boundary_recall": 89, "concept_recall": 589, "definition_recall": 121, "discrimination": 25, "exact_recall": 66, "list_recall": 69, "numeric_recall": 81, "procedure_recall": 567, "reverse_recall": 6, "source_navigation": 29}
- 41 cards use context-light label prompts shorter than four words.
- 4 cards have answers shorter than four words.
- 7 cards overload one reveal with more than 50 words or a long list.
- 0 reverse cards do not provide a clear reverse-side prompt.
- 433 non-reference cards use paragraph-location scaffolding.
- 0 cards substantially repeat prompt language in the answer.
- 46 within-paragraph prompt pairs have at least 0.78 token similarity.
- 83 paragraphs have at least three flashcard retrieval modes.

## Activity Findings

- Activity types: {"discrimination": 1, "format_check": 1, "identification_decision": 1, "knowledge_check": 108, "list_membership": 1, "phraseology_decision": 1, "readback_check": 9, "responsibility_check": 1, "sequence_check": 1, "situation_action": 154, "source_lookup": 5, "source_use": 1, "spot_the_error": 2, "traffic_advisory_decision": 1}
- Learning modes: {"discrimination": 3, "exact_application": 11, "knowledge_check": 108, "list_or_sequence": 2, "scenario_application": 157, "source_use": 6}
- Stored correct-answer position is not scored because the application shuffles choices at runtime.
- 40 activities make the correct answer conspicuously longer than the distractors.
- 0 activities have fewer than two choices or do not have exactly one correct choice.
- 0 activities contain normalized duplicate choices.
- 4 scenario/decision activities provide fewer than twelve words of decision context.
- 4 activities use negative framing.
- 9 non-source-use activities rely on paragraph-location scaffolding.
- 0 within-paragraph activity pairs have at least 0.78 prompt similarity.
- 5 paragraphs have at least three activity modes.

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
| 1 | 55 | 0 | 2 | 21 | 0 | 1 |
| 2 | 207 | 14 | 2 | 19 | 1 | 1 |
| 3 | 166 | 0 | 9 | 10 | 1 | 0 |
| 4 | 221 | 7 | 15 | 0 | 0 | 0 |
| 5 | 273 | 4 | 166 | 35 | 0 | 18 |
| 6 | 108 | 0 | 85 | 5 | 1 | 0 |
| 7 | 100 | 15 | 5 | 39 | 0 | 3 |
| 8 | 91 | 0 | 43 | 37 | 0 | 5 |
| 9 | 126 | 0 | 101 | 37 | 2 | 0 |
| 10 | 139 | 0 | 3 | 33 | 1 | 6 |
| 11 | 27 | 0 | 0 | 5 | 1 | 0 |
| 12 | 25 | 0 | 0 | 5 | 0 | 2 |
| 13 | 55 | 0 | 2 | 26 | 1 | 4 |
| 14 | 49 | 1 | 0 | 15 | 1 | 0 |

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

- `3-10-2` `question/flashcard` (1.00): “Nonapproach control towers must forward what to arriving aircraft?” / “What must nonapproach control towers forward to arriving aircraft?”
- `7-2-1` `question/flashcard` (1.00): “When is tower-applied visual separation not authorized?” / “Tower-applied visual separation: when NOT authorized”
- `7-5-5` `question/flashcard` (1.00): “What is the key condition for authorizing local SVFR operations for a specified period?” / “What is the key condition for authorizing local SVFR operations for a specified period?”
- `8-2-2` `question/flashcard` (1.00): “How many ATC units may control an aircraft at any given time?” / “How many ATC units may control an aircraft at any given time?”
- `10-1-4` `question/flashcard` (1.00): “Which two conditions must both be met before aircraft may join up in formation during emergency conditions?” / “What two conditions must both be met before aircraft may join up in formation during emergency conditions?”
- `2-1-1` `question/flashcard` (1.00): “What is the primary purpose of the ATC system?” / “ATC system: primary purpose”
- `4-5-8` `question/flashcard` (1.00): “When should a controller inform an aircraft about when to expect a climb or descent clearance?” / “When should a controller inform an aircraft about when to expect a climb or descent clearance?”
- `9-8-1` `question/flashcard` (1.00): “What does 'UAP' stand for?” / “9-8-1: What does UAP stand for?”
- `9-2-20` `question/flashcard` (1.00): “What is the total altitude block within which the evasive action maneuver must be confined?” / “What is the total altitude block within which an evasive action maneuver must be confined?”
- `3-1-14` `question/flashcard` (1.00): “What two operational harms does newly airborne volcanic ash cause to following aircraft?” / “What two operational harms does newly airborne volcanic ash cause to following aircraft?”
- `9-2-18` `question/flashcard` (1.00): “How are AWACS/NORAD Special flights identified in the flight plan?” / “How are AWACS/NORAD Special flights identified in the flight plan?”
- `2-2-12` `question/flashcard` (1.00): “What two categories of information from airborne military aircraft must be forwarded to FSSs?” / “What two categories of information from airborne military aircraft must be forwarded to FSSs?”

## Lowest Multi-Format Reinforcement

- `2-6-4`: 0/34 essential statements covered by two or more formats; Q 1, cards 0, activities 0.
- `2-10-1`: 0/20 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `2-9-3`: 0/17 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `5-8-3`: 0/17 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `3-10-5`: 0/14 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `3-9-7`: 0/14 essential statements covered by two or more formats; Q 1, cards 1, activities 0.
- `5-2-1`: 0/12 essential statements covered by two or more formats; Q 3, cards 0, activities 0.
- `2-10-3`: 0/10 essential statements covered by two or more formats; Q 1, cards 1, activities 0.
- `10-4-4`: 0/9 essential statements covered by two or more formats; Q 0, cards 2, activities 0.
- `3-10-12`: 0/9 essential statements covered by two or more formats; Q 0, cards 4, activities 0.
- `5-2-7`: 0/9 essential statements covered by two or more formats; Q 3, cards 0, activities 0.
- `5-5-9`: 0/9 essential statements covered by two or more formats; Q 0, cards 5, activities 0.
- `3-10-13`: 0/8 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
- `3-12-3`: 0/8 essential statements covered by two or more formats; Q 0, cards 0, activities 0.
- `3-9-10`: 0/8 essential statements covered by two or more formats; Q 0, cards 1, activities 0.
