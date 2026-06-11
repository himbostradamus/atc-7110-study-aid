# Aircraft Image Search Agent Harness

This harness coordinates DeepSeek running through Claude Code to find serviceable aircraft recognition images for JO 7360.1K aircraft cards.

## Purpose

The agents are not curriculum authors. Their job is to find auditable, license-usable, recognition-quality image candidates and leave source-rich manifests for later human review and merge.

## Storage Contract

Agents may only write under:

- `backend/app/data/aircraft_image_search_workspace/outputs/<agent_slug>/`
- `backend/app/data/aircraft_image_search_workspace/logs/`
- `backend/app/data/aircraft_image_search_workspace/prompts/`

Agents must not edit:

- `frontend/**`
- `frontend/public/aircraft-images/**`
- `frontend/dist/**`
- `backend/app/data/curated_*`
- `scripts/collect_aircraft_images.py`
- `scripts/repair_curriculum.py`
- Any database file

The live app reads `frontend/public/aircraft-images`. Keeping agent output outside that directory prevents frontend rebuilds, manifest refreshes, or agent mistakes from replacing reviewed assets.

## Source Policy

Preferred source is Wikimedia Commons. It exposes stable file pages, license metadata, author/credit data, and image URLs through an API.

Agents may use other sources only when all of the following are true:

- The original source page is included.
- The license is explicit and reusable.
- The image URL is stable.
- Author or credit metadata is included.
- The agent clearly states why Commons did not provide enough usable candidates.

No generated images. No unsourced Google Images results. No screenshots from videos unless the video license and frame reuse rights are clear.

## Serviceability Criteria

A serviceable aircraft recognition image should usually have:

- Whole aircraft visible.
- Exterior view.
- Side profile or clean three-quarter view.
- Enough resolution for recognition at card size.
- Minimal occlusion.
- No confusing second aircraft as the main subject.
- Source title, category, or metadata consistent with the target type designator.
- License metadata preserved.

Reject or flag:

- `wrong_aircraft`: type/model does not match.
- `bad_angle`: technically relevant but poor recognition angle.
- `bad_crop`: source image is good, but the platform crop would be poor.
- `not_recognition_image`: cockpit, cabin, logo, diagram, wreck, simulator, panel, or generic scene.
- `license_hold`: license or attribution is unclear.

## Packet Flow

Export target packets:

```bash
python scripts/export_aircraft_image_agent_packet.py --group cessna --batch-size 18
```

The packet tells each agent which type designators need image coverage, how many manifest candidates already exist, and how many reviewed approvals exist if a review JSON export is provided.

Start agents:

```bash
python scripts/start_aircraft_image_search_agents.py --run --max-agents 4
```

Default mode is dry-run. It writes prompt files and prints the commands it would launch.

## Agent Deliverables

Each agent should leave:

- `outputs/<agent_slug>/aircraft-images/manifest.jsonl`
- `outputs/<agent_slug>/aircraft-images/manifest.csv`
- `outputs/<agent_slug>/aircraft-images/failures.json`
- `outputs/<agent_slug>/shortlist.json`
- `outputs/<agent_slug>/agent_report.md`

The `shortlist.json` should include only the agent's best candidates and use this shape:

```json
{
  "agent_slug": "cessna_001",
  "packet": "backend/app/data/aircraft_image_search_workspace/packets/aircraft_image_targets_cessna_001.json",
  "candidates": [
    {
      "type_designator": "C172",
      "source_page": "https://commons.wikimedia.org/wiki/File:Example.jpg",
      "file_title": "File:Example.jpg",
      "public_path": "/aircraft-images/images/C172/example.jpg",
      "identity_status": "not_reviewed",
      "serviceability_notes": "Whole aircraft, side profile, title and metadata match Cessna 172."
    }
  ],
  "shortfalls": [
    {
      "type_designator": "C120",
      "reason": "No serviceable exterior candidates found in this pass."
    }
  ]
}
```

## Recommended Agent Command Pattern

Agents should use the existing collector, with output isolated to their workspace:

```bash
python scripts/collect_aircraft_images.py \
  --input backend/app/data/curated_aircraft_jo7360_weighted_rows.csv \
  --spoken-input backend/app/data/curated_aircraft_designators.csv \
  --output backend/app/data/aircraft_image_search_workspace/outputs/<agent_slug>/aircraft-images \
  --types C172,C182,C210 \
  --per-type 4 \
  --search-limit 10 \
  --thumb-width 960 \
  --min-width 640 \
  --min-height 360 \
  --sleep 1.5 \
  --append
```

Agents can do multiple passes with different type lists or higher `--max-queries-per-type` for hard targets. They should not increase concurrency against Wikimedia.
