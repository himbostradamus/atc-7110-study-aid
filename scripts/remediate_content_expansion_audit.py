#!/usr/bin/env python3
"""Apply the critical and major findings from expansion audit pass 01."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "backend" / "app" / "data" / "content_expansion_staging"
AUDITS = ROOT / "backend" / "app" / "data" / "content_expansion_audits"
REPORT = AUDITS / "remediation_pass_01.json"


def load_chapter(chapter: int) -> tuple[Path, dict[str, Any]]:
    path = STAGING / f"chapter_{chapter:02d}_pass_01.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def item(payload: dict[str, Any], family: str, para_id: str, index: int = 0) -> dict[str, Any]:
    return payload[family][para_id]["items"][index]


def remove_item(payload: dict[str, Any], family: str, para_id: str, index: int = 0) -> None:
    del payload[family][para_id]["items"][index]
    if not payload[family][para_id]["items"]:
        del payload[family][para_id]


def move_item(
    payload: dict[str, Any],
    family: str,
    source_para: str,
    destination_para: str,
    index: int = 0,
) -> None:
    moved = payload[family][source_para]["items"].pop(index)
    payload[family].setdefault(destination_para, {"items": []})["items"].append(moved)
    if not payload[family][source_para]["items"]:
        del payload[family][source_para]


def choice(text: str, correct: bool, sort_order: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"text": text, "is_correct": correct}
    if sort_order is not None:
        result["sort_order"] = sort_order
    return result


def remediate_chapter_02(payload: dict[str, Any]) -> None:
    activity = item(payload, "activities", "2-4-19")
    activity["situation"] = (
        "Columbus, Mississippi has both an Air Force Base and Golden Triangle "
        "Regional Airport in the same general area."
    )
    activity["question_text"] = "How should the Air Force Base tower be identified on frequency?"
    activity["explanation"] = (
        "When military and civil airports in the same general area have similar "
        "names, state the military service, the military facility name, and "
        "\"Tower.\" The applicable identification is \"Air Force Columbus Tower.\""
    )

    activity = item(payload, "activities", "2-4-16")
    activity["instruction"] = "Apply prescribed phonetic and number pronunciation."
    activity["situation"] = (
        "On a noisy frequency, a controller must transmit the aircraft identification N5JQ."
    )
    activity["question_text"] = "Which transmission uses the prescribed pronunciations?"
    activity["choices"] = [
        choice("November Five Juliett Quebec.", False),
        choice("November Fife Juliett Quebec.", True),
        choice("Nancy Fife John Queen.", False),
        choice("November Fife Japan Quebec.", False),
    ]
    activity["explanation"] = (
        "Use the prescribed spoken forms for individual characters: November, "
        "Fife, Juliett, Quebec. The operational skill is clear pronunciation; "
        "the numeral 5 is spoken \"Fife,\" not \"Five.\""
    )

    card = item(payload, "flashcards", "2-3-2")
    card["front"] = (
        "What strip entry supports identification of the controlling position "
        "for a recorded transmission?"
    )
    card["back"] = (
        "The sector or position number entry. On the en route flight progress "
        "strip, it is recorded in block 26 when applicable."
    )

    remove_item(payload, "activities", "2-9-2")

    activity = item(payload, "activities", "2-2-14")
    activity["instruction"] = "Apply Canadian-to-U.S. flight-data format requirements."
    activity["situation"] = (
        "A Canadian ACC must send a correction to flight data previously transmitted "
        "to an FAA ARTCC."
    )
    activity["question_text"] = "Which handling is supported by the prescribed exchange format?"
    activity["choices"] = [
        choice("Send a NADIN II correction message to the FAA ARTCC.", True),
        choice("Send only a cancellation, then require the pilot to file a new flight plan.", False),
        choice("Use the U.S.-to-Canada strip format because correction messages are not supported.", False),
        choice("Delay the correction until the aircraft checks in with the FAA ARTCC.", False),
    ]
    activity["explanation"] = (
        "Canadian ACC transmissions to FAA ARTCCs may use the NADIN II input "
        "format for correction messages. Apply the permitted message format to "
        "the operational need rather than comparing document lists."
    )

    card = item(payload, "flashcards", "2-2-10")
    card["front"] = (
        "When must NADIN forward a proposed flight plan to all affected centers "
        "even though Computer B is operating?"
    )
    card["back"] = (
        "When the route contains more than 20 elements outside the originating "
        "ARTCC's area. The route scope triggers NADIN forwarding regardless of "
        "Computer B network status."
    )


def remediate_chapter_03(payload: dict[str, Any]) -> None:
    move_item(payload, "questions", "3-10-3", "3-10-2")
    move_item(payload, "questions", "3-7-5", "3-7-1")
    move_item(payload, "flashcards", "3-7-5", "3-7-1")


def remediate_chapter_04(payload: dict[str, Any]) -> None:
    card = item(payload, "flashcards", "4-7-10")
    card["back"] = (
        "(Airport) AWOS/ASOS WEATHER AVAILABLE ON (frequency). Example: "
        "\"AIRPORT AWOS WEATHER AVAILABLE ON ONE TWO EIGHT POINT THREE TWO.\" "
        "If the pilot cannot receive the broadcast, issue the last long-line "
        "disseminated weather."
    )

    question = item(payload, "questions", "4-5-6")
    question["explanation"] = (
        "When a higher MEA begins at a fix and no MCA is specified, clear the "
        "aircraft to begin the climb prior to or immediately after passing that "
        "fix. Unlike an MCA case, the rule does not require the aircraft to cross "
        "the fix already level at the higher MEA."
    )
    question["choices"] = [
        choice(
            "Clear the aircraft to begin climbing prior to or immediately after passing RIGEL.",
            True,
        ),
        choice(
            "Require the aircraft to be level at the higher MEA before crossing RIGEL.",
            False,
        ),
        choice("Wait until the aircraft is at least 5 NM beyond RIGEL.", False),
        choice("Begin the climb only after the pilot reports unable to maintain the lower MEA.", False),
    ]

    move_item(payload, "questions", "4-6-4", "4-6-1")
    question = payload["questions"]["4-6-1"]["items"][-1]
    question["question_text"] = (
        "The assigned route includes a charted holding pattern. If complete "
        "holding instructions are not requested, what must the controller still issue?"
    )
    question["explanation"] = (
        "For a charted holding pattern included in the assigned procedure or "
        "route, the controller may omit the detailed holding elements but must "
        "still issue the charted holding direction and the statement \"as published.\" "
        "Complete instructions are required if the pilot requests them."
    )
    question["choices"] = [
        choice("The charted holding direction and the statement \"as published.\"", True),
        choice("Only the holding fix because the chart supplies the direction.", False),
        choice("The radial, leg length, and turn direction in every case.", False),
        choice("No holding information because the entire clearance is implied by the chart.", False),
    ]


def remediate_chapter_05(payload: dict[str, Any]) -> None:
    question = item(payload, "questions", "5-5-1")
    question["question_text"] = (
        "An RNAV aircraft at FL430 is flying point-to-point via an impromptu route "
        "outside oceanic airspace. Does the mandatory Q-route/random-RNAV rule in "
        "5-5-1a apply solely because the aircraft is RNAV-equipped?"
    )
    question["explanation"] = (
        "No. The mandatory application in 5-5-1a covers RNAV aircraft at and "
        "below FL450 on Q routes or random RNAV routes outside oceanic airspace, "
        "but expressly excepts point-to-point routes via an impromptu route. "
        "Other applicable separation requirements still remain."
    )
    question["choices"] = [
        choice("No. Point-to-point travel via an impromptu route is the stated exception.", True),
        choice("Yes. Every RNAV aircraft at or below FL450 is included regardless of routing.", False),
        choice("Yes, but only when the aircraft is below FL180.", False),
        choice("No, because radar separation is never applied to impromptu routes.", False),
    ]

    payload["flashcards"]["5-5-9"]["items"] = [
        {
            "front": "What primary terminal obstruction separation applies based on distance from the radar antenna?",
            "back": "Less than 40 miles: 3 miles. At 40 miles or more: 5 miles.",
            "card_type": "threshold",
            "generation_source": "question_agent",
        },
        {
            "front": "What obstruction separation applies to FUSION targets?",
            "back": "Use 3 miles for a FUSION target symbol, or 5 miles when an ISR is displayed.",
            "card_type": "threshold",
            "generation_source": "question_agent",
        },
    ]

    card = item(payload, "flashcards", "5-2-12")
    card["front"] = (
        "What should a controller tell an aircraft when its transponder appears "
        "inoperative or malfunctioning?"
    )
    card["back"] = (
        "Advise that the transponder appears inoperative or malfunctioning, then "
        "instruct the aircraft to reset and squawk the appropriate code."
    )

    card = item(payload, "flashcards", "5-2-22")
    card["front"] = (
        "What must be done if a malfunctioning ADS-B transmitter jeopardizes the "
        "safe execution of ATC functions?"
    )
    card["back"] = (
        "Instruct the aircraft to stop ADS-B transmissions and notify the OS/CIC. "
        "If able, the aircraft should squawk the assigned Mode 3/A code."
    )

    card = item(payload, "flashcards", "5-4-8")
    card["front"] = (
        "Does Automated Information Transfer remove the need for coordination "
        "awareness between affected positions?"
    )
    card["back"] = (
        "No. AIT may be bidirectional and involve more than two sectors; complete "
        "coordination, traffic-flow awareness, and shared understanding of each "
        "position's responsibilities remain essential."
    )

    remove_item(payload, "flashcards", "5-13-7")

    card = item(payload, "flashcards", "5-3-2")
    card["front"] = (
        "Which coordination methods support identifying a departing aircraft "
        "within 1 mile of the runway end?"
    )
    card["back"] = (
        "A verbal rolling or boundary notification for each departure, or a "
        "nonverbal rolling or boundary notification for each departure aircraft."
    )


def remediate_chapter_06(payload: dict[str, Any]) -> None:
    activity = item(payload, "activities", "6-6-3")
    activity["choices"][2]["text"] = (
        "Yes; Aircraft A is the upper aircraft descending toward Aircraft B, "
        "which matches the permitted assignment."
    )


def remediate_chapter_07(payload: dict[str, Any]) -> None:
    question = item(payload, "questions", "7-6-7")
    question["question_text"] = (
        "A faster trailing VFR aircraft is closing on an aircraft established on "
        "final to an adjacent parallel runway 2,000 feet away. Wake turbulence "
        "separation is required. What restriction applies?"
    )
    question["explanation"] = (
        "When parallel runways are less than 2,500 feet apart, do not permit an "
        "aircraft to overtake another aircraft established on the adjacent final "
        "within the facility's area of responsibility when wake turbulence "
        "separation is required. The prohibition is conditional, not universal."
    )
    question["choices"] = [
        choice(
            "The trailing aircraft must not overtake while wake turbulence separation is required.",
            True,
            0,
        ),
        choice("Overtaking is allowed if both pilots report the other aircraft in sight.", False, 1),
        choice("Overtaking is allowed if 1,000 feet vertical separation is maintained.", False, 2),
        choice("No restriction applies because the aircraft are assigned different runways.", False, 3),
    ]

    payload["flashcards"]["7-4-5"]["items"] = [
        {
            "front": "What weather minimums normally permit a Charted Visual Flight Procedure?",
            "back": (
                "Reported ceiling at least 500 feet above the MVA or MIA and "
                "visibility at least 3 miles, unless the published CVFP requires higher minimums."
            ),
            "card_type": "threshold",
            "generation_source": "question_agent",
        },
        {
            "front": "What visual reference is required for an aircraft not following another aircraft on a CVFP?",
            "back": (
                "The pilot must report a charted visual landmark in sight, or report "
                "a preceding aircraft landing on the same runway in sight after being instructed to follow it."
            ),
            "card_type": "requirement",
            "generation_source": "question_agent",
        },
        {
            "front": "What must a CVFP approach clearance identify?",
            "back": (
                "The published CVFP name and the landing runway. An operating "
                "control tower is also required."
            ),
            "card_type": "phraseology",
            "generation_source": "question_agent",
        },
    ]


def remediate_chapter_09(payload: dict[str, Any]) -> None:
    activity = item(payload, "activities", "9-1-2")
    activity["choices"] = [
        choice(
            "Ask the flight inspection aircraft to deviate because the conflict must be resolved to preclude the emergency.",
            True,
        ),
        choice(
            "Continue the recorded run and vector the emergency aircraft away from the runway.",
            False,
        ),
        choice(
            "Terminate the recorded run without coordinating with the flight inspection pilot.",
            False,
        ),
        choice(
            "Give the recorded run absolute priority and delay handling of the emergency aircraft.",
            False,
        ),
    ]


def remediate_chapter_12(payload: dict[str, Any]) -> None:
    question = item(payload, "questions", "12-1-6")
    question["question_text"] = (
        "A pilot requests authorization for a parachute jump in delegated Canadian "
        "airspace but has not obtained permission from the appropriate Canadian authority. "
        "What should the controller do?"
    )
    question["question_type"] = "multiple_choice"
    question["difficulty"] = 2
    question["explanation"] = (
        "Do not authorize the jump without prior permission from the appropriate "
        "Canadian authority. Traffic conditions, VFR status, or a pilot assurance "
        "do not replace that prerequisite."
    )
    question["choices"] = [
        choice("Do not authorize the jump until the required Canadian permission exists.", True),
        choice("Authorize it if traffic permits and the pilot remains VFR.", False),
        choice("Coordinate locally, then approve it without prior Canadian permission.", False),
        choice("Authorize it after the pilot verbally accepts responsibility.", False),
    ]


def remediate_chapter_13(payload: dict[str, Any]) -> None:
    activity = item(payload, "activities", "13-1-2")
    activity["choices"][0]["text"] = (
        "Recognize that conflict probe does not account for non-standard "
        "formations that may require greater separation."
    )


def build_report() -> dict[str, Any]:
    resolutions: dict[tuple[int, str], tuple[str, str]] = {
        (2, "activities.2-4-19.items[0]"): ("fixed", "Rewrote the broken scenario and teaching explanation."),
        (2, "activities.2-4-16.items[0]"): ("fixed", "Replaced spelling trivia with operational spoken pronunciation."),
        (2, "flashcards.2-3-2.items[0]"): ("fixed", "Reframed block-number recall around the operational purpose."),
        (2, "activities.2-9-2.items[0]"): ("removed", "Removed the duplicate activity; retained the flashcard."),
        (2, "flashcards.2-9-2.items[0]"): ("retained", "Retained as the single staged representation after removing its duplicate."),
        (2, "activities.2-2-14.items[0]"): ("fixed", "Replaced list comparison with an applied correction-message scenario."),
        (2, "flashcards.2-2-10.items[0]"): ("fixed", "Reframed the threshold as an operational forwarding condition."),
        (3, "questions.3-10-3.items[0]"): ("moved", "Moved to paragraph 3-10-2, which contains the tested obligation."),
        (3, "questions.3-7-5.items[0]"): ("moved", "Moved to paragraph 3-7-1, which contains the tested taxi rule."),
        (3, "flashcards.3-7-5.items[0]"): ("moved", "Moved to paragraph 3-7-1, which contains the tested taxi rule."),
        (4, "flashcards.4-7-10.items[0]"): ("fixed", "Corrected the prescribed AWOS/ASOS phraseology."),
        (4, "questions.4-5-6.items[0]"): ("fixed", "Corrected the no-MCA climb timing rule."),
        (4, "questions.4-6-4.items[0]"): ("moved_and_fixed", "Moved to 4-6-1 and corrected the charted-hold exception."),
        (5, "questions.5-5-1.items[0]"): ("fixed", "Replaced the duplicate application question with the impromptu-route exception."),
        (5, "flashcards.5-5-9.items[0]"): ("split", "Split the overloaded minima card into two coherent retrieval targets."),
        (5, "questions.5-2-12.items[0]"): ("retained", "Retained the scenario question and rewrote its flashcard counterpart."),
        (5, "flashcards.5-2-22.items[0]"): ("fixed", "Changed the card to the safety-jeopardy response."),
        (5, "flashcards.5-4-8.items[0]"): ("fixed", "Changed the card to the continuing coordination requirement."),
        (5, "flashcards.5-13-7.items[0]"): ("removed", "Removed the duplicate flashcard and retained the staged question."),
        (5, "flashcards.5-3-2.items[0]"): ("fixed", "Changed the card to the permitted coordination methods."),
        (6, "activities.6-6-3.items[0]"): ("fixed", "Corrected the internally contradictory answer text."),
        (7, "questions.7-6-7.items[0]"): ("fixed", "Made the overtaking restriction explicitly conditional on wake turbulence."),
        (7, "flashcards.7-4-5.items[0]"): ("split", "Split the overloaded CVFP card into three focused cards."),
        (9, "activities.9-1-2.items[0]"): ("fixed", "Removed duplicate answer meanings and clarified the emergency exception."),
        (10, "questions.10-2-1.items[0]"): ("already_satisfied", "Current staged explanation already cites and applies 10-2-1a correctly."),
        (10, "questions.10-3-6.items[0]"): ("already_satisfied", "Current scenario already states the immediate SAR need identified by the audit."),
        (12, "questions.12-1-6.items[0]"): ("fixed", "Replaced the grammar-clued blank with an operational decision question."),
        (13, "activities.13-1-2.items[0]"): ("fixed", "Shortened the correct option while retaining the teaching detail in the explanation."),
    }

    findings: list[dict[str, Any]] = []
    for audit_path in sorted(AUDITS.glob("chapter_*_pass_01.json")):
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        chapter = int(audit["chapter"])
        for finding in audit["findings"]:
            if finding["severity"] not in {"critical", "major"}:
                continue
            key = (chapter, finding["item_path"])
            if key not in resolutions:
                raise KeyError(f"Missing remediation resolution for {key}")
            status, detail = resolutions[key]
            findings.append(
                {
                    "chapter": chapter,
                    "severity": finding["severity"],
                    "item_path": finding["item_path"],
                    "status": status,
                    "detail": detail,
                }
            )

    if len(findings) != len(resolutions):
        raise RuntimeError(
            f"Resolution count mismatch: {len(findings)} audit findings vs "
            f"{len(resolutions)} resolutions"
        )

    return {
        "version": 1,
        "audit_pass": 1,
        "remediation_pass": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "All critical and major findings from chapter expansion audit pass 01.",
        "summary": {
            "findings_realized": len(findings),
            "critical": sum(f["severity"] == "critical" for f in findings),
            "major": sum(f["severity"] == "major" for f in findings),
            "by_status": {
                status: sum(f["status"] == status for f in findings)
                for status in sorted({f["status"] for f in findings})
            },
        },
        "findings": findings,
    }


def main() -> int:
    if REPORT.exists():
        print(f"Remediation already applied: {REPORT.relative_to(ROOT)}")
        return 0

    remediators = {
        2: remediate_chapter_02,
        3: remediate_chapter_03,
        4: remediate_chapter_04,
        5: remediate_chapter_05,
        6: remediate_chapter_06,
        7: remediate_chapter_07,
        9: remediate_chapter_09,
        12: remediate_chapter_12,
        13: remediate_chapter_13,
    }
    for chapter, remediate in remediators.items():
        path, payload = load_chapter(chapter)
        remediate(payload)
        save(path, payload)
        print(f"Remediated {path.relative_to(ROOT)}")

    save(REPORT, build_report())
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
