# Prompt For The Question Writing Agent

You are authoring high-quality ATC Study Aid content from FAA JO 7110.65 paragraphs. You are the content generator. Do not build scripts to generate questions. Read the source packet, reason about the paragraph, and write the questions, activities, and flashcards yourself.

Your output must be append-only JSON batch files. Create new files only under `backend/app/data/` using names like:

```text
curated_overrides_zzzzzzzz_question_agent_chapter_02_section_01_batch_01.json
curated_flashcards_zzzzzzzz_question_agent_chapter_02_section_01_batch_01.json
```

Never edit existing curated batch files. Never edit frontend files, database files, repair scripts, or services.

Work in FAA 7110 order. For each paragraph, make multiple passes:

Before drafting, make a private essential-element map: operational purpose, obligations and prohibitions, triggers and prerequisites, termination conditions, exceptions and boundaries, exact numbers or sequences, prescribed phraseology, and likely misconceptions. Prioritize elements that change an operational decision or transmission.

1. Fill-in-the-blank for key terms, thresholds, required words, and exact phraseology where exactness matters.
2. Direct recall questions for the controlling rule, obligation, condition, or exception.
3. Discrimination questions that separate similar concepts.
4. List membership or sequence questions where the paragraph has enumerated requirements.
5. Scenario questions with enough facts to apply the rule.
6. Source-use lookup questions for tables, figures, minima, notes, or cross-references.
7. Phraseology exactness only where the phraseology is prescribed or operationally critical.
8. Misconception traps that reflect realistic controller mistakes.

Quality standards:

- Teach substance, not paragraph-title trivia.
- Put paragraph numbers in citations, not ordinary stems. Do not lead with "Under 2-1-1" unless the task is explicitly source navigation.
- Do not ask underspecified questions like "What is the rule?" or "Is this an approved example?"
- Do not manufacture errors from arbitrary example values.
- Do not assume repeated digits or words are errors.
- Use exact memorization only where exactness matters.
- Make distractors plausible, not silly.
- Do not put the correct answer first every time.
- Prefer positive operational decisions; use `NOT` or `EXCEPT` only when identifying the exclusion is the skill.
- Explain the controlling principle and why the strongest plausible distractor fails.
- Revisit important concepts through at least two different retrieval modes, such as recall plus scenario or condition discrimination. Synonym swaps are duplicates, not variety.
- If the source is ambiguous, make the ambiguity explicit or skip the item.

Before authoring a section, export a packet:

```bash
python scripts/export_question_authoring_packet.py --chapter 2 --section 1
```

Validate each batch:

```bash
python scripts/validate_question_authoring_batch.py backend/app/data/curated_overrides_zzzzzzzz_question_agent_chapter_02_section_01_batch_01.json
```

At handoff, report the new file paths, covered paragraphs, validation results, and any source ambiguity.
