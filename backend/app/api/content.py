"""
Content API
Serves the 7110.65 content hierarchy and search.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..models.orm import OrderVersion, Chapter, Section, Paragraph, ContentBlock, Tag
from ..services.db import get_db

router = APIRouter()


# ── Versions ──────────────────────────────────────────────────────────────────

@router.get("/versions")
def list_versions(db: Session = Depends(get_db)):
    """List all imported 7110.65 editions."""
    return db.query(OrderVersion).order_by(OrderVersion.effective_date.desc()).all()


@router.get("/versions/current")
def current_version(db: Session = Depends(get_db)):
    v = db.query(OrderVersion).filter(OrderVersion.is_current == True).first()
    if not v:
        raise HTTPException(404, "No current version set")
    return v


# ── Chapters ──────────────────────────────────────────────────────────────────

@router.get("/chapters")
def list_chapters(
    version_id: UUID | None = None,
    db: Session = Depends(get_db)
):
    """List all chapters, defaulting to the current version."""
    q = db.query(Chapter)
    if version_id:
        q = q.filter(Chapter.version_id == version_id)
    else:
        current = db.query(OrderVersion).filter(OrderVersion.is_current == True).first()
        if current:
            q = q.filter(Chapter.version_id == current.id)
    return q.order_by(Chapter.sort_order).all()


@router.get("/chapters/{chapter_id}")
def get_chapter(chapter_id: UUID, db: Session = Depends(get_db)):
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not ch:
        raise HTTPException(404, "Chapter not found")
    return ch


# ── Sections ──────────────────────────────────────────────────────────────────

@router.get("/chapters/{chapter_id}/sections")
def list_sections(chapter_id: UUID, db: Session = Depends(get_db)):
    return (
        db.query(Section)
        .filter(Section.chapter_id == chapter_id)
        .order_by(Section.sort_order)
        .all()
    )


# ── Paragraphs ────────────────────────────────────────────────────────────────

@router.get("/paragraphs")
def list_paragraphs(
    section_id: UUID | None = None,
    chapter_id: UUID | None = None,
    version_id: UUID | None = None,
    tag: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Flexible paragraph listing with optional filtering by section,
    chapter, version, or tag name.
    """
    q = db.query(Paragraph)
    if section_id:
        q = q.filter(Paragraph.section_id == section_id)
    if chapter_id:
        q = q.join(Section).filter(Section.chapter_id == chapter_id)
    if version_id:
        q = q.filter(Paragraph.version_id == version_id)
    if tag:
        t = db.query(Tag).filter(Tag.name == tag).first()
        if t:
            q = q.join(Paragraph.tags).filter_by(tag_id=t.id)
    return q.order_by(Paragraph.sort_order).offset(skip).limit(limit).all()


@router.get("/paragraphs/{para_id_str}")
def get_paragraph_by_id(
    para_id_str: str,
    version_id: UUID | None = None,
    db: Session = Depends(get_db)
):
    """
    Look up a paragraph by its canonical ID (e.g. '2-1-6').
    Returns the current version unless version_id is specified.
    """
    q = db.query(Paragraph).filter(Paragraph.para_id == para_id_str)
    if version_id:
        q = q.filter(Paragraph.version_id == version_id)
    else:
        current = db.query(OrderVersion).filter(OrderVersion.is_current == True).first()
        if current:
            q = q.filter(Paragraph.version_id == current.id)
    para = q.first()
    if not para:
        raise HTTPException(404, f"Paragraph {para_id_str} not found")
    return para


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search")
def search_content(
    q: str = Query(..., min_length=2, description="Search terms"),
    version_id: UUID | None = None,
    block_type: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Full-text search across content blocks using PostgreSQL trigram similarity.
    Returns matching content blocks with their parent paragraph info.
    """
    from sqlalchemy import func, text

    query = db.query(ContentBlock, Paragraph).join(
        Paragraph, ContentBlock.paragraph_id == Paragraph.id
    )

    if version_id:
        query = query.filter(ContentBlock.version_id == version_id)
    if block_type:
        query = query.filter(ContentBlock.block_type == block_type)

    # Trigram similarity search
    query = query.filter(
        func.similarity(ContentBlock.content, q) > 0.1
    ).order_by(
        func.similarity(ContentBlock.content, q).desc()
    ).limit(25)

    results = []
    for block, para in query.all():
        results.append({
            "para_id":    para.para_id,
            "para_title": para.title,
            "block_type": block.block_type,
            "content":    block.content[:300],
            "score":      None  # populated by the DB
        })
    return results


# ── Tags ──────────────────────────────────────────────────────────────────────

@router.get("/tags")
def list_tags(category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Tag)
    if category:
        q = q.filter(Tag.category == category)
    return q.order_by(Tag.name).all()
