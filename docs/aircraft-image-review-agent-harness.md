# Aircraft Image Review Agent Harness

This harness prepares DeepSeek/Claude Code review agents for aircraft image candidates.

Review agents are separate from search agents. Search agents gather candidates. Review agents classify whether candidates are serviceable for aircraft recognition.

## Review Lanes

Create separate review packets for the main rejection filters:

- `wrong_aircraft`: aircraft identity, model, or type designator mismatch.
- `not_recognition_image`: not an exterior aircraft recognition image, including cockpit, cabin, logo, diagram, wreck, simulator, panel/detail, generic airport scene, or confusing multi-aircraft image.
- `bad_angle`: aircraft may be correct, but view angle is poor for recognition.

Agents may also use:

- `bad_crop`: source image is usable, but the current platform crop or framing would be poor.
- `license_hold`: source/license/credit metadata is unclear.
- `approved`: whole-aircraft exterior view is serviceable and identity is plausible.
- `not_reviewed`: insufficient confidence after review.

## Storage Contract

Review agents may only write under:

- `backend/app/data/aircraft_image_search_workspace/outputs/<review_slug>/review_decisions.json`
- `backend/app/data/aircraft_image_search_workspace/outputs/<review_slug>/review_report.md`
- `backend/app/data/aircraft_image_search_workspace/logs/`
- `backend/app/data/aircraft_image_search_workspace/prompts/`

They must not edit:

- `frontend/**`
- `frontend/public/aircraft-images/**`
- `frontend/dist/**`
- `backend/app/data/curated_*`
- Search-agent manifests
- Database files

## Packet Flow

Create packets:

```bash
python scripts/export_aircraft_image_review_packet.py --focus wrong_aircraft
python scripts/export_aircraft_image_review_packet.py --focus not_recognition_image
python scripts/export_aircraft_image_review_packet.py --focus bad_angle
```

Prepare prompts:

```bash
python scripts/start_aircraft_image_review_agents.py
```

Launch only when explicitly desired:

```bash
python scripts/start_aircraft_image_review_agents.py --run --max-agents 3
```

## Decision Shape

Review agents output:

```json
{
  "agent_slug": "review_wrong_aircraft_001",
  "packet": "backend/app/data/aircraft_image_search_workspace/packets/aircraft_image_review_wrong_aircraft_001.json",
  "decisions": {
    "sha256-or-stable-key": {
      "identity_status": "wrong_aircraft",
      "confidence": "high",
      "review_notes": "Source title says A319 but target is A320; visible fuselage/door layout also does not support target."
    }
  }
}
```

The main agent or a human reviewer later merges decisions into the app review workflow.

