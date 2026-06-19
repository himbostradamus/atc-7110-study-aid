#!/usr/bin/env python3
"""Clean flashcard prompts that teach paragraph locations instead of concepts."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
TARGET_CHAPTERS = {"5", "6", "8", "9"}
QUESTION_LEAD_RE = re.compile(
    r"^(?:what|when|where|who|which|how|why|identify|name|state|list|"
    r"select|choose|determine|give|describe|explain)\b",
    re.IGNORECASE,
)

CATEGORY_WORDS = {
    "A": "Alpha",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
}

MANUAL_FRONT_REWRITES = {
    "5-2-16": {
        "5-2-16 vs 5-2-17: Difference in altitude confirmation exceptions":
            "How do Mode C and non-Mode C altitude-confirmation exceptions differ?",
    },
    "5-2-17": {
        "5-2-17b (USA): Controller response to pilot altitude readback":
            "How must a controller respond to a pilot altitude readback?",
    },
    "5-3-2": {
        "Military TACAN DME complication (5-3-2b note)":
            "Why can military TACAN DME complicate radar identification?",
    },
    "5-3-3": {
        "ERAM paired LDB note (5-3-3d note)":
            "What does an ERAM paired limited data block omit?",
    },
    "5-3-9": {
        "VFR data block retention exception in terminal (5-3-9a note)":
            "When does the terminal VFR data-block retention exception apply?",
    },
    "5-4-3": {
        "Physical pointing exception (5-4-3b note)":
            "What information can be omitted when physically pointing to the target?",
    },
    "5-4-9": {
        "Five proper means of coordination (5-4-9 note)":
            "What are the proper means of coordination?",
    },
    "5-4-10": {
        "Airspeed format in fourth line (5-4-10g-h)":
            "How are airspeed and Mach requests shown in the fourth line?",
        "Requesting altitude or route change in fourth line (5-4-10j-k)":
            "How are altitude or route-change requests shown in the fourth line?",
    },
    "5-5-10": {
        "Adjacent airspace boundary minima WITHOUT coordination (5-5-10a-b)":
            "What adjacent-airspace boundary minima apply without coordination?",
    },
    "5-5-4": {
        "Terminal radar separation minima by system type (5-5-4a-c)":
            "What terminal radar separation minima apply by system type?",
        "For Table 5-5-2 wake turbulence on approach, when must the listed spacing exist?":
            "For approach wake-turbulence spacing, when must the listed spacing exist?",
    },
    "5-6-1": {
        "Vectoring rules by airspace type (5-6-1a-b)":
            "How do vectoring rules differ between controlled airspace and Class G?",
    },
    "5-6-2": {
        "Effect of vectoring off SID/STAR after climb via/descend via (5-6-2d note)":
            "What happens to SID/STAR restrictions after vectoring off a climb-via or descend-via procedure?",
    },
    "5-9-2": {
        "Final approach course interception angles (TBL 5-9-1)":
            "What final-approach course interception angle limits apply?",
    },
    "5-9-7": {
        "What runway-centerline spacing normally supports dual simultaneous independent approaches?":
            "Dual independent approaches: required runway-centerline spacing",
        "What runway-centerline spacing normally supports triple simultaneous independent approaches?":
            "Triple independent approaches: required runway-centerline spacing",
    },
    "5-9-9": {
        "SOIA: separation requirements (5-9-9a1-a3)":
            "What separation requirements apply before a SOIA visual segment?",
        "SOIA: visual segment pilot responsibility (5-9-9d-f)":
            "What is the trailing pilot responsible for during the SOIA visual segment?",
    },
    "5-14-6": {
        "What is the terminal equivalent of 5-13-1?":
            "What is the terminal automation equivalent of en route CA/MCI alert handling?",
    },
    "6-7-4": {
        "What is the level-flight requirement when 6-7-2b is applied and IFR conditions exist over the final approach fix?":
            "What level-flight requirement applies when IFR conditions exist over the final approach fix?",
    },
    "6-1-5": {
        "6-1-5b vs 6-1-5c: What is the key operational distinction?":
            "How do same-runway and close/crossing-runway arrival wake minima differ?",
        "Terminal arrivals, H or I behind Category Alpha":
            "Terminal arrivals: Hotel/India followers behind Alpha leader",
        "Terminal arrivals, behind Category Alpha":
            "Terminal arrivals: Bravo-Golf followers behind Alpha leader",
        "Terminal arrivals, H or I behind Category Bravo, C, or D":
            "Terminal arrivals: Hotel/India followers behind Bravo/Charlie/Delta leader",
        "Terminal arrivals, behind Category Bravo or D":
            "Terminal arrivals: Bravo-Golf followers behind Bravo/Delta leader",
    },
    "6-1-4": {
        "Terminal adjacent-airport wake minima: behind Category Alpha":
            "Adjacent-airport departures: Bravo-India followers behind Alpha leader",
        "Terminal adjacent-airport wake minima: behind Category Bravo or D":
            "Adjacent-airport departures: Bravo-India followers behind Bravo/Delta leader",
        "Terminal adjacent-airport wake minima: behind Category Charlie":
            "Adjacent-airport departures: Echo-India followers behind Charlie leader",
        "Terminal adjacent-airport wake minima: behind Category Echo":
            "Adjacent-airport departures: India follower behind Echo leader",
    },
    "6-2-1": {
        "6-2-1 note 2: How are helipad/vertipad departures referenced for diverging-course minima?":
            "How are helipad or vertipad departures referenced for diverging-course minima?",
    },
    "6-2-2": {
        "Same-course climb-through separation methods":
            "What are the two same-course climb-through separation options?",
        "When the following aircraft will climb through the leading aircraft's altitude on the same course, what is the distance-based separation minimum?":
            "Same-course climb-through: distance-based separation option",
        "When the following aircraft will climb through the leading aircraft's altitude on the same course, what is the timed separation minimum?":
            "Same-course climb-through: time-based separation option",
    },
    "6-3-1": {
        "6-3-1a vs 6-3-1b: What is the key difference when takeoff direction does NOT differ by ≥45°?":
            "What extra condition applies when departure and arrival courses do not diverge by at least 45 degrees?",
    },
    "6-4-3": {
        "Opposite-course vertical separation window":
            "When must different altitudes be assigned for opposite-course vertical separation?",
    },
    "6-5-2": {
        "TBL 6-5-2 vs TBL 6-5-1: when to use which?":
            "When should DME lateral-separation values replace non-DME values?",
    },
    "6-5-4": {
        "6-5-4b/c: Overflown side protection for course changes: 16-90° vs 91-180°":
            "How does overflown-side protection change for 16-90 degree versus 91-180 degree turns?",
        "For a course change of 16-90 degrees at FL180-FL230, what overflown-side protection applies?":
            "Overflown-side protection for a 16-90 degree turn at FL180-FL230",
        "For a course change of 91-180 degrees at FL180-FL230, what overflown-side protection applies?":
            "Overflown-side protection for a 91-180 degree turn at FL180-FL230",
    },
    "6-6-1": {
        "What phraseology requests an aircraft's altitude when the aircraft is known to be at or above the lowest usable flight level?":
            "Known at or above the lowest usable flight level: altitude-report phraseology",
        "What phraseology requests an aircraft's altitude when the aircraft is known to be below the lowest usable flight level?":
            "Known below the lowest usable flight level: altitude-report phraseology",
    },
    "6-6-2": {
        "6-6-2 note: Cruise clearance: can pilot return to a verbally-left altitude?":
            "After verbally reporting leaving an altitude on a cruise clearance, may the pilot return to it?",
    },
    "6-6-3": {
        "Which aircraft is authorized to maintain vertical separation when pilots concur during climb?":
            "Pilot-concurred climb: which aircraft may maintain vertical separation?",
        "Which aircraft is authorized to maintain vertical separation when pilots concur during descent?":
            "Pilot-concurred descent: which aircraft may maintain vertical separation?",
    },
    "6-7-7": {
        "When 6-7-2b applies and first aircraft goes missed: what happens to the second aircraft?":
            "When the first aircraft goes missed under approach separation, what happens to the second aircraft?",
    },
    "8-2-2": {
        "May the accepting unit alter an aircraft's clearance before the transfer point?":
            "What restriction applies before an accepting unit alters a clearance before the transfer point?",
        "When may the accepting unit alter an aircraft's clearance before the transfer point?":
            "Accepting unit clearance changes before transfer point: approval condition",
    },
    "8-5-3": {
        "When may an outbound aircraft climb through opposite-direction oceanic traffic during offshore-to-oceanic transition?":
            "Outbound offshore-to-oceanic transition: climb-through condition for opposite-direction traffic",
    },
    "9-1-3": {
        "Altitude range for preplanned automatic flight check":
            "What altitude range applies to a preplanned automatic flight check?",
        "Route of flight orbital range for preplanned automatic flight check":
            "What orbital range applies to a preplanned automatic flight check?",
    },
    "9-4-4": {
        "VFR separation from fuel-dumping aircraft":
            "What separation applies to radar-identified VFR aircraft near fuel dumping?",
        "What separation from a fuel-dumping aircraft?":
            "What IFR separation options apply around a fuel-dumping aircraft?",
    },
    "9-7-3": {
        "9-7-3 vs 9-7-2: Class D vs Class A/B/C parachute handling":
            "How does Class D parachute handling differ from Class A/B/C parachute handling?",
    },
}

DELETE_CARD_IDS = {
    # Redundant same-answer cards in target chapters; keep the clearer companion.
    "5d8760e8-7ca0-4260-8e86-f596d74e32b1",
    "239bf12e-8f02-4074-977d-64eea9f2e2f7",
    "3dc93818-3dcd-4cb3-bb02-65b8da62b862",
    "508b2457-19f4-47e3-a8c2-5287b7b333e5",
    "cb7d59ab-a483-46ea-8ec2-97a364306a75",
    "9f56357f-7df6-42d4-a3ed-b790051487ca",
    "2a7493cf-aa9f-44a4-9045-ad088a4b6756",
    "180f9c88-a0f1-4dc4-b23c-c4d689aefc9a",
    "0edb000f-baef-4c97-902b-3b1ee98da0be",
    "77778967-cffb-4f11-b923-4d104dafca66",
    "7a3f8826-e3a3-4fcc-a07d-c8bec8ed686d",
    "6b5aca0a-8b51-443c-96fc-ae737ae068e1",
    "64da42e8-324f-4e4b-b9d4-f2d44ffec137",
    "b06f9f93-d874-4883-9453-2726eed4ed81",
    "95a32909-0361-4cb9-a525-c2490c114f24",
    "de0cefcd-a5c4-4ec9-997f-21f6be7bf650",
    "c8b015ef-b306-4905-9b09-00dac5e5aa21",
    "d459f8d3-b966-4d09-b19e-06b530674f56",
    "e8e24089-7773-44e0-bf02-8f37e3662d73",
    "c2023501-88ba-4e73-baa1-cda1fee714db",
    "448ca65c-774f-4cef-9737-0223d995374b",
    "ef840ad1-aa95-4df6-a85e-443a9439e897",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def category_replacer(match: re.Match[str]) -> str:
    letter = match.group(1).upper()
    return f"Category {CATEGORY_WORDS.get(letter, letter)}"


def clean_front(front: str, para_id: str) -> str:
    rewritten = MANUAL_FRONT_REWRITES.get(para_id, {}).get(front)
    if rewritten:
        return rewritten

    text = front.replace("\u2212", "-")
    para_pattern = re.escape(para_id)

    # Remove leading paragraph labels: "5-3-2: ..." or "5-3-2a - ...".
    text = re.sub(
        rf"^\s*(?:§\s*)?{para_pattern}[a-z0-9]*\s*[:\-–]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove trailing paragraph labels: "... (5-3-2b)".
    text = re.sub(
        r"\s*\(\s*(?:§\s*)?\d{1,2}(?:[-\u2212]\d+){2,}[a-z0-9]*\s*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove inline source-location phrasing where it only points at the order.
    text = re.sub(
        r"\b(?:under|from|in|per)\s+(?:paragraph\s+|para\s+|section\s+)?"
        r"\d{1,2}(?:[-\u2212]\d+){2,}[a-z0-9]*\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Category letters are too terse for both learners and duplicate detection.
    text = re.sub(r"\bCategory\s+([A-I])\b", category_replacer, text)
    text = re.sub(r"\bCategories\s+([A-I])\b", category_replacer, text)

    text = text.replace(" — ", ": ")
    text = text.replace(" - ", ": ")
    text = re.sub(r"\s+([?:,])", r"\1", text)
    text = re.sub(r":\s*:", ":", text)
    text = re.sub(r"^APPLICATION:\s*", "", text, flags=re.IGNORECASE)
    text = promptify_context_light(normalize_space(text), para_id)
    return normalize_space(text)


def promptify_context_light(front: str, para_id: str) -> str:
    if len(front.split()) >= 4 or QUESTION_LEAD_RE.search(front):
        return front
    if not front:
        return front
    front_lower = front.lower()
    if "phraseology" in front_lower:
        return f"What phraseology is used for {front}?"
    if any(word in front_lower for word in ("timing", "threshold", "minimum", "minima")):
        return f"What threshold applies to {front}?"
    if any(word in front_lower for word in ("procedure", "instruction", "transfer", "changeover")):
        return f"What procedure applies to {front}?"
    if para_id.startswith("5-14"):
        return f"What STARS rule applies to {front}?"
    return f"What rule applies to {front}?"


def clean_back(back: str) -> str:
    text = back.replace("\u2212", "-")
    text = re.sub(
        r"\s+Per\s+\d{1,2}(?:[-\u2212]\d+){2,}[a-z0-9]*(?:\([a-z0-9]+\))?\.",
        ".",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\bCategory\s+([A-I])\b", category_replacer, text)
    text = re.sub(r"\bCategories\s+([A-I])\b", category_replacer, text)
    return normalize_space(text)


def chapter_for(para_id: str) -> str:
    return para_id.split("-", 1)[0]


def unique_front(
    db: sqlite3.Connection,
    card_id: str,
    para_id: str,
    card_type: str,
    front: str,
) -> str:
    existing = db.execute(
        """
        SELECT id FROM flashcards
        WHERE para_id = ? AND card_type = ? AND front = ? AND id <> ?
        """,
        (para_id, card_type, front, card_id),
    ).fetchone()
    if not existing:
        return front

    # Preserve both cards if their backs differ, but avoid a uniqueness collision.
    suffix = " concept check"
    candidate = f"{front} ({suffix})"
    index = 2
    while db.execute(
        """
        SELECT 1 FROM flashcards
        WHERE para_id = ? AND card_type = ? AND front = ? AND id <> ?
        """,
        (para_id, card_type, candidate, card_id),
    ).fetchone():
        candidate = f"{front} ({suffix} {index})"
        index += 1
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT id, para_id, front, back, card_type
        FROM flashcards
        ORDER BY para_id, front
        """
    ).fetchall()

    if DELETE_CARD_IDS:
        existing_deletes = db.execute(
            f"SELECT count(*) FROM flashcards WHERE id IN ({','.join('?' for _ in DELETE_CARD_IDS)})",
            tuple(DELETE_CARD_IDS),
        ).fetchone()[0]
    else:
        existing_deletes = 0

    updates: list[tuple[str, str, str]] = []
    for row in rows:
        if row["id"] in DELETE_CARD_IDS:
            continue
        para_id = row["para_id"]
        if chapter_for(para_id) not in TARGET_CHAPTERS:
            continue

        front = clean_front(row["front"], para_id)
        back = clean_back(row["back"])
        front = unique_front(db, row["id"], para_id, row["card_type"], front)
        if front != row["front"] or back != row["back"]:
            updates.append((front, back, row["id"]))

    print(f"flashcards_to_delete={existing_deletes}")
    print(f"flashcards_to_update={len(updates)}")
    if args.dry_run:
        for front, back, card_id in updates[:25]:
            print(f"{card_id}: {front} -> {back[:120]}")
        return 0

    if DELETE_CARD_IDS:
        db.execute(
            f"DELETE FROM flashcards WHERE id IN ({','.join('?' for _ in DELETE_CARD_IDS)})",
            tuple(DELETE_CARD_IDS),
        )
    db.executemany(
        "UPDATE flashcards SET front = ?, back = ? WHERE id = ?",
        updates,
    )
    db.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
