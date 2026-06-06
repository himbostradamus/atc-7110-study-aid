"""
Shared deterministic generators used to avoid external authoring API calls.
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Optional


ATC_DISTRACTOR_POOL = [
    "ADVISE", "AFFIRM", "APPROVED", "CANCEL", "CAUTION", "CLEARED", "CONTACT",
    "CONTINUE", "CROSS", "DESCEND", "DIRECT", "DISREGARD", "EXPEDITE", "EXPECT",
    "FILED", "FLIGHT", "GROUND", "HOLD", "IMMEDIATELY", "INCREASE", "INFORMATION",
    "LEFT", "MAINTAIN", "MONITOR", "NEGATIVE", "NOTIFY", "PROCEED", "RADAR",
    "REPORT", "REQUEST", "RIGHT", "ROGER", "RUNWAY", "SEPARATION", "STANDBY",
    "STOP", "TOWER", "TRAFFIC", "TURN", "UNABLE", "VERIFY",
]

TOKEN_MUTATIONS = {
    "ALERT": "ADVISORY",
    "ADVISORY": "ALERT",
    "ATTENTION": "CAUTION",
    "CAUTION": "ATTENTION",
    "AVAILABLE": "UNAVAILABLE",
    "UNAVAILABLE": "AVAILABLE",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
    "CLIMB": "DESCEND",
    "DESCEND": "CLIMB",
    "MAINTAIN": "CLIMB",
    "CONTACT": "MONITOR",
    "MONITOR": "CONTACT",
    "STOP": "CONTINUE",
    "CONTINUE": "STOP",
    "HOLD": "PROCEED",
    "PROCEED": "HOLD",
    "VERIFY": "REPORT",
    "REPORT": "VERIFY",
    "APPROVED": "UNABLE",
    "UNABLE": "APPROVED",
    "IMMEDIATELY": "NOW",
    "DOWN": "UP",
    "UP": "DOWN",
    "ZERO": "ONE",
    "ONE": "TWO",
    "TWO": "THREE",
    "THREE": "FOUR",
    "FOUR": "FIVE",
    "FIVE": "SIX",
    "SIX": "SEVEN",
    "SEVEN": "EIGHT",
    "EIGHT": "NINER",
    "NINER": "EIGHT",
    "GROUND": "TOWER",
    "TOWER": "GROUND",
    "CENTER": "APPROACH",
    "APPROACH": "CENTER",
    "DEPARTURE": "ARRIVAL",
    "ARRIVAL": "DEPARTURE",
    "BRAVO": "CHARLIE",
    "CHARLIE": "BRAVO",
    "PROVIDING": "RECEIVING",
    "RECEIVING": "PROVIDING",
    "SIGNIFICANT": "MINOR",
    "MINOR": "SIGNIFICANT",
    "IDENTIFIED": "OMITTED",
    "OMITTED": "IDENTIFIED",
    "MANDATORY": "OPTIONAL",
    "OPTIONAL": "MANDATORY",
    "RECOMMENDED": "PROHIBITED",
    "PROHIBITED": "RECOMMENDED",
    "APPROPRIATE": "INAPPROPRIATE",
    "INAPPROPRIATE": "APPROPRIATE",
    "WRITING": "VERBALLY",
    "VERBALLY": "WRITING",
    "REVIEW": "IGNORE",
    "IGNORE": "REVIEW",
    "SUBMIT": "WITHHOLD",
    "WITHHOLD": "SUBMIT",
    "SAFE": "UNSAFE",
    "UNSAFE": "SAFE",
    "ALLOW": "PROHIBIT",
    "PROHIBIT": "ALLOW",
    "RUNWAY": "TAXIWAY",
    "TAXIWAY": "RUNWAY",
    "REVISED": "AMENDED",
    "AMENDED": "REVISED",
    "POINT": "DECIMAL",
    "DECIMAL": "POINT",
    "OUTER": "INNER",
    "INNER": "OUTER",
    "VOR": "NDB",
    "NDB": "VOR",
    "ILS": "MLS",
    "MLS": "ILS",
    "HIGH": "LOW",
    "LOW": "HIGH",
    "MORE": "LESS",
    "LESS": "MORE",
    "OPEN": "CLOSED",
    "CLOSED": "OPEN",
    "TRUE": "FALSE",
    "FALSE": "TRUE",
    "MUST": "MAY",
    "MAY": "MUST",
    "BEFORE": "AFTER",
    "AFTER": "BEFORE",
    "IFR": "VFR",
    "VFR": "IFR",
    "MINIMUM": "MAXIMUM",
    "MAXIMUM": "MINIMUM",
}

SPOT_THE_ERROR_NUMBER_TOKENS = {
    "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE",
    "SIX", "SEVEN", "EIGHT", "NINER",
}
SPOT_THE_ERROR_DIRECTION_TOKENS = {
    "LEFT", "RIGHT", "NORTH", "SOUTH", "EAST", "WEST",
}
SPOT_THE_ERROR_FACILITY_TOKENS = {
    "GROUND", "TOWER", "CENTER", "APPROACH", "DEPARTURE", "ARRIVAL", "RADIO",
}
SPOT_THE_ERROR_SURFACE_TOKENS = {
    "RUNWAY", "TAXIWAY", "HELIPAD",
    "ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT",
    "GOLF", "HOTEL", "INDIA", "JULIET", "JULIETT", "KILO",
    "LIMA", "MIKE", "NOVEMBER", "OSCAR", "PAPA", "QUEBEC",
    "ROMEO", "SIERRA", "TANGO", "UNIFORM", "VICTOR",
    "WHISKEY", "XRAY", "X-RAY", "YANKEE", "ZULU",
}
SPOT_THE_ERROR_CONTEXTUAL_TOKENS = (
    SPOT_THE_ERROR_NUMBER_TOKENS
    | SPOT_THE_ERROR_DIRECTION_TOKENS
    | SPOT_THE_ERROR_FACILITY_TOKENS
    | SPOT_THE_ERROR_SURFACE_TOKENS
)
ALLOWED_ADJACENT_DUPLICATE_TOKENS = SPOT_THE_ERROR_NUMBER_TOKENS | {"MAYDAY"}

GENERIC_DECISION_ERRORS = [
    "Treat the action as optional unless the pilot specifically requests it.",
    "Delay the action until workload permits before applying the rule.",
    "Apply the rule only after another controller confirms the need for it.",
    "Wait for pilot confirmation before carrying out the action.",
]
GENERIC_DECISION_ERROR_PREFIXES = tuple(
    re.sub(r"\s+", " ", item).strip().rstrip(".")
    for item in GENERIC_DECISION_ERRORS
)

GENERIC_MC_DISTRACTORS = [
    "The section makes the action optional unless specifically requested.",
    "The section applies only after pilot confirmation.",
    "The section narrows the rule to fewer cases than stated.",
    "The section describes a recommendation rather than a requirement.",
    "The section applies only when local workload permits.",
]

STATEMENT_REPLACEMENTS = [
    ("not responsible", "responsible"),
    ("identified in", "omitted from"),
    ("for use by", "for reference by"),
    ("in writing", "verbally"),
    ("in accordance with", "contrary to"),
    ("consistent with", "contrary to"),
    ("required to", "not required to"),
    ("should submit", "should not submit"),
    ("must review", "may ignore"),
    ("must be submitted", "may be submitted"),
    ("must be used", "need not be used"),
    ("prior to", "after"),
    ("after", "before"),
    ("before", "after"),
    ("at least", "at most"),
    ("at most", "at least"),
    ("more than", "less than"),
    ("less than", "more than"),
    ("must", "may"),
    ("shall", "may"),
    ("should", "may"),
    ("may", "must"),
    ("required", "optional"),
    ("available", "unavailable"),
    ("identified", "omitted"),
    ("published", "withheld"),
    ("prescribes", "recommends"),
    ("recommends", "prescribes"),
    ("applies to", "does not apply to"),
    ("applies", "does not apply"),
    ("includes", "excludes"),
    ("approved", "denied"),
    ("authorized", "prohibited"),
    ("difficult", "easy"),
    ("outside", "inside"),
    ("inside", "outside"),
    ("primary", "secondary"),
    ("fundamental", "secondary"),
    ("same", "different"),
]
LOW_QUALITY_VARIANT_PATTERNS = (
    re.compile(r"\b(?:not not|need not not|may not not|must not not|should not not|do not not)\b", re.IGNORECASE),
    re.compile(r"\bnot all to\b", re.IGNORECASE),
    re.compile(r"\bonly all\b|\ball only\b", re.IGNORECASE),
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
ACTION_SPECIFIC_REPLACEMENTS = (
    ('will include the phrase', 'will omit the phrase'),
    ('must include the phrase', 'must omit the phrase'),
    ('must include the letter', 'must omit the letter'),
    ('include the name of', 'omit the name of'),
    ('is not to be used for', 'is to be used for'),
    ('is to be used for', 'is not to be used for'),
    ('is aware of', 'is not aware of'),
    ('is notified of', 'is not notified of'),
    ('is not expected to', 'is expected to'),
    ('must not be', 'must be'),
    ('only if', 'even if'),
    ('full identification', 'abbreviated identification'),
    ('exactly as issued', 'in paraphrased form'),
    ('transmit these values', 'withhold these values'),
    ('normal sequence used for weather reporting', 'reverse order from the normal weather-reporting sequence'),
    ('always state both', 'state only one of'),
    ('accurately reflects', 'inaccurately reflects'),
    ('from any other aircraft', 'with other aircraft'),
    ('DVFR to', 'VFR to'),
)
ACTION_MARKER_POOL = ("A", "B", "C", "D", "H", "L", "R", "Z")
ACTION_ALT_RE = re.compile(
    r"\b(?:Another controller|A trainee|A coworker|One controller|A second controller)\s+"
    r"(?:wants|says|suggests|proposes|assumes)\s+(.+?)(?:[.?!]|$)",
    re.IGNORECASE,
)

PHRASEOLOGY_PRIORITY_PHRASES = (
    "ADVISE",
    "ALERT",
    "CLEARED",
    "CHECK",
    "CONTACT",
    "MAINTAIN",
    "MONITOR",
    "CLIMB",
    "DESCEND",
    "TURN",
    "RUNWAY",
    "HOLD",
    "CROSS",
    "TAXI",
    "SQUAWK",
    "ALTIMETER",
    "FLIGHT LEVEL",
    "HEADING",
    "REPORT",
)
PHRASEOLOGY_FILL_PRIORITY_TOKENS = set(PHRASEOLOGY_PRIORITY_PHRASES) | {
    "APPROVED",
    "AVAILABLE",
    "BRAKING",
    "CAUTION",
    "CONTACT",
    "CROSSING",
    "HOLDING",
    "IMMEDIATELY",
    "MAYDAY",
    "MISSED",
    "OUTSIDE",
    "POSITION",
    "SIDE-STEP",
    "SHORT",
}
LOW_VALUE_PHRASEOLOGY_BLANK_TOKENS = {
    "AIRCRAFT",
    "AIRPORT",
    "ALTITUDE",
    "CALL",
    "CALLSIGN",
    "DEGREES",
    "DIRECTION",
    "DISTANCE",
    "FACILITY",
    "FREQUENCY",
    "HEADING",
    "IDENT",
    "LOCATION",
    "MILE",
    "MILES",
    "NAME",
    "NUMBER",
    "ROUTE",
    "RUNWAY",
    "SIGN",
    "TYPE",
}
PHRASEOLOGY_FRAGMENT_PREFIXES = (
    "OR ",
    "AND ",
    "WHEN ",
    "IF ",
    "THEN ",
    "PRECEDED BY ",
    "FOLLOWED BY ",
    "FOR ",
    "TO ",
    "OF ",
    "IN ",
)
READBACK_DISALLOWED_PREFIXES = (
    "ATTENTION ALL AIRCRAFT",
    "CAUTION",
    "CHECK ",
    "POSSIBLE PILOT DEVIATION",
    "ACTIVE RUNWAY",
    "CAB AND APPROACH",
    "THE ALTIMETER",
    "PRECEDED BY",
    "FOLLOWED BY",
    "REQUEST ",
    "OR ",
)
READBACK_DISALLOWED_PHRASES = (
    "MAY OPT",
    "INFORMATION ALERTS ONLY",
    "REPORTED UNRELIABLE",
    "FOR PURPOSES OTHER THAN",
)
OPERATIONAL_KEYWORDS = (
    "AIRCRAFT",
    "PILOT",
    "CONTROLLER",
    "TRAFFIC",
    "RUNWAY",
    "TAXI",
    "TAXIWAY",
    "TAKEOFF",
    "LANDING",
    "APPROACH",
    "DEPARTURE",
    "ARRIVAL",
    "RADAR",
    "VECTOR",
    "SEPARATION",
    "WEATHER",
    "WIND",
    "TURBULENCE",
    "ALTIMETER",
    "ALTITUDE",
    "FLIGHT LEVEL",
    "HEADING",
    "CLEARANCE",
    "COMMUNICATION",
    "FREQUENCY",
    "AIRSPACE",
    "SQUAWK",
    "BEACON",
    "HOLD",
    "CROSS",
)
ADMIN_TITLE_TERMS = (
    "PURPOSE",
    "AUDIENCE",
    "WHERE TO FIND",
    "WHAT THIS ORDER CANCELS",
    "EXPLANATION OF CHANGES",
    "EFFECTIVE DATES",
    "DELIVERY DATES",
    "RECOMMENDATIONS",
    "REQUESTS FOR INTERPRETATIONS",
    "WAIVERS",
    "SERVICE AREA",
    "PUBLICATIONS",
    "WEBSITE",
)
DOCUMENT_CONTROL_KEYWORDS = (
    "order",
    "changes",
    "change",
    "published",
    "publication",
    "effective",
    "website",
    "distributed",
    "distribution",
    "applies",
    "apply",
    "canceled",
    "cancelled",
    "waiver",
    "waivers",
    "safety",
    "sms",
    "employees",
    "subscribers",
    "submissions",
    "directive",
    "directives",
    "audience",
    "purpose",
    "toolbox",
)
ACTION_VERBS = (
    "authorize",
    "continue",
    "must",
    "shall",
    "should",
    "ensure",
    "issue",
    "provide",
    "obtain",
    "assign",
    "use",
    "apply",
    "advise",
    "inform",
    "separate",
    "vector",
    "coordinate",
    "approve",
    "deny",
    "determine",
    "add",
    "maintain",
    "climb",
    "descend",
    "turn",
    "hold",
    "clear",
    "instruct",
    "broadcast",
    "verify",
    "monitor",
    "contact",
    "take",
    "change",
    "identify",
    "record",
    "annotate",
    "transmit",
    "delay",
    "release",
    "relay",
    "specify",
)
REFERENCE_ORDER_RE = re.compile(r"(FAA\s+Order\s+JO\s+[0-9.]+[A-Z]*)", re.IGNORECASE)
REFERENCE_PARA_RE = re.compile(r"(Para\s+\d+[−\-]\d+[−\-]\d+)", re.IGNORECASE)
REFERENCE_CHAPTER_SECTION_RE = re.compile(
    r"(Chapter\s+\d+(?:,\s*Section\s+\d+)?)",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
INLINE_FIG_TBL_RE = re.compile(r"\(\s*See\s*(?:TBL|FIG)[^)]*\)", re.IGNORECASE)
BARE_CITATION_LEAD_RE = re.compile(r"^(?:FAA\s+Order\s+JO|ICAO\s+DOC|14\s+CFR|P/CG\s+Term)\b", re.IGNORECASE)
ADMIN_SUBSTANCE_RE = re.compile(
    r"\b(?:is|are|was|were|canceled|cancelled|retained|prescribes?|applies?|available|"
    r"distributed|distribution|responsible|submi(?:t|tted)|contact|found|effective|"
    r"published|updated|revised|establishes?)\b",
    re.IGNORECASE,
)
EXAMPLE_LABEL_RE = re.compile(r"\b([A-Za-z][A-Za-z /'\-]{2,20})\s*:\s*\"([^\"]{3,180})\"")
QUOTE_CONTENT_RE = re.compile(r"\"([^\"]{3,180})\"")
PAIR_LEADING_MARKER_RE = re.compile(r"^(?:[a-z]|\d+)\.\s+", re.IGNORECASE)
PAIR_SKIP_RE = re.compile(
    r"(?:\bJO\s*7110\.65\b|\bFAA\b|^\d{1,2}/\d{1,2}/\d{2,4}$|^Page\s+\d+$)",
    re.IGNORECASE,
)
QUOTE_TRANSLATION = str.maketrans({
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
})
AUXILIARY_VERB_RE = re.compile(
    r"\b(?:is|are|must|may|should|will|was|were|be|being|been|"
    r"has|have|had|does|do|did|can|could|shall)\b",
    re.IGNORECASE,
)
IMPERATIVE_START_RE = re.compile(
    r"^(?:Issue|Request|Report|Move|Forward|Retain|Prefix|Use|Respond|Consider|"
    r"Clear|Confirm|Maintain|Coordinate|Inform|Advise|Apply|Provide|Transfer|"
    r"Assign|Establish|Obtain|Contact|Monitor|Check|State|Describe|Separate|"
    r"Remind|Broadcast|Ensure|Turn|Climb|Descend|Approve|Interrupt|Relay|"
    r"Terminate|Inhibit|Keep|Change|Identify|Record|Annotate|Transmit|Notify|"
    r"Instruct|Direct|"
    r"Delay|Release|Specify)\b",
    re.IGNORECASE,
)
CONTENT_VERB_RE = re.compile(
    r"\b(?:apply|applies|use|uses|keep|keeps|operate|operates|transmit|transmits|"
    r"affect|affects|relieve|relieves|support|supports|include|includes|"
    r"govern|governs|direct|directs|require|requires|relay|relays|terminate|"
    r"terminates|approve|approves|interrupt|interrupts|inhibit|inhibits|"
    r"establish|establishes|maintain|maintains|provide|provides|clear|clears|"
    r"record|records|change|changes|identify|identifies|annotate|annotates|"
    r"specify|specifies|delay|delays|continue|continues|transfer|transfers)\b",
    re.IGNORECASE,
)
CONDITIONAL_START_RE = re.compile(
    r"^(?:If|When|Where|Upon|After|Before|Unless|In the event|Except(?: when)?)\b",
    re.IGNORECASE,
)
CONDITIONAL_CUE_RE = re.compile(
    r"\b(?:if|when|where|upon|after|before|unless|in the event|except(?: when)?)\b",
    re.IGNORECASE,
)
DEICTIC_LEAD_RE = re.compile(r"^(?:This|These|That|Those)\b", re.IGNORECASE)
DEFINITION_CUE_RE = re.compile(
    r"\b(?:means|refers to|is defined as|are defined as|is set forth as|are set forth as)\b",
    re.IGNORECASE,
)
TERM_DEFINITION_PATTERN_RE = re.compile(
    r'^(?:The term\s+)?["\']?[A-Za-z0-9/()"\' -]{3,80}["\']?\s+'
    r'(?:means|refers to|is defined as|are defined as|is set forth as|are set forth as|'
    r'is based on|are based on)\s+.{3,220}[.!?]?$',
    re.IGNORECASE,
)
TERM_DEFINITION_LEAD_RE = re.compile(
    r'^(?:The term\s+)?["\']?[A-Za-z0-9/()"\' -]{3,80}["\']?\s+'
    r'(?:means|refers to|is defined as|are defined as|is set forth as|are set forth as|'
    r'is based on|are based on)\b',
    re.IGNORECASE,
)
LOW_SIGNAL_SENTENCE_RE = re.compile(r"^(?:TBL|FIG|\(?See\s+(?:TBL|FIG))\b", re.IGNORECASE)
UPPER_LABEL_PREFIX_RE = re.compile(r"^(?:EN ROUTE|TERMINAL|USA/USAF/USN NOT APPLICABLE)\s+", re.IGNORECASE)
COLON_LABEL_RE = re.compile(r"^[A-Z][A-Z0-9/&() .-]{2,45}:\s+")
TABLEISH_LINE_RE = re.compile(
    r"^(?:"
    r"TBL\b|FIG\b|"
    r"\d+\s+(?:Less|More|When|At|Below|Above|Within|Behind|Category|One|Any)\b|"
    r"(?:Step|Visibility|Day|Night|Examples|Aircraft|Operating|magnetic|surface)\b"
    r")",
    re.IGNORECASE,
)
RUNNING_HEADER_RE = re.compile(
    r"^(?:JO\s*7110\.65.*|\d{1,2}/\d{1,2}/\d{2,4}|[A-Z][A-Za-z /-]{6,}\s+\d+[−\-]\d+[−\-]\d+)$",
    re.IGNORECASE,
)
BAD_SENTENCE_FRAGMENT_RE = re.compile(
    r"\b(?:Application of the Mach Number Technique When the Following Aircraft is Faster|"
    r"Distance to Fly and Separation(?: \(in Minutes\))? Required at Entry Point|"
    r"Section\s+\d+)\b",
    re.IGNORECASE,
)
INCOMPLETE_SENTENCE_TAIL_RE = re.compile(
    r"\b(?:after|before|during|when|while|unless|until|if|because|than|from|to|of|for|"
    r"with|without|between|within|on|in|at|by|or|and|the|a|an)$",
    re.IGNORECASE,
)
INTRO_CLAUSE_IMPERATIVE_RE = re.compile(
    r",\s*(?:do not\s+)?(?:Issue|Request|Report|Move|Forward|Retain|Prefix|Use|Respond|"
    r"Consider|Clear|Confirm|Maintain|Coordinate|Inform|Advise|Apply|Provide|Transfer|"
    r"Assign|Establish|Obtain|Contact|Monitor|Check|State|Describe|Separate|Remind|"
    r"Broadcast|Ensure|Turn|Climb|Descend|Approve|Interrupt|Relay|Terminate|Inhibit|"
    r"Keep|Change|Identify|Record|Annotate|Transmit|Notify|Instruct|Direct|Delay|"
    r"Release|Specify)\b",
    re.IGNORECASE,
)
SCENARIO_FRAMES = (
    (
        ("RUNWAY", "TAXI", "TAXIWAY", "HOLD SHORT", "LINE UP", "TAKEOFF", "LAND"),
        "You are working local or ground control with aircraft operating on or near the runway.",
    ),
    (
        ("WEATHER", "WIND", "TURBULENCE", "WINDSHEAR", "ALTIMETER", "BRAKING", "VISIBILITY"),
        "Weather or aerodrome conditions are affecting traffic you are handling.",
    ),
    (
        ("RADAR", "VECTOR", "HEADING", "TURN"),
        "You are providing radar services to an aircraft in your sector.",
    ),
    (
        ("CLIMB", "DESCEND", "ALTITUDE", "FLIGHT LEVEL"),
        "You are issuing altitude or flight level instructions to an aircraft in flight.",
    ),
    (
        ("CLEARANCE", "IFR", "VFR", "ROUTE", "DEPARTURE", "ARRIVAL"),
        "You are issuing or amending a clearance for an aircraft.",
    ),
    (
        ("SEPARATION", "TRAFFIC", "CONFLICT", "WAKE"),
        "You are managing a traffic situation that requires controller action.",
    ),
    (
        ("COORDINATE", "FACILITY", "TRANSFER", "LOA"),
        "You are coordinating responsibility with another position or facility.",
    ),
)

STOPWORDS = {
    "A", "AN", "AND", "AT", "FOR", "FROM", "IN", "IS", "OF", "ON", "OR",
    "THE", "TO", "YOUR", "YOU", "ALL", "WITH",
}
GENERIC_SECTION_TITLES = {
    "APPLICATION",
    "DESCRIPTION",
    "GENERAL",
    "PROCEDURES",
    "PURPOSE",
    "RESPONSIBILITY",
    "TERMINOLOGY",
}
PARA_HEADING_RE = re.compile(r"^\s*\d+[−\-]\d+[−\-]\d+\.\s+.*?(?:\n+|$)")
LEADING_MARKER_RE = re.compile(r"^\s*(?:[a-z]|\d+)\.\s+", re.IGNORECASE)
BLOCK_LABEL_RE = re.compile(r"^\s*(?:NOTE|REFERENCE|EXAMPLE|PHRASEOLOGY|INTERPRETATION)[−\-:]?\s*", re.IGNORECASE)
SCOPE_TITLE_TERMS = (
    "APPLICATION",
    "AUDIENCE",
    "PURPOSE",
    "RESPONSIBILITY",
    "DISTRIBUTION",
    "DESCRIPTION",
    "ROUTING",
    "ALTITUDE ASSIGNMENT",
    "SEPARATION MINIMA",
    "FREQUENCY CHANGES",
)
SCOPE_SENTENCE_RE = re.compile(
    r"\b(?:applies?|apply|used?|use|responsib(?:le|ility)|required|must|need not|"
     r"does not relieve|relieve|familiar|adhere|recorded|annotate|specify|"
    r"subject to|solely|authorized|available|distributed|cancel(?:ed|led)?|"
    r"set forth as|defined as|"
    r"found|viewing|downloading)\b",
    re.IGNORECASE,
)
REQUIREMENT_SENTENCE_RE = re.compile(
    r"\b(?:must|shall|should|required|need not|may not|do not|only if|only when|"
    r"unless|use|monitor|terminate|transmit|record|relay|specify|continue|"
    r"annotate|identify|forward|advise|inform|interrupt|retain|clear|assign|"
    r"provide|separate|authorize|approve|insert|coordinate|advisable|"
    r"instruct|direct|turn|change)\b",
    re.IGNORECASE,
)
CAPABILITY_SENTENCE_RE = re.compile(
    r"\b(?:is an integrated function|uses?|provides?|predicts?|deriv(?:e|es)|"
    r"records?|automatically recorded|is based on|are based on|will remove|"
    r"may be affected|establishes procedures|supports?|needed for|capabilit(?:y|ies))\b",
    re.IGNORECASE,
)
MINIMA_SENTENCE_RE = re.compile(
    r"\b(?:minimum|minima|mile|miles|foot|feet|flight level|laterally|vertically|"
    r"above|below|protected airspace|separation|29\.92|altimeter|agl|nm)\b",
    re.IGNORECASE,
)
MINIMA_VALUE_RE = re.compile(
    r"\b(?:\d+(?:,\d+)?(?:\.\d+)?)\s*(?:mile|miles|foot|feet|minute|minutes|nm|agl|inches?\s*hg)\b",
    re.IGNORECASE,
)
LIST_INTRO_CUE_RE = re.compile(
    r"\b(?:one of the following|as follows|"
    r"following conditions? (?:is|are) met|"
    r"following actions? (?:are|is) taken|"
    r"the following (?:conditions?|actions?|items?|information|services?|techniques?|procedures?))\b",
    re.IGNORECASE,
)
CLAUSE_LEAD_RE = re.compile(
    r"\b(?:If|When|Where|Upon|After|Before|Unless|Except(?: when)?)\b",
    re.IGNORECASE,
)


def rng_for(*parts: object) -> random.Random:
    key = "||".join(str(p) for p in parts)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def normalise_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_display_text(text: str) -> str:
    clean = normalise_ws(text).translate(QUOTE_TRANSLATION)
    if not clean:
        return clean
    clean = re.sub(r'(?<=[A-Za-z0-9])"([^"]+)"(?=[A-Za-z0-9])', r' "\1" ', clean)
    clean = re.sub(r'(?<=[A-Za-z0-9])"([^"]+)"', r' "\1"', clean)
    clean = re.sub(r'"([^"]+)"(?=[A-Za-z0-9])', r'"\1" ', clean)
    clean = re.sub(r"\s+([,.;:?!])", r"\1", clean)
    clean = re.sub(r'"\s*([^"]*?)\s*"', r'"\1"', clean)
    clean = re.sub(r"([(\[“‘])\s+", r"\1", clean)
    clean = re.sub(r"\s+([)\]”’])", r"\1", clean)
    return normalise_ws(clean)


def display_section_label(title: str, fallback: str = "") -> str:
    clean = normalize_display_text(title).strip()
    clean = clean.rstrip(".;:!?")
    if not clean:
        return fallback
    if clean.upper() in GENERIC_SECTION_TITLES:
        return fallback
    return clean


def is_tableish_line(line: str) -> bool:
    candidate = normalise_ws(line)
    if not candidate:
        return False
    if TABLEISH_LINE_RE.match(candidate) or RUNNING_HEADER_RE.match(candidate):
        return True
    if re.match(r"^\d+\s+(?:mile|miles|foot|feet|minute|minutes)\b", candidate, re.IGNORECASE):
        if not re.search(r"[.!?,;]", candidate):
            return True
    if candidate.count("  ") >= 2 and not re.search(r"[.!?]", candidate):
        return True
    if (
        len(re.findall(r"\b\d+\b", candidate)) >= 2
        and re.match(r"^\d", candidate)
        and not AUXILIARY_VERB_RE.search(candidate)
        and not IMPERATIVE_START_RE.match(candidate)
        and not CONTENT_VERB_RE.search(candidate)
    ):
        return True
    words = candidate.split()
    if (
        len(words) <= 5
        and not re.search(r"[.!?]", candidate)
        and not AUXILIARY_VERB_RE.search(candidate)
        and not IMPERATIVE_START_RE.match(candidate)
        and not CONTENT_VERB_RE.search(candidate)
        and all(
            word[:1].isupper()
            or word[:1].isdigit()
            or word.upper() in STOPWORDS
            for word in words
        )
    ):
        return True
    if (
        len(words) <= 6
        and candidate.upper() == candidate
        and not AUXILIARY_VERB_RE.search(candidate)
    ):
        return True
    return False


def prose_text(text: str) -> str:
    cleaned = strip_paragraph_heading(text)
    if not cleaned:
        return ""

    segments: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        current = normalise_ws(current)
        if current:
            segments.append(current)
        current = ""

    for raw_line in cleaned.splitlines():
        line = raw_line.rstrip()
        candidate = normalise_ws(line)
        if not candidate:
            flush()
            continue
        if is_tableish_line(line):
            flush()
            continue

        bullet = bool(LEADING_MARKER_RE.match(candidate))
        candidate = BLOCK_LABEL_RE.sub("", candidate)
        candidate = LEADING_MARKER_RE.sub("", candidate)
        if not candidate:
            continue

        if bullet:
            flush()
            current = candidate
            continue

        if not current:
            current = candidate
            continue

        if current.endswith((".", "!", "?", ";")):
            flush()
            current = candidate
            continue

        current = f"{current} {candidate}"

    flush()
    return "\n".join(segments)


def sentence_split(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", normalise_ws(prose_text(text))) if p.strip()]
    if not parts:
        return []

    merged: list[str] = []
    abbreviation_tail_re = re.compile(r"\b(?:[A-Z]\.){2,}$")

    for part in parts:
        if (
            merged
            and abbreviation_tail_re.search(merged[-1])
            and re.match(r"^[a-z]", part)
        ):
            merged[-1] = f"{merged[-1]} {part}"
            continue
        merged.append(part)

    return [p for p in merged if len(p.split()) >= 3]


def strip_paragraph_heading(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
    return PARA_HEADING_RE.sub("", cleaned, count=1).strip()


def clean_sentence_candidate(sentence: str) -> str:
    cleaned = normalise_ws(sentence)
    cleaned = cleaned.translate(QUOTE_TRANSLATION)
    cleaned = BLOCK_LABEL_RE.sub("", cleaned)
    cleaned = LEADING_MARKER_RE.sub("", cleaned)
    cleaned = UPPER_LABEL_PREFIX_RE.sub("", cleaned)
    cleaned = COLON_LABEL_RE.sub("", cleaned)
    cleaned = re.sub(r"\(\s*[a-z]\s*\)", "", cleaned, flags=re.IGNORECASE)
    if len(cleaned) > 220 and "(" in cleaned and ")" in cleaned:
        without_parenthetical = normalise_ws(re.sub(r"\([^)]{1,120}\)", "", cleaned))
        if len(without_parenthetical.split()) >= 4:
            cleaned = without_parenthetical
    cleaned = cleaned.rstrip(":")
    cleaned = cleaned.replace("O rders", "Orders")
    return cleaned.strip()


def strip_urls_and_contacts(text: str) -> str:
    cleaned = URL_RE.sub("", text)
    cleaned = EMAIL_RE.sub("", cleaned)
    cleaned = INLINE_FIG_TBL_RE.sub("", cleaned)
    cleaned = re.sub(r"\bwebsite at\b", "website", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bat and\b", " and", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(" & ", " and ")
    return normalise_ws(cleaned).strip(" ,;")


def sentence_case_lead(text: str) -> str:
    for idx, char in enumerate(text):
        if not char.isalpha():
            continue
        if char.isupper():
            return text
        return f"{text[:idx]}{char.upper()}{text[idx + 1:]}"
    return text


def is_bare_reference_sentence(sentence: str) -> bool:
    clean = normalise_ws(sentence)
    return bool(BARE_CITATION_LEAD_RE.match(clean) and not ADMIN_SUBSTANCE_RE.search(clean))


def is_fragmentary_sentence(sentence: str) -> bool:
    clean = normalise_ws(sentence)
    if not clean:
        return True
    if LOW_SIGNAL_SENTENCE_RE.match(clean):
        return True
    if BAD_SENTENCE_FRAGMENT_RE.search(clean):
        return True
    if INCOMPLETE_SENTENCE_TAIL_RE.search(clean.rstrip(".!?")):
        return True
    return False


def trim_list_intro_clause(sentence: str) -> str:
    if ":" not in sentence:
        return sentence

    head, tail = sentence.split(":", 1)
    head = normalise_ws(head).rstrip(" ,;")
    tail = normalise_ws(tail)
    if not head or not tail:
        return sentence
    if not IMPERATIVE_START_RE.match(head):
        return sentence

    trimmed = re.sub(
        r"(?:,\s*)?(?:when|if|where|unless|except(?: when)?)$",
        "",
        head,
        flags=re.IGNORECASE,
    ).rstrip(" ,;")
    if len(trimmed.split()) < 4:
        return sentence
    return trimmed


def is_overloaded_procedure_sentence(sentence: str) -> bool:
    clean = normalise_ws(sentence)
    if not clean:
        return True
    if LIST_INTRO_CUE_RE.search(clean):
        return True
    if clean.count(";") >= 2:
        return True
    if ":" in clean:
        head, tail = clean.split(":", 1)
        if len(head.split()) >= 4 and len(tail.split()) >= 5:
            return True
    if len(CLAUSE_LEAD_RE.findall(clean)) >= 2 and len(clean.split()) > 28:
        return True
    if clean.count(",") >= 5 and len(clean.split()) > 32:
        return True
    return False


def meaningful_sentences_from_text(text: str) -> list[str]:
    sentences: list[str] = []
    seen: set[str] = set()

    for raw_sentence in sentence_split(text):
        sentence = clean_sentence_candidate(raw_sentence)
        lower = sentence.lower()
        has_prose_verb = (
            AUXILIARY_VERB_RE.search(sentence)
            or IMPERATIVE_START_RE.match(sentence)
            or CONTENT_VERB_RE.search(lower)
        )
        if len(sentence) > 360:
            if len(sentence) > 480:
                continue
        if ":" in sentence:
            tail = sentence.rsplit(":", 1)[1].strip(" .")
            if tail and len(tail.split()) <= 3 and tail.upper() == tail:
                continue
        if re.match(r"^\d", sentence):
            continue
        if LOW_SIGNAL_SENTENCE_RE.match(sentence):
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9 /-]{4,}", sentence):
            continue
        if len(re.findall(r"\b\d+\b", sentence)) > 8:
            continue
        if len(re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", sentence)) >= 2:
            continue
        if re.fullmatch(r"(?:[A-Za-z]|\d+)\.", sentence.strip()):
            continue
        if len(re.findall(r"[A-Za-z]{3,}", sentence)) < 4 and not has_prose_verb:
            continue
        if not has_prose_verb:
            continue
        if is_fragmentary_sentence(sentence):
            continue
        if is_bare_reference_sentence(sentence):
            continue
        if sentence not in seen:
            seen.add(sentence)
            sentences.append(sentence)

    return sentences


def select_document_control_sentence(para_title: str, text: str) -> Optional[str]:
    sentences = meaningful_sentences_from_text(text)
    if not sentences:
        return None

    title_upper = para_title.upper()
    best_rank = (-999, 0)
    best_sentence = None

    for raw_sentence in sentences:
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            continue
        if is_fragmentary_sentence(sentence) or is_bare_reference_sentence(sentence):
            continue

        words = sentence.split()
        if len(words) < 4 or len(words) > 32:
            continue

        lower = sentence.lower()
        score = 0
        if any(term in title_upper for term in ADMIN_TITLE_TERMS):
            score += 4
        if "this order" in lower:
            score += 3
        score += sum(1 for keyword in DOCUMENT_CONTROL_KEYWORDS if keyword in lower)
        if REFERENCE_ORDER_RE.search(sentence):
            score += 2
        if len(re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", sentence)) >= 2:
            score -= 4
        if len(words) <= 18:
            score += 1

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    if best_rank[0] < 4 or not best_sentence:
        return None
    if best_sentence.endswith((".", "!", "?")):
        return best_sentence
    return f"{best_sentence}."


def select_scope_sentence(para_title: str, text: str) -> Optional[str]:
    sentences = meaningful_sentences_from_text(text)
    if not sentences:
        return None

    title_upper = para_title.upper()
    best_rank = (-999, 0)
    best_sentence = None

    for raw_sentence in sentences:
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            continue
        if is_fragmentary_sentence(sentence) or is_bare_reference_sentence(sentence):
            continue
        if is_overloaded_procedure_sentence(sentence):
            continue

        words = sentence.split()
        if len(words) < 4 or len(words) > 36:
            continue

        lower = sentence.lower()
        score = 0
        if any(term in title_upper for term in SCOPE_TITLE_TERMS):
            score += 3
        if "this order" in lower:
            score += 2
        elif DEICTIC_LEAD_RE.match(sentence):
            score -= 4
        if IMPERATIVE_START_RE.match(sentence) or lower.startswith("do not "):
            score -= 5
        if re.search(r"\b(?:applies to|are to be used|used solely|must be|need not|does not relieve|must adhere)\b", lower):
            score += 4
        if SCOPE_SENTENCE_RE.search(sentence):
            score += 3
        if AUXILIARY_VERB_RE.search(sentence):
            score += 1
        if len(re.findall(r"\b\d+\b", sentence)) >= 4:
            score -= 2
        if any(term in lower for term in ("figure", "table", "tbl", "website")):
            score -= 1

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    if best_rank[0] < 4 or not best_sentence:
        return None
    return _sentence_with_period(best_sentence)


def select_requirement_sentence(text: str) -> Optional[str]:
    best_rank = (-999, 0)
    best_sentence = None

    def consider(raw_sentence: str) -> None:
        nonlocal best_rank, best_sentence
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            return
        sentence = trim_list_intro_clause(sentence)
        sentence = sentence_case_lead(sentence)
        if not sentence:
            return
        if is_fragmentary_sentence(sentence) or is_bare_reference_sentence(sentence):
            return
        if is_overloaded_procedure_sentence(sentence):
            return

        words = sentence.split()
        if len(words) < 4 or len(words) > 34:
            return

        lower = sentence.lower()
        score = 0
        if IMPERATIVE_START_RE.match(sentence) or lower.startswith("do not "):
            score += 4
        elif CONDITIONAL_START_RE.match(sentence) and INTRO_CLAUSE_IMPERATIVE_RE.search(sentence):
            score += 4
        if REQUIREMENT_SENTENCE_RE.search(sentence):
            score += 3
        if any(verb in lower for verb in ACTION_VERBS):
            score += 2
        if CONDITIONAL_CUE_RE.search(sentence):
            score += 2
        if re.search(r"\b(?:only if|only when|unless|need not|may not)\b", lower):
            score += 2
        if sentence.startswith("For ") and re.search(r"\b(?:use|annotate|record|continue)\b", lower):
            score += 2
        if "advisable" in lower:
            score += 1
        if len(words) <= 22:
            score += 1
        if DEICTIC_LEAD_RE.match(sentence) and not lower.startswith("this order"):
            score -= 4
        if any(term in lower for term in ("website", "order", "publication")) and not IMPERATIVE_START_RE.match(sentence):
            score -= 2
        if any(term in lower for term in ("figure", "table", "tbl")):
            score -= 4

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    for raw_sentence in meaningful_sentences_from_text(text):
        consider(raw_sentence)

    if best_rank[0] < 5:
        for raw_line in strip_paragraph_heading(text).splitlines():
            candidate = clean_sentence_candidate(raw_line)
            if not candidate or RUNNING_HEADER_RE.match(candidate) or is_tableish_line(candidate):
                continue
            consider(candidate)

    if best_rank[0] < 4 or not best_sentence:
        return None
    return _sentence_with_period(best_sentence)


def select_capability_sentence(para_title: str, text: str) -> Optional[str]:
    sentences = meaningful_sentences_from_text(text)
    if not sentences:
        return None

    title_upper = para_title.upper()
    best_rank = (-999, 0)
    best_sentence = None

    for raw_sentence in sentences:
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            continue
        if is_fragmentary_sentence(sentence) or is_bare_reference_sentence(sentence):
            continue

        words = sentence.split()
        if len(words) < 5 or len(words) > 46:
            continue

        lower = sentence.lower()
        score = 0
        if DEICTIC_LEAD_RE.match(sentence) and not lower.startswith("this order"):
            score -= 4
        if IMPERATIVE_START_RE.match(sentence):
            score -= 4
        if CONDITIONAL_START_RE.match(sentence):
            score -= 2
        if "is an integrated function" in lower:
            score += 6
        if re.search(r"\b(?:uses|provides|predicts|derives|records|supports)\b", lower):
            score += 3
        if re.search(r"\b(?:is based on|are based on|will remove|may be affected|establishes procedures)\b", lower):
            score += 4
        if "data" in lower or "notification" in lower or "equipment" in lower:
            score += 1
        if "description" in title_upper or "application" in title_upper:
            score += 1
        if len(re.findall(r"\b[A-Z]{2,}\b", sentence)) >= 2:
            score += 1

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    if best_rank[0] < 4 or not best_sentence:
        return None
    return _sentence_with_period(best_sentence)


def select_minima_rule_sentence(text: str) -> Optional[str]:
    best_rank = (-999, 0)
    best_sentence = None

    def consider(raw_sentence: str) -> None:
        nonlocal best_rank, best_sentence
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            return
        if is_fragmentary_sentence(sentence) or is_bare_reference_sentence(sentence):
            return
        if is_overloaded_procedure_sentence(sentence):
            return

        words = sentence.split()
        if len(words) < 6 or len(words) > 42:
            return

        lower = sentence.lower()
        score = 0
        if DEICTIC_LEAD_RE.match(sentence) and not lower.startswith("this order"):
            score -= 4
        if MINIMA_SENTENCE_RE.search(sentence):
            score += 4
        if MINIMA_VALUE_RE.search(sentence) or "29.92" in sentence:
            score += 4
        if "consider separation to exist" in lower or "at least" in lower:
            score += 2
        if re.search(r"\b(?:separate|avoid|assign|reduce|protect)\b", lower):
            score += 2
        if re.search(r"\b(?:laterally|vertically|above|below|within)\b", lower):
            score += 2
        if IMPERATIVE_START_RE.match(sentence) or CONDITIONAL_CUE_RE.search(sentence):
            score += 1
        if any(term in lower for term in ("figure", "table", "tbl")):
            score -= 4

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    for raw_sentence in meaningful_sentences_from_text(text):
        consider(raw_sentence)

    if best_rank[0] < 6:
        for raw_line in strip_paragraph_heading(text).splitlines():
            candidate = clean_sentence_candidate(raw_line)
            if not candidate or RUNNING_HEADER_RE.match(candidate) or is_tableish_line(candidate):
                continue
            consider(candidate)

    if best_rank[0] < 6 or not best_sentence:
        return None
    return _sentence_with_period(best_sentence)


def _sentence_with_period(sentence: str) -> str:
    sentence = normalise_ws(sentence)
    if not sentence:
        return sentence
    if sentence.endswith((".", "!", "?")):
        return sentence
    return f"{sentence}."


def select_conditional_rule_sentence(text: str) -> Optional[str]:
    best_rank = (-999, 0)
    best_sentence = None

    def consider(raw_sentence: str) -> None:
        nonlocal best_rank, best_sentence
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            return
        if is_fragmentary_sentence(sentence) or is_bare_reference_sentence(sentence):
            return
        if is_overloaded_procedure_sentence(sentence):
            return

        first_alpha = next((char for char in sentence if char.isalpha()), "")
        if first_alpha and first_alpha.islower():
            return

        words = sentence.split()
        if len(words) < 5 or len(words) > 40:
            return

        lower = sentence.lower()
        score = 0
        if DEICTIC_LEAD_RE.match(sentence) and not lower.startswith("this order"):
            score -= 4
        if CONDITIONAL_START_RE.match(sentence):
            score += 5
        if CONDITIONAL_CUE_RE.search(sentence):
            score += 4
        if any(verb in lower for verb in ACTION_VERBS):
            score += 3
        if AUXILIARY_VERB_RE.search(sentence) or IMPERATIVE_START_RE.match(sentence):
            score += 1
        if "figure" in lower or "fig " in lower:
            score -= 2

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    for raw_sentence in meaningful_sentences_from_text(text):
        consider(raw_sentence)

    if best_rank[0] < 6:
        for raw_line in strip_paragraph_heading(text).splitlines():
            candidate = clean_sentence_candidate(raw_line)
            if not candidate or RUNNING_HEADER_RE.match(candidate) or is_tableish_line(candidate):
                continue
            consider(candidate)

    if best_rank[0] < 6 or not best_sentence:
        return None
    return _sentence_with_period(best_sentence)


def select_title_definition_sentence(para_title: str, text: str) -> Optional[str]:
    sentences = meaningful_sentences_from_text(text)

    title_tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z]{3,}", para_title)
        if token.upper() not in STOPWORDS
    ]

    raw_matches: list[str] = []
    current = ""
    for raw_line in strip_paragraph_heading(text).translate(QUOTE_TRANSLATION).splitlines():
        candidate = clean_sentence_candidate(raw_line)
        if not candidate or RUNNING_HEADER_RE.match(candidate):
            continue

        if current:
            current = normalise_ws(f"{current} {candidate}")
            if current.endswith((".", "!", "?")):
                if TERM_DEFINITION_PATTERN_RE.match(current):
                    raw_matches.append(current)
                current = ""
            continue

        if is_tableish_line(candidate):
            continue
        first_alpha = next((char for char in candidate if char.isalpha()), "")
        if not first_alpha or not first_alpha.isupper():
            continue
        if TERM_DEFINITION_LEAD_RE.match(candidate):
            current = candidate
            if current.endswith((".", "!", "?")):
                if TERM_DEFINITION_PATTERN_RE.match(current):
                    raw_matches.append(current)
                current = ""

    if current and TERM_DEFINITION_PATTERN_RE.match(current):
        raw_matches.append(current)

    best_rank = (-999, 0)
    best_sentence = None
    for raw_sentence in raw_matches + sentences:
        sentence = strip_urls_and_contacts(raw_sentence)
        if not sentence:
            continue

        lower = sentence.lower()
        if CONDITIONAL_START_RE.match(sentence):
            continue
        has_definition_pattern = bool(TERM_DEFINITION_PATTERN_RE.match(sentence))
        has_title_match = any(re.search(rf"\b{re.escape(token)}\b", lower) for token in title_tokens)
        has_definition_cue = bool(DEFINITION_CUE_RE.search(sentence))
        has_term_lead = lower.startswith("the term ")
        if not (has_definition_pattern or has_definition_cue or has_term_lead):
            continue

        words = sentence.split()
        if len(words) < 5 or len(words) > 34:
            continue

        score = 0
        if has_title_match:
            score += 2
        if has_definition_pattern:
            score += 4
        if has_definition_cue:
            score += 6
        if has_term_lead:
            score += 3
        if IMPERATIVE_START_RE.match(sentence):
            score -= 6
        elif any(verb in lower for verb in ACTION_VERBS):
            score -= 3

        rank = (score, -len(words))
        if rank > best_rank:
            best_rank = rank
            best_sentence = sentence

    if best_rank[0] < 6 or not best_sentence:
        return None
    return _sentence_with_period(best_sentence)


def joined_blocks(blocks: list[dict], *types: str) -> str:
    wanted = set(types)
    return "\n\n".join(
        strip_paragraph_heading(block.get("content", ""))
        for block in blocks
        if not wanted or block.get("block_type", "body") in wanted
    ).strip()


def meaningful_body_sentences(blocks: list[dict]) -> list[str]:
    text = joined_blocks(blocks, "body", "note", "exception", "interpretation")
    return meaningful_sentences_from_text(text)


def phraseology_lines_from_blocks(blocks: list[dict]) -> list[str]:
    text = joined_blocks(blocks, "phraseology", "example")
    return phraseology_lines_from_text(text)


def _normalize_phraseology_placeholder(content: str) -> str:
    clean = normalise_ws(content.replace("−", "-").replace("–", "-"))
    clean = clean.strip(" .,:;\"'")
    if not clean:
        return ""
    if re.search(
        r"\b(?:see|note|example|figure|fig|table|tbl|para|section|chapter)\b",
        clean,
        re.IGNORECASE,
    ):
        return ""

    clean = re.sub(r"\band/or\b", "or", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[^A-Za-z0-9 /-]", "", clean)
    clean = normalise_ws(clean)
    if not clean:
        return ""
    if len(clean.split()) > 3 and "/" not in clean:
        return ""
    return clean


def phraseology_lines_from_text(text: str) -> list[str]:
    lines: list[str] = []
    cleaned = text.replace("−", "-").replace("–", "-").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(
        r"([A-Za-z0-9/-]+)\(([A-Za-z0-9/-]+)\)",
        lambda match: f"{match.group(1)}{match.group(2)}",
        cleaned,
    )
    cleaned = re.sub(
        r"\(([^)]*)\)",
        lambda match: (
            f' {_normalize_phraseology_placeholder(match.group(1))} '
            if _normalize_phraseology_placeholder(match.group(1))
            else " "
        ),
        cleaned,
    )
    cleaned = re.sub(
        r"\[([^\]]*)\]",
        lambda match: (
            f' {_normalize_phraseology_placeholder(match.group(1))} '
            if _normalize_phraseology_placeholder(match.group(1))
            else " "
        ),
        cleaned,
    )
    logical_lines: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        current = normalise_ws(current).strip()
        if current:
            logical_lines.append(current)
        current = ""

    for raw_line in cleaned.splitlines():
        line = re.sub(r"\s/[A-Z]+$", "", raw_line.strip())
        line = normalise_ws(line)
        if not line:
            flush_current()
            continue
        if line.lower() == "or":
            flush_current()
            continue
        if line.startswith("-"):
            flush_current()
            continue
        if re.match(r"^(?:\d+\.|[a-z]\.)\s+", line, re.IGNORECASE):
            flush_current()
            continue
        if BLOCK_LABEL_RE.match(line):
            flush_current()
            continue
        if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", line):
            flush_current()
            continue
        if re.search(r"\b\d+(?:[-−]\d+)+\b", line):
            flush_current()
            continue
        if RUNNING_HEADER_RE.match(line):
            flush_current()
            continue

        if current and not re.search(r"[.!?]\"?$", current):
            current = f"{current} {line}"
        else:
            flush_current()
            current = line

        if re.search(r"[.!?]\"?$", line):
            flush_current()

    flush_current()

    for raw_line in logical_lines:
        line = raw_line.rstrip(".,;:")
        line = re.sub(r"[^A-Za-z0-9 /-]", "", line).upper()
        line = normalise_ws(line)
        words = line.split()
        if len(words) < 3 or len(words) > 16:
            continue
        if re.search(r"\b(FAA|ORDER|JO|PARA|P/CG)\b", line):
            continue
        if any(len(word) == 1 for word in words):
            continue
        if line not in lines:
            lines.append(line)
    return lines


def extract_steps_from_text(text: str, max_steps: int = 5) -> list[str]:
    if not text:
        return []
    cleaned_text = strip_paragraph_heading(text)
    items = re.findall(
        r"(?:^|\n)\s*([a-e]|\d+)\.\s+(.+?)(?=\n\s*(?:[a-e]|\d+)\.\s+|$)",
        cleaned_text,
        re.DOTALL | re.IGNORECASE,
    )
    steps: list[str] = []
    for _, step_text in items[:max_steps]:
        clean = clean_sentence_candidate(step_text)
        clean = normalise_ws(clean).strip()
        if not clean:
            continue
        if len(clean) > 140:
            continue
        if len(clean.split()) < 3 or len(clean.split()) > 18:
            continue
        if clean.endswith(":"):
            continue
        if PAIR_SKIP_RE.search(clean) or LOW_SIGNAL_SENTENCE_RE.match(clean):
            continue
        if RUNNING_HEADER_RE.search(clean):
            continue
        if re.search(r"\b(?:the following|as follows|one of the following)\b", clean, re.IGNORECASE):
            continue
        if re.search(r"\bJO\s*7110\.65|\b\d{1,2}/\d{1,2}/\d{2,4}\b", clean, re.IGNORECASE):
            continue
        if is_tableish_line(clean):
            continue
        steps.append(clean)
    return steps


def extract_list_items(text: str, max_items: int = 6) -> list[str]:
    if not text:
        return []

    items = re.findall(
        r"(?:^|\n)\s*([a-z]|\d+)\.\s+(.+?)(?=\n\s*(?:[a-z]|\d+)\.\s+|$)",
        strip_paragraph_heading(text),
        re.DOTALL | re.IGNORECASE,
    )
    extracted: list[str] = []
    seen: set[str] = set()

    for _, item_text in items:
        clean = clean_sentence_candidate(item_text)
        clean = normalise_ws(clean).strip(" .;:")
        if not clean:
            continue
        if len(clean.split()) > 60 or len(clean) > 400:
            continue
        if PAIR_SKIP_RE.search(clean) or LOW_SIGNAL_SENTENCE_RE.match(clean):
            continue

        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        extracted.append(clean)
        if len(extracted) >= max_items:
            break

    return extracted


def extract_reference_entries(text: str, max_entries: int = 6) -> list[dict]:
    if not text:
        return []

    cleaned = strip_paragraph_heading(text).translate(QUOTE_TRANSLATION)
    lines = [normalise_ws(raw_line) for raw_line in cleaned.splitlines()]
    entries: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line or RUNNING_HEADER_RE.match(line) or "ORDER JO" not in line.upper():
            idx += 1
            continue
        if not line.endswith((".", ";")):
            next_idx = idx + 1
            combined = line
            while next_idx < len(lines):
                continuation = lines[next_idx]
                if (
                    not continuation
                    or RUNNING_HEADER_RE.match(continuation)
                    or re.fullmatch(r"\d+\.", continuation)
                    or LEADING_MARKER_RE.match(continuation)
                    or BLOCK_LABEL_RE.match(continuation)
                    or re.fullmatch(r"[A-Z][A-Z0-9 /-]{4,}", continuation)
                ):
                    break
                combined = normalise_ws(f"{combined} {continuation}")
                next_idx += 1
                if combined.endswith((".", ";")):
                    break
            line = combined

        for match in REFERENCE_ORDER_RE.finditer(line):
            order = normalise_ws(match.group(1))
            remainder = line[match.end():].strip(" ,.")
            locator = ""
            title = ""

            para_match = REFERENCE_PARA_RE.search(remainder)
            chapter_section_match = REFERENCE_CHAPTER_SECTION_RE.search(remainder)
            locator_match = para_match or chapter_section_match

            if locator_match:
                locator = normalise_ws(locator_match.group(1).replace("−", "-"))
                before = remainder[:locator_match.start()].strip(" ,.")
                after = remainder[locator_match.end():].strip(" ,.")
                title = before or after
            else:
                title = remainder

            if not locator and not title:
                title = ""

            key = (order.lower(), locator.lower(), title.lower())
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "order": order,
                    "locator": locator,
                    "title": title.rstrip("."),
                }
            )
            if len(entries) >= max_entries:
                return entries
        idx += 1

    return entries


def extract_example_snippets(text: str, max_examples: int = 8) -> list[str]:
    if not text:
        return []

    cleaned = strip_paragraph_heading(text).translate(QUOTE_TRANSLATION)
    snippets: list[str] = []
    seen: set[str] = set()

    def push(candidate: str) -> None:
        candidate = normalise_ws(candidate).strip()
        if not candidate:
            return
        token_count = len(re.findall(r"[A-Za-z0-9]+", candidate))
        if token_count < 2 or token_count > 22:
            return
        if re.fullmatch(r"[A-Z]\.[A-Z]\.?", candidate):
            return
        key = candidate.lower()
        if key in seen:
            return
        seen.add(key)
        snippets.append(candidate)

    for raw_line in cleaned.splitlines():
        line = normalise_ws(raw_line)
        if not line or RUNNING_HEADER_RE.match(line) or re.fullmatch(r"\d+\.", line):
            continue

        labelled = EXAMPLE_LABEL_RE.findall(line)
        if labelled:
            for label, quoted in labelled:
                push(f'{label.strip()}: "{normalise_ws(quoted)}"')
                if len(snippets) >= max_examples:
                    return snippets
            continue

        if not re.match(r'^[“"]', line):
            continue

        for quoted in QUOTE_CONTENT_RE.findall(line):
            push(f'"{normalise_ws(quoted)}"')
            if len(snippets) >= max_examples:
                return snippets

    return snippets


def extract_step_visibility_table_rows(text: str, max_rows: int = 5) -> list[dict]:
    if not text:
        return []

    cleaned = strip_paragraph_heading(text).translate(QUOTE_TRANSLATION)
    cleaned = cleaned.replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
    lines = cleaned.splitlines()

    in_table = False
    saw_day_night = False
    current_row = ""
    raw_rows: list[str] = []

    def flush_row() -> None:
        nonlocal current_row
        current_row = current_row.rstrip()
        if current_row:
            raw_rows.append(current_row)
        current_row = ""

    for raw_line in lines:
        line = raw_line.rstrip()
        candidate = line.strip()
        upper = candidate.upper()

        if not candidate:
            continue
        if "TBL " in upper or upper.startswith("TABLE "):
            in_table = True
            flush_row()
            continue
        if not in_table:
            continue
        if BLOCK_LABEL_RE.match(candidate) or upper.startswith(("REFERENCE", "NOTE", "EXAMPLE")):
            flush_row()
            break
        if "DAY" in upper and "NIGHT" in upper:
            saw_day_night = True
            continue
        if re.search(r"\b(?:STEP|VISIBILITY|EXAMPLES|OPERATING|AIRCRAFT|MAGNETIC)\b", upper):
            continue
        if re.match(r"^\s*\d+\s+", line):
            flush_row()
            current_row = line
            continue
        if current_row and raw_line[:1].isspace():
            current_row = f"{current_row}  {candidate}"
            continue
        if current_row:
            flush_row()

    flush_row()

    if not saw_day_night:
        return []

    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_row in raw_rows:
        row_text = raw_row.replace("−", "-")
        match = re.match(r"^\s*(\d+)\s+(.+?)\s{2,}(.+?)\s*$", row_text)
        if not match:
            continue

        step, day_text, night_text = match.groups()
        day = normalise_ws(day_text).strip(" .;:")
        night = normalise_ws(night_text).strip(" .;:")
        if not day or not night:
            continue
        if len(day.split()) > 12 or len(night.split()) > 12:
            continue

        key = (step, day.lower(), night.lower())
        if key in seen:
            continue
        seen.add(key)
        rows.append({"step": step, "day": day, "night": night})
        if len(rows) >= max_rows:
            break

    return rows


def extract_term_pairs_from_text(text: str, max_pairs: int = 5) -> list[tuple[str, str]]:
    def normalise_pair_term(term: str) -> str:
        cleaned = normalise_ws(term.translate(QUOTE_TRANSLATION))
        cleaned = cleaned.strip(" .,:;-")
        cleaned = re.sub(r'^(?:the word|the term)\s+', "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace('"', "")
        return cleaned

    def normalise_pair_definition(definition: str) -> str:
        cleaned = normalise_ws(definition.translate(QUOTE_TRANSLATION))
        cleaned = cleaned.strip(" .,:;-")
        return cleaned

    def is_valid_pair(term: str, definition: str) -> bool:
        if not term or not definition:
            return False
        if term.lower() == definition.lower():
            return False
        if len(term) < 2 or len(term) > 60:
            return False
        if len(definition) < 3 or len(definition) > 160:
            return False
        if len(term.split()) > 8 or len(definition.split()) > 24:
            return False
        if PAIR_SKIP_RE.search(term) or PAIR_SKIP_RE.search(definition):
            return False
        if re.search(r"https?://", definition):
            return False
        if term.lower().startswith(("as used in", "some common", "the following")):
            return False
        if term.endswith(":"):
            return False
        return True

    def candidate_lines(source_text: str) -> list[str]:
        cleaned = strip_paragraph_heading(source_text).translate(QUOTE_TRANSLATION)
        cleaned = cleaned.replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
        logical_lines: list[str] = []
        current = ""

        for raw_line in cleaned.splitlines():
            line = normalise_ws(raw_line)
            if not line or PAIR_SKIP_RE.search(line):
                continue
            if BLOCK_LABEL_RE.match(line):
                continue

            if PAIR_LEADING_MARKER_RE.match(line):
                if current:
                    logical_lines.append(current)
                current = PAIR_LEADING_MARKER_RE.sub("", line)
                continue

            if current:
                current = f"{current} {line}"
            else:
                current = line

        if current:
            logical_lines.append(current)
        return logical_lines

    candidates: list[tuple[str, str]] = []
    for line in candidate_lines(text):
        line = line.strip()

        definition_match = re.match(
            r"^(.+?)\s+(?:means|shall mean|is defined as|refers to|indicates?)\s+(.+?)(?:\.\s*)?$",
            line,
            re.IGNORECASE,
        )
        if definition_match:
            term = normalise_pair_term(definition_match.group(1))
            definition = normalise_pair_definition(definition_match.group(2))
            if is_valid_pair(term, definition):
                candidates.append((term, definition))
            continue

        equals_match = re.match(r"^(.+?)\s*=\s*(.+?)$", line)
        if equals_match:
            term = normalise_pair_term(equals_match.group(1))
            definition = normalise_pair_definition(equals_match.group(2))
            if is_valid_pair(term, definition):
                candidates.append((term, definition))

    seen_terms: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for term, definition in candidates:
        key = term.lower()
        if key in seen_terms:
            continue
        seen_terms.add(key)
        pairs.append((term, definition))
        if len(pairs) >= max_pairs:
            break
    return pairs


def make_word_bank(target_phrase: str, seed_key: str) -> tuple[list[str], list[int]]:
    rng = rng_for(seed_key, target_phrase)
    words = target_phrase.split()
    distractors = [word for word in ATC_DISTRACTOR_POOL if word not in words]
    rng.shuffle(distractors)
    distractors = distractors[: min(4, max(2, len(words) // 2 or 1))]
    entries = [
        {"kind": "target", "source_idx": idx, "word": word}
        for idx, word in enumerate(words)
    ]
    entries.extend(
        {"kind": "distractor", "source_idx": idx, "word": word}
        for idx, word in enumerate(distractors)
    )
    rng.shuffle(entries)
    word_bank = [entry["word"] for entry in entries]
    correct_sequence = [0] * len(words)
    for bank_idx, entry in enumerate(entries):
        if entry["kind"] == "target":
            correct_sequence[entry["source_idx"]] = bank_idx
    return word_bank, correct_sequence


def has_numbered_steps(text: str) -> bool:
    return bool(re.search(r"(?:^|\n)\s*(?:\d+\.|[a-z]\.|step\s+\d)", text, re.IGNORECASE))


def split_token_parts(token: str) -> tuple[str, str, str]:
    match = re.match(r"^([^A-Za-z0-9]*)([A-Za-z0-9/-]+)([^A-Za-z0-9]*)$", token)
    if not match:
        return "", token, ""
    return match.group(1), match.group(2), match.group(3)


def is_contextual_spot_token(token: str) -> bool:
    _, core, _ = split_token_parts(token)
    upper_core = core.upper()
    return upper_core.isdigit() or upper_core in SPOT_THE_ERROR_CONTEXTUAL_TOKENS


def match_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original.istitle():
        return replacement.title()
    if original.islower():
        return replacement.lower()
    return replacement


def replace_phrase_once(text: str, source: str, replacement: str) -> Optional[str]:
    pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return None
    original = match.group(0)
    return pattern.sub(match_case(original, replacement), text, count=1)


def mutate_token(
    token: str,
    rng: random.Random,
    allow_generic: bool = True,
) -> Optional[str]:
    prefix, core, suffix = split_token_parts(token)
    upper_core = core.upper()
    if not core:
        return None

    replacement = TOKEN_MUTATIONS.get(upper_core)
    if not replacement and core.isdigit():
        replacement = str(int(core) + 1)
    if allow_generic and not replacement and upper_core.isalpha() and len(upper_core) > 2:
        choices = [word for word in ATC_DISTRACTOR_POOL if word != upper_core]
        replacement = rng.choice(choices) if choices else None
    if not replacement:
        return None

    return f"{prefix}{match_case(core, replacement)}{suffix}"


def build_statement_variants(
    text: str,
    seed_key: str,
    max_variants: int = 6,
) -> list[str]:
    variants: list[str] = []
    seen = {normalise_ws(text).lower()}

    def add(candidate: Optional[str]) -> None:
        if not candidate:
            return
        cleaned = normalise_ws(candidate)
        if (
            not cleaned
            or cleaned.lower() in seen
            or any(pattern.search(cleaned) for pattern in LOW_QUALITY_VARIANT_PATTERNS)
        ):
            return
        seen.add(cleaned.lower())
        variants.append(cleaned)

    for source, replacement in STATEMENT_REPLACEMENTS:
        add(replace_phrase_once(text, source, replacement))
        if len(variants) >= max_variants:
            return variants[:max_variants]

    negation_patterns = [
        (r"\bis\b", "is not"),
        (r"\bare\b", "are not"),
        (r"\bmust\b", "must not"),
        (r"\bshould\b", "should not"),
        (r"\bmay\b", "may not"),
    ]
    for pattern, replacement in negation_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            original = match.group(0)
            candidate = re.sub(
                pattern,
                match_case(original, replacement),
                text,
                count=1,
                flags=re.IGNORECASE,
            )
            add(candidate)
            if len(variants) >= max_variants:
                return variants[:max_variants]

    token_rng = rng_for(seed_key, text, "statement_tokens")
    tokens = text.split()
    indexes = list(range(len(tokens)))
    token_rng.shuffle(indexes)
    for idx in indexes:
        mutated = mutate_token(tokens[idx], token_rng, allow_generic=False)
        if not mutated or mutated == tokens[idx]:
            continue
        candidate_tokens = tokens[:]
        candidate_tokens[idx] = mutated
        add(" ".join(candidate_tokens))
        if len(variants) >= max_variants:
            return variants[:max_variants]

    for match in re.finditer(r"\b\d{1,4}\b", text):
        original = match.group(0)
        value = int(original)
        replacements: list[str] = []
        if value > 1:
            replacements.append(str(value - 1))
        replacements.append(str(value + 1))
        for replacement in replacements:
            add(f"{text[:match.start()]}{replacement}{text[match.end():]}")
            if len(variants) >= max_variants:
                return variants[:max_variants]

    add(replace_phrase_once(text, "and", "or"))
    add(replace_phrase_once(text, "or", "and"))
    return variants[:max_variants]


def mutate_phrase_line(
    line: str,
    seed_key: str,
    allow_generic: bool = False,
) -> Optional[dict]:
    rng = rng_for(seed_key, line)
    tokens = line.split()
    candidate_indexes = []

    for idx, token in enumerate(tokens):
        _, core, _ = split_token_parts(token)
        if not core or len(core) <= 2:
            continue
        if is_contextual_spot_token(token):
            continue
        candidate_indexes.append(idx)

    rng.shuffle(candidate_indexes)
    for idx in candidate_indexes:
        mutated = mutate_token(tokens[idx], rng, allow_generic=allow_generic)
        if not mutated or mutated == tokens[idx]:
            continue
        display_tokens = tokens[:]
        display_tokens[idx] = mutated
        _, correct_core, _ = split_token_parts(tokens[idx])
        _, wrong_core, _ = split_token_parts(mutated)
        if not wrong_core or wrong_core.upper() == correct_core.upper():
            continue
        if sum(
            1
            for token in display_tokens
            if split_token_parts(token)[1].upper() == wrong_core.upper()
        ) != 1:
            continue
        return {
            "tokens": display_tokens,
            "error_index": idx,
            "correct_token": correct_core.upper(),
            "wrong_token": wrong_core.upper(),
            "display_text": " ".join(display_tokens),
        }
    return None


def score_phraseology_line(line: str, purpose: str = "general") -> int:
    upper = line.upper()
    words = upper.split()
    score = 0

    if 4 <= len(words) <= 12:
        score += 3
    elif len(words) <= 3:
        score -= 2
    elif len(words) > 16:
        score -= 2

    if re.search(r"\d", upper):
        score += 1

    score += sum(1 for phrase in PHRASEOLOGY_PRIORITY_PHRASES if phrase in upper)

    if any(upper.startswith(prefix) for prefix in PHRASEOLOGY_FRAGMENT_PREFIXES):
        score -= 5

    if purpose == "error":
        if upper.startswith("AIRCRAFT "):
            score -= 4
        if upper.startswith("ATTENTION ALL AIRCRAFT"):
            score -= 2
        if not any(phrase in upper for phrase in PHRASEOLOGY_PRIORITY_PHRASES):
            score -= 3

    if purpose == "readback":
        if any(upper.startswith(prefix) for prefix in READBACK_DISALLOWED_PREFIXES):
            score -= 8
        if any(phrase in upper for phrase in READBACK_DISALLOWED_PHRASES):
            score -= 8
        if not any(phrase in upper for phrase in PHRASEOLOGY_PRIORITY_PHRASES):
            score -= 4

    return score


def pick_best_phraseology_line(
    lines: list[str],
    seed_key: str,
    purpose: str = "general",
) -> Optional[str]:
    scored = [(score_phraseology_line(line, purpose), line) for line in lines]
    if not scored:
        return None

    threshold = 4 if purpose == "readback" else 2
    viable = [(score, line) for score, line in scored if score >= threshold]
    if not viable:
        return None

    best_score = max(score for score, _ in viable)
    finalists = sorted(line for score, line in viable if score == best_score)
    if len(finalists) == 1:
        return finalists[0]
    return rng_for(seed_key, purpose, *finalists).choice(finalists)


def _fill_blank_candidate_score(tokens: list[str], idx: int) -> int:
    _, core, _ = split_token_parts(tokens[idx])
    upper = core.upper()
    if not core or upper in STOPWORDS or len(core) <= 2:
        return -999

    score = 0
    if upper in PHRASEOLOGY_FILL_PRIORITY_TOKENS:
        score += 8
    if upper in ATC_DISTRACTOR_POOL:
        score += 4
    if upper in TOKEN_MUTATIONS:
        score += 4
    if upper in LOW_VALUE_PHRASEOLOGY_BLANK_TOKENS:
        score -= 6
    if re.fullmatch(r"\d+", core):
        score -= 4
    if "/" in core:
        score -= 5
    if idx == 0 and upper not in PHRASEOLOGY_FILL_PRIORITY_TOKENS:
        score -= 2
    if idx == len(tokens) - 1:
        score -= 2
    if len(core) >= 5:
        score += 2
    if len(core) >= 8:
        score += 1
    return score


def build_fill_blank(line: str, seed_key: str) -> Optional[dict]:
    rng = rng_for(seed_key, line)
    tokens = line.split()
    scored_candidates = [
        (_fill_blank_candidate_score(tokens, idx), idx)
        for idx in range(len(tokens))
    ]
    candidate_indexes = [idx for score, idx in scored_candidates if score > 0]
    if not candidate_indexes:
        return None

    best_score = max(score for score, _ in scored_candidates)
    if best_score <= 0:
        return None

    top_choices = [
        idx for score, idx in sorted(scored_candidates, key=lambda item: (-item[0], item[1]))
        if score == best_score
    ]
    answer_index = rng.choice(top_choices)
    _, answer_core, _ = split_token_parts(tokens[answer_index])

    blanked_tokens = tokens[:]
    blanked_tokens[answer_index] = "_____"
    return {
        "masked_text": " ".join(blanked_tokens),
        "answer": answer_core.upper(),
        "full_phrase": line,
    }


def build_readback_choices(clearance: str, seed_key: str) -> Optional[dict]:
    mutated = mutate_phrase_line(clearance, seed_key)
    callsign = "UNITED 234"
    correct = f"{callsign}, {clearance}"
    wrongs = [
        clearance,
        f"ROGER, {callsign}",
    ]
    if mutated:
        wrongs.append(f"{callsign}, {mutated['display_text']}")

    tokens = clearance.split()
    if len(tokens) >= 4:
        wrongs.append(f"{callsign}, {' '.join(tokens[:-1])}")

    for fallback in [
        f"{callsign}, STANDBY",
        f"{callsign}, SAY AGAIN",
    ]:
        if fallback not in wrongs and fallback != correct:
            wrongs.append(fallback)
        if len(wrongs) >= 3:
            break

    if len(wrongs) < 3:
        return None

    rng = rng_for(seed_key, clearance, "readback")
    choices = [
        {"text": correct, "is_correct": True},
        *({"text": wrong, "is_correct": False} for wrong in wrongs[:3]),
    ]
    rng.shuffle(choices)
    return {"clearance": clearance, "choices": choices}


def mutate_statement(text: str, seed_key: str) -> Optional[str]:
    rng = rng_for(seed_key, text)
    tokens = text.split()
    indexes = list(range(len(tokens)))
    rng.shuffle(indexes)
    for idx in indexes:
        prefix, core, suffix = split_token_parts(tokens[idx])
        upper_core = core.upper()
        replacement = None
        if upper_core in TOKEN_MUTATIONS:
            replacement = TOKEN_MUTATIONS[upper_core]
        elif core.isdigit():
            replacement = str(int(core) + 1)

        if replacement and replacement != upper_core:
            changed = tokens[:]
            changed[idx] = f"{prefix}{match_case(core, replacement)}{suffix}"
            return " ".join(changed)
    return None


def build_mc_distractors(
    correct_text: str,
    seed_key: str,
    allow_generic: bool = True,
) -> list[str]:
    rng = rng_for(seed_key, correct_text, "mc")
    distractors: list[str] = []
    for variant in build_statement_variants(correct_text, seed_key):
        if variant != correct_text and variant not in distractors:
            distractors.append(variant)
        if len(distractors) >= 3:
            return distractors[:3]

    if not allow_generic:
        return distractors[:3]

    generic = GENERIC_MC_DISTRACTORS[:]
    rng.shuffle(generic)
    for option in generic:
        if option != correct_text and option not in distractors:
            distractors.append(option)
        if len(distractors) >= 3:
            break
    return distractors[:3]


def is_generic_action_distractor(text: str) -> bool:
    clean = normalise_ws(text).rstrip(".")
    return any(clean.startswith(prefix) for prefix in GENERIC_DECISION_ERROR_PREFIXES)


def _normalize_action_distractor(candidate: Optional[str]) -> Optional[str]:
    if not candidate:
        return None

    clean = normalise_ws(candidate).strip(" \"'")
    clean = re.sub(r"^(?:that|you to)\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^to\s+", "", clean, flags=re.IGNORECASE)
    clean = clean.rstrip(" ,;:")
    if not clean:
        return None

    lower = clean.lower()
    if len(clean.split()) > 18:
        for separator in (" because ", " since ", " so that "):
            if separator in lower:
                clean = clean[: lower.index(separator)].rstrip(" ,;:")
                break
        if not clean:
            return None

    clean = sentence_case_lead(clean)
    if len(clean.split()) < 4 or len(clean.split()) > 34:
        return None
    return _sentence_with_period(clean)


def _extract_situation_wrong_actions(situation_text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for match in ACTION_ALT_RE.finditer(normalise_ws(situation_text)):
        candidate = _normalize_action_distractor(match.group(1))
        if not candidate:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return candidates


def _mutate_action_marker_reference(text: str, seed_key: str) -> Optional[str]:
    for match in re.finditer(r'"([A-Z])"', text):
        start_context = text[max(0, match.start() - 24): match.start()].lower()
        end_context = text[match.end(): match.end() + 24].lower()
        if not any(keyword in start_context for keyword in ("letter", "symbol")) and "suffix" not in end_context:
            continue
        marker = match.group(1)
        replacements = [item for item in ACTION_MARKER_POOL if item != marker.upper()]
        if not replacements:
            return None
        replacement = rng_for(seed_key, text, "action_marker").choice(replacements)
        return f"{text[:match.start(1)]}{replacement}{text[match.end(1):]}"
    return None


def _build_action_specific_distractors(
    correct_text: str,
    situation_text: str,
    seed_key: str,
) -> list[str]:
    distractors: list[str] = []
    seen = {normalise_ws(correct_text).lower()}

    def add(candidate: Optional[str]) -> None:
        if not candidate:
            return
        normalized = _normalize_action_distractor(candidate)
        if not normalized or is_generic_action_distractor(normalized):
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        distractors.append(normalized)

    for candidate in _extract_situation_wrong_actions(situation_text):
        add(candidate)

    for source, replacement in ACTION_SPECIFIC_REPLACEMENTS:
        add(replace_phrase_once(correct_text, source, replacement))

    add(_mutate_action_marker_reference(correct_text, seed_key))

    clean = correct_text.rstrip(".")
    if IMPERATIVE_START_RE.match(clean):
        verb, _, remainder = clean.partition(" ")
        if remainder:
            add(f"Do not {verb.lower()} {remainder}")
            if re.search(r"\badvisory information\b", remainder, re.IGNORECASE):
                add(f"{verb} {remainder} only after a pilot specifically requests it")
                add(f"Treat the activity as informational only and omit the advisory")
    elif clean.lower().startswith("do not "):
        positive = clean[7:].strip()
        if positive:
            add(f"{positive[:1].upper()}{positive[1:]}")
    elif re.match(r"^To .+ use:", clean, re.IGNORECASE):
        add(re.sub(r"\buse:", "do not use:", clean, count=1, flags=re.IGNORECASE))

    ensure_match = re.match(
        r"^Ensure (?:that )?(.+?) is notified of (.+)$",
        clean,
        re.IGNORECASE,
    )
    if ensure_match:
        add(f"Do not notify {ensure_match.group(1)} of {ensure_match.group(2)}")

    aware_match = re.match(
        r"^Ensure (?:that )?(.+?) is aware of (.+)$",
        clean,
        re.IGNORECASE,
    )
    if aware_match:
        add(f"Keep {aware_match.group(1)} unaware of {aware_match.group(2)}")

    if correct_text.lower().startswith("identify ") and ":" in correct_text:
        add(re.sub(r":\s*", ": Do not identify them as ", correct_text, count=1))

    return distractors


def build_action_choices(
    correct_text: str,
    seed_key: str,
    situation_text: str = "",
) -> list[dict]:
    rng = rng_for(seed_key, correct_text, "action")
    wrongs: list[str] = []

    for candidate in _build_action_specific_distractors(correct_text, situation_text, f"{seed_key}:specific"):
        if candidate != correct_text and candidate not in wrongs:
            wrongs.append(candidate)

    for variant in build_statement_variants(correct_text, f"{seed_key}:action", max_variants=6):
        sentence = variant if variant.endswith(".") else f"{variant}."
        if sentence != correct_text and sentence not in wrongs:
            wrongs.append(sentence)

    generic_wrongs = GENERIC_DECISION_ERRORS[:]
    rng.shuffle(generic_wrongs)
    for generic in generic_wrongs:
        if generic != correct_text and generic not in wrongs:
            wrongs.append(generic)

    deduped_wrongs: list[str] = []
    for wrong in wrongs:
        if wrong != correct_text and wrong not in deduped_wrongs:
            deduped_wrongs.append(wrong)
    choices = [{"text": correct_text, "is_correct": True}]
    choices.extend({"text": wrong, "is_correct": False} for wrong in deduped_wrongs[:3])
    rng.shuffle(choices)
    return choices


def is_operational_context(para_title: str, sentence: str) -> bool:
    title_upper = para_title.upper()
    combined = f"{para_title} {sentence}".upper()
    if any(term in title_upper for term in ADMIN_TITLE_TERMS):
        return False
    return any(keyword in combined for keyword in OPERATIONAL_KEYWORDS)


def select_action_sentence(para_title: str, sentences: list[str]) -> Optional[str]:
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        upper = sentence.upper()
        lower = sentence.lower()
        if is_overloaded_procedure_sentence(sentence):
            continue
        if len(sentence.split()) > 34:
            continue
        if re.search(r"\b(?:may|can|could|is|are)\s+be\s+used\b", lower):
            continue
        score = 0

        if "http" in lower or "faa.gov" in lower:
            score -= 10
        if re.search(r"\bmust\b|\bshall\b|\bshould\b", lower):
            score += 4
        if any(verb in lower for verb in ACTION_VERBS):
            score += 3
        if any(keyword in upper for keyword in OPERATIONAL_KEYWORDS):
            score += 2
        if len(sentence.split()) < 6:
            score -= 2
        scored.append((score, sentence))

    if not scored:
        return None

    best_score, best_sentence = max(scored, key=lambda item: (item[0], len(item[1])))
    if best_score < 3:
        return None
    if not is_operational_context(para_title, best_sentence):
        return None
    return best_sentence


def build_situation_prompt(para_id: str, para_title: str, sentence: str) -> str:
    combined = f"{para_title} {sentence}".upper()
    frame = "You are handling traffic and need to decide the correct controller action."
    for keywords, candidate_frame in SCENARIO_FRAMES:
        if any(keyword in combined for keyword in keywords):
            frame = candidate_frame
            break

    condition = normalise_ws(sentence).rstrip(".")
    return f"{frame} The applicable condition is: {condition}."
