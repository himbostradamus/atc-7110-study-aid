#!/usr/bin/env python3
"""
generate_curriculum.py
======================
Builds the complete ATC 7110.65 curriculum database in one pass.

Outputs:  curriculum.db  (SQLite, portable — ships with the app)

Strategy
--------
  Rule-based (zero API cost):
    • phraseology_builder  — direct extraction from phraseology blocks
    • sequence_steps       — parse numbered / lettered lists in body blocks
    • match_pairs          — definition extraction from body + note blocks
    • flashcards           — phraseology front/back + key-term cards

  Local enrichment:
    • phraseology_builder_backfill — cover example-only phraseology paragraphs
    • spot_the_error       — introduce one plausible error into phraseology
    • readback_check       — write 3 wrong pilot read-backs
    • situation_action     — write a realistic ATC scenario
    • directive_check      — validate short imperative directives
    • conditional_rule_check — validate conditional procedures
    • term_definition_check — validate short definitional paragraphs
    • document_control_check — validate document-admin statements
    • requirement_check    — validate controller requirement/permission statements
    • scope_check          — validate scope/responsibility statements
    • capability_check     — validate system/equipment capability statements
    • minima_rule_check    — validate minima/separation statements
    • list_membership      — curated-only checks for meaningful listed items
    • table_lookup         — verify simple threshold-table rows
    • example_check        — validate example phraseology/examples
    • quiz_questions       — deterministic MC / T-F / fill-blank / ordering

Usage
-----
  python3 generate_curriculum.py [--source /mnt/project] [--out curriculum.db]
                                  [--resume] [--chapter 2] [--publish frontend/public]

  --resume    Skip paragraphs already in the DB (safe to restart after crash)
  --chapter   Generate only specific chapter(s); otherwise auto-detect from source
  --dry-run   Parse + rule-based only; skip local enrichment
  --publish   Copy the finished curriculum.db into a frontend/public path
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.activity_generator import (
    generate_activities_for_paragraph as generate_local_activities_for_paragraph,
)
from backend.app.services.card_generator import (
    generate_cards_for_paragraph as generate_local_cards_for_paragraph,
)
from backend.app.services.curated_content import (
    get_curated_activity_override,
)
from backend.app.services.local_generation import (
    extract_term_pairs_from_text,
    meaningful_sentences_from_text,
    phraseology_lines_from_text,
)
from backend.app.services.question_generator import (
    generate_questions_for_paragraph as generate_local_questions_for_paragraph,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

BATCH_SIZE     = 4       # paragraphs per enrichment batch

# ATC vocabulary pool for phraseology_builder distractors
ATC_DISTRACTOR_POOL = [
    "ADVISE","AFFIRM","APPROVED","CANCEL","CAUTION","CLEARED","CONTACT",
    "CONTINUE","CROSS","DESCEND","DIRECT","DISREGARD","EXPEDITE","EXPECT",
    "FILED","FLIGHT","HOLD","IMMEDIATELY","IDENT","INCREASE","INFORMATION",
    "MAINTAIN","MONITOR","NEGATIVE","NOTIFY","OVER","PROCEED","RADAR",
    "READBACK","REDUCE","REMAIN","REPORT","REQUEST","ROGER","SEPARATION",
    "SQUAWK","STANDBY","STOP","TRAFFIC","TURN","UNABLE","VERIFY","WILCO",
]

# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Para:
    id:         str
    chapter:    int
    section:    int
    para_id:    str   # e.g. "2-1-6"
    title:      str
    blocks:     list[dict]
    page:       int   = 0
    has_visual: bool  = False

    def text(self, *btypes) -> str:
        types = set(btypes) if btypes else None
        parts = [b["content"] for b in self.blocks
                 if types is None or b["block_type"] in types]
        return "\n\n".join(parts).strip()

    def has_block(self, btype: str) -> bool:
        return any(b["block_type"] == btype for b in self.blocks)


@dataclass
class GeneratedContent:
    para_id:     str
    activities:  list[dict] = field(default_factory=list)
    flashcards:  list[dict] = field(default_factory=list)
    questions:   list[dict] = field(default_factory=list)
    errors:      list[str]  = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# SQLITE SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS paragraphs (
    id          TEXT PRIMARY KEY,
    chapter     INTEGER NOT NULL,
    section     INTEGER NOT NULL,
    para_id     TEXT NOT NULL UNIQUE,
    title       TEXT,
    page        INTEGER,
    has_visual  INTEGER DEFAULT 0,
    content_json TEXT NOT NULL,   -- full blocks array as JSON
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_para_chapter ON paragraphs(chapter);

CREATE TABLE IF NOT EXISTS activities (
    id              TEXT PRIMARY KEY,
    paragraph_db_id TEXT NOT NULL REFERENCES paragraphs(id),
    para_id         TEXT NOT NULL,
    activity_type   TEXT NOT NULL,
    content_json    TEXT NOT NULL,
    difficulty      INTEGER DEFAULT 2,
    generation_src  TEXT DEFAULT 'rule_based',
    is_verified     INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(para_id, activity_type, generation_src)
);
CREATE INDEX IF NOT EXISTS idx_act_para   ON activities(para_id);
CREATE INDEX IF NOT EXISTS idx_act_type   ON activities(activity_type);

CREATE TABLE IF NOT EXISTS flashcards (
    id              TEXT PRIMARY KEY,
    paragraph_db_id TEXT NOT NULL REFERENCES paragraphs(id),
    para_id         TEXT NOT NULL,
    front           TEXT NOT NULL,
    back            TEXT NOT NULL,
    card_type       TEXT DEFAULT 'phraseology',
    generation_src  TEXT DEFAULT 'rule_based',
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(para_id, card_type, front)
);
CREATE INDEX IF NOT EXISTS idx_fc_para ON flashcards(para_id);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id              TEXT PRIMARY KEY,
    paragraph_db_id TEXT NOT NULL REFERENCES paragraphs(id),
    para_id         TEXT NOT NULL,
    question_text   TEXT NOT NULL,
    question_type   TEXT DEFAULT 'multiple_choice',
    explanation     TEXT,
    difficulty      INTEGER DEFAULT 2,
    generation_src  TEXT DEFAULT 'local_auto',
    is_verified     INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_qq_para ON quiz_questions(para_id);

CREATE TABLE IF NOT EXISTS question_choices (
    id          TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES quiz_questions(id),
    choice_text TEXT NOT NULL,
    is_correct  INTEGER NOT NULL DEFAULT 0,
    sort_order  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qc_question ON question_choices(question_id);

CREATE TABLE IF NOT EXISTS source_assets (
    id              TEXT PRIMARY KEY,
    para_id         TEXT NOT NULL,
    chapter         INTEGER NOT NULL,
    section         INTEGER NOT NULL,
    asset_type      TEXT NOT NULL,
    label           TEXT NOT NULL,
    title           TEXT,
    source_url      TEXT NOT NULL,
    source_page_url TEXT NOT NULL,
    pdf_url         TEXT,
    html            TEXT,
    image_url       TEXT,
    alt_text        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(label, source_url)
);
CREATE INDEX IF NOT EXISTS idx_source_assets_para ON source_assets(para_id);
CREATE INDEX IF NOT EXISTS idx_source_assets_label ON source_assets(label);

CREATE TABLE IF NOT EXISTS generation_log (
    para_id     TEXT PRIMARY KEY,
    status      TEXT NOT NULL,   -- 'complete' | 'partial' | 'failed'
    rule_acts   INTEGER DEFAULT 0,
    ai_acts     INTEGER DEFAULT 0,
    flashcards  INTEGER DEFAULT 0,
    questions   INTEGER DEFAULT 0,
    errors      TEXT DEFAULT '[]',
    updated_at  TEXT DEFAULT (datetime('now'))
);
"""


