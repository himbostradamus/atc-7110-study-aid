"""
Local question generator.

This provides a deterministic baseline question bank without external API calls.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from .curated_content import get_curated_question_override
from .local_generation import (
    CONDITIONAL_START_RE,
    IMPERATIVE_START_RE,
    build_action_choices,
    build_fill_blank,
    build_mc_distractors,
    display_section_label,
    extract_steps_from_text,
    has_numbered_steps,
    is_overloaded_procedure_sentence,
    joined_blocks,
    meaningful_body_sentences,
    normalise_ws,
    normalize_display_text,
    pick_best_phraseology_line,
    phraseology_lines_from_blocks,
    rng_for,
    select_capability_sentence,
    select_conditional_rule_sentence,
    select_document_control_sentence,
    select_minima_rule_sentence,
    select_requirement_sentence,
    select_scope_sentence,
    select_title_definition_sentence,
)

log = logging.getLogger(__name__)


TYPE_TARGETS = {
    "multiple_choice": 2,
    "true_false": 0,
    "fill_blank": 1,
}
UNDER_PREFIX_RE = re.compile(r"^Under [^,]{1,120},\s*(.+)$", re.IGNORECASE)
PARA_ID_PATTERN = r"\d+(?:-\d+)+(?:[a-z]\d*)?"
NOTE_PREFIX_RE = re.compile(
    rf"^(?:According to|Under) (?:the |a |USAF )?note in\s+{PARA_ID_PATTERN},?\s*",
    re.IGNORECASE,
)
ACCORDING_TO_NOTE_RE = re.compile(
    rf"^According to (?:the )?note in\s+{PARA_ID_PATTERN},\s*",
    re.IGNORECASE,
)
ACCORDING_TO_PARA_RE = re.compile(
    rf"^According to\s+{PARA_ID_PATTERN},\s*",
    re.IGNORECASE,
)
AS_USED_IN_PARA_RE = re.compile(
    rf"^As used in\s+{PARA_ID_PATTERN},\s*",
    re.IGNORECASE,
)
WHAT_DOES_NOTE_SAY_RE = re.compile(
    rf"^What does (?:the )?note in\s+{PARA_ID_PATTERN}\s+say about\s+(.+)\?$",
    re.IGNORECASE,
)
REFERRED_TO_IN_PARA_RE = re.compile(
    rf"\s+(?:referred to|discussed)\s+in\s+{PARA_ID_PATTERN}\b",
    re.IGNORECASE,
)
INLINE_UNDER_PARA_RE = re.compile(
    rf"\s+under\s+{PARA_ID_PATTERN}\b",
    re.IGNORECASE,
)
INLINE_FROM_PARA_RE = re.compile(
    rf"\s+from\s+{PARA_ID_PATTERN}\b",
    re.IGNORECASE,
)
INLINE_IN_PARA_RE = re.compile(
    rf"\s+in\s+{PARA_ID_PATTERN}\b",
    re.IGNORECASE,
)
DOC_LOCATION_RE = re.compile(
    rf"\b(?:under|from|in)\s+{PARA_ID_PATTERN}\b|"
    rf"\b(?:paragraph|para|section)\s+{PARA_ID_PATTERN}\b|"
    rf"\bAccording to (?:the )?note in\s+{PARA_ID_PATTERN}\b|"
    rf"\bAccording to\s+{PARA_ID_PATTERN}\b",
    re.IGNORECASE,
)
MATCHES_SECTION_RE = re.compile(r"^Which statement matches [^?]+\?$", re.IGNORECASE)
SUPPORTED_BY_SECTION_RE = re.compile(r"^Which statement is supported by the section\?$", re.IGNORECASE)
FILL_BLANK_FROM_RE = re.compile(
    r'^Complete the (?:(?:advisory|prescribed|phraseology) )?(?:example|phraseology|statement|requirement) from [^:]+:\s*(.+)$',
    re.IGNORECASE,
)
ORDERING_FROM_RE = re.compile(
    r"^Place the steps from [^ ]+ \([^)]*\) in the correct order\.$",
    re.IGNORECASE,
)
DOC_STRUCTURE_REF_RE = re.compile(
    r"\b(?:this paragraph|paragraph['’]s|paragraph\s+\d+(?:[−-]\d+)+(?:[−-]\d+)?|"
    r"subparagraphs?\s+[a-z0-9]+(?:\s*(?:through|and)\s*[a-z0-9]+)?|"
    r"listed application paragraphs)\b",
    re.IGNORECASE,
)
LIST_MEMBERSHIP_RE = re.compile(
    r"^(?P<item>.+?) is (?P<neg>not )?one of the listed items in .+\.$",
    re.IGNORECASE,
)
SECTION_LIST_PROMPT_RE = re.compile(
    r"^The section's list(?P<neg>\s+does not)?\s+include[s]?:\s*(?P<item>.+)$",
    re.IGNORECASE,
)
EXPLICIT_INCLUDED_PROMPT_RE = re.compile(
    r"^Is the following item explicitly included:\s*(?P<item>.+?)\??$",
    re.IGNORECASE,
)
FIGURE_TABLE_LEAD_RE = re.compile(r"^\(?See\s+(?:FIG|TBL)\b", re.IGNORECASE)
LOW_QUALITY_QUESTION_PATTERNS = (
    re.compile(r"\b(?:to|should|must|may|will|would|could|can)\s+do not\b", re.IGNORECASE),
    re.compile(r"\b(?:need not not|may not not|must not not|should not not|do not not)\b", re.IGNORECASE),
    re.compile(r"\bused all for\b", re.IGNORECASE),
    re.compile(r"\(See it\b", re.IGNORECASE),
    re.compile(r"\bonly items will\b", re.IGNORECASE),
    re.compile(r"\bnot all to\b", re.IGNORECASE),
    re.compile(r"\bonly all\b|\ball only\b", re.IGNORECASE),
    re.compile(r"\bnot only\b.{0,120}\bthey do not provide\b", re.IGNORECASE),
    re.compile(r"^All\b.{0,80}\b(?:are|is) not\b", re.IGNORECASE),
    re.compile(r"\ball changes to it are not canceled\b", re.IGNORECASE),
    re.compile(r"\bposition verify\b", re.IGNORECASE),
    re.compile(r"\b(?:the )?decimal where\b", re.IGNORECASE),
    re.compile(r"\bless than one (?:aircraft|facility)\b", re.IGNORECASE),
    re.compile(r"\bincreases?\b.{0,80}\bnot increased\b", re.IGNORECASE),
    re.compile(r"\bDo not submit a landing clearance\b", re.IGNORECASE),
    re.compile(r"\bwhere final descent is not to start\b", re.IGNORECASE),
    re.compile(r"\balert information\b", re.IGNORECASE),
    re.compile(r"\bunavailable to (?:the )?(?:FAA|FSSs|centers?)\b", re.IGNORECASE),
)
GENERIC_SECTION_TITLES = {
    "APPLICATION",
    "DESCRIPTION",
    "GENERAL",
    "PROCEDURES",
    "PURPOSE",
    "RESPONSIBILITY",
    "TERMINOLOGY",
}
SUBJECT_PROMPT_RE = re.compile(
    r"^(?P<subject>(?!This\b|These\b|That\b|Those\b)[A-Za-z0-9/(),\"' -]{2,120}?)\s+"
    r"(?P<verb>must|shall|should|may|need not|may not|is|are|was|were|can|cannot|will|do not)\b",
    re.IGNORECASE,
)
QUESTION_LIST_INTRO_RE = re.compile(
    r"\b(?:the following|as follows|one of the following)\b",
    re.IGNORECASE,
)
TRAILING_FRAGMENT_RE = re.compile(
    r"\b(?:after|before|during|when|while|unless|until|if|because|than|from|to|of|for|"
    r"with|without|between|within|on|in|at|by|or|and|the|a|an|you)$",
    re.IGNORECASE,
)
GENERIC_ABOUT_STEM_RE = re.compile(r"^What is correct about\b", re.IGNORECASE)
LOW_VALUE_MC_SENTENCE_RE = re.compile(
    r"\b(?:can be obtained by|available for all employees|training is available|"
    r"additional courses\b.+\bavailable from|available from AJI|"
    r"visiting the SMS Toolbox|emailing the Office of Safety|contacting the service center)\b",
    re.IGNORECASE,
)
PROMPT_CONTEXT_SPLIT_RE = re.compile(
    r"\b(?:if|when|unless|before|after|because|provided|while|due to|as soon as)\b",
    re.IGNORECASE,
)
LEADING_TRANSITION_RE = re.compile(
    r"^(?:however|in addition|additionally|as necessary|if necessary|when possible|when practicable|normally|ordinarily),\s+",
    re.IGNORECASE,
)


@dataclass
class GeneratedChoice:
    text: str
    is_correct: bool


@dataclass
class GeneratedQuestion:
    question_text: str
    question_type: str
    choices: list[GeneratedChoice]
    explanation: str
    difficulty: int
    source_block: str
    generation_source: str = "local_auto"
    is_verified: bool = False


def _capitalize_lead(text: str) -> str:
    clean = normalize_display_text(text)
    if not clean:
        return clean
    return f"{clean[:1].upper()}{clean[1:]}"


def _sentence_with_period(text: str) -> str:
    clean = normalize_display_text(text)
    if not clean:
        return clean
    if clean.endswith((".", "!", "?")):
        return clean
    return f"{clean}."


def _normalize_section_structure_text(text: str) -> str:
    clean = text
    clean = re.sub(
        r"\bthe procedures in this section\b",
        "these procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bprocedures in Section\s+\d+\b",
        "these procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthe provisions of this section\b",
        "these procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bprocedures and minima contained in this section\b",
        "regional procedures and minima",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bprocedures and minima contained in Section\s+\d+\b",
        "regional procedures and minima",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bin accordance with Chapter 4, IFR, Section 5(?:, Altitude Assignment and Verification)?\b",
        "in accordance with IFR altitude assignment and verification procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 4, IFR, Section 5, Altitude Assignment and Verification\b",
        "IFR altitude assignment and verification procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 4, IFR, Section 5\b",
        "IFR altitude assignment and verification procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 2, Section 7\b",
        "altimeter-setting procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^The basic services described in Chapter 7, Visual, Section 6, Basic Radar Service to VFR Aircraft-Terminal\.?$",
        "Basic terminal radar service to VFR aircraft.",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 7, Visual, Section 6, Basic Radar Service to VFR Aircraft-Terminal\b",
        "basic terminal radar service to VFR aircraft",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bbasic terminal radar services in Section 6\b",
        "basic terminal radar services",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bOnly special VFR services described in Section 5\b",
        "Only special VFR services",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bOnly Chapter 4 procedures, with no Section\s+\d+-specific guidance\b",
        "Only standard IFR procedures, with no region-specific guidance",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bOnly the procedures in Chapter 4, with no Section\s+\d+ exceptions\b",
        "Only standard IFR procedures, with no region-specific exceptions",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bOnly Chapter 4 procedures, with no Section\s+\d+ exceptions\b",
        "Only standard IFR procedures, with no region-specific exceptions",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bIn accordance only with Section\s+\d+ longitudinal standards\b",
        "Only in accordance with the region's longitudinal standards",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthe section's IFR-condition criteria\b",
        "the IFR-condition criteria",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bfor purposes of the section\b",
        "for these procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^What does the section permit\?$",
        "What is permitted for through clearances?",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bfor IFR departure turning procedures in the section\b",
        "for IFR departure turning procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\blisted in the section\b",
        "authorized",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bprocedures in the section\b",
        "procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bapplying the section's procedures\b",
        "applying these procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bspecified in the section, a facility directive, or an LOA\b",
        "specified by the procedure, a facility directive, or an LOA",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthe code rules in Section 2\b",
        "beacon-code rules",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\bthe these procedures\b", "these procedures", clean, flags=re.IGNORECASE)
    return clean


def normalize_question_text(question_type: str, question_text: str) -> str:
    clean = normalize_display_text(question_text)
    if not clean:
        return clean

    clean = _normalize_section_structure_text(clean)

    note_say_match = WHAT_DOES_NOTE_SAY_RE.match(clean)
    if note_say_match:
        topic = note_say_match.group(1).strip()
        return _capitalize_lead(f"What is true about {topic}?")

    if re.match(r'^Complete the phraseology\s*:\s*', clean, re.IGNORECASE):
        return re.sub(
            r'^Complete the phraseology\s*:\s*',
            "Complete the prescribed phraseology: ",
            clean,
            flags=re.IGNORECASE,
        )

    fill_blank_match = FILL_BLANK_FROM_RE.match(clean)
    if fill_blank_match:
        return f"Complete the prescribed phraseology: {fill_blank_match.group(1).strip()}"

    under_match = UNDER_PREFIX_RE.match(clean)
    if under_match:
        clean = under_match.group(1).strip()
    clean = NOTE_PREFIX_RE.sub("", clean)
    clean = ACCORDING_TO_NOTE_RE.sub("", clean)
    clean = ACCORDING_TO_PARA_RE.sub("", clean)
    clean = AS_USED_IN_PARA_RE.sub("", clean)
    clean = re.sub(
        rf"^Except as stated in\s+{PARA_ID_PATTERN},\s*",
        "Except where explicitly authorized otherwise, ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = REFERRED_TO_IN_PARA_RE.sub("", clean)
    clean = re.sub(
        rf"\b(traffic)\s+issued\s+under\s+{PARA_ID_PATTERN}\b",
        r"\1",
        clean,
        flags=re.IGNORECASE,
    )
    clean = INLINE_UNDER_PARA_RE.sub("", clean)
    clean = INLINE_FROM_PARA_RE.sub("", clean)
    clean = INLINE_IN_PARA_RE.sub("", clean)
    clean = re.sub(
        r"\b(?:is\s+)?specifically named\s+in connection with\b",
        "applies in connection with",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\buse the phraseology\.$",
        "use the applicable surface-taxi phraseology.",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bexcept as authorized\.$",
        "except as authorized for LAHSO operations.",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^What volcanic-ash information is specifically listed\?$",
        "What volcanic-ash information should be issued when known?",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^Which display requirement is specifically stated for\b",
        "Which display requirement applies when",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"^Which phraseology is published for\b",
        "Which phraseology is used for",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r",\s+when\b", ", when", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b,\s*,\b", ",", clean)
    clean = re.sub(r"\s+([?.!])", r"\1", clean)

    if (
        MATCHES_SECTION_RE.match(clean)
        or SUPPORTED_BY_SECTION_RE.match(clean)
        or clean == "Select the statement supported by the section."
    ):
        return "Which statement is correct?"

    if ORDERING_FROM_RE.match(clean):
        return "Place these steps in the correct procedural order."

    list_match = LIST_MEMBERSHIP_RE.match(clean)
    if list_match:
        item = list_match.group("item").rstrip(".")
        return f"Is this item required or authorized: {item}?"
    section_list_match = SECTION_LIST_PROMPT_RE.match(clean)
    if section_list_match:
        item = section_list_match.group("item").rstrip(".")
        return f"Is this item required or authorized: {item}?"
    explicit_included_match = EXPLICIT_INCLUDED_PROMPT_RE.match(clean)
    if explicit_included_match:
        item = explicit_included_match.group("item").rstrip(".")
        return f"Is this item required or authorized: {item}?"

    clean = re.sub(r"\bthe paragraph's\b", "the section's", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bthis paragraph\b", "the section", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bthe paragraph\b", "the section", clean, flags=re.IGNORECASE)

    return _capitalize_lead(clean)


def normalize_choice_text(choice_text: str) -> str:
    clean = normalize_display_text(choice_text)
    if not clean:
        return clean
    clean = INLINE_FROM_PARA_RE.sub("", clean)
    clean = INLINE_UNDER_PARA_RE.sub("", clean)
    clean = INLINE_IN_PARA_RE.sub("", clean)
    clean = REFERRED_TO_IN_PARA_RE.sub("", clean)
    clean = _normalize_section_structure_text(clean)
    clean = re.sub(r"\bthe paragraph's\b", "the section's", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bthis paragraph\b", "the section", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bthe paragraph\b", "the section", clean, flags=re.IGNORECASE)
    return _capitalize_lead(clean)


def normalize_generated_question(question: GeneratedQuestion) -> GeneratedQuestion:
    question.question_text = normalize_question_text(question.question_type, question.question_text)
    question.choices = [
        GeneratedChoice(text=normalize_choice_text(choice.text), is_correct=choice.is_correct)
        for choice in question.choices
    ]
    return question


def question_text_errors(question_type: str, question_text: str) -> list[str]:
    errors: list[str] = []
    clean = normalise_ws(question_text)
    if not clean:
        return ["missing question_text"]
    if re.search(r"\s+([,.;:?!])", clean):
        errors.append("question text contains spacing before punctuation")
    if UNDER_PREFIX_RE.match(clean):
        errors.append("question text depends on a paragraph/title prefix")
    if DOC_LOCATION_RE.search(clean):
        errors.append("question text includes a document-location reference")
    if MATCHES_SECTION_RE.match(clean):
        errors.append("question text names a paragraph instead of the concept")
    if SUPPORTED_BY_SECTION_RE.match(clean) or clean == "Select the statement supported by the section.":
        errors.append("question text uses section-scaffold wording")
    if FILL_BLANK_FROM_RE.match(clean):
        errors.append("question text includes a paragraph id")
    if ORDERING_FROM_RE.match(clean):
        errors.append("ordering prompt includes a paragraph id")
    if DOC_STRUCTURE_REF_RE.search(clean):
        errors.append("question text depends on document cross-references")
    if LIST_MEMBERSHIP_RE.match(clean):
        errors.append("list-membership question uses document-structure wording")
    if SECTION_LIST_PROMPT_RE.match(clean):
        errors.append("list-membership question uses section-list scaffolding")
    if EXPLICIT_INCLUDED_PROMPT_RE.match(clean):
        errors.append("list-membership question uses explicit-inclusion scaffolding")
    if FIGURE_TABLE_LEAD_RE.match(clean):
        errors.append("question text begins with a figure/table reference")
    for pattern in LOW_QUALITY_QUESTION_PATTERNS:
        if pattern.search(clean):
            errors.append(f"matches low-quality pattern: {pattern.pattern}")
    return errors


def choice_text_errors(choice_text: str) -> list[str]:
    errors: list[str] = []
    clean = normalise_ws(choice_text)
    if not clean:
        return ["missing choice_text"]
    if re.search(r"\s+([,.;:?!])", clean):
        errors.append("choice text contains spacing before punctuation")
    if DOC_STRUCTURE_REF_RE.search(clean):
        errors.append("choice text depends on document cross-references")
    if DOC_LOCATION_RE.search(clean):
        errors.append("choice text includes a document-location reference")
    if re.search(r"\bthe paragraph\b", clean, re.IGNORECASE):
        errors.append("choice text uses paragraph-structure wording")
    for pattern in LOW_QUALITY_QUESTION_PATTERNS:
        if pattern.search(clean):
            errors.append(f"choice matches low-quality pattern: {pattern.pattern}")
    return errors


def validate_generated_question(question: GeneratedQuestion) -> list[str]:
    errors = question_text_errors(question.question_type, question.question_text)
    if question.question_type in {"multiple_choice", "true_false"} and not question.choices:
        errors.append("missing answer choices")
    for choice in question.choices:
        errors.extend(choice_text_errors(choice.text))
    return errors


def local_auto_question_quality_errors(question: GeneratedQuestion) -> list[str]:
    if getattr(question, "generation_source", "local_auto") != "local_auto":
        return []

    errors: list[str] = []
    question_text = normalise_ws(question.question_text)

    if question.question_type == "true_false":
        errors.append("local-auto true/false rewards verbatim recall")
        return errors

    if question.question_type == "multiple_choice":
        if question_text == "Which statement is correct?":
            errors.append("multiple-choice stem is too generic")
        if GENERIC_ABOUT_STEM_RE.match(question_text):
            errors.append("multiple-choice stem relies on generic about-format wording")
        if len(question_text) > 180:
            errors.append("multiple-choice stem is too long")
        if is_overloaded_procedure_sentence(question_text):
            errors.append("multiple-choice stem is an overloaded procedural sentence")
        if re.match(r"^What is correct about (?:below|above|after|before|during|when|while|unless|if|or|and)\b", question_text):
            errors.append("multiple-choice stem is built from a sentence fragment")
        if LOW_VALUE_MC_SENTENCE_RE.search(question.explanation or ""):
            errors.append("multiple-choice source sentence is administrative/support material")
        for choice in question.choices:
            clean = normalise_ws(choice.text)
            if len(clean) > 220:
                errors.append("multiple-choice choice text is too long")
                break
            if TRAILING_FRAGMENT_RE.search(clean.rstrip(".!?")):
                errors.append("multiple-choice choice text ends with a fragment")
                break
    elif question.question_type == "ordering":
        for choice in question.choices:
            clean = normalise_ws(choice.text)
            if len(clean.split()) > 18:
                errors.append("ordering step is too long")
                break
            if clean.endswith(":"):
                errors.append("ordering step is a list header")
                break
            if QUESTION_LIST_INTRO_RE.search(clean):
                errors.append("ordering step contains list-intro scaffolding")
                break
            if TRAILING_FRAGMENT_RE.search(clean.rstrip(".!?")):
                errors.append("ordering step ends with a fragment")
                break
            if re.search(r"JO\s*7110\.65|\b\d{1,2}/\d{1,2}/\d{2,4}\b", clean, re.IGNORECASE):
                errors.append("ordering step contains running-header noise")
                break
    elif question.question_type == "fill_blank":
        if not question_text.lower().startswith("complete the prescribed phraseology:"):
            errors.append("fill-blank is not framed as prescribed phraseology")
        if len(question_text) > 180:
            errors.append("fill-blank prompt is too long")
        if re.search(r"\b\d+(?:-\d+)+\b", question_text):
            errors.append("fill-blank prompt contains paragraph/header noise")
        question_phrase_match = re.search(r'"([^"]+)"', question_text)
        if question_phrase_match:
            phrase = normalise_ws(question_phrase_match.group(1)).rstrip(".!?")
            if TRAILING_FRAGMENT_RE.search(phrase):
                errors.append("fill-blank phraseology ends with a fragment")
        explanation_phrase_match = re.search(r'"([^"]+)"', question.explanation or "")
        if explanation_phrase_match:
            phrase = normalise_ws(explanation_phrase_match.group(1)).rstrip(".!?")
            if TRAILING_FRAGMENT_RE.search(phrase):
                errors.append("fill-blank explanation phrase ends with a fragment")

    return errors


async def generate_questions_for_paragraph(
    para_id: str,
    para_title: str,
    blocks: list[dict],
) -> list[GeneratedQuestion]:
    """
    Generate a deterministic set of quiz questions for one paragraph.
    """
    if not blocks:
        return []

    questions: list[GeneratedQuestion] = []
    body_sentences = _question_candidate_sentences(para_title, blocks)
    phraseology_lines = phraseology_lines_from_blocks(blocks)
    body_text = joined_blocks(blocks, "body")

    questions.extend(_generate_multiple_choice(para_id, para_title, body_sentences))
    questions.extend(_generate_true_false(para_id, body_sentences))

    if phraseology_lines:
        phraseology_line = pick_best_phraseology_line(
            phraseology_lines,
            f"{para_id}:fill",
            purpose="fill_blank",
        )
        fill_blank = _generate_fill_blank(para_id, phraseology_line) if phraseology_line else None
        if fill_blank:
            questions.append(fill_blank)

    if body_text and has_numbered_steps(body_text):
        ordering = _generate_ordering(para_id, para_title, body_text)
        if ordering:
            questions.append(ordering)

    questions = _merge_curated_questions(para_id, questions)
    questions = [normalize_generated_question(question) for question in questions]
    questions = [
        question
        for question in questions
        if not validate_generated_question(question)
        and not local_auto_question_quality_errors(question)
    ]
    questions = _dedupe_questions(questions)
    log.info("Generated %s local questions for %s", len(questions), para_id)
    return questions


def _dedupe_questions(questions: list[GeneratedQuestion]) -> list[GeneratedQuestion]:
    """Drop duplicate stems within a paragraph while preserving order."""
    seen: set[tuple[str, str]] = set()
    deduped: list[GeneratedQuestion] = []

    for question in questions:
        key = (question.question_type, question.question_text.strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(question)

    return deduped


def _true_false_choices(correct_answer: Optional[str]) -> list[GeneratedChoice]:
    if correct_answer is None:
        return []

    if isinstance(correct_answer, bool):
        normalised = "true" if correct_answer else "false"
    else:
        normalised = str(correct_answer).strip().lower()
    if normalised == "true":
        return [
            GeneratedChoice(text="True", is_correct=True),
            GeneratedChoice(text="False", is_correct=False),
        ]
    if normalised == "false":
        return [
            GeneratedChoice(text="True", is_correct=False),
            GeneratedChoice(text="False", is_correct=True),
        ]
    return []


def _sentence_question_score(sentence: str, specific_distractors: list[str]) -> int:
    lower = sentence.lower()
    score = len(specific_distractors) * 10

    if re.search(r"https?://|faa\.gov", lower):
        score -= 12
    if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", sentence):
        score -= 20
    if re.search(r"\b\d{4,5}\b", sentence):
        score -= 4
    if sentence.count("Change") >= 2 or sentence.count("Publication") >= 2 or sentence.count("JO ") >= 2:
        score -= 20
    if sentence.endswith(":"):
        score -= 8
    if re.search(r"\bmust\b|\bshall\b|\bshould\b|\brequired\b", lower):
        score += 3
    if re.search(r"\baircraft\b|\bcontroller\b|\btraffic\b|\brunway\b|\bclearance\b", lower):
        score += 2
    if len(sentence.split()) < 6:
        score -= 3
    if len(sentence.split()) > 35:
        score -= 6
    if len(sentence.split()) > 55:
        score -= 10
    if not re.search(r"\b(is|are|must|may|should|will|was|were|be|issue|issues|submit|submits|review|reviews|control|controls|provide|provides|coordinate|coordinates|report|reports|advise|advises|apply|applies)\b", lower):
        score -= 6

    return score


def _prepare_sentence_candidates(
    para_id: str,
    sentences: list[str],
) -> list[dict]:
    candidates: list[dict] = []
    for idx, sentence in enumerate(sentences):
        specific = build_mc_distractors(
            sentence,
            f"{para_id}:mc:{idx}",
            allow_generic=False,
        )
        candidates.append(
            {
                "idx": idx,
                "sentence": sentence,
                "specific": specific,
                "score": _sentence_question_score(sentence, specific),
            }
        )

    candidates.sort(key=lambda item: (-item["score"], item["idx"]))
    return candidates


def _question_candidate_sentences(para_title: str, blocks: list[dict]) -> list[str]:
    text = joined_blocks(blocks, "body", "note", "exception", "interpretation")
    candidates = [
        select_requirement_sentence(text),
        select_conditional_rule_sentence(text),
        select_minima_rule_sentence(text),
        select_scope_sentence(para_title, text),
        select_capability_sentence(para_title, text),
        select_document_control_sentence(para_title, text),
        select_title_definition_sentence(para_title, text),
    ]
    candidates.extend(meaningful_body_sentences(blocks))

    deduped: list[str] = []
    seen: set[str] = set()
    for sentence in candidates:
        clean = _sentence_with_period(sentence or "")
        key = clean.lower()
        if not clean or key in seen:
            continue
        if is_overloaded_procedure_sentence(clean):
            continue
        if QUESTION_LIST_INTRO_RE.search(clean):
            continue
        if re.search(r"\bnot only\b", clean, re.IGNORECASE):
            continue
        if re.search(r"\bJO\s*7110\.65|\b\d{1,2}/\d{1,2}/\d{2,4}\b", clean, re.IGNORECASE):
            continue
        if TRAILING_FRAGMENT_RE.search(clean.rstrip(".!?")):
            continue
        if re.search(r"\b[A-Z]\.$", clean):
            continue
        if len(clean.split()) > 34:
            continue
        seen.add(key)
        deduped.append(clean)

    filtered: list[str] = []
    for sentence in deduped:
        stem = sentence.rstrip(".").lower()
        if any(
            other != sentence
            and other.lower().startswith(stem)
            and len(other) > len(sentence) + 10
            for other in deduped
        ):
            continue
        filtered.append(sentence)

    return filtered


def _split_condition_action(sentence: str) -> Optional[tuple[str, str]]:
    clean = LEADING_TRANSITION_RE.sub("", normalise_ws(sentence)).rstrip(".")
    if not CONDITIONAL_START_RE.match(clean):
        return None
    if "," not in clean:
        return None

    condition, action = clean.split(",", 1)
    condition = normalise_ws(condition).rstrip(" ,;:")
    action = _sentence_with_period(action.strip())
    if not condition or not action:
        return None
    if len(condition.split()) < 2 or len(condition.split()) > 26:
        return None
    if len(action.split()) < 3 or len(action.split()) > 22:
        return None
    if is_overloaded_procedure_sentence(action):
        return None
    return condition, action


def _conditional_question_text(condition: str, action: str) -> str:
    lower_action = action.lower()
    if lower_action.startswith("include "):
        return f"{condition}, what should be included?"
    if lower_action.startswith("state "):
        return f"{condition}, what should be stated?"
    if lower_action.startswith("use "):
        return f"{condition}, what should be used?"
    if lower_action.startswith("request "):
        return f"{condition}, what should be requested?"
    if lower_action.startswith("inform ") or lower_action.startswith("advise "):
        return f"{condition}, what should the pilot be told?"
    return f"{condition}, what is the correct action?"


def _prompt_subject_text(subject: str) -> str:
    clean = normalise_ws(subject).rstrip(" ,;:")
    if not clean:
        return clean
    if clean.startswith('"'):
        return clean
    token_match = re.match(r"^([A-Za-z][A-Za-z0-9/-]*)", clean)
    token = token_match.group(1) if token_match else ""
    if token and len(token) >= 2 and token[:2].isupper():
        return clean
    return f"{clean[:1].lower()}{clean[1:]}"


def _trim_prompt_context(text: str) -> str:
    clean = normalise_ws(text).rstrip(" .")
    if not clean:
        return clean
    parts = PROMPT_CONTEXT_SPLIT_RE.split(clean, maxsplit=1)
    return parts[0].rstrip(" ,;:.")


def _strip_prompt_prefix(text: str) -> str:
    clean = normalise_ws(text)
    if not clean:
        return clean
    return LEADING_TRANSITION_RE.sub("", clean)


def _subject_prompt(subject: str, verb: str, predicate: str) -> Optional[str]:
    clean_subject = normalise_ws(subject).rstrip(" ,;:")
    clean_predicate = normalise_ws(predicate).rstrip(" .")
    if not clean_subject or not clean_predicate:
        return None
    if LOW_VALUE_MC_SENTENCE_RE.search(clean_predicate):
        return None

    lower_predicate = clean_predicate.lower()
    subject_text = _prompt_subject_text(clean_subject)
    aux = "is" if verb.lower() in {"is", "was"} else "are"

    if lower_predicate.startswith("responsible for "):
        return f"What {aux} {subject_text} responsible for?"
    if lower_predicate.startswith("required to be familiar with "):
        return f"What {aux} {subject_text} required to be familiar with?"
    if lower_predicate.startswith("required to "):
        return f"What {aux} {subject_text} required to do?"
    if lower_predicate.startswith("be obtained from "):
        return f"Where must {subject_text} be obtained?"
    if lower_predicate.startswith("fundamental to "):
        rest = _trim_prompt_context(clean_predicate[len("fundamental to "):])
        if rest:
            return f"What is fundamental to {rest}?"
    if lower_predicate.startswith("set forth as "):
        return f"What {aux} {subject_text} set forth as?"
    if lower_predicate.startswith("not expected to "):
        return f"What is {subject_text} not expected to do?"
    if lower_predicate.startswith("based on "):
        return f"What is {subject_text} based on?"
    if clean_subject.lower() == "you" and verb.lower() == "may" and lower_predicate.startswith("use as a holding fix "):
        return "What location may be used as a holding fix?"
    if clean_subject.startswith('"') and lower_predicate.startswith("not "):
        return f"What does {subject_text} not mean?"
    if lower_predicate.startswith("should be made to ensure ") and clean_subject.lower() == "every effort":
        return "What should every effort ensure?"
    if lower_predicate.startswith("be used for ") and verb.lower() == "may":
        return f"What may {subject_text} be used for?"
    if lower_predicate.startswith("be used to ") and verb.lower() == "may":
        rest = _trim_prompt_context(clean_predicate[len("be used to "):])
        if rest:
            first_word = rest.split()[0]
            return f"What may {subject_text} be used to {first_word}?"
    if lower_predicate.startswith("dictate ") and verb.lower() == "may":
        return f"What may {subject_text} dictate?"
    if lower_predicate.startswith("be retained in ") and verb.lower() in {"must", "shall", "should"}:
        location = _trim_prompt_context(clean_predicate[len("be retained in "):])
        if location:
            return f"What {verb.lower()} be retained in {location}?"
    if lower_predicate.startswith("be removed from ") and verb.lower() in {"must", "shall", "should"}:
        location = _trim_prompt_context(clean_predicate[len("be removed from "):])
        if location:
            return f"What {verb.lower()} be removed from {location}?"
    if lower_predicate.startswith("not be entered in ") and verb.lower() in {"must", "shall", "should"}:
        location = _trim_prompt_context(clean_predicate[len("not be entered in "):])
        if location:
            return f"What {verb.lower()} not be entered in {location}?"
    if lower_predicate.startswith("be entered in ") and verb.lower() in {"must", "shall", "should"}:
        location = _trim_prompt_context(clean_predicate[len("be entered in "):])
        if location:
            return f"What {verb.lower()} be entered in {location}?"

    return None


def _multiple_choice_prompt(sentence: str, para_title: str) -> Optional[str]:
    clean = _strip_prompt_prefix(sentence).rstrip(".")
    if not clean:
        return None
    if LOW_VALUE_MC_SENTENCE_RE.search(clean):
        return None

    title = display_section_label(para_title)
    title_is_specific = bool(title and title.upper() not in GENERIC_SECTION_TITLES)

    if IMPERATIVE_START_RE.match(clean) or clean.lower().startswith(("do not ", "authorize ")):
        if title_is_specific:
            return f"For {title.lower()}, what is the correct action?"
        return "What is the correct action?"

    subject_match = SUBJECT_PROMPT_RE.match(clean)
    if subject_match:
        subject = normalise_ws(subject_match.group("subject")).rstrip(" ,;:")
        predicate = clean[subject_match.end("verb"):].strip()
        if (
            1 <= len(subject.split()) <= 16
            and not CONDITIONAL_START_RE.match(subject)
            and (subject.lower() == "you" or not TRAILING_FRAGMENT_RE.search(subject))
        ):
            prompt = _subject_prompt(subject, subject_match.group("verb"), predicate)
            if prompt:
                return prompt

    return None


def _merge_curated_questions(
    para_id: str,
    generated: list[GeneratedQuestion],
) -> list[GeneratedQuestion]:
    override = get_curated_question_override(para_id)
    if not override:
        return generated

    replace_types = set(override.get("replace_types", []))
    kept = [q for q in generated if q.question_type not in replace_types]

    curated: list[GeneratedQuestion] = []
    for item in override.get("items", []):
        choices = [
            GeneratedChoice(text=choice["text"], is_correct=choice["is_correct"])
            for choice in item.get("choices", [])
        ]
        if not choices and item.get("question_type") == "true_false":
            choices = _true_false_choices(item.get("correct_answer"))

        curated.append(
            GeneratedQuestion(
                question_text=item["question_text"].strip(),
                question_type=item["question_type"],
                choices=choices,
                explanation=item.get("explanation", ""),
                difficulty=item.get("difficulty", 2),
                source_block=item.get("source_block", "body"),
                generation_source=item.get("generation_source", "curated"),
            )
        )

    return curated + kept


def _generate_multiple_choice(
    para_id: str,
    para_title: str,
    sentences: list[str],
) -> list[GeneratedQuestion]:
    questions: list[GeneratedQuestion] = []
    candidates = _prepare_sentence_candidates(para_id, sentences)

    for candidate in candidates:
        if len(questions) >= TYPE_TARGETS["multiple_choice"]:
            break
        sentence = candidate["sentence"]
        idx = candidate["idx"]
        specific = candidate["specific"]

        condition_action = _split_condition_action(sentence)
        if condition_action:
            condition, action = condition_action
            question_text = _conditional_question_text(condition, action)
            action_choices = build_action_choices(
                action,
                f"{para_id}:mc_action:{idx}",
                question_text,
            )
            if len(action_choices) != 4:
                continue
            choices = [
                GeneratedChoice(text=choice["text"], is_correct=choice["is_correct"])
                for choice in action_choices
            ]
            questions.append(
                GeneratedQuestion(
                    question_text=question_text,
                    question_type="multiple_choice",
                    choices=choices,
                    explanation=f"Per {para_id}: {sentence}",
                    difficulty=2,
                    source_block="body",
                )
            )
            continue

        if candidate["score"] < 8:
            continue

        prompt = _multiple_choice_prompt(sentence, para_title)
        if not prompt:
            continue

        if len(specific) >= 3:
            distractors = specific[:3]
        elif len(specific) >= 1 and candidate["score"] >= 10:
            distractors = []
            for option in build_mc_distractors(sentence, f"{para_id}:mc:{idx}", allow_generic=True):
                if option != sentence and option not in distractors:
                    distractors.append(option)
            if len(distractors) < 3:
                continue
        else:
            continue

        choices = [GeneratedChoice(text=sentence, is_correct=True)]
        choices.extend(GeneratedChoice(text=text, is_correct=False) for text in distractors[:3])

        rng = rng_for(para_id, idx, "mc")
        shuffled = choices[:]
        rng.shuffle(shuffled)

        questions.append(
            GeneratedQuestion(
                question_text=prompt,
                question_type="multiple_choice",
                choices=shuffled,
                explanation=f"Per {para_id}: {sentence}",
                difficulty=1 if len(sentence.split()) <= 16 else 2,
                source_block="body",
            )
        )

    return questions


def _generate_true_false(para_id: str, sentences: list[str]) -> list[GeneratedQuestion]:
    if TYPE_TARGETS["true_false"] <= 0 or not sentences:
        return []
    return []


def _generate_fill_blank(para_id: str, line: str) -> Optional[GeneratedQuestion]:
    payload = build_fill_blank(line, f"{para_id}:fill")
    if not payload:
        return None

    return GeneratedQuestion(
        question_text=f'Complete the prescribed phraseology: "{payload["masked_text"]}"',
        question_type="fill_blank",
        choices=[GeneratedChoice(text=payload["answer"], is_correct=True)],
        explanation=f'Per {para_id}: "{payload["full_phrase"]}"',
        difficulty=1,
        source_block="phraseology",
    )


def _generate_ordering(
    para_id: str,
    para_title: str,
    body_text: str,
) -> Optional[GeneratedQuestion]:
    steps = extract_steps_from_text(body_text)
    if len(steps) < 3:
        return None

    return GeneratedQuestion(
        question_text="Place these steps in the correct procedural order.",
        question_type="ordering",
        choices=[GeneratedChoice(text=step, is_correct=True) for step in steps],
        explanation=f"Per {para_id}, the source text presents these procedural steps in this order.",
        difficulty=2,
        source_block="body",
    )


async def generate_questions_for_chapter(
    paragraphs: list[dict],
    skip_para_ids: Optional[set[str]] = None,
    on_progress: Optional[callable] = None,
) -> dict[str, list[GeneratedQuestion]]:
    """
    Generate questions for all paragraphs in a chapter batch.
    Returns {para_id: [GeneratedQuestion, ...]}
    """
    import asyncio

    skip = skip_para_ids or set()
    results: dict[str, list[GeneratedQuestion]] = {}

    for para in paragraphs:
        para_id = para.get("para_id", "")
        if para_id in skip:
            continue

        questions = await generate_questions_for_paragraph(
            para_id=para_id,
            para_title=para.get("title", ""),
            blocks=para.get("blocks", []),
        )
        results[para_id] = questions

        if on_progress:
            on_progress(para_id, len(questions), len(paragraphs))

        await asyncio.sleep(0)

    return results
