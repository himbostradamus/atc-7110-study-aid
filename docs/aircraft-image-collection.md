# Aircraft Image Collection

Aircraft images should be treated as reviewed source assets, not generated curriculum.

## Source Policy

- Preferred source: Wikimedia Commons, because file pages expose license, author, credit, and source-page metadata through the API.
- Do not use arbitrary Google Images results.
- Do not show an image to learners until the manifest row has been reviewed for aircraft identity and license usability.
- Keep the image manifest with the image files so every displayed image can be audited.

## Current Collector

```bash
python3 scripts/collect_aircraft_images.py \
  --input backend/app/data/curated_aircraft_jo7360_weighted_rows.csv \
  --output frontend/public/aircraft-images \
  --types BE20,SR22,C72R \
  --per-type 2
```

Outputs:

- `frontend/public/aircraft-images/images/<TYPE>/...`
- `frontend/public/aircraft-images/manifest.csv`
- `frontend/public/aircraft-images/manifest.jsonl`
- `frontend/public/aircraft-images/failures.json`

Manifest rows include `source_page`, `license_short_name`, `license_url`, `artist`, `credit`, `local_path`, `public_path`, and `identity_status`.

## Rate Limit Notes

Wikimedia may reject rapid direct downloads. Keep runs small, use the default conservative delay, and work in batches. If rate-limited, wait before retrying rather than increasing concurrency.

## Review Model

Suggested identity states:

- `not_reviewed`: downloaded but not checked.
- `approved`: aircraft type/designator is visually and textually plausible.
- `wrong_aircraft`: image does not match the designator/model group.
- `bad_angle`: technically correct but not useful for recognition.
- `bad_crop`: source image is usable, but the platform's displayed crop/framing makes it suboptimal.
- `not_recognition_image`: source is not an exterior aircraft-recognition image, such as a cockpit, logo, panel/detail, cabin, or ambiguous multi-aircraft scene.
- `license_hold`: source/license is unclear or unsuitable.

The app should only display `approved` rows.

## In-App Review

The Aircraft Recognition tab now includes:

- `Review Images`: opens the local image candidate review screen.
- `Image Cards`: starts image flashcards, but only after candidates are marked `approved`.

Review decisions are stored in browser localStorage under `atc_aircraft_image_review_v1`. The raw manifest is not mutated by the frontend. This keeps downloaded/source metadata separate from human approval state.

Use `Copy Review JSON` or `Download Review` from the review screen when the browser-local decisions need to be audited or preserved outside the browser. The export includes the local decisions, candidate keys, source links, and computed status for each candidate.