def open_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.execute("INSERT OR IGNORE INTO meta VALUES ('version','1.0')")
    generated_at = datetime.now(timezone.utc).isoformat()
    db.execute(f"INSERT OR REPLACE INTO meta VALUES ('generated_at','{generated_at}')")
    db.commit()
    return db


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE PARSING  (re-uses ingestion pipeline logic inline)
# ─────────────────────────────────────────────────────────────────────────────

RE_PARA    = re.compile(r'^(\d+[−\-]\d+[−\-]\d+)\.\s*(.*?)$', re.MULTILINE)
RE_SECTION = re.compile(r'^(\d+[−\-]\d+)\.\s+([A-Z][A-Z /\(\)\-]{3,})$', re.MULTILINE)
RE_MARKERS = {
    'note':           re.compile(r'^NOTE[−\-]?\s*$', re.MULTILINE),
    'phraseology':    re.compile(r'^PHRASEOLOGY[−\-]\s*$', re.MULTILINE),
    'example':        re.compile(r'^EXAMPLE[−\-]\s*$', re.MULTILINE),
    'reference':      re.compile(r'^REFERENCE[−\-]\s*$', re.MULTILINE),
    'exception':      re.compile(r'^EXCEPTION[.\-]', re.MULTILINE),
    'interpretation': re.compile(r'^INTERPRETATION[−\-]\s*$', re.MULTILINE),
}

CHAPTER_FILES = {
    2: "7110_65BB_Ch2_GeneralControl",
    3: "7110_65BB_Ch3_AirTrafficControlTerminal",
    4: "7110_65BB_Ch4_IFR",
}
CHAPTER_TITLES = {
    2: "General Control",
    3: "Air Traffic Control – Terminal",
    4: "IFR",
}
CHAPTER_HINTS = {
    2: ("711065bb", "ch2", "general"),
    3: ("711065bb", "ch3", "terminal"),
    4: ("711065bb", "ch4", "ifr"),
}
GENERIC_CHAPTER_RE = re.compile(
    r"(?:^|[^a-z0-9])ch(?:apter)?[\s._-]*(\d{1,2})(?:[^a-z0-9]|$)",
    re.IGNORECASE,
)
FILENAME_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[-_](\d{1,2})[-_](\d{2,4})(?!\d)")
CHANGE_RE = re.compile(r"chg[\s._-]*(\d+)", re.IGNORECASE)
FULL_ORDER_CHAPTERS = list(range(1, 15))


def _normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_chapter_number_from_name(value: str) -> Optional[int]:
    match = GENERIC_CHAPTER_RE.search(value)
    if not match:
        return None
    return int(match.group(1))


def is_full_order_candidate(path: Path) -> bool:
    normalised = _normalise_name(path.stem)
    return "711065" in normalised and parse_chapter_number_from_name(path.stem.lower()) is None


def source_recency_key(path: Path) -> tuple[int, int, int, int]:
    match = None
    for candidate in FILENAME_DATE_RE.finditer(path.stem):
        match = candidate

    year = month = day = 0
    if match:
        month, day, year = map(int, match.groups())
        if year < 100:
            year += 2000

    change_match = CHANGE_RE.search(path.stem)
    change_number = int(change_match.group(1)) if change_match else 0
    return (year, month, day, change_number)


def list_candidate_sources(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_dir}")
    if source_dir.is_file():
        return [source_dir]
    return sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".zip", ".pdf"}
    )


def discover_available_chapters(source_dir: Path) -> list[int]:
    chapters: set[int] = set()
    for candidate in list_candidate_sources(source_dir):
        chapter_number = parse_chapter_number_from_name(candidate.stem.lower())
        if chapter_number is not None:
            chapters.add(chapter_number)
        elif is_full_order_candidate(candidate):
            chapters.update(FULL_ORDER_CHAPTERS)
    return sorted(chapters)


