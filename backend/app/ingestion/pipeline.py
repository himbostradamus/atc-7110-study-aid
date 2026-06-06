"""
7110.65 Content Ingestion Pipeline
====================================
Parses the FAA Order JO 7110.65 ZIP packages (per-chapter) and extracts
structured content into a normalized JSON format ready for database import.

Each source file is a ZIP containing:
  - {page}.txt  — extracted text per page
  - {page}.jpeg — page image
  - manifest.json — page metadata (dimensions, has_visual_content, page_uuid)

Pipeline stages:
  1. Unpack  — extract ZIP, load manifest
  2. Assemble — concatenate page text in order
  3. Parse    — identify chapters, sections, paragraphs, content blocks
  4. Tag      — auto-apply tags based on content patterns
  5. Link     — resolve cross-references between paragraphs
  6. Output   — write structured JSON (or insert into DB via SQLAlchemy)
"""

import re
import json
import zipfile
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES  (mirror the DB schema)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ContentBlock:
    block_type: str          # body | note | phraseology | example | reference | exception | interpretation
    sequence: int
    label: str               # "a.", "1.", "NOTE 1", etc.
    content: str


@dataclass
class Paragraph:
    para_id: str             # canonical e.g. "2-1-6"
    title: str               # ALL-CAPS title if present
    page_number: int
    page_uuid: str
    has_visual: bool
    sort_order: int
    blocks: list[ContentBlock] = field(default_factory=list)
    raw_text: str = ""
    auto_tags: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)  # raw para strings


@dataclass
class Section:
    section_number: int      # e.g. 1
    title: str               # e.g. "General"
    sort_order: int
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass
class Chapter:
    chapter_number: int      # e.g. 2
    title: str               # e.g. "General Control"
    sort_order: int
    sections: list[Section] = field(default_factory=list)


@dataclass
class ParsedDocument:
    edition: str             # e.g. "7110.65BB"
    effective_date: str      # e.g. "2025-02-20"
    source_file: str
    chapters: list[Chapter] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS  (tuned to 7110.65 formatting)
# ─────────────────────────────────────────────────────────────────────────────

# Paragraph number:  2−1−6.   or  2-1-6.   (em-dash and hyphen variants)
RE_PARA_ID = re.compile(
    r'^(\d+[−\-]\d+[−\-]\d+)\.\s*(.*?)$',
    re.MULTILINE
)

# Section header (bold all-caps short title on its own line, preceded by section number)
# e.g.  "2−1. GENERAL"
RE_SECTION = re.compile(
    r'^(\d+[−\-]\d+)\.\s+([A-Z][A-Z /\(\)\-]+)$',
    re.MULTILINE
)

# Content block markers
RE_NOTE       = re.compile(r'^NOTE[−\-]?\s*$|^NOTE[−\-]\s*\n', re.MULTILINE)
RE_PHRASEOLOGY = re.compile(r'^PHRASEOLOGY[−\-]\s*$', re.MULTILINE)
RE_EXAMPLE    = re.compile(r'^EXAMPLE[−\-]\s*$', re.MULTILINE)
RE_REFERENCE  = re.compile(r'^REFERENCE[−\-]\s*$', re.MULTILINE)
RE_EXCEPTION  = re.compile(r'^EXCEPTION[.\-]', re.MULTILINE)
RE_INTERPRET  = re.compile(r'^INTERPRETATION[−\-]\s*$', re.MULTILINE)

# Cross-reference pattern inside REFERENCE− blocks
RE_XREF = re.compile(
    r'(?:JO\s+)?7110\.65[A-Z]?,?\s+Para\s+([\d\-−]+)',
    re.IGNORECASE
)

# Page header/footer noise to strip
RE_PAGE_NOISE = re.compile(
    r'^\s*(?:\d+/\d+/\d+\s+JO\s+7110\.\d+[A-Z]+.*|JO\s+7110\.\d+[A-Z]+\s+\d+/\d+/\d+.*|[A-Za-z\s]+\d+[−\-]\d+[−\-]\d+)\s*$',
    re.MULTILINE
)

