# Chapter Content Remediation Agent Harness

This harness governs chapter-scoped review and remediation of assigned
questions, flashcards, and activities. It is intentionally separate from live
curriculum files.

## Goal

Each agent must review one complete FAA JO 7110.65 chapter and:

- verify source fidelity against the source blocks in its packet;
- identify items that teach paragraph-location trivia instead of ATC substance;
- correct underspecified prompts, weak distractors, answer-position or answer-length
  cues, thin explanations, malformed reverse cards, and context-light cards;
- preserve exact recall where prescribed phraseology, required readbacks, minima,
  codes, sequences, or defined terms genuinely require it;
- prefer operational decisions, conditions, exceptions, responsibilities, and
  source-use skills over superficial verbatim repetition;
- avoid duplicating the same concept in the same retrieval mode.

## Safety Boundary

Agents write only under:

```text
backend/app/data/question_authoring_workspace/remediation/
```

They must not edit:

- curated override or flashcard JSON;
- SQLite or PostgreSQL databases;
- frontend files;
- repair/import scripts;
- source documents;
- another chapter agent's output.

The output is a proposed remediation manifest. It does not become curriculum
until a separate deterministic integration step validates and applies it.

## Required Review Scope

Review every target item in the assigned packet:

- quiz questions from the packet's `target_generation_source`;
- activities from the packet's `target_generation_source`;
- flashcards from the packet's `target_generation_source`.

The manifest must list every target ID in `reviewed_item_ids`, grouped by entity
type. The validator rejects incomplete or foreign ID coverage.

## Item Decisions

Create a decision only when an item needs intervention:

- `replace`: substitute one complete item.
- `remove`: delete an item that is wrong, redundant, or educationally harmful.
- `split`: replace an overloaded item with two or more focused items.

Do not emit redundant `keep` decisions. Complete review is represented by the
`reviewed_item_ids` ledger.

Every decision requires:

- stable `item_id`;
- matching `entity_type` and `para_id`;
- severity and defect categories;
- a concrete explanation of the problem;
- source basis stated from the packet;
- a complete replacement payload for `replace` or `split`.

## Quality Standards

### Questions

- The stem must be self-contained without requiring paragraph-number knowledge.
- Exactly one answer is correct for multiple choice and true/false.
- Distractors must represent plausible operational mistakes.
- Explanation must teach the controlling rule, condition, exception, or reason.
- Do not invent a safety rationale, policy purpose, or operational consequence
  that is not supported by the packet's source blocks.
- Negative stems are used only when exclusion recognition is the actual skill.
- Do not manufacture phraseology errors from arbitrary frequencies, runway
  numbers, callsigns, duplicate digits, or squawk codes.
- Do not intervene solely because the correct answer is first in stored data;
  the application randomizes choice order at runtime. Do intervene when answer
  wording, length, specificity, or implausible distractors reveal the answer.

### Flashcards

- The front must identify the concept being recalled.
- The back must be concise enough for one retrieval target.
- Reverse cards must be valid questions in both directions.
- Split long lists or multi-rule dumps unless the complete list itself is the
  required retrieval target.
- Exact wording is appropriate for prescribed phraseology and defined terms,
  but not as a substitute for operational understanding.

### Activities

- The activity type must match the skill.
- Inspect the complete activity `content` object. Activity schemas vary across
  types; fields such as `original_phrase`, `display_text`, `clearance`,
  `question_text`, `situation`, and `choices` may carry the substantive task.
  Never classify an activity as empty merely because a generic `prompt` field
  is absent.
- Scenario and source-use activities need enough operational context.
- Table and figure items must identify the source and ask for a lookup decision,
  not merely ask whether an isolated value is “approved.”
- Choice activities follow the same answer and distractor standards as questions.
- Explanations must connect the answer to the operational principle.

## Output Files

Use the exact output paths supplied in the assignment prompt:

```text
chapter_XX_pass_NN.json
chapter_XX_pass_NN.md
```

The packet and output directories may be namespaced by generation source, for
example `packets/curated/` and `outputs/curated/chapter_05/`. Always use the
exact paths supplied in the assigned prompt. Never write into another source or
pass namespace.

Write valid JSON incrementally to a temporary file if needed, then rename it to
the required final path only when the chapter pass is complete.

## Manifest Shape

```json
{
  "version": 1,
  "audit_type": "chapter_content_remediation",
  "chapter": 5,
  "pass": 1,
  "status": "complete",
  "reviewed_at": "YYYY-MM-DDTHH:MM:SSZ",
  "reviewed_item_ids": {
    "question": ["..."],
    "activity": ["..."],
    "flashcard": ["..."]
  },
  "summary": {
    "overall": "...",
    "patterns": ["..."],
    "generation_guidance": ["..."]
  },
  "decisions": [
    {
      "entity_type": "question",
      "item_id": "...",
      "para_id": "5-2-3",
      "action": "replace",
      "severity": "major",
      "categories": ["context", "educational_coherence"],
      "problem": "...",
      "source_basis": "...",
      "replacement": {
        "question_text": "...",
        "question_type": "multiple_choice",
        "difficulty": 3,
        "explanation": "...",
        "choices": [
          {"text": "...", "is_correct": false},
          {"text": "...", "is_correct": true},
          {"text": "...", "is_correct": false},
          {"text": "...", "is_correct": false}
        ]
      }
    }
  ]
}
```

For `split`, `replacement` is an array of complete replacement objects.

## Completion

Before finishing, run:

```bash
python scripts/validate_content_remediation_manifest.py \
  --packet ASSIGNED_PACKET \
  --manifest OUTPUT_JSON
```

Fix all errors. Warnings require review but do not necessarily block completion.
