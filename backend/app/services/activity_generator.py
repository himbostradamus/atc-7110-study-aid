"""
Local activity generator.

This replaces the previous prompt-based generator with deterministic
extractors so activity generation does not require external authoring APIs.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from .local_generation import (
    ALLOWED_ADJACENT_DUPLICATE_TOKENS,
    AUXILIARY_VERB_RE,
    CONDITIONAL_CUE_RE,
    CONDITIONAL_START_RE,
    DEICTIC_LEAD_RE,
    DEFINITION_CUE_RE,
    IMPERATIVE_START_RE,
    INTRO_CLAUSE_IMPERATIVE_RE,
    TERM_DEFINITION_PATTERN_RE,
    build_statement_variants,
    build_mc_distractors,
    build_situation_prompt,
    build_action_choices,
    build_readback_choices,
    clean_sentence_candidate,
    display_section_label,
    extract_example_snippets,
    extract_list_items,
    extract_reference_entries,
    extract_steps_from_text,
    extract_step_visibility_table_rows,
    extract_term_pairs_from_text,
    is_generic_action_distractor,
    is_contextual_spot_token,
    make_word_bank,
    meaningful_sentences_from_text,
    mutate_phrase_line,
    normalise_ws,
    normalize_display_text,
    pick_best_phraseology_line,
    phraseology_lines_from_text,
    rng_for,
    score_phraseology_line,
    select_capability_sentence,
    select_conditional_rule_sentence,
    select_document_control_sentence,
    select_minima_rule_sentence,
    select_action_sentence,
    select_requirement_sentence,
    select_scope_sentence,
    select_title_definition_sentence,
    split_token_parts,
    strip_paragraph_heading,
)
from .curated_content import merge_curated_activities

log = logging.getLogger(__name__)

CHOICE_ACTIVITY_TYPES = {
    "directive_check",
    "conditional_rule_check",
    "term_definition_check",
    "document_control_check",
    "requirement_check",
    "scope_check",
    "capability_check",
    "reference_check",
    "minima_rule_check",
    "list_membership",
    "table_lookup",
    "visual_interpretation",
    "example_check",
    "knowledge_check",
    "readback_check",
    "situation_action",
}
SELF_CONTAINED_STATEMENT_TYPES = {
    "conditional_rule_check",
    "term_definition_check",
    "document_control_check",
    "requirement_check",
    "scope_check",
    "capability_check",
    "minima_rule_check",
}
LOW_QUALITY_PATTERNS = (
    re.compile(r"\bnot not\b", re.IGNORECASE),
    re.compile(r"\bonly who\b", re.IGNORECASE),
    re.compile(r"\bonly aircraft\b", re.IGNORECASE),
    re.compile(r"\bfor reference by\b", re.IGNORECASE),
    re.compile(r"\ball when\b", re.IGNORECASE),
    re.compile(r"\b(?:to|should|must|may|will|would|could|can)\s+do not\b", re.IGNORECASE),
    re.compile(r"\b(?:need not not|may not not|must not not|should not not|do not not)\b", re.IGNORECASE),
    re.compile(r"\bused all for\b", re.IGNORECASE),
    re.compile(r"\(See it\b", re.IGNORECASE),
    re.compile(r"\bonly items will\b", re.IGNORECASE),
    re.compile(r"\bnot only\b.{0,120}\bthey do not provide\b", re.IGNORECASE),
    re.compile(r"\bneed not\b.{0,120}\bnot only\b", re.IGNORECASE),
    re.compile(r"\bdo not\b.{0,140}\bonly when\b", re.IGNORECASE),
    re.compile(r"\bthe do not use\b", re.IGNORECASE),
    re.compile(r"\b14 CFR section is\b", re.IGNORECASE),
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
DIRECTIVE_LOW_QUALITY_PATTERNS = (
    re.compile(r"^Do not use the word\b", re.IGNORECASE),
    re.compile(r"^Do not use approved\b", re.IGNORECASE),
    re.compile(r"^Do not use mileage-based\b", re.IGNORECASE),
    re.compile(r"^Do not apply\b", re.IGNORECASE),
    re.compile(r"^Do not change initiators\b", re.IGNORECASE),
    re.compile(r"\btransfer of\b", re.IGNORECASE),
)
DIRECTIVE_LABEL_PREFIX_RE = re.compile(
    r"^(?:[A-Z][A-Z /-]{2,24}\.)\s+(?=(?:do not\s+)?(?:Issue|Request|Report|Move|Forward|"
    r"Retain|Prefix|Use|Respond|Consider|Clear|Confirm|Maintain|Coordinate|Inform|Advise|"
    r"Apply|Provide|Transfer|Assign|Establish|Obtain|Contact|Monitor|Check|State|Describe|"
    r"Separate|Remind|Broadcast|Ensure|Turn|Climb|Descend|Approve|Interrupt|Relay|Terminate|"
    r"Inhibit|Keep|Change|Identify|Record|Annotate|Transmit|Notify|Instruct|Direct|Delay|"
    r"Release|Specify)\b)",
    re.IGNORECASE,
)
DIRECT_QUESTION_RE = re.compile(
    r"^(?:what|which|who|when|where|why|how|is|are|do|does|did|can|could|should|"
    r"would|will|must|may)\b",
    re.IGNORECASE,
)
DOC_STRUCTURE_REF_RE = re.compile(
    r"\b(?:this paragraph|paragraph['’]s|paragraph\s+\d+(?:[−-]\d+)+(?:[−-]\d+)?|"
    r"subparagraphs?\s+[a-z0-9]+(?:\s*(?:through|and)\s*[a-z0-9]+)?|"
    r"listed application paragraphs)\b",
    re.IGNORECASE,
)
UNDER_PREFIX_RE = re.compile(r"^Under [^,]{1,120},\s*(.+)$", re.IGNORECASE)
INLINE_PARA_REF_RE = re.compile(r"\s+under\s+\d+(?:-\d+)+(?:[a-z])?(?=(?:[?.!]|$))", re.IGNORECASE)
FIGURE_TABLE_LEAD_RE = re.compile(r"^\(?See\s*(?:FIG|TBL)\b", re.IGNORECASE)
CITATION_LEAD_RE = re.compile(r"^(?:FAA\s+Order\s+JO|ICAO\s+DOC|14\s+CFR|P/CG\s+Term)\b", re.IGNORECASE)
MATCHES_PARAGRAPH_RE = re.compile(r"^Select the statement that matches .+\.$", re.IGNORECASE)
SUPPORTED_BY_SECTION_RE = re.compile(r"^Which statement is supported by the section\?$", re.IGNORECASE)
LIST_MEMBERSHIP_RE = re.compile(
    r"^(?P<item>.+?) is (?P<neg>not )?one of the listed items in .+\.$",
    re.IGNORECASE,
)
SECTION_LIST_PROMPT_RE = re.compile(
    r"^The section's list(?P<neg>\s+does not)?\s+include[s]?:\s*(?P<item>.+)$",
    re.IGNORECASE,
)
TRAILING_FRAGMENT_RE = re.compile(
    r"\b(?:after|before|during|when|while|unless|until|if|because|than|from|to|of|"
    r"for|with|without|between|within|on|in|at|by|or|and|the|a|an)$",
    re.IGNORECASE,
)
SITUATION_PROMPT_TAIL_RE = re.compile(
    r"\s*What action best complies with\s+[^?]+\?\s*$",
    re.IGNORECASE,
)
SITUATION_SCAFFOLD_RE = re.compile(
    r"^You are working traffic and this section governs the situation\.\s*",
    re.IGNORECASE,
)
DOCUMENT_CONTROL_SUBSTANCE_RE = re.compile(
    r"\b(?:canceled|cancelled|retained|prescribes?|applies?|available|distributed|"
    r"distribution|responsible|submi(?:t|tted)|contact|found|effective|published|"
    r"updated|revised|identified|omitted|establishes?)\b",
    re.IGNORECASE,
)
GENERIC_SUBJECT_HEADS = {
    "information",
    "procedure",
    "procedures",
    "authorization",
    "method",
    "separation",
    "equipment",
    "action",
    "rule",
    "instruction",
    "concurrence",
    "items",
    "distances",
    "flights",
    "service",
    "responsibility",
    "point",
    "maneuvers",
}
GENERIC_EXAMPLE_INSTRUCTION = "Is this approved phraseology?"
LEGACY_GENERIC_EXAMPLE_INSTRUCTIONS = {
    "Is this an approved example?",
    "Is this an approved example from the section?",
    "Is this approved wording?",
}
GENERIC_EXAMPLE_TOPIC_WORDS = {
    "application",
    "description",
    "example",
    "examples",
    "general",
    "information",
    "purpose",
    "responsibility",
    "section",
}
EXAMPLE_TOPIC_STOPWORDS = {"a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "with"}
EXAMPLE_TOPIC_ACRONYMS = {
    "ADS-B",
    "ASOS",
    "ATIS",
    "AWOS",
    "CPDLC",
    "ERAM",
    "GCA",
    "GPS",
    "IFR",
    "ILS",
    "MDA",
    "MVA",
    "NDB",
    "NTZ",
    "PRM",
    "RNAV",
    "RNP",
    "RVR",
    "RVSM",
    "SID",
    "SOIA",
    "STAR",
    "STARS",
    "TCAS",
    "UAS",
    "VFR",
    "VOR",
    "WAAS",
}
EXAMPLE_CHECK_CUSTOM_INSTRUCTION_PATTERNS = (
    (
        re.compile(
            r"\b(?:debris[−-]generating space launch or reentry vehicle mishaps|system situations)\b",
            re.IGNORECASE,
        ),
        "Is this an approved advisory?",
    ),
    (re.compile(r"\bsafety alert\b", re.IGNORECASE), "Is this an approved safety alert?"),
    (re.compile(r"\blow level wind shear/microburst advisories\b", re.IGNORECASE), "Is this an approved wind shear advisory?"),
    (
        re.compile(
            r"\b(?:unmanned aircraft system \(uas\) activity information\.?|bird activity information|"
            r"traffic information|approach information|altitude information|clearance information|"
            r"observed abnormalities|landing area condition|content)\b",
            re.IGNORECASE,
        ),
        "Is this approved information to issue?",
    ),
    (
        re.compile(
            r"\b(?:landing clearance|takeoff clearance|approach clearance|departure clearances?|"
            r"abbreviated departure clearance|clearance for visual approach)\b",
            re.IGNORECASE,
        ),
        "Is this an approved clearance?",
    ),
    (
        re.compile(
            r"\b(?:arrival instructions|low approach and touch-and-go|ground traffic movement|"
            r"taxi and ground movement operations|ground operations|overhead maneuver|runway exiting|"
            r"initial heading|line up and wait|cancellation of ifr flight plan)\b",
            re.IGNORECASE,
        ),
        "Is this an approved instruction?",
    ),
    (re.compile(r"\binterphone message format\b", re.IGNORECASE), "Is this an approved interphone transmission?"),
    (re.compile(r"\bradio communications\b", re.IGNORECASE), "Is this an approved radio instruction?"),
    (re.compile(r"\bformation flights\b", re.IGNORECASE), "Is this approved formation-flight phraseology?"),
    (re.compile(r"\brvsm operations\b", re.IGNORECASE), "Is this approved RVSM phraseology?"),
    (re.compile(r"\bemphasis for clarity\b", re.IGNORECASE), "Is this approved phraseology for clarity?"),
    (re.compile(r"\baircraft identification\b", re.IGNORECASE), "When identifying the aircraft, is this the correct spoken identification?"),
    (re.compile(r"\bdescription of aircraft types\b", re.IGNORECASE), "When describing the aircraft type, is this the correct spoken description?"),
    (re.compile(r"\bairspace classes\b", re.IGNORECASE), "Is this approved airspace phraseology?"),
    (re.compile(r"\bpilot acknowledgment/read back\b", re.IGNORECASE), "Is this an approved readback?"),
    (re.compile(r"\bnumbers usage\b", re.IGNORECASE), "Is this the approved way to state the number?"),
    (re.compile(r"\bnumber clarification\b", re.IGNORECASE), "Is this an approved number clarification?"),
    (re.compile(r"\bair traffic service\b.*\broutes?\b", re.IGNORECASE), "When stating the ATS route designator, is this correct?"),
    (re.compile(r"\broute use\b", re.IGNORECASE), "Is this the approved way to state the route?"),
    (re.compile(r"\bnavaid terms\b", re.IGNORECASE), "Is this the approved way to state the navaid reference?"),
    (re.compile(r"\bnavaid fixes\b", re.IGNORECASE), "Is this the approved way to state the fix?"),
    (re.compile(r"\bbraking action\b", re.IGNORECASE), "Is this approved braking-action information?"),
    (re.compile(r"\barresting system operation\b", re.IGNORECASE), "Is this approved arresting-system information?"),
    (re.compile(r"\broute or altitude amendments\b", re.IGNORECASE), "When amending route or altitude, is this the correct clearance?"),
    (re.compile(r"\bmilitary turbojet en route descent\b", re.IGNORECASE), "When issuing approach-expectation information, is this the correct transmission?"),
    (re.compile(r"\bside[−-]step maneuver\b", re.IGNORECASE), "Is this an approved side-step clearance?"),
    (re.compile(r"\belevation failure\b", re.IGNORECASE), "Is this approved PAR phraseology?"),
    (re.compile(r"\bpassing or diverging\b", re.IGNORECASE), "Is this an approved traffic call?"),
    (re.compile(r"\bvfr-on-top\b", re.IGNORECASE), "Is this an approved VFR-on-top clearance?"),
    (re.compile(r"\blongitudinal separation\b", re.IGNORECASE), "Is this an approved separation instruction?"),
    (re.compile(r"\bmach number technique\b", re.IGNORECASE), "When assigning a Mach number, is this the correct transmission?"),
    (re.compile(r"\bflynet\b", re.IGNORECASE), "Is this approved FLYNET phraseology?"),
)
EXAMPLE_CHECK_CUSTOM_EXPLANATION_PATTERNS = (
    (
        re.compile(
            r"\b(?:debris[−-]generating space launch or reentry vehicle mishaps|system situations)\b",
            re.IGNORECASE,
        ),
        "approved advisories include",
    ),
    (re.compile(r"\bsafety alert\b", re.IGNORECASE), "approved safety alerts include"),
    (re.compile(r"\blow level wind shear/microburst advisories\b", re.IGNORECASE), "approved wind shear advisories include"),
    (
        re.compile(
            r"\b(?:unmanned aircraft system \(uas\) activity information\.?|bird activity information|"
            r"traffic information|approach information|altitude information|clearance information|"
            r"observed abnormalities|landing area condition|content)\b",
            re.IGNORECASE,
        ),
        "approved information includes",
    ),
    (
        re.compile(
            r"\b(?:landing clearance|takeoff clearance|approach clearance|departure clearances?|"
            r"abbreviated departure clearance|clearance for visual approach)\b",
            re.IGNORECASE,
        ),
        "approved clearances include",
    ),
    (
        re.compile(
            r"\b(?:arrival instructions|low approach and touch-and-go|ground traffic movement|"
            r"taxi and ground movement operations|ground operations|overhead maneuver|runway exiting|"
            r"initial heading|line up and wait|cancellation of ifr flight plan)\b",
            re.IGNORECASE,
        ),
        "approved instructions include",
    ),
    (re.compile(r"\binterphone message format\b", re.IGNORECASE), "approved interphone transmissions include"),
    (re.compile(r"\bradio communications\b", re.IGNORECASE), "approved radio instructions include"),
    (re.compile(r"\bformation flights\b", re.IGNORECASE), "approved formation-flight phraseology includes"),
    (re.compile(r"\brvsm operations\b", re.IGNORECASE), "approved RVSM phraseology includes"),
    (re.compile(r"\bemphasis for clarity\b", re.IGNORECASE), "approved phraseology for clarity includes"),
    (re.compile(r"\baircraft identification\b", re.IGNORECASE), "correct spoken aircraft identifications include"),
    (re.compile(r"\bdescription of aircraft types\b", re.IGNORECASE), "correct spoken aircraft-type descriptions include"),
    (re.compile(r"\bairspace classes\b", re.IGNORECASE), "approved airspace phraseology includes"),
    (re.compile(r"\bpilot acknowledgment/read back\b", re.IGNORECASE), "approved readbacks include"),
    (re.compile(r"\bnumbers usage\b", re.IGNORECASE), "approved number phraseology includes"),
    (re.compile(r"\bnumber clarification\b", re.IGNORECASE), "approved number clarifications include"),
    (re.compile(r"\bair traffic service\b.*\broutes?\b", re.IGNORECASE), "correct ATS route designators include"),
    (re.compile(r"\broute use\b", re.IGNORECASE), "approved route phraseology includes"),
    (re.compile(r"\bnavaid terms\b", re.IGNORECASE), "approved navaid phraseology includes"),
    (re.compile(r"\bnavaid fixes\b", re.IGNORECASE), "approved fix phraseology includes"),
    (re.compile(r"\bbraking action\b", re.IGNORECASE), "approved braking-action information includes"),
    (re.compile(r"\barresting system operation\b", re.IGNORECASE), "approved arresting-system information includes"),
    (re.compile(r"\broute or altitude amendments\b", re.IGNORECASE), "correct route-or-altitude amendments include"),
    (re.compile(r"\bmilitary turbojet en route descent\b", re.IGNORECASE), "correct approach-expectation transmissions include"),
    (re.compile(r"\bside[−-]step maneuver\b", re.IGNORECASE), "approved side-step clearances include"),
    (re.compile(r"\belevation failure\b", re.IGNORECASE), "approved PAR phraseology includes"),
    (re.compile(r"\bpassing or diverging\b", re.IGNORECASE), "approved traffic calls include"),
    (re.compile(r"\bvfr-on-top\b", re.IGNORECASE), "approved VFR-on-top clearances include"),
    (re.compile(r"\blongitudinal separation\b", re.IGNORECASE), "approved separation instructions include"),
    (re.compile(r"\bmach number technique\b", re.IGNORECASE), "correct Mach-number transmissions include"),
    (re.compile(r"\bflynet\b", re.IGNORECASE), "approved FLYNET phraseology includes"),
)
EXAMPLE_CHECK_CUSTOM_BY_PARA = {
    "2-1-21": (
        "Is this an approved traffic advisory?",
        "approved traffic advisories include",
    ),
    "2-1-22": (
        "Is this an approved UAS advisory?",
        "approved UAS advisories include",
    ),
    "2-1-23": (
        "Is this an approved bird-activity advisory?",
        "approved bird-activity advisories include",
    ),
    "2-2-11": (
        "Is this an approved amended-flight-data transmission?",
        "approved amended-flight-data transmissions include",
    ),
    "2-3-8": (
        "When forwarding equipment capability, is this the correct suffix transmission?",
        "correct equipment-suffix transmissions include",
    ),
    "2-4-15": (
        "Is this approved duplicate-call-sign phraseology?",
        "approved duplicate-call-sign phraseology includes",
    ),
    "2-4-21": (
        "When describing the aircraft type, is this the correct spoken description?",
        "correct spoken aircraft-type descriptions include",
    ),
    "2-5-1": (
        "When stating the ATS route designator, is this correct?",
        "correct ATS route designators include",
    ),
    "2-6-4": (
        "Is this approved weather-deviation phraseology?",
        "approved weather-deviation phraseology includes",
    ),
    "2-8-3": (
        "Is this approved RVR phraseology?",
        "approved RVR phraseology includes",
    ),
    "2-9-2": (
        "When updating ATIS information, is this the correct broadcast?",
        "correct ATIS updates include",
    ),
    "2-9-3": (
        "Is this approved ATIS broadcast content?",
        "approved ATIS broadcast content includes",
    ),
    "3-1-6": (
        "When issuing traffic information, is this the correct advisory?",
        "correct traffic-information advisories include",
    ),
    "3-1-9": (
        "Is this approved display-aided traffic information?",
        "approved display-aided traffic information includes",
    ),
    "3-1-10": (
        "When advising a pilot of an observed abnormality, is this the correct advisory?",
        "correct abnormal-condition advisories include",
    ),
    "3-3-1": (
        "Is this an approved runway-condition report?",
        "approved runway-condition reports include",
    ),
    "3-7-1": (
        "Is this an approved movement-area instruction?",
        "approved movement-area instructions include",
    ),
    "3-7-3": (
        "Is this an approved ground-operations instruction?",
        "approved ground-operations instructions include",
    ),
    "3-7-2": (
        "Is this an approved ground-movement instruction?",
        "approved ground-movement instructions include",
    ),
    "3-9-4": (
        "Is this an approved line-up-and-wait instruction?",
        "approved line-up-and-wait instructions include",
    ),
    "3-9-10": (
        "Is this an approved takeoff clearance?",
        "approved takeoff clearances include",
    ),
    "3-10-5": (
        "Is this an approved go-around instruction?",
        "approved go-around instructions include",
    ),
    "3-10-4": (
        "Is this approved intersecting-runway phraseology?",
        "approved intersecting-runway phraseology includes",
    ),
    "3-10-6": (
        "Is this an approved anticipatory landing clearance?",
        "approved anticipatory landing clearances include",
    ),
    "3-10-9": (
        "Is this an approved runway-exit instruction?",
        "approved runway-exit instructions include",
    ),
    "3-10-12": (
        "Is this an approved overhead-maneuver instruction?",
        "approved overhead-maneuver instructions include",
    ),
    "3-7-6": (
        "Is this an approved missed-approach advisory?",
        "approved missed-approach advisories include",
    ),
    "4-2-5": (
        "When amending route or altitude, is this the correct clearance?",
        "correct route-or-altitude amendments include",
    ),
    "4-2-10": (
        "Is this an approved IFR-cancellation instruction?",
        "approved IFR-cancellation instructions include",
    ),
    "4-3-2": (
        "Is this an approved departure clearance?",
        "approved departure clearances include",
    ),
    "4-3-3": (
        "Is this an approved abbreviated departure clearance?",
        "approved abbreviated departure clearances include",
    ),
    "4-5-7": (
        "Is this an approved altitude assignment?",
        "approved altitude assignments include",
    ),
    "4-7-5": (
        "When issuing approach-expectation information, is this the correct transmission?",
        "correct approach-expectation transmissions include",
    ),
    "4-6-1": (
        "Is this approved holding-clearance phraseology?",
        "approved holding-clearance phraseology includes",
    ),
    "4-7-1": (
        "Is this approved arrival-clearance information?",
        "approved arrival-clearance information includes",
    ),
    "4-7-10": (
        "Is this approved approach information?",
        "approved approach information includes",
    ),
    "4-8-1": (
        "Is this an approved approach clearance?",
        "approved approach clearances include",
    ),
    "4-8-12": (
        "Is this an approved low-approach instruction?",
        "approved low-approach instructions include",
    ),
    "5-4-3": (
        "Is this approved point-out phraseology?",
        "approved point-out phraseology includes",
    ),
    "5-6-2": (
        "Is this an approved routing instruction?",
        "approved routing instructions include",
    ),
    "5-8-2": (
        "Is this an approved RNAV departure instruction?",
        "approved RNAV departure instructions include",
    ),
    "5-9-3": (
        "If vectors will cross final, is this the required advisory?",
        "required vectors-across-final advisories include",
    ),
    "5-9-4": (
        "Is this an approved approach-frequency transfer instruction?",
        "approved approach-frequency transfer instructions include",
    ),
    "5-7-2": (
        "Is this an approved speed assignment?",
        "approved speed assignments include",
    ),
    "7-2-1": (
        "When approving visual separation, is this the correct advisory?",
        "correct visual-separation advisories include",
    ),
    "7-4-3": (
        "Is this an approved visual-approach traffic advisory?",
        "approved visual-approach traffic advisories include",
    ),
}
EXAMPLE_CHECK_PREFER_FALSE_PARA_IDS = {
    "2-2-11",
    "2-4-20",
    "2-4-21",
    "2-5-1",
    "3-1-10",
    "4-8-1",
    "5-4-3",
    "8-3-3",
}
EXAMPLE_CHECK_TRUE_ONLY_PARA_IDS = {
    "2-4-12",
}
EXAMPLE_CHECK_OPERATIONAL_RE = re.compile(
    r"\b(?:contact|monitor|runway|rvr|traffic|tower|ground|approach|departure|arrival|"
    r"transition|center|radio|clearance|climb|maintain|descend|turn|cleared|hold|short|"
    r"report|wind|altimeter|flight level|vfr|ifr|taxi|cross|route|bearing|heading|"
    r"go-around|touch-and-go)\b",
    re.IGNORECASE,
)
EXAMPLE_CHECK_IDENTITY_RE = re.compile(
    r"^(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Tower|Ground|Approach|Departure|Radio|Center)\.?$"
)
EXAMPLE_CHECK_CODE_RE = re.compile(r"^[A-Z]{2,4}\s+\d{5,6}\.?$")
EXAMPLE_CHECK_GROUP_FORM_RE = re.compile(
    r"^[A-Z][A-Za-z0-9-]+\s+"
    r"(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Niner)"
    r"(?:\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Niner))?\.$"
)
EXAMPLE_CHECK_ACRONYM_ID_RE = re.compile(
    r"^[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:[A-Z](?:[-−][A-Z])+)\.?$"
)
EXAMPLE_CHECK_ALTERNATIVE_RE = re.compile(r"/")
EXAMPLE_CHECK_PLACEHOLDER_RE = re.compile(r"[()]")
EXAMPLE_CHECK_THIN_ACK_RE = re.compile(r"\bRoger\.$", re.IGNORECASE)
EXAMPLE_CHECK_TRUNCATED_DOTS_RE = re.compile(r"(?:\.\s*){3,}|…")
EXAMPLE_CHECK_DETAIL_RE = re.compile(
    r"\b(?:taxi via|cross runway|hold short of|cleared to|expect further clearance|"
    r"point out|attention all aircraft|traffic,|unable radar vectors)\b",
    re.IGNORECASE,
)
EXAMPLE_CHECK_SUPPORT_RE = re.compile(r"\bunable radar vectors\b", re.IGNORECASE)
EXAMPLE_FALSE_NUMBER_WORDS = {
    "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINER",
    "TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN",
    "SEVENTEEN", "EIGHTEEN", "NINETEEN", "TWENTY", "THIRTY", "FORTY", "FIFTY",
    "SIXTY", "SEVENTY", "EIGHTY", "NINETY", "HUNDRED", "THOUSAND",
}
EXAMPLE_FALSE_PHONETIC_WORDS = {
    "ALFA", "ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF",
    "HOTEL", "INDIA", "JULIET", "JULIETT", "KILO", "LIMA", "MIKE", "NOVEMBER",
    "OSCAR", "PAPA", "QUEBEC", "ROMEO", "SIERRA", "TANGO", "UNIFORM", "VICTOR",
    "WHISKEY", "XRAY", "X-RAY", "YANKEE", "ZULU",
}
EXAMPLE_FALSE_DIRECTION_WORDS = {
    "LEFT", "RIGHT", "NORTH", "SOUTH", "EAST", "WEST",
    "NORTHEAST", "NORTHWEST", "SOUTHEAST", "SOUTHWEST",
}
EXAMPLE_FALSE_FACILITY_WORDS = {"CENTER", "APPROACH", "GROUND", "TOWER", "DEPARTURE", "ARRIVAL", "RADIO"}
EXAMPLE_FALSE_SLOT_CONTEXT_WORDS = {
    "RUNWAY", "TAXIWAY", "FL", "FLIGHT", "LEVEL", "MACH", "HEADING", "DEGREES",
    "RADIAL", "LOCALIZER", "COURSE", "FIX", "MILE", "MILES", "FEET",
    "VOR", "VORTAC", "NDB", "ILS", "RVR", "INFORMATION", "CODE", "TRANSITION",
    "DIRECT", "VIA", "TO", "FROM", "AT", "OF",
}
EXAMPLE_FALSE_STRUCTURAL_WORDS = {
    "AND", "OR", "ATTENTION", "CAUTION", "UNABLE", "APPROVED", "ACTIVE",
    "INACTIVE", "ABOVE", "BELOW", "ARRIVAL", "DEPARTURE", "MORE", "LESS",
}
EXAMPLE_CHECK_PREFERRED_PATTERNS_BY_PARA = {
    "2-1-21": re.compile(r'^"Traffic,', re.IGNORECASE),
}
EXAMPLE_FALSE_BAD_PATTERNS = (
    re.compile(r"\bproceed short\b", re.IGNORECASE),
    re.compile(r"\bread back proceed instructions\b", re.IGNORECASE),
    re.compile(r'^"?Decimal Out\b', re.IGNORECASE),
    re.compile(r'^"?Climb Mach\b', re.IGNORECASE),
)
LIST_MEMBERSHIP_ITEM_RE = re.compile(
    r"^The section's list(?: does not)? includes:\s*(.+)$",
    re.IGNORECASE,
)
DOCUMENT_CONTROL_TEXT_RE = re.compile(
    r"\b(?:this order|order|changes?|published|publication|effective|website|distributed|"
    r"distribution|applies?|waivers?|safety|sms|directives?|subscribers?|submissions?)\b",
    re.IGNORECASE,
)
SCOPE_TEXT_RE = re.compile(
    r"\b(?:applies?|apply|used?|use|responsib(?:le|ility)|required|must|need not|"
    r"does not relieve|relieves|familiar|adhere|recorded|annotate|specify|subject to|"
    r"solely|authorized|available|distributed|cancel(?:ed|led)?|found|set forth as)\b",
    re.IGNORECASE,
)
REQUIREMENT_TEXT_RE = re.compile(
    r"\b(?:must|shall|should|required|need not|may not|do not|only if|only when|"
    r"unless|use|monitor|terminate|transmit|record|relay|specify|continue|"
    r"annotate|identify|forward|advise|inform|interrupt|retain|clear|assign|"
    r"provide|separate|authorize|approve|insert|coordinate|advisable|"
    r"instruct|direct|turn|change|apply|delay|may)\b",
    re.IGNORECASE,
)
CAPABILITY_TEXT_RE = re.compile(
    r"\b(?:is an integrated function|uses?|provides?|predicts?|deriv(?:e|es)|"
    r"records?|automatically recorded|is based on|are based on|is not based on|"
    r"are not based on|will remove|will not remove|"
    r"may be affected|establishes procedures|supports?|needed for|capabilit(?:y|ies))\b",
    re.IGNORECASE,
)
MINIMA_RULE_TEXT_RE = re.compile(
    r"\b(?:minimum|minima|mile|miles|foot|feet|flight level|laterally|vertically|"
    r"above|below|protected airspace|separation|29\.92|altimeter|agl|nm|"
    r"minute|minutes|interval)\b",
    re.IGNORECASE,
)
CONDITIONAL_ACTION_RE = re.compile(
    r"\b(?:must|may|should|required|authorize|continue|apply|add|take|turn|use|notify|"
    r"contact|submit|retain|review|coordinate|maintain|state|determine|distribute|"
    r"provide|cancel|prescribe|remove)\b",
    re.IGNORECASE,
)
TERM_DEFINITION_FALLBACK_RE = re.compile(
    r"\b(?:is based on|are based on|is set forth as|are set forth as|means|refers to)\b",
    re.IGNORECASE,
)


async def generate_activities_for_paragraph(
    para_id: str,
    para_title: str,
    blocks: list[dict],
    types: Optional[list[str]] = None,
) -> dict[str, list[dict]]:
    """
    Generate activities for one paragraph without external API calls.
    """
    by_type: dict[str, list[str]] = {}
    for block in blocks:
        block_type = block.get("block_type", "body")
        by_type.setdefault(block_type, []).append(block.get("content", ""))

    def joined(*block_types: str) -> str:
        return "\n\n".join(
            text for block_type in block_types for text in by_type.get(block_type, [])
        ).strip()

    generators = {
        "phraseology_builder": (_gen_phraseology_builder, joined("phraseology")),
        "spot_the_error": (_gen_spot_the_error, joined("phraseology")),
        "sequence_steps": (_gen_sequence_steps, joined("body")),
        "match_pairs": (_gen_match_pairs, joined("body", "note", "interpretation")),
        "readback_check": (_gen_readback_check, joined("phraseology", "example")),
        "situation_action": (_gen_situation_action, joined("body", "note", "exception")),
        "directive_check": (_gen_directive_check, joined("body", "note", "exception")),
        "conditional_rule_check": (_gen_conditional_rule_check, joined("body", "note", "exception")),
        "term_definition_check": (_gen_term_definition_check, joined("body", "note", "interpretation")),
        "document_control_check": (_gen_document_control_check, joined("body", "note", "reference")),
        "requirement_check": (_gen_requirement_check, joined("body", "note", "reference", "exception")),
        "scope_check": (_gen_scope_check, joined("body", "note", "reference", "exception")),
        "capability_check": (_gen_capability_check, joined("body", "note", "interpretation")),
        "reference_check": (_gen_reference_check, joined("reference", "body")),
        "minima_rule_check": (_gen_minima_rule_check, joined("body", "note", "exception")),
        "list_membership": (_gen_list_membership, joined("body", "note", "exception")),
        "table_lookup": (_gen_table_lookup, joined("body", "note", "exception")),
        "example_check": (_gen_example_check, joined("example")),
        "knowledge_check": (_gen_knowledge_check, joined("body", "note", "exception", "interpretation")),
    }

    # Reference checks teach citation matching rather than ATC procedure substance.
    # Keep the generator available for explicit regression/debug calls, but do not
    # include it in normal activity generation.
    requested = types or [slug for slug in generators.keys() if slug != "reference_check"]
    results: dict[str, list[dict]] = {}

    for slug in requested:
        generator = generators.get(slug)
        if not generator:
            continue
        gen_fn, content = generator
        if not content:
            continue
        activities = gen_fn(para_id, para_title, content)
        if activities:
            results[slug] = activities

    merged = merge_curated_activities(para_id, results, requested)
    validated_results: dict[str, list[dict]] = {}
    for slug, activities in merged.items():
        validated: list[dict] = []
        for activity in activities:
            normalized = normalize_activity_payload(slug, activity, para_title, para_id)
            if not validate_activity_payload(slug, normalized, para_title):
                validated.append(normalized)
        if validated:
            validated_results[slug] = validated

    return validated_results


def _gen_phraseology_builder(para_id: str, para_title: str, content: str) -> list[dict]:
    # Phraseology reconstruction now depends on curated, scenario-authored items.
    # Auto-picking a fragment from a paragraph routinely produces context-free or
    # semantically wrong drills.
    return []


def _gen_spot_the_error(para_id: str, para_title: str, content: str) -> list[dict]:
    lines = phraseology_lines_from_text(content)
    if not lines:
        return []

    candidates = sorted(
        ((score_phraseology_line(line, "error"), line) for line in lines),
        key=lambda item: (-item[0], item[1]),
    )

    line = None
    mutated = None
    for score, candidate_line in candidates:
        upper_line = candidate_line.upper()
        if score < 2:
            continue
        if len(candidate_line.split()) < 5:
            continue
        if re.search(r"\bOR\b", upper_line):
            continue
        if upper_line.endswith((" AT", " OF", " AND", " OR", " TO", " VIA")):
            continue
        candidate_mutation = mutate_phrase_line(
            candidate_line,
            f"{para_id}:spot:{candidate_line}",
            allow_generic=False,
        )
        if candidate_mutation:
            line = candidate_line
            mutated = candidate_mutation
            break

    if not line or not mutated:
        return []

    return [{
        "instruction": "One word in this phraseology is incorrect. Tap it.",
        "original_phrase": line,
        "display_text": mutated["display_text"],
        "tokens": mutated["tokens"],
        "error_index": mutated["error_index"],
        "correct_token": mutated["correct_token"],
        "explanation": f"Per {para_id}: the correct phraseology is '{line}'.",
        "difficulty": 2,
    }]


def _gen_sequence_steps(para_id: str, para_title: str, content: str) -> list[dict]:
    steps = extract_steps_from_text(content)
    if len(steps) < 3:
        return []

    ordered = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{para_id}:{idx}:{step}"))[:8],
            "text": step,
        }
        for idx, step in enumerate(steps)
    ]
    shuffled = ordered[:]
    shuffled.sort(key=lambda item: item["id"])

    return [{
        "instruction": "Place these steps in the correct procedural order.",
        "steps": shuffled,
        "correct_order": [step["id"] for step in ordered],
        "explanation": f"Per {para_id}, the procedure follows the order shown in the source text.",
        "difficulty": 2,
    }]


def _gen_match_pairs(para_id: str, para_title: str, content: str) -> list[dict]:
    pairs = extract_term_pairs_from_text(content)
    if len(pairs) < 3:
        return []

    return [{
        "instruction": "Match each term with its correct definition.",
        "pairs": [{"term": term, "definition": definition} for term, definition in pairs],
        "difficulty": 1,
    }]


def _gen_readback_check(para_id: str, para_title: str, content: str) -> list[dict]:
    lines = phraseology_lines_from_text(content)
    if not lines:
        return []

    clearance = pick_best_phraseology_line(lines, f"{para_id}:readback", purpose="readback")
    if not clearance:
        return []

    payload = build_readback_choices(clearance, f"{para_id}:readback")
    if not payload:
        return []

    return [{
        "instruction": "The controller issued this clearance. Which pilot read-back is correct?",
        "clearance": payload["clearance"],
        "choices": payload["choices"],
        "explanation": f"Per {para_id}, the pilot should read back the key clearance elements accurately.",
        "difficulty": 2,
    }]


def _gen_situation_action(para_id: str, para_title: str, content: str) -> list[dict]:
    sentences = meaningful_sentences_from_text(content)
    if not sentences:
        return []

    para_context = select_action_sentence(para_title, sentences)
    if not para_context:
        return []

    correct_action = para_context
    if not correct_action.endswith("."):
        correct_action += "."

    situation = build_situation_prompt(para_id, para_title, para_context)

    return [{
        "instruction": "What should you do?",
        "situation": situation,
        "para_context": para_context,
        "choices": build_action_choices(correct_action, f"{para_id}:situation", situation),
        "explanation": f"Per {para_id}: {para_context}",
        "difficulty": 2,
    }]


def _boolean_choices(correct_is_true: bool) -> list[dict]:
    return [
        {"text": "True", "is_correct": correct_is_true},
        {"text": "False", "is_correct": not correct_is_true},
    ]


def _fragment_text(text: str) -> str:
    clean = normalize_display_text(text)
    if not clean:
        return clean
    first_word = clean.split()[0]
    if first_word.isupper() and len(first_word) <= 5:
        return clean
    return f"{clean[:1].lower()}{clean[1:]}"


def _sentence_with_period(text: str) -> str:
    clean = normalize_display_text(text)
    if not clean:
        return clean
    if clean.endswith((".", "!", "?")):
        return clean
    return f"{clean}."


def _capitalize_lead(text: str) -> str:
    clean = normalize_display_text(text)
    if not clean:
        return clean
    return f"{clean[:1].upper()}{clean[1:]}"


def _normalize_document_structure_text(text: str) -> str:
    clean = text
    clean = re.sub(
        r"\bauthorized fourth-line entries specified in the section, a facility directive, or an LOA\b",
        "authorized fourth-line entries specified by the procedure, a facility directive, or an LOA",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bonly messages specified in the section, a facility directive, or an LOA\b",
        "only messages specified by the procedure, a facility directive, or an LOA",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthe procedures in this section\b",
        "these procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthese procedures are to be used solely in oceanic airspace\b",
        "Oceanic procedures are to be used solely in oceanic airspace",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bprocedures stated in this section\b",
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
        r"\bfor the purposes of ([^,.]+?) contained in this section\b",
        r"for \1",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:from|in|under) the section\b(?!')",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bmatches the section\b",
        "is correct",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthe section's ([A-Za-z-]+) procedures\b",
        r"these \1 procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 7, Visual, Section 6, Basic Radar Service to VFR Aircraft[−-]\s*Terminal\b",
        "basic terminal radar service to VFR aircraft",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bbasic services described in Chapter 7, Visual, Section 6, Basic Radar Service to VFR Aircraft[−-]\s*Terminal\b",
        "basic terminal radar services to VFR aircraft",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bbasic services described in basic terminal radar service[s]? to VFR aircraft\b",
        "basic terminal radar services to VFR aircraft",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bIn accordance with Chapter 8, Offshore/Oceanic Procedures, Section 4, Lateral Separation,\s*",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 8, Offshore/Oceanic Procedures, Section 2, Coordination\b",
        "offshore/oceanic coordination procedures",
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
        r"\bChapter 11, Section 3\b",
        "overdue-aircraft procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bChapter 10, Section 3\b",
        "overdue-aircraft procedures",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\bthe these\b", "these", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+([?.!])", r"\1", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    clean = re.sub(r"\s+:", ":", clean)
    return clean


def _normalize_choice_text(text: str) -> str:
    clean = normalize_display_text(text)
    if not clean:
        return clean
    clean = _normalize_document_structure_text(clean)
    clean = re.sub(r"\bthe paragraph's\b", "the section's", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bthis paragraph\b", "the section", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bthe paragraph\b(?!')", "the section", clean, flags=re.IGNORECASE)
    return _capitalize_lead(clean)


def _is_true_false_choice_activity(payload: dict) -> bool:
    choices = payload.get("choices", [])
    if len(choices) != 2:
        return False
    labels = {normalise_ws(choice.get("text", "")).lower() for choice in choices}
    return labels == {"true", "false"}


def _statement_instruction(para_title: str) -> str:
    return "Is this statement operationally correct?"


def _contextualize_statement(para_title: str, question_text: str) -> str:
    title = display_section_label(para_title)
    clean = normalize_display_text(question_text)
    if not clean or re.match(r"^This order\b", clean, re.IGNORECASE):
        return clean
    under_match = UNDER_PREFIX_RE.match(clean)
    if under_match:
        clean = under_match.group(1).strip()
        if DIRECT_QUESTION_RE.match(clean):
            return _capitalize_lead(clean)
    match = re.match(r"^(This|These|That|Those)\s+(.+)$", clean)
    if not match:
        return _capitalize_lead(clean)

    body = match.group(2)
    if not title:
        return _capitalize_lead(body)
    lower_body = body.lower()
    lower_title = title.lower()
    title_tokens = set(re.findall(r"[A-Za-z]{3,}", lower_title))

    if lower_title in lower_body:
        return _capitalize_lead(body)

    head_match = re.match(r"^([A-Za-z][A-Za-z/-]*)(?:\s+|$)", body)
    head = head_match.group(1).lower() if head_match else ""
    singular_head = head.rstrip("s")
    if head and (head in title_tokens or singular_head in title_tokens):
        remainder = body[len(head_match.group(1)):].lstrip()
        return f"{title}{' ' + remainder if remainder else ''}"

    if head in GENERIC_SUBJECT_HEADS:
        return _capitalize_lead(body)

    return _capitalize_lead(body)


def _normalize_question_text(
    activity_type: str,
    para_title: str,
    question_text: str,
    *,
    is_true_false: bool,
) -> str:
    clean = normalize_display_text(question_text)
    if not clean:
        return clean
    clean = _normalize_document_structure_text(clean)
    under_match = UNDER_PREFIX_RE.match(clean)
    if under_match:
        clean = under_match.group(1).strip()
        if DIRECT_QUESTION_RE.match(clean):
            return _capitalize_lead(clean)
    clean = INLINE_PARA_REF_RE.sub("", clean)
    clean = re.sub(r"\s+([?.!])", r"\1", clean)
    if (
        MATCHES_PARAGRAPH_RE.match(clean)
        or SUPPORTED_BY_SECTION_RE.match(clean)
        or clean == "Select the statement supported by the section."
    ):
        return "Select the correct statement."
    list_match = LIST_MEMBERSHIP_RE.match(clean)
    if list_match:
        item = list_match.group("item").rstrip(".")
        return _sentence_with_period(item)
    section_list_match = SECTION_LIST_PROMPT_RE.match(clean)
    if section_list_match:
        return _sentence_with_period(section_list_match.group("item").rstrip("."))
    if activity_type in SELF_CONTAINED_STATEMENT_TYPES and is_true_false:
        return _contextualize_statement(para_title, clean)
    if activity_type == "fill_blank":
        clean = re.sub(
            r"^Complete the phraseology from [^:]+:\s*",
            "Complete the phraseology: ",
            clean,
            flags=re.IGNORECASE,
        )
    return _capitalize_lead(clean)


def normalize_activity_payload(
    activity_type: str,
    payload: dict,
    para_title: str = "",
    para_id: str = "",
) -> dict:
    normalized = dict(payload)
    is_true_false = _is_true_false_choice_activity(normalized)
    instruction = normalize_display_text(normalized.get("instruction", ""))
    if instruction:
        instruction = _normalize_document_structure_text(instruction)
        instruction = re.sub(r"\bthe paragraph's\b", "the section's", instruction, flags=re.IGNORECASE)
        instruction = re.sub(r"\bthis paragraph\b", "the section", instruction, flags=re.IGNORECASE)
        instruction = re.sub(r"\bthe paragraph\b(?!')", "the section", instruction, flags=re.IGNORECASE)
        instruction = re.sub(r"\bin this paragraph\b", "in the section", instruction, flags=re.IGNORECASE)
        instruction = re.sub(r"\bunder this paragraph\b", "in the section", instruction, flags=re.IGNORECASE)
        instruction = re.sub(r"\bfrom the paragraph\b", "from the section", instruction, flags=re.IGNORECASE)
        instruction = re.sub(r"\bmatches the paragraph\b", "matches the section", instruction, flags=re.IGNORECASE)
        if instruction == "Does this citation statement match the section?":
            instruction = "Does this citation match the section's reference?"
        if instruction == "Does this statement match the section?":
            instruction = "Is this statement correct?"
        if instruction == "Which statement is supported by the section?":
            instruction = "Which statement is correct?"
        if instruction == "Is this statement supported by the section?":
            instruction = "Is this statement correct?"
        if instruction == "Choose the correct answer based on the section.":
            instruction = "Choose the correct answer."
        normalized["instruction"] = instruction

    if activity_type == "situation_action" and "situation" in normalized:
        situation = normalize_display_text(normalized.get("situation", ""))
        if situation:
            situation = SITUATION_SCAFFOLD_RE.sub(
                "You are handling traffic and need to decide the correct controller action. ",
                situation,
            )
            situation = SITUATION_PROMPT_TAIL_RE.sub("", situation).strip()
            if situation and not re.search(r"[.?!]$", situation):
                situation = f"{situation}."
            normalized["situation"] = _capitalize_lead(situation)

    if activity_type == "phraseology_builder":
        target_phrase = normalize_display_text(normalized.get("target_phrase", ""))
        if target_phrase:
            normalized["target_phrase"] = target_phrase
            if not normalise_ws(normalized.get("instruction", "")):
                normalized["instruction"] = "Build the controller transmission."
            if not normalise_ws(normalized.get("explanation", "")):
                normalized["explanation"] = f'The correct transmission is "{target_phrase}."'
            word_bank = normalized.get("word_bank")
            correct_sequence = normalized.get("correct_sequence")
            if not word_bank or not correct_sequence:
                seed_key = para_id or para_title or target_phrase
                built_bank, built_sequence = make_word_bank(target_phrase, seed_key)
                normalized["word_bank"] = built_bank
                normalized["correct_sequence"] = built_sequence

    if "question_text" in normalized:
        normalized["question_text"] = _normalize_question_text(
            activity_type,
            para_title,
            normalized.get("question_text", ""),
            is_true_false=is_true_false,
        )
    if "choices" in normalized and isinstance(normalized["choices"], list):
        normalized["choices"] = [
            {
                **choice,
                "text": _normalize_choice_text(choice.get("text", "")),
            }
            if isinstance(choice, dict) and "text" in choice
            else choice
            for choice in normalized["choices"]
        ]
    for field in (
        "instruction",
        "question_text",
        "situation",
        "para_context",
        "explanation",
        "clearance",
        "target_phrase",
        "display_text",
        "masked_text",
        "full_phrase",
        "original_phrase",
    ):
        if isinstance(normalized.get(field), str):
            normalized[field] = _normalize_document_structure_text(
                normalize_display_text(normalized[field])
            )
    if activity_type in SELF_CONTAINED_STATEMENT_TYPES:
        if is_true_false:
            normalized["instruction"] = _statement_instruction(para_title)
        else:
            instruction = normalise_ws(normalized.get("instruction", ""))
            if not instruction or instruction.startswith("Does this statement about "):
                normalized["instruction"] = "Choose the correct answer."
    elif activity_type == "list_membership":
        instruction = normalise_ws(normalized.get("instruction", ""))
        if (
            not instruction
            or instruction == "Does this statement match the paragraph's list?"
            or instruction == "Does this item belong in the section's list?"
        ):
            normalized["instruction"] = "Is this item explicitly included?"
    elif activity_type == "knowledge_check":
        instruction = normalise_ws(normalized.get("instruction", ""))
        if instruction == "Which statement matches this paragraph?":
            normalized["instruction"] = "Which statement is correct?"
        elif instruction == "Is this statement correct for the paragraph?":
            normalized["instruction"] = "Is this statement correct?"
    elif activity_type == "reference_check":
        instruction = normalise_ws(normalized.get("instruction", ""))
        if instruction == "Does this citation match the paragraph's reference?":
            normalized["instruction"] = "Does this citation match the section's reference?"
    elif activity_type == "example_check":
        instruction = normalise_ws(normalized.get("instruction", ""))
        if (
            not instruction
            or "approved examples" in instruction.lower()
            or instruction == GENERIC_EXAMPLE_INSTRUCTION
            or instruction in LEGACY_GENERIC_EXAMPLE_INSTRUCTIONS
        ):
            normalized["instruction"] = _example_check_instruction(para_id, para_title)

    return normalized


def _first_alpha_char(text: str) -> str:
    return next((char for char in text if char.isalpha()), "")


def _build_title_tokens(para_title: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z]{3,}", para_title)
    ]


def _example_topic_text(para_title: str) -> str:
    clean = normalize_display_text(para_title).replace("−", "-").strip(" .")
    if not clean:
        return ""

    words: list[str] = []
    for raw_token in clean.split():
        prefix, core, suffix = split_token_parts(raw_token)
        if not core:
            words.append(raw_token)
            continue
        upper = core.upper()
        alnum = re.sub(r"[^A-Za-z0-9]", "", upper)
        if upper.lower() in EXAMPLE_TOPIC_STOPWORDS:
            display = core.lower()
        elif upper in EXAMPLE_TOPIC_ACRONYMS or (core.isupper() and 1 <= len(alnum) <= 4):
            display = upper
        else:
            display = core.lower()
        words.append(f"{prefix}{display}{suffix}")

    topic = normalise_ws(" ".join(words))
    if topic.lower() in GENERIC_EXAMPLE_TOPIC_WORDS:
        return ""
    return topic


def _example_check_instruction(para_id: str, para_title: str) -> str:
    exact = EXAMPLE_CHECK_CUSTOM_BY_PARA.get(para_id)
    if exact:
        return exact[0]
    for pattern, prompt in EXAMPLE_CHECK_CUSTOM_INSTRUCTION_PATTERNS:
        if pattern.search(para_title):
            return prompt
    topic = _example_topic_text(para_title)
    if topic:
        return f"For {topic}, is this approved phraseology?"
    return GENERIC_EXAMPLE_INSTRUCTION


def _example_check_explanation_prefix(para_id: str, para_title: str) -> str:
    exact = EXAMPLE_CHECK_CUSTOM_BY_PARA.get(para_id)
    if exact:
        return exact[1]
    for pattern, prefix in EXAMPLE_CHECK_CUSTOM_EXPLANATION_PATTERNS:
        if pattern.search(para_title):
            return prefix
    return "approved phraseology includes"


def _find_disallowed_adjacent_duplicate(text: str) -> str:
    previous = ""
    for raw_token in text.split():
        token = split_token_parts(raw_token)[1].upper()
        if not token:
            continue
        if token == previous and token not in ALLOWED_ADJACENT_DUPLICATE_TOKENS:
            return token
        previous = token
    return ""


def _generic_text_errors(text: str, *, allow_quoted_start: bool = False) -> list[str]:
    errors: list[str] = []
    clean = normalise_ws(text)
    if not clean:
        return ["empty text"]

    first_alpha = _first_alpha_char(clean)
    if first_alpha and first_alpha.islower():
        errors.append("starts with lowercase text")
    quote_check_text = re.sub(r'(?<=\d)"', " in", clean)
    if quote_check_text.count('"') % 2:
        errors.append("unbalanced quotes")
    if re.search(r"\s+([,.;:?!])", clean):
        errors.append("contains spacing before punctuation")
    for pattern in LOW_QUALITY_PATTERNS:
        if pattern.search(clean):
            errors.append(f"matches low-quality pattern: {pattern.pattern}")
    if clean.endswith(":"):
        errors.append("ends with colon")
    if not allow_quoted_start and clean.startswith('"') and not clean.endswith('"') and ':"' not in clean:
        errors.append("quoted text is malformed")
    return errors


def _directive_text_errors(text: str) -> list[str]:
    clean = normalise_ws(text).rstrip(".")
    if not clean:
        return ["directive text is empty"]

    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", clean)
    if not tokens:
        return ["directive text is empty"]

    lower_tokens = [token.lower() for token in tokens]
    if lower_tokens[:2] == ["do", "not"]:
        if len(tokens) < 3 or not IMPERATIVE_START_RE.match(tokens[2]):
            return ["directive does not start with an imperative verb"]
        lead_tokens = tokens[2:5]
    elif IMPERATIVE_START_RE.match(tokens[0]):
        lead_tokens = tokens[:3]
        for token in lead_tokens[1:3]:
            if AUXILIARY_VERB_RE.fullmatch(token):
                return ["directive starts with a declarative subject rather than a command"]
    elif CONDITIONAL_START_RE.match(clean) and INTRO_CLAUSE_IMPERATIVE_RE.search(clean):
        pass
    elif re.search(r"\b(?:must not|must|shall|should|need not)\b", clean, re.IGNORECASE):
        pass
    else:
        return ["directive does not start with a directive clause"]

    errors: list[str] = []
    for pattern in DIRECTIVE_LOW_QUALITY_PATTERNS:
        if pattern.search(clean):
            errors.append(f"directive matches low-quality pattern: {pattern.pattern}")
    return errors


def _question_text_errors(activity_type: str, text: str, para_title: str) -> list[str]:
    errors = _generic_text_errors(
        text,
        allow_quoted_start=activity_type == "example_check",
    )
    clean = normalise_ws(text)
    lower = clean.lower()
    under_match = UNDER_PREFIX_RE.match(clean)
    if under_match:
        under_body = under_match.group(1).strip()
        if DIRECT_QUESTION_RE.match(under_body):
            errors.append("question text depends on a paragraph/title prefix")
        elif DEICTIC_LEAD_RE.match(under_body):
            errors.append("question text depends on removed antecedent")
    elif activity_type in SELF_CONTAINED_STATEMENT_TYPES and DEICTIC_LEAD_RE.match(clean):
        errors.append("question text depends on removed antecedent")
    if INLINE_PARA_REF_RE.search(clean):
        errors.append("question text includes a paragraph id")
    if activity_type not in {"reference_check", "document_control_check"} and DOC_STRUCTURE_REF_RE.search(clean):
        errors.append("question text depends on document cross-references")

    if FIGURE_TABLE_LEAD_RE.match(clean):
        errors.append("question text begins with figure/table reference")
    if MATCHES_PARAGRAPH_RE.match(clean):
        errors.append("question text names a paragraph instead of the concept")
    if SUPPORTED_BY_SECTION_RE.match(clean) or clean == "Select the statement supported by the section.":
        errors.append("question text uses section-scaffold wording")
    if LIST_MEMBERSHIP_RE.match(clean):
        errors.append("question text uses document-structure list wording")
    if SECTION_LIST_PROMPT_RE.match(clean):
        errors.append("question text uses section-list scaffolding")
    if TRAILING_FRAGMENT_RE.search(clean.rstrip(".!?")):
        errors.append("question text ends with incomplete phrase")
    if activity_type != "document_control_check" and CITATION_LEAD_RE.match(clean):
        errors.append("question text is a citation rather than study content")
    if (
        activity_type in SELF_CONTAINED_STATEMENT_TYPES
        and " if " in lower
        and not IMPERATIVE_START_RE.match(clean)
        and not lower.startswith("do not ")
    ):
        lead = re.split(r"\bif\b", clean, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,;:")
        if lead and not AUXILIARY_VERB_RE.search(lead) and len(lead.split()) <= 6:
            errors.append("question text is a list fragment rather than a sentence")

    if activity_type == "conditional_rule_check":
        if not (CONDITIONAL_START_RE.match(clean) or CONDITIONAL_CUE_RE.search(clean)):
            errors.append("conditional rule is missing a conditional cue")
        if not CONDITIONAL_ACTION_RE.search(clean):
            errors.append("conditional rule is missing an action verb")
    elif activity_type == "directive_check":
        errors.extend(_directive_text_errors(clean))
    elif activity_type == "term_definition_check":
        if CONDITIONAL_START_RE.match(clean):
            errors.append("term definition starts like a conditional rule")
        title_tokens = _build_title_tokens(para_title)
        has_title_ref = bool(
            title_tokens and any(re.search(rf"\b{re.escape(token)}\b", lower) for token in title_tokens)
        )
        has_definition_subject = bool(TERM_DEFINITION_PATTERN_RE.match(clean))
        if title_tokens and not (has_title_ref or has_definition_subject):
            errors.append("term definition does not identify a defined subject")
        if not (DEFINITION_CUE_RE.search(clean) or TERM_DEFINITION_FALLBACK_RE.search(clean)):
            errors.append("term definition is missing definition language")
    elif activity_type == "document_control_check":
        if not DOCUMENT_CONTROL_TEXT_RE.search(clean):
            errors.append("document-control statement lacks admin/reference language")
        if CITATION_LEAD_RE.match(clean) and not DOCUMENT_CONTROL_SUBSTANCE_RE.search(clean):
            errors.append("document-control statement is only a citation")
    elif activity_type == "requirement_check":
        if not REQUIREMENT_TEXT_RE.search(clean):
            errors.append("requirement statement lacks obligation/permission language")
    elif activity_type == "scope_check":
        if not SCOPE_TEXT_RE.search(clean):
            errors.append("scope statement lacks scope/responsibility language")
    elif activity_type == "capability_check":
        if not CAPABILITY_TEXT_RE.search(clean):
            errors.append("capability statement lacks system/function language")
    elif activity_type == "reference_check":
        if not re.match(r"^This paragraph cites FAA Order JO ", clean, re.IGNORECASE):
            errors.append("reference statement does not follow citation format")
    elif activity_type == "minima_rule_check":
        if not MINIMA_RULE_TEXT_RE.search(clean):
            errors.append("minima statement lacks numeric/minima language")
    elif activity_type == "example_check":
        if '"' not in clean:
            errors.append("example text is missing quoted content")
    elif activity_type == "list_membership":
        match = LIST_MEMBERSHIP_ITEM_RE.match(clean)
        item_text = match.group(1) if match else clean
        lower_item = item_text.lower()
        if "the following" in lower_item:
            errors.append("list item is a lead-in rather than a list member")
        if "as follows" in lower_item or "one of the following" in lower_item:
            errors.append("list item is a list lead-in rather than a member")
        if len(item_text.split()) > 20:
            errors.append("list item is too long to be a focused question")
        if ";" in item_text:
            errors.append("list item contains multiple list members")
        if re.search(r"\(\s*See\s+(?:FIG|TBL)\b", item_text, re.IGNORECASE):
            errors.append("list item depends on a figure/table reference")
        if re.search(r"\b\d+\.\s+[A-Za-z]", item_text):
            errors.append("list item contains numbering artifacts")
        if re.search(r"JO\s*7110\.65|\b\d{1,2}/\d{1,2}/\d{2,4}\b", item_text, re.IGNORECASE):
            errors.append("list item contains running-header noise")

    return errors


def _choice_text_errors(activity_type: str, text: str) -> list[str]:
    errors: list[str] = []
    clean = normalise_ws(text)
    if not clean:
        return ["choice text is empty"]
    for pattern in LOW_QUALITY_PATTERNS:
        if pattern.search(clean):
            errors.append(f"choice matches low-quality pattern: {pattern.pattern}")
    if activity_type not in {"reference_check", "document_control_check"}:
        if DOC_STRUCTURE_REF_RE.search(clean):
            errors.append("choice text depends on document cross-references")
        if re.search(r"\bthe paragraph\b", clean, re.IGNORECASE):
            errors.append("choice text uses paragraph-structure wording")
    return errors


def _phraseology_builder_errors(payload: dict) -> list[str]:
    errors: list[str] = []
    target_phrase = normalise_ws(payload.get("target_phrase", ""))
    word_bank = payload.get("word_bank", [])
    correct_sequence = payload.get("correct_sequence", [])

    if not target_phrase:
        errors.append("missing target_phrase")
    else:
        errors.extend(_generic_text_errors(target_phrase))
        repeated_token = _find_disallowed_adjacent_duplicate(target_phrase)
        if repeated_token:
            errors.append(f"contains repeated token: {repeated_token}")
        if "/" in target_phrase:
            errors.append("target_phrase contains unresolved alternatives")
        if target_phrase.endswith((" ON", " AT", " OF", " TO", " VIA", " AND", " OR", " WITH", " BY")):
            errors.append("target_phrase ends with an unresolved phrase fragment")

    if not isinstance(word_bank, list) or not word_bank:
        errors.append("missing word_bank")
        word_bank = []
    else:
        word_bank = [normalise_ws(str(token)) for token in word_bank]
        if any(not token for token in word_bank):
            errors.append("word_bank contains empty text")

    if not isinstance(correct_sequence, list) or not correct_sequence:
        errors.append("missing correct_sequence")
        correct_sequence = []
    else:
        if any(not isinstance(idx, int) for idx in correct_sequence):
            errors.append("correct_sequence must contain integers")
        elif word_bank and any(idx < 0 or idx >= len(word_bank) for idx in correct_sequence):
            errors.append("correct_sequence index out of range")
        elif len(set(correct_sequence)) != len(correct_sequence):
            errors.append("correct_sequence reuses a word-bank tile")

    if target_phrase and word_bank and correct_sequence:
        built_phrase = " ".join(word_bank[idx] for idx in correct_sequence)
        if normalise_ws(built_phrase) != target_phrase:
            errors.append("correct_sequence does not reconstruct target_phrase")
        if len(correct_sequence) != len(target_phrase.split()):
            errors.append("correct_sequence length does not match target_phrase")

    return errors


def _spot_the_error_errors(payload: dict) -> list[str]:
    errors: list[str] = []
    original_phrase = normalise_ws(payload.get("original_phrase", ""))
    display_text = normalise_ws(payload.get("display_text", ""))
    tokens_raw = payload.get("tokens", [])
    correct_token = normalise_ws(payload.get("correct_token", "")).upper()
    error_index = payload.get("error_index")

    if not original_phrase:
        errors.append("missing original_phrase")
    if not display_text:
        errors.append("missing display_text")
    if not isinstance(tokens_raw, list) or not tokens_raw:
        errors.append("missing tokens")
        tokens: list[str] = []
    else:
        tokens = [normalise_ws(str(token)) for token in tokens_raw]
        if any(not token for token in tokens):
            errors.append("tokens contain empty text")
        if display_text and normalise_ws(" ".join(tokens)) != display_text:
            errors.append("display_text does not match tokens")

    if not isinstance(error_index, int):
        errors.append("missing error_index")
    elif tokens and not 0 <= error_index < len(tokens):
        errors.append("error_index out of range")

    if not correct_token:
        errors.append("missing correct_token")

    if tokens and isinstance(error_index, int) and 0 <= error_index < len(tokens):
        wrong_token = tokens[error_index]
        wrong_core = split_token_parts(wrong_token)[1].upper()
        if not wrong_core:
            errors.append("incorrect token is empty")
        else:
            token_cores = [split_token_parts(token)[1].upper() for token in tokens]
            if token_cores.count(wrong_core) != 1:
                errors.append("incorrect token is not uniquely tappable")
            if correct_token and wrong_core == correct_token:
                errors.append("incorrect token matches correct_token")
            if is_contextual_spot_token(wrong_token) or (
                correct_token and is_contextual_spot_token(correct_token)
            ):
                errors.append("mutated token is context-specific rather than phraseology-fixed")

    if original_phrase and correct_token:
        original_cores = [
            split_token_parts(token)[1].upper()
            for token in original_phrase.split()
        ]
        if correct_token not in original_cores:
            errors.append("correct_token not found in original_phrase")

    return errors


def validate_activity_payload(activity_type: str, payload: dict, para_title: str = "") -> list[str]:
    errors: list[str] = []
    instruction = normalise_ws(payload.get("instruction", ""))
    explanation = normalise_ws(payload.get("explanation", ""))

    if not instruction:
        errors.append("missing instruction")
    elif activity_type == "example_check" and "paragraph's approved examples" in instruction.lower():
        errors.append("instruction depends on paragraph structure")
    elif activity_type not in {"reference_check", "document_control_check"} and re.search(
        r"\b(?:this paragraph|the paragraph|paragraph's)\b",
        instruction,
        re.IGNORECASE,
    ):
        errors.append("instruction uses paragraph-structure wording")
    if explanation:
        errors.extend(_generic_text_errors(explanation))
        if activity_type == "list_membership" and len(explanation) > 220:
            errors.append("list-membership explanation is too long")

    if activity_type == "phraseology_builder":
        errors.extend(_phraseology_builder_errors(payload))
    elif activity_type == "spot_the_error":
        errors.extend(_spot_the_error_errors(payload))
    elif activity_type in CHOICE_ACTIVITY_TYPES:
        question_text = ""
        if activity_type == "situation_action":
            question_text = normalise_ws(payload.get("situation", ""))
            if not question_text:
                errors.append("missing situation")
            else:
                errors.extend(_generic_text_errors(question_text))
                if DOC_STRUCTURE_REF_RE.search(question_text):
                    errors.append("situation text depends on document cross-references")
                if re.search(r"\bthis paragraph\b", question_text, re.IGNORECASE):
                    errors.append("situation text uses paragraph-structure wording")
                if SITUATION_SCAFFOLD_RE.search(question_text):
                    errors.append("situation text uses document-scaffold wording")
                if SITUATION_PROMPT_TAIL_RE.search(question_text):
                    errors.append("situation text includes a redundant question tail")
            if not normalise_ws(payload.get("para_context", "")):
                errors.append("missing para_context")
        elif activity_type == "readback_check":
            question_text = normalise_ws(payload.get("clearance", ""))
            if not question_text:
                errors.append("missing clearance")
        else:
            question_text = normalise_ws(payload.get("question_text", ""))
            if not question_text:
                errors.append("missing question_text")
            else:
                errors.extend(_question_text_errors(activity_type, question_text, para_title))
                if activity_type == "example_check":
                    match = re.search(r'"([^"]+)"', question_text)
                    if (
                        instruction == GENERIC_EXAMPLE_INSTRUCTION
                        or instruction in LEGACY_GENERIC_EXAMPLE_INSTRUCTIONS
                    ) and match:
                        token_count = len(re.findall(r"[A-Za-z0-9]+", match.group(1)))
                        if token_count <= 3:
                            errors.append("example check lacks enough topic context for a short example")
        choices = payload.get("choices", [])
        if not choices:
            errors.append("missing choices")
        elif sum(1 for choice in choices if choice.get("is_correct")) != 1:
            errors.append("choice activity must have exactly one correct answer")
        for choice in choices:
            errors.extend(_choice_text_errors(activity_type, choice.get("text", "")))
        if activity_type == "situation_action":
            generic_count = sum(
                1
                for choice in choices
                if not choice.get("is_correct") and is_generic_action_distractor(choice.get("text", ""))
            )
            if generic_count > 1:
                errors.append("situation action uses too many generic distractors")

    return errors


def _candidate_variants(text: str, seed_key: str, preferred: Optional[list[str]] = None) -> list[str]:
    seen: set[str] = {normalise_ws(text).lower()}
    ordered: list[str] = []

    for candidate in preferred or []:
        clean = _sentence_with_period(candidate)
        key = normalise_ws(clean).lower()
        if clean and key not in seen:
            seen.add(key)
            ordered.append(clean)

    for variant in build_statement_variants(text, seed_key, max_variants=6):
        clean = _sentence_with_period(variant)
        key = normalise_ws(clean).lower()
        if clean and key not in seen:
            seen.add(key)
            ordered.append(clean)

    return ordered


def _pick_false_statement(
    text: str,
    seed_key: str,
    *,
    activity_type: str,
    para_title: str = "",
    preferred: Optional[list[str]] = None,
) -> Optional[str]:
    for candidate in _candidate_variants(text, seed_key, preferred):
        if _question_text_errors(activity_type, candidate, para_title):
            continue
        return candidate
    return None


def _increment_last_number(text: str) -> Optional[str]:
    matches = list(re.finditer(r"\d+", text))
    if not matches:
        return None
    match = matches[-1]
    replacement = str(int(match.group(0)) + 1)
    return f"{text[:match.start()]}{replacement}{text[match.end():]}"


def _directive_candidates(content: str) -> list[str]:
    candidates: list[str] = []
    for sentence in meaningful_sentences_from_text(content):
        clean = sentence if sentence.endswith(".") else f"{sentence}."
        clean = DIRECTIVE_LABEL_PREFIX_RE.sub("", clean).strip()
        if INTRO_CLAUSE_IMPERATIVE_RE.search(clean):
            clean = clean.split(",", 1)[1].strip()
            clean = clean[:1].upper() + clean[1:]
            clean = _sentence_with_period(clean)

        lower = clean.lower()
        if not IMPERATIVE_START_RE.match(clean):
            if not lower.startswith("do not "):
                continue
        if len(clean.split()) < 3 or len(clean.split()) > 34:
            continue
        if any(marker in lower for marker in ("the following", "except:", "except", "table", "tbl")):
            continue
        if _directive_text_errors(clean):
            continue
        candidates.append(clean)

    return sorted(candidates, key=lambda item: (len(item.split()), len(item)))


def _toggle_directive(sentence: str) -> Optional[str]:
    clean = normalise_ws(sentence).rstrip(".")
    if not clean:
        return None
    if clean.lower().startswith("do not "):
        positive = clean[7:].strip()
        if not positive:
            return None
        return f"{positive[:1].upper()}{positive[1:]}."
    if " " not in clean:
        return None
    verb, remainder = clean.split(" ", 1)
    return f"Do not {verb.lower()} {remainder}."


def _pick_false_directive(directive: str, seed_key: str) -> Optional[str]:
    preferred: list[str] = []
    if directive.lower().startswith("do not "):
        toggled = _toggle_directive(directive)
        if toggled:
            preferred.append(toggled)

    replacements = (
        (" approved ", " unapproved "),
        (" maximum ", " minimum "),
        (" minimum ", " maximum "),
        (" consistent with ", " contrary to "),
        (" only when ", " even when "),
        (" only if ", " even if "),
        (" unless ", " even if "),
        (" more information ", " less information "),
        (" to the extent possible ", " only if convenient "),
    )
    padded = f" {directive.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(re.sub(re.escape(source.strip()), target.strip(), directive, count=1, flags=re.IGNORECASE))

    for candidate in _candidate_variants(directive, seed_key, preferred):
        if _question_text_errors("directive_check", candidate, ""):
            continue
        return candidate

    if not directive.lower().startswith("do not "):
        toggled = _toggle_directive(directive)
        if toggled and not _question_text_errors("directive_check", toggled, ""):
            return toggled
    return None


def _gen_directive_check(para_id: str, para_title: str, content: str) -> list[dict]:
    if "ABBREVIATION" in para_title.upper():
        return []

    candidates = _directive_candidates(content)
    if not candidates:
        return []

    directive = candidates[0]
    false_directive = _pick_false_directive(directive, f"{para_id}:directive_check")
    rng = rng_for(para_id, "directive_check", directive)
    show_true = bool(rng.randint(0, 1)) or not false_directive
    question_text = directive if show_true else false_directive

    return [{
        "instruction": "Is this directive stated correctly?",
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {directive}",
        "difficulty": 1,
    }]


def _gen_scope_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_scope_sentence(para_title, content)
    if not sentence:
        return []

    preferred = []
    replacements = (
        (" are set forth as ", " are not set forth as "),
        (" is set forth as ", " is not set forth as "),
        (" applies to ", " does not apply to "),
        (" apply to ", " do not apply to "),
        (" are to be used ", " are not to be used "),
        (" is to be used ", " is not to be used "),
        (" may be used ", " may not be used "),
        (" must ", " need not "),
        (" need not ", " must "),
        (" does not relieve ", " relieves "),
        (" are required to ", " are not required to "),
        (" is required to ", " is not required to "),
        (" are responsible for ", " are not responsible for "),
        (" is responsible for ", " is not responsible for "),
        (" must adhere ", " need not adhere "),
        (" is available ", " is not available "),
        (" is distributed ", " is not distributed "),
        (" are distributed ", " are not distributed "),
    )
    padded = f" {sentence.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(re.sub(re.escape(source.strip()), target.strip(), sentence, count=1, flags=re.IGNORECASE))

    false_statement = _pick_false_statement(
        sentence,
        f"{para_id}:scope_check",
        activity_type="scope_check",
        para_title=para_title,
        preferred=preferred,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "scope_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)
    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1 if len(sentence.split()) <= 18 else 2,
    }]


def _gen_requirement_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_requirement_sentence(content)
    if not sentence:
        return []

    preferred = []
    if IMPERATIVE_START_RE.match(sentence) or sentence.lower().startswith("do not "):
        toggled = _toggle_directive(sentence)
        if toggled and normalise_ws(toggled).lower() != normalise_ws(sentence).lower():
            preferred.append(toggled)

    replacements = (
        (" must not be less than ", " may be less than "),
        (" must not be more than ", " may be more than "),
        (" must not be greater than ", " may be greater than "),
        (" use ", " do not use "),
        (" monitor ", " do not monitor "),
        (" terminate ", " do not terminate "),
        (" transmit ", " do not transmit "),
        (" record ", " do not record "),
        (" relay ", " do not relay "),
        (" specify ", " do not specify "),
        (" continue ", " do not continue "),
        (" annotate ", " do not annotate "),
        (" identify ", " do not identify "),
        (" forward ", " do not forward "),
        (" advise ", " do not advise "),
        (" inform ", " do not inform "),
        (" interrupt ", " do not interrupt "),
        (" retain ", " do not retain "),
        (" clear ", " do not clear "),
        (" assign ", " do not assign "),
        (" provide ", " do not provide "),
        (" separate ", " do not separate "),
        (" authorize ", " do not authorize "),
        (" approve ", " do not approve "),
        (" turn ", " do not turn "),
        (" instruct ", " do not instruct "),
        (" direct ", " do not direct "),
        (" insert ", " do not insert "),
        (" coordinate ", " do not coordinate "),
        (" must be provided ", " need not be provided "),
        (" must be handled ", " need not be handled "),
        (" must be covered ", " need not be covered "),
        (" must ", " need not "),
        (" shall ", " need not "),
        (" should ", " need not "),
        (" need not ", " must "),
        (" may not ", " may "),
        (" only if ", " even if "),
        (" only when ", " regardless of whether "),
        (" unless ", " even if "),
        (" are required to ", " are not required to "),
        (" is required to ", " is not required to "),
    )
    padded = f" {sentence.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(re.sub(re.escape(source.strip()), target.strip(), sentence, count=1, flags=re.IGNORECASE))

    false_statement = None
    for candidate in preferred:
        candidate = _sentence_with_period(candidate)
        if not _question_text_errors("requirement_check", candidate, para_title):
            false_statement = candidate
            break
    if not false_statement:
        return []

    rng = rng_for(para_id, "requirement_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)
    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1 if len(sentence.split()) <= 18 else 2,
    }]


def _gen_capability_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_capability_sentence(para_title, content)
    if not sentence:
        return []

    preferred = []
    replacements = (
        (" is an integrated function of ", " is separate from "),
        (" uses ", " does not use "),
        (" provides ", " does not provide "),
        (" predicts ", " does not predict "),
        (" derives ", " does not derive "),
        (" records ", " does not record "),
        (" is based on ", " is not based on "),
        (" are based on ", " are not based on "),
        (" will remove ", " will not remove "),
        (" may be affected ", " will not be affected "),
        (" establishes procedures for ", " does not establish procedures for "),
        (" supports ", " does not support "),
    )
    padded = f" {sentence.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(re.sub(re.escape(source.strip()), target.strip(), sentence, count=1, flags=re.IGNORECASE))

    false_statement = _pick_false_statement(
        sentence,
        f"{para_id}:capability_check",
        activity_type="capability_check",
        para_title=para_title,
        preferred=preferred,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "capability_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)
    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1 if len(sentence.split()) <= 18 else 2,
    }]


def _gen_conditional_rule_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_conditional_rule_sentence(content)
    if not sentence:
        return []

    false_statement = _pick_false_statement(
        sentence,
        f"{para_id}:conditional_rule",
        activity_type="conditional_rule_check",
        para_title=para_title,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "conditional_rule_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)

    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1 if len(sentence.split()) <= 18 else 2,
    }]


def _gen_term_definition_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_title_definition_sentence(para_title, content)
    if not sentence:
        return []

    preferred = []
    replacements = (
        (" are set forth as ", " are not set forth as "),
        (" is set forth as ", " is not set forth as "),
        (" refers to ", " does not refer to "),
        (" means ", " does not mean "),
        (" is based on ", " is not based on "),
        (" are based on ", " are not based on "),
        (" is not based on ", " is based on "),
        (" are not set forth as ", " are set forth as "),
    )
    padded = f" {sentence.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(re.sub(re.escape(source.strip()), target.strip(), sentence, count=1, flags=re.IGNORECASE))
    false_statement = _pick_false_statement(
        sentence,
        f"{para_id}:term_definition",
        activity_type="term_definition_check",
        para_title=para_title,
        preferred=preferred,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "term_definition_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)

    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1,
    }]


def _gen_document_control_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_document_control_sentence(para_title, content)
    if not sentence:
        return []

    preferred = []
    replacements = (
        ("prescribes", "does not prescribe"),
        ("applies to", "does not apply to"),
        ("is available", "is not available"),
        ("are canceled", "are retained"),
        ("are identified", "are omitted"),
        ("must submit", "need not submit"),
        ("is distributed", "is not distributed"),
        ("are responsible", "are not responsible"),
        ("may contact", "may not contact"),
        ("is found in", "is not found in"),
    )
    for source, target in replacements:
        candidate = re.sub(rf"\b{re.escape(source)}\b", target, sentence, count=1, flags=re.IGNORECASE)
        if normalise_ws(candidate).lower() != normalise_ws(sentence).lower():
            preferred.append(candidate)
    false_statement = _pick_false_statement(
        sentence,
        f"{para_id}:document_control",
        activity_type="document_control_check",
        para_title=para_title,
        preferred=preferred,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "document_control_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)

    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1 if len(sentence.split()) <= 16 else 2,
    }]


def _reference_statement(entry: dict) -> str:
    parts = [f"This paragraph cites {entry['order']}"]
    if entry.get("locator"):
        parts.append(entry["locator"])
    if entry.get("title"):
        parts.append(entry["title"])
    return _sentence_with_period(", ".join(parts))


def _mutate_reference_statement(entry: dict) -> Optional[str]:
    if entry.get("locator"):
        mutated_locator = _increment_last_number(entry["locator"])
        if mutated_locator and mutated_locator != entry["locator"]:
            return _reference_statement({**entry, "locator": mutated_locator})

    mutated_order = _increment_last_number(entry["order"])
    if mutated_order and mutated_order != entry["order"]:
        return _reference_statement({**entry, "order": mutated_order})

    if entry.get("title"):
        variants = build_statement_variants(entry["title"], f"ref:{entry['title']}", max_variants=4)
        for variant in variants:
            if normalise_ws(variant).lower() != normalise_ws(entry["title"]).lower():
                return _reference_statement({**entry, "title": variant.rstrip(".")})

    return None


def _gen_reference_check(para_id: str, para_title: str, content: str) -> list[dict]:
    references = extract_reference_entries(content)
    if not references:
        return []

    entry = references[0]
    correct_statement = _reference_statement(entry)
    false_statement = _mutate_reference_statement(entry)
    if not false_statement:
        return []

    rng = rng_for(para_id, "reference_check", correct_statement)
    show_true = bool(rng.randint(0, 1))

    explanation = f"Per {para_id}, the cited reference is {entry['order']}"
    if entry.get("locator"):
        explanation += f", {entry['locator']}"
    if entry.get("title"):
        explanation += f", {entry['title']}"
    explanation = _sentence_with_period(explanation)

    return [{
        "instruction": "Does this citation match the section's reference?",
        "question_text": correct_statement if show_true else false_statement,
        "choices": _boolean_choices(show_true),
        "explanation": explanation,
        "difficulty": 1,
    }]


def _gen_minima_rule_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentence = select_minima_rule_sentence(content)
    if not sentence:
        return []

    preferred = []
    replacements = (
        (" above ", " below "),
        (" below ", " above "),
        (" laterally ", " vertically "),
        (" vertically ", " laterally "),
        (" at least ", " at most "),
        (" 1 mile ", " 2 miles "),
        (" 2 miles ", " 1 mile "),
        (" 3 minutes ", " 5 minutes "),
        (" 5 miles ", " 3 miles "),
        (" 2,000 feet ", " 1,000 feet "),
        (" 6,000 feet ", " 3,000 feet "),
        (" 29.92 ", " 30.12 "),
    )
    padded = f" {sentence.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(re.sub(re.escape(source.strip()), target.strip(), sentence, count=1, flags=re.IGNORECASE))

    false_statement = _pick_false_statement(
        sentence,
        f"{para_id}:minima_rule_check",
        activity_type="minima_rule_check",
        para_title=para_title,
        preferred=preferred,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "minima_rule_check", sentence)
    show_true = bool(rng.randint(0, 1))
    question_text = _contextualize_statement(para_title, sentence if show_true else false_statement)
    return [{
        "instruction": _statement_instruction(para_title),
        "question_text": question_text,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {sentence}",
        "difficulty": 1 if len(sentence.split()) <= 18 else 2,
    }]


def _list_item_score(item: str) -> int:
    words = len(item.split())
    score = 0
    if 1 <= words <= 5:
        score += 4
    elif words <= 9:
        score += 2
    if "," not in item:
        score += 1
    if "/" in item:
        score += 1
    return score


def _list_item_key(text: str) -> str:
    return normalise_ws(text).rstrip(".").lower()


def _pick_false_list_item(item_text: str, listed_items: list[str], seed_key: str) -> Optional[str]:
    preferred: list[str] = []
    listed_keys = {_list_item_key(item) for item in listed_items}

    if IMPERATIVE_START_RE.match(item_text) or item_text.lower().startswith("do not "):
        toggled = _toggle_directive(item_text)
        if toggled:
            preferred.append(toggled)

    replacements = (
        (" must not be ", " may be "),
        (" must be ", " need not be "),
        (" must ", " need not "),
        (" should ", " should not "),
        (" may not ", " may "),
        (" may ", " may not "),
        (" do not ", ""),
        (" are ", " are not "),
        (" is ", " is not "),
        (" before ", " after "),
        (" after ", " before "),
        (" above ", " below "),
        (" below ", " above "),
        (" at least ", " at most "),
        (" within ", " beyond "),
    )
    padded = f" {item_text.rstrip('.')} "
    for source, target in replacements:
        if source in padded.lower():
            preferred.append(
                re.sub(
                    rf"\b{re.escape(source.strip())}\b",
                    target.strip(),
                    item_text,
                    count=1,
                    flags=re.IGNORECASE,
                )
            )

    number_variant = _increment_last_number(item_text)
    if number_variant:
        preferred.append(number_variant)

    seen: set[str] = set()
    for candidate in preferred:
        candidate = _sentence_with_period(candidate)
        key = _list_item_key(candidate)
        if not candidate or key in seen or key in listed_keys:
            continue
        seen.add(key)
        if _question_text_errors("list_membership", candidate, ""):
            continue
        return candidate

    return None


def _example_snippet_score(example: str) -> int:
    match = re.search(r'"([^"]+)"', example)
    inner = normalise_ws(match.group(1) if match else example).strip()
    words = re.findall(r"[A-Za-z0-9]+", inner)
    word_count = len(words)
    score = 0

    if 6 <= word_count <= 14:
        score += 6
    elif word_count == 5:
        score += 2
    elif word_count == 4:
        score += 1
    elif 15 <= word_count <= 24:
        score += 3
    elif word_count <= 3:
        score -= 5
    elif word_count > 28:
        score -= 4

    if "," in inner:
        score += 2
    if re.search(r"\d", inner):
        score += 1
    if EXAMPLE_CHECK_OPERATIONAL_RE.search(inner):
        score += 2
    operational_hits = len(EXAMPLE_CHECK_OPERATIONAL_RE.findall(inner))
    if operational_hits >= 4:
        score += 2
    elif operational_hits >= 2:
        score += 1
    if EXAMPLE_CHECK_DETAIL_RE.search(inner):
        score += 2
    sentence_count = len(re.findall(r"[.!?]", inner))
    if sentence_count == 1 and word_count == 5:
        score += 1
    if sentence_count >= 2:
        score += 1 if EXAMPLE_CHECK_OPERATIONAL_RE.search(inner) else -4
    if re.search(r'^[^"]+:\s*"', example):
        score -= 2
    if inner.endswith(","):
        score -= 3
    if re.search(
        r"\b(?:Contact|Monitor)\b[^.]*\b(?:Point|Decimal)\s+(?:Zero|One|Two|Three|Four|Five|Six|Seven|Eight|Niner)\b",
        inner,
        re.IGNORECASE,
    ) and not re.search(
        r"\b(?:Zero|One|Two|Three|Four|Five|Six|Seven|Eight|Niner)\s+"
        r"(?:Zero|One|Two|Three|Four|Five|Six|Seven|Eight|Niner)\s+"
        r"(?:Zero|One|Two|Three|Four|Five|Six|Seven|Eight|Niner)\s+"
        r"(?:Point|Decimal)\b",
        inner,
        re.IGNORECASE,
    ):
        score -= 3
    if "..." in inner or "…" in inner:
        score -= 6
    if EXAMPLE_CHECK_TRUNCATED_DOTS_RE.search(inner):
        score -= 6
    if EXAMPLE_CHECK_THIN_ACK_RE.search(inner):
        score -= 6
    if EXAMPLE_CHECK_SUPPORT_RE.search(inner):
        score -= 3
    if re.search(r'"[A-Z]\.[A-Z]\."', example):
        score -= 4
    return score


def _example_check_inner_text(example: str) -> str:
    match = re.search(r'"([^"]+)"', example)
    return normalise_ws(match.group(1) if match else example).strip()


def _example_sort_details(example: str) -> tuple[int, int]:
    inner = _example_check_inner_text(example)
    return (inner.count(","), len(inner.split()))


def _example_para_preference_score(para_id: str, example: str) -> int:
    pattern = EXAMPLE_CHECK_PREFERRED_PATTERNS_BY_PARA.get(para_id)
    inner = _example_check_inner_text(example)
    if pattern and pattern.search(example):
        score = 4
    else:
        score = 0

    if para_id == "2-1-21" and re.search(r"\bo['’]clock\b|\bmiles?\b|\baltitude unknown\b|\bbelow you\b", inner, re.IGNORECASE):
        score += 3
    if para_id == "2-5-2" and re.search(r"\bwithin\b.+\bmile radius\b|\bbearing from\b|\bmile arc\b", inner, re.IGNORECASE):
        score += 3
    if para_id == "3-3-4":
        if inner.lower().startswith("braking action"):
            score += 4
        if "reported by" in inner.lower():
            score += 1
        if re.search(r"\bfirst half of runway\b|\bbeyond the intersection\b", inner, re.IGNORECASE):
            score += 1
    if para_id == "4-6-1" and re.search(r"\bhold\b|\bexpect further clearance\b|\bdelay indefinite\b", inner, re.IGNORECASE):
        score += 4

    if inner.count(",") >= 3:
        score += 1

    if score:
        return score
    return 0


def _example_token_is_slot_like(token: str) -> bool:
    _, core, _ = split_token_parts(token)
    upper = core.upper()
    if not upper:
        return False
    if upper in EXAMPLE_FALSE_STRUCTURAL_WORDS:
        return False
    if upper in EXAMPLE_FALSE_NUMBER_WORDS:
        return True
    if upper in EXAMPLE_FALSE_PHONETIC_WORDS:
        return True
    if upper in EXAMPLE_FALSE_DIRECTION_WORDS:
        return True
    if re.search(r"\d", upper):
        return True
    if upper.isalpha() and len(upper) == 1:
        return True
    return False


def _example_diff_is_slot_like(raw_tokens: list[str], idx: int, left: str, right: str) -> bool:
    left_upper = split_token_parts(left)[1].upper()
    right_upper = split_token_parts(right)[1].upper()
    prev_upper = split_token_parts(raw_tokens[idx - 1])[1].upper() if idx > 0 else ""
    next_upper = split_token_parts(raw_tokens[idx + 1])[1].upper() if idx + 1 < len(raw_tokens) else ""
    current_raw = raw_tokens[idx] if idx < len(raw_tokens) else ""

    if (
        (left_upper in EXAMPLE_FALSE_FACILITY_WORDS or right_upper in EXAMPLE_FALSE_FACILITY_WORDS)
        and ("," in current_raw or next_upper == "ON")
    ):
        return True

    comma_index = next((i for i, token in enumerate(raw_tokens) if "," in token), None)
    if comma_index is not None and idx <= comma_index:
        if left_upper not in EXAMPLE_FALSE_STRUCTURAL_WORDS and right_upper not in EXAMPLE_FALSE_STRUCTURAL_WORDS:
            return True

    if left_upper in EXAMPLE_FALSE_STRUCTURAL_WORDS or right_upper in EXAMPLE_FALSE_STRUCTURAL_WORDS:
        return False

    if _example_token_is_slot_like(left) or _example_token_is_slot_like(right):
        return True
    if prev_upper in EXAMPLE_FALSE_SLOT_CONTEXT_WORDS or next_upper in EXAMPLE_FALSE_SLOT_CONTEXT_WORDS:
        return True
    return False


def _example_false_candidate_is_slot_only(example: str, candidate: str) -> bool:
    example_inner = _example_check_inner_text(example)
    candidate_inner = _example_check_inner_text(candidate)
    if not example_inner or not candidate_inner:
        return False

    example_tokens = example_inner.split()
    candidate_tokens = candidate_inner.split()
    if len(example_tokens) != len(candidate_tokens):
        return False

    diff_positions = [
        idx
        for idx, (left, right) in enumerate(zip(example_tokens, candidate_tokens))
        if split_token_parts(left)[1].upper() != split_token_parts(right)[1].upper()
    ]
    if not diff_positions:
        return False
    return all(
        _example_diff_is_slot_like(example_tokens, idx, example_tokens[idx], candidate_tokens[idx])
        for idx in diff_positions
    )


def _is_viable_example_check_snippet(example: str) -> bool:
    inner = _example_check_inner_text(example)
    if not inner:
        return False

    if "..." in inner or "…" in inner:
        return False
    if EXAMPLE_CHECK_TRUNCATED_DOTS_RE.search(inner):
        return False
    if EXAMPLE_CHECK_ALTERNATIVE_RE.search(inner):
        return False
    if EXAMPLE_CHECK_PLACEHOLDER_RE.search(inner):
        return False
    if EXAMPLE_CHECK_THIN_ACK_RE.search(inner):
        return False
    if EXAMPLE_CHECK_ACRONYM_ID_RE.fullmatch(inner):
        return False
    if EXAMPLE_CHECK_IDENTITY_RE.fullmatch(inner):
        return False
    if EXAMPLE_CHECK_CODE_RE.fullmatch(inner):
        return False
    if EXAMPLE_CHECK_GROUP_FORM_RE.fullmatch(inner):
        return False

    token_count = len(re.findall(r"[A-Za-z0-9-]+", inner))
    if token_count <= 3:
        return False
    if token_count <= 4 and not EXAMPLE_CHECK_OPERATIONAL_RE.search(inner):
        return False

    return True


def _looks_tabular_sentence(sentence: str) -> bool:
    if sentence.count("Pronunciation") >= 2:
        return True

    word_count = len(sentence.split())
    digit_count = len(re.findall(r"\b\d+\b", sentence))
    titleish_count = len(re.findall(r"\b[A-Z][a-z]+(?:-[A-Za-z]+)?\b", sentence))
    uppercase_count = len(re.findall(r"\b[A-Z]{2,}(?:-[A-Z]+)?\b", sentence))

    if word_count >= 18 and digit_count >= 2 and titleish_count >= 8:
        return True
    if word_count >= 16 and digit_count >= 1 and uppercase_count >= 6:
        return True
    return False


def _mutate_example_snippet(
    example: str,
    seed_key: str,
    *,
    disallowed_keys: Optional[set[str]] = None,
) -> Optional[str]:
    blocked = {normalise_ws(item).lower() for item in (disallowed_keys or set())}
    accepted: list[str] = []
    labelled = re.match(r'^(?P<label>[^:"]+:\s*)?(?P<quote>"(?P<inner>[^"]+)")(?P<tail>.*)$', example)
    if labelled:
        label = labelled.group("label") or ""
        inner = labelled.group("inner")
        tail = labelled.group("tail") or ""
        mutated = mutate_phrase_line(inner, seed_key, allow_generic=False)
        candidates: list[str] = []
        if mutated:
            candidates.append(f'{label}"{mutated["display_text"]}"{tail}')
        for variant in build_statement_variants(inner, seed_key, max_variants=6):
            candidates.append(f'{label}"{variant}"{tail}')
        for candidate in candidates:
            if normalise_ws(candidate).lower() in blocked:
                continue
            if _example_false_candidate_is_slot_only(example, candidate):
                continue
            if not _question_text_errors("example_check", candidate, ""):
                accepted.append(candidate)
    else:
        for variant in _candidate_variants(
            example,
            seed_key,
            preferred=[],
        ):
            if normalise_ws(variant).lower() in blocked:
                continue
            if _example_false_candidate_is_slot_only(example, variant):
                continue
            if not _question_text_errors("example_check", variant, ""):
                accepted.append(variant)

    if not accepted:
        return None

    return sorted(
        accepted,
        key=lambda candidate: (
            -_example_false_candidate_score(example, candidate),
            candidate.lower(),
        ),
    )[0]


def _example_false_candidate_score(example: str, candidate: str) -> int:
    example_inner = _example_check_inner_text(example)
    candidate_inner = _example_check_inner_text(candidate)
    if not example_inner or not candidate_inner:
        return -10
    if _example_false_candidate_is_slot_only(example, candidate):
        return -20

    score = 0
    if len(example_inner.split()) == len(candidate_inner.split()):
        score += 2

    example_tokens = [split_token_parts(token)[1].upper() for token in example_inner.split()]
    candidate_tokens = [split_token_parts(token)[1].upper() for token in candidate_inner.split()]
    diffs = [
        (left, right)
        for left, right in zip(example_tokens, candidate_tokens)
        if left and right and left != right
    ]
    if len(diffs) == 1:
        score += 3
        left, right = diffs[0]
        if left.isdigit() or right.isdigit():
            score += 2
        elif is_contextual_spot_token(left) or is_contextual_spot_token(right):
            score += 2
    elif len(diffs) == 2:
        score += 1

    for pattern in EXAMPLE_FALSE_BAD_PATTERNS:
        if pattern.search(candidate_inner):
            score -= 10
    if candidate_inner.startswith("Taxiway ") and example_inner.startswith("Runway "):
        score -= 6
    if candidate_inner.count("Taxiway") > example_inner.count("Taxiway") and "Runway" in example_inner:
        score -= 8
    if len(re.findall(r"[.!?]", example_inner)) >= 2 and not EXAMPLE_CHECK_OPERATIONAL_RE.search(example_inner):
        score -= 4
    if "..." in candidate_inner or "…" in candidate_inner:
        score -= 2

    return score


def _gen_example_check(para_id: str, para_title: str, content: str) -> list[dict]:
    examples = [
        example
        for example in extract_example_snippets(content, max_examples=24)
        if _is_viable_example_check_snippet(example)
    ]
    if not examples:
        return []

    ranked_examples = sorted(
        examples,
        key=lambda item: (
            -(_example_snippet_score(item) + _example_para_preference_score(para_id, item)),
            -_example_sort_details(item)[0],
            -_example_sort_details(item)[1],
            item.lower(),
        ),
    )
    best_example = ranked_examples[0]
    best_example_score = _example_snippet_score(best_example) + _example_para_preference_score(para_id, best_example)

    def build_true_example_activity(example_text: str) -> list[dict]:
        return [{
            "instruction": _example_check_instruction(para_id, para_title),
            "question_text": example_text,
            "choices": _boolean_choices(True),
            "explanation": f"Per {para_id}, {_example_check_explanation_prefix(para_id, para_title)}: {example_text}",
            "difficulty": 1 if len(example_text.split()) <= 10 else 2,
        }]

    if para_id in EXAMPLE_CHECK_TRUE_ONLY_PARA_IDS:
        return build_true_example_activity(best_example)

    example_keys = {normalise_ws(item).lower() for item in examples}
    ranked_candidates: list[tuple[int, int, str, str]] = []
    for example in examples:
        false_example = _mutate_example_snippet(
            example,
            f"{para_id}:example_check",
            disallowed_keys=example_keys,
        )
        if not false_example or normalise_ws(false_example).lower() == normalise_ws(example).lower():
            continue
        ranked_candidates.append(
            (
                _example_false_candidate_score(example, false_example),
                _example_snippet_score(example) + _example_para_preference_score(para_id, example),
                example,
                false_example,
            )
        )
    if not ranked_candidates:
        return build_true_example_activity(best_example)

    false_quality, _, example, false_example = sorted(
        ranked_candidates,
        key=lambda item: (
            -(item[0] + item[1]),
            -item[0],
            -item[1],
            -_example_sort_details(item[2])[0],
            -_example_sort_details(item[2])[1],
            item[2].lower(),
        ),
    )[0]

    if para_id not in EXAMPLE_CHECK_PREFER_FALSE_PARA_IDS and (false_quality + _example_snippet_score(example) + _example_para_preference_score(para_id, example)) < best_example_score + 2:
        return build_true_example_activity(best_example)

    if para_id in EXAMPLE_CHECK_PREFER_FALSE_PARA_IDS:
        show_true = False
    else:
        if false_quality < 0:
            show_true = True
        else:
            rng = rng_for(para_id, "example_check", example)
            show_true = bool(rng.randint(0, 1))

    return [{
        "instruction": _example_check_instruction(para_id, para_title),
        "question_text": example if show_true else false_example,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}, {_example_check_explanation_prefix(para_id, para_title)}: {example}",
        "difficulty": 1 if len(example.split()) <= 10 else 2,
    }]


def _gen_list_membership(para_id: str, para_title: str, content: str) -> list[dict]:
    items = extract_list_items(content)
    if len(items) < 2:
        return []

    def valid_item(item: str) -> bool:
        clean = _sentence_with_period(item)
        lower = clean.lower()
        if len(clean.split()) < 2 or len(clean.split()) > 18:
            return False
        if "the following" in lower or "as follows" in lower or "one of the following" in lower:
            return False
        if ";" in clean:
            return False
        if re.search(r"\(\s*See\s+(?:FIG|TBL)\b", clean, re.IGNORECASE):
            return False
        if re.search(r"\b\d+\.\s+[A-Za-z]", clean):
            return False
        if re.search(r"JO\s*7110\.65|\b\d{1,2}/\d{1,2}/\d{2,4}\b", clean, re.IGNORECASE):
            return False
        return True

    filtered = [_sentence_with_period(item) for item in items if valid_item(item)]
    if len(filtered) < 2:
        return []

    ordered = sorted(filtered, key=lambda item: (-_list_item_score(item), item.lower()))
    item = ordered[0]
    false_item = None
    for candidate in ordered:
        false_candidate = _pick_false_list_item(
            candidate,
            filtered,
            f"{para_id}:list_membership:{candidate}",
        )
        if false_candidate:
            item = candidate
            false_item = false_candidate
            break

    rng = rng_for(para_id, "list_membership", item)
    show_true = not false_item or bool(rng.randint(0, 1))
    prompt_item = item if show_true else false_item
    explanation = f"Per {para_id}: {item.rstrip('.')} is explicitly included."

    return [{
        "instruction": "Is this item explicitly included?",
        "question_text": prompt_item,
        "choices": _boolean_choices(show_true),
        "explanation": explanation,
        "difficulty": 1 if len(item.split()) <= 5 else 2,
    }]


def _table_row_statement(row: dict) -> str:
    return (
        f"Step {row['step']} corresponds to day {_fragment_text(row['day'])} "
        f"and night {_fragment_text(row['night'])}."
    )


def _gen_table_lookup(para_id: str, para_title: str, content: str) -> list[dict]:
    rows = extract_step_visibility_table_rows(content)
    if len(rows) < 2:
        return []

    chosen = rows[0]
    correct_statement = _table_row_statement(chosen)
    variants = build_statement_variants(correct_statement, f"{para_id}:table_lookup", max_variants=6)
    false_statement = next(
        (
            variant if variant.endswith(".") else f"{variant}."
            for variant in variants
            if variant != correct_statement
        ),
        None,
    )
    if not false_statement:
        return []

    rng = rng_for(para_id, "table_lookup", correct_statement)
    show_true = bool(rng.randint(0, 1))

    return [{
        "instruction": "Does this table statement match the paragraph?",
        "question_text": correct_statement if show_true else false_statement,
        "choices": _boolean_choices(show_true),
        "explanation": f"Per {para_id}: {correct_statement}",
        "difficulty": 2,
    }]


def _knowledge_sentences(content: str) -> list[str]:
    sentences = meaningful_sentences_from_text(content)
    if sentences:
        return sentences

    fallback: list[str] = []
    seen: set[str] = set()
    stripped = strip_paragraph_heading(content)

    def push(sentence: str) -> None:
        sentence = clean_sentence_candidate(sentence)
        sentence = normalise_ws(sentence)
        if len(sentence.split()) < 3 or len(sentence.split()) > 28:
            return
        if sentence.endswith(":"):
            return
        if re.search(r"https?://|faa\.gov", sentence, re.IGNORECASE):
            return
        first_alpha = next((ch for ch in sentence if ch.isalpha()), "")
        if not first_alpha or not first_alpha.isupper():
            return
        if sentence not in seen:
            seen.add(sentence)
            fallback.append(sentence)

    for raw in re.split(r"(?<=[.!?])\s+|\n+", stripped):
        push(raw)

    normalised_text = normalise_ws(stripped.replace("\n", " "))
    for raw in re.split(r"(?<=[.!?])\s+", normalised_text):
        push(raw)

    return fallback


def _knowledge_sentence_score(sentence: str, specific: list[str]) -> int:
    score = len(specific) * 4
    lower = sentence.lower()

    if AUXILIARY_VERB_RE.search(sentence) or IMPERATIVE_START_RE.match(sentence):
        score += 3
    else:
        score -= 6
    if sentence.startswith("(") or re.match(r"^\d", sentence):
        score -= 8
    if len(re.findall(r"\b\d+\b", sentence)) > 3:
        score -= 4
    if len(re.findall(r"\b\d+\b", sentence)) >= 2 and not AUXILIARY_VERB_RE.search(sentence):
        score -= 6
    if len(sentence.split()) > 20:
        score -= 2
    if len(sentence.split()) > 30:
        score -= 8
    if sentence.count(",") > 3:
        score -= 1
    if _looks_tabular_sentence(sentence):
        score -= 20
    if sentence.startswith(("When ", "If ", "This ", "Controllers ", "Operate ", "Relay ", "Terminate ")):
        score += 2
    if any(term in lower for term in ("table", "tbl", "figure")):
        score -= 5

    return score


def _gen_knowledge_check(para_id: str, para_title: str, content: str) -> list[dict]:
    sentences = _knowledge_sentences(content)
    if not sentences:
        return []

    best_sentence = None
    best_specific: list[str] = []
    best_score = -999

    for idx, sentence in enumerate(sentences):
        specific = build_mc_distractors(
            sentence,
            f"{para_id}:knowledge:{idx}",
            allow_generic=False,
        )
        score = _knowledge_sentence_score(sentence, specific)
        if best_sentence is None or score > best_score:
            best_sentence = sentence
            best_specific = specific
            best_score = score

    if not best_sentence:
        return []

    explanation = f"Per {para_id}: {best_sentence}"
    seed = f"{para_id}:knowledge:{best_sentence}"
    rng = rng_for(seed)
    prefer_true_false = len(best_sentence.split()) > 22 or len(best_sentence) > 180

    if len(best_specific) >= 2 and not prefer_true_false:
        distractors = build_mc_distractors(best_sentence, seed, allow_generic=True)
        choices = [{"text": best_sentence, "is_correct": True}]
        choices.extend({"text": text, "is_correct": False} for text in distractors[:3])
        rng.shuffle(choices)
        return [{
            "instruction": "Which statement is correct?",
            "question_text": "Select the correct statement.",
            "choices": choices,
            "explanation": explanation,
            "difficulty": 1 if len(best_sentence.split()) <= 16 else 2,
        }]

    statement = best_specific[0] if best_specific else best_sentence
    statement_correct = statement == best_sentence
    choices = [
        {"text": "True", "is_correct": statement_correct},
        {"text": "False", "is_correct": not statement_correct},
    ]
    return [{
        "instruction": "Is this statement correct?",
        "question_text": statement,
        "choices": choices,
        "explanation": explanation,
        "difficulty": 1,
    }]


async def generate_activities_for_chapter(
    paragraphs: list[dict],
    types: Optional[list[str]] = None,
    skip_para_ids: Optional[set[str]] = None,
    on_progress: Optional[callable] = None,
) -> dict[str, dict[str, list[dict]]]:
    """
    Batch-generate activities for all paragraphs in a chapter.
    Returns {para_id: {activity_type: [content_json, ...]}}
    """
    import asyncio

    skip = skip_para_ids or set()
    results = {}

    for para in paragraphs:
        para_id = para.get("para_id", "")
        if para_id in skip:
            continue

        activities = await generate_activities_for_paragraph(
            para_id=para_id,
            para_title=para.get("title", ""),
            blocks=para.get("blocks", []),
            types=types,
        )
        results[para_id] = activities

        if on_progress:
            on_progress(para_id, sum(len(v) for v in activities.values()), len(paragraphs))

        await asyncio.sleep(0)

    return results
