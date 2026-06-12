# Content Expansion Pass 02

## Baseline

Pass one added 310 questions, 116 activities, and 283 flashcards. Its items are
structurally cleaner than the legacy corpus, but the portfolio is too narrow:

- 75.8 percent of new questions use scenario application.
- 87.1 percent of new activities use situation/action.
- 232 of 249 question-covered paragraphs have only one question mode.
- Every activity-covered paragraph has only one activity mode.
- Chapters 4, 7, 8, 9, 13, and 14 received relatively little expansion.

The complete curriculum also retains older paragraph-location scaffolding,
generic references, thin explanations, overloaded cards, and punctuation
defects. Generation source does not exempt an item from review.

## Pass Objective

Pass two increases retrieval-mode diversity and source coverage rather than
adding another paraphrased scenario to each paragraph. Agents review every
paragraph and prioritize:

- prescribed phraseology and exact readback where wording is operationally
  significant;
- ordering, sequence, list membership, and exception boundaries;
- table, figure, and source-use decisions;
- discrimination between plausible neighboring rules;
- numeric minima and thresholds;
- concise bidirectional or contrast cards;
- stronger replacement candidates for weak legacy items.

No more than half of a chapter's new questions should be scenario application,
and no more than half of its activities should be situation/action unless the
source packet explicitly justifies the exception.

## Publication Gates

- Full paragraph-by-paragraph review evidence.
- Zero validator errors and zero warnings.
- Source fidelity review by the main process.
- No live-database publication until cross-format duplication, answer cues,
  mode mix, and legacy replacement claims are audited.
- The same packet analysis will later be applied to all older content, not only
  the latest expansion cohort.

## Final Outcome

The reviewed pass publishes 336 questions, 156 activities, and 162 flashcards
across all 14 chapters. QA removed 146 staged items that duplicated an existing
retrieval target or conflicted with another staged item. Seven lexical overlap
findings remain by design because they test distinct table bands, maneuver
boundaries, threshold cases, or complete multi-part duties.

The final cohort has:

- zero paragraph-location scaffolds or generic source references;
- zero thin question explanations, flashcard backs, or activity scenarios;
- zero malformed or duplicate choice sets and zero answer-length cues;
- zero within-format card/activity near-duplicates and zero cross-format
  near-duplicates;
- one intentional negative-framed source-use task that asks the learner to
  identify a missing contact-approach condition;
- one intentional question similarity pair covering opposite magnetic-course
  outcomes in the IFR altitude table.

The review also corrected the five-minute lost-communications trigger in
paragraph 10-4-4: after communications remain lost for five minutes, the
aircraft or pilot activity is treated as suspicious and reported to the OS/CIC.
The database repair path now updates append-only activities by stable
`publication_id`, so later content corrections replace previously published
JSON instead of being silently skipped.
