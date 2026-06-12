# Content Expansion Agent Harness

Numbered authoring passes are isolated from live curriculum and frontend rebuilds.
Each chapter agent owns one file under:

```text
backend/app/data/content_expansion_staging/chapter_XX_pass_NN.json
```

These files are not loaded by the curriculum services. They must be reviewed,
validated, and explicitly published before they can affect the platform.

Agents read:

- the assigned chapter packet under
  `backend/app/data/question_authoring_workspace/expansion/packets/` for pass
  one or `expansion/pass_NN_packets/` for later passes;
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
  backend/app/data/content_expansion_staging/chapter_XX_pass_NN.json \
  --db frontend/public/curriculum.db --strict
```

Pass two and later require zero warnings as well as zero errors. The main
process will audit cross-format duplication, answer cues, source fidelity,
coverage, and whether the author followed the requested modality mix before
publishing staged content.

Monitor the complete run with:

```bash
python scripts/check_content_expansion_agents.py
```

Use `--fail-incomplete` in automation when every chapter must be stopped,
nonempty, and validator-clean before the next stage begins.

If an agent leaves skipped paragraphs as empty `items` arrays, normalize the
batch before review:

```bash
python scripts/normalize_content_expansion_batch.py \
  backend/app/data/content_expansion_staging/chapter_XX_pass_NN.json
```

Before QA review, remove answer-position cues without changing authored text:

```bash
python scripts/rebalance_content_expansion_choices.py \
  backend/app/data/content_expansion_staging/chapter_XX_pass_NN.json
```

Generate pass-specific packets before launching agents:

```bash
python scripts/export_content_expansion_pass_packets.py --pass-number 2
```

These packets rank missing retrieval modes and include legacy quality flags
from every generation source. They are planning inputs only and never affect
the live curriculum.