# Auto-tag keyword map: tag_name → list of trigger patterns
AUTO_TAG_PATTERNS: dict[str, list[str]] = {
    "separation":     [r'separat', r'spacing', r'distance'],
    "radar":          [r'radar', r'MSAW', r'conflict alert', r'data block'],
    "IFR":            [r'\bIFR\b', r'instrument flight', r'clearance'],
    "VFR":            [r'\bVFR\b', r'visual flight'],
    "phraseology":    [r'PHRASEOLOGY'],
    "emergencies":    [r'emergency', r'mayday', r'distress', r'safety alert'],
    "weather":        [r'weather', r'pirep', r'SIGMET', r'AIRMET', r'turbulence'],
    "coordination":   [r'coordinat', r'handoff', r'point out'],
    "TRACON":         [r'approach control', r'TRACON', r'terminal'],
    "ARTCC":          [r'\bARTCC\b', r'en route', r'center'],
    "Tower":          [r'\btower\b', r'ATCT', r'local control'],
    "runway":         [r'\brunway\b', r'LUAW', r'land and hold short', r'LAHSO'],
    "oceanic":        [r'oceanic', r'MNPS', r'PBCS'],
    "RNAV":           [r'\bRNAV\b', r'\bGPS\b', r'\bWAAS\b', r'GNSS'],
}


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1: UNPACK
# ─────────────────────────────────────────────────────────────────────────────

def unpack_zip(zip_path: Path) -> tuple[dict, dict[int, str], dict[int, dict]]:
    """
    Returns:
      manifest   — parsed manifest.json
      page_texts — {page_number: text_content}
      page_meta  — {page_number: page metadata dict from manifest}
    """
    with zipfile.ZipFile(zip_path, 'r') as z:
        manifest = json.loads(z.read('manifest.json'))
        page_texts = {}
        page_meta = {}

        for page in manifest['pages']:
            n = page['page_number']
            page_meta[n] = page
            try:
                page_texts[n] = z.read(page['text']['path']).decode('utf-8', errors='replace')
            except KeyError:
                page_texts[n] = ""

    log.info(f"Unpacked {zip_path.name}: {len(page_texts)} pages")
    return manifest, page_texts, page_meta


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: ASSEMBLE
# ─────────────────────────────────────────────────────────────────────────────

def assemble_text(page_texts: dict[int, str]) -> list[tuple[int, str]]:
    """
    Returns a list of (page_number, cleaned_text) in page order.
    Strips header/footer noise but keeps a page boundary marker so we
    can later trace each paragraph back to its source page.
    """
    pages = []
    for n in sorted(page_texts.keys()):
        raw = page_texts[n]
        # Normalize em-dashes used as hyphens in para IDs
        cleaned = raw.replace('\r\n', '\n').replace('\r', '\n')
        pages.append((n, cleaned))
    return pages


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3: PARSE
# ─────────────────────────────────────────────────────────────────────────────

def classify_block_type(line: str) -> Optional[str]:
    """Identify if a line is a content block marker."""
    stripped = line.strip()
    if RE_NOTE.match(stripped):        return 'note'
    if RE_PHRASEOLOGY.match(stripped): return 'phraseology'
    if RE_EXAMPLE.match(stripped):     return 'example'
    if RE_REFERENCE.match(stripped):   return 'reference'
    if RE_EXCEPTION.match(stripped):   return 'exception'
    if RE_INTERPRET.match(stripped):   return 'interpretation'
    return None


def extract_cross_references(text: str) -> list[str]:
    """Pull all paragraph cross-references from a text block."""
    refs = []
    for m in RE_XREF.finditer(text):
        raw = m.group(1).replace('−', '-').strip()
        refs.append(raw)
    return list(set(refs))


def parse_paragraph_blocks(raw_text: str) -> list[ContentBlock]:
    """
    Split a paragraph's raw text into typed ContentBlocks.

    Strategy: scan lines looking for block-type markers. When found,
    start accumulating text for that block type until the next marker.
    """
    blocks = []
    lines = raw_text.split('\n')
    if lines and RE_PARA_ID.match(lines[0].strip()):
        lines = lines[1:]

    current_type = 'body'
    current_label = ''
    current_lines: list[str] = []
    seq = 0

    def flush():
        nonlocal seq, current_lines, current_type, current_label
        content = '\n'.join(current_lines).strip()
        if content:
            blocks.append(ContentBlock(
                block_type=current_type,
                sequence=seq,
                label=current_label,
                content=content
            ))
            seq += 1
        current_lines = []

    for line in lines:
        btype = classify_block_type(line)
        if btype:
            flush()
            current_type = btype
            current_label = line.strip().rstrip('-−').strip()
        else:
            current_lines.append(line)

    flush()
    return blocks