def discover_chapter_source(source_dir: Path, chapter_number: int) -> Optional[Path]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_dir}")

    if source_dir.is_file():
        return source_dir

    exact_candidates = []
    if chapter_number in CHAPTER_FILES:
        for ext in (".zip", ".pdf"):
            exact_candidates.append(source_dir / f"{CHAPTER_FILES[chapter_number]}{ext}")

    for candidate in exact_candidates:
        if candidate.exists():
            return candidate

    hints = CHAPTER_HINTS.get(chapter_number, (f"ch{chapter_number}",))
    candidates = list_candidate_sources(source_dir)
    scored: list[tuple[int, Path]] = []
    for candidate in candidates:
        normalised = _normalise_name(candidate.stem)
        score = 0
        if chapter_number in CHAPTER_FILES and normalised == _normalise_name(CHAPTER_FILES[chapter_number]):
            score += 100
        parsed_chapter = parse_chapter_number_from_name(candidate.stem.lower())
        if parsed_chapter == chapter_number:
            score += 40
        if candidate.suffix.lower() == ".zip":
            score += 20
        for hint in hints:
            if hint in normalised:
                score += 15
        if score >= 30:
            scored.append((score, candidate))

    if not scored:
        full_order_candidates = [
            path for path in candidates
            if is_full_order_candidate(path)
        ]
        if not full_order_candidates:
            return None
        full_order_candidates.sort(
            key=lambda path: (source_recency_key(path), -len(path.name), path.name),
            reverse=True,
        )
        return full_order_candidates[0]

    scored.sort(key=lambda item: (-item[0], len(item[1].name), item[1].name))
    best_match = scored[0][1]

    full_order_candidates = [path for path in candidates if is_full_order_candidate(path)]
    if full_order_candidates:
        best_full_order = max(full_order_candidates, key=source_recency_key)
        if source_recency_key(best_full_order) > source_recency_key(best_match):
            return best_full_order

    return best_match


def _load_zip_pages(zip_path: Path) -> tuple[dict[int, str], dict[int, dict]]:
    with zipfile.ZipFile(zip_path) as z:
        manifest = json.loads(z.read('manifest.json'))
        page_texts = {}
        page_meta = {}
        for pg in manifest['pages']:
            n = pg['page_number']
            page_meta[n] = pg
            try:
                page_texts[n] = z.read(pg['text']['path']).decode('utf-8', errors='replace')
            except KeyError:
                page_texts[n] = ""
    return page_texts, page_meta


def _load_pdf_pages(pdf_path: Path) -> tuple[dict[int, str], dict[int, dict]]:
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pdftotext is required to parse PDF chapter files") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown pdftotext failure"
        raise RuntimeError(f"pdftotext failed for {pdf_path.name}: {stderr}") from exc

    pages = proc.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()

    page_texts: dict[int, str] = {}
    page_meta: dict[int, dict] = {}
    for index, page_text in enumerate(pages, start=1):
        cleaned = page_text.replace("\r\n", "\n").replace("\r", "\n")
        page_texts[index] = cleaned
        page_meta[index] = {
            "page_number": index,
            "has_visual_content": False,
            "source_type": "pdf",
        }

    return page_texts, page_meta


def load_source_pages(source_path: Path) -> tuple[dict[int, str], dict[int, dict]]:
    suffix = source_path.suffix.lower()
    if suffix == ".zip":
        return _load_zip_pages(source_path)
    if suffix == ".pdf":
        return _load_pdf_pages(source_path)
    raise ValueError(f"Unsupported source type: {source_path}")


def publish_db(out_path: Path, publish_path: Path) -> Path:
    target = publish_path
    if target.suffix.lower() != ".db":
        target.mkdir(parents=True, exist_ok=True)
        target = target / "curriculum.db"
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_path, target)
    return target


def reset_sqlite_output(path: Path) -> None:
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            candidate.unlink()


def _classify(line: str) -> Optional[str]:
    s = line.strip()
    for btype, pat in RE_MARKERS.items():
        if pat.match(s):
            return btype
    return None


def _parse_blocks(raw: str) -> list[dict]:
    blocks, cur_type, cur_lines, seq = [], 'body', [], 0
    lines = raw.split('\n')
    if lines and RE_PARA.match(lines[0].strip()):
        lines = lines[1:]

    def flush():
        nonlocal seq, cur_lines
        content = '\n'.join(cur_lines).strip()
        if content:
            blocks.append({"block_type": cur_type, "sequence": seq,
                           "label": "", "content": content})
            seq += 1
        cur_lines = []

    for line in lines:
        bt = _classify(line)
        if bt:
            flush()
            cur_type = bt
        else:
            cur_lines.append(line)
    flush()
    return blocks


