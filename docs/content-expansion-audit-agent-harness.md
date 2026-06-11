# Content Expansion Audit Agent Harness

Each chapter audit is isolated from live curriculum. Reviewers read:

```text
backend/app/data/content_expansion_staging/chapter_XX_pass_01.json
backend/app/data/question_authoring_workspace/expansion/packets/chapter_XX.json
backend/app/data/content_remediation/chapter_XX.json
```

They write only:

```text
backend/app/data/content_expansion_audits/chapter_XX_pass_01.json
backend/app/data/content_expansion_audits/chapter_XX_pass_01.md
```

Reports are append-only review artifacts. They do not affect the application.
Every staged item must appear exactly once in `reviewed_item_paths`.

Validate a report with:

```bash
python scripts/validate_content_expansion_audit.py \
  --batch backend/app/data/content_expansion_staging/chapter_XX_pass_01.json \
  --report backend/app/data/content_expansion_audits/chapter_XX_pass_01.json
```

No staged content is published until critical and major findings are resolved
and the resulting batches are revalidated.
