Static assets served by the frontend belong here.

The generated curriculum database should be published to:

`frontend/public/curriculum.db`

Do not place `curriculum.db.*.bak` files here; Vite copies every file in this directory into the public site.

Do not treat aircraft image candidates in `aircraft-images/` as learner-facing content unless a human has verified aircraft identity, recognition usefulness, and reuse metadata. Public/static builds should hide internal image-review tooling and only expose approved image cards.

Example:

```bash
python scripts/generate_curriculum.py \
  --source "/path/to/faa/source-documents" \
  --out curriculum.db \
  --publish frontend/public
```
