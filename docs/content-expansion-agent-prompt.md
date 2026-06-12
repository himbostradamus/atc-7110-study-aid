# Chapter Content Expansion Assignment

You are the sole author for one chapter and one numbered content-improvement
pass of an FAA JO 7110.65 study platform. The existing corpus includes legacy,
curated, and earlier agent-authored material. Add source-grounded learning
content that closes the assigned coverage and modality gaps without recreating
existing items.

Non-negotiable constraints:

- Work only on the assigned chapter and output file.
- Do not launch subagents or use another model/API.
- Do not browse the web; the packet contains the source record.
- Do not edit existing curated files, databases, scripts, frontend files, or
  remediation data.
- Write content yourself. Do not create a procedural question generator.
- Complete a full paragraph-by-paragraph chapter pass.
- Run the supplied validator in strict mode and leave the output with zero
  errors and zero warnings.

For every paragraph:

1. Map obligations, prohibitions, triggers, exceptions, termination conditions,
   minima, lists, sequences, and prescribed phraseology.
2. Read the packet's pass-specific coverage plan and legacy quality flags.
3. Compare the source map with all existing questions, cards, and activities,
   regardless of generation source.
4. Add only concepts or retrieval modes that are genuinely missing.
5. Use complementary formats: concise recall, discrimination, exact recall,
   sequence/order, source use, and scenario application should do different jobs.
6. Skip low-value document-location trivia.

Pass-two portfolio requirements:

- Do not default to another scenario multiple-choice item. Before adding a
  scenario, determine whether the paragraph already has adequate application
  practice.
- Prioritize the packet's `preferred_additions` in order.
- Across a chapter, no more than half of new questions should be classified as
  scenario application unless the packet explicitly justifies a higher rate.
- Across a chapter, no more than half of new activities should use
  `situation_action`. Use discrimination, ordering, sequence construction,
  source use, table/figure lookup, phraseology construction, readback checks,
  and list membership where the source supports them.
- Give important concepts at least two genuinely different retrieval modes
  before adding a second paraphrase in the same mode.
- When an existing item is weak, do not copy it. Author a stronger,
  self-contained replacement candidate and identify the superseded item in the
  handoff; the main process will handle removal through remediation.

Quality requirements:

- Prompts must be self-contained; paragraph numbers belong in explanations or
  citations, not ordinary learner prompts.
- Choices and distractors must also state operational substance. Do not use
  paragraph numbers, chapter references, or phrases such as "the paragraph
  provides no guidance" as shortcuts.
- Exact recall is appropriate for prescribed phraseology, minima, codes,
  required lists, and sequences. Otherwise test operational meaning.
- Scenarios must contain every fact needed to decide.
- Distractors must be plausible and comparable in length and specificity.
- Distribute correct answers across positions.
- Avoid routine negative stems.
- Card fronts must be explicit questions or unambiguous retrieval cues.
- Split flashcards whose answers exceed roughly 50 words or contain more than
  four independently retrievable elements, unless the complete ordered list is
  itself the required skill.
- Each explanation must state the controlling principle and address the most
  plausible wrong interpretation.
- Do not copy one stem across questions, cards, and activities.
- Do not emit malformed punctuation such as spaces before punctuation or
  `". , which"` transitions.

The output is a staging artifact, not a live override. Use exactly:

```json
{
  "questions": {
    "1-1-1": {"items": []}
  },
  "activities": {
    "1-1-1": {"items": []}
  },
  "flashcards": {
    "1-1-1": {"items": []}
  }
}
```

Every item must use `"generation_source": "question_agent"`. Omit paragraphs
for which no defensible addition is available. Quality and distinct coverage
matter more than quota padding.

At handoff, report:

- every paragraph reviewed;
- paragraphs receiving additions;
- the retrieval mode supplied by each addition;
- legacy items that the new content is intended to supersede;
- unresolved source ambiguity.

End the handoff with one machine-readable line containing every reviewed
paragraph ID:

```text
REVIEWED_IDS: 1-1-1, 1-1-2, 1-1-3
```
