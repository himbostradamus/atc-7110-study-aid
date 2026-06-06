# Question Writing Agent Harness

This harness is for an asynchronous authoring agent that produces high-quality ATC Study Aid questions, activities, and flashcards from FAA JO 7110.65 material. The agent is the generator: it should write the content itself, not create procedural generation scripts to author the content.

## Non-Negotiable Storage Contract

Write new authored content only as new append-only batch files under:

- `backend/app/data/curated_overrides_zzzzzzzz_question_agent_chapter_XX_section_YY_batch_NN.json`
- `backend/app/data/curated_flashcards_zzzzzzzz_question_agent_chapter_XX_section_YY_batch_NN.json`

Use zero-padded chapter, section, and batch numbers. Example:

```text
backend/app/data/curated_overrides_zzzzzzzz_question_agent_chapter_02_section_01_batch_03.json
```

Never edit, delete, rename, or reorder existing curated batch files unless the main agent explicitly assigns that specific operation. This is what prevents asynchronous work from being overwritten by frontend rebuilds, database refreshes, or structural changes.

## Files To Avoid

Do not modify these during normal question drafting:

- `frontend/**`
- `frontend/public/curriculum.db`
- `frontend/dist/curriculum.db`
- `curriculum.db`
- `scripts/repair_curriculum.py`
- `backend/app/services/**`
- Existing `backend/app/data/curated_overrides*.json`
- Existing `backend/app/data/curated_flashcards*.json`

The only normal exception is creating a new uniquely named batch file in `backend/app/data/`.

## Workspace Files

Use these support files for planning and validation:

- `backend/app/data/question_authoring_workspace/progress.json`
- `backend/app/data/question_authoring_workspace/templates/curated_overrides_template.json`
- `scripts/export_question_authoring_packet.py`
- `scripts/validate_question_authoring_batch.py`

The progress ledger is helpful, but content batch files are authoritative. If there is a conflict, preserve the batch file and reconstruct progress later.

## Default Ordering

Work in FAA 7110 order:

1. Chapter ascending.
2. Section ascending.
3. Paragraph ascending within section.
4. Multiple passes over each paragraph before moving on.

Do not skip Chapter 1 or Chapter 2. They need the same treatment as later chapters.

## Paragraph Packet

Before authoring a section, export a packet:

```bash
python scripts/export_question_authoring_packet.py --chapter 2 --section 1
```

For one paragraph:

```bash
python scripts/export_question_authoring_packet.py --para-id 2-1-1
```

The packet includes paragraph text, existing questions, activities, flashcards, and current counts. Use it to avoid duplicating existing stems and to understand what is already thin.

## Authoring Ladder

Start slow and move up in complexity. For each paragraph, make several passes:

1. Fill-in-the-blank and cloze: key terms, required conditions, thresholds, lists, exact phraseology where exactness matters.
2. Direct recall: who, what, when, where, and controller obligation questions.
3. Discrimination: true/false or multiple choice that separates similar concepts.
4. List membership and sequence: required elements, exceptions, order of actions, preconditions.
5. Scenario application: short operational facts, then ask what the controller should do or recognize.
6. Source-use lookup: table, figure, minima, exception, or note lookup when the paragraph relies on source structure.
7. Phraseology exactness: only where prescribed phraseology or exact readback is materially important.
8. Misconception traps: common wrong interpretations, but not trick questions.

The goal is not one question per paragraph. The goal is repeated contact with the same concept from different angles.

## Quality Rules

Every item should teach substance, not document trivia.