def _parse_source_document(source_path: Path, requested_chapters: set[int]) -> list[Para]:
    page_texts, page_meta = load_source_pages(source_path)
    full_text = '\n'.join(page_texts[n] for n in sorted(page_texts))

    sections: dict[str, tuple[int, str]] = {}
    for m in RE_SECTION.finditer(full_text):
        key = m.group(1).replace('−', '-')
        parts = key.split('-')
        if len(parts) == 2:
            try:
                sections[key] = (int(parts[1]), m.group(2).strip())
            except ValueError:
                pass

    offsets: dict[int, int] = {}
    pos = 0
    for n in sorted(page_texts):
        offsets[pos] = n
        pos += len(page_texts[n]) + 1
    sorted_offsets = sorted(offsets)

    def off2page(off: int) -> tuple[int, bool]:
        for i in range(len(sorted_offsets) - 1, -1, -1):
            if off >= sorted_offsets[i]:
                pn = offsets[sorted_offsets[i]]
                return pn, page_meta.get(pn, {}).get('has_visual_content', False)
        return 1, False

    paras: list[Para] = []
    para_matches = list(RE_PARA.finditer(full_text))
    seen_para_ids: set[str] = set()
    for i, pm in enumerate(para_matches):
        raw_id = pm.group(1).replace('−', '-')
        title  = pm.group(2).strip()
        start  = pm.start()
        end    = para_matches[i + 1].start() if i + 1 < len(para_matches) else len(full_text)
        raw    = full_text[start:end].strip()

        parts = raw_id.split('-')
        try:
            chapter_num = int(parts[0])
        except (IndexError, ValueError):
            continue
        if requested_chapters and chapter_num not in requested_chapters:
            continue
        if raw_id in seen_para_ids:
            continue
        seen_para_ids.add(raw_id)

        section_num = 1
        if len(parts) >= 2:
            try:
                section_num = sections.get(f"{parts[0]}-{parts[1]}", (int(parts[1]), ""))[0]
            except ValueError:
                section_num = 1

        pn, has_vis = off2page(start)
        paras.append(Para(
            id         = str(uuid.uuid4()),
            chapter    = chapter_num,
            section    = section_num,
            para_id    = raw_id,
            title      = title,
            blocks     = _parse_blocks(raw),
            page       = pn,
            has_visual = has_vis,
        ))

    return paras


def load_paragraphs(source_dir: Path, chapters: list[int]) -> list[Para]:
    requested_chapters = set(chapters)
    source_map: dict[Path, set[int]] = {}

    if source_dir.is_file():
        source_map[source_dir] = requested_chapters
    else:
        for ch_num in chapters:
            source_path = discover_chapter_source(source_dir, ch_num)
            if not source_path:
                print(f"  [WARN] No source file for Chapter {ch_num}")
                continue
            source_map.setdefault(source_path, set()).add(ch_num)

    paras: list[Para] = []
    for source_path, source_chapters in sorted(source_map.items(), key=lambda item: item[0].name):
        chapter_list = sorted(source_chapters)
        chapter_label = ", ".join(str(ch) for ch in chapter_list)
        print(f"  [SRC] Chapters {chapter_label}: {source_path.name}")
        paras.extend(_parse_source_document(source_path, source_chapters))

    paras.sort(key=lambda para: tuple(int(part) for part in para.para_id.split('-')))
    print(f"  Parsed {len(paras)} paragraphs from chapters {chapters}")
    return paras


# ─────────────────────────────────────────────────────────────────────────────
# RULE-BASED EXTRACTORS
# ─────────────────────────────────────────────────────────────────────────────

def extract_phraseology_builder(para: Para) -> list[dict]:
    """Phraseology reconstruction is now curated rather than auto-extracted."""
    return []


def extract_sequence_steps(para: Para) -> list[dict]:
    """Parse numbered/lettered procedure lists from body blocks."""
    activities = []

    for block in para.blocks:
        if block['block_type'] not in ('body',):
            continue
        text = block['content']

        # Match numbered items: "1. ...", "a. ...", "2. ..."
        items = re.findall(
            r'(?:^|\n)\s*([a-e]|\d+)\.\s+(.+?)(?=\n\s*(?:[a-e]|\d+)\.|$)',
            text, re.DOTALL
        )
        if len(items) < 3:
            continue

        steps = []
        for label, step_text in items[:5]:
            clean = re.sub(r'\s+', ' ', step_text.strip())
            clean = clean[:100]   # truncate for display
            if len(clean) < 10:
                continue
            steps.append({"id": str(uuid.uuid4())[:8], "text": clean})

        if len(steps) < 3:
            continue

        # Correct order = order as written; shuffle for presentation
        import random
        rng  = random.Random(hash(para.para_id))
        correct_order = [s['id'] for s in steps]
        shuffled = steps[:]
        rng.shuffle(shuffled)

        activities.append({
            "activity_type":  "sequence_steps",
            "difficulty":      2,
            "generation_src": "rule_based",
            "content": {
                "instruction":   "Place these steps in the correct procedural order",
                "steps":         shuffled,
                "correct_order": correct_order,
                "explanation":   f"Per {para.para_id}: steps must be performed in this order.",
            },
        })
        break  # one sequence per paragraph

    return activities


def extract_match_pairs(para: Para) -> list[dict]:
    text = para.text('body', 'note', 'interpretation')
    pairs = [
        {"term": term, "definition": definition}
        for term, definition in extract_term_pairs_from_text(text)
    ]
    if len(pairs) < 3:
        return []

    return [{
        "activity_type":  "match_pairs",
        "difficulty":      1,
        "generation_src": "rule_based",
        "content": {
            "instruction": "Match each ATC term with its correct definition",
            "pairs":       pairs,
        },
    }]


