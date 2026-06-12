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

## Essential-Element Map

Before writing any item, make a private concept map for the paragraph. Identify:

- The operational purpose or controlling principle.
- Each obligation and prohibition.
- Each trigger, prerequisite, and termination condition.
- Each exception, boundary, and workload qualification.
- Each number, minimum, sequence, or list whose exact value matters.
- Any prescribed phraseology whose wording must be recalled faithfully.
- The most plausible operational misconception.

Do not turn every sentence into a question. Prioritize the elements that change a controller's decision, transmission, coordination, separation, or source lookup.

For each important concept, build a small concept family using at least two genuinely different retrieval modes:

- Direct recall of the controlling rule.
- Condition or exception discrimination.
- Short scenario application.
- Contrast with a nearby concept or realistic misconception.
- Exact recall only when wording, order, or a value is prescribed.

Synonym swaps and minor stem rewrites are duplicates, not reinforcement. A second item earns its place only when it changes what the learner must notice or reason about.

Assign each format a distinct job where practical:

- Flashcard: concise retrieval of the controlling fact, trigger, boundary, value, sequence, or prescribed wording.
- Question: discriminate the rule from a plausible misconception, exception, or neighboring concept.
- Activity: apply the same concept to operational facts, phraseology construction, sequencing, or source use.

Do not copy the same stem into all three formats. A paragraph does not have broad coverage merely because the same direct-recall prompt exists as a card, question, and activity.

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
- Do not begin ordinary questions with "Under 2-1-1," or similar paragraph-number scaffolding. Paragraph numbers belong in citations, not in the learner's reasoning context, unless the task explicitly teaches source navigation.
- Do not ask "Does this scope or responsibility statement match the paragraph?" without enough operational context.
- Do not ask "Is this an approved example?" using a thin quoted phrase with no topic or source-use context.
- Do not manufacture a phraseology error when a different value is operationally acceptable. Example frequencies, squawk codes, runway numbers, headings, and callsigns may be arbitrary unless the paragraph requires a specific value.
- Do not treat duplicated digits or repeated words as automatically wrong. Controllers may need to say "seven seven zero zero" or similar values in the correct context.
- Use rote memorization only where exact wording, exact sequence, exact phraseology, or exact minima matter.
- Distractors must be plausible operational mistakes, not obviously absurd choices.
- Stored choice position is not a quality signal; the application shuffles choices at runtime.
- Prefer positive operational decisions. Use `NOT` or `EXCEPT` only when identifying an exclusion is itself the required skill.
- Every scenario must include enough facts to decide the answer without guessing the source title.
- Every explanation must state the controlling principle and, for multiple choice, explain why the strongest plausible distractor fails.
- Important concepts should appear in at least two retrieval modes before lower-value details receive additional paraphrases.
- If source text is ambiguous, write a source-use or concept-boundary item instead of pretending there is a single magic answer.

Flashcard-specific rules:

- The front must be an explicit, independently understandable retrieval cue. Avoid labels such as "MARSA authority" or "First duty priority" when a short question would remove ambiguity.
- Test one coherent target per card. Split large procedures and long lists unless recalling the complete set as a unit is operationally important.
- Keep citations and paragraph numbers out of the cue and answer unless the card explicitly teaches source navigation.
- A reverse card must actually work in reverse: one side supplies the fact or term and the other side asks a clear question. A paragraph title or label is not a reverse prompt.
- Do not duplicate a question stem verbatim as a flashcard. Use the card for compact recall and the question for discrimination or application.

Activity-specific rules:

- Scenario and decision activities must contain all facts needed to choose an action without knowing the paragraph title.
- Use activities for application, sequencing, phraseology assembly, source lookup, and misconception discrimination rather than another direct-recall wrapper.
- Do not spend authoring effort rearranging otherwise unchanged choices; runtime controls their displayed order.
- Keep the correct answer and distractors comparable in length, detail, grammar, and specificity. The longest option must not routinely reveal the answer.
- Binary checks are acceptable only when true/false discrimination is educationally useful; otherwise provide at least three plausible operational choices.
- The activity explanation must state the controlling rule and address the strongest realistic alternative.

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

After the database is refreshed, the main agent can audit the complete authored corpus with:

```bash
python scripts/audit_learning_content_output.py --fail-on-regression
```

## Handoff Format

When stopping, leave:

- New batch file paths.
- Paragraphs covered.
- Any validation failures or unresolved warnings.
- Any source ambiguity that needs human review.

Do not run a DB repair or frontend build unless the main agent explicitly requests it.
