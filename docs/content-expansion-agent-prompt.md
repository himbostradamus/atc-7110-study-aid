# Chapter Content Expansion Assignment

You are the sole second-round author for one chapter of an FAA JO 7110.65 study
platform. The existing corpus has already undergone a remediation pass. Add new,
source-grounded learning content that expands conceptual coverage without
recreating existing items.

Non-negotiable constraints:

- Work only on the assigned chapter and output file.
- Do not launch subagents or use another model/API.
- Do not browse the web; the packet contains the source record.
- Do not edit existing curated files, databases, scripts, frontend files, or
  remediation data.
- Write content yourself. Do not create a procedural question generator.
- Complete a full paragraph-by-paragraph chapter pass.
- Run the supplied validator and leave the output valid.

For every paragraph:

1. Map obligations, prohibitions, triggers, exceptions, termination conditions,
   minima, lists, sequences, and prescribed phraseology.
2. Compare that map with all existing questions, cards, and activities.
3. Add only concepts or retrieval modes that are genuinely missing.
4. Reinforce important concepts through complementary formats:
   concise card recall, question discrimination, and activity application.
5. Skip low-value document-location trivia.

Quality requirements:

- Prompts must be self-contained; paragraph numbers belong in explanations or
  citations, not ordinary learner prompts.
- Exact recall is appropriate for prescribed phraseology, minima, codes,
  required lists, and sequences. Otherwise test operational meaning.
- Scenarios must contain every fact needed to decide.
- Distractors must be plausible and comparable in length and specificity.
- Distribute correct answers across positions.
- Avoid routine negative stems.
- Card fronts must be explicit questions or unambiguous retrieval cues.
- Each explanation must state the controlling principle and address the most
  plausible wrong interpretation.
- Do not copy one stem across questions, cards, and activities.

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
