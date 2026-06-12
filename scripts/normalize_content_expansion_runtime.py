#!/usr/bin/env python3
"""Make expansion activities satisfy the runtime activity contract."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "backend" / "app" / "data" / "content_expansion_staging"
DB = ROOT / "frontend" / "public" / "curriculum.db"


def load_titles() -> dict[str, str]:
    db = sqlite3.connect(DB)
    try:
        return {
            str(para_id): str(title or "")
            for para_id, title in db.execute("SELECT para_id, title FROM paragraphs")
        }
    finally:
        db.close()


def clean_lead(text: object, *, explanation: bool = False) -> object:
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"\s+([,.;:?!])", r"\1", text.strip())
    if explanation and re.match(r"^\d+(?:-\d+)+", cleaned):
        cleaned = f"Paragraph {cleaned}"
    match = re.search(r"[A-Za-z]", cleaned)
    if match and cleaned[match.start()].islower():
        cleaned = cleaned[: match.start()] + cleaned[match.start()].upper() + cleaned[match.start() + 1 :]
    return cleaned


def special_repairs(payloads: dict[int, dict[str, Any]]) -> None:
    chapter_02 = payloads[2]
    chapter_02["activities"]["2-6-3"]["items"][0]["choices"][1]["text"] = (
        "2.5 miles. Use the lower of the tower and surface observations for aircraft operations."
    )
    chapter_02["activities"]["2-8-2"]["items"][0]["choices"][3]["text"] = (
        "Yes. An RVR of 5,500 feet is reportable, so issue it regardless of prevailing visibility."
    )

    chapter_03 = payloads[3]
    chapter_03["activities"]["3-1-6"]["items"] = [
        {
            "activity_type": "discrimination",
            "generation_source": "question_agent",
            "difficulty": 2,
            "instruction": "Select the traffic description that most directly helps the pilot recognize the hazard.",
            "situation": (
                "An aircraft is approaching Runway 18 while a mower is operating "
                "just left of that runway."
            ),
            "question_text": "Which advisory uses the prescribed plain relative-position format?",
            "choices": [
                {"text": "MOWER LEFT OF RUNWAY ONE EIGHT.", "is_correct": True},
                {"text": "GROUND EQUIPMENT IN THE GENERAL AIRPORT AREA.", "is_correct": False},
                {"text": "CAUTION, VEHICLE SOMEWHERE NEAR THE MOVEMENT AREA.", "is_correct": False},
                {"text": "MOWER TRAFFIC, POSITION UNKNOWN.", "is_correct": False},
            ],
            "explanation": (
                "Describe vehicles, equipment, or personnel in a way that helps "
                "the pilot recognize them. A direct relative position such as "
                "\"Mower left of runway one eight\" supplies that useful context."
            ),
        }
    ]

    chapter_05 = payloads[5]
    chapter_05["activities"]["5-1-3"]["items"][0]["explanation"] = (
        "Include the facility name, EA activity type, affected radar band, and, "
        "when feasible, the expected suspension duration."
    )
    chapter_05["activities"]["5-13-4"]["items"][0]["explanation"] = (
        "Enter the reported altitude at assigned altitude, when issuing a climb "
        "or descent, and at least each 10,000 feet while climbing to or descending "
        "from FL180 and above."
    )

    chapter_06 = payloads[6]
    item = chapter_06["activities"]["6-5-4"]["items"][0]
    item["choices"][0]["text"] = (
        "17 miles on the overflown side because the change is 16 through 90 degrees and the aircraft is above FL230."
    )
    item["choices"][1]["text"] = (
        "14 miles on the overflown side, which applies from FL180 through FL230."
    )
    item["choices"][2]["text"] = (
        "28 miles on the overflown side, which applies to a larger course-change range."
    )
    item["choices"][3]["text"] = (
        "Use direct-course protection because a 45-degree change needs no additional overflown-side protection."
    )
    chapter_06["activities"]["6-6-3"]["items"][0]["choices"][1]["text"] = (
        "Yes, but the authorization would have to be assigned to Aircraft B "
        "regardless of which aircraft is descending."
    )

    chapter_07 = payloads[7]
    repairs = {
        "7-1-3": {
            "situation": (
                "Established local procedures call for arriving VFR aircraft to "
                "contact approach control for landing information. A VFR arrival "
                "instead makes initial contact with the tower."
            ),
            "question_text": "What should the tower instruct the aircraft to do?",
        },
        "7-3-1": {
            "situation": (
                "An IFR aircraft requests a climb through an overcast layer to "
                "VFR-on-top. No tops report is available, and 8,000 feet is the "
                "altitude at which the controller wants the pilot to stop and advise."
            ),
            "question_text": "Which transmission correctly provides the clearance and fallback?",
        },
        "7-4-7": {
            "situation": (
                "A pilot requests a contact approach with reported ground visibility "
                "of 1 mile. Fog may make the approach impracticable, and the ILS "
                "Runway 18 approach is available as a backup."
            ),
            "question_text": "Which clearance includes the required alternative procedure?",
        },
        "7-5-2": {
            "situation": (
                "An SVFR arrival is about 2 minutes from landing when an IFR "
                "aircraft becomes ready for departure. Sending the SVFR aircraft "
                "around would create more total delay."
            ),
            "question_text": "How may the controller apply IFR priority efficiently?",
        },
    }
    for para_id, updates in repairs.items():
        chapter_07["activities"][para_id]["items"][0].update(updates)

    visual = chapter_07["activities"]["7-4-1"]["items"][0]
    visual["situation"] = (
        "An IFR aircraft executes a go-around from a visual approach at an airport "
        "without an operating control tower because a deer is on the runway."
    )
    visual["question_text"] = "What is expected after the go-around?"
    visual["choices"] = [
        {
            "text": (
                "Complete a landing as soon as possible or contact ATC for further "
                "clearance while ATC maintains approved IFR separation."
            ),
            "is_correct": True,
        },
        {
            "text": "Fly the published missed approach for an instrument procedure to the same runway.",
            "is_correct": False,
        },
        {
            "text": "Cancel IFR immediately and continue solely under VFR.",
            "is_correct": False,
        },
        {
            "text": "Hold over the airport at the MVA until the runway becomes available.",
            "is_correct": False,
        },
    ]
    visual["explanation"] = (
        "A visual approach has no missed-approach segment. At an airport without "
        "an operating tower, an aircraft that goes around is expected to complete "
        "a landing as soon as possible or contact ATC for further clearance. ATC "
        "must maintain approved separation from other IFR aircraft."
    )


def main() -> int:
    titles = load_titles()
    paths = sorted(STAGING.glob("chapter_*_pass_01.json"))
    payloads = {
        int(path.stem.split("_")[1]): json.loads(path.read_text(encoding="utf-8"))
        for path in paths
    }
    special_repairs(payloads)

    changed = 0
    for chapter, payload in payloads.items():
        for para_id, override in payload.get("activities", {}).items():
            for activity in override.get("items", []):
                if activity.get("activity_type") == "situation_action":
                    if not str(activity.get("para_context") or "").strip():
                        activity["para_context"] = titles.get(para_id, "")
                        changed += 1
                for field in (
                    "instruction",
                    "situation",
                    "question_text",
                    "explanation",
                ):
                    before = activity.get(field)
                    after = clean_lead(before, explanation=field == "explanation")
                    if after != before:
                        activity[field] = after
                        changed += 1

        path = STAGING / f"chapter_{chapter:02d}_pass_01.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    print(f"Normalized runtime activity content across {len(payloads)} chapters ({changed} field updates).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
