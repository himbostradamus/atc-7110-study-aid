# Content Expansion Agent Harness

Second-round authoring is isolated from live curriculum and frontend rebuilds.
Each chapter agent owns one file under:

```text
backend/app/data/content_expansion_staging/chapter_XX_pass_01.json
```

These files are not loaded by the curriculum services. They must be reviewed,
validated, and explicitly published before they can affect the platform.

Agents read:

- the assigned chapter packet under
  `backend/app/data/question_authoring_workspace/expansion/packets/`;
- the chapter remediation summary under
  `backend/app/data/content_remediation/chapter_XX.json`;
- `docs/question-writing-agent-harness.md`;
- `docs/content-expansion-agent-prompt.md`.

Agents must not modify any other path. A full pass means every paragraph was
read and compared with current questions, activities, and flashcards, even when
the correct decision is to add nothing.

Validate with:

```bash
python scripts/validate_question_authoring_batch.py \
  backend/app/data/content_expansion_staging/chapter_XX_pass_01.json \
  --db frontend/public/curriculum.db
```

Warnings require judgment; errors must be resolved. The main process will audit
cross-format duplication, answer cues, source fidelity, and coverage before
publishing staged content.

Monitor the complete run with:

```bash
python scripts/check_content_expansion_agents.py
```

Use `--fail-incomplete` in automation when every chapter must be stopped,
nonempty, and validator-clean before the next stage begins.
