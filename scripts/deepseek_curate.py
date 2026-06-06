#!/usr/bin/env python3
"""
DeepSeek-curated content inserter.
Purely additive — never modifies or deletes existing rows.
All inserted rows use generation_src = 'deepseek'.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "curriculum_ready.db"

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def insert_flashcards(db: sqlite3.Connection, para_id: str, cards: list[dict]) -> int:
    """Insert flashcards. Each card: {front, back, card_type}."""
    row = db.execute("SELECT id FROM paragraphs WHERE para_id = ?", (para_id,)).fetchone()
    if not row:
        raise ValueError(f"Paragraph not found: {para_id}")
    para_db_id = row[0]
    count = 0
    for card in cards:
        card_id = str(uuid.uuid4())
        try:
            db.execute(
                """INSERT INTO flashcards (id, paragraph_db_id, para_id, front, back, card_type, generation_src, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'deepseek', ?)""",
                (card_id, para_db_id, para_id, card["front"], card["back"], card["card_type"], _now()),
            )
            count += 1
        except sqlite3.IntegrityError:
            print(f"  SKIP (duplicate flashcard): {card['front'][:60]}...")
    return count


def insert_quiz_questions(db: sqlite3.Connection, para_id: str, questions: list[dict]) -> int:
    """Insert quiz questions. Each question: {question_text, question_type, explanation, difficulty, choices: [{choice_text, is_correct, sort_order}]}.
    Skips questions that already exist with the same text, para_id, and generation_src."""
    row = db.execute("SELECT id FROM paragraphs WHERE para_id = ?", (para_id,)).fetchone()
    if not row:
        raise ValueError(f"Paragraph not found: {para_id}")
    para_db_id = row[0]
    count = 0
    for q in questions:
        # Guard against duplicates (quiz_questions has no UNIQUE constraint)
        existing = db.execute(
            "SELECT 1 FROM quiz_questions WHERE para_id = ? AND question_text = ? AND generation_src = 'deepseek'",
            (para_id, q["question_text"]),
        ).fetchone()
        if existing:
            print(f"  SKIP (duplicate question): {q['question_text'][:60]}...")
            continue
        q_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO quiz_questions (id, paragraph_db_id, para_id, question_text, question_type, explanation, difficulty, generation_src, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'deepseek', ?)""",
            (q_id, para_db_id, para_id, q["question_text"], q["question_type"],
             q.get("explanation", ""), q.get("difficulty", 2), _now()),
        )
        for choice in q.get("choices", []):
            db.execute(
                """INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), q_id, choice["choice_text"], choice["is_correct"], choice["sort_order"]),
            )
        count += 1
    return count


def insert_activities(db: sqlite3.Connection, para_id: str, activities: list[dict]) -> int:
    """Insert activities. Each activity: {activity_type, content_json (dict), difficulty}."""
    row = db.execute("SELECT id FROM paragraphs WHERE para_id = ?", (para_id,)).fetchone()
    if not row:
        raise ValueError(f"Paragraph not found: {para_id}")
    para_db_id = row[0]
    count = 0
    for act in activities:
        act_id = str(uuid.uuid4())
        content = json.dumps(act["content_json"], ensure_ascii=False)
        try:
            db.execute(
                """INSERT INTO activities (id, paragraph_db_id, para_id, activity_type, content_json, difficulty, generation_src, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'deepseek', ?)""",
                (act_id, para_db_id, para_id, act["activity_type"], content, act.get("difficulty", 2), _now()),
            )
            count += 1
        except sqlite3.IntegrityError as e:
            print(f"  SKIP (duplicate activity): {act['activity_type']} — {e}")
    return count


# ═══════════════════════════════════════════════════════════════
# Paragraph content definitions
# ═══════════════════════════════════════════════════════════════

def curate_2_1_1(db: sqlite3.Connection):
    """2-1-1 ATC SERVICE"""
    para = "2-1-1"
    print(f"\n{'='*60}\nCurating {para} — ATC SERVICE\n{'='*60}")

    # --- Flashcards ---
    cards = [
        {
            "front": "What are the six factors that may preclude provision of additional ATC services?",
            "back": "1. Volume of traffic\n2. Frequency congestion\n3. Quality of surveillance\n4. Controller workload\n5. Higher priority duties\n6. Physical inability to scan and detect situations",
            "card_type": "definition",
        },
        {
            "front": "Under what three conditions may a controller deviate from 7110.65 procedures and minima?",
            "back": "1. Deviation necessary to conform with ICAO Documents, National Rules of the Air, or special agreements where the U.S. provides ATC service in airspace outside the U.S.\n2. Other procedures/minima prescribed in an LOA, FAA directive, or military document\n3. Deviation necessary to assist an aircraft when an emergency has been declared",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    # --- Quiz Questions ---
    questions = [
        # Fill-in-blank
        {
            "question_text": 'The primary purpose of the ATC system is to prevent a _____ involving aircraft operating in the system.',
            "question_type": "fill_blank",
            "explanation": "Per 2-1-1(a): The primary purpose of the ATC system is to prevent a collision involving aircraft operating in the system.",
            "difficulty": 1,
            "choices": [{"choice_text": "collision", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Air traffic control services are not provided for model aircraft operating in the NAS or to any UAS operating entirely at or below _____ feet AGL.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-1(e): ATC services are not provided for model aircraft operating in the NAS or to any UAS at or below 400ft AGL.",
            "difficulty": 1,
            "choices": [{"choice_text": "400", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": 'The provision of additional services is not _____ on the part of the controller, but rather required when the work situation permits.',
            "question_type": "fill_blank",
            "explanation": "Per 2-1-1(c): additional services are not optional on the part of the controller, but rather required when the work situation permits.",
            "difficulty": 1,
            "choices": [{"choice_text": "optional", "is_correct": 1, "sort_order": 0}],
        },
        # Multiple choice
        {
            "question_text": "Which of the following is NOT one of the six factors that may preclude the provision of additional ATC services?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-1(c), the six preclusion factors are: volume of traffic, frequency congestion, quality of surveillance, controller workload, higher priority duties, and physical inability to scan and detect situations. 'Pilot request' is not among them.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Volume of traffic", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Frequency congestion", "is_correct": 0, "sort_order": 1},
                {"choice_text": "Pilot request", "is_correct": 1, "sort_order": 2},
                {"choice_text": "Controller workload", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "A controller may deviate from the procedures and minima in this order when:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-1(d), all three conditions permit deviation: (1) ICAO/special agreement conformance outside U.S., (2) other procedures in LOA/FAA directive/military document, and (3) emergency assistance.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "A deviation is necessary to conform with ICAO Documents or special agreements where the U.S. provides ATC service outside the U.S.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Other procedures/minima are prescribed in a letter of agreement, FAA directive, or a military document", "is_correct": 0, "sort_order": 1},
                {"choice_text": "A deviation is necessary to assist an aircraft when an emergency has been declared", "is_correct": 0, "sort_order": 2},
                {"choice_text": "All of the above", "is_correct": 1, "sort_order": 3},
            ],
        },
        {
            "question_text": "In addition to preventing collisions, the ATC system also provides a safe, orderly, and expeditious flow of air traffic and supports what other mission?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-1(b): In addition to its primary purpose, the ATC system also provides a safe, orderly, and expeditious flow of air traffic and supports National Security and Homeland Defense missions.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Commercial aviation efficiency", "is_correct": 0, "sort_order": 0},
                {"choice_text": "National Security and Homeland Defense missions", "is_correct": 1, "sort_order": 1},
                {"choice_text": "International trade facilitation", "is_correct": 0, "sort_order": 2},
                {"choice_text": "General aviation outreach", "is_correct": 0, "sort_order": 3},
            ],
        },
        # True/false
        {
            "question_text": "The provision of additional services is optional on the part of the controller when workload permits.",
            "question_type": "true_false",
            "explanation": "Per 2-1-1(c): The provision of additional services is not optional on the part of the controller, but rather required when the work situation permits.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
        {
            "question_text": "Controllers are permitted to deviate from 7110.65 procedures to assist an aircraft that has declared an emergency.",
            "question_type": "true_false",
            "explanation": "Per 2-1-1(d)(3): A deviation is permitted when necessary to assist an aircraft when an emergency has been declared.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 1, "sort_order": 0},
                {"choice_text": "False", "is_correct": 0, "sort_order": 1},
            ],
        },
        {
            "question_text": "ATC services are provided to model aircraft operating at 300 feet AGL in the NAS.",
            "question_type": "true_false",
            "explanation": "Per 2-1-1(e): ATC services are not provided for model aircraft operating in the NAS, regardless of altitude.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    # --- Activities ---
    # 2-1-1 is a general policy paragraph — no phraseology to work with.
    # spot_the_error and phraseology_builder don't map well here.
    # We add a higher-quality situation_action and a readback_check
    # adapted to test comprehension of the exception conditions.

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 3,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "You are working a busy radar position with high-frequency congestion and multiple aircraft on frequency. A pilot requests an additional service beyond separation. Per 2-1-1(c), additional services are required when the work situation permits. You assess that frequency congestion and controller workload currently preclude providing the additional service safely.",
                "para_context": "2-1-1(c): The provision of additional services is not optional on the part of the controller, but rather required when the work situation permits. It is recognized that the provision of these services may be precluded by various factors, including but not limited to: volume of traffic, frequency congestion, quality of surveillance, controller workload, higher priority duties, and the physical inability to scan and detect situations.",
                "choices": [
                    {"text": "Provide the additional service immediately — it is mandatory under all circumstances.", "is_correct": False},
                    {"text": "Inform the pilot the service is unavailable due to workload and that you will provide it when the work situation permits.", "is_correct": True},
                    {"text": "Tell the pilot the service is optional and they should not expect it.", "is_correct": False},
                    {"text": "Delegate the service to another controller regardless of their workload.", "is_correct": False},
                ],
                "explanation": "Per 2-1-1(c): Additional services are required when the work situation permits — meaning the controller must provide them if able, but workload and other listed factors may legitimately preclude provision. The correct action is to acknowledge the request and provide the service when conditions allow.",
            },
        },
        {
            "activity_type": "situation_action",
            "difficulty": 3,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "You are providing ATC service in airspace outside the U.S. under a special agreement. The procedures in 7110.65 conflict with ICAO Document procedures applicable in this airspace.",
                "para_context": "2-1-1(d)(1): A deviation is necessary to conform with ICAO Documents, National Rules of the Air, or special agreements where the U.S. provides air traffic control service in airspace outside the U.S. and its possessions.",
                "choices": [
                    {"text": "Apply 7110.65 procedures regardless — they always take precedence.", "is_correct": False},
                    {"text": "Conform with the applicable ICAO Documents or special agreement procedures.", "is_correct": True},
                    {"text": "Cease providing ATC service until the conflict is resolved.", "is_correct": False},
                    {"text": "Ask the pilot which procedures they prefer.", "is_correct": False},
                ],
                "explanation": "Per 2-1-1(d)(1): When providing ATC service in airspace outside the U.S., a deviation from 7110.65 is permitted to conform with ICAO Documents, National Rules of the Air, or special agreements.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def curate_2_1_2(db: sqlite3.Connection):
    """2-1-2 DUTY PRIORITY"""
    para = "2-1-2"
    print(f"\n{'='*60}\nCurating {para} — DUTY PRIORITY\n{'='*60}")

    # --- Flashcards ---
    cards = [
        {
            "front": "What is the first priority duty of controllers under 2-1-2?",
            "back": "Separating aircraft and issuing safety alerts as required in this order.",
            "card_type": "definition",
        },
        {
            "front": "What is the four-tier hierarchy of controller duties per 2-1-2?",
            "back": "1. Separate aircraft and issue safety alerts (FIRST PRIORITY)\n2. Support national security and homeland defense activities\n3. Provide and/or solicit weather information\n4. Provide additional services to the extent possible, contingent upon higher priority duties",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    # --- Quiz Questions ---
    questions = [
        # Fill-in-blank
        {
            "question_text": "Give first priority to _____ aircraft and issuing safety alerts as required in this order.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-2(a): Give first priority to separating aircraft and issuing safety alerts as required in this order.",
            "difficulty": 1,
            "choices": [{"choice_text": "separating", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "When more than one action is required, controllers must exercise their best _____ based on the facts and circumstances known to them.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-2 Note: Each set of circumstances must be evaluated on its own merit, and controllers must exercise their best judgment based on the facts and circumstances known to them.",
            "difficulty": 1,
            "choices": [{"choice_text": "judgment", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "That action which is most critical from a _____ standpoint is performed first.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-2 Note: That action which is most critical from a safety standpoint is performed first.",
            "difficulty": 1,
            "choices": [{"choice_text": "safety", "is_correct": 1, "sort_order": 0}],
        },
        # Multiple choice
        {
            "question_text": "Which of the following takes FIRST priority among controller duties under 2-1-2?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-2(a): Give first priority to separating aircraft and issuing safety alerts. All other duties are subordinate to this primary responsibility.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Providing weather information to pilots", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Separating aircraft and issuing safety alerts", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Supporting national security activities", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Providing additional services to the extent possible", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "Why does 2-1-2 state it is 'virtually impossible' to develop a standard list of duty priorities?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-2 Note: Because there are many variables involved, it is virtually impossible to develop a standard list of duty priorities that would apply uniformly to every conceivable situation. Each set of circumstances must be evaluated on its own merit.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "Because the FAA has not yet completed the necessary research", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Because too many variables exist — each situation must be evaluated on its own merit", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Because controllers are expected to memorize all procedures", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Because duty priorities change with each new edition of the 7110.65", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "According to 2-1-2, controllers must provide support to national security and homeland defense activities including what specific action?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-2(b): Provide support to national security and homeland defense activities to include, but not be limited to, reporting of suspicious and/or unusual aircraft/pilot activities.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Issuing NOTAMs for all military operations", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Reporting of suspicious and/or unusual aircraft/pilot activities", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Coordinating with the Department of Defense on all IFR flight plans", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Providing priority handling to all government aircraft", "is_correct": 0, "sort_order": 3},
            ],
        },
        # True/false
        {
            "question_text": "A standard list of duty priorities exists that applies uniformly to every conceivable situation a controller may face.",
            "question_type": "true_false",
            "explanation": "Per 2-1-2 Note: It is virtually impossible to develop a standard list of duty priorities that would apply uniformly to every conceivable situation. Each set of circumstances must be evaluated on its own merit.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
        {
            "question_text": "When more than one action is required, the action most critical from a safety standpoint is performed first.",
            "question_type": "true_false",
            "explanation": "Per 2-1-2 Note: That action which is most critical from a safety standpoint is performed first.",
            "difficulty": 1,
            "choices": [
                {"choice_text": "True", "is_correct": 1, "sort_order": 0},
                {"choice_text": "False", "is_correct": 0, "sort_order": 1},
            ],
        },
        {
            "question_text": "Providing additional services to pilots takes priority over separating aircraft.",
            "question_type": "true_false",
            "explanation": "Per 2-1-2(a): Give first priority to separating aircraft and issuing safety alerts. Providing additional services is the lowest tier of duty priority, contingent upon higher priority duties.",
            "difficulty": 1,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    # --- Activities ---
    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 3,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "You are working a radar position. Two aircraft are on converging courses and will lose separation in approximately 2 minutes. At the same time, a pilot calls in a PIREP of moderate turbulence at their altitude, and another pilot is requesting weather information for their destination. You also notice an aircraft squawking a hijack code.",
                "para_context": "2-1-2(a): Give first priority to separating aircraft and issuing safety alerts. 2-1-2(b): Provide support to national security and homeland defense activities to include reporting of suspicious and/or unusual aircraft/pilot activities. 2-1-2(c): Provide and/or solicit weather information. 2-1-2 Note: When more than one action is required, that action which is most critical from a safety standpoint is performed first.",
                "choices": [
                    {"text": "First separate the converging aircraft, then immediately report the hijack code to the supervisor, then handle the weather requests.", "is_correct": True},
                    {"text": "First provide the weather information since the pilot requested it, then address the converging aircraft.", "is_correct": False},
                    {"text": "Handle all requests in the order they were received — PIREP first, then separation, then hijack code.", "is_correct": False},
                    {"text": "First report the hijack code since national security is the highest priority in all situations.", "is_correct": False},
                ],
                "explanation": "Per 2-1-2: Separating aircraft is the first priority (imminent loss of separation is a safety-critical situation). The hijack code (national security) is the next priority. Weather services are lower priority and should be handled when the higher-priority duties are addressed. When multiple actions are required, the most safety-critical action is performed first.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_3(db: sqlite3.Connection):
    """2-1-3 PROCEDURAL PREFERENCE"""
    para = "2-1-3"
    print(f"\n{'='*60}\nCurating {para} — PROCEDURAL PREFERENCE\n{'='*60}")

    cards = [
        {
            "front": "What is the preference rule for automation vs. nonautomation procedures?",
            "back": "Use automation procedures in preference to nonautomation procedures when workload, communications, and equipment capabilities permit.",
            "card_type": "definition",
        },
        {
            "front": "When should a controller use nonradar separation in preference to radar separation?",
            "back": "When the situation dictates that an operational advantage will be gained. Example: vertical separation may preclude excessive vectoring, making nonradar separation the better choice.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        # Fill-in-blank
        {
            "question_text": "Use _____ procedures in preference to nonautomation procedures when workload, communications, and equipment capabilities permit.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-3(a): Use automation procedures in preference to nonautomation procedures when workload, communications, and equipment capabilities permit.",
            "difficulty": 1,
            "choices": [{"choice_text": "automation", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Use _____ loop clearances in preference to open loop clearances to promote operational advantage for time-based management (TBM) when workload permits.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-3(b): Use automation procedures that provide closed loop clearances in preference to open loop clearances to promote operational advantage for TBM.",
            "difficulty": 1,
            "choices": [{"choice_text": "closed", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Use _____ separation in preference to nonradar separation when it will be to an operational advantage and workload, communications, and equipment permit.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-3(c): Use radar separation in preference to nonradar separation when it will be to an operational advantage and conditions permit.",
            "difficulty": 1,
            "choices": [{"choice_text": "radar", "is_correct": 1, "sort_order": 0}],
        },
        # Multiple choice
        {
            "question_text": "According to 2-1-3, automation procedures should be used in preference to nonautomation procedures when:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-3(a): Use automation procedures in preference to nonautomation procedures when workload, communications, and equipment capabilities permit.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "At all times, regardless of conditions", "is_correct": 0, "sort_order": 0},
                {"choice_text": "When workload, communications, and equipment capabilities permit", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Only during reduced visibility operations", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Only when the supervisor authorizes it", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "Under what circumstance does 2-1-3(d) state nonradar separation should be used in preference to radar separation?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-3(d): Use nonradar separation in preference to radar separation when the situation dictates that an operational advantage will be gained. The note gives the example of vertical separation precluding excessive vectoring.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "When the radar system is undergoing maintenance", "is_correct": 0, "sort_order": 0},
                {"choice_text": "When the situation dictates that an operational advantage will be gained", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Nonradar separation is never preferred over radar separation", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Only when the pilot requests nonradar procedures", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "What is an example given in 2-1-3 of a situation where nonradar separation may provide an operational advantage?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-3 Note: One situation may be where vertical separation would preclude excessive vectoring.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "During arrivals to a busy terminal area", "is_correct": 0, "sort_order": 0},
                {"choice_text": "When vertical separation would preclude excessive vectoring", "is_correct": 1, "sort_order": 1},
                {"choice_text": "When two aircraft are on identical routes", "is_correct": 0, "sort_order": 2},
                {"choice_text": "During emergency operations only", "is_correct": 0, "sort_order": 3},
            ],
        },
        # True/false
        {
            "question_text": "Radar separation must always be used in preference to nonradar separation.",
            "question_type": "true_false",
            "explanation": "Per 2-1-3(d): Use nonradar separation in preference to radar separation when the situation dictates that an operational advantage will be gained. There are valid exceptions to the radar-first preference.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
        {
            "question_text": "Closed loop clearances are preferred over open loop clearances when workload permits, to promote operational advantage for time-based management.",
            "question_type": "true_false",
            "explanation": "Per 2-1-3(b): Use automation procedures that provide closed loop clearances in preference to open loop clearances to promote operational advantage for TBM when workload permits.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 1, "sort_order": 0},
                {"choice_text": "False", "is_correct": 0, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 3,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "You are vectoring an aircraft for a 20-mile final. The automation system is operational, your frequency is quiet, and you have full equipment capability. Using radar vectors would require multiple heading changes with 5-mile legs. Using vertical separation (nonradar) would allow a direct descent to the final approach fix without any vectoring.",
                "para_context": "2-1-3(c): Use radar separation in preference to nonradar separation when it will be to an operational advantage. 2-1-3(d): Use nonradar separation in preference to radar separation when the situation dictates that an operational advantage will be gained. Note: vertical separation may preclude excessive vectoring.",
                "choices": [
                    {"text": "Use radar vectors as required — radar separation is always preferred.", "is_correct": False},
                    {"text": "Use vertical (nonradar) separation — it provides operational advantage by precluding excessive vectoring.", "is_correct": True},
                    {"text": "Use closed loop clearances and ignore the separation decision.", "is_correct": False},
                    {"text": "Ask the pilot which method they would prefer.", "is_correct": False},
                ],
                "explanation": "Per 2-1-3(d): When nonradar separation (vertical) provides an operational advantage by avoiding excessive vectoring, it should be used in preference to radar separation — even when radar is available. This directly applies the note example.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_4(db: sqlite3.Connection):
    """2-1-4 OPERATIONAL PRIORITY"""
    para = "2-1-4"
    print(f"\n{'='*60}\nCurating {para} — OPERATIONAL PRIORITY\n{'='*60}")

    cards = [
        {
            "front": "What is the baseline rule for providing ATC service per 2-1-4?",
            "back": "Provide ATC service to aircraft on a 'first come, first served' basis as circumstances permit, with specific exceptions for priority aircraft.",
            "card_type": "definition",
        },
        {
            "front": "Name at least 8 categories that receive priority handling under 2-1-4.",
            "back": "1. Aircraft in distress\n2. MEDEVAC / AIR EVAC / HOSP\n3. Presidential aircraft & entourage\n4. SAR aircraft\n5. Interceptor (active air defense)\n6. NIGHT WATCH 'NAOC'\n7. FLYNET\n8. Garden Plot (CARF authorized only)\n9. SAMP (aerial sampling)\n10. SCOOT (Special Air Mission)\n11. TEAL / NOAA missions\n12. Flight Check aircraft\n13. IFR over SVFR\n14. NRP aircraft\n15. Diverted flights (DVRSN)\n16. FALLEN HERO flights",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        {
            "question_text": "Provide air traffic control service to aircraft on a '_____ come, first served' basis as circumstances permit, except for specified priority aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-4: The baseline rule is 'first come, first served' with specific exceptions for priority handling.",
            "difficulty": 1,
            "choices": [{"choice_text": "first", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "An aircraft in _____ has the right of way over all other air traffic.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-4(a): An aircraft in distress has the right of way over all other air traffic.",
            "difficulty": 1,
            "choices": [{"choice_text": "distress", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Provide priority handling to civil air ambulance flights when the pilot verbally identifies the flight by stating '_____' followed by the FAA authorized call sign.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-4(b)(1): MEDEVAC must be verbally stated by the pilot to receive priority. Flight plan notations are informational only.",
            "difficulty": 2,
            "choices": [{"choice_text": "MEDEVAC", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "How does a civil air ambulance flight obtain operational priority?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-4(b)(1): Priority is provided when the pilot verbally states 'MEDEVAC' followed by the call sign. Flight plan entries are informational only — they do not trigger priority.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "By including the letter 'L' in the flight plan", "is_correct": 0, "sort_order": 0},
                {"choice_text": "By including 'MEDEVAC' in the remarks section of the flight plan", "is_correct": 0, "sort_order": 1},
                {"choice_text": "By the pilot verbally stating 'MEDEVAC' followed by the call sign in radio transmissions", "is_correct": 1, "sort_order": 2},
                {"choice_text": "Priority is automatic for any aircraft with an IFR flight plan", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "Which priority category requires CARF authorization before priority handling is provided?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-4(h): Garden Plot flights require CARF notification that priority is authorized. All other priority categories are self-identifying or triggered by specific call signs.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "MEDEVAC flights", "is_correct": 0, "sort_order": 0},
                {"choice_text": "FLYNET aircraft", "is_correct": 0, "sort_order": 1},
                {"choice_text": "Garden Plot flights", "is_correct": 1, "sort_order": 2},
                {"choice_text": "SCOOT aircraft", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "According to 2-1-4(m), which type of aircraft must have priority?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-4(m): IFR aircraft must have priority over SVFR aircraft.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "VFR aircraft over SVFR aircraft", "is_correct": 0, "sort_order": 0},
                {"choice_text": "IFR aircraft over SVFR aircraft", "is_correct": 1, "sort_order": 1},
                {"choice_text": "SVFR aircraft over IFR aircraft", "is_correct": 0, "sort_order": 2},
                {"choice_text": "All aircraft have equal priority", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "What is the pronunciation of 'NAOC' as specified in 2-1-4?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-4(f): NIGHT WATCH 'NAOC' is pronounced NAY-OCK.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "NAY-OCK", "is_correct": 1, "sort_order": 0},
                {"choice_text": "NOCK", "is_correct": 0, "sort_order": 1},
                {"choice_text": "EN-AY-OH-SEE", "is_correct": 0, "sort_order": 2},
                {"choice_text": "NAY-OH-SEE", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "North American Route Program (NRP) aircraft are:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-4(n): NRP aircraft are not subject to route limiting restrictions such as published preferred IFR routes, LOA requirements, or standard operating procedures.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Subject to all published preferred IFR routes", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Not subject to route limiting restrictions", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Required to file routes at least 2 hours in advance", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Limited to routes within the continental United States only", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "Including 'MEDEVAC' in the remarks section of a flight plan is sufficient to obtain operational priority handling.",
            "question_type": "true_false",
            "explanation": "Per 2-1-4(b)(1) Note: Flight plan entries with 'L' or 'MEDEVAC' in remarks are informational only — they do NOT trigger priority. The pilot must verbally state 'MEDEVAC' in radio transmissions.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
        {
            "question_text": "An IFR aircraft must have priority over an SVFR aircraft.",
            "question_type": "true_false",
            "explanation": "Per 2-1-4(m): IFR aircraft must have priority over SVFR aircraft.",
            "difficulty": 1,
            "choices": [
                {"choice_text": "True", "is_correct": 1, "sort_order": 0},
                {"choice_text": "False", "is_correct": 0, "sort_order": 1},
            ],
        },
        {
            "question_text": "The term 'NAOC' will be part of the Flight ID in the flight plan.",
            "question_type": "true_false",
            "explanation": "Per 2-1-4(f) Note: The term 'NAOC' will NOT be a part of the Flight ID in the flight plan or used with the call sign. It may be used when the aircraft is airborne.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
        {
            "question_text": "Retaining an IFR flight plan gives an arriving IFR aircraft priority over VFR aircraft entering the traffic pattern.",
            "question_type": "true_false",
            "explanation": "Per 2-1-4 Note: A pilot's retention of an IFR flight plan does NOT afford priority over VFR aircraft. The IFR aircraft must adjust its flight path to enter the traffic pattern in sequence with arriving VFR aircraft.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 3,
            "content_json": {
                "instruction": "Which aircraft should receive priority?",
                "situation": "You are working approach control. In your airspace: (1) N123AB, IFR on 10-mile final; (2) N456CD, VFR in the pattern; (3) N789EF, pilot just stated 'MEDEVAC N789EF' requesting direct routing; (4) N012GH, IFR holding for weather. Traffic is heavy.",
                "para_context": "2-1-4: Baseline 'first come, first served.' Exceptions: (a) distress = right of way over all. (b)(1) MEDEVAC = priority when verbally identified. (m) IFR > SVFR. Note: IFR flight plan does not afford priority over VFR.",
                "choices": [
                    {"text": "N123AB — first in the sequence on final approach.", "is_correct": False},
                    {"text": "N789EF (MEDEVAC) — verbally identified air ambulance receives priority handling.", "is_correct": True},
                    {"text": "N456CD — VFR aircraft already in the pattern have right of way.", "is_correct": False},
                    {"text": "N012GH — the holding aircraft has been waiting longest.", "is_correct": False},
                ],
                "explanation": "Per 2-1-4(b)(1): A MEDEVAC flight verbally identified by the pilot receives priority handling. While baseline is 'first come, first served,' MEDEVAC is an explicit exception and takes precedence over routine IFR and VFR traffic.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_5(db: sqlite3.Connection):
    """2-1-5 EXPEDITIOUS COMPLIANCE"""
    para = "2-1-5"
    print(f"\n{'='*60}\nCurating {para} — EXPEDITIOUS COMPLIANCE\n{'='*60}")

    cards = [
        {
            "front": "What is the mutual responsibility of pilots and controllers under 2-1-5?",
            "back": "Pilots must comply with ATC clearances expeditiously. Controllers should allow sufficient time for pilots to respond when issuing clearances.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        {
            "question_text": "Pilots are required to comply with ATC clearances _____.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-5: The paragraph title is 'Expeditious Compliance' — pilots must comply with ATC clearances expeditiously.",
            "difficulty": 1,
            "choices": [{"choice_text": "expeditiously", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Which statement best reflects the controller's responsibility under 2-1-5?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-5: Controllers should allow sufficient time for pilots to respond to clearances — the duty of expeditious compliance is balanced by the controller's responsibility to give pilots adequate time.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Controllers must demand immediate compliance with every clearance", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Controllers should allow sufficient time for pilot response when issuing clearances", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Controllers have no responsibility for timing of pilot compliance", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Controllers may penalize pilots who do not respond within 5 seconds", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "A pilot may delay compliance with an ATC clearance if they disagree with the instruction.",
            "question_type": "true_false",
            "explanation": "Per 2-1-5: Pilots must comply expeditiously with ATC clearances. If a pilot cannot comply, they should advise ATC promptly rather than delaying.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 2,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "You issue a descent clearance. After 15 seconds the pilot has not responded and has not begun descending. Another aircraft is at the assigned altitude, 5 miles ahead and closing.",
                "para_context": "2-1-5: Pilots must comply expeditiously. Controllers should allow sufficient time for pilot response.",
                "choices": [
                    {"text": "Immediately file a pilot deviation — 15 seconds is excessive.", "is_correct": False},
                    {"text": "Reissue the clearance; if still no response, take action to ensure separation — the pilot may not have received the transmission.", "is_correct": True},
                    {"text": "Wait another 60 seconds — pilots have unlimited time to comply with any clearance.", "is_correct": False},
                    {"text": "Assume the pilot is complying silently and take no further action.", "is_correct": False},
                ],
                "explanation": "Per 2-1-5: The controller should allow reasonable time for pilot response, but if no response is received and separation is at risk, the controller must take proactive action. Expeditious compliance is expected but not at the cost of safety.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_6(db: sqlite3.Connection):
    """2-1-6 SAFETY ALERT (enhance existing strong coverage)"""
    para = "2-1-6"
    print(f"\n{'='*60}\nCurating {para} — SAFETY ALERT\n{'='*60}")

    cards = [
        {
            "front": "When must a controller issue a safety alert?",
            "back": "When you are aware an aircraft is in a position/altitude that, in your judgment, places it in unsafe proximity to terrain, obstructions, or other aircraft.",
            "card_type": "definition",
        },
        {
            "front": "When may a controller discontinue issuing safety alerts?",
            "back": "Once the pilot informs you action is being taken to resolve the situation. Do NOT assume another controller has issued the alert — inform the appropriate controller.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        {
            "question_text": "Issue a safety alert to an aircraft if you are aware the aircraft is in a position/altitude that, in your _____, places it in unsafe proximity to terrain, obstructions, or other aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-6: The controller's judgment is the trigger for issuing a safety alert.",
            "difficulty": 2,
            "choices": [{"choice_text": "judgment", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Once the pilot informs you action is being taken to resolve the situation, you may _____ the issuance of further alerts.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-6: Discontinue further alerts once the pilot confirms action is being taken.",
            "difficulty": 1,
            "choices": [{"choice_text": "discontinue", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Do not assume that because someone else has responsibility for the aircraft that the unsafe situation has been _____ and the safety alert issued; inform the appropriate controller.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-6: Do not assume another controller has observed the unsafe situation. You must inform the appropriate controller.",
            "difficulty": 2,
            "choices": [{"choice_text": "observed", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "You observe an aircraft on your radar that appears to be in unsafe proximity to terrain. The aircraft is under the jurisdiction of another controller. What must you do?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-6: Do not assume that because someone else has responsibility for the aircraft that the unsafe situation has been observed. Inform the appropriate controller and issue the safety alert.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "Nothing — the aircraft is under another controller's jurisdiction.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Inform the appropriate controller — do not assume the unsafe situation has been observed.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Wait 30 seconds to see if the other controller issues an alert.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Call the supervisor before taking any action.", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "A controller may safely assume another controller has issued a safety alert if that controller has responsibility for the aircraft.",
            "question_type": "true_false",
            "explanation": "Per 2-1-6: Do NOT assume another controller has observed the unsafe situation. You must inform the appropriate controller.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")


def curate_2_1_7(db: sqlite3.Connection):
    """2-1-7 INFLIGHT EQUIPMENT MALFUNCTIONS"""
    para = "2-1-7"
    print(f"\n{'='*60}\nCurating {para} — INFLIGHT EQUIPMENT MALFUNCTIONS\n{'='*60}")

    cards = [
        {
            "front": "What must a controller do when a pilot reports an inflight equipment malfunction?",
            "back": "Determine the nature and extent of any special handling desired by the pilot.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        {
            "question_text": "When a pilot reports an inflight equipment malfunction, determine the _____ and extent of any special handling desired.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-7(a): The controller must determine the nature and extent of special handling the pilot desires.",
            "difficulty": 1,
            "choices": [{"choice_text": "nature", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "When a pilot reports an inflight equipment malfunction, what is the controller's primary responsibility?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-7(a): Determine the nature and extent of any special handling desired. Do not assume — ask the pilot what they need.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Immediately declare an emergency and vector the aircraft to the nearest airport.", "is_correct": False, "sort_order": 0},
                {"choice_text": "Determine the nature and extent of any special handling the pilot desires.", "is_correct": True, "sort_order": 0},
                {"choice_text": "Transfer the aircraft to the next sector without delay.", "is_correct": False, "sort_order": 0},
                {"choice_text": "Assume the pilot needs no assistance unless an emergency is declared.", "is_correct": False, "sort_order": 0},
            ],
        },
        {
            "question_text": "When a pilot reports an equipment malfunction, the controller should assume the pilot needs to divert to the nearest airport.",
            "question_type": "true_false",
            "explanation": "Per 2-1-7(a): The controller must determine the nature and extent of special handling desired — do not assume. The pilot may need anything from no assistance to priority handling.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 2,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "A pilot reports 'Center, N123AB has lost our number two navigation radio.' The aircraft is at FL350, 200 miles from destination, in VMC.",
                "para_context": "2-1-7(a): When a pilot reports an inflight equipment malfunction, determine the nature and extent of any special handling desired.",
                "choices": [
                    {"text": "Declare an emergency and clear all traffic below the aircraft.", "is_correct": False},
                    {"text": "Ask the pilot what special handling, if any, they require due to the malfunction.", "is_correct": True},
                    {"text": "No action is required since the aircraft has a second navigation radio.", "is_correct": False},
                    {"text": "Immediately vector the aircraft to the nearest suitable airport.", "is_correct": False},
                ],
                "explanation": "Per 2-1-7(a): The controller must determine what special handling the pilot desires. Do not assume the severity — ask the pilot. The aircraft may need nothing, or may need specific assistance.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_8(db: sqlite3.Connection):
    """2-1-8 MINIMUM FUEL"""
    para = "2-1-8"
    print(f"\n{'='*60}\nCurating {para} — MINIMUM FUEL\n{'='*60}")

    cards = [
        {
            "front": "What must a controller do when an aircraft declares 'minimum fuel'?",
            "back": "1. Inform any facility to whom control jurisdiction is transferred of the minimum fuel problem.\n2. Be alert for any occurrence which might delay the aircraft en route.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        {
            "question_text": "If an aircraft declares a state of '_____ fuel,' inform any facility to whom control jurisdiction is transferred and be alert for any occurrence which might delay the aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-8: The exact phrase is 'minimum fuel.' This is NOT an emergency declaration but requires specific controller actions.",
            "difficulty": 1,
            "choices": [{"choice_text": "minimum", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "When an aircraft declares minimum fuel, the controller must inform the receiving facility and:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-8: Be alert for any occurrence which might delay the aircraft en route. Minimum fuel is not an emergency but requires heightened awareness.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Declare an emergency immediately.", "is_correct": False, "sort_order": 0},
                {"choice_text": "Be alert for any occurrence which might delay the aircraft en route.", "is_correct": True, "sort_order": 0},
                {"choice_text": "Vector the aircraft to the nearest airport regardless of destination.", "is_correct": False, "sort_order": 0},
                {"choice_text": "No action is required beyond normal handling.", "is_correct": False, "sort_order": 0},
            ],
        },
        {
            "question_text": "A declaration of 'minimum fuel' by a pilot is the same as declaring an emergency.",
            "question_type": "true_false",
            "explanation": "Per 2-1-8: 'Minimum fuel' is NOT an emergency declaration. It indicates the aircraft's fuel supply has reached a state where the flight cannot accept any undue delay. The controller must be alert for delays but does not treat it as an emergency.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 3,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "N456CD declares 'minimum fuel' while en route at FL280. Ten minutes later, you are about to hand off the aircraft to the next sector. The receiving sector is experiencing slight delays with aircraft holding at the boundary fix.",
                "para_context": "2-1-8: Inform any facility to whom control jurisdiction is transferred of the minimum fuel problem and be alert for any occurrence which might delay the aircraft.",
                "choices": [
                    {"text": "Hand off normally — minimum fuel is not your concern once the aircraft leaves your sector.", "is_correct": False},
                    {"text": "Inform the receiving facility of the minimum fuel status and coordinate to minimize any delay at the boundary.", "is_correct": True},
                    {"text": "Declare an emergency on behalf of the pilot and give the aircraft priority over all other traffic.", "is_correct": False},
                    {"text": "Tell the pilot to divert since the receiving sector has delays.", "is_correct": False},
                ],
                "explanation": "Per 2-1-8: You must inform the receiving facility of the minimum fuel problem. You should also be alert for and try to mitigate delays. While not an emergency, minimum fuel requires proactive coordination.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_9(db: sqlite3.Connection):
    """2-1-9 REPORTING ESSENTIAL FLIGHT INFORMATION"""
    para = "2-1-9"
    print(f"\n{'='*60}\nCurating {para} — REPORTING ESSENTIAL FLIGHT INFORMATION\n{'='*60}")

    cards = [
        {
            "front": "What must a controller do with information about NAS components or flight conditions that may adversely affect air safety?",
            "back": "Report as soon as possible to the appropriate FSS, airport manager's office, ARTCC, approach control facility, operations office, or military operations office.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  Flashcards: {n} inserted")

    questions = [
        {
            "question_text": "Report as soon as possible to the appropriate facility any information concerning components of the _____ or any flight conditions which may have an adverse effect on air safety.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-9: Information concerning NAS (National Airspace System) components or adverse flight conditions must be reported promptly.",
            "difficulty": 2,
            "choices": [{"choice_text": "NAS", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Which of the following is NOT listed in 2-1-9 as a facility to which essential flight information should be reported?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-9: Report to FSS, airport manager's office, ARTCC, approach control, operations office, or military operations office. 'Flight Standards District Office (FSDO)' is not listed.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "Flight Service Station (FSS)", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Airport manager's office", "is_correct": 0, "sort_order": 1},
                {"choice_text": "Flight Standards District Office (FSDO)", "is_correct": 1, "sort_order": 2},
                {"choice_text": "ARTCC", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "A controller who observes a NAVAID malfunction should report it:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-9: Report as soon as possible — not at the end of the shift or when convenient. Timely reporting of adverse conditions is essential for air safety.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "At the end of the shift during the position relief briefing.", "is_correct": False, "sort_order": 0},
                {"choice_text": "As soon as possible to the appropriate facility.", "is_correct": True, "sort_order": 0},
                {"choice_text": "Only if a pilot reports the same malfunction.", "is_correct": False, "sort_order": 0},
                {"choice_text": "By filing a written report within 24 hours.", "is_correct": False, "sort_order": 0},
            ],
        },
        {
            "question_text": "Controllers are only required to report flight conditions that have already caused an accident.",
            "question_type": "true_false",
            "explanation": "Per 2-1-9: Report any flight conditions which MAY have an adverse effect on air safety — potential hazards must be reported, not just those that have already caused incidents.",
            "difficulty": 1,
            "choices": [
                {"choice_text": "True", "is_correct": 0, "sort_order": 0},
                {"choice_text": "False", "is_correct": 1, "sort_order": 1},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  Quiz Questions: {n} inserted")

    activities = [
        {
            "activity_type": "situation_action",
            "difficulty": 2,
            "content_json": {
                "instruction": "What should you do?",
                "situation": "While working approach control, a pilot reports that the localizer for Runway 27 appears to be giving erratic indications — they broke off the approach. A second aircraft is now on the same approach.",
                "para_context": "2-1-9: Report as soon as possible to the appropriate facility any information concerning components of the NAS or flight conditions which may have an adverse effect on air safety.",
                "choices": [
                    {"text": "Wait for a second pilot report before taking action — one report could be an isolated incident.", "is_correct": False},
                    {"text": "Immediately warn the second aircraft, report the potential NAVAID malfunction to the appropriate facility, and suspend approaches until the issue is resolved.", "is_correct": True},
                    {"text": "Tell the pilot to try the approach again — equipment is probably fine.", "is_correct": False},
                    {"text": "Log the report for review at the next quarterly safety meeting.", "is_correct": False},
                ],
                "explanation": "Per 2-1-9: The controller must report information concerning NAS components (like a localizer) that may adversely affect air safety as soon as possible. Waiting endangers subsequent aircraft.",
            },
        },
    ]
    n = insert_activities(db, para, activities)
    print(f"  Activities: {n} inserted")


def curate_2_1_10(db: sqlite3.Connection):
    """2-1-10 NAVAID MALFUNCTIONS (add to already strong coverage)"""
    para = "2-1-10"
    print(f"\nCurating {para} — NAVAID MALFUNCTIONS")

    cards = [{
        "front": "What two-step procedure must a controller follow when an aircraft reports a ground-based NAVAID malfunction?",
        "back": "1. Request a report from a second aircraft.\n2. If the second aircraft reports normal operations, continue use and inform the first aircraft of the discrepancy.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "When an aircraft reports a ground-based NAVAID malfunction, first request a report from a _____ aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-10(a)(1): Request a report from a second aircraft before taking action on a reported malfunction.",
            "difficulty": 1,
            "choices": [{"choice_text": "second", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "If a second aircraft reports normal NAVAID operations after another pilot reported a malfunction, the controller should:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-10(a)(2): Continue use of the NAVAID and inform the first aircraft of the normal report.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "NOTAM the NAVAID as out of service immediately.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Continue use and inform the first aircraft.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Wait for a third report before making a decision.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Shut down the approach procedure using that NAVAID.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}")


def curate_2_1_11(db: sqlite3.Connection):
    """2-1-11 USE OF MARSA"""
    para = "2-1-11"
    print(f"\nCurating {para} — USE OF MARSA")

    cards = [{
        "front": "When may MARSA be applied?",
        "back": "MARSA may only be applied to military operations specified in a letter of agreement or other appropriate FAA or military document.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "MARSA may only be applied to _____ operations specified in a letter of agreement or other appropriate FAA or military document.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-11(a): MARSA is exclusively for military operations with prior authorization in an LOA or appropriate document.",
            "difficulty": 1,
            "choices": [{"choice_text": "military", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "MARSA may be applied to any military formation flight upon the pilot's verbal request.",
            "question_type": "true_false",
            "explanation": "Per 2-1-11(a): MARSA may ONLY be applied to operations specified in an LOA or appropriate FAA/military document. A pilot's ad-hoc verbal request is insufficient.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 3,
        "content_json": {
            "instruction": "Can MARSA be applied?",
            "situation": "Two F-16s from the same squadron request formation practice. The flight lead states 'we'll take MARSA.' There is no LOA or FAA/military document authorizing MARSA for this specific operation.",
            "para_context": "2-1-11(a): MARSA may only be applied to military operations specified in a letter of agreement or other appropriate FAA or military document.",
            "choices": [
                {"text": "Yes — the pilot verbally assumed separation responsibility.", "is_correct": False},
                {"text": "No — MARSA requires prior written authorization in an LOA or appropriate document.", "is_correct": True},
                {"text": "Yes — MARSA applies automatically to all military formation flights.", "is_correct": False},
                {"text": "No — MARSA only applies to civilian operations.", "is_correct": False},
            ],
            "explanation": "Per 2-1-11(a): MARSA cannot be applied on pilot request alone. It must be authorized in advance through an LOA or appropriate FAA/military document.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_12(db: sqlite3.Connection):
    """2-1-12 MILITARY PROCEDURES"""
    para = "2-1-12"
    print(f"\nCurating {para} — MILITARY PROCEDURES")

    cards = [{
        "front": "What are military procedures in the context of the 7110.65?",
        "back": "Additions, modifications, and exceptions to basic FAA procedures, prescribed when a common procedure has not been attained or to fulfill a specific military requirement.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Military procedures in the 7110.65 take the form of additions, modifications, and _____ to the basic FAA procedure.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-12: Military procedures are additions, modifications, and exceptions to basic FAA procedures.",
            "difficulty": 1,
            "choices": [{"choice_text": "exceptions", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Military procedures are prescribed when a common procedure has not been _____ or to fulfill a specific requirement.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-12: Military procedures fill gaps where common civil-military procedures have not been attained.",
            "difficulty": 2,
            "choices": [{"choice_text": "attained", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Who must apply military procedures prescribed in the 7110.65?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-12: Military procedures must be applied by the appropriate controllers — both civilian and military — when the circumstances call for them.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Military controllers only.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "All controllers (civilian or military) handling aircraft under the prescribed circumstances.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Civilian controllers only when a military controller is unavailable.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Only controllers at military airfields.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "Which procedure applies?",
            "situation": "You are a civilian controller at an ARTCC. A flight of four military aircraft requests a nonstandard formation approach covered by a military procedure in the 7110.65. The basic FAA procedure does not address this type of approach.",
            "para_context": "2-1-12: Military procedures are prescribed when a common procedure has not been attained. They must be applied by the appropriate controllers.",
            "choices": [
                {"text": "Apply the military procedure from the 7110.65 — it exists for this exact situation.", "is_correct": True},
                {"text": "Deny the request — civilian controllers cannot apply military procedures.", "is_correct": False},
                {"text": "Apply the closest basic FAA procedure even though it does not fit.", "is_correct": False},
                {"text": "Tell the flight to break formation and proceed individually.", "is_correct": False},
            ],
            "explanation": "Per 2-1-12: Military procedures are prescribed because no common procedure exists, and they must be applied regardless of whether the controller is civilian or military.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_13(db: sqlite3.Connection):
    """2-1-13 FORMATION FLIGHTS"""
    para = "2-1-13"
    print(f"\nCurating {para} — FORMATION FLIGHTS")

    cards = [{
        "front": "How are formation flights controlled, and who is responsible for separation within the formation?",
        "back": "Control formation flights as a single aircraft. Separation between aircraft within the formation rests with the flight leader and the pilots, including during transition periods.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Control formation flights as a _____ aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-13: The controller treats the entire formation as one aircraft for control purposes.",
            "difficulty": 1,
            "choices": [{"choice_text": "single", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Separation responsibility between aircraft within the formation rests with the flight _____ and the pilots of the other aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-13: The flight leader bears responsibility for separation within the formation.",
            "difficulty": 1,
            "choices": [{"choice_text": "leader", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Who is responsible for separation between aircraft within a formation during transition periods?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-13: The flight leader and pilots retain responsibility even during transition periods when aircraft maneuver to attain separation for individual control.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "The controller — separation responsibility transfers to ATC during transitions.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "The flight leader and pilots of the other aircraft in the flight.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "The lead aircraft only — wing aircraft have no responsibility.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "No one — transitions are uncontrolled by design.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "You are controlling a formation of four aircraft. The formation leader reports they are beginning a maneuver to transition from formation flight to individual control. During the transition, the aircraft will maneuver to attain separation from each other.",
            "para_context": "2-1-13: Control formation flights as a single aircraft. Separation within the formation rests with the flight leader and pilots, including during transition periods.",
            "choices": [
                {"text": "Issue individual separation instructions to each aircraft during the transition.", "is_correct": False},
                {"text": "Continue controlling the formation as a single aircraft — the flight leader is responsible for separation within the formation, even during transition.", "is_correct": True},
                {"text": "Tell the formation to abort the transition — controllers must maintain separation at all times.", "is_correct": False},
                {"text": "Hand off each aircraft to a different controller for individual control during the transition.", "is_correct": False},
            ],
            "explanation": "Per 2-1-13: The flight leader retains separation responsibility throughout transition periods. The controller continues to treat the formation as a single aircraft.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_14(db: sqlite3.Connection):
    """2-1-14 COORDINATE USE OF AIRSPACE"""
    para = "2-1-14"
    print(f"\nCurating {para} — COORDINATE USE OF AIRSPACE")

    cards = [{
        "front": "What must a controller ensure before allowing an aircraft to enter another controller's airspace?",
        "back": "Ensure the necessary coordination has been accomplished before you allow an aircraft under your control to enter another controller's area of jurisdiction.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Ensure that the necessary _____ has been accomplished before you allow an aircraft under your control to enter another controller's area of jurisdiction.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-14(a): Coordination is the prerequisite for crossing jurisdictional boundaries.",
            "difficulty": 1,
            "choices": [{"choice_text": "coordination", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "A controller may allow an aircraft to enter another controller's airspace while coordination is still in progress if the situation is urgent.",
            "question_type": "true_false",
            "explanation": "Per 2-1-14(a): Coordination must be accomplished BEFORE allowing the aircraft to enter. There is no exception for urgency.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "An aircraft under your control is 5 miles from the adjacent sector boundary. You have not yet coordinated the handoff with the receiving controller, who is busy working another aircraft.",
            "para_context": "2-1-14(a): Ensure coordination has been accomplished before allowing an aircraft to enter another controller's jurisdiction.",
            "choices": [
                {"text": "Allow the aircraft to cross — the receiving controller will adapt.", "is_correct": False},
                {"text": "Coordinate with the receiving controller before the aircraft reaches the boundary. Do not allow entry without coordination.", "is_correct": True},
                {"text": "Have the aircraft hold at the boundary without notifying the receiving controller.", "is_correct": False},
                {"text": "Transfer control silently — the data block will alert the receiving controller automatically.", "is_correct": False},
            ],
            "explanation": "Per 2-1-14(a): Coordination must be completed BEFORE the aircraft enters the other controller's jurisdiction. If coordination hasn't happened, complete it or hold the aircraft short of the boundary.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_15(db: sqlite3.Connection):
    """2-1-15 CONTROL TRANSFER"""
    para = "2-1-15"
    print(f"\nCurating {para} — CONTROL TRANSFER")

    cards = [{
        "front": "Under what two conditions may control of an aircraft be transferred?",
        "back": "1. At a prescribed or coordinated location, time, fix, or altitude.\n2. At the time a radar handoff and frequency change to the receiving controller have been completed.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Transfer control of an aircraft at a prescribed or coordinated location, time, _____, or altitude.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-15(a)(1): The four transfer triggers are location, time, fix, or altitude.",
            "difficulty": 2,
            "choices": [{"choice_text": "fix", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Control may be transferred when a radar _____ and frequency change to the receiving controller have been completed.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-15(a)(2): The radar handoff must be completed along with the frequency change.",
            "difficulty": 1,
            "choices": [{"choice_text": "handoff", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Control transfer must occur at exactly which of the following?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-15(a): Transfer may occur at any prescribed point — location, time, fix, OR altitude — OR upon completion of radar handoff and frequency change.",
            "difficulty": 3,
            "choices": [
                {"choice_text": "At the geographic boundary line only.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "At a prescribed or coordinated location, time, fix, or altitude — or when radar handoff and frequency change are complete.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Only when the receiving controller verbally accepts the transfer.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Whenever the transferring controller decides — coordination is encouraged but not required.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "Has control been properly transferred?",
            "situation": "Controller A initiates a radar handoff to Controller B. The data block flashes on Controller B's scope, but Controller B has not yet accepted. Controller A instructs the aircraft to contact Controller B's frequency. The pilot changes frequency before the handoff is accepted.",
            "para_context": "2-1-15(a)(2): Transfer control at the time a radar handoff AND frequency change to the receiving controller have been completed.",
            "choices": [
                {"text": "Yes — the pilot changed frequency, so transfer is complete.", "is_correct": False},
                {"text": "No — both the radar handoff AND frequency change must be completed. The handoff was not yet accepted.", "is_correct": True},
                {"text": "Yes — initiating the handoff is sufficient to transfer control.", "is_correct": False},
                {"text": "No — control transfer can only occur at a geographic fix, never by handoff.", "is_correct": False},
            ],
            "explanation": "Per 2-1-15(a)(2): Control transfer requires BOTH the radar handoff and frequency change to be completed. Initiating a handoff is not sufficient — it must be accepted by the receiving controller first.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")




def curate_2_1_16(db: sqlite3.Connection):
    """2-1-16 SURFACE AREAS"""
    para = "2-1-16"
    print(f"\nCurating {para} — SURFACE AREAS")

    cards = [{
        "front": "What must a controller do before issuing a clearance that would require flight within a surface area for which a tower has responsibility?",
        "back": "Coordinate with the appropriate nonapproach control tower on an individual aircraft basis, unless otherwise specified in a letter of agreement.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Coordinate with the appropriate nonapproach control tower on an individual _____ basis before issuing a clearance that would require flight within a surface area for which the tower has responsibility.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-16(a): Coordination must be done on an individual aircraft basis unless an LOA specifies otherwise.",
            "difficulty": 2,
            "choices": [{"choice_text": "aircraft", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "A controller must always coordinate individually with the tower for each aircraft entering a surface area, even if a letter of agreement says otherwise.",
            "question_type": "true_false",
            "explanation": "Per 2-1-16(a): Individual coordination is required UNLESS otherwise specified in a letter of agreement. An LOA may waive the individual coordination requirement.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "You are working approach control. You need to vector an IFR arrival through a portion of the tower's surface area at 1,200 feet to join the final approach course. Your facility has a letter of agreement with the tower that waives individual coordination for IFR arrivals on this procedure.",
            "para_context": "2-1-16(a): Coordinate with the tower on an individual aircraft basis unless otherwise specified in an LOA.",
            "choices": [
                {"text": "Coordinate with the tower for this specific aircraft before issuing the vector.", "is_correct": False},
                {"text": "Issue the vector without individual coordination — the LOA waives this requirement for IFR arrivals on this procedure.", "is_correct": True},
                {"text": "Hand the aircraft off to the tower and let them vector the aircraft.", "is_correct": False},
                {"text": "The aircraft cannot enter a surface area regardless of any LOA.", "is_correct": False},
            ],
            "explanation": "Per 2-1-16(a): If an LOA specifies alternative coordination procedures, individual aircraft coordination is not required. The LOA provisions take precedence.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_17(db: sqlite3.Connection):
    """2-1-17 RADIO COMMUNICATIONS (targeted additions)"""
    para = "2-1-17"
    print(f"\nCurating {para} — RADIO COMMUNICATIONS")

    cards = [{
        "front": "When must radio communications be transferred to the receiving controller?",
        "back": "Before an aircraft enters the receiving controller's area of jurisdiction, unless otherwise coordinated or specified by an LOA or facility directive.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Transfer radio communications _____ an aircraft enters the receiving controller's area of jurisdiction.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-17(a): Communications must be transferred before the aircraft enters the receiving controller's airspace.",
            "difficulty": 1,
            "choices": [{"choice_text": "before", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Radio communications must always be transferred before the jurisdictional boundary, with no exceptions.",
            "question_type": "true_false",
            "explanation": "Per 2-1-17(a): Transfer before entry UNLESS otherwise coordinated or specified by an LOA or facility directive. Exceptions exist.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}")


def curate_2_1_18(db: sqlite3.Connection):
    """2-1-18 OPERATIONAL REQUESTS (targeted additions)"""
    para = "2-1-18"
    print(f"\nCurating {para} — OPERATIONAL REQUESTS")

    questions = [
        {
            "question_text": "A controller may respond to a request by restating the request followed by the word '_____'.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-18(a): Restate the request in complete or abbreviated terms followed by 'APPROVED.'",
            "difficulty": 1,
            "choices": [{"choice_text": "APPROVED", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "The phraseology '_____ AS REQUESTED' may be substituted in lieu of a lengthy readback of an operational request.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-18(a): 'APPROVED AS REQUESTED' is the standard shorthand for approving a request without lengthy readback.",
            "difficulty": 1,
            "choices": [{"choice_text": "APPROVED", "is_correct": 1, "sort_order": 0}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"\nCurating {para} — OPERATIONAL REQUESTS\n  FC:0 Q:{n}")


def curate_2_1_19(db: sqlite3.Connection):
    """2-1-19 WAKE TURBULENCE"""
    para = "2-1-19"
    print(f"\nCurating {para} — WAKE TURBULENCE")

    cards = [{
        "front": "When must wake turbulence procedures be applied?",
        "back": "Apply wake turbulence procedures to an aircraft operating behind another aircraft when wake turbulence separation is required.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Apply wake turbulence procedures to an aircraft operating _____ another aircraft when wake turbulence separation is required.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-19(a): Wake turbulence procedures apply to aircraft operating behind another aircraft — the trailing aircraft needs the separation.",
            "difficulty": 1,
            "choices": [{"choice_text": "behind", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Wake turbulence separation is required:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-19(a): Wake turbulence procedures are applied to any aircraft operating behind another aircraft when the required wake turbulence separation minima apply.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Only when the pilot requests it.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "When an aircraft operates behind another aircraft and wake turbulence separation is required.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "For all aircraft regardless of position.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Only during VFR conditions.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "A B737 is on a 5-mile final behind a B757 that landed 2 minutes ago. The required wake turbulence separation behind a B757 is 4 miles. Current radar shows the B737 is 4.5 miles from the runway threshold.",
            "para_context": "2-1-19(a): Apply wake turbulence procedures to an aircraft operating behind another aircraft when wake turbulence separation is required.",
            "choices": [
                {"text": "Clear the B737 to land — 4.5 miles exceeds the 4-mile minimum.", "is_correct": False},
                {"text": "Ensure the B737 maintains at least 4 miles of separation until the runway threshold — wake turbulence separation must be maintained throughout.", "is_correct": True},
                {"text": "Wake turbulence is not a factor after the preceding aircraft has landed.", "is_correct": False},
                {"text": "Ask the B737 pilot if they want additional separation — wake turbulence is advisory only.", "is_correct": False},
            ],
            "explanation": "Per 2-1-19(a): Wake turbulence procedures are mandatory when separation is required. The controller must ensure the required separation is maintained — it is not advisory and does not end when the preceding aircraft lands.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_20(db: sqlite3.Connection):
    """2-1-20 WAKE TURBULENCE CAUTIONARY ADVISORIES (targeted additions)"""
    para = "2-1-20"
    print(f"\nCurating {para} — WAKE TURBULENCE CAUTIONARY ADVISORIES")

    questions = [
        {
            "question_text": "Issue wake turbulence cautionary advisories including the _____, altitude if known, and direction of flight of the preceding aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-20(a): The advisory must include position, altitude (if known), and direction of flight.",
            "difficulty": 2,
            "choices": [{"choice_text": "position", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "A wake turbulence cautionary advisory must include the position, altitude, and _____ of flight of the preceding aircraft.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-20(a): The three required elements are position, altitude (if known), and direction of flight.",
            "difficulty": 2,
            "choices": [{"choice_text": "direction", "is_correct": 1, "sort_order": 0}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"\nCurating {para} — WAKE TURBULENCE CAUTIONARY ADVISORIES\n  FC:0 Q:{n}")




def curate_2_1_21(db: sqlite3.Connection):
    """2-1-21 TRAFFIC ADVISORIES (targeted)"""
    para = "2-1-21"
    print(f"\nCurating {para} — TRAFFIC ADVISORIES")
    questions = [
        {
            "question_text": "Issue traffic advisories to all aircraft on your frequency when, in your _____, their proximity may diminish to less than the applicable separation minima.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-21: The trigger for issuing traffic advisories is the controller's judgment that proximity may diminish below separation minima.",
            "difficulty": 2,
            "choices": [{"choice_text": "judgment", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Traffic advisories must be issued to IFR aircraft only — VFR aircraft are responsible for their own separation.",
            "question_type": "true_false",
            "explanation": "Per 2-1-21: Traffic advisories are issued to ALL aircraft (IFR or VFR) on your frequency, unless in Class A airspace or omission is requested by the pilot.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  FC:0 Q:{n}")


def curate_2_1_22(db: sqlite3.Connection):
    """2-1-22 UAS ACTIVITY INFORMATION"""
    para = "2-1-22"
    print(f"\nCurating {para} — UAS ACTIVITY INFORMATION")

    cards = [{
        "front": "What information must be included in a UAS activity advisory, if known?",
        "back": "Position, distance, course, type of unmanned aircraft (UA), and altitude.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Issue UAS advisory information when, in your judgment, their _____ warrants it.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-22(a): UAS advisories are issued when proximity warrants — a judgment call by the controller.",
            "difficulty": 1,
            "choices": [{"choice_text": "proximity", "is_correct": 1, "sort_order": 0}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "A pilot reports seeing a drone approximately 2 miles ahead at their altitude. You have no other information about this UAS. Another aircraft is on the same route, 5 miles behind the reporting aircraft.",
            "para_context": "2-1-22(a): Issue UAS advisory information for known UAS activity when proximity warrants. Include position, distance, course, type, and altitude if known.",
            "choices": [
                {"text": "No action needed — one report doesn't confirm the UAS is still there.", "is_correct": False},
                {"text": "Issue a UAS advisory to the trailing aircraft with the reported position, distance, and altitude.", "is_correct": True},
                {"text": "Wait for a second pilot report before issuing any advisory.", "is_correct": False},
                {"text": "Close the airspace to all traffic until the UAS is confirmed gone.", "is_correct": False},
            ],
            "explanation": "Per 2-1-22(a): When you have known UAS activity and another aircraft's proximity warrants it, issue the advisory with whatever information you have. One credible report is sufficient to trigger the advisory.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_23(db: sqlite3.Connection):
    """2-1-23 BIRD ACTIVITY INFORMATION"""
    para = "2-1-23"
    print(f"\nCurating {para} — BIRD ACTIVITY INFORMATION")

    cards = [{
        "front": "For how long must controllers issue bird activity advisories after receipt of a report?",
        "back": "At least 15 minutes after receipt of the report.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Issue bird activity advisories for at least _____ minutes after receipt of the report.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-23(a): Controllers must continue issuing bird activity advisories for at least 15 minutes after the initial report.",
            "difficulty": 1,
            "choices": [{"choice_text": "15", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Bird activity advisories must include position, species or size if known, course of flight, and _____.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-23(a): Include position, species or size of birds (if known), course of flight, and altitude.",
            "difficulty": 2,
            "choices": [{"choice_text": "altitude", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "A controller receives a bird activity report at 1420Z. Until what time must advisories be issued at minimum?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-23(a): Advisories must continue for at least 15 minutes. 1420 + 15 min = 1435Z.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "1425Z", "is_correct": 0, "sort_order": 0},
                {"choice_text": "1435Z", "is_correct": 1, "sort_order": 1},
                {"choice_text": "1500Z", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Until the birds are confirmed gone, with no time minimum.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "At 1405Z, a pilot reports a large flock of geese at 3,000 feet, 2 miles north of the airport, heading southeast. You issue advisories to aircraft in the area. At 1418Z — 13 minutes later — another aircraft is about to depart on a route that will pass near the reported location.",
            "para_context": "2-1-23(a): Issue advisories for at least 15 minutes after receipt of the report. Include position, species/size, course, and altitude.",
            "choices": [
                {"text": "The 15-minute requirement has nearly elapsed — no advisory is needed for the departing aircraft.", "is_correct": False},
                {"text": "Issue the advisory — 15 minutes have not elapsed since the report (1405 + 15 = 1420Z).", "is_correct": True},
                {"text": "Issue the advisory only if the pilot asks about bird activity.", "is_correct": False},
                {"text": "13 minutes is close enough to 15 — advisories can stop now.", "is_correct": False},
            ],
            "explanation": "Per 2-1-23(a): Advisories must be issued for AT LEAST 15 minutes after receipt. At 1418Z, only 13 minutes have passed — the advisory requirement is still in effect until 1420Z.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_24(db: sqlite3.Connection):
    """2-1-24 TRANSFER OF POSITION RESPONSIBILITY (CRITICAL — 0 Q, 0 ACT)"""
    para = "2-1-24"
    print(f"\nCurating {para} — TRANSFER OF POSITION RESPONSIBILITY (PRIORITY)")

    cards = [
        {
            "front": "How must transfer of position responsibility be accomplished?",
            "back": "In accordance with the Standard Operating Practice (SOP) for the Transfer of Position Responsibility and appropriate facility directives — each time operational responsibility for a position is transferred.",
            "card_type": "definition",
        },
        {
            "front": "When must the transfer of position responsibility procedures be followed?",
            "back": "Each and every time operational responsibility for a position is transferred between controllers.",
            "card_type": "definition",
        },
    ]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "The transfer of position responsibility must be accomplished in accordance with the Standard Operating Practice for the Transfer of Position Responsibility and appropriate facility directives _____ time operational responsibility for a position is transferred.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-24: The SOP must be followed EACH time responsibility transfers — no exceptions for routine or frequent transfers.",
            "difficulty": 1,
            "choices": [{"choice_text": "each", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Position responsibility transfer must follow:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-24: Transfer must follow BOTH the SOP for Transfer of Position Responsibility AND appropriate facility directives.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Only verbal coordination between controllers — no formal procedure is required.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "The SOP for Transfer of Position Responsibility and appropriate facility directives.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Only the facility directives — the SOP is optional guidance.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Any procedure the transferring controller deems appropriate.", "is_correct": 0, "sort_order": 3},
            ],
        },
        {
            "question_text": "The transfer of position responsibility procedure is only required at the end of a shift.",
            "question_type": "true_false",
            "explanation": "Per 2-1-24: The procedure must be followed EACH TIME operational responsibility is transferred — including mid-shift breaks, sector combination/decombination, and any other transfer.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "You are being relieved for a 15-minute break by another controller. This is a routine mid-shift relief. You have been working the position for 45 minutes and the traffic is moderate.",
            "para_context": "2-1-24: The transfer of position responsibility must be accomplished in accordance with the SOP and facility directives each time operational responsibility is transferred.",
            "choices": [
                {"text": "Just tell the relieving controller 'traffic is moderate' and leave — it's only 15 minutes.", "is_correct": False},
                {"text": "Complete the full SOP transfer procedure including position briefing per facility directives — it is required for EVERY transfer, regardless of duration.", "is_correct": True},
                {"text": "A transfer procedure is only required if the relieving controller asks for it.", "is_correct": False},
                {"text": "Since you're coming back in 15 minutes, no transfer of responsibility actually occurs.", "is_correct": False},
            ],
            "explanation": "Per 2-1-24: The SOP for Transfer of Position Responsibility must be followed EACH time operational responsibility transfers — even for brief relief periods. Duration of absence does not matter.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_25(db: sqlite3.Connection):
    """2-1-25 WHEELS DOWN CHECK (targeted)"""
    para = "2-1-25"
    print(f"\nCurating {para} — WHEELS DOWN CHECK")
    questions = [
        {
            "question_text": "Remind _____ aircraft to check wheels down on each approach unless the pilot has previously reported wheels down for that approach.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-25: This applies specifically to USA/USN (military) aircraft.",
            "difficulty": 2,
            "choices": [{"choice_text": "USA/USN", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "A USAF aircraft on approach requires a wheels-down reminder on every approach regardless of prior reports.",
            "question_type": "true_false",
            "explanation": "Per 2-1-25: The wheels-down check applies to USA/USN aircraft only, and the reminder is not needed if the pilot has previously reported wheels down for that approach.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  FC:0 Q:{n}")


def curate_2_1_26(db: sqlite3.Connection):
    """2-1-26 SUPERVISORY NOTIFICATION (CRITICAL — 0 Q)"""
    para = "2-1-26"
    print(f"\nCurating {para} — SUPERVISORY NOTIFICATION (PRIORITY)")

    cards = [{
        "front": "What conditions require notification of the supervisor/CIC under 2-1-26?",
        "back": "1. Weather conditions affecting operations\n2. Equipment status changes\n3. Potential sector overload\n4. Emergency situations\nAnd other conditions impacting sector/position operations.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "Ensure the supervisor/CIC is aware of conditions which impact sector/position operations including, but not limited to: weather, equipment status, potential sector _____, and emergency situations.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-26(c): Potential sector overload is one of the specific conditions requiring supervisory notification.",
            "difficulty": 1,
            "choices": [{"choice_text": "overload", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "Which of the following is NOT explicitly listed in 2-1-26 as a condition requiring supervisory notification?",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-26: Weather, equipment status, potential sector overload, and emergency situations are listed. 'Routine shift change' is not a condition requiring special notification — though position transfer SOP applies.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Weather conditions affecting operations.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Equipment status changes.", "is_correct": 0, "sort_order": 1},
                {"choice_text": "Routine shift change.", "is_correct": 1, "sort_order": 2},
                {"choice_text": "Potential sector overload.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 2,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "You are working a radar position when a fast-moving thunderstorm begins affecting multiple routes in your sector. Three aircraft request deviations, frequency congestion is rapidly increasing, and your primary radar display begins showing intermittent degradation.",
            "para_context": "2-1-26: Ensure supervisor/CIC is aware of conditions impacting operations including weather, equipment status, potential sector overload, and emergency situations.",
            "choices": [
                {"text": "Handle it yourself — calling the supervisor during busy periods is discouraged.", "is_correct": False},
                {"text": "Notify the supervisor/CIC immediately — weather, equipment degradation, and potential overload all require notification.", "is_correct": True},
                {"text": "Only notify the supervisor if a pilot declares an emergency.", "is_correct": False},
                {"text": "Wait 5 minutes to see if conditions improve before notifying anyone.", "is_correct": False},
            ],
            "explanation": "Per 2-1-26: Multiple notification triggers are present — weather, equipment status, and potential sector overload. The controller must ensure the supervisor is aware so they can manage sector resources appropriately.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")




def curate_2_1_27(db: sqlite3.Connection):
    """2-1-27 POSSIBLE PILOT DEVIATION (targeted)"""
    para = "2-1-27"
    print(f"\nCurating {para} — POSSIBLE PILOT DEVIATION")
    questions = [
        {
            "question_text": "When it appears that the actions of a pilot constitute a pilot deviation, notify the pilot, _____ permitting.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-27: Notification is required but contingent on workload — the controller must notify when workload permits.",
            "difficulty": 1,
            "choices": [{"choice_text": "workload", "is_correct": 1, "sort_order": 0}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  FC:0 Q:{n}")


def curate_2_1_28(db: sqlite3.Connection):
    """2-1-28 TCAS RESOLUTION ADVISORIES"""
    para = "2-1-28"
    print(f"\nCurating {para} — TCAS RESOLUTION ADVISORIES")

    cards = [{
        "front": "What must a controller NOT do when an aircraft is responding to a TCAS Resolution Advisory (RA)?",
        "back": "Do not issue control instructions contrary to the RA procedure that the crew has advised they are executing.",
        "card_type": "definition",
    }]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")

    questions = [
        {
            "question_text": "When an aircraft informs you it is responding to a TCAS RA, do _____ issue control instructions that are contrary to the RA procedure.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-28(a): The controller must NOT issue instructions contrary to the RA the crew is executing.",
            "difficulty": 1,
            "choices": [{"choice_text": "not", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "When a pilot reports a TCAS RA, the controller should immediately issue a conflicting instruction to resolve the traffic situation faster than TCAS can.",
            "question_type": "true_false",
            "explanation": "Per 2-1-28(a): Do NOT issue control instructions contrary to the RA. The pilot must follow the RA — the controller's role is to support, not override, the TCAS maneuver.",
            "difficulty": 2,
            "choices": [{"choice_text": "True", "is_correct": 0, "sort_order": 0}, {"choice_text": "False", "is_correct": 1, "sort_order": 1}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")

    activities = [{
        "activity_type": "situation_action",
        "difficulty": 3,
        "content_json": {
            "instruction": "What should you do?",
            "situation": "N123AB reports 'TCAS RA, climbing.' You were about to issue a descent clearance to the same aircraft for traffic that is now 1,000 feet below and climbing. The RA is instructing the pilot to climb.",
            "para_context": "2-1-28(a): Do not issue control instructions contrary to the RA procedure that a crew member has advised you they are executing.",
            "choices": [
                {"text": "Issue the descent clearance anyway — ATC instructions take priority over TCAS.", "is_correct": False},
                {"text": "Do not issue the descent — it contradicts the RA climb. Support the RA maneuver and manage other traffic accordingly.", "is_correct": True},
                {"text": "Tell the pilot to disregard the RA — TCAS is malfunctioning.", "is_correct": False},
                {"text": "Issue the descent but tell the pilot to follow whichever instruction they prefer.", "is_correct": False},
            ],
            "explanation": "Per 2-1-28(a): Once a pilot reports they are responding to an RA, the controller must not issue contrary instructions. The controller must work around the RA maneuver to maintain safety.",
        },
    }]
    n = insert_activities(db, para, activities)
    print(f"ACT:{n}")


def curate_2_1_29(db: sqlite3.Connection):
    """2-1-29 RVSM OPERATIONS (targeted — key hard numbers)"""
    para = "2-1-29"
    print(f"\nCurating {para} — RVSM OPERATIONS")

    questions = [
        {
            "question_text": "RVSM airspace is defined as any airspace between FL _____ and FL 410 inclusive.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-29: RVSM airspace exists between FL 290 and FL 410 inclusive.",
            "difficulty": 1,
            "choices": [{"choice_text": "290", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "In RVSM airspace, eligible aircraft are separated vertically by _____ feet.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-29: RVSM reduces vertical separation from 2,000 feet to 1,000 feet between FL 290 and FL 410.",
            "difficulty": 1,
            "choices": [{"choice_text": "1000", "is_correct": 1, "sort_order": 0}],  # will match '1,000' context
        },
        {
            "question_text": "RVSM vertical separation of 1,000 feet applies:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-29: RVSM applies between FL 290 and FL 410 inclusive, for eligible aircraft only.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "To all aircraft at all altitudes.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Between FL 290 and FL 410 inclusive for eligible aircraft.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Only above FL 410.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Only in oceanic airspace.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  FC:0 Q:{n}")


def curate_2_1_30(db: sqlite3.Connection):
    """2-1-30 TAWS ALERTS"""
    para = "2-1-30"
    print(f"\nCurating {para} — TAWS ALERTS")

    questions = [
        {
            "question_text": "When an aircraft informs you it is responding to a TAWS alert, do _____ issue control instructions contrary to the TAWS procedure the crew is executing.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-30(a): Same principle as TCAS — do not override onboard safety system alerts with contrary instructions.",
            "difficulty": 1,
            "choices": [{"choice_text": "not", "is_correct": 1, "sort_order": 0}],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  FC:0 Q:{n}")


def curate_2_1_31(db: sqlite3.Connection):
    """2-1-31 BLUE LIGHTNING EVENTS"""
    para = "2-1-31"
    print(f"\nCurating {para} — BLUE LIGHTNING EVENTS")

    questions = [
        {
            "question_text": "Ensure the supervisor/CIC is notified of reports of possible _____ trafficking, which may be referred to as 'Blue Lightning' events.",
            "question_type": "fill_blank",
            "explanation": "Per 2-1-31: 'Blue Lightning' is the referral term for possible human trafficking reports that must be brought to the supervisor's attention.",
            "difficulty": 1,
            "choices": [{"choice_text": "human", "is_correct": 1, "sort_order": 0}],
        },
        {
            "question_text": "'Blue Lightning' refers to reports of possible:",
            "question_type": "multiple_choice",
            "explanation": "Per 2-1-31: Blue Lightning events are reports of possible human trafficking that must be reported to the supervisor/CIC.",
            "difficulty": 2,
            "choices": [
                {"choice_text": "Aircraft electrical system malfunctions.", "is_correct": 0, "sort_order": 0},
                {"choice_text": "Human trafficking.", "is_correct": 1, "sort_order": 1},
                {"choice_text": "Severe weather with lightning activity.", "is_correct": 0, "sort_order": 2},
                {"choice_text": "Military intercept operations.", "is_correct": 0, "sort_order": 3},
            ],
        },
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"  FC:0 Q:{n}")



def curate_2_2_1(db: sqlite3.Connection):
    """2-2-1 RECORDING INFORMATION"""
    para = "2-2-1"
    print(f"\nCurating {para} — RECORDING INFORMATION")
    cards = [{'front': 'What flight plan information must be recorded per 2-2-1?', 'back': 'Record flight plan information required by the type of flight plan and existing circumstances, using authorized abbreviations when possible.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Record flight plan information required by the type of flight plan and existing circumstances. Use authorized _____ when possible.', "question_type": "fill_blank", "explanation": 'Per 2-2-1(a): Authorized abbreviations should be used when possible.', "difficulty": 1, "choices": [{"choice_text": "abbreviations", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_2(db: sqlite3.Connection):
    """2-2-2 FORWARDING INFORMATION"""
    para = "2-2-2"
    print(f"\nCurating {para} — FORWARDING INFORMATION")
    cards = [{'front': 'What must be recorded when forwarding flight plan information?', 'back': 'Record the time of filing and delivery on the form when forwarding flight plan information to the appropriate facility.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Forward the flight plan information and record the time of _____ and delivery on the form.', "question_type": "fill_blank", "explanation": 'Per 2-2-2(a): Both the time of filing and delivery must be recorded.', "difficulty": 1, "choices": [{"choice_text": "filing", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_3(db: sqlite3.Connection):
    """2-2-3 FORWARDING VFR DATA"""
    para = "2-2-3"
    print(f"\nCurating {para} — FORWARDING VFR DATA")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward aircraft _____ times to FSSs or military operations offices when they have requested them.', "question_type": "fill_blank", "explanation": 'Per 2-2-3: Forward departure times when requested by FSS or military operations offices.', "difficulty": 1, "choices": [{"choice_text": "departure", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_4(db: sqlite3.Connection):
    """2-2-4 MILITARY DVFR DEPARTURES"""
    para = "2-2-4"
    print(f"\nCurating {para} — MILITARY DVFR DEPARTURES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward departure times on all _____ departures from joint-use airports to the military operations office.', "question_type": "fill_blank", "explanation": 'Per 2-2-4: DVFR (Defense VFR) departures from joint-use airports require forwarding departure times to the military operations office.', "difficulty": 1, "choices": [{"choice_text": "DVFR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_5(db: sqlite3.Connection):
    """2-2-5 IFR TO VFR FLIGHT PLAN CHANGE"""
    para = "2-2-5"
    print(f"\nCurating {para} — IFR TO VFR FLIGHT PLAN CHANGE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Request a pilot to contact the appropriate _____ if the pilot informs you of a desire to change from an IFR to a VFR flight plan.', "question_type": "fill_blank", "explanation": 'Per 2-2-5: The pilot must contact FSS to change from IFR to VFR flight plan.', "difficulty": 1, "choices": [{"choice_text": "FSS", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_6(db: sqlite3.Connection):
    """2-2-6 IFR FLIGHT PROGRESS DATA"""
    para = "2-2-6"
    print(f"\nCurating {para} — IFR FLIGHT PROGRESS DATA")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward control information from controller to controller within a facility, then to the _____ facility as the aircraft progresses along its route.', "question_type": "fill_blank", "explanation": 'Per 2-2-6: Control information must be forwarded to the receiving facility as the aircraft progresses.', "difficulty": 1, "choices": [{"choice_text": "receiving", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_7(db: sqlite3.Connection):
    """2-2-7 MANUAL INPUT OF COMPUTER-ASSIGNED BEACON CODES"""
    para = "2-2-7"
    print(f"\nCurating {para} — MANUAL INPUT OF COMPUTER-ASSIGNED BEACON CODES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When a flight plan is manually entered into the computer and a computer-assigned _____ code has been forwarded, insert it in the appropriate field.', "question_type": "fill_blank", "explanation": 'Per 2-2-7: The computer-assigned beacon code must be inserted as part of the input message.', "difficulty": 1, "choices": [{"choice_text": "beacon", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_8(db: sqlite3.Connection):
    """2-2-8 ALTRV INFORMATION"""
    para = "2-2-8"
    print(f"\nCurating {para} — ALTRV INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When an aircraft is part of an approved _____, forward only those items necessary to properly identify the flight or revise previously given information.', "question_type": "fill_blank", "explanation": 'Per 2-2-8: ALTRV (Altitude Reservation) flights require forwarding only essential identification and update items.', "difficulty": 1, "choices": [{"choice_text": "ALTRV", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_9(db: sqlite3.Connection):
    """2-2-9 COMPUTER MESSAGE VERIFICATION"""
    para = "2-2-9"
    print(f"\nCurating {para} — COMPUTER MESSAGE VERIFICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When you transfer control information by computer message, obtain acknowledgment that the receiving center has received the data via Service _____.', "question_type": "fill_blank", "explanation": 'Per 2-2-9: Use Service F to obtain acknowledgment of data receipt when automatic acknowledgment is not available.', "difficulty": 1, "choices": [{"choice_text": "F", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_10(db: sqlite3.Connection):
    """2-2-10 TRANSMIT PROPOSED FLIGHT PLAN"""
    para = "2-2-10"
    print(f"\nCurating {para} — TRANSMIT PROPOSED FLIGHT PLAN")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Transmit proposed flight plans which fall within an ARTCC's Proposed Boundary Crossing Time (_____) parameter to adjacent ARTCCs.", "question_type": "fill_blank", "explanation": 'Per 2-2-10(a): PBCT = Proposed Boundary Crossing Time parameter used for inter-center flight plan transmission.', "difficulty": 1, "choices": [{"choice_text": "PBCT", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_11(db: sqlite3.Connection):
    """2-2-11 FORWARDING AMENDED AND UTM DATA"""
    para = "2-2-11"
    print(f"\nCurating {para} — FORWARDING AMENDED AND UTM DATA")
    cards = [{'front': 'When must revisions to ETA information be forwarded per 2-2-11?', 'back': 'Only when the time differs by more than 3 minutes from the estimate given in the original flight plan.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Revisions to ETA information need only be forwarded when the time differs by more than _____ minutes from the estimate given in the original flight plan.', "question_type": "fill_blank", "explanation": 'Per 2-2-11(a): The 3-minute threshold is the trigger for forwarding ETA revisions — minor differences do not require forwarding.', "difficulty": 1, "choices": [{"choice_text": "3", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'You receive an updated ETA for an aircraft that differs by 2 minutes from the original. Must you forward this revision?', "question_type": "multiple_choice", "explanation": 'Per 2-2-11(a): The 3-minute rule — revisions of 3 minutes or less do not require forwarding.', "difficulty": 1, "choices": [{'choice_text': 'Yes — any change to ETA must be forwarded.', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'No — ETA revisions only need forwarding when the difference exceeds 3 minutes.', 'is_correct': 1, 'sort_order': 1}, {'choice_text': 'Yes — but only if the aircraft is IFR.', 'is_correct': 0, 'sort_order': 2}, {'choice_text': 'No — ETA revisions are never forwarded.', 'is_correct': 0, 'sort_order': 3}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_12(db: sqlite3.Connection):
    """2-2-12 AIRBORNE MILITARY FLIGHTS"""
    para = "2-2-12"
    print(f"\nCurating {para} — AIRBORNE MILITARY FLIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward to FSSs IFR flight plans and changes from VFR to IFR flight plans received from _____ military aircraft.', "question_type": "fill_blank", "explanation": 'Per 2-2-12: This applies specifically to information received from airborne military aircraft.', "difficulty": 1, "choices": [{"choice_text": "airborne", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_13(db: sqlite3.Connection):
    """2-2-13 FORWARDING FLIGHT PLAN DATA BETWEEN U.S. ARTCCs AND CANADIAN ACCs"""
    para = "2-2-13"
    print(f"\nCurating {para} — FORWARDING FLIGHT PLAN DATA BETWEEN U.S. ARTCCs AND CANADIAN ACCs")
    cards = [{'front': 'What is the lead time for handling proposed departure flight plans between U.S. ARTCCs and Canadian ACCs?', 'back': '30 minutes (or as bilaterally agreed) for domestic continental U.S./Canadian airspace.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Domestic proposed departure flight plans between ACCs and ARTCCs will be handled on a _____ minute lead time or as bilaterally agreed.', "question_type": "fill_blank", "explanation": 'Per 2-2-13(a): 30-minute lead time is the standard for domestic ACC-ARTCC coordination.', "difficulty": 1, "choices": [{"choice_text": "30", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_14(db: sqlite3.Connection):
    """2-2-14 TELETYPE FLIGHT DATA FORMAT"""
    para = "2-2-14"
    print(f"\nCurating {para} — TELETYPE FLIGHT DATA FORMAT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'U.S. ARTCCs transmit flight data to Canadian ACCs in NADIN II input format as described in the _____ exchange documentation.', "question_type": "fill_blank", "explanation": 'Per 2-2-14(a)(1): NADIN II is the standard format for U.S.-Canadian flight data exchange.', "difficulty": 1, "choices": [{"choice_text": "NADIN", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_2_15(db: sqlite3.Connection):
    """2-2-15 NORTH AMERICAN ROUTE PROGRAM INFORMATION"""
    para = "2-2-15"
    print(f"\nCurating {para} — NORTH AMERICAN ROUTE PROGRAM INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "'_____' must be retained in the remarks section of the flight plan if the aircraft is moved due to weather, traffic, or other tactical reasons.", "question_type": "fill_blank", "explanation": 'Per 2-2-15(a): The NRP designation must be preserved in remarks when an NRP aircraft is tactically rerouted.', "difficulty": 1, "choices": [{"choice_text": "NRP", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()



def curate_2_3_1(db: sqlite3.Connection):
    """2-3-1 GENERAL"""
    para = "2-3-1"
    print(f"\nCurating {para} — GENERAL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use flight progress _____ to post current data on air traffic and clearances required for control.', "question_type": "fill_blank", "explanation": 'Per 2-3-1: Flight progress strips are the standard tool for posting current data.', "difficulty": 1, "choices": [{"choice_text": "strips", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_2(db: sqlite3.Connection):
    """2-3-2 EN ROUTE DATA ENTRIES"""
    para = "2-3-2"
    print(f"\nCurating {para} — EN ROUTE DATA ENTRIES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Information recorded on flight progress strips (FAA Forms _____) must be entered in the correspondingly numbered spaces.', "question_type": "fill_blank", "explanation": 'Per 2-3-2(a): Form 7230-19 is the standard flight progress strip for en route operations.', "difficulty": 1, "choices": [{"choice_text": "7230-19", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_3(db: sqlite3.Connection):
    """2-3-3 OCEANIC DATA ENTRIES"""
    para = "2-3-3"
    print(f"\nCurating {para} — OCEANIC DATA ENTRIES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Oceanic data entries follow the same principles as en route entries but with _____-specific requirements for position reporting and time estimates.', "question_type": "fill_blank", "explanation": 'Per 2-3-3: Oceanic operations have specific data entry requirements.', "difficulty": 1, "choices": [{"choice_text": "oceanic", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_4(db: sqlite3.Connection):
    """2-3-4 TERMINAL DATA ENTRIES"""
    para = "2-3-4"
    print(f"\nCurating {para} — TERMINAL DATA ENTRIES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Terminal arrival information is recorded on FAA Forms 7230-7.1, 7230-7.2, and _____.', "question_type": "fill_blank", "explanation": 'Per 2-3-4(a): These three form variants cover terminal arrival strip requirements.', "difficulty": 1, "choices": [{"choice_text": "7230-8", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_5(db: sqlite3.Connection):
    """2-3-5 AIRCRAFT IDENTITY"""
    para = "2-3-5"
    print(f"\nCurating {para} — AIRCRAFT IDENTITY")
    cards = [{'front': 'What is the maximum length of an aircraft identifier on a flight progress strip?', 'back': 'Seven alphanumeric characters — combinations must not exceed this limit.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Indicate aircraft identity using combinations not to exceed _____ alphanumeric characters.', "question_type": "fill_blank", "explanation": 'Per 2-3-5: Aircraft identifiers are limited to seven alphanumeric characters maximum.', "difficulty": 1, "choices": [{"choice_text": "seven", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'An aircraft identifier on a flight progress strip may contain up to 10 alphanumeric characters.', "question_type": "true_false", "explanation": 'Per 2-3-5: Combinations must not exceed seven alphanumeric characters.', "difficulty": 1, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_6(db: sqlite3.Connection):
    """2-3-6 AIRCRAFT TYPE"""
    para = "2-3-6"
    print(f"\nCurating {para} — AIRCRAFT TYPE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use the approved aircraft type designator in accordance with FAA Order _____, Aircraft Type Designators.', "question_type": "fill_blank", "explanation": 'Per 2-3-6: FAA Order 7360.1 is the authoritative reference for aircraft type designators.', "difficulty": 1, "choices": [{"choice_text": "7360.1", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_7(db: sqlite3.Connection):
    """2-3-7 USAF/USN UNDERGRADUATE PILOTS"""
    para = "2-3-7"
    print(f"\nCurating {para} — USAF/USN UNDERGRADUATE PILOTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "To identify aircraft piloted by solo USAF/USN undergraduate student pilots, the aircraft identification must include the letter '_____'.", "question_type": "fill_blank", "explanation": "Per 2-3-7: The letter 'U' in the flight plan identifies undergraduate student pilots who may be restricted to VFR conditions.", "difficulty": 1, "choices": [{"choice_text": "U", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_8(db: sqlite3.Connection):
    """2-3-8 AIRCRAFT EQUIPMENT SUFFIX"""
    para = "2-3-8"
    print(f"\nCurating {para} — AIRCRAFT EQUIPMENT SUFFIX")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The aircraft equipment suffix is generated by automation using the equipment codes of the _____ flight plan.', "question_type": "fill_blank", "explanation": 'Per 2-3-8(a): ICAO flight plan equipment codes drive the automated generation of equipment suffixes.', "difficulty": 1, "choices": [{"choice_text": "ICAO", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_9(db: sqlite3.Connection):
    """2-3-9 CLEARANCE STATUS"""
    para = "2-3-9"
    print(f"\nCurating {para} — CLEARANCE STATUS")
    cards = [{'front': 'What symbol indicates holding instructions on a flight progress strip?', 'back': "The symbol 'H' at the clearance limit, followed by a dash (-) and other pertinent information.", 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": "To indicate delay status, use the symbol '_____' at the clearance limit when holding instructions have been issued.", "question_type": "fill_blank", "explanation": "Per 2-3-9(a): 'H' is the standard symbol indicating holding instructions at the clearance limit.", "difficulty": 1, "choices": [{"choice_text": "H", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_3_10(db: sqlite3.Connection):
    """2-3-10 CONTROL SYMBOLOGY"""
    para = "2-3-10"
    print(f"\nCurating {para} — CONTROL SYMBOLOGY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'You may use plain _____ markings when it will aid in understanding information recorded on flight progress strips.', "question_type": "fill_blank", "explanation": 'Per 2-3-10(a): Plain language may be used alongside standard symbols when it aids understanding.', "difficulty": 1, "choices": [{"choice_text": "language", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()



def curate_2_4_1(db: sqlite3.Connection):
    """2-4-1 RADIO COMMUNICATIONS"""
    para = "2-4-1"
    print(f"\nCurating {para} — RADIO COMMUNICATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When combining positions in the tower, do not use _____ control frequency for airborne communications.', "question_type": "fill_blank", "explanation": 'Per 2-4-1: Ground control frequency must not be used for airborne communications when positions are combined.', "difficulty": 1, "choices": [{"choice_text": "ground", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_10(db: sqlite3.Connection):
    """2-4-10 INTERPHONE TRANSMISSION PRIORITIES"""
    para = "2-4-10"
    print(f"\nCurating {para} — INTERPHONE TRANSMISSION PRIORITIES")
    cards = [{'front': 'What are the interphone transmission priorities?', 'back': '1st: Emergency messages including accident information.\n2nd: Clearance and control messages.\nAfter an emergency passes, lower priority is given to messages relating to that accident.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Give _____ priority to emergency messages including essential information on aircraft accidents or suspected accidents.', "question_type": "fill_blank", "explanation": 'Per 2-4-10(a): Emergency messages always take first priority on interphone.', "difficulty": 1, "choices": [{"choice_text": "first", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_11(db: sqlite3.Connection):
    """2-4-11 PRIORITY INTERRUPTION"""
    para = "2-4-11"
    print(f"\nCurating {para} — PRIORITY INTERRUPTION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Use the words '_____' or 'control' for interrupting lower priority messages when you have an emergency or control message to transmit.", "question_type": "fill_blank", "explanation": "Per 2-4-11: 'Emergency' or 'control' are the authorized priority interruption words.", "difficulty": 1, "choices": [{"choice_text": "emergency", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_12(db: sqlite3.Connection):
    """2-4-12 INTERPHONE MESSAGE FORMAT"""
    para = "2-4-12"
    print(f"\nCurating {para} — INTERPHONE MESSAGE FORMAT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Both the caller and receiver identify their facility and/or _____ in a manner that ensures they will not be confused with another.', "question_type": "fill_blank", "explanation": 'Per 2-4-12(a): Facility and position identification prevents confusion between positions.', "difficulty": 1, "choices": [{"choice_text": "position", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_13(db: sqlite3.Connection):
    """2-4-13 INTERPHONE MESSAGE TERMINATION"""
    para = "2-4-13"
    print(f"\nCurating {para} — INTERPHONE MESSAGE TERMINATION")
    cards = [{'front': 'How are interphone messages terminated?', 'back': 'Terminate interphone messages with your operating initials.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Terminate interphone messages with your operating _____.', "question_type": "fill_blank", "explanation": 'Per 2-4-13: Operating initials are the standard termination for interphone messages.', "difficulty": 1, "choices": [{"choice_text": "initials", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_14(db: sqlite3.Connection):
    """2-4-14 WORDS AND PHRASES"""
    para = "2-4-14"
    print(f"\nCurating {para} — WORDS AND PHRASES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use the words or phrases in radiotelephone and interphone communication as contained in the _____.', "question_type": "fill_blank", "explanation": 'Per 2-4-14(a): The Pilot/Controller Glossary (P/CG) is the authoritative source for standard phraseology.', "difficulty": 1, "choices": [{"choice_text": "P/CG", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_15(db: sqlite3.Connection):
    """2-4-15 EMPHASIS FOR CLARITY"""
    para = "2-4-15"
    print(f"\nCurating {para} — EMPHASIS FOR CLARITY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Treat aircraft with similar sounding identifications by _____ appropriate digits, letters, or similar sounding words to aid in distinguishing them.', "question_type": "fill_blank", "explanation": 'Per 2-4-15(a): Emphasis — not abbreviation — is the tool for distinguishing similar sounding callsigns.', "difficulty": 1, "choices": [{"choice_text": "emphasizing", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_16(db: sqlite3.Connection):
    """2-4-16 ICAO PHONETICS"""
    para = "2-4-16"
    print(f"\nCurating {para} — ICAO PHONETICS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use the _____ pronunciation of numbers and individual letters.', "question_type": "fill_blank", "explanation": 'Per 2-4-16: ICAO standard pronunciation must be used for numbers and letters.', "difficulty": 1, "choices": [{"choice_text": "ICAO", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_17(db: sqlite3.Connection):
    """2-4-17 NUMBERS USAGE"""
    para = "2-4-17"
    print(f"\nCurating {para} — NUMBERS USAGE")
    cards = [{'front': 'How are serial numbers stated in radio communications?', 'back': "State serial numbers as the separate digits. Example: '12' is stated as 'one two'.", 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'State serial numbers as the separate _____.', "question_type": "fill_blank", "explanation": 'Per 2-4-17(a): Serial numbers are spoken digit by digit, not as whole numbers.', "difficulty": 1, "choices": [{"choice_text": "digits", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_18(db: sqlite3.Connection):
    """2-4-18 NUMBER CLARIFICATION"""
    para = "2-4-18"
    print(f"\nCurating {para} — NUMBER CLARIFICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'If deemed necessary for clarity, controllers may restate numbers using either group or _____-digit form.', "question_type": "fill_blank", "explanation": 'Per 2-4-18(a): Numbers can be restated in group or single-digit form for clarity after the standard pronunciation.', "difficulty": 1, "choices": [{"choice_text": "single", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_19(db: sqlite3.Connection):
    """2-4-19 FACILITY IDENTIFICATION"""
    para = "2-4-19"
    print(f"\nCurating {para} — FACILITY IDENTIFICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "State the name of the facility followed by the word '_____' for airport traffic control towers.", "question_type": "fill_blank", "explanation": "Per 2-4-19(a): The standard format is '[name] tower' for airport traffic control towers.", "difficulty": 1, "choices": [{"choice_text": "tower", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_2(db: sqlite3.Connection):
    """2-4-2 MONITORING"""
    para = "2-4-2"
    print(f"\nCurating {para} — MONITORING")
    cards = [{'front': 'What must a controller monitor continuously?', 'back': 'Interphones and assigned radio frequencies must be monitored continuously.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Monitor interphones and assigned radio frequencies _____.', "question_type": "fill_blank", "explanation": "Per 2-4-2: Continuous monitoring is required — there is no 'occasional' or 'periodic' option.", "difficulty": 1, "choices": [{"choice_text": "continuously", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_20(db: sqlite3.Connection):
    """2-4-20 AIRCRAFT IDENTIFICATION"""
    para = "2-4-20"
    print(f"\nCurating {para} — AIRCRAFT IDENTIFICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use the _____ identification in reply to aircraft with similar sounding identifications.', "question_type": "fill_blank", "explanation": 'Per 2-4-20: Full identification must be used when replying to aircraft with similar sounding identifications.', "difficulty": 1, "choices": [{"choice_text": "full", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_21(db: sqlite3.Connection):
    """2-4-21 DESCRIPTION OF AIRCRAFT TYPES"""
    para = "2-4-21"
    print(f"\nCurating {para} — DESCRIPTION OF AIRCRAFT TYPES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Except for super and _____ aircraft, describe aircraft by military designator, service and type, or type only when issuing traffic information.', "question_type": "fill_blank", "explanation": "Per 2-4-21: 'Super' and 'heavy' aircraft have specific description exceptions when issuing traffic information.", "difficulty": 1, "choices": [{"choice_text": "heavy", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_22(db: sqlite3.Connection):
    """2-4-22 AIRSPACE CLASSES"""
    para = "2-4-22"
    print(f"\nCurating {para} — AIRSPACE CLASSES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Airspace classes A, B, C, D, E, and G are pronounced in _____ phonetics for clarification.', "question_type": "fill_blank", "explanation": "Per 2-4-22: ICAO phonetics apply to airspace class pronunciation. The term 'Class' may be dropped in communications.", "difficulty": 1, "choices": [{"choice_text": "ICAO", "is_correct": 1, "sort_order": 0}]},
        {"question_text": "The term 'Class' must always be included when referring to airspace in pilot/controller communications.", "question_type": "true_false", "explanation": "Per 2-4-22: The term 'Class' may be dropped — 'Bravo airspace' is acceptable in place of 'Class Bravo airspace.'", "difficulty": 1, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_3(db: sqlite3.Connection):
    """2-4-3 PILOT ACKNOWLEDGMENT/READ BACK"""
    para = "2-4-3"
    print(f"\nCurating {para} — PILOT ACKNOWLEDGMENT/READ BACK")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Ensure the read back of _____ short instructions is correct, whether part of taxi instructions or a LAHSO clearance.', "question_type": "fill_blank", "explanation": 'Per 2-4-3(b): Hold short readbacks must be verified for correctness — this is a critical safety item.', "difficulty": 1, "choices": [{"choice_text": "hold", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_4(db: sqlite3.Connection):
    """2-4-4 AUTHORIZED INTERRUPTIONS"""
    para = "2-4-4"
    print(f"\nCurating {para} — AUTHORIZED INTERRUPTIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'As necessary, authorize a pilot to _____ his/her communications guard.', "question_type": "fill_blank", "explanation": 'Per 2-4-4: Controllers may authorize pilots to interrupt monitoring when necessary.', "difficulty": 1, "choices": [{"choice_text": "interrupt", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_5(db: sqlite3.Connection):
    """2-4-5 AUTHORIZED TRANSMISSIONS"""
    para = "2-4-5"
    print(f"\nCurating {para} — AUTHORIZED TRANSMISSIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Transmit only those messages necessary for air traffic control or otherwise contributing to air _____.', "question_type": "fill_blank", "explanation": 'Per 2-4-5: Transmissions must be limited to ATC purposes or air safety contributions.', "difficulty": 1, "choices": [{"choice_text": "safety", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_6(db: sqlite3.Connection):
    """2-4-6 FALSE OR DECEPTIVE COMMUNICATIONS"""
    para = "2-4-6"
    print(f"\nCurating {para} — FALSE OR DECEPTIVE COMMUNICATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When false or deceptive communications occur, broadcast an _____ to aircraft operating on all frequencies.', "question_type": "fill_blank", "explanation": 'Per 2-4-6(b): An alert broadcast to all frequencies is required when false/deceptive communications are detected.', "difficulty": 1, "choices": [{"choice_text": "alert", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_7(db: sqlite3.Connection):
    """2-4-7 AUTHORIZED RELAYS"""
    para = "2-4-7"
    print(f"\nCurating {para} — AUTHORIZED RELAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Give the _____ of any operational message you relay to an aircraft.', "question_type": "fill_blank", "explanation": 'Per 2-4-7(a): The controller must identify the source of relayed messages.', "difficulty": 1, "choices": [{"choice_text": "source", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_8(db: sqlite3.Connection):
    """2-4-8 RADIO MESSAGE FORMAT"""
    para = "2-4-8"
    print(f"\nCurating {para} — RADIO MESSAGE FORMAT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'On initial radio contact, state the identification of the _____ first, followed by identification of the ATC unit.', "question_type": "fill_blank", "explanation": 'Per 2-4-8(a): Aircraft identification comes first, then ATC unit identification on initial contact.', "difficulty": 1, "choices": [{"choice_text": "aircraft", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_4_9(db: sqlite3.Connection):
    """2-4-9 ABBREVIATED TRANSMISSIONS"""
    para = "2-4-9"
    print(f"\nCurating {para} — ABBREVIATED TRANSMISSIONS")
    cards = [{'front': 'When can aircraft identification be abbreviated in radio transmissions?', 'back': 'Use the identification prefix and the last 3 digits or letters of the aircraft identification after communications have been established. Do NOT abbreviate similar sounding identifications.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Use the identification prefix and the last _____ digits or letters of the aircraft identification after communications have been established.', "question_type": "fill_blank", "explanation": 'Per 2-4-9(a): The last 3 digits/letters plus prefix is the standard abbreviation format after initial contact.', "difficulty": 1, "choices": [{"choice_text": "3", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'Similar sounding aircraft identifications may be abbreviated after communications have been established.', "question_type": "true_false", "explanation": 'Per 2-4-9(b): Do NOT abbreviate similar sounding aircraft identifications — they must remain full to prevent confusion.', "difficulty": 1, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()



def curate_2_10_1(db: sqlite3.Connection):
    """2-10-1 EN ROUTE OR OCEANIC SECTOR TEAM POSITION RESPONSIBILITIES"""
    para = "2-10-1"
    print(f"\nCurating {para} — EN ROUTE OR OCEANIC SECTOR TEAM POSITION RESPONSIBILITIES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'There are no _____ divisions of responsibilities regarding position operations in the en route/oceanic team concept.', "question_type": "fill_blank", "explanation": 'Per 2-10-1(a): Responsibilities are shared — the team as a whole is responsible for safe and efficient operations.', "difficulty": 1, "choices": [{"choice_text": "absolute", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_10_2(db: sqlite3.Connection):
    """2-10-2 TERMINAL RADAR/NONRADAR TEAM POSITION RESPONSIBILITIES"""
    para = "2-10-2"
    print(f"\nCurating {para} — TERMINAL RADAR/NONRADAR TEAM POSITION RESPONSIBILITIES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The tasks to be completed remain the same whether one, two, or _____ people are working positions within a terminal facility/sector.', "question_type": "fill_blank", "explanation": 'Per 2-10-2(a): The team concept applies regardless of staffing level — the same tasks must be completed.', "difficulty": 1, "choices": [{"choice_text": "three", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_10_3(db: sqlite3.Connection):
    """2-10-3 TOWER TEAM POSITION RESPONSIBILITIES"""
    para = "2-10-3"
    print(f"\nCurating {para} — TOWER TEAM POSITION RESPONSIBILITIES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'In the tower team concept, each controller has strictly defined responsibilities that cannot be shared with other team members.', "question_type": "true_false", "explanation": 'Per 2-10-3(a): There are no absolute divisions of responsibilities. The team as a whole shares responsibility for safe and efficient operations.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_5_1(db: sqlite3.Connection):
    """2-5-1 AIR TRAFFIC SERVICE (ATS) ROUTES"""
    para = "2-5-1"
    print(f"\nCurating {para} — AIR TRAFFIC SERVICE (ATS) ROUTES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "State the word '_____' followed by the number of the airway in group form for VOR airways.", "question_type": "fill_blank", "explanation": "Per 2-5-1(a): VOR airways are identified as 'Victor' with the number in group form.", "difficulty": 1, "choices": [{"choice_text": "Victor", "is_correct": 1, "sort_order": 0}]},
        {"question_text": "State the letter '_____' followed by the number of the route in group form for jet routes.", "question_type": "fill_blank", "explanation": "Per 2-5-1(a): Jet routes are identified with the letter 'J' followed by the number in group form.", "difficulty": 1, "choices": [{"choice_text": "J", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_5_2(db: sqlite3.Connection):
    """2-5-2 NAVAID TERMS"""
    para = "2-5-2"
    print(f"\nCurating {para} — NAVAID TERMS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Describe NAVAIDs by stating the name or _____ followed by the type of NAVAID.', "question_type": "fill_blank", "explanation": 'Per 2-5-2(a): NAVAIDs are described by name or phonetic spelling followed by the type.', "difficulty": 1, "choices": [{"choice_text": "phonetic", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_5_3(db: sqlite3.Connection):
    """2-5-3 NAVAID FIXES"""
    para = "2-5-3"
    print(f"\nCurating {para} — NAVAID FIXES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Describe fixes determined by reference to a radial/localizer/azimuth and _____ from a VOR-DME/VORTAC/TACAN/ILS-DME.', "question_type": "fill_blank", "explanation": 'Per 2-5-3: Fixes are described by radial/localizer/azimuth AND distance from the defining NAVAID.', "difficulty": 1, "choices": [{"choice_text": "distance", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_6_1(db: sqlite3.Connection):
    """2-6-1 FAMILIARIZATION"""
    para = "2-6-1"
    print(f"\nCurating {para} — FAMILIARIZATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Controllers must become familiar with pertinent _____ information when coming on duty.', "question_type": "fill_blank", "explanation": 'Per 2-6-1: Weather familiarization is a duty requirement when assuming a position.', "difficulty": 1, "choices": [{"choice_text": "weather", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_6_2(db: sqlite3.Connection):
    """2-6-2 PIREP SOLICITATION AND DISSEMINATION"""
    para = "2-6-2"
    print(f"\nCurating {para} — PIREP SOLICITATION AND DISSEMINATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Emphasis must be placed on the solicitation and dissemination of Urgent (_____) and Routine (UA) PIREPs.', "question_type": "fill_blank", "explanation": 'Per 2-6-2: UUA = Urgent PIREP, UA = Routine PIREP. Both must be actively solicited and disseminated.', "difficulty": 2, "choices": [{"choice_text": "UUA", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_6_3(db: sqlite3.Connection):
    """2-6-3 REPORTING WEATHER CONDITIONS"""
    para = "2-6-3"
    print(f"\nCurating {para} — REPORTING WEATHER CONDITIONS")
    cards = [{'front': 'When must tower personnel take prevailing visibility observations?', 'back': 'When the prevailing visibility at the usual point of observation, or at the tower level, is less than 4 miles.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'When prevailing visibility is less than _____ miles, tower personnel must take prevailing visibility observations.', "question_type": "fill_blank", "explanation": 'Per 2-6-3(a): The 4-mile threshold triggers mandatory tower visibility observations.', "difficulty": 1, "choices": [{"choice_text": "4", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'When both tower and surface visibility observations are available, use the higher of the two.', "question_type": "true_false", "explanation": 'Per 2-6-3(a)(1): Use the LOWER of the two observations (tower or surface) for aircraft operations.', "difficulty": 3, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_6_4(db: sqlite3.Connection):
    """2-6-4 ISSUING WEATHER AND CHAFF AREAS"""
    para = "2-6-4"
    print(f"\nCurating {para} — ISSUING WEATHER AND CHAFF AREAS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Define the area of weather/chaff coverage in terms of azimuth by referring to the _____-hour clock and distance from the aircraft.', "question_type": "fill_blank", "explanation": 'Per 2-6-4(a)(1): The 12-hour clock reference system is used for azimuth description.', "difficulty": 1, "choices": [{"choice_text": "12", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_6_5(db: sqlite3.Connection):
    """2-6-5 DISSEMINATING OFFICIAL WEATHER INFORMATION"""
    para = "2-6-5"
    print(f"\nCurating {para} — DISSEMINATING OFFICIAL WEATHER INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Observed weather elements which do not include _____ values, such as 'large breaks in the overcast,' may be disseminated as general weather information.", "question_type": "fill_blank", "explanation": 'Per 2-6-5(a): General statements without specific values are acceptable for non-instrument weather observations.', "difficulty": 1, "choices": [{"choice_text": "specific", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_6_6(db: sqlite3.Connection):
    """2-6-6 HAZARDOUS INFLIGHT WEATHER ADVISORY"""
    para = "2-6-6"
    print(f"\nCurating {para} — HAZARDOUS INFLIGHT WEATHER ADVISORY")
    cards = [{'front': 'Within what distance must controllers advise pilots of hazardous weather?', 'back': 'Within 150 NM of their sector or area of jurisdiction.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Controllers must advise pilots of hazardous weather that may impact operations within _____ NM of their sector or area of jurisdiction.', "question_type": "fill_blank", "explanation": "Per 2-6-6: 150 NM is the mandatory advisory radius for hazardous weather impacting the controller's airspace.", "difficulty": 1, "choices": [{"choice_text": "150", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_7_1(db: sqlite3.Connection):
    """2-7-1 CURRENT SETTINGS"""
    para = "2-7-1"
    print(f"\nCurating {para} — CURRENT SETTINGS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Current altimeter settings must be obtained from _____-reading instruments or directly from weather reporting stations.', "question_type": "fill_blank", "explanation": 'Per 2-7-1(a): Only direct-reading instruments or official weather reporting stations provide valid altimeter settings.', "difficulty": 1, "choices": [{"choice_text": "direct", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_7_2(db: sqlite3.Connection):
    """2-7-2 ALTIMETER SETTING ISSUANCE BELOW LOWEST USABLE FL"""
    para = "2-7-2"
    print(f"\nCurating {para} — ALTIMETER SETTING ISSUANCE BELOW LOWEST USABLE FL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'EN ROUTE: Identify the _____ of all altimeter settings when issued.', "question_type": "fill_blank", "explanation": 'Per 2-7-2(b): En route controllers must always identify the source of altimeter settings. Terminal controllers must identify source for non-departure/destination airports.', "difficulty": 1, "choices": [{"choice_text": "source", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_7_3(db: sqlite3.Connection):
    """2-7-3 ALTIMETER SETTINGS GREATER THAN 31.00 INCHES MERCURY"""
    para = "2-7-3"
    print(f"\nCurating {para} — ALTIMETER SETTINGS GREATER THAN 31.00 INCHES MERCURY")
    cards = [{'front': 'What is the procedure when barometric pressure exceeds 31.00 inches of mercury?', 'back': 'Issue the altimeter setting and advise that high barometric pressure procedures are in effect. En Route/Arrivals: advise pilots to leave altimeter set to 31.00 until reaching the final approach fix.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'When barometric pressure is greater than _____ inches of mercury, issue the altimeter setting and advise that high barometric pressure procedures are in effect.', "question_type": "fill_blank", "explanation": 'Per 2-7-3: 31.00 inches of mercury is the threshold for high barometric pressure procedures.', "difficulty": 1, "choices": [{"choice_text": "31.00", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'During high barometric pressure procedures, advise pilots to leave altimeter set to 31.00 until reaching the _____ approach fix.', "question_type": "fill_blank", "explanation": 'Per 2-7-3(a): The altimeter remains at 31.00 until the final approach fix is reached.', "difficulty": 2, "choices": [{"choice_text": "final", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_8_1(db: sqlite3.Connection):
    """2-8-1 FURNISH RVR VALUES"""
    para = "2-8-1"
    print(f"\nCurating {para} — FURNISH RVR VALUES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Where RVR equipment is operational, furnish the values for the runway in use irrespective of subsequent operation or nonoperation of _____ or visual aids.', "question_type": "fill_blank", "explanation": 'Per 2-8-1: RVR values must be provided regardless of the status of navigational or visual aids.', "difficulty": 1, "choices": [{"choice_text": "navigational", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_8_2(db: sqlite3.Connection):
    """2-8-2 ARRIVAL/DEPARTURE RUNWAY VISIBILITY"""
    para = "2-8-2"
    print(f"\nCurating {para} — ARRIVAL/DEPARTURE RUNWAY VISIBILITY")
    cards = [{'front': 'When must touchdown RVR be issued?', 'back': '1. When prevailing visibility is 1 mile or less regardless of the RVR value.\n2. When RVR indicates a reportable value regardless of prevailing visibility.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Issue current touchdown RVR when prevailing visibility is _____ mile or less regardless of the value indicated.', "question_type": "fill_blank", "explanation": 'Per 2-8-2(a)(1): The 1-mile threshold is one of two triggers for mandatory RVR issuance.', "difficulty": 1, "choices": [{"choice_text": "1", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_8_3(db: sqlite3.Connection):
    """2-8-3 TERMINOLOGY"""
    para = "2-8-3"
    print(f"\nCurating {para} — TERMINOLOGY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Provide RVR information by stating the runway, the abbreviation _____, and the indicated value.', "question_type": "fill_blank", "explanation": "Per 2-8-3(a): The standard format is: runway, 'RVR', value.", "difficulty": 1, "choices": [{"choice_text": "RVR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_9_1(db: sqlite3.Connection):
    """2-9-1 APPLICATION"""
    para = "2-9-1"
    print(f"\nCurating {para} — APPLICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Identify each ATIS message by a _____ letter code word at both the beginning and the end of the message.', "question_type": "fill_blank", "explanation": 'Per 2-9-1(a): The phonetic letter code (Alpha, Bravo, etc.) must appear at the beginning AND end of every ATIS broadcast.', "difficulty": 1, "choices": [{"choice_text": "phonetic", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_9_2(db: sqlite3.Connection):
    """2-9-2 OPERATING PROCEDURES"""
    para = "2-9-2"
    print(f"\nCurating {para} — OPERATING PROCEDURES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Make a new ATIS recording upon receipt of _____ new official weather regardless of whether there is a change in values.', "question_type": "fill_blank", "explanation": 'Per 2-9-2(a)(1): ANY new official weather triggers a new ATIS recording — no change in values is still a trigger.', "difficulty": 2, "choices": [{"choice_text": "any", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_2_9_3(db: sqlite3.Connection):
    """2-9-3 CONTENT"""
    para = "2-9-3"
    print(f"\nCurating {para} — CONTENT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The ATIS broadcast includes the airport/facility name, phonetic letter code, time of the latest weather sequence in _____, and weather information.', "question_type": "fill_blank", "explanation": 'Per 2-9-3(a)(3): Weather sequence time is given in UTC (Coordinated Universal Time).', "difficulty": 1, "choices": [{"choice_text": "UTC", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()



def curate_3_1_1(db: sqlite3.Connection):
    """3-1-1 PROVIDE SERVICE"""
    para = "3-1-1"
    print(f"\nCurating {para} — PROVIDE SERVICE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Provide airport traffic control service based only upon _____ or known traffic and airport conditions.', "question_type": "fill_blank", "explanation": 'Per 3-1-1: Controllers must base service on observed or known conditions — not assumptions or hearsay.', "difficulty": 1, "choices": [{"choice_text": "observed", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_10(db: sqlite3.Connection):
    """3-1-10 ABNORMAL AIRCRAFT CONDITION"""
    para = "3-1-10"
    print(f"\nCurating {para} — ABNORMAL AIRCRAFT CONDITION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When requested by a pilot or when you deem it _____, inform an aircraft of any observed abnormal aircraft condition.', "question_type": "fill_blank", "explanation": 'Per 3-1-10: The controller has discretion to inform aircraft of abnormal conditions even without a pilot request.', "difficulty": 1, "choices": [{"choice_text": "necessary", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_11(db: sqlite3.Connection):
    """3-1-11 SURFACE AREA RESTRICTIONS"""
    para = "3-1-11"
    print(f"\nCurating {para} — SURFACE AREA RESTRICTIONS")
    cards = [{'front': 'What is the maximum speed a controller may approve in Class C or D airspace?', 'back': '250 knots (288 mph) unless the pilot informs you a higher minimum speed is required for their aircraft type.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Do not approve a speed in excess of _____ knots (288 mph) in Class C or D airspace unless the pilot informs you a higher minimum speed is required.', "question_type": "fill_blank", "explanation": 'Per 3-1-11(a): 250 knots is the hard speed limit for Class C/D surface areas.', "difficulty": 1, "choices": [{"choice_text": "250", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'A pilot may exceed 250 knots in Class D airspace if they inform the controller a higher minimum speed is required for their aircraft.', "question_type": "true_false", "explanation": 'Per 3-1-11(a): The 250-knot limit can be waived when the pilot states a higher minimum speed is required.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 1, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 0, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_12(db: sqlite3.Connection):
    """3-1-12 VISUALLY SCANNING RUNWAYS"""
    para = "3-1-12"
    print(f"\nCurating {para} — VISUALLY SCANNING RUNWAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Local controllers must visually scan runways to the _____ extent possible. Ground control must _____ local control in visually scanning runways.', "question_type": "fill_blank", "explanation": 'Per 3-1-12: Both local and ground controllers share responsibility for visually scanning runways to the maximum extent possible.', "difficulty": 1, "choices": [{"choice_text": "maximum", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_13(db: sqlite3.Connection):
    """3-1-13 CLASS D RADIO COMMUNICATIONS"""
    para = "3-1-13"
    print(f"\nCurating {para} — CLASS D RADIO COMMUNICATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "If the controller responds to a radio call with '(a/c call sign) _____', radio communications have been established and the pilot can enter Class D airspace.", "question_type": "fill_blank", "explanation": "Per 3-1-13: The word 'standby' alone is sufficient to establish two-way communications for Class D entry.", "difficulty": 2, "choices": [{"choice_text": "standby", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_14(db: sqlite3.Connection):
    """3-1-14 GROUND OPERATIONS WHEN VOLCANIC ASH IS PRESENT"""
    para = "3-1-14"
    print(f"\nCurating {para} — GROUND OPERATIONS WHEN VOLCANIC ASH IS PRESENT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When volcanic ash is present, avoid requiring aircraft to come to a full _____ while taxiing and provide for a _____ takeoff for all departures.', "question_type": "fill_blank", "explanation": 'Per 3-1-14: Rolling operations prevent ash ingestion — avoid full stops and use rolling takeoffs.', "difficulty": 1, "choices": [{"choice_text": "stop", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_15(db: sqlite3.Connection):
    """3-1-15 TARMAC DELAYS"""
    para = "3-1-15"
    print(f"\nCurating {para} — TARMAC DELAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When a pilot requests to return to the ramp due to the Three/Four-Hour _____ Rule, provide the requested services as soon as operationally practical.', "question_type": "fill_blank", "explanation": 'Per 3-1-15: The Three/Four-Hour Tarmac Rule gives pilots the right to request return to the gate after extended delays.', "difficulty": 2, "choices": [{"choice_text": "Tarmac", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_2(db: sqlite3.Connection):
    """3-1-2 PREVENTIVE CONTROL"""
    para = "3-1-2"
    print(f"\nCurating {para} — PREVENTIVE CONTROL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Provide preventive control service only to aircraft operating in accordance with a letter of _____.', "question_type": "fill_blank", "explanation": 'Per 3-1-2: Preventive control requires an LOA — it is not provided to aircraft generally.', "difficulty": 1, "choices": [{"choice_text": "agreement", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_3(db: sqlite3.Connection):
    """3-1-3 LOCAL CONTROLLER RESPONSIBILITY"""
    para = "3-1-3"
    print(f"\nCurating {para} — LOCAL CONTROLLER RESPONSIBILITY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The _____ controller has primary responsibility for operations conducted on the active runway.', "question_type": "fill_blank", "explanation": 'Per 3-1-3: Local control owns the active runway — this is a fundamental division of tower responsibilities.', "difficulty": 1, "choices": [{"choice_text": "local", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_4(db: sqlite3.Connection):
    """3-1-4 COORDINATION BETWEEN LOCAL AND GROUND CONTROLLERS"""
    para = "3-1-4"
    print(f"\nCurating {para} — COORDINATION BETWEEN LOCAL AND GROUND CONTROLLERS")
    cards = [{'front': 'What is the minimum information local and ground controllers must exchange?', 'back': 'Aircraft identification and the runway assignment.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'As a minimum, provide aircraft _____ and the runway assignment to the ground controller.', "question_type": "fill_blank", "explanation": 'Per 3-1-4: Aircraft identification and runway assignment are the minimum coordination items between local and ground.', "difficulty": 1, "choices": [{"choice_text": "identification", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_5(db: sqlite3.Connection):
    """3-1-5 VEHICLES ON RUNWAYS"""
    para = "3-1-5"
    print(f"\nCurating {para} — VEHICLES ON RUNWAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Vehicles with two-way radio communications may operate in the runway safety area up to the edge of the runway surface when authorized by an LOA, even when aircraft are arriving or departing.', "question_type": "true_false", "explanation": 'Per 3-1-5(a): LOA-authorized vehicles with two-way comms may operate in the RSA up to the runway edge, including during aircraft operations.', "difficulty": 3, "choices": [{'choice_text': 'True', 'is_correct': 1, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 0, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_6(db: sqlite3.Connection):
    """3-1-6 TRAFFIC INFORMATION"""
    para = "3-1-6"
    print(f"\nCurating {para} — TRAFFIC INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Describe vehicles, equipment, or personnel on or near the _____ area in a manner which will assist pilots in recognizing them.', "question_type": "fill_blank", "explanation": 'Per 3-1-6(a): Descriptions must help pilots recognize objects on or near the movement area.', "difficulty": 1, "choices": [{"choice_text": "movement", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_7(db: sqlite3.Connection):
    """3-1-7 POSITION DETERMINATION"""
    para = "3-1-7"
    print(f"\nCurating {para} — POSITION DETERMINATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Determine the position of an aircraft, personnel or equipment _____ issuing taxi instructions, takeoff clearance, or authorizing movement onto the movement area.', "question_type": "fill_blank", "explanation": "Per 3-1-7: Position must be confirmed BEFORE issuing clearances — never assume an aircraft's location.", "difficulty": 1, "choices": [{"choice_text": "before", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_8(db: sqlite3.Connection):
    """3-1-8 LOW LEVEL WIND SHEAR/MICROBURST"""
    para = "3-1-8"
    print(f"\nCurating {para} — LOW LEVEL WIND SHEAR/MICROBURST")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When wind shear/microburst is reported by pilots, _____, or detected on LLWAS or TDWR, controllers must issue the alert to all arriving and departing aircraft.', "question_type": "fill_blank", "explanation": 'Per 3-1-8(a): ITWS (Integrated Terminal Weather System) is one of the detection sources that triggers mandatory wind shear alerts.', "difficulty": 2, "choices": [{"choice_text": "ITWS", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_1_9(db: sqlite3.Connection):
    """3-1-9 TOWER DISPLAY WORKSTATIONS"""
    para = "3-1-9"
    print(f"\nCurating {para} — TOWER DISPLAY WORKSTATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": '_____ tower display workstations must be used only as an aid to assist controllers in visually locating aircraft.', "question_type": "fill_blank", "explanation": 'Per 3-1-9(a): Uncertified tower displays are visual aids only — they cannot be used for radar services or traffic advisories.', "difficulty": 2, "choices": [{"choice_text": "Uncertified", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_1(db: sqlite3.Connection):
    """3-10-1 LANDING INFORMATION"""
    para = "3-10-1"
    print(f"\nCurating {para} — LANDING INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Landing information contained in the ATIS broadcast may be omitted if the pilot states the appropriate _____ code.', "question_type": "fill_blank", "explanation": 'Per 3-10-1: Same as departure — ATIS code acknowledgment waives repeating the information.', "difficulty": 1, "choices": [{"choice_text": "ATIS", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_10(db: sqlite3.Connection):
    """3-10-10 LOW APPROACH"""
    para = "3-10-10"
    print(f"\nCurating {para} — LOW APPROACH")
    cards = [{'front': 'What is the minimum altitude for a low approach?', 'back': 'No less than 500 feet above the airport, except over an aircraft holding in position or a departing aircraft.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'A low approach with an altitude restriction of no less than _____ feet above the airport may be authorized.', "question_type": "fill_blank", "explanation": 'Per 3-10-10: 500 feet AGL is the minimum for a low approach.', "difficulty": 1, "choices": [{"choice_text": "500", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_11(db: sqlite3.Connection):
    """3-10-11 CLOSED TRAFFIC"""
    para = "3-10-11"
    print(f"\nCurating {para} — CLOSED TRAFFIC")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Approve or disapprove pilot requests to remain in _____ traffic for successive operations subject to local traffic conditions.', "question_type": "fill_blank", "explanation": "Per 3-10-11: 'Closed traffic' refers to aircraft staying in the pattern for repeated operations.", "difficulty": 1, "choices": [{"choice_text": "closed", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_12(db: sqlite3.Connection):
    """3-10-12 OVERHEAD MANEUVER"""
    para = "3-10-12"
    print(f"\nCurating {para} — OVERHEAD MANEUVER")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue pattern _____ and direction of traffic to arriving aircraft conducting an overhead maneuver.', "question_type": "fill_blank", "explanation": 'Per 3-10-12(a): Pattern altitude and traffic direction are the key elements for overhead maneuver arrivals.', "difficulty": 2, "choices": [{"choice_text": "altitude", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_13(db: sqlite3.Connection):
    """3-10-13 SFO/ELP OPERATIONS"""
    para = "3-10-13"
    print(f"\nCurating {para} — SFO/ELP OPERATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Authorize military aircraft to make SFO/ELP/practice precautionary approaches only if a letter of _____ is in place.', "question_type": "fill_blank", "explanation": 'Per 3-10-13(a)(1): An LOA is required for SFO/ELP/practice precautionary approach authorization.', "difficulty": 2, "choices": [{"choice_text": "agreement", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_2(db: sqlite3.Connection):
    """3-10-2 FORWARDING APPROACH INFORMATION BY NONAPPROACH CONTROL"""
    para = "3-10-2"
    print(f"\nCurating {para} — FORWARDING APPROACH INFORMATION BY NONAPPROACH CONTROL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward approach information to the control facility having _____ jurisdiction in your area.', "question_type": "fill_blank", "explanation": 'Per 3-10-2(a): Non-approach facilities must forward information to the IFR-controlling facility.', "difficulty": 2, "choices": [{"choice_text": "IFR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_3(db: sqlite3.Connection):
    """3-10-3 SAME RUNWAY SEPARATION — ARRIVALS"""
    para = "3-10-3"
    print(f"\nCurating {para} — SAME RUNWAY SEPARATION — ARRIVALS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate an arriving aircraft from another aircraft using the same runway by ensuring it does not cross the landing _____ until separation conditions exist.', "question_type": "fill_blank", "explanation": 'Per 3-10-3(a): The landing threshold is the control point for same-runway arrival separation.', "difficulty": 2, "choices": [{"choice_text": "threshold", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_4(db: sqlite3.Connection):
    """3-10-4 INTERSECTING RUNWAY ARRIVALS"""
    para = "3-10-4"
    print(f"\nCurating {para} — INTERSECTING RUNWAY ARRIVALS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue _____ information to each aircraft operating on intersecting runways.', "question_type": "fill_blank", "explanation": 'Per 3-10-4: Traffic advisories on intersecting runways apply to both departures AND arrivals.', "difficulty": 1, "choices": [{"choice_text": "traffic", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_5(db: sqlite3.Connection):
    """3-10-5 LANDING CLEARANCE PHRASEOLOGY"""
    para = "3-10-5"
    print(f"\nCurating {para} — LANDING CLEARANCE PHRASEOLOGY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When issuing a clearance to land, first state the _____ number followed by the landing clearance.', "question_type": "fill_blank", "explanation": 'Per 3-10-5(a): Same format as takeoff — runway number first, then the clearance.', "difficulty": 1, "choices": [{"choice_text": "runway", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_6(db: sqlite3.Connection):
    """3-10-6 ANTICIPATING SEPARATION — LANDING"""
    para = "3-10-6"
    print(f"\nCurating {para} — ANTICIPATING SEPARATION — LANDING")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Landing clearance to succeeding aircraft need not be withheld if you observe positions and determine that prescribed runway separation _____ exist when the aircraft crosses the threshold.', "question_type": "fill_blank", "explanation": 'Per 3-10-6(a): Similar to departure anticipation — reasonable assurance of future separation is sufficient.', "difficulty": 2, "choices": [{"choice_text": "will", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_7(db: sqlite3.Connection):
    """3-10-7 AIRCRAFT NOT IN SIGHT"""
    para = "3-10-7"
    print(f"\nCurating {para} — AIRCRAFT NOT IN SIGHT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When an arriving aircraft reports where it should be seen but has not been visually observed, advise the aircraft as part of the landing clearance that it is _____ in sight.', "question_type": "fill_blank", "explanation": 'Per 3-10-7: If the controller cannot see the aircraft, this must be communicated to the pilot.', "difficulty": 2, "choices": [{"choice_text": "not", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_8(db: sqlite3.Connection):
    """3-10-8 WITHHOLDING LANDING CLEARANCE"""
    para = "3-10-8"
    print(f"\nCurating {para} — WITHHOLDING LANDING CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'A controller may withhold a landing clearance indefinitely if the pilot appears to have violated a Federal Aviation Regulation.', "question_type": "true_false", "explanation": 'Per 3-10-8: Do NOT withhold landing clearance indefinitely — the apparent violation might have a legitimate explanation. Issue the clearance and report the incident.', "difficulty": 3, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_10_9(db: sqlite3.Connection):
    """3-10-9 RUNWAY TURN-OFF"""
    para = "3-10-9"
    print(f"\nCurating {para} — RUNWAY TURN-OFF")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Instruct aircraft where to _____-off the runway after landing, when appropriate.', "question_type": "fill_blank", "explanation": 'Per 3-10-9(a): Turn-off instructions are issued when appropriate to manage runway occupancy.', "difficulty": 1, "choices": [{"choice_text": "turn", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_11_1(db: sqlite3.Connection):
    """3-11-1 HELICOPTER TAXI"""
    para = "3-11-1"
    print(f"\nCurating {para} — HELICOPTER TAXI")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When necessary for a wheeled helicopter to taxi on the surface, use the phraseology in paragraph _____, Taxi and Ground Movement Operations.', "question_type": "fill_blank", "explanation": 'Per 3-11-1: Helicopter taxi operations use the same phraseology as fixed-wing aircraft (3-7-2).', "difficulty": 2, "choices": [{"choice_text": "3-7-2", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_11_2(db: sqlite3.Connection):
    """3-11-2 HELICOPTER TAKEOFF CLEARANCE"""
    para = "3-11-2"
    print(f"\nCurating {para} — HELICOPTER TAKEOFF CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue takeoff clearances from movement areas other than _____ runways, with additional instructions as necessary.', "question_type": "fill_blank", "explanation": 'Per 3-11-2: Helicopters may take off from areas other than active runways.', "difficulty": 2, "choices": [{"choice_text": "active", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_11_3(db: sqlite3.Connection):
    """3-11-3 HELICOPTER DEPARTURE SEPARATION"""
    para = "3-11-3"
    print(f"\nCurating {para} — HELICOPTER DEPARTURE SEPARATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate a departing helicopter from other helicopters by ensuring it does not _____ until separation conditions exist.', "question_type": "fill_blank", "explanation": 'Per 3-11-3: The takeoff point is the control gate for helicopter departure separation.', "difficulty": 1, "choices": [{"choice_text": "takeoff", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_11_4(db: sqlite3.Connection):
    """3-11-4 HELICOPTER ARRIVAL SEPARATION"""
    para = "3-11-4"
    print(f"\nCurating {para} — HELICOPTER ARRIVAL SEPARATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate an arriving helicopter from other helicopters by ensuring it does not _____ until the preceding helicopter has come to a stop or taxied off.', "question_type": "fill_blank", "explanation": 'Per 3-11-4(a): Landing clearance depends on the preceding helicopter clearing the landing area.', "difficulty": 1, "choices": [{"choice_text": "land", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_11_5(db: sqlite3.Connection):
    """3-11-5 SIMULTANEOUS LANDINGS OR TAKEOFFS"""
    para = "3-11-5"
    print(f"\nCurating {para} — SIMULTANEOUS LANDINGS OR TAKEOFFS")
    cards = [{'front': 'What is the minimum distance between helicopter landing/takeoff points for simultaneous operations?', 'back': 'At least 200 feet, and the courses to be flown must not conflict.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Authorize simultaneous helicopter landings or takeoffs if the distance between points is at least _____ feet and courses do not conflict.', "question_type": "fill_blank", "explanation": 'Per 3-11-5: 200 feet is the minimum separation distance between simultaneous helicopter operating points.', "difficulty": 2, "choices": [{"choice_text": "200", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_11_6(db: sqlite3.Connection):
    """3-11-6 HELICOPTER LANDING CLEARANCE"""
    para = "3-11-6"
    print(f"\nCurating {para} — HELICOPTER LANDING CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue landing clearances to helicopters going to movement areas other than active runways, with _____ instructions as necessary.', "question_type": "fill_blank", "explanation": 'Per 3-11-6(a): Additional instructions ensure safe helicopter operations to non-runway landing areas.', "difficulty": 1, "choices": [{"choice_text": "additional", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_12_1(db: sqlite3.Connection):
    """3-12-1 SEA LANES — APPLICATION"""
    para = "3-12-1"
    print(f"\nCurating {para} — SEA LANES — APPLICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Where _____ lanes are established and controlled, apply the provisions of this section.', "question_type": "fill_blank", "explanation": 'Per 3-12-1: Section 3-12 applies specifically to controlled sea lane operations.', "difficulty": 1, "choices": [{"choice_text": "sea", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_12_2(db: sqlite3.Connection):
    """3-12-2 SEA LANE DEPARTURE SEPARATION"""
    para = "3-12-2"
    print(f"\nCurating {para} — SEA LANE DEPARTURE SEPARATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate a departing aircraft from a preceding aircraft using the same sea lane by ensuring it does not commence takeoff until the other aircraft has _____ and crossed the end of the sea lane.', "question_type": "fill_blank", "explanation": 'Per 3-12-2(a): The preceding aircraft must have departed AND crossed the end of the sea lane before the next departure begins takeoff.', "difficulty": 2, "choices": [{"choice_text": "departed", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_12_3(db: sqlite3.Connection):
    """3-12-3 SEA LANE ARRIVAL SEPARATION"""
    para = "3-12-3"
    print(f"\nCurating {para} — SEA LANE ARRIVAL SEPARATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate an arriving aircraft from another aircraft using the same sea lane by ensuring it does not cross the landing _____ until separation conditions exist.', "question_type": "fill_blank", "explanation": 'Per 3-12-3: Sea lane arrival separation mirrors runway separation — the threshold is the control point.', "difficulty": 2, "choices": [{"choice_text": "threshold", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_2_1(db: sqlite3.Connection):
    """3-2-1 LIGHT SIGNALS"""
    para = "3-2-1"
    print(f"\nCurating {para} — LIGHT SIGNALS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use ATC light signals from TBL 3-2-1 to control aircraft and movement of vehicles on the movement area when _____ communications cannot be employed.', "question_type": "fill_blank", "explanation": 'Per 3-2-1: Light signals are the backup when radio communications are not available.', "difficulty": 1, "choices": [{"choice_text": "radio", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_2_2(db: sqlite3.Connection):
    """3-2-2 WARNING SIGNAL"""
    para = "3-2-2"
    print(f"\nCurating {para} — WARNING SIGNAL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Direct a general warning signal, alternating _____ and green, to aircraft or vehicle operators as appropriate.', "question_type": "fill_blank", "explanation": 'Per 3-2-2: The alternating red and green light is the standard warning signal for aircraft and vehicles.', "difficulty": 1, "choices": [{"choice_text": "red", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_2_3(db: sqlite3.Connection):
    """3-2-3 RECEIVER-ONLY ACKNOWLEDGMENT"""
    para = "3-2-3"
    print(f"\nCurating {para} — RECEIVER-ONLY ACKNOWLEDGMENT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'To obtain acknowledgment from a receiver-only aircraft between sunrise and sunset, request the aircraft to move _____.', "question_type": "fill_blank", "explanation": 'Per 3-2-3(a)(1)(a): Fixed-wing receiver-only aircraft acknowledge by moving ailerons during daylight hours.', "difficulty": 2, "choices": [{"choice_text": "ailerons", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_1(db: sqlite3.Connection):
    """3-3-1 LANDING AREA CONDITION"""
    para = "3-3-1"
    print(f"\nCurating {para} — LANDING AREA CONDITION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'If you observe or are _____ of any condition which affects the safe use of a landing area, take appropriate action.', "question_type": "fill_blank", "explanation": 'Per 3-3-1: The controller must act on both observed conditions AND reported/informed conditions affecting landing area safety.', "difficulty": 1, "choices": [{"choice_text": "informed", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_2(db: sqlite3.Connection):
    """3-3-2 CLOSED/UNSAFE RUNWAY"""
    para = "3-3-2"
    print(f"\nCurating {para} — CLOSED/UNSAFE RUNWAY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'If a pilot persists in requesting to land on a closed runway, the controller should issue a landing clearance since the pilot has the final authority.', "question_type": "true_false", "explanation": 'Per 3-3-2: Inform the pilot the runway is closed or unsafe. If the pilot persists, quote the pilot the runway condition information — do NOT issue a landing clearance.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_3(db: sqlite3.Connection):
    """3-3-3 AIRPORT CONDITION INFORMATION"""
    para = "3-3-3"
    print(f"\nCurating {para} — AIRPORT CONDITION INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Issue airport condition information necessary for an aircraft's safe operation in time for it to be _____ to the pilot.", "question_type": "fill_blank", "explanation": 'Per 3-3-3: Timing matters — information must arrive in time to be useful for pilot decision-making.', "difficulty": 1, "choices": [{"choice_text": "useful", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_4(db: sqlite3.Connection):
    """3-3-4 BRAKING ACTION"""
    para = "3-3-4"
    print(f"\nCurating {para} — BRAKING ACTION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Describe the quality of braking action using terms 'good,' 'good to medium,' '_____', 'medium to poor,' 'poor,' or 'nil.'", "question_type": "fill_blank", "explanation": "Per 3-3-4(a): The standardized braking action scale ranges from 'good' to 'nil' with specific intermediate terms.", "difficulty": 1, "choices": [{"choice_text": "medium", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_5(db: sqlite3.Connection):
    """3-3-5 RUNWAY CONDITION REPORTS"""
    para = "3-3-5"
    print(f"\nCurating {para} — RUNWAY CONDITION REPORTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "When runway braking action reports include '_____', 'poor,' or 'nil,' special handling and notification procedures apply.", "question_type": "fill_blank", "explanation": 'Per 3-3-5(a): Reports of medium, poor, or nil braking action trigger additional procedures.', "difficulty": 2, "choices": [{"choice_text": "medium", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_6(db: sqlite3.Connection):
    """3-3-6 ARRESTING SYSTEMS"""
    para = "3-3-6"
    print(f"\nCurating {para} — ARRESTING SYSTEMS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'For normal operations, arresting systems remotely controlled by ATC must remain in the _____ or down position.', "question_type": "fill_blank", "explanation": 'Per 3-3-6(a): Arresting systems stay retracted/down during normal ops — they are only raised when needed.', "difficulty": 1, "choices": [{"choice_text": "retracted", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_3_7(db: sqlite3.Connection):
    """3-3-7 CAT III WEATHER"""
    para = "3-3-7"
    print(f"\nCurating {para} — CAT III WEATHER")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Type II equipment being upgraded to Integrity Level _____ will support operations under CAT III weather conditions.', "question_type": "fill_blank", "explanation": 'Per 3-3-7(a): Integrity Level 3 supports CAT III operations.', "difficulty": 3, "choices": [{"choice_text": "3", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_1(db: sqlite3.Connection):
    """3-4-1 EMERGENCY LIGHTING"""
    para = "3-4-1"
    print(f"\nCurating {para} — EMERGENCY LIGHTING")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Whenever you become aware that an _____ has or will occur, take action to provide for the operation of all appropriate airport lighting aids.', "question_type": "fill_blank", "explanation": 'Per 3-4-1: Emergency conditions trigger mandatory activation of all appropriate lighting aids.', "difficulty": 1, "choices": [{"choice_text": "emergency", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_10(db: sqlite3.Connection):
    """3-4-10 RUNWAY EDGE LIGHTS"""
    para = "3-4-10"
    print(f"\nCurating {para} — RUNWAY EDGE LIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate the runway _____ light system serving the runway/s in use.', "question_type": "fill_blank", "explanation": 'Per 3-4-10: Runway edge lights must be operated for the active runway.', "difficulty": 1, "choices": [{"choice_text": "edge", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_11(db: sqlite3.Connection):
    """3-4-11 HIGH INTENSITY RUNWAY LIGHTS"""
    para = "3-4-11"
    print(f"\nCurating {para} — HIGH INTENSITY RUNWAY LIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate high intensity runway, runway centerline, and _____ zone lights in accordance with TBL 3-4-8.', "question_type": "fill_blank", "explanation": 'Per 3-4-11: HIRL, centerline, and touchdown zone lights are governed by TBL 3-4-8.', "difficulty": 1, "choices": [{"choice_text": "touchdown", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_12(db: sqlite3.Connection):
    """3-4-12 HIRL ASSOCIATED WITH MALSR"""
    para = "3-4-12"
    print(f"\nCurating {para} — HIRL ASSOCIATED WITH MALSR")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate HIRL which control the associated MALSR in accordance with TBL _____.', "question_type": "fill_blank", "explanation": 'Per 3-4-12: TBL 3-4-9 governs HIRL/MALSR combined operation.', "difficulty": 2, "choices": [{"choice_text": "3-4-9", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_13(db: sqlite3.Connection):
    """3-4-13 HIRL CHANGES AFFECTING RVR"""
    para = "3-4-13"
    print(f"\nCurating {para} — HIRL CHANGES AFFECTING RVR")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Keep the appropriate _____ controller or PAR controller informed, in advance if possible, of HIRL changes that affect RVR.', "question_type": "fill_blank", "explanation": 'Per 3-4-13: Approach/PAR controllers must be notified of HIRL changes that impact RVR readings.', "difficulty": 2, "choices": [{"choice_text": "approach", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_14(db: sqlite3.Connection):
    """3-4-14 MEDIUM INTENSITY RUNWAY LIGHTS (MIRL)"""
    para = "3-4-14"
    print(f"\nCurating {para} — MEDIUM INTENSITY RUNWAY LIGHTS (MIRL)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate MIRL in accordance with TBL _____.', "question_type": "fill_blank", "explanation": 'Per 3-4-14: TBL 3-4-10 governs MIRL operation.', "difficulty": 2, "choices": [{"choice_text": "3-4-10", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_15(db: sqlite3.Connection):
    """3-4-15 HIGH SPEED TURNOFF LIGHTS"""
    para = "3-4-15"
    print(f"\nCurating {para} — HIGH SPEED TURNOFF LIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Leave high speed turnoff lights on until the aircraft has either entered a _____ or passed the last light.', "question_type": "fill_blank", "explanation": 'Per 3-4-15(a): Turnoff lights stay on until the aircraft has exited the runway onto a taxiway or passed all lights.', "difficulty": 1, "choices": [{"choice_text": "taxiway", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_16(db: sqlite3.Connection):
    """3-4-16 TAXIWAY LIGHTS"""
    para = "3-4-16"
    print(f"\nCurating {para} — TAXIWAY LIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate taxiway lights in accordance with TBL 3-4-11, TBL 3-4-12, or TBL _____.', "question_type": "fill_blank", "explanation": 'Per 3-4-16: Three tables govern taxiway light operation.', "difficulty": 2, "choices": [{"choice_text": "3-4-13", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_17(db: sqlite3.Connection):
    """3-4-17 OBSTRUCTION LIGHTS"""
    para = "3-4-17"
    print(f"\nCurating {para} — OBSTRUCTION LIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'If controls are provided, turn obstruction lights on between _____ and sunrise.', "question_type": "fill_blank", "explanation": 'Per 3-4-17: Obstruction lights follow the sunset-to-sunrise schedule when controllable.', "difficulty": 1, "choices": [{"choice_text": "sunset", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_18(db: sqlite3.Connection):
    """3-4-18 ROTATING BEACON"""
    para = "3-4-18"
    print(f"\nCurating {para} — ROTATING BEACON")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The rotating beacon should only be operated between sunset and sunrise.', "question_type": "true_false", "explanation": 'Per 3-4-18: The rotating beacon is also operated between sunrise and sunset when the reported ceiling or visibility is below basic VFR minima.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_19(db: sqlite3.Connection):
    """3-4-19 TERMINAL LIGHTING"""
    para = "3-4-19"
    print(f"\nCurating {para} — TERMINAL LIGHTING")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Chapter 3, Section 4 covers airport _____ — the most lighting-intensive section of the 7110.65.', "question_type": "fill_blank", "explanation": 'Per 3-4: Section 4 is dedicated entirely to airport lighting systems and their operation.', "difficulty": 1, "choices": [{"choice_text": "lighting", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_2(db: sqlite3.Connection):
    """3-4-2 RUNWAY END IDENTIFIER LIGHTS (REIL)"""
    para = "3-4-2"
    print(f"\nCurating {para} — RUNWAY END IDENTIFIER LIGHTS (REIL)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Turn the REIL off after an arriving aircraft has _____.', "question_type": "fill_blank", "explanation": 'Per 3-4-2(a)(1): REIL are turned off once the arriving aircraft has landed — not before.', "difficulty": 1, "choices": [{"choice_text": "landed", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_3(db: sqlite3.Connection):
    """3-4-3 VISUAL APPROACH SLOPE INDICATORS (VASI)"""
    para = "3-4-3"
    print(f"\nCurating {para} — VISUAL APPROACH SLOPE INDICATORS (VASI)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'VASI systems with remote on-off switching must be operated when they serve the runway _____ use.', "question_type": "fill_blank", "explanation": 'Per 3-4-3: VASI is operated for the active runway in use.', "difficulty": 1, "choices": [{"choice_text": "in", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_4(db: sqlite3.Connection):
    """3-4-4 PRECISION APPROACH PATH INDICATORS (PAPI)"""
    para = "3-4-4"
    print(f"\nCurating {para} — PRECISION APPROACH PATH INDICATORS (PAPI)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'PAPI systems with remote on-off switching must be operated when they serve the runway in use and intensities are controlled per TBL _____.', "question_type": "fill_blank", "explanation": 'Per 3-4-4: PAPI intensity settings are governed by TBL 3-4-4.', "difficulty": 2, "choices": [{"choice_text": "3-4-4", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_5(db: sqlite3.Connection):
    """3-4-5 APPROACH LIGHTS"""
    para = "3-4-5"
    print(f"\nCurating {para} — APPROACH LIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate approach lights between _____ and sunrise when they serve the landing runway or a runway to which an approach is being made.', "question_type": "fill_blank", "explanation": 'Per 3-4-5(a): Sunset to sunrise is the standard operating window for approach lights serving the landing runway.', "difficulty": 1, "choices": [{"choice_text": "sunset", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_6(db: sqlite3.Connection):
    """3-4-6 APPROACH LIGHT INTENSITY"""
    para = "3-4-6"
    print(f"\nCurating {para} — APPROACH LIGHT INTENSITY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate ALS intensity controls in accordance with TBL _____ except when facility directives specify other settings.', "question_type": "fill_blank", "explanation": 'Per 3-4-6: TBL 3-4-5 governs ALS intensity, subject to local facility directive exceptions.', "difficulty": 2, "choices": [{"choice_text": "3-4-5", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_7(db: sqlite3.Connection):
    """3-4-7 SEQUENCED FLASHING LIGHTS (SFL)"""
    para = "3-4-7"
    print(f"\nCurating {para} — SEQUENCED FLASHING LIGHTS (SFL)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate Sequenced Flashing Lights whenever the associated _____ lights are operated.', "question_type": "fill_blank", "explanation": 'Per 3-4-7: SFL are tied to approach light operation — they operate together.', "difficulty": 1, "choices": [{"choice_text": "approach", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_8(db: sqlite3.Connection):
    """3-4-8 MALSR/ODALS"""
    para = "3-4-8"
    print(f"\nCurating {para} — MALSR/ODALS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Operate MALSR/ODALS in accordance with TBL _____ and TBL 3-4-7.', "question_type": "fill_blank", "explanation": 'Per 3-4-8: TBL 3-4-6 and TBL 3-4-7 govern MALSR/ODALS settings.', "difficulty": 2, "choices": [{"choice_text": "3-4-6", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_4_9(db: sqlite3.Connection):
    """3-4-9 ALSF-2/SSALR"""
    para = "3-4-9"
    print(f"\nCurating {para} — ALSF-2/SSALR")
    cards = [{'front': 'When must the ALSF-2 system be operated?', 'back': 'When prevailing visibility is 3/4 mile or less or the RVR is 4,000 feet or less. Also as requested by the pilot or as the controller deems necessary.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'When the prevailing visibility is _____ mile or less or the RVR is 4,000 feet or less, operate the ALSF-2 system.', "question_type": "fill_blank", "explanation": 'Per 3-4-9(a): Two triggers for ALSF-2 operation: visibility ≤ 3/4 mile OR RVR ≤ 4,000 feet.', "difficulty": 2, "choices": [{"choice_text": "3/4", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'Operate ALSF-2 when RVR is _____ feet or less.', "question_type": "fill_blank", "explanation": 'Per 3-4-9(a): The RVR threshold for ALSF-2 operation is 4,000 feet.', "difficulty": 2, "choices": [{"choice_text": "4000", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_5_1(db: sqlite3.Connection):
    """3-5-1 RUNWAY SELECTION"""
    para = "3-5-1"
    print(f"\nCurating {para} — RUNWAY SELECTION")
    cards = [{'front': 'What wind condition triggers runway designation in the tower?', 'back': 'Assign the runway most nearly aligned with the wind when the wind is 5 knots or more.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Assign the runway most nearly aligned with the wind when the wind is _____ knots or more.', "question_type": "fill_blank", "explanation": 'Per 3-5-1(b): 5 knots is the threshold — below this, runway assignment is less wind-dependent.', "difficulty": 1, "choices": [{"choice_text": "5", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_5_2(db: sqlite3.Connection):
    """3-5-2 STOL RUNWAYS"""
    para = "3-5-2"
    print(f"\nCurating {para} — STOL RUNWAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'A designated STOL runway may be assigned only when requested by the pilot or as specified in a letter of _____.', "question_type": "fill_blank", "explanation": 'Per 3-5-2(a): STOL runways require either pilot request or LOA authorization — they are not assigned routinely.', "difficulty": 2, "choices": [{"choice_text": "agreement", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_5_3(db: sqlite3.Connection):
    """3-5-3 TAILWIND COMPONENTS"""
    para = "3-5-3"
    print(f"\nCurating {para} — TAILWIND COMPONENTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When authorizing use of runways and a tailwind component exists, always state both wind _____ and _____.', "question_type": "fill_blank", "explanation": 'Per 3-5-3: Both direction and velocity must be stated when a tailwind exists — pilots need full wind picture for tailwind operations.', "difficulty": 1, "choices": [{"choice_text": "direction", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_6_1(db: sqlite3.Connection):
    """3-6-1 EQUIPMENT USAGE"""
    para = "3-6-1"
    print(f"\nCurating {para} — EQUIPMENT USAGE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The operational status of _____ systems must be determined during the relief briefing or as soon as possible after assuming the position.', "question_type": "fill_blank", "explanation": 'Per 3-6-1(a): ASDE (Airport Surface Detection Equipment) status must be confirmed at position assumption.', "difficulty": 2, "choices": [{"choice_text": "ASDE", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_6_2(db: sqlite3.Connection):
    """3-6-2 ASDE TARGET IDENTIFICATION"""
    para = "3-6-2"
    print(f"\nCurating {para} — ASDE TARGET IDENTIFICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'To identify an observed target on an ASDE display, _____ its position with one or more sources including pilot position reports and visual observation.', "question_type": "fill_blank", "explanation": 'Per 3-6-2(a): Correlation of multiple position sources is required for positive ASDE target identification.', "difficulty": 2, "choices": [{"choice_text": "correlate", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_6_3(db: sqlite3.Connection):
    """3-6-3 ASDE APPLICATIONS"""
    para = "3-6-3"
    print(f"\nCurating {para} — ASDE APPLICATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'ASDE system derived information may be used to _____ clearances and control instructions to aircraft and vehicles on the movement area.', "question_type": "fill_blank", "explanation": "Per 3-6-3(a)(1): ASDE data can be used to formulate clearances — it's an operational tool, not just a situational awareness aid.", "difficulty": 2, "choices": [{"choice_text": "formulate", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_6_4(db: sqlite3.Connection):
    """3-6-4 SAFETY LOGIC ALERT RESPONSES"""
    para = "3-6-4"
    print(f"\nCurating {para} — SAFETY LOGIC ALERT RESPONSES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When the system generates an alert, the controller must _____ assess the situation visually and as presented on the ASDE display.', "question_type": "fill_blank", "explanation": 'Per 3-6-4: Immediate assessment is required — alerts cannot be ignored or deferred.', "difficulty": 2, "choices": [{"choice_text": "immediately", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_7_1(db: sqlite3.Connection):
    """3-7-1 GROUND TRAFFIC MOVEMENT"""
    para = "3-7-1"
    print(f"\nCurating {para} — GROUND TRAFFIC MOVEMENT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue by radio or _____ light signals specific instructions which approve or disapprove the movement of aircraft or vehicles on the movement area.', "question_type": "fill_blank", "explanation": 'Per 3-7-1: Directional light signals are the backup for radio-issued movement instructions.', "difficulty": 1, "choices": [{"choice_text": "directional", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_7_2(db: sqlite3.Connection):
    """3-7-2 TAXI ROUTE ISSUANCE"""
    para = "3-7-2"
    print(f"\nCurating {para} — TAXI ROUTE ISSUANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The taxi clearance must include the _____ route to follow.', "question_type": "fill_blank", "explanation": "Per 3-7-2: Taxi clearances require a specific route — vague instructions like 'taxi to the ramp' are insufficient.", "difficulty": 2, "choices": [{"choice_text": "specific", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_7_3(db: sqlite3.Connection):
    """3-7-3 GROUND OPERATIONS"""
    para = "3-7-3"
    print(f"\nCurating {para} — GROUND OPERATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Controllers should avoid clearances that require super or heavy aircraft to use greater than normal taxiing power.', "question_type": "true_false", "explanation": 'Per 3-7-3(a): Heavy/super aircraft should not be forced to use excessive power during taxi — it can cause jet blast damage.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 1, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 0, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_7_4(db: sqlite3.Connection):
    """3-7-4 HOLDING AIRCRAFT"""
    para = "3-7-4"
    print(f"\nCurating {para} — HOLDING AIRCRAFT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Instruct aircraft or vehicle to hold _____ of a specific runway.', "question_type": "fill_blank", "explanation": "Per 3-7-4(a): 'Hold short' is the standard phraseology for keeping aircraft/vehicles clear of an active runway.", "difficulty": 1, "choices": [{"choice_text": "short", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_7_5(db: sqlite3.Connection):
    """3-7-5 ILS CRITICAL AREA"""
    para = "3-7-5"
    print(f"\nCurating {para} — ILS CRITICAL AREA")
    cards = [{'front': 'When must aircraft/vehicle access to the ILS critical area be controlled?', 'back': 'When the official weather observation is a ceiling of less than 800 feet or visibility is less than 2 miles.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Aircraft access to the ILS critical area must be controlled when the ceiling is less than _____ feet or visibility is less than 2 miles.', "question_type": "fill_blank", "explanation": 'Per 3-7-5(a): 800-foot ceiling OR 2-mile visibility is the trigger for ILS critical area protection.', "difficulty": 2, "choices": [{"choice_text": "800", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_7_6(db: sqlite3.Connection):
    """3-7-6 PRECISION OBSTACLE FREE ZONE (POFZ)"""
    para = "3-7-6"
    print(f"\nCurating {para} — PRECISION OBSTACLE FREE ZONE (POFZ)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Ensure the POFZ is clear of traffic when an aircraft on a vertically-guided final approach is within _____ miles of the runway threshold.', "question_type": "fill_blank", "explanation": 'Per 3-7-6(a): 2 miles from the threshold is the POFZ protection zone for vertically-guided approaches.', "difficulty": 2, "choices": [{"choice_text": "2", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_8_1(db: sqlite3.Connection):
    """3-8-1 SEQUENCE/SPACING APPLICATION"""
    para = "3-8-1"
    print(f"\nCurating {para} — SEQUENCE/SPACING APPLICATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Establish the sequence of arriving and departing aircraft by requiring them to _____ flight or ground operation as necessary to achieve proper spacing.', "question_type": "fill_blank", "explanation": "Per 3-8-1: Controllers actively manage sequence by requiring aircraft to adjust — it's not passive.", "difficulty": 1, "choices": [{"choice_text": "adjust", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_8_2(db: sqlite3.Connection):
    """3-8-2 TOUCH-AND-GO OR STOP-AND-GO OR LOW APPROACH"""
    para = "3-8-2"
    print(f"\nCurating {para} — TOUCH-AND-GO OR STOP-AND-GO OR LOW APPROACH")
    cards = [{'front': 'How is an aircraft conducting a touch-and-go classified?', 'back': 'As an arriving aircraft until it touches down. For stop-and-go: until complete stop. For low approach: until it crosses the landing threshold.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Consider an aircraft cleared for touch-and-go as an _____ aircraft until it touches down.', "question_type": "fill_blank", "explanation": 'Per 3-8-2: Touch-and-go aircraft are treated as arrivals until touchdown — then they transition to departure status.', "difficulty": 2, "choices": [{"choice_text": "arriving", "is_correct": 1, "sort_order": 0}]},
        {"question_text": "When does a stop-and-go aircraft transition from 'arriving' to 'departing' status?", "question_type": "multiple_choice", "explanation": 'Per 3-8-2: A stop-and-go aircraft is an arrival until it makes a complete stop, at which point it transitions to departure status.', "difficulty": 3, "choices": [{'choice_text': 'When the aircraft crosses the landing threshold.', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'When the aircraft makes a complete stop.', 'is_correct': 1, 'sort_order': 1}, {'choice_text': 'When the pilot reports ready for departure.', 'is_correct': 0, 'sort_order': 2}, {'choice_text': 'When the controller issues a takeoff clearance.', 'is_correct': 0, 'sort_order': 3}]},
        {"question_text": 'A low approach aircraft is considered an arriving aircraft until it crosses the landing threshold.', "question_type": "true_false", "explanation": 'Per 3-8-2: The landing threshold crossing is the transition point for low approach aircraft.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 1, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 0, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_8_3(db: sqlite3.Connection):
    """3-8-3 SIMULTANEOUS SAME DIRECTION OPERATIONS"""
    para = "3-8-3"
    print(f"\nCurating {para} — SIMULTANEOUS SAME DIRECTION OPERATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Authorize simultaneous, same direction operations on parallel runways only when operations are conducted in VFR conditions unless procedures have been approved for _____.', "question_type": "fill_blank", "explanation": 'Per 3-8-3: Same-direction parallel ops require VFR unless specifically approved for SVFR.', "difficulty": 3, "choices": [{"choice_text": "SVFR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_8_4(db: sqlite3.Connection):
    """3-8-4 SIMULTANEOUS OPPOSITE DIRECTION OPERATION"""
    para = "3-8-4"
    print(f"\nCurating {para} — SIMULTANEOUS OPPOSITE DIRECTION OPERATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Authorize simultaneous opposite direction operations on parallel runways only when the _____ are separated by at least 2,500 feet.', "question_type": "fill_blank", "explanation": 'Per 3-8-4: 2,500-foot centerline separation is the minimum for opposite-direction parallel operations.', "difficulty": 3, "choices": [{"choice_text": "centerlines", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_1(db: sqlite3.Connection):
    """3-9-1 DEPARTURE INFORMATION"""
    para = "3-9-1"
    print(f"\nCurating {para} — DEPARTURE INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Departure information contained in the _____ broadcast may be omitted if the pilot states the appropriate ATIS code.', "question_type": "fill_blank", "explanation": 'Per 3-9-1(a): ATIS code acknowledgment by the pilot relieves the controller of repeating ATIS departure information.', "difficulty": 1, "choices": [{"choice_text": "ATIS", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_10(db: sqlite3.Connection):
    """3-9-10 TAKEOFF CLEARANCE PHRASEOLOGY"""
    para = "3-9-10"
    print(f"\nCurating {para} — TAKEOFF CLEARANCE PHRASEOLOGY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When issuing a clearance for takeoff, first state the _____ number followed by the takeoff clearance.', "question_type": "fill_blank", "explanation": 'Per 3-9-10(a): Runway number precedes the takeoff clearance — always state the runway first.', "difficulty": 1, "choices": [{"choice_text": "runway", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_11(db: sqlite3.Connection):
    """3-9-11 CANCEL TAKEOFF CLEARANCE"""
    para = "3-9-11"
    print(f"\nCurating {para} — CANCEL TAKEOFF CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Once an aircraft has started takeoff roll, cancel the takeoff clearance only for the purpose of _____.', "question_type": "fill_blank", "explanation": 'Per 3-9-11: After takeoff roll begins, cancellation is for safety purposes only.', "difficulty": 2, "choices": [{"choice_text": "safety", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_2(db: sqlite3.Connection):
    """3-9-2 GATE-HOLD PROCEDURES"""
    para = "3-9-2"
    print(f"\nCurating {para} — GATE-HOLD PROCEDURES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When _____-hold procedures are in effect, issue departure delay information as appropriate.', "question_type": "fill_blank", "explanation": 'Per 3-9-2: Gate-hold procedures manage departure queues during delays.', "difficulty": 1, "choices": [{"choice_text": "gate", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_3(db: sqlite3.Connection):
    """3-9-3 PRE-DEPARTURE INFORMATION"""
    para = "3-9-3"
    print(f"\nCurating {para} — PRE-DEPARTURE INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Before takeoff, issue the appropriate _____ control frequency and beacon code to departing IFR aircraft.', "question_type": "fill_blank", "explanation": 'Per 3-9-3(a)(1): Departure frequency and beacon code must be issued before takeoff.', "difficulty": 1, "choices": [{"choice_text": "departure", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_4(db: sqlite3.Connection):
    """3-9-4 LINE UP AND WAIT (LUAW)"""
    para = "3-9-4"
    print(f"\nCurating {para} — LINE UP AND WAIT (LUAW)")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The intent of LUAW is to position aircraft for an _____ departure.', "question_type": "fill_blank", "explanation": 'Per 3-9-4(a): LUAW is for imminent departures — not for holding aircraft on the runway.', "difficulty": 2, "choices": [{"choice_text": "imminent", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_5(db: sqlite3.Connection):
    """3-9-5 ANTICIPATING SEPARATION"""
    para = "3-9-5"
    print(f"\nCurating {para} — ANTICIPATING SEPARATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Takeoff clearance need not be withheld until prescribed separation exists if there is _____ assurance it will exist when the aircraft starts takeoff roll.', "question_type": "fill_blank", "explanation": 'Per 3-9-5: The controller may issue takeoff clearance based on reasonable assurance of separation — the standard is not absolute certainty.', "difficulty": 2, "choices": [{"choice_text": "reasonable", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_6(db: sqlite3.Connection):
    """3-9-6 SAME RUNWAY SEPARATION"""
    para = "3-9-6"
    print(f"\nCurating {para} — SAME RUNWAY SEPARATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate a departing aircraft from a preceding aircraft using the same runway by ensuring it does not begin _____ roll until separation exists.', "question_type": "fill_blank", "explanation": 'Per 3-9-6: The takeoff roll start is the critical control point for same-runway departure separation.', "difficulty": 1, "choices": [{"choice_text": "takeoff", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_7(db: sqlite3.Connection):
    """3-9-7 INTERSECTION DEPARTURES"""
    para = "3-9-7"
    print(f"\nCurating {para} — INTERSECTION DEPARTURES")
    cards = [{'front': 'What is the weight threshold for small aircraft wake turbulence criteria at intersection departures?', 'back': 'Small aircraft weighing 12,500 lbs or less taking off from an intersection on the same runway.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Separate a small aircraft weighing _____ lbs or less taking off from an intersection behind a larger aircraft on the same runway.', "question_type": "fill_blank", "explanation": 'Per 3-9-7(a)(1): 12,500 lbs is the threshold for small aircraft intersection departure wake turbulence criteria.', "difficulty": 2, "choices": [{"choice_text": "12500", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_8(db: sqlite3.Connection):
    """3-9-8 INTERSECTING RUNWAY DEPARTURES"""
    para = "3-9-8"
    print(f"\nCurating {para} — INTERSECTING RUNWAY DEPARTURES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue _____ information to each aircraft operating on intersecting runways.', "question_type": "fill_blank", "explanation": 'Per 3-9-8(a): Traffic information must be issued to all aircraft on intersecting runways.', "difficulty": 1, "choices": [{"choice_text": "traffic", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_3_9_9(db: sqlite3.Connection):
    """3-9-9 NONINTERSECTING CONVERGING RUNWAY OPERATIONS"""
    para = "3-9-9"
    print(f"\nCurating {para} — NONINTERSECTING CONVERGING RUNWAY OPERATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate departing aircraft from an aircraft using a nonintersecting runway when the _____ paths intersect.', "question_type": "fill_blank", "explanation": 'Per 3-9-9(a): Nonintersecting runways still require separation if flight paths intersect.', "difficulty": 2, "choices": [{"choice_text": "flight", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()


def curate_4_1_1(db: sqlite3.Connection):
    """4-1-1 ALTITUDE AND DISTANCE LIMITATIONS"""
    para = "4-1-1"
    print(f"\nCurating {para} — ALTITUDE AND DISTANCE LIMITATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When specifying a route other than an established airway, do not exceed the limitations in TBL 4-1-1, TBL 4-1-2, and TBL _____ on any portion within controlled airspace.', "question_type": "fill_blank", "explanation": 'Per 4-1-1: Three tables govern altitude and distance limitations for non-airway routes.', "difficulty": 2, "choices": [{"choice_text": "4-1-3", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_1_2(db: sqlite3.Connection):
    """4-1-2 EXCEPTIONS"""
    para = "4-1-2"
    print(f"\nCurating {para} — EXCEPTIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Altitude and distance limitations need not be applied when routing is initiated by ATC or requested by the pilot and radar _____ is provided.', "question_type": "fill_blank", "explanation": 'Per 4-1-2(a): Radar monitoring is the key condition that waives altitude/distance limitations.', "difficulty": 2, "choices": [{"choice_text": "monitoring", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_1_3(db: sqlite3.Connection):
    """4-1-3 CROSSING ALTITUDE"""
    para = "4-1-3"
    print(f"\nCurating {para} — CROSSING ALTITUDE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Use an altitude consistent with the limitations of the _____ when clearing an aircraft to cross or hold at a fix.', "question_type": "fill_blank", "explanation": "Per 4-1-3: The navaid's service volume limitations determine crossing/holding altitude.", "difficulty": 1, "choices": [{"choice_text": "aid", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_1_4(db: sqlite3.Connection):
    """4-1-4 VFR-ON-TOP"""
    para = "4-1-4"
    print(f"\nCurating {para} — VFR-ON-TOP")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Use a route not meeting service volume limitations only if an aircraft requests to operate '_____-on-top' on this route.", "question_type": "fill_blank", "explanation": 'Per 4-1-4: VFR-on-top is the only condition under which a sub-service-volume route may be assigned.', "difficulty": 1, "choices": [{"choice_text": "VFR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_1_5(db: sqlite3.Connection):
    """4-1-5 FIX USE"""
    para = "4-1-5"
    print(f"\nCurating {para} — FIX USE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Request aircraft position reports only over fixes shown on _____ used for the altitude being flown.', "question_type": "fill_blank", "explanation": 'Per 4-1-5: Position reports are limited to charted fixes appropriate for the altitude flown.', "difficulty": 1, "choices": [{"choice_text": "charts", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_1(db: sqlite3.Connection):
    """4-2-1 CLEARANCE ITEMS"""
    para = "4-2-1"
    print(f"\nCurating {para} — CLEARANCE ITEMS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue clearance items in the order listed: aircraft identification, clearance _____, then route and altitude.', "question_type": "fill_blank", "explanation": 'Per 4-2-1(a-b): Clearance limit follows aircraft identification in the standard clearance format.', "difficulty": 1, "choices": [{"choice_text": "limit", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_10(db: sqlite3.Connection):
    """4-2-10 CANCELLATION OF IFR FLIGHT PLAN"""
    para = "4-2-10"
    print(f"\nCurating {para} — CANCELLATION OF IFR FLIGHT PLAN")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Before instructing an IFR aircraft arriving at an airport not served by a tower to change to the _____ traffic advisory frequency, provide instructions on how to cancel the IFR flight plan.', "question_type": "fill_blank", "explanation": 'Per 4-2-10(a): CTAF (Common Traffic Advisory Frequency) instructions must include IFR cancellation guidance.', "difficulty": 2, "choices": [{"choice_text": "common", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_2(db: sqlite3.Connection):
    """4-2-2 CLEARANCE PREFIX"""
    para = "4-2-2"
    print(f"\nCurating {para} — CLEARANCE PREFIX")
    cards = [{'front': 'What prefix is used when relaying a clearance through a non-ATC facility?', 'back': "State 'A-T-C clears,' 'A-T-C advises,' or 'A-T-C requests' before the clearance, information, or request.", 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": "Prefix a clearance relayed through a non-ATC facility by stating '_____ clears,' 'A-T-C advises,' or 'A-T-C requests.'", "question_type": "fill_blank", "explanation": "Per 4-2-2(a): 'A-T-C' prefix identifies the message as originating from air traffic control.", "difficulty": 2, "choices": [{"choice_text": "A-T-C", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_3(db: sqlite3.Connection):
    """4-2-3 DELIVERY INSTRUCTIONS"""
    para = "4-2-3"
    print(f"\nCurating {para} — DELIVERY INSTRUCTIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue _____ clearance delivery instructions, if appropriate.', "question_type": "fill_blank", "explanation": 'Per 4-2-3: Clearance delivery instructions should be specific — not generic.', "difficulty": 1, "choices": [{"choice_text": "specific", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_4(db: sqlite3.Connection):
    """4-2-4 CLEARANCE RELAY"""
    para = "4-2-4"
    print(f"\nCurating {para} — CLEARANCE RELAY")
    cards = [{'front': 'How must clearances be relayed?', 'back': 'Relay clearances VERBATIM — do not paraphrase, summarize, or alter the wording.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Relay clearances _____.', "question_type": "fill_blank", "explanation": 'Per 4-2-4: Clearances must be relayed word-for-word — paraphrasing is not permitted.', "difficulty": 1, "choices": [{"choice_text": "verbatim", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'When relaying a clearance, a controller may summarize the key points to save frequency time.', "question_type": "true_false", "explanation": 'Per 4-2-4: Clearances must be relayed verbatim — summarizing is not permitted. Exact wording matters.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_5(db: sqlite3.Connection):
    """4-2-5 ROUTE OR ALTITUDE AMENDMENTS"""
    para = "4-2-5"
    print(f"\nCurating {para} — ROUTE OR ALTITUDE AMENDMENTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Amend route of flight by stating which _____ of the route is being amended and then state the amendment.', "question_type": "fill_blank", "explanation": 'Per 4-2-5(a)(1): Identify the specific portion being amended, then give the amendment — be precise.', "difficulty": 2, "choices": [{"choice_text": "portion", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_6(db: sqlite3.Connection):
    """4-2-6 THROUGH CLEARANCES"""
    para = "4-2-6"
    print(f"\nCurating {para} — THROUGH CLEARANCES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'You _____ clear an aircraft through intermediate stops.', "question_type": "fill_blank", "explanation": 'Per 4-2-6: Through clearances are authorized — an aircraft can be cleared to a destination with intermediate stops.', "difficulty": 1, "choices": [{"choice_text": "may", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_7(db: sqlite3.Connection):
    """4-2-7 ALTRV CLEARANCE"""
    para = "4-2-7"
    print(f"\nCurating {para} — ALTRV CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Use the phrase 'via approved _____ reservation flight plan' if the aircraft will operate in an approved ALTRV.", "question_type": "fill_blank", "explanation": 'Per 4-2-7: The standard ALTRV phraseology references the approved altitude reservation.', "difficulty": 1, "choices": [{"choice_text": "altitude", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_8(db: sqlite3.Connection):
    """4-2-8 IFR-VFR AND VFR-IFR FLIGHTS"""
    para = "4-2-8"
    print(f"\nCurating {para} — IFR-VFR AND VFR-IFR FLIGHTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Clear an aircraft planning IFR for the initial part of flight and VFR for the latter part to the _____ at which the IFR part ends.', "question_type": "fill_blank", "explanation": 'Per 4-2-8(a): The IFR-to-VFR transition point is a specific fix.', "difficulty": 2, "choices": [{"choice_text": "fix", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_2_9(db: sqlite3.Connection):
    """4-2-9 AIRFILE AIRCRAFT"""
    para = "4-2-9"
    print(f"\nCurating {para} — AIRFILE AIRCRAFT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Ensure the aircraft is within your area of _____ unless otherwise coordinated before processing an airfile flight.', "question_type": "fill_blank", "explanation": 'Per 4-2-9(a): Jurisdiction must be confirmed before processing airfile aircraft.', "difficulty": 2, "choices": [{"choice_text": "jurisdiction", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_1(db: sqlite3.Connection):
    """4-3-1 DEPARTURE TERMINOLOGY"""
    para = "4-3-1"
    print(f"\nCurating {para} — DEPARTURE TERMINOLOGY")
    cards = [{'front': "When should the term 'takeoff' be used?", 'back': "ONLY to actually clear an aircraft for takeoff or to cancel a takeoff clearance. Use 'depart,' 'departure,' or 'fly' in all other contexts.", 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": "Avoid using the term '_____' except to actually clear an aircraft for takeoff or to cancel a takeoff clearance.", "question_type": "fill_blank", "explanation": "Per 4-3-1: 'Takeoff' is reserved for actual takeoff clearances — use 'depart' or 'fly' otherwise.", "difficulty": 2, "choices": [{"choice_text": "takeoff", "is_correct": 1, "sort_order": 0}]},
        {"question_text": "A controller may say 'takeoff will be in about 5 minutes' when providing delay information.", "question_type": "true_false", "explanation": "Per 4-3-1: Do NOT use 'takeoff' except to clear for takeoff or cancel — say 'departure in about 5 minutes.'", "difficulty": 3, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_10(db: sqlite3.Connection):
    """4-3-10 FORWARDING DEPARTURE TIMES"""
    para = "4-3-10"
    print(f"\nCurating {para} — FORWARDING DEPARTURE TIMES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward departure times to the facility from which you received the clearance and to the terminal _____ controller.', "question_type": "fill_blank", "explanation": 'Per 4-3-10: Both the clearance-originating facility and the departure controller need departure times.', "difficulty": 1, "choices": [{"choice_text": "departure", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_2(db: sqlite3.Connection):
    """4-3-2 DEPARTURE CLEARANCES"""
    para = "4-3-2"
    print(f"\nCurating {para} — DEPARTURE CLEARANCES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Include the required items in _____ departure clearances in the prescribed order.', "question_type": "fill_blank", "explanation": 'Per 4-3-2: IFR departure clearances have a specific set of required items.', "difficulty": 1, "choices": [{"choice_text": "IFR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_3(db: sqlite3.Connection):
    """4-3-3 ABBREVIATED DEPARTURE CLEARANCE"""
    para = "4-3-3"
    print(f"\nCurating {para} — ABBREVIATED DEPARTURE CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue an abbreviated departure clearance if its use reduces _____ and specific conditions are met.', "question_type": "fill_blank", "explanation": "Per 4-3-3(a): Abbreviated clearances save frequency time — they're about efficiency.", "difficulty": 1, "choices": [{"choice_text": "verbiage", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_4(db: sqlite3.Connection):
    """4-3-4 DEPARTURE RELEASE AND VOID TIMES"""
    para = "4-3-4"
    print(f"\nCurating {para} — DEPARTURE RELEASE AND VOID TIMES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Assign departure restrictions, clearance _____ times, or release times to separate departures or regulate flow.', "question_type": "fill_blank", "explanation": 'Per 4-3-4: Void times, release times, and departure restrictions are the three tools for departure flow management.', "difficulty": 2, "choices": [{"choice_text": "void", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_5(db: sqlite3.Connection):
    """4-3-5 GROUND STOP"""
    para = "4-3-5"
    print(f"\nCurating {para} — GROUND STOP")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Do not release an aircraft if a _____ stop applicable to that aircraft is in effect, without the originator's approval.", "question_type": "fill_blank", "explanation": 'Per 4-3-5: Ground stops require originator approval before any release — no exceptions.', "difficulty": 2, "choices": [{"choice_text": "ground", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_6(db: sqlite3.Connection):
    """4-3-6 DELAY SEQUENCING"""
    para = "4-3-6"
    print(f"\nCurating {para} — DELAY SEQUENCING")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When aircraft take delay on the ground, issue departure clearances in the _____ in which requests were originally made, if practicable.', "question_type": "fill_blank", "explanation": 'Per 4-3-6: First-requested, first-cleared is the principle for ground delay sequencing.', "difficulty": 2, "choices": [{"choice_text": "order", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_7(db: sqlite3.Connection):
    """4-3-7 FORWARD DEPARTURE DELAY INFORMATION"""
    para = "4-3-7"
    print(f"\nCurating {para} — FORWARD DEPARTURE DELAY INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Inform _____ control facilities and/or towers of anticipated departure delays.', "question_type": "fill_blank", "explanation": 'Per 4-3-7: Approach control and towers need advance notice of departure delays for flow planning.', "difficulty": 1, "choices": [{"choice_text": "approach", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_8(db: sqlite3.Connection):
    """4-3-8 COORDINATION WITH RECEIVING FACILITY"""
    para = "4-3-8"
    print(f"\nCurating {para} — COORDINATION WITH RECEIVING FACILITY")
    cards = [{'front': 'When must departure coordination occur with the receiving facility?', 'back': "When the departure point is less than 15 minutes flying time from the transferring facility's boundary, unless automatic data transfer occurs.", 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": "Coordinate with the receiving facility before departure if the departure point is less than _____ minutes flying time from the transferring facility's boundary.", "question_type": "fill_blank", "explanation": 'Per 4-3-8(a): 15 minutes flying time is the coordination trigger.', "difficulty": 2, "choices": [{"choice_text": "15", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_3_9(db: sqlite3.Connection):
    """4-3-9 VFR RELEASE OF IFR DEPARTURE"""
    para = "4-3-9"
    print(f"\nCurating {para} — VFR RELEASE OF IFR DEPARTURE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When an IFR aircraft requests a _____ departure, after obtaining approval from the responsible facility, you may authorize it.', "question_type": "fill_blank", "explanation": 'Per 4-3-9: VFR departure of an IFR flight requires approval from the IFR-controlling facility.', "difficulty": 2, "choices": [{"choice_text": "VFR", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_4_1(db: sqlite3.Connection):
    """4-4-1 ROUTE USE"""
    para = "4-4-1"
    print(f"\nCurating {para} — ROUTE USE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Clear aircraft via routes consistent with the altitude _____ in which the operation is to be conducted.', "question_type": "fill_blank", "explanation": 'Per 4-4-1: Route and altitude stratum must be consistent.', "difficulty": 1, "choices": [{"choice_text": "stratum", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_4_2(db: sqlite3.Connection):
    """4-4-2 ROUTE STRUCTURE TRANSITIONS"""
    para = "4-4-2"
    print(f"\nCurating {para} — ROUTE STRUCTURE TRANSITIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'To transition within or between route structures, vector aircraft to or from radials, courses, or azimuths of the _____ route assigned, or assign a SID/STAR.', "question_type": "fill_blank", "explanation": 'Per 4-4-2: ATS route radials/courses/azimuths are the reference for vector transitions.', "difficulty": 2, "choices": [{"choice_text": "ATS", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_4_3(db: sqlite3.Connection):
    """4-4-3 DEGREE-DISTANCE ROUTE FOR MILITARY"""
    para = "4-4-3"
    print(f"\nCurating {para} — DEGREE-DISTANCE ROUTE FOR MILITARY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Do not accept a military flight plan whose route does not coincide with designated ATS routes or a direct course between NAVAIDs unless it meets degree-_____ route definition requirements.', "question_type": "fill_blank", "explanation": 'Per 4-4-3(a): Military degree-distance routes must meet specific procedural requirements.', "difficulty": 3, "choices": [{"choice_text": "distance", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_4_4(db: sqlite3.Connection):
    """4-4-4 ALTERNATIVE ROUTES"""
    para = "4-4-4"
    print(f"\nCurating {para} — ALTERNATIVE ROUTES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Use the word '_____' immediately preceding the alternative route description when clearing aircraft via an alternative route.", "question_type": "fill_blank", "explanation": "Per 4-4-4(a): 'Substitute' signals to the pilot that this is an alternative to their filed route.", "difficulty": 2, "choices": [{"choice_text": "substitute", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_4_5(db: sqlite3.Connection):
    """4-4-5 CLASS G AIRSPACE"""
    para = "4-4-5"
    print(f"\nCurating {para} — CLASS G AIRSPACE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Include routes through Class _____ airspace only when requested by the pilot.', "question_type": "fill_blank", "explanation": 'Per 4-4-5: Routes through Class G airspace are at pilot request only — controllers do not assign them.', "difficulty": 2, "choices": [{"choice_text": "G", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_4_6(db: sqlite3.Connection):
    """4-4-6 DIRECT CLEARANCES"""
    para = "4-4-6"
    print(f"\nCurating {para} — DIRECT CLEARANCES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Unless operational necessity dictates, do not issue a routing clearance that will take an aircraft off its flight plan route if the aircraft is part of a known traffic _____ initiative.', "question_type": "fill_blank", "explanation": 'Per 4-4-6(a)(1): TMI-participating aircraft should not be taken off route unnecessarily.', "difficulty": 2, "choices": [{"choice_text": "management", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_1(db: sqlite3.Connection):
    """4-5-1 VERTICAL SEPARATION MINIMA"""
    para = "4-5-1"
    print(f"\nCurating {para} — VERTICAL SEPARATION MINIMA")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Separate IFR aircraft using the prescribed minima between _____.', "question_type": "fill_blank", "explanation": 'Per 4-5-1: Vertical separation minima are prescribed between specific altitude layers.', "difficulty": 1, "choices": [{"choice_text": "altitudes", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_2(db: sqlite3.Connection):
    """4-5-2 FLIGHT DIRECTION"""
    para = "4-5-2"
    print(f"\nCurating {para} — FLIGHT DIRECTION")
    cards = [{'front': 'What is the flight direction rule for IFR cruising altitudes?', 'back': 'Eastbound (0-179 degrees) = odd thousands. Westbound (180-359 degrees) = even thousands. Based on magnetic course.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'IFR eastbound flights (0-179 degrees magnetic course) use _____ thousands of feet.', "question_type": "fill_blank", "explanation": 'Per 4-5-2: East is odd, west is even — IFR cruising altitude rule.', "difficulty": 1, "choices": [{"choice_text": "odd", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'An aircraft on a magnetic course of 270 degrees at FL310 is:', "question_type": "multiple_choice", "explanation": 'Per 4-5-2: 270 degrees is westbound — even thousands. FL310 is odd. The aircraft should be at FL300 or FL320.', "difficulty": 3, "choices": [{'choice_text': "At a correct altitude — 270 is westbound, even altitudes are correct, and 310 is odd so it's wrong.", 'is_correct': 1, 'sort_order': 0}, {'choice_text': 'At a correct altitude — all courses use the same altitudes above FL290.', 'is_correct': 0, 'sort_order': 1}, {'choice_text': 'At an incorrect altitude — the aircraft should be at FL320.', 'is_correct': 0, 'sort_order': 2}, {'choice_text': 'At an incorrect altitude — westbound aircraft must use FL290 only.', 'is_correct': 0, 'sort_order': 3}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_3(db: sqlite3.Connection):
    """4-5-3 CRUISING ALTITUDE"""
    para = "4-5-3"
    print(f"\nCurating {para} — CRUISING ALTITUDE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Assign cruising altitudes consistent with the aircraft's magnetic _____.", "question_type": "fill_blank", "explanation": 'Per 4-5-3: Magnetic course determines the appropriate cruising altitude stratum.', "difficulty": 1, "choices": [{"choice_text": "course", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_4(db: sqlite3.Connection):
    """4-5-4 ALTITUDE ASSIGNMENT"""
    para = "4-5-4"
    print(f"\nCurating {para} — ALTITUDE ASSIGNMENT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When an aircraft requests an altitude different from the prescribed cruising altitude, the controller _____ approve or disapprove based on traffic and separation.', "question_type": "fill_blank", "explanation": 'Per 4-5-4: Controllers have discretion to approve non-standard altitudes when traffic permits.', "difficulty": 1, "choices": [{"choice_text": "may", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_5(db: sqlite3.Connection):
    """4-5-5 ADJUSTED MINIMUM FLIGHT LEVEL"""
    para = "4-5-5"
    print(f"\nCurating {para} — ADJUSTED MINIMUM FLIGHT LEVEL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The minimum usable flight level is adjusted based on _____ pressure to ensure adequate terrain and obstacle clearance.', "question_type": "fill_blank", "explanation": 'Per 4-5-5: Barometric pressure changes affect minimum usable flight levels.', "difficulty": 2, "choices": [{"choice_text": "barometric", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_6(db: sqlite3.Connection):
    """4-5-6 ALTIMETER SETTING"""
    para = "4-5-6"
    print(f"\nCurating {para} — ALTIMETER SETTING")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue the current altimeter setting for the _____ concerned.', "question_type": "fill_blank", "explanation": 'Per 4-5-6: The altimeter setting must be for the airport being served.', "difficulty": 1, "choices": [{"choice_text": "airport", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_7(db: sqlite3.Connection):
    """4-5-7 LOWEST USABLE FLIGHT LEVEL"""
    para = "4-5-7"
    print(f"\nCurating {para} — LOWEST USABLE FLIGHT LEVEL")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Do not assign an altitude below the _____ usable flight level for the area.', "question_type": "fill_blank", "explanation": 'Per 4-5-7: Lowest usable flight level is the floor for IFR altitude assignments.', "difficulty": 2, "choices": [{"choice_text": "lowest", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_8(db: sqlite3.Connection):
    """4-5-8 TERRAIN AND OBSTRUCTION CLEARANCE"""
    para = "4-5-8"
    print(f"\nCurating {para} — TERRAIN AND OBSTRUCTION CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Ensure assigned altitudes provide required _____ and obstruction clearance.', "question_type": "fill_blank", "explanation": 'Per 4-5-8: Terrain and obstruction clearance is a fundamental safety requirement for all altitude assignments.', "difficulty": 1, "choices": [{"choice_text": "terrain", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_5_9(db: sqlite3.Connection):
    """4-5-9 ALTITUDE CHANGES"""
    para = "4-5-9"
    print(f"\nCurating {para} — ALTITUDE CHANGES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When issuing altitude changes, specify the new altitude and, if necessary, a _____ or point by which the change must be completed.', "question_type": "fill_blank", "explanation": 'Per 4-5-9: Altitude changes may include time or fix constraints for completion.', "difficulty": 2, "choices": [{"choice_text": "time", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_1(db: sqlite3.Connection):
    """4-6-1 HOLDING INSTRUCTIONS"""
    para = "4-6-1"
    print(f"\nCurating {para} — HOLDING INSTRUCTIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue holding instructions that include the holding _____, direction, and radial/course/bearing.', "question_type": "fill_blank", "explanation": 'Per 4-6-1: The holding fix is the first required element of holding instructions.', "difficulty": 1, "choices": [{"choice_text": "fix", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_2(db: sqlite3.Connection):
    """4-6-2 HOLDING PATTERN"""
    para = "4-6-2"
    print(f"\nCurating {para} — HOLDING PATTERN")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'The standard holding pattern uses _____ turns.', "question_type": "fill_blank", "explanation": 'Per 4-6-2: Standard holding patterns use right turns unless left turns are specified.', "difficulty": 1, "choices": [{"choice_text": "right", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_3(db: sqlite3.Connection):
    """4-6-3 DELAYS"""
    para = "4-6-3"
    print(f"\nCurating {para} — DELAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When holding instructions are issued due to _____, inform the pilot of the reason and expected duration.', "question_type": "fill_blank", "explanation": "Per 4-6-3: Pilots must be told why they're holding and for approximately how long.", "difficulty": 2, "choices": [{"choice_text": "delays", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_4(db: sqlite3.Connection):
    """4-6-4 HOLDING ALTITUDE"""
    para = "4-6-4"
    print(f"\nCurating {para} — HOLDING ALTITUDE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Assign a holding altitude at or above the _____ IFR altitude for the area.', "question_type": "fill_blank", "explanation": 'Per 4-6-4: Holding altitudes must be at or above minimum IFR altitude.', "difficulty": 2, "choices": [{"choice_text": "minimum", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_5(db: sqlite3.Connection):
    """4-6-5 HOLDING CLEARANCE"""
    para = "4-6-5"
    print(f"\nCurating {para} — HOLDING CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'A holding clearance automatically includes authorization to fly the _____ holding pattern.', "question_type": "fill_blank", "explanation": 'Per 4-6-5: Unless nonstandard is specified, the standard pattern is authorized.', "difficulty": 1, "choices": [{"choice_text": "standard", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_6(db: sqlite3.Connection):
    """4-6-6 EXPECT FURTHER CLEARANCE"""
    para = "4-6-6"
    print(f"\nCurating {para} — EXPECT FURTHER CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Issue an Expect Further Clearance time to all holding aircraft, communicated as 'expect further clearance at _____.'", "question_type": "fill_blank", "explanation": 'Per 4-6-6: EFC time must be given as a specific time — not a duration.', "difficulty": 2, "choices": [{"choice_text": "time", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_7(db: sqlite3.Connection):
    """4-6-7 HOLDING PATTERN AIRSPACE"""
    para = "4-6-7"
    print(f"\nCurating {para} — HOLDING PATTERN AIRSPACE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When holding aircraft at the same fix, assign altitudes so that the _____ aircraft holds at the highest altitude.', "question_type": "fill_blank", "explanation": 'Per 4-6-7: The first aircraft to hold gets the highest altitude — stacking.', "difficulty": 2, "choices": [{"choice_text": "first", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_6_8(db: sqlite3.Connection):
    """4-6-8 TERMINATION OF HOLDING"""
    para = "4-6-8"
    print(f"\nCurating {para} — TERMINATION OF HOLDING")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When holding is no longer necessary, _____ the holding clearance and issue onward routing.', "question_type": "fill_blank", "explanation": 'Per 4-6-8: Holding clearances must be explicitly cancelled when no longer needed.', "difficulty": 1, "choices": [{"choice_text": "cancel", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_1(db: sqlite3.Connection):
    """4-7-1 CLEARANCE INFORMATION"""
    para = "4-7-1"
    print(f"\nCurating {para} — CLEARANCE INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward clearance information to the appropriate facility _____ enough to permit adjustment of traffic flow.', "question_type": "fill_blank", "explanation": 'Per 4-7-1: Timing matters — coordination must arrive in time to be actionable.', "difficulty": 1, "choices": [{"choice_text": "soon", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_10(db: sqlite3.Connection):
    """4-7-10 SUSPENDING OPERATIONS"""
    para = "4-7-10"
    print(f"\nCurating {para} — SUSPENDING OPERATIONS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When weather or equipment conditions require, a controller may _____ operations until conditions improve.', "question_type": "fill_blank", "explanation": 'Per 4-7-10: Suspension is a controller tool for managing unsafe conditions.', "difficulty": 1, "choices": [{"choice_text": "suspend", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_11(db: sqlite3.Connection):
    """4-7-11 CLEARANCE BEYOND CLEARANCE LIMIT"""
    para = "4-7-11"
    print(f"\nCurating {para} — CLEARANCE BEYOND CLEARANCE LIMIT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Do not clear an aircraft beyond its clearance _____ until further routing has been coordinated.', "question_type": "fill_blank", "explanation": 'Per 4-7-11: The clearance limit is the boundary — do not exceed it without coordination.', "difficulty": 2, "choices": [{"choice_text": "limit", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_12(db: sqlite3.Connection):
    """4-7-12 FACILITY FAILURE"""
    para = "4-7-12"
    print(f"\nCurating {para} — FACILITY FAILURE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "During a facility communication _____, implement the facility's contingency procedures.", "question_type": "fill_blank", "explanation": 'Per 4-7-12: Facility-specific contingency procedures apply during communication failures.', "difficulty": 1, "choices": [{"choice_text": "failure", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_13(db: sqlite3.Connection):
    """4-7-13 SWITCHING ILS RUNWAYS"""
    para = "4-7-13"
    print(f"\nCurating {para} — SWITCHING ILS RUNWAYS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When switching ILS runways, ensure all affected aircraft are _____ and issued the new approach clearance.', "question_type": "fill_blank", "explanation": 'Per 4-7-13: All affected aircraft must be notified when ILS runways change.', "difficulty": 2, "choices": [{"choice_text": "advised", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'When switching ILS runways, the controller may simply begin using the new ILS frequency without advising aircraft already on approach.', "question_type": "true_false", "explanation": 'Per 4-7-13: All affected aircraft must be advised and re-cleared — silent runway switches are not permitted.', "difficulty": 2, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_2(db: sqlite3.Connection):
    """4-7-2 ADVANCE DESCENT CLEARANCE"""
    para = "4-7-2"
    print(f"\nCurating {para} — ADVANCE DESCENT CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue advance descent clearances when it will provide operational _____.', "question_type": "fill_blank", "explanation": 'Per 4-7-2: Advance descent clearances are issued for operational advantage.', "difficulty": 1, "choices": [{"choice_text": "advantage", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_3(db: sqlite3.Connection):
    """4-7-3 SINGLE FREQUENCY APPROACHES (SFA)"""
    para = "4-7-3"
    print(f"\nCurating {para} — SINGLE FREQUENCY APPROACHES (SFA)")
    cards = [{'front': 'What is a Single Frequency Approach (SFA)?', 'back': 'A procedure where the pilot uses a single frequency for both communication and navigation — requiring specific controller handling and coordination.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Single Frequency Approaches require the pilot to use a single frequency for both communication and _____.', "question_type": "fill_blank", "explanation": 'Per 4-7-3: SFA combines comm and nav on one frequency — a specialized procedure.', "difficulty": 3, "choices": [{"choice_text": "navigation", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_4(db: sqlite3.Connection):
    """4-7-4 RADIO FREQUENCY CHANGES FOR MILITARY"""
    para = "4-7-4"
    print(f"\nCurating {para} — RADIO FREQUENCY CHANGES FOR MILITARY")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When military aircraft change radio frequencies and radar beacon codes, coordinate with the _____ controller.', "question_type": "fill_blank", "explanation": 'Per 4-7-4: Frequency/code changes require receiving controller coordination.', "difficulty": 2, "choices": [{"choice_text": "receiving", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_5(db: sqlite3.Connection):
    """4-7-5 FORWARDING CLEARANCE INFORMATION"""
    para = "4-7-5"
    print(f"\nCurating {para} — FORWARDING CLEARANCE INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Forward aircraft identification, type, and _____ to nonapproach control towers soon enough to permit traffic flow adjustment.', "question_type": "fill_blank", "explanation": 'Per 4-7-5(a): ID, type, and ETA are the three minimum forwarding items to towers.', "difficulty": 2, "choices": [{"choice_text": "ETA", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_6(db: sqlite3.Connection):
    """4-7-6 ALTIMETER ISSUANCE"""
    para = "4-7-6"
    print(f"\nCurating {para} — ALTIMETER ISSUANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Issue the current _____ setting to arriving aircraft with the approach clearance.', "question_type": "fill_blank", "explanation": 'Per 4-7-6: Altimeter setting is part of the approach clearance package.', "difficulty": 1, "choices": [{"choice_text": "altimeter", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_7(db: sqlite3.Connection):
    """4-7-7 WEATHER INFORMATION"""
    para = "4-7-7"
    print(f"\nCurating {para} — WEATHER INFORMATION")
    cards = [{'front': 'When must weather reports be transmitted to arriving aircraft?', 'back': 'When the official weather report shows conditions below a 1,000-foot ceiling (USAF: 1,500-foot) or below the highest circling minimum, whichever is higher, or less than 3 miles visibility.', 'card_type': 'definition'}]
    n = insert_flashcards(db, para, cards)
    print(f"  FC:{n}", end=" ")
    questions = [
        {"question_text": 'Transmit weather when ceiling is below _____ feet (USAF: 1,500 feet) or visibility is less than 3 miles.', "question_type": "fill_blank", "explanation": 'Per 4-7-7: 1,000-foot ceiling (1,500 USAF) OR <3 miles visibility triggers mandatory weather transmission.', "difficulty": 2, "choices": [{"choice_text": "1000", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_8(db: sqlite3.Connection):
    """4-7-8 BELOW MINIMA REPORT BY PILOT"""
    para = "4-7-8"
    print(f"\nCurating {para} — BELOW MINIMA REPORT BY PILOT")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'If an arriving aircraft reports weather conditions are _____ his/her landing minima, take appropriate action.', "question_type": "fill_blank", "explanation": 'Per 4-7-8: A below-minima pilot report requires controller action.', "difficulty": 2, "choices": [{"choice_text": "below", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_7_9(db: sqlite3.Connection):
    """4-7-9 TRANSFER OF JURISDICTION"""
    para = "4-7-9"
    print(f"\nCurating {para} — TRANSFER OF JURISDICTION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Transfer radio communications and control responsibility _____ enough to allow the receiving facility to clear an aircraft beyond the clearance limit before the aircraft reaches it.', "question_type": "fill_blank", "explanation": 'Per 4-7-9: Early transfer gives the receiving controller time to act before the aircraft hits the limit.', "difficulty": 2, "choices": [{"choice_text": "early", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_1(db: sqlite3.Connection):
    """4-8-1 APPROACH CLEARANCE"""
    para = "4-8-1"
    print(f"\nCurating {para} — APPROACH CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": "Clear aircraft for '_____' or 'special' instrument approach procedures only.", "question_type": "fill_blank", "explanation": 'Per 4-8-1(a): Only standard or special IAPs may be cleared — no ad-hoc approach procedures.', "difficulty": 2, "choices": [{"choice_text": "standard", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_10(db: sqlite3.Connection):
    """4-8-10 APPROACH INFORMATION"""
    para = "4-8-10"
    print(f"\nCurating {para} — APPROACH INFORMATION")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When the pilot says they are _____ with the procedure, specify initial approach altitude, procedure turn details, and missed approach instructions.', "question_type": "fill_blank", "explanation": 'Per 4-8-10: Unfamiliar pilots get a full approach briefing including procedure turn details.', "difficulty": 2, "choices": [{"choice_text": "unfamiliar", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_11(db: sqlite3.Connection):
    """4-8-11 PRACTICE INSTRUMENT APPROACHES"""
    para = "4-8-11"
    print(f"\nCurating {para} — PRACTICE INSTRUMENT APPROACHES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When workload prevents authorization of practice instrument approaches, advise the pilot of the _____ and, if applicable, when to expect authorization.', "question_type": "fill_blank", "explanation": 'Per 4-8-11(a): Pilots must be told WHY their practice approach was denied and WHEN they can expect it.', "difficulty": 2, "choices": [{"choice_text": "reason", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_12(db: sqlite3.Connection):
    """4-8-12 LOW APPROACH AND TOUCH-AND-GO"""
    para = "4-8-12"
    print(f"\nCurating {para} — LOW APPROACH AND TOUCH-AND-GO")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Consider an aircraft cleared for touch-and-go as an arriving aircraft until it touches down; thereafter, consider it as a _____ aircraft.', "question_type": "fill_blank", "explanation": 'Per 4-8-12: Touch-and-go transitions from arrival to departure at touchdown.', "difficulty": 2, "choices": [{"choice_text": "departing", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_2(db: sqlite3.Connection):
    """4-8-2 APPROACH CLEARANCE TO UNCONTROLLED AIRPORTS"""
    para = "4-8-2"
    print(f"\nCurating {para} — APPROACH CLEARANCE TO UNCONTROLLED AIRPORTS")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When issuing an approach clearance at locations without an operating control tower, state the name of the _____.', "question_type": "fill_blank", "explanation": 'Per 4-8-2: Airport name is specifically required for uncontrolled airport approach clearances.', "difficulty": 2, "choices": [{"choice_text": "airport", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_3(db: sqlite3.Connection):
    """4-8-3 RELAYED APPROACH CLEARANCE"""
    para = "4-8-3"
    print(f"\nCurating {para} — RELAYED APPROACH CLEARANCE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Include the _____ report when it is required and available when an approach clearance is relayed through a non-air carrier station.', "question_type": "fill_blank", "explanation": 'Per 4-8-3: Relayed approach clearances must include the weather report when available.', "difficulty": 2, "choices": [{"choice_text": "weather", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_4(db: sqlite3.Connection):
    """4-8-4 ALTITUDE ASSIGNMENT FOR MILITARY HIGH ALTITUDE APPROACHES"""
    para = "4-8-4"
    print(f"\nCurating {para} — ALTITUDE ASSIGNMENT FOR MILITARY HIGH ALTITUDE APPROACHES")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Altitudes _____ those shown on the high altitude instrument approach chart may be specified when required for separation.', "question_type": "fill_blank", "explanation": 'Per 4-8-4: Military high altitude approaches may be assigned altitudes above charted values for separation.', "difficulty": 3, "choices": [{"choice_text": "above", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_5(db: sqlite3.Connection):
    """4-8-5 SPECIFYING ALTITUDE"""
    para = "4-8-5"
    print(f"\nCurating {para} — SPECIFYING ALTITUDE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Specify in the approach clearance the altitude shown in the approach procedures when adherence to that altitude is required for _____.', "question_type": "fill_blank", "explanation": "Per 4-8-5: Altitude must be specified when it's needed for separation.", "difficulty": 2, "choices": [{"choice_text": "separation", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_6(db: sqlite3.Connection):
    """4-8-6 CIRCLING APPROACH"""
    para = "4-8-6"
    print(f"\nCurating {para} — CIRCLING APPROACH")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Circling approach instructions may only be given for aircraft landing at airports with _____ control towers.', "question_type": "fill_blank", "explanation": 'Per 4-8-6(a): Circling approaches are restricted to airports with operating control towers.', "difficulty": 2, "choices": [{"choice_text": "operational", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_7(db: sqlite3.Connection):
    """4-8-7 SIDE-STEP MANEUVER"""
    para = "4-8-7"
    print(f"\nCurating {para} — SIDE-STEP MANEUVER")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'When authorized by an IAP, you may clear an aircraft for an approach to one runway and inform the aircraft that landing will be made on a _____ runway.', "question_type": "fill_blank", "explanation": 'Per 4-8-7: Side-step maneuvers go from one runway to a parallel runway.', "difficulty": 2, "choices": [{"choice_text": "parallel", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_8(db: sqlite3.Connection):
    """4-8-8 COMMUNICATIONS RELEASE"""
    para = "4-8-8"
    print(f"\nCurating {para} — COMMUNICATIONS RELEASE")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'If an IFR aircraft intends to land at an airport not served by a tower or FSS, approve a change to the _____ service frequency when you no longer require direct communications.', "question_type": "fill_blank", "explanation": 'Per 4-8-8: Advisory frequency (CTAF) is the release destination for non-tower airports.', "difficulty": 2, "choices": [{"choice_text": "advisory", "is_correct": 1, "sort_order": 0}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()

def curate_4_8_9(db: sqlite3.Connection):
    """4-8-9 MISSED APPROACH"""
    para = "4-8-9"
    print(f"\nCurating {para} — MISSED APPROACH")
    print(f"  FC:0", end=" ")
    questions = [
        {"question_text": 'Except for a VFR aircraft practicing an instrument approach, an approach clearance _____ authorizes the aircraft to execute the missed approach procedure.', "question_type": "fill_blank", "explanation": 'Per 4-8-9(a): The missed approach is automatically authorized with the approach clearance — no separate clearance needed.', "difficulty": 2, "choices": [{"choice_text": "automatically", "is_correct": 1, "sort_order": 0}]},
        {"question_text": 'A separate clearance is required for an IFR aircraft to execute the missed approach procedure.', "question_type": "true_false", "explanation": 'Per 4-8-9(a): The approach clearance automatically authorizes the missed approach — no separate clearance is needed.', "difficulty": 3, "choices": [{'choice_text': 'True', 'is_correct': 0, 'sort_order': 0}, {'choice_text': 'False', 'is_correct': 1, 'sort_order': 1}]},
    ]
    n = insert_quiz_questions(db, para, questions)
    print(f"Q:{n}", end=" ")
    print()


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA foreign_keys = ON")
    try:
        curate_4_1_1(db)
        curate_4_1_2(db)
        curate_4_1_3(db)
        curate_4_1_4(db)
        curate_4_1_5(db)
        curate_4_2_1(db)
        curate_4_2_10(db)
        curate_4_2_2(db)
        curate_4_2_3(db)
        curate_4_2_4(db)
        curate_4_2_5(db)
        curate_4_2_6(db)
        curate_4_2_7(db)
        curate_4_2_8(db)
        curate_4_2_9(db)
        curate_4_3_1(db)
        curate_4_3_10(db)
        curate_4_3_2(db)
        curate_4_3_3(db)
        curate_4_3_4(db)
        curate_4_3_5(db)
        curate_4_3_6(db)
        curate_4_3_7(db)
        curate_4_3_8(db)
        curate_4_3_9(db)
        curate_4_4_1(db)
        curate_4_4_2(db)
        curate_4_4_3(db)
        curate_4_4_4(db)
        curate_4_4_5(db)
        curate_4_4_6(db)
        curate_4_5_1(db)
        curate_4_5_2(db)
        curate_4_5_3(db)
        curate_4_5_4(db)
        curate_4_5_5(db)
        curate_4_5_6(db)
        curate_4_5_7(db)
        curate_4_5_8(db)
        curate_4_5_9(db)
        curate_4_6_1(db)
        curate_4_6_2(db)
        curate_4_6_3(db)
        curate_4_6_4(db)
        curate_4_6_5(db)
        curate_4_6_6(db)
        curate_4_6_7(db)
        curate_4_6_8(db)
        curate_4_7_1(db)
        curate_4_7_10(db)
        curate_4_7_11(db)
        curate_4_7_12(db)
        curate_4_7_13(db)
        curate_4_7_2(db)
        curate_4_7_3(db)
        curate_4_7_4(db)
        curate_4_7_5(db)
        curate_4_7_6(db)
        curate_4_7_7(db)
        curate_4_7_8(db)
        curate_4_7_9(db)
        curate_4_8_1(db)
        curate_4_8_10(db)
        curate_4_8_11(db)
        curate_4_8_12(db)
        curate_4_8_2(db)
        curate_4_8_3(db)
        curate_4_8_4(db)
        curate_4_8_5(db)
        curate_4_8_6(db)
        curate_4_8_7(db)
        curate_4_8_8(db)
        curate_4_8_9(db)
        db.commit()
        print("\n✓ All content inserted successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