def parse_chapter_text(
    chapter_number: int,
    pages: list[tuple[int, str]],
    page_meta: dict[int, dict]
) -> Chapter:
    """
    Parse all pages belonging to a chapter into a Chapter object.

    Identifies:
     - Section boundaries (X−Y. TITLE pattern)
     - Paragraph boundaries (X−Y−Z. pattern)
     - Content blocks within each paragraph
    """
    # Concatenate all page text with page markers
    full_text_parts = []
    page_boundary_offsets: dict[int, int] = {}  # offset → page_number

    char_offset = 0
    for (pn, text) in pages:
        page_boundary_offsets[char_offset] = pn
        full_text_parts.append(text)
        char_offset += len(text) + 1

    full_text = '\n'.join([t for _, t in pages])

    # Find all paragraph locations
    para_matches = list(RE_PARA_ID.finditer(full_text))
    section_matches = list(RE_SECTION.finditer(full_text))

    # Build section lookup: para_id prefix → section
    # e.g. "2-1" → Section(section_number=1, ...)
    sections: dict[str, Section] = {}
    section_sort = 0

    for sm in section_matches:
        sec_id = sm.group(1).replace('−', '-')
        sec_title = sm.group(2).strip()
        parts = sec_id.split('-')
        if len(parts) == 2:
            sec_num = int(parts[1])
            if sec_id not in sections:
                sections[sec_id] = Section(
                    section_number=sec_num,
                    title=sec_title,
                    sort_order=section_sort
                )
                section_sort += 1

    # Determine which page a text offset belongs to
    sorted_offsets = sorted(page_boundary_offsets.keys())

    def offset_to_page(offset: int) -> int:
        for i in range(len(sorted_offsets) - 1, -1, -1):
            if offset >= sorted_offsets[i]:
                return page_boundary_offsets[sorted_offsets[i]]
        return 1

    # Parse paragraphs
    para_sort = 0
    for i, pm in enumerate(para_matches):
        raw_para_id = pm.group(1).replace('−', '-')
        para_title = pm.group(2).strip()

        # Text for this paragraph = from here to next paragraph (or end)
        start = pm.start()
        end = para_matches[i + 1].start() if i + 1 < len(para_matches) else len(full_text)
        raw_text = full_text[start:end].strip()

        # Determine which section this belongs to
        parts = raw_para_id.split('-')
        if len(parts) >= 2:
            sec_key = f"{parts[0]}-{parts[1]}"
        else:
            sec_key = f"{chapter_number}-1"

        if sec_key not in sections:
            sections[sec_key] = Section(
                section_number=int(parts[1]) if len(parts) >= 2 else 0,
                title="Unknown",
                sort_order=section_sort
            )
            section_sort += 1

        page_num = offset_to_page(start)
        meta = page_meta.get(page_num, {})

        para = Paragraph(
            para_id=raw_para_id,
            title=para_title,
            page_number=page_num,
            page_uuid=meta.get('page_uuid', ''),
            has_visual=meta.get('has_visual_content', False),
            sort_order=para_sort,
            raw_text=raw_text,
            blocks=parse_paragraph_blocks(raw_text),
            cross_references=extract_cross_references(raw_text)
        )
        sections[sec_key].paragraphs.append(para)
        para_sort += 1

    # Determine chapter title from first section or first page header
    chapter_title = _infer_chapter_title(full_text, chapter_number)

    chapter = Chapter(
        chapter_number=chapter_number,
        title=chapter_title,
        sort_order=chapter_number - 1,
        sections=list(sections.values())
    )

    log.info(
        f"Chapter {chapter_number}: {len(sections)} sections, "
        f"{sum(len(s.paragraphs) for s in sections.values())} paragraphs"
    )
    return chapter


def _infer_chapter_title(text: str, chapter_number: int) -> str:
    """Try to extract the chapter title from the first page of text."""
    # 7110.65 uses "Chapter X − TITLE" format in the TOC
    pattern = re.compile(
        rf'Chapter\s+{chapter_number}\s*[−\-]\s*([A-Z][A-Z\s,/]+)',
        re.IGNORECASE
    )
    m = pattern.search(text[:3000])
    if m:
        return m.group(1).strip().title()

    # Fallback: known chapter titles
    known = {
        1: "Prefatory Information",
        2: "General Control",
        3: "Air Traffic Control – Terminal",
        4: "IFR",
        5: "Radar",
        6: "Nonradar",
        7: "Visual Separation",
        8: "Offshore/Oceanic Procedures",
        9: "Emergencies",
        10: "Special Operations",
        11: "Military",
        12: "NMAC/Deviation Reporting",
        14: "North Atlantic Operations",
        15: "Miscellaneous",
    }
    return known.get(chapter_number, f"Chapter {chapter_number}")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4: AUTO-TAG
