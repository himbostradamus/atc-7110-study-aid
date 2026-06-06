# Question Audit Agent Harness

This harness is for asynchronous audit agents reviewing ATC Study Aid authored content. Audit agents are reviewers only. They must not edit curriculum, database, frontend, source, or generated batch files.

## Audit Goal

Review question-agent output for:

- Source fidelity: the item accurately follows FAA JO 7110.65 source text and does not invent requirements.
- Educational coherence: the item tests an operationally meaningful concept, not paragraph-title trivia or document-location memorization.
- Stem quality: the learner has enough context to answer without guessing the paragraph title.
- Answer quality: correct answer is defensible, distractors are plausible, and multiple-choice items do not have multiple unintended correct answers.
- Explanation quality: explanation teaches the operative rule, condition, exception, or phraseology requirement.
- Activity fit: activity type matches the concept being tested; phraseology exactness is used only where exactness matters.
- Flashcard quality: cards are concise, bidirectional where useful, and not misleading rote fragments.
- Sourcing/citation: item references the right paragraph/source idea and does not rely on unsupported examples.

## Non-Negotiable Storage Contract

Write audit output only under:

```text
backend/app/data/question_authoring_workspace/audits/
```

Use append-only files:

```text
audit_question_agent_chapter_XX_pass_NN.json
audit_question_agent_chapter_XX_pass_NN.md
```

Cross-cutting auditors may use:

```text
audit_question_agent_crosscut_TOPIC_pass_NN.json
audit_question_agent_crosscut_TOPIC_pass_NN.md
```

Never edit or delete existing audit files. If the target file exists, increment `NN`.

## Files To Avoid

Audit agents must not modify:

- `backend/app/data/curated_overrides*.json`
- `backend/app/data/curated_flashcards*.json`
- `backend/app/data/question_authoring_workspace/progress.json`
- `frontend/**`
- `frontend/public/curriculum.db`
- `frontend/dist/curriculum.db`
- `scripts/repair_curriculum.py`
- `backend/app/services/**`
- source PDFs, image assets, aircraft assets, or generated databases

## What To Read

For the assigned chapter:

1. Export/reuse source packets:

```bash
python scripts/export_question_authoring_packet.py --chapter 5
```

2. Read the generated append-only files:

```text
backend/app/data/curated_overrides_zzzzzzzz_question_agent_chapter_XX_section_*.json
backend/app/data/curated_flashcards_zzzzzzzz_question_agent_chapter_XX_section_*.json
```

3. Run structural validation when useful:

```bash
python scripts/validate_question_authoring_batch.py PATH_TO_BATCH.json
```

## Severity

Use these severities consistently:

- `critical`: materially wrong rule, unsafe operational implication, false phraseology/minima, or ambiguous item likely to teach the wrong action.
- `major`: underspecified stem, weak/invalid distractors, multiple plausible answers, rote/document-trivia item, or item type mismatched to concept.
- `minor`: awkward wording, thin explanation, duplicate-ish item, poor difficulty, weak but not wrong flashcard.
- `suggestion`: good-faith improvement idea, enrichment opportunity, or item that should be promoted into a better activity type.

## Finding Schema

Each finding should identify:

- `chapter`
- `section`
- `para_id`
- `file`
- `item_path`
- `severity`
- `category`
- `problem`
- `source_basis`
- `recommended_action`

Prefer precise item paths such as:

```text
questions.5-2-3.items[4]
activities.4-7-10.items[2]
flashcards.2-4-16.items[7]
```

## Review Method

Do not try to line-edit everything. Sample intelligently but cover the full chapter:

1. Review every section at least once.
2. Inspect all files in the chapter.
3. Deep-review high-risk categories:
   - phraseology builders
   - spot-the-error
   - example checks
   - table/figure/source-use activities
   - emergencies, separation, minima, wake turbulence, radar identification
   - items with exact numeric thresholds or phraseology
4. Record repeated patterns as chapter-level findings if the same defect appears across many items.
5. Include a final `coverage` object stating sections reviewed and files reviewed.

## Audit Output

Write a JSON report and a concise Markdown summary.

The Markdown summary should include:

- Overall chapter assessment.
- Highest-risk findings first.
- Repeated issue patterns.
- Whether the chapter is safe to import, safe with fixes, or should be blocked pending fixes.

Do not run a DB repair/import or frontend build.