- Do not test whether a learner memorized that a section title maps to a paragraph number.
- Do not ask "Does this scope or responsibility statement match the paragraph?" without enough operational context.
- Do not ask "Is this an approved example?" using a thin quoted phrase with no topic or source-use context.
- Do not manufacture a phraseology error when a different value is operationally acceptable. Example frequencies, squawk codes, runway numbers, headings, and callsigns may be arbitrary unless the paragraph requires a specific value.
- Do not treat duplicated digits or repeated words as automatically wrong. Controllers may need to say "seven seven zero zero" or similar values in the correct context.
- Use rote memorization only where exact wording, exact sequence, exact phraseology, or exact minima matter.
- Distractors must be plausible operational mistakes, not obviously absurd choices.
- Multiple-choice answers must not always put the correct answer first.
- Every scenario must include enough facts to decide the answer without guessing the source title.
- Every explanation must ground the answer in the paragraph substance and, when possible, identify the operative rule or exception.
- If source text is ambiguous, write a source-use or concept-boundary item instead of pretending there is a single magic answer.

## Recommended Density

Use paragraph density to decide quantity. These are minimum direction-of-travel targets, not hard quotas.

- Thin paragraph: 2-4 fill blanks, 2-4 direct/discrimination questions, 1 scenario or application item, 1-3 flashcards.
- Normal paragraph: 4-8 fill blanks, 4-8 mixed questions, 2-4 scenarios/activities, 2-6 flashcards.
- Dense paragraph: 8-15 fill blanks, 8-15 mixed questions, 4-8 scenarios/activities, table/list/source-use items as needed, 4-10 flashcards.

If quality drops, reduce count. Do not pad.

## Override Shape

Question/activity batches use:

```json
{
  "questions": {
    "2-1-1": {
      "items": [
        {
          "question_text": "In the ATC service rule, what is the system's primary purpose?",
          "question_type": "multiple_choice",
          "difficulty": 2,
          "source_block": "body",
          "generation_source": "question_agent",
          "explanation": "The paragraph states that preventing collisions involving aircraft operating in the system is the primary purpose.",
          "choices": [
            {"text": "Prevent collisions involving aircraft operating in the system.", "is_correct": true},
            {"text": "Support National Security and Homeland Defense as the only mission.", "is_correct": false},
            {"text": "Provide optional additional services whenever a pilot requests them.", "is_correct": false},
            {"text": "Move every aircraft as quickly as possible regardless of separation needs.", "is_correct": false}
          ]
        }
      ]
    }
  },
  "activities": {
    "2-1-1": {
      "items": [
        {
          "activity_type": "situation_action",
          "generation_source": "question_agent",
          "difficulty": 3,
          "instruction": "Choose the controller priority that best fits the situation.",
          "situation": "Traffic is heavy, the frequency is saturated, and a pilot asks for an additional advisory service that would distract from active separation duties.",
          "question_text": "How should the controller treat the additional service request?",
          "choices": [
            {"text": "Provide it only to the extent the work situation permits.", "is_correct": true},
            {"text": "Provide it immediately because additional services are always mandatory.", "is_correct": false},
            {"text": "Refuse it because additional services are optional for controllers.", "is_correct": false}
          ],
          "explanation": "Additional services are required when the work situation permits, but workload, frequency congestion, and higher-priority duties may preclude them."
        }
      ]
    }
  }
}
```

Flashcard batches use:

```json
{
  "flashcards": {
    "2-1-1": {
      "items": [
        {
          "front": "ATC system: primary purpose",
          "back": "Prevent collisions involving aircraft operating in the system.",
          "card_type": "concept",
          "generation_source": "question_agent"
        }
      ]
    }
  }
}
```

## Validation

Before handoff, run:

```bash
python scripts/validate_question_authoring_batch.py backend/app/data/curated_overrides_zzzzzzzz_question_agent_chapter_02_section_01_batch_03.json
```

For flashcards:

```bash
python scripts/validate_question_authoring_batch.py backend/app/data/curated_flashcards_zzzzzzzz_question_agent_chapter_02_section_01_batch_03.json
```

Warnings are not automatic failures, but do not ignore warnings about underspecified stems, duplicate choices, or answer-position bias.

## Handoff Format

When stopping, leave:

- New batch file paths.
- Paragraphs covered.
- Any validation failures or unresolved warnings.
- Any source ambiguity that needs human review.

Do not run a DB repair or frontend build unless the main agent explicitly requests it.
