"""
SQLAlchemy ORM Models
Mirrors schema.sql — used by FastAPI routes and the ingestion pipeline
to read/write the database.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, SmallInteger, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Enum as SAEnum


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    student    = "student"
    instructor = "instructor"
    admin      = "admin"

class BlockType(str, PyEnum):
    body           = "body"
    note           = "note"
    phraseology    = "phraseology"
    example        = "example"
    reference      = "reference"
    exception      = "exception"
    interpretation = "interpretation"

class ChangeType(str, PyEnum):
    new       = "new"
    modified  = "modified"
    unchanged = "unchanged"
    deleted   = "deleted"

class QuestionType(str, PyEnum):
    multiple_choice = "multiple_choice"
    true_false      = "true_false"
    fill_blank      = "fill_blank"
    ordering        = "ordering"


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT
# ─────────────────────────────────────────────────────────────────────────────

class OrderVersion(Base):
    __tablename__ = "order_versions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edition        = Column(String(20), nullable=False, unique=True)
    effective_date = Column(Date, nullable=False)
    is_current     = Column(Boolean, nullable=False, default=False)
    supersedes_id  = Column(UUID(as_uuid=True), ForeignKey("order_versions.id"), nullable=True)
    notes          = Column(Text)
    imported_at    = Column(DateTime, default=datetime.utcnow)
    created_at     = Column(DateTime, default=datetime.utcnow)

    chapters       = relationship("Chapter", back_populates="version", cascade="all, delete-orphan")
    supersedes     = relationship("OrderVersion", remote_side="OrderVersion.id")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("version_id", "chapter_number"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id     = Column(UUID(as_uuid=True), ForeignKey("order_versions.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title          = Column(String(255), nullable=False)
    sort_order     = Column(Integer, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    version        = relationship("OrderVersion", back_populates="chapters")
    sections       = relationship("Section", back_populates="chapter", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("chapter_id", "section_number"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id     = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    version_id     = Column(UUID(as_uuid=True), ForeignKey("order_versions.id", ondelete="CASCADE"), nullable=False)
    section_number = Column(Integer, nullable=False)
    title          = Column(String(255), nullable=False)
    sort_order     = Column(Integer, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    chapter        = relationship("Chapter", back_populates="sections")
    paragraphs     = relationship("Paragraph", back_populates="section", cascade="all, delete-orphan")


class Paragraph(Base):
    __tablename__ = "paragraphs"
    __table_args__ = (UniqueConstraint("version_id", "para_id"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id     = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    version_id     = Column(UUID(as_uuid=True), ForeignKey("order_versions.id", ondelete="CASCADE"), nullable=False)
    para_id        = Column(String(30), nullable=False)
    title          = Column(String(500))
    page_number    = Column(Integer)
    page_uuid      = Column(String(50))
    has_visual     = Column(Boolean, default=False)
    sort_order     = Column(Integer, nullable=False)
    change_type    = Column(SAEnum(ChangeType))
    prior_para_id  = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id"), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    section        = relationship("Section", back_populates="paragraphs")
    content_blocks = relationship("ContentBlock", back_populates="paragraph", cascade="all, delete-orphan")
    tags           = relationship("ParagraphTag", back_populates="paragraph", cascade="all, delete-orphan")
    prior_version  = relationship("Paragraph", remote_side="Paragraph.id")


class ContentBlock(Base):
    __tablename__ = "content_blocks"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paragraph_id = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id", ondelete="CASCADE"), nullable=False)
    version_id   = Column(UUID(as_uuid=True), ForeignKey("order_versions.id", ondelete="CASCADE"), nullable=False)
    block_type   = Column(SAEnum(BlockType), nullable=False)
    sequence     = Column(Integer, nullable=False)
    label        = Column(String(100))
    content      = Column(Text, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    paragraph    = relationship("Paragraph", back_populates="content_blocks")


# ─────────────────────────────────────────────────────────────────────────────
# TAGGING
# ─────────────────────────────────────────────────────────────────────────────

class Tag(Base):
    __tablename__ = "tags"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False, unique=True)
    category    = Column(String(50))
    description = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)

    paragraphs  = relationship("ParagraphTag", back_populates="tag")


class ParagraphTag(Base):
    __tablename__ = "paragraph_tags"

    paragraph_id = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id", ondelete="CASCADE"), primary_key=True)
    tag_id       = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    auto_tagged  = Column(Boolean, default=False)
    tagged_at    = Column(DateTime, default=datetime.utcnow)

    paragraph    = relationship("Paragraph", back_populates="tags")
    tag          = relationship("Tag", back_populates="paragraphs")


class CrossReference(Base):
    __tablename__ = "cross_references"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_para_id  = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id", ondelete="CASCADE"), nullable=False)
    target_para_id  = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id", ondelete="SET NULL"), nullable=True)
    target_para_str = Column(String(30))
    reference_text  = Column(Text)
    resolved        = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name    = Column(String(100))
    last_name     = Column(String(100))
    role          = Column(SAEnum(UserRole), nullable=False, default=UserRole.student)
    facility_type = Column(String(50))
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login    = Column(DateTime)


# ─────────────────────────────────────────────────────────────────────────────
# LEARNING FEATURES
# ─────────────────────────────────────────────────────────────────────────────

class Flashcard(Base):
    __tablename__ = "flashcards"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paragraph_id = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id", ondelete="CASCADE"), nullable=False)
    version_id   = Column(UUID(as_uuid=True), ForeignKey("order_versions.id"), nullable=False)
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    front        = Column(Text, nullable=False)
    back         = Column(Text, nullable=False)
    card_type    = Column(String(30), default="definition")
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paragraph_id  = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id", ondelete="SET NULL"), nullable=True)
    version_id    = Column(UUID(as_uuid=True), ForeignKey("order_versions.id"), nullable=False)
    created_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(SAEnum(QuestionType), nullable=False, default=QuestionType.multiple_choice)
    explanation   = Column(Text)
    difficulty    = Column(SmallInteger)
    is_active     = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    choices       = relationship("QuestionChoice", back_populates="question", cascade="all, delete-orphan")


class QuestionChoice(Base):
    __tablename__ = "question_choices"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    choice_text = Column(Text, nullable=False)
    is_correct  = Column(Boolean, nullable=False, default=False)
    sort_order  = Column(Integer, nullable=False)

    question    = relationship("QuizQuestion", back_populates="choices")


class Scenario(Base):
    __tablename__ = "scenarios"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id    = Column(UUID(as_uuid=True), ForeignKey("order_versions.id"), nullable=False)
    created_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title         = Column(String(255), nullable=False)
    description   = Column(Text, nullable=False)
    facility_type = Column(String(50))
    difficulty    = Column(SmallInteger)
    is_published  = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    steps         = relationship("ScenarioStep", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioStep(Base):
    __tablename__ = "scenario_steps"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id    = Column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    sort_order     = Column(Integer, nullable=False)
    prompt         = Column(Text, nullable=False)
    correct_action = Column(Text, nullable=False)
    reference_para = Column(UUID(as_uuid=True), ForeignKey("paragraphs.id"), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    scenario       = relationship("Scenario", back_populates="steps")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id       = Column(UUID(as_uuid=True), ForeignKey("order_versions.id"), nullable=False)
    source_file      = Column(String(500))
    status           = Column(String(20))
    chapters_parsed  = Column(Integer, default=0)
    paragraphs_parsed = Column(Integer, default=0)
    errors           = Column(JSONB, default=list)
    started_at       = Column(DateTime, default=datetime.utcnow)
    completed_at     = Column(DateTime)