def extract_flashcards(para: Para) -> list[dict]:
    """
    Rule-based flashcard extraction:
      1. Phraseology cards — front: situation, back: exact phraseology
      2. Definition cards — front: what is X?, back: body description
      3. Procedure cards — front: when must you..., back: procedure text
    """
    cards = []

    # Phraseology cards (most valuable)
    phrasing = [b for b in para.blocks if b['block_type'] == 'phraseology']
    for pb in phrasing[:2]:
        raw = pb['content'].strip()
        if len(raw) < 10:
            continue
        phrase_lines = phraseology_lines_from_text(raw)
        if not phrase_lines:
            continue
        # Find the preceding body text as context
        body_before = ""
        for b in para.blocks:
            if b['sequence'] < pb['sequence'] and b['block_type'] == 'body':
                body_before = b['content']
        context_sentences = meaningful_sentences_from_text(body_before)
        front_ctx = context_sentences[0] if context_sentences else para.title
        cards.append({
            "card_type":      "phraseology",
            "generation_src": "rule_based",
            "front": f"State the phraseology for: {front_ctx or para.title}",
            "back":  phrase_lines[0][:300],
        })

    # Definition / key-concept card from body
    body_text = para.text('body')
    if body_text and para.title and len(para.title) > 3:
        # First meaningful sentence after the paragraph number
        sentences = re.split(r'(?<=[.!?])\s+', body_text)
        first_sent = next(
            (s for s in sentences if len(s.split()) > 8 and not re.match(r'^\d', s)), ""
        )
        if first_sent:
            clean = re.sub(r'\s+', ' ', first_sent[:250]).strip()
            cards.append({
                "card_type":      "definition",
                "generation_src": "rule_based",
                "front": f"§{para.para_id} ({para.title}): What is the rule?",
                "back":  clean,
            })

    return cards


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL ENRICHMENT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _wrap_activity_batch(activity_type: str, items: list[dict]) -> list[dict]:
    return [
        {
            "activity_type": activity_type,
            "difficulty": int(item.get("difficulty", 2)),
            "generation_src": item.get("generation_source", "local_auto"),
            "content": item,
        }
        for item in items
    ]


async def _local_activity_batch(
    paras: list[Para],
    activity_type: str,
) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for para in paras:
        generated = await generate_local_activities_for_paragraph(
            para_id=para.para_id,
            para_title=para.title,
            blocks=para.blocks,
            types=[activity_type],
        )
        items = generated.get(activity_type, [])
        if items:
            results[para.para_id] = _wrap_activity_batch(activity_type, items)
    return results


async def local_spot_the_error_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "spot_the_error")


async def local_phraseology_builder_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "phraseology_builder")


async def local_sequence_steps_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "sequence_steps")


async def local_readback_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "readback_check")


async def local_situation_action_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "situation_action")


async def local_directive_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "directive_check")


async def local_conditional_rule_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "conditional_rule_check")


async def local_term_definition_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "term_definition_check")


async def local_document_control_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "document_control_check")


async def local_requirement_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "requirement_check")


async def local_scope_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "scope_check")


async def local_capability_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "capability_check")


async def local_reference_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "reference_check")


async def local_minima_rule_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "minima_rule_check")


async def local_list_membership_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "list_membership")


async def local_table_lookup_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "table_lookup")


async def local_example_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "example_check")


async def local_knowledge_check_batch(paras: list[Para]) -> dict[str, list[dict]]:
    return await _local_activity_batch(paras, "knowledge_check")


def _activity_type_count(db: sqlite3.Connection, para_id: str) -> int:
    row = db.execute(
        "SELECT COUNT(DISTINCT activity_type) FROM activities WHERE para_id=?",
        (para_id,),
    ).fetchone()
    return int(row[0] or 0)


def _has_curated_activity_type(para: Para, activity_type: str) -> bool:
    override = get_curated_activity_override(para.para_id)
    if not override:
        return False
    if activity_type in override.get("replace_types", []):
        return True
    return any(
        item.get("activity_type") == activity_type
        for item in override.get("items", [])
    )


def _filter_rule_based_activities(para: Para, activities: list[dict]) -> list[dict]:
    override = get_curated_activity_override(para.para_id)
    if not override:
        return activities
    suppressed = set(override.get("replace_types", []))
    if not suppressed:
        return activities
    return [
        activity for activity in activities
        if activity.get("activity_type") not in suppressed
    ]


def _question_to_dict(question) -> dict:
    return {
        "question_text": question.question_text.strip(),
        "question_type": question.question_type,
        "choices": [
            {"text": choice.text, "is_correct": choice.is_correct}
            for choice in question.choices
        ],
        "explanation": question.explanation.strip(),
        "difficulty": int(question.difficulty),
        "generation_src": getattr(question, "generation_source", "local_auto"),
    }


def _card_to_dict(card) -> dict:
    return {
        "front": card.front.strip(),
        "back": card.back.strip(),
        "card_type": card.card_type,
        "generation_src": getattr(card, "generation_source", "local_auto"),
    }


async def local_flashcards_batch(paras: list[Para]) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for para in paras:
        cards = await generate_local_cards_for_paragraph(
            para_id=para.para_id,
            para_title=para.title,
            blocks=para.blocks,
        )
        if cards:
            results[para.para_id] = [_card_to_dict(card) for card in cards]
    return results


async def local_quiz_questions_batch(paras: list[Para]) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for para in paras:
        questions = await generate_local_questions_for_paragraph(
            para_id=para.para_id,
            para_title=para.title,
            blocks=para.blocks,
        )
        if questions:
            results[para.para_id] = [_question_to_dict(question) for question in questions]
    return results


# ─────────────────────────────────────────────────────────────────────────────
# DB WRITERS
# ─────────────────────────────────────────────────────────────────────────────

def write_paragraph(db: sqlite3.Connection, para: Para):
    db.execute("""
        INSERT OR IGNORE INTO paragraphs
            (id, chapter, section, para_id, title, page, has_visual, content_json)
        VALUES (?,?,?,?,?,?,?,?)
    """, (para.id, para.chapter, para.section, para.para_id, para.title,
          para.page, int(para.has_visual), json.dumps(para.blocks)))
    # Always sync para.id to the stored DB value (handles resume/re-runs)
    row = db.execute("SELECT id FROM paragraphs WHERE para_id=?", (para.para_id,)).fetchone()
    if row:
        para.id = row[0]


def write_activity(db: sqlite3.Connection, para: Para, act: dict):
    db.execute("""
        INSERT OR IGNORE INTO activities
            (id, paragraph_db_id, para_id, activity_type, content_json,
             difficulty, generation_src)
        VALUES (?,?,?,?,?,?,?)
    """, (str(uuid.uuid4()), para.id, para.para_id,
          act["activity_type"], json.dumps(act["content"]),
          act.get("difficulty", 2), act.get("generation_src","rule_based")))


