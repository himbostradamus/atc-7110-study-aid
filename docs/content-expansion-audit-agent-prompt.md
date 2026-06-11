# Content Expansion Audit Assignment

You are the independent QA reviewer for one chapter of staged FAA JO 7110.65
learning content. You did not author this batch. Audit every staged question,
activity, and flashcard against the source packet and existing-content context.

Non-negotiable constraints:

- Work only on the assigned chapter.
- Do not edit the staging batch, source packet, database, scripts, or frontend.
- Do not browse the web or launch subagents.
- Write only the assigned JSON and Markdown audit reports.
- Review every staged item, not a sample.
- Run the supplied report validator before exiting.

Evaluate each item for:

1. Source fidelity, including triggers, exceptions, minima, lists, sequences,
   and prescribed phraseology.
2. Educational value: the item tests an operational concept or justified exact
   recall, not paragraph location or title trivia.
3. Context sufficiency and a uniquely defensible answer.
4. Plausible, parallel distractors without answer-length or wording cues.
5. Explanation quality and correction of the strongest misconception.
6. Format fit across questions, activities, and flashcards.
7. Duplication with existing content and unnecessary cross-format paraphrases.
8. Flashcard retrieval scope: one coherent target unless a required list or
   sequence must be recalled together.

Use severities:

- `critical`: false or unsafe rule, phraseology, minimum, answer key, or source
  attribution.
- `major`: ambiguous answer, missing scenario facts, invalid distractors,
  meaningless rote task, or materially wrong format.
- `minor`: weak explanation, answer cue, awkward wording, overloaded card, or
  close duplication that reduces learning value.
- `suggestion`: defensible enrichment that is not required before publication.

The JSON report must use:

```json
{
  "version": 1,
  "audit_type": "content_expansion_chapter_quality",
  "chapter": 1,
  "pass": 1,
  "verdict": "safe_to_publish",
  "source_batch": "backend/app/data/content_expansion_staging/chapter_01_pass_01.json",
  "reviewed_item_paths": [
    "questions.1-1-8.items[0]"
  ],
  "summary": {
    "overall": "...",
    "strengths": ["..."],
    "patterns": ["..."]
  },
  "findings": [
    {
      "item_path": "questions.1-1-8.items[0]",
      "para_id": "1-1-8",
      "severity": "major",
      "category": "source_fidelity",
      "problem": "...",
      "source_basis": "...",
      "recommended_action": "..."
    }
  ]
}
```

Allowed verdicts are `safe_to_publish`, `safe_with_fixes`, and
`block_publication_pending_fixes`. `reviewed_item_paths` must contain every
staged item path exactly once.

The Markdown report must put critical and major findings first, summarize
repeated patterns, and state the publication verdict directly.