# ─────────────────────────────────────────────────────────────────────────────

def auto_tag_paragraph(para: Paragraph) -> list[str]:
    """Apply keyword-based tags to a paragraph."""
    text = para.raw_text.lower()
    tags = []
    for tag, patterns in AUTO_TAG_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                tags.append(tag)
                break
    return tags


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

CHAPTER_FILE_MAP = {
    # Maps chapter number → source ZIP filename pattern
    2: "7110_65BB_Ch2_GeneralControl",
    3: "7110_65BB_Ch3_AirTrafficControlTerminal",
    4: "7110_65BB_Ch4_IFR",
}


def run_pipeline(
    source_dir: Path,
    edition: str = "7110.65BB",
    effective_date: str = "2025-02-20",
    output_path: Optional[Path] = None,
) -> ParsedDocument:
    """
    Full pipeline entry point.

    Args:
        source_dir:     Directory containing the ZIP chapter files
        edition:        Order edition string e.g. "7110.65BB"
        effective_date: ISO date string
        output_path:    If provided, write JSON output here

    Returns:
        ParsedDocument with all extracted content
    """
    doc = ParsedDocument(
        edition=edition,
        effective_date=effective_date,
        source_file=str(source_dir)
    )

    for chapter_num, file_stem in CHAPTER_FILE_MAP.items():
        # Accept either .pdf or .zip extension (the files are ZIPs regardless)
        zip_path = None
        for ext in ['.pdf', '.zip']:
            candidate = source_dir / f"{file_stem}{ext}"
            if candidate.exists():
                zip_path = candidate
                break

        if not zip_path:
            msg = f"Source file not found for chapter {chapter_num}: {file_stem}.*"
            log.warning(msg)
            doc.errors.append(msg)
            continue

        log.info(f"Processing chapter {chapter_num} from {zip_path.name}")
        try:
            manifest, page_texts, page_meta = unpack_zip(zip_path)
            pages = assemble_text(page_texts)
            chapter = parse_chapter_text(chapter_num, pages, page_meta)

            # Auto-tag all paragraphs
            for section in chapter.sections:
                for para in section.paragraphs:
                    para.auto_tags = auto_tag_paragraph(para)

            doc.chapters.append(chapter)

        except Exception as e:
            msg = f"Failed to parse chapter {chapter_num}: {e}"
            log.error(msg)
            doc.errors.append(msg)

    _resolve_cross_references(doc)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(doc), f, indent=2, ensure_ascii=False)
        log.info(f"Output written to {output_path}")

    return doc


def _resolve_cross_references(doc: ParsedDocument):
    """
    Build a lookup of all para_ids in the doc and mark cross-references
    as resolved or unresolved.
    """
    all_para_ids = set()
    for chapter in doc.chapters:
        for section in chapter.sections:
            for para in section.paragraphs:
                all_para_ids.add(para.para_id)

    unresolved = 0
    for chapter in doc.chapters:
        for section in chapter.sections:
            for para in section.paragraphs:
                resolved = []
                for ref in para.cross_references:
                    if ref in all_para_ids:
                        resolved.append(ref)
                    else:
                        unresolved += 1
                para.cross_references = resolved

    log.info(f"Cross-reference resolution: {unresolved} unresolved (expected — other chapters not yet imported)")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/mnt/project")
    out    = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/7110_parsed.json")

    result = run_pipeline(source_dir=source, output_path=out)

    total_paras = sum(
        len(s.paragraphs)
        for ch in result.chapters
        for s in ch.sections
    )
    print(f"\n{'='*50}")
    print(f"Edition:    {result.edition}")
    print(f"Chapters:   {len(result.chapters)}")
    print(f"Paragraphs: {total_paras}")
    print(f"Errors:     {len(result.errors)}")
    if result.errors:
        for e in result.errors:
            print(f"  - {e}")
    print(f"Output:     {out}")