def write_flashcard(db: sqlite3.Connection, para: Para, fc: dict):
    db.execute("""
        INSERT OR IGNORE INTO flashcards
            (id, paragraph_db_id, para_id, front, back, card_type, generation_src)
        VALUES (?,?,?,?,?,?,?)
    """, (str(uuid.uuid4()), para.id, para.para_id,
          fc["front"], fc["back"],
          fc.get("card_type","definition"), fc.get("generation_src","rule_based")))


def write_question(db: sqlite3.Connection, para: Para, q: dict):
    choices = q.get("choices", [])
    if not choices:
        raise ValueError(
            f"Question {para.para_id} {q['question_type']} has no answer choices: {q['question_text']}"
        )

    qid = str(uuid.uuid4())
    db.execute("""
        INSERT INTO quiz_questions
            (id, paragraph_db_id, para_id, question_text, question_type,
             explanation, difficulty, generation_src)
        VALUES (?,?,?,?,?,?,?,?)
    """, (qid, para.id, para.para_id, q["question_text"], q["question_type"],
          q.get("explanation",""), q.get("difficulty",2), q.get("generation_src", "local_auto")))
    for i, choice in enumerate(choices):
        db.execute("""
            INSERT INTO question_choices (id, question_id, choice_text, is_correct, sort_order)
            VALUES (?,?,?,?,?)
        """, (str(uuid.uuid4()), qid, choice["text"], int(choice.get("is_correct",False)), i))


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

