# Content remediation

The chapter JSON files in this directory are durable, source-targeted corrections
for learning content originally authored with `generation_src=question_agent`.

They are generated from validated review manifests with:

```bash
python scripts/publish_content_remediation.py
```

Apply them after curriculum generation or repair:

```bash
python scripts/apply_content_remediation.py --db frontend/public/curriculum.db
```

The applier matches the original authored item by stable content fields, changes
only that generation source, and is safe to run again.

After publishing semantic chapter reviews, generate the deterministic enforcement
overlay from a database where those reviews have already been applied:

```bash
python scripts/publish_content_enforcement.py
```
