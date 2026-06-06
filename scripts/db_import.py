"""
db_import.py
============
Takes the JSON output from pipeline.py and upserts it into PostgreSQL.

Usage:
    python scripts/db_import.py /tmp/7110_parsed.json \
        --edition "7110.65BB" \
        --effective-date 2025-02-20 \
        --set-current

This is idempotent: re-running with the same edition will UPDATE existing
records rather than creating duplicates, making it safe to re-import after
pipeline improvements without wiping user progress or quiz banks.
"""

import json
import argparse
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.app.models.orm import (
    Base, OrderVersion, Chapter, Section, Paragraph,
    ContentBlock, Tag, ParagraphTag, CrossReference, IngestionRun
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Pre-defined tags to seed
SEED_TAGS = [
    # Facility types
    {"name": "TRACON",    "category": "facility_type"},
    {"name": "ARTCC",     "category": "facility_type"},
    {"name": "Tower",     "category": "facility_type"},
    {"name": "FSS",       "category": "facility_type"},
    # Topics
    {"name": "separation",  "category": "topic"},
    {"name": "radar",       "category": "topic"},
    {"name": "IFR",         "category": "topic"},
    {"name": "VFR",         "category": "topic"},
    {"name": "phraseology", "category": "topic"},
    {"name": "emergencies", "category": "topic"},
    {"name": "weather",     "category": "topic"},
    {"name": "coordination","category": "topic"},
    {"name": "runway",      "category": "topic"},
    {"name": "oceanic",     "category": "topic"},
    {"name": "RNAV",        "category": "topic"},
    # Difficulty
    {"name": "basic",        "category": "difficulty"},
    {"name": "intermediate", "category": "difficulty"},
    {"name": "advanced",     "category": "difficulty"},
]


def get_engine(db_url: str):
    return create_engine(db_url, echo=False)


def seed_tags(session: Session) -> dict[str, Tag]:
    """Ensure all standard tags exist; return name→Tag map."""
    tag_map: dict[str, Tag] = {}
    for t in SEED_TAGS:
        existing = session.query(Tag).filter_by(name=t["name"]).first()
        if not existing:
            existing = Tag(**t)
            session.add(existing)
            session.flush()
        tag_map[t["name"]] = existing
    return tag_map


def upsert_version(
    session: Session,
    edition: str,
    effective_date: date,
    set_current: bool,
    source_file: str
) -> OrderVersion:
    v = session.query(OrderVersion).filter_by(edition=edition).first()
    if not v:
        v = OrderVersion(edition=edition, effective_date=effective_date)
        session.add(v)
        session.flush()
        log.info(f"Created version: {edition}")
    else:
        log.info(f"Updating existing version: {edition}")

    if set_current:
        # Clear existing current flag
        session.query(OrderVersion).filter(OrderVersion.is_current == True).update(
            {"is_current": False}
        )
        v.is_current = True

    return v


def import_chapter(
    session: Session,
    ch_data: dict,
    version: OrderVersion,
    tag_map: dict[str, Tag]
) -> tuple[int, int]:
    """Import one chapter. Returns (sections_count, paragraphs_count)."""

    ch = session.query(Chapter).filter_by(
        version_id=version.id,
        chapter_number=ch_data["chapter_number"]
    ).first()

    if not ch:
        ch = Chapter(
            version_id=version.id,
            chapter_number=ch_data["chapter_number"],
            title=ch_data["title"],
            sort_order=ch_data["sort_order"]
        )
        session.add(ch)
        session.flush()
    else:
        ch.title = ch_data["title"]

    total_paras = 0

    for sec_data in ch_data.get("sections", []):
        sec = session.query(Section).filter_by(
            chapter_id=ch.id,
            section_number=sec_data["section_number"]
        ).first()

        if not sec:
            sec = Section(
                chapter_id=ch.id,
                version_id=version.id,
                section_number=sec_data["section_number"],
                title=sec_data["title"],
                sort_order=sec_data["sort_order"]
            )
            session.add(sec)
            session.flush()
        else:
            sec.title = sec_data["title"]

        for para_data in sec_data.get("paragraphs", []):
            para = session.query(Paragraph).filter_by(
                version_id=version.id,
                para_id=para_data["para_id"]
            ).first()

            if not para:
                para = Paragraph(
                    section_id=sec.id,
                    version_id=version.id,
                    para_id=para_data["para_id"],
                    title=para_data.get("title"),
                    page_number=para_data.get("page_number"),
                    page_uuid=para_data.get("page_uuid"),
                    has_visual=para_data.get("has_visual", False),
                    sort_order=para_data["sort_order"],
                    change_type="new"
                )
                session.add(para)
                session.flush()
            else:
                para.title = para_data.get("title")
                para.page_number = para_data.get("page_number")
                para.has_visual = para_data.get("has_visual", False)

            # Replace content blocks
            session.query(ContentBlock).filter_by(paragraph_id=para.id).delete()
            for block_data in para_data.get("blocks", []):
                block = ContentBlock(
                    paragraph_id=para.id,
                    version_id=version.id,
                    block_type=block_data["block_type"],
                    sequence=block_data["sequence"],
                    label=block_data.get("label", ""),
                    content=block_data["content"]
                )
                session.add(block)

            # Apply auto-tags
            for tag_name in para_data.get("auto_tags", []):
                if tag_name in tag_map:
                    existing_pt = session.query(ParagraphTag).filter_by(
                        paragraph_id=para.id, tag_id=tag_map[tag_name].id
                    ).first()
                    if not existing_pt:
                        session.add(ParagraphTag(
                            paragraph_id=para.id,
                            tag_id=tag_map[tag_name].id,
                            auto_tagged=True
                        ))

            total_paras += 1

    session.flush()
    return len(ch_data.get("sections", [])), total_paras


def run_import(
    db_url: str,
    json_path: Path,
    edition: str,
    effective_date: date,
    set_current: bool = True
):
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)  # Create tables if they don't exist

    with open(json_path, encoding='utf-8') as f:
        doc = json.load(f)

    with Session(engine) as session:
        run = IngestionRun(
            version_id=None,  # filled after version upsert
            source_file=str(json_path),
            status="running"
        )

        try:
            tag_map = seed_tags(session)
            version = upsert_version(session, edition, effective_date, set_current, str(json_path))
            run.version_id = version.id
            session.add(run)
            session.flush()

            total_sections = 0
            total_paras = 0

            for ch_data in doc.get("chapters", []):
                secs, paras = import_chapter(session, ch_data, version, tag_map)
                total_sections += secs
                total_paras += paras
                log.info(f"  Chapter {ch_data['chapter_number']}: {secs} sections, {paras} paragraphs")

            run.chapters_parsed = len(doc.get("chapters", []))
            run.paragraphs_parsed = total_paras
            run.status = "complete"
            run.errors = doc.get("errors", [])

            session.commit()
            log.info(f"\nImport complete: {total_paras} paragraphs across {len(doc['chapters'])} chapters")

        except Exception as e:
            session.rollback()
            run.status = "failed"
            run.errors = [str(e)]
            log.error(f"Import failed: {e}")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import 7110.65 JSON into PostgreSQL")
    parser.add_argument("json_file", help="Path to pipeline output JSON")
    parser.add_argument("--db-url", default="postgresql://atc:atc@localhost:5432/atc_platform")
    parser.add_argument("--edition", default="7110.65BB")
    parser.add_argument("--effective-date", default="2025-02-20")
    parser.add_argument("--set-current", action="store_true", default=True)
    args = parser.parse_args()

    run_import(
        db_url=args.db_url,
        json_path=Path(args.json_file),
        edition=args.edition,
        effective_date=date.fromisoformat(args.effective_date),
        set_current=args.set_current
    )