class Progress:
    def __init__(self, total: int):
        self.total    = total
        self.done     = 0
        self.start    = time.time()
        self.rule_acts = 0
        self.ai_acts   = 0
        self.cards     = 0
        self.questions = 0
        self.api_calls = 0

    def update(self, para_id: str, r_acts: int, a_acts: int, fcs: int, qs: int):
        self.done      += 1
        self.rule_acts += r_acts
        self.ai_acts   += a_acts
        self.cards     += fcs
        self.questions += qs
        pct  = self.done / self.total * 100
        rate = self.done / max(time.time() - self.start, 1)
        eta  = (self.total - self.done) / rate if rate > 0 else 0
        bar  = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"\r  [{bar}] {pct:5.1f}%  {self.done}/{self.total}"
              f"  acts:{self.rule_acts+self.ai_acts}"
              f"  cards:{self.cards}"
              f"  Qs:{self.questions}"
              f"  eta:{eta:.0f}s  {para_id:<12}", end="", flush=True)

    def finish(self):
        elapsed = time.time() - self.start
        print(f"\n\n  Done in {elapsed:.1f}s")
        print(f"  Rule-based activities: {self.rule_acts}")
        print(f"  Enriched activities:   {self.ai_acts}")
        print(f"  Flashcards:            {self.cards}")
        print(f"  Quiz questions:        {self.questions}")
        print(f"  Batches processed:     {self.api_calls}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

async def generate_all(
    source_dir: Path,
    out_path:   Path,
    chapters:   list[int],
    resume:     bool,
    dry_run:    bool,
    publish_path: Optional[Path] = None,
):
    print(f"\n{'─'*60}")
    print(f"  ATC 7110.65 Curriculum Generator")
    print(f"  Source: {source_dir}")
    print(f"  Output: {out_path}")
    print(f"  Chapters: {chapters}  |  Resume: {resume}  |  Dry run: {dry_run}")
    if publish_path:
        print(f"  Publish: {publish_path}")
    print(f"{'─'*60}\n")

    if not resume:
        reset_sqlite_output(out_path)

    # Open DB
    db = open_db(out_path)

    # Load paragraphs
    print("1. Parsing source files…")
    paras = load_paragraphs(source_dir, chapters)

    # Filter if resuming
    if resume:
        done_ids = {row[0] for row in db.execute("SELECT para_id FROM generation_log WHERE status='complete'")}
        before   = len(paras)
        paras    = [p for p in paras if p.para_id not in done_ids]
        print(f"  Resuming: {before - len(paras)} already done, {len(paras)} remaining")

    if not paras:
        print("  Nothing to generate — all paragraphs already complete.")
        db.close()
        return

    prog = Progress(len(paras))

    # ── Phase 1: Write all paragraphs + rule-based content ─────────────────
    print(f"\n2. Rule-based extraction ({len(paras)} paragraphs)…")
    for para in paras:
        write_paragraph(db, para)

        r_acts = []
        # Rule-based activities
        r_acts += extract_phraseology_builder(para)
        r_acts += extract_sequence_steps(para)
        r_acts += extract_match_pairs(para)
        r_acts = _filter_rule_based_activities(para, r_acts)

        fcs = extract_flashcards(para)

        for act in r_acts:
            write_activity(db, para, act)
        for fc in fcs:
            write_flashcard(db, para, fc)

        prog.update(para.para_id, len(r_acts), 0, len(fcs), 0)

    db.commit()
    print("\n  Rule-based phase complete.")

    if dry_run:
        print("\n  [DRY RUN] Skipping local enrichment.")
        prog.finish()
        db.execute(f"INSERT OR REPLACE INTO meta VALUES ('dry_run','true')")
        db.commit()
        db.close()
        return

    # ── Phase 2: local enrichment ──────────────────────────────────────────
    print(f"\n3. Local enrichment (batched {BATCH_SIZE} paras/call)…")

    # Split into batches
    def batched(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i+n]

    # Paragraphs with phraseology or curated overrides for specific activity types
    phraseology_backfill_paras = [
        p for p in paras
        if (
            p.has_block('phraseology')
            or p.has_block('example')
            or _has_curated_activity_type(p, "phraseology_builder")
        )
        and db.execute(
            "SELECT COUNT(*) FROM activities WHERE para_id=? AND activity_type='phraseology_builder'",
            (p.para_id,),
        ).fetchone()[0] == 0
    ]
    sequence_steps_backfill_paras = [
        p for p in paras
        if _has_curated_activity_type(p, "sequence_steps")
        and db.execute(
            "SELECT COUNT(*) FROM activities WHERE para_id=? AND activity_type='sequence_steps'",
            (p.para_id,),
        ).fetchone()[0] == 0
    ]
    spot_the_error_paras = [
        p for p in paras
        if p.has_block('phraseology') or _has_curated_activity_type(p, "spot_the_error")
    ]
    readback_paras = [
        p for p in paras
        if p.has_block('phraseology') or _has_curated_activity_type(p, "readback_check")
    ]

    async def run_batch(batch_fn, batch_paras, label):
        results: dict[str, list[dict]] = {}
        for batch in batched(batch_paras, BATCH_SIZE):
            try:
                res = await batch_fn(batch)
                results.update(res)
                prog.api_calls += 1
            except Exception as e:
                for p in batch:
                    db.execute("""
                        INSERT OR REPLACE INTO generation_log
                            (para_id, status, errors)
                        VALUES (?,?,?)
                    """, (p.para_id, 'partial', json.dumps([f"{label}: {e}"])))
            await asyncio.sleep(0)
        return results

    # Phraseology builder backfill for example-only or curated phraseology paragraphs
    print("\n  → phraseology_builder_backfill…")
    pb_results = await run_batch(local_phraseology_builder_batch, phraseology_backfill_paras, "phraseology_builder")
    for pid, acts in pb_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(pb_results)} activities generated")

    # Curated sequence-steps replacements for paragraphs where rule-based steps were suppressed
    print("\n  → sequence_steps…")
    seq_results = await run_batch(local_sequence_steps_batch, sequence_steps_backfill_paras, "sequence_steps")
    for pid, acts in seq_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(seq_results)} activities generated")

    # Spot the error
    print("\n  → spot_the_error…")
    ste_results = await run_batch(local_spot_the_error_batch, spot_the_error_paras, "spot_the_error")
    for pid, acts in ste_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(ste_results)} activities generated")

    # Read-back check
    print("  → readback_check…")
    rb_results = await run_batch(local_readback_check_batch, readback_paras, "readback_check")
    for pid, acts in rb_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(rb_results)} activities generated")

    # Situation → action (all paragraphs)
    print("  → situation_action…")
    sit_results = await run_batch(local_situation_action_batch, paras, "situation_action")
    for pid, acts in sit_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(sit_results)} activities generated")

    # Directive checks for short imperative paragraphs
    print("  → directive_check…")
    directive_results = await run_batch(local_directive_check_batch, paras, "directive_check")
    for pid, acts in directive_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(directive_results)} activities generated")

    # Conditional procedure checks for rule paragraphs with explicit conditions
    print("  → conditional_rule_check…")
    conditional_results = await run_batch(local_conditional_rule_check_batch, paras, "conditional_rule_check")
    for pid, acts in conditional_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(conditional_results)} activities generated")

    # Short definitional paragraphs keyed to the paragraph title
    print("  → term_definition_check…")
    definition_results = await run_batch(local_term_definition_check_batch, paras, "term_definition_check")
    for pid, acts in definition_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(definition_results)} activities generated")

    # Document-control checks for admin/reference-style paragraphs
    print("  → document_control_check…")
    doc_control_results = await run_batch(local_document_control_check_batch, paras, "document_control_check")
    for pid, acts in doc_control_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(doc_control_results)} activities generated")

    # Requirement checks for explicit controller obligations and permissions
    print("  → requirement_check…")
    requirement_results = await run_batch(local_requirement_check_batch, paras, "requirement_check")
    for pid, acts in requirement_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(requirement_results)} activities generated")

    # Scope/responsibility checks for applicability and accountability statements
    print("  → scope_check…")
    scope_results = await run_batch(local_scope_check_batch, paras, "scope_check")
    for pid, acts in scope_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(scope_results)} activities generated")

    # Capability checks for system/equipment behavior and tool descriptions
    print("  → capability_check…")
    capability_results = await run_batch(local_capability_check_batch, paras, "capability_check")
    for pid, acts in capability_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(capability_results)} activities generated")

    print("  → reference_check skipped (citation drills are not part of the active study curriculum)")

    # Minima/separation checks for numeric rule paragraphs
    print("  → minima_rule_check…")
    minima_results = await run_batch(local_minima_rule_check_batch, paras, "minima_rule_check")
    for pid, acts in minima_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(minima_results)} activities generated")

    # Local-auto list drills are too prone to structural recall and weak negatives.
    # Keep curated list-membership activities only.
    list_paras = [p for p in paras if _has_curated_activity_type(p, "list_membership")]
    print("  → list_membership (curated only)…")
    list_results = await run_batch(local_list_membership_batch, list_paras, "list_membership")
    list_written = 0
    for pid, acts in list_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                if act.get("generation_src") != "curated":
                    continue
                write_activity(db, para, act)
                list_written += 1
    db.commit()
    print(f"     {list_written} activities generated")

    # Table lookups for simple threshold tables
    table_paras = [
        p for p in paras
        if "TBL" in p.text("body", "note", "exception").upper()
        or _has_curated_activity_type(p, "table_lookup")
    ]
    print("  → table_lookup…")
    table_results = await run_batch(local_table_lookup_batch, table_paras, "table_lookup")
    for pid, acts in table_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(table_results)} activities generated")

    # Example checks for example-heavy communication paragraphs
    example_paras = [
        p for p in paras
        if p.has_block("example") or _has_curated_activity_type(p, "example_check")
    ]
    print("  → example_check…")
    example_results = await run_batch(local_example_check_batch, example_paras, "example_check")
    for pid, acts in example_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(example_results)} activities generated")

    # Knowledge check fallback for paragraphs with thin activity coverage
    knowledge_check_paras = [
        p for p in paras
        if _has_curated_activity_type(p, "knowledge_check") or _activity_type_count(db, p.para_id) < 2
    ]
    print("  → knowledge_check…")
    kc_results = await run_batch(local_knowledge_check_batch, knowledge_check_paras, "knowledge_check")
    for pid, acts in kc_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for act in acts:
                write_activity(db, para, act)
    db.commit()
    print(f"     {len(kc_results)} activities generated")

    # Local flashcard backfill for paragraphs that did not get rule-based cards
    flashcard_paras = [
        p for p in paras
        if db.execute("SELECT COUNT(*) FROM flashcards WHERE para_id=?", (p.para_id,)).fetchone()[0] == 0
    ]
    print("  → flashcard_backfill…")
    card_results = await run_batch(local_flashcards_batch, flashcard_paras, "flashcard_backfill")
    total_cards = 0
    for pid, cards in card_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for card in cards:
                write_flashcard(db, para, card)
                total_cards += 1
    db.commit()
    print(f"     {total_cards} flashcards generated")

    # Quiz questions (all paragraphs)
    print("  → quiz_questions…")
    quiz_results = await run_batch(local_quiz_questions_batch, paras, "quiz_questions")
    total_qs = 0
    for pid, qs in quiz_results.items():
        para = next((p for p in paras if p.para_id == pid), None)
        if para:
            for q in qs:
                write_question(db, para, q)
                total_qs += 1
    db.commit()
    print(f"     {total_qs} questions generated")

    # ── Phase 3: Log completion ─────────────────────────────────────────────
    print("\n4. Writing generation log…")
    for para in paras:
        acts = db.execute(
            "SELECT COUNT(*), generation_src FROM activities WHERE para_id=? GROUP BY generation_src",
            (para.para_id,)
        ).fetchall()
        rule_c = sum(r[0] for r in acts if r[1] == 'rule_based')
        ai_c   = sum(r[0] for r in acts if r[1] in ('ai_auto', 'local_auto', 'curated'))
        fc_c   = db.execute("SELECT COUNT(*) FROM flashcards WHERE para_id=?", (para.para_id,)).fetchone()[0]
        q_c    = db.execute("SELECT COUNT(*) FROM quiz_questions WHERE para_id=?", (para.para_id,)).fetchone()[0]
        db.execute("""
            INSERT OR REPLACE INTO generation_log
                (para_id, status, rule_acts, ai_acts, flashcards, questions)
            VALUES (?,?,?,?,?,?)
        """, (para.para_id, 'complete', rule_c, ai_c, fc_c, q_c))

    db.commit()

    # ── Final stats ─────────────────────────────────────────────────────────
    totals = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM paragraphs)   AS paras,
            (SELECT COUNT(*) FROM activities)   AS acts,
            (SELECT COUNT(*) FROM flashcards)   AS cards,
            (SELECT COUNT(*) FROM quiz_questions) AS qs,
            (SELECT COUNT(*) FROM question_choices) AS choices
    """).fetchone()
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    by_type = db.execute("""
        SELECT activity_type, COUNT(*) FROM activities GROUP BY activity_type ORDER BY activity_type
    """).fetchall()
    rule_total = db.execute("""
        SELECT COUNT(*) FROM activities WHERE generation_src='rule_based'
    """).fetchone()[0]
    enriched_total = db.execute("""
        SELECT COUNT(*) FROM activities WHERE generation_src IN ('ai_auto', 'local_auto', 'curated')
    """).fetchone()[0]

    prog.rule_acts = rule_total
    prog.ai_acts = enriched_total
    prog.cards = totals[2]
    prog.questions = totals[3]

    print(f"\n{'─'*60}")
    print(f"  curriculum.db  →  {out_path}")
    print(f"  Size: {out_path.stat().st_size / 1024:.0f} KB")
    print(f"\n  Paragraphs:      {totals[0]}")
    print(f"  Activities:      {totals[1]}")
    print(f"  Flashcards:      {totals[2]}")
    print(f"  Quiz questions:  {totals[3]}")
    print(f"  Answer choices:  {totals[4]}")
    print(f"\n  Activities by type:")
    for atype, count in by_type:
        print(f"    {atype:<25} {count}")
    print(f"{'─'*60}\n")

    prog.api_calls = prog.api_calls  # already tracked
    prog.finish()
    if publish_path:
        published = publish_db(out_path, publish_path)
        print(f"  Published DB: {published}")
    db.close()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate ATC 7110.65 curriculum database")
    ap.add_argument("--source",  default="/mnt/project",    help="Directory with chapter ZIP/PDF files")
    ap.add_argument("--out",     default="curriculum.db",   help="Output SQLite path")
    ap.add_argument("--chapter", type=int, action="append", help="Chapter(s) to process (default: auto-detect from source)")
    ap.add_argument("--resume",  action="store_true",       help="Skip already-completed paragraphs")
    ap.add_argument("--dry-run", action="store_true",       help="Rule-based only; skip local enrichment")
    ap.add_argument("--publish", help="Copy finished DB into a frontend/public directory or specific .db path")
    args = ap.parse_args()

    source_dir = Path(args.source)
    chapters = args.chapter or discover_available_chapters(source_dir) or [2, 3, 4]
    asyncio.run(generate_all(
        source_dir = source_dir,
        out_path   = Path(args.out),
        chapters   = chapters,
        resume     = args.resume,
        dry_run    = args.dry_run,
        publish_path = Path(args.publish) if args.publish else None,
    ))


if __name__ == "__main__":
    main()
