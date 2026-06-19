/**
 * useCurriculum.js
 * ================
 * SQLite-in-WASM data layer for the ATC learning platform.
 *
 * Uses a vendored sql.js build (SQLite compiled to WebAssembly) to query
 * curriculum.db directly in the browser — no backend or external CDN required.
 *
 * curriculum.db is a static file served alongside the app.
 * Crown/mastery progress is kept in localStorage.
 * Editorial QA review state is persisted through the local backend so the
 * notes/statuses live outside the browser and can be versioned with the repo.
 *
 * Usage:
 *   const { db, loading, error, getChapters, startSession, ... } = useCurriculum();
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { assetUrl, isStaticDeploy } from "./assetPaths";
import { buildFaaSourceRef, buildJo7360SourceRef } from "./faaSource";

const SQLJS_SCRIPT_URL = assetUrl("vendor/sql.js/sql-wasm.js");
const SQLJS_WASM_URL   = assetUrl("vendor/sql.js/sql-wasm.wasm");
const MASTERY_KEY    = "atc_mastery_v1";
const FOCUS_LIST_KEY = "atc_focus_list_v1";
const CONCEPT_MEMORY_KEY = "atc_concept_memory_v1";
const MISTAKE_QUEUE_KEY = "atc_mistake_queue_v1";
const LEGACY_REVIEW_KEY = "atc_review_v1";
const LEGACY_REVIEW_MIGRATED_KEY = "atc_review_backend_migrated_v1";
const REVIEW_EXPORT_VERSION = 1;
const REVIEW_STATUSES = new Set(["pending", "approved", "weak", "replace"]);
const DB_PATH_CANDIDATES = [
  window.__ATC_DB_PATH__,
  assetUrl("curriculum.db"),
  "./curriculum.db",
].filter(Boolean);

function isPerfProbeEnabled() {
  try {
    return new URLSearchParams(window.location.search).has("perf");
  } catch {
    return false;
  }
}

function compactSql(sql) {
  return String(sql || "").replace(/\s+/g, " ").trim().slice(0, 160);
}
const REVIEW_API_BASE_CANDIDATES = [
  window.__ATC_API_BASE__,
  import.meta.env.VITE_ATC_API_BASE,
  ...(isStaticDeploy() ? [] : [
    window.location.origin,
    "http://127.0.0.1:8000",
    "http://localhost:8000",
  ]),
].filter(Boolean);
const CHAPTER_TITLES = {
  1: "General",
  2: "General Control",
  3: "Airport Traffic Control - Terminal",
  4: "IFR",
  5: "Radar",
  6: "Nonradar",
  7: "Visual",
  8: "Offshore/Oceanic Procedures",
  9: "Special Flights",
  10: "Emergencies",
  11: "Traffic Management Procedures",
  12: "Canadian Airspace Procedures",
  13: "Decision Support Tools",
  14: "Data Link Communications",
};

const PUBLISHED_FLASHCARD_FILTER = "f.generation_src IN ('curated', 'deepseek', 'question_agent')";
const PUBLISHED_FLASHCARD_FILTER_NO_ALIAS = "generation_src IN ('curated', 'deepseek', 'question_agent')";
const SECTION_LABELS = {
  "2-1":"General","2-2":"Flight Data","2-3":"Strip Marking","2-4":"Radar",
  "2-5":"ATS Routes","2-6":"Weather","2-7":"Preflight","2-8":"Flight Plans",
  "2-9":"Position Reports","2-10":"Nonradar",
  "3-1":"General Terminal","3-2":"Light Signals","3-3":"Local Control",
  "3-4":"Ground Control","3-5":"Clearance Delivery","3-6":"ATIS",
  "3-7":"Transfer of Control","3-8":"TRACON","3-9":"Departure",
  "3-10":"Arrival","3-11":"Approach Control","3-12":"Radar Approach",
  "4-1":"General IFR","4-2":"Clearances","4-3":"Altitude Assignment",
  "4-4":"Route Assignment","4-5":"Speed Adjustments","4-6":"Holding",
  "4-7":"Approach","4-8":"Approach Clearances",
  "5-1":"General Radar",
  "5-2":"Beacon/ADS-B Systems",
  "5-3":"Radar Identification",
  "5-4":"Transfer of Radar Identification",
  "5-5":"Radar Separation",
  "5-6":"Vectoring",
  "5-7":"Speed Adjustment",
  "5-8":"Radar Departures",
  "5-9":"Radar Arrivals",
  "5-10":"Radar Approaches - Terminal",
  "5-11":"Surveillance Approaches - Terminal",
  "5-12":"PAR Approaches - Terminal",
  "5-13":"Automation - En Route",
  "5-14":"STARS - Terminal Automation",
};
const REVIEW_ACTIVITY_WEIGHTS = {
  capability_check: 4,
  table_lookup: 4,
  visual_interpretation: 4,
  term_definition_check: 3,
  minima_rule_check: 3,
  document_control_check: 3,
  reference_check: 2,
  phraseology_builder: 2,
  readback_check: 2,
  scope_check: 1,
  requirement_check: 1,
  conditional_rule_check: 1,
  directive_check: 1,
  example_check: 1,
  match_pairs: 1,
};
const REVIEW_ACTIVITY_REASONS = {
  capability_check: "system capability logic",
  table_lookup: "table-driven content",
  visual_interpretation: "figure/diagram interpretation",
  term_definition_check: "definition language",
  minima_rule_check: "numeric/minima rule",
  document_control_check: "admin/document wording",
  reference_check: "cross-reference citation",
  phraseology_builder: "phraseology reconstruction",
  readback_check: "read-back fidelity",
  scope_check: "scope/responsibility wording",
  requirement_check: "controller requirement wording",
  conditional_rule_check: "conditional phrasing",
  directive_check: "directive phrasing",
  example_check: "example phrasing",
  match_pairs: "mapping exercise",
};
const PRACTICE_MODE_CONFIG = {
  diagnostic: {
    label: "Diagnostic",
    activityTypes: null,
    conceptIds: null,
  },
  weak_areas: {
    label: "Weak Areas",
    activityTypes: null,
    conceptIds: null,
  },
  tables_minima: {
    label: "Tables & Minima",
    activityTypes: ["table_lookup", "minima_rule_check"],
    conceptIds: ["tables-minima", "wake-turbulence", "radar-separation"],
  },
  phraseology: {
    label: "Phraseology",
    activityTypes: ["phraseology_builder", "readback_check", "spot_the_error", "example_check"],
    conceptIds: ["phraseology"],
  },
  scenarios: {
    label: "Scenario Judgment",
    activityTypes: ["situation_action", "conditional_rule_check", "capability_check", "requirement_check"],
    conceptIds: ["emergencies", "taxi-ground", "approach-clearance"],
  },
  visuals: {
    label: "Figures & Visuals",
    activityTypes: ["visual_interpretation"],
    conceptIds: ["runway-separation", "approach-clearance", "approach-vectors"],
  },
};
const SOURCE_ASSET_ACTIVITY_TYPES = new Set(["table_lookup", "visual_interpretation", "minima_rule_check"]);
const CONCEPT_RULES = [
  {
    id: "runway-separation",
    label: "Runway Separation",
    patterns: [/\brunway separation\b/i, /\bsame runway\b/i, /\bopposite direction\b/i, /\bsame direction operation\b/i, /\bintersecting runway\b/i],
    activityTypes: ["minima_rule_check", "visual_interpretation"],
  },
  {
    id: "wake-turbulence",
    label: "Wake Turbulence",
    patterns: [/\bwake\b/i, /\bsuper\b/i, /\bheavy\b/i, /\bcategory [a-i]\b/i],
    activityTypes: ["minima_rule_check", "table_lookup"],
  },
  {
    id: "approach-clearance",
    label: "Approach Clearance",
    patterns: [/\bapproach clearance\b/i, /\binstrument approach\b/i, /\bIAF\b/i, /\bintermediate fix\b/i, /\bprocedure turn\b/i, /\bRF leg\b/i],
    activityTypes: ["visual_interpretation", "phraseology_builder", "example_check"],
  },
  {
    id: "approach-vectors",
    label: "Approach Vectors",
    patterns: [/\bfinal approach course\b/i, /\bapproach gate\b/i, /\bintercept/i, /\bvector/i, /\bsimultaneous dependent approaches\b/i],
    activityTypes: ["table_lookup", "minima_rule_check", "situation_action"],
  },
  {
    id: "taxi-ground",
    label: "Taxi/Ground Movement",
    patterns: [/\btaxi\b/i, /\bground movement\b/i, /\bmovement area\b/i, /\bhold short\b/i, /\brunway crossing\b/i],
    activityTypes: ["phraseology_builder", "visual_interpretation"],
  },
  {
    id: "light-signals-lighting",
    label: "Light Signals/Lighting",
    patterns: [/\blight signal\b/i, /\brunway lights?\b/i, /\btaxiway lights?\b/i, /\bVASI\b/i, /\bPAPI\b/i, /\bMALSR\b/i, /\bODALS\b/i, /\bHIRL\b/i, /\bMIRL\b/i],
    activityTypes: ["table_lookup"],
  },
  {
    id: "strip-marking",
    label: "Strip Marking",
    patterns: [/\bflight progress strip\b/i, /\bstrip marking\b/i, /\bcontrol symbology\b/i, /\bhand-printed\b/i, /\bclearance abbreviations?\b/i],
    activityTypes: ["visual_interpretation", "table_lookup"],
  },
  {
    id: "phraseology",
    label: "Phraseology",
    patterns: [/\bphraseology\b/i, /\bapproved phraseology\b/i, /\bcontact\b/i, /\bcleared\b/i, /\bsay\b/i],
    activityTypes: ["phraseology_builder", "readback_check", "spot_the_error", "example_check"],
  },
  {
    id: "tables-minima",
    label: "Tables/Minima",
    patterns: [/\bTBL\b/i, /\btable\b/i, /\bminima\b/i, /\bdistance\b/i, /\baltitude assignment\b/i, /\bflight level\b/i],
    activityTypes: ["table_lookup", "minima_rule_check"],
  },
  {
    id: "emergencies",
    label: "Emergencies",
    patterns: [/\bemergency\b/i, /\bdistress\b/i, /\blost communications\b/i, /\bradio communications failure\b/i, /\balert\b/i],
    activityTypes: ["situation_action"],
  },
  {
    id: "radar-separation",
    label: "Radar Separation",
    patterns: [/\bradar separation\b/i, /\btarget\b/i, /\bradar identification\b/i, /\btrack separation\b/i, /\bradials?\b/i, /\bNAVAID\b/i],
    activityTypes: ["minima_rule_check", "table_lookup", "visual_interpretation"],
  },
  {
    id: "cpdlc",
    label: "CPDLC/Data Link",
    patterns: [/\bCPDLC\b/i, /\bdata link\b/i, /\buplink\b/i, /\bdownlink\b/i, /\bmessage set\b/i, /\bfree text\b/i],
    activityTypes: ["table_lookup", "situation_action"],
  },
];
const HIGH_VALUE_TITLE_RE = /\b(?:RUNWAY|SEPARATION|WAKE|EMERGENCY|EMERGENCIES|CLEARANCE|ALTITUDE|APPROACH|LANDING|TAKEOFF|RADAR|NONRADAR|VISUAL|IFR|TRAFFIC|DESCENT|CLIMB|HOLDING)\b/i;
const REVIEW_STATUS_META = {
  pending:  { label: "Pending",  color: "#8c9c91" },
  approved: { label: "Approved", color: "#39c36f" },
  weak:     { label: "Weak",     color: "#f0a500" },
  replace:  { label: "Replace",  color: "#f43f5e" },
};
const PUBLISH_MODE_META = {
  all: {
    label: "All content",
    description: "No publish gating. All learner-facing paragraphs remain visible.",
  },
  hide_flagged: {
    label: "Hide flagged",
    description: "Learner-facing surfaces hide paragraphs marked weak or replace.",
  },
  approved_only: {
    label: "Approved only",
    description: "Learner-facing surfaces show only paragraphs explicitly marked approved.",
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// MASTERY STORE  (localStorage)
// ─────────────────────────────────────────────────────────────────────────────

function loadMastery() {
  try {
    return JSON.parse(localStorage.getItem(MASTERY_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveMastery(state) {
  try {
    localStorage.setItem(MASTERY_KEY, JSON.stringify(state));
  } catch {}
}

function loadFocusList() {
  try {
    const raw = JSON.parse(localStorage.getItem(FOCUS_LIST_KEY) || "[]");
    return Array.isArray(raw)
      ? [...new Set(raw.map((item) => String(item || "").trim()).filter(Boolean))]
      : [];
  } catch {
    return [];
  }
}

function saveFocusList(state) {
  try {
    localStorage.setItem(FOCUS_LIST_KEY, JSON.stringify([...new Set(state)]));
  } catch {}
}

function loadConceptMemory() {
  try {
    const raw = JSON.parse(localStorage.getItem(CONCEPT_MEMORY_KEY) || "{}");
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
    const normalized = {};
    for (const [conceptId, record] of Object.entries(raw)) {
      if (!record || typeof record !== "object" || Array.isArray(record)) continue;
      normalized[conceptId] = {
        misses: Math.max(0, Number(record.misses || 0)),
        recoveries: Math.max(0, Number(record.recoveries || 0)),
        lastMissAt: typeof record.lastMissAt === "string" ? record.lastMissAt : null,
        lastSeenAt: typeof record.lastSeenAt === "string" ? record.lastSeenAt : null,
        paraIds: Array.isArray(record.paraIds)
          ? [...new Set(record.paraIds.map((item) => String(item || "").trim()).filter(Boolean))]
          : [],
      };
    }
    return normalized;
  } catch {
    return {};
  }
}

function saveConceptMemory(state) {
  try {
    localStorage.setItem(CONCEPT_MEMORY_KEY, JSON.stringify(state));
  } catch {}
}

function loadMistakeQueue() {
  try {
    const raw = JSON.parse(localStorage.getItem(MISTAKE_QUEUE_KEY) || "{}");
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
    const normalized = {};
    for (const [activityId, record] of Object.entries(raw)) {
      if (!record || typeof record !== "object" || Array.isArray(record)) continue;
      const id = String(record.activityId || activityId || "").trim();
      const paraId = String(record.paraId || "").trim();
      if (!id || !paraId) continue;
      normalized[id] = {
        activityId: id,
        paraId,
        activityType: String(record.activityType || "").trim(),
        misses: Math.max(1, Number(record.misses || 1)),
        lastMissAt: typeof record.lastMissAt === "string" ? record.lastMissAt : null,
        concepts: Array.isArray(record.concepts) ? record.concepts : [],
      };
    }
    return normalized;
  } catch {
    return {};
  }
}

function saveMistakeQueue(state) {
  try {
    localStorage.setItem(MISTAKE_QUEUE_KEY, JSON.stringify(state));
  } catch {}
}

function loadLegacyReviewState() {
  try {
    return normalizeReviewState(JSON.parse(localStorage.getItem(LEGACY_REVIEW_KEY) || "{}"));
  } catch {
    return {};
  }
}

function saveLocalReviewState(state) {
  try {
    localStorage.setItem(LEGACY_REVIEW_KEY, JSON.stringify(normalizeReviewState(state)));
  } catch {}
}

function markLegacyReviewMigrated() {
  try {
    localStorage.setItem(LEGACY_REVIEW_MIGRATED_KEY, "1");
  } catch {}
}

function hasLegacyReviewMigrationFlag() {
  try {
    return localStorage.getItem(LEGACY_REVIEW_MIGRATED_KEY) === "1";
  } catch {
    return false;
  }
}

async function fetchDatabaseBinary() {
  const attempts = [];
  for (const path of DB_PATH_CANDIDATES) {
    try {
      const resp = await fetch(path, { cache: "no-store" });
      if (!resp.ok) {
        attempts.push(`${path} (${resp.status})`);
        continue;
      }
      return await resp.arrayBuffer();
    } catch (err) {
      attempts.push(`${path} (${err.message})`);
    }
  }
  throw new Error(`Failed to load curriculum.db from: ${attempts.join(", ")}`);
}

async function parseApiError(resp) {
  try {
    const payload = await resp.json();
    return payload?.detail || payload?.message || `${resp.status} ${resp.statusText}`;
  } catch {
    return `${resp.status} ${resp.statusText}`;
  }
}

function uniq(values) {
  return [...new Set(values.filter(Boolean))];
}

async function requestReviewApi(path, options = {}, knownBaseRef = null) {
  const candidates = uniq([knownBaseRef?.current, ...REVIEW_API_BASE_CANDIDATES]);
  let lastError = null;

  for (const base of candidates) {
    const url = `${String(base).replace(/\/$/, "")}/api/review${path}`;
    try {
      const resp = await fetch(url, {
        ...options,
        headers: {
          Accept: "application/json",
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...(options.headers || {}),
        },
      });

      if (resp.status === 404) {
        lastError = new Error(`${url} returned 404`);
        continue;
      }
      if (!resp.ok) {
        lastError = new Error(await parseApiError(resp));
        continue;
      }

      knownBaseRef.current = base;
      return await resp.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw new Error(
    `Review API unavailable. Start the backend or set VITE_ATC_API_BASE. ${lastError ? `Last error: ${lastError.message}` : ""}`.trim(),
  );
}

/**
 * Crown level 0–4 from per-paragraph mastery state.
 *
 * state shape: {
 *   total: number,                 // total activities completed
 *   type_counts: { [type]: n },    // per-type completion count
 *   type_scores: { [type]: avg },  // per-type rolling average score
 *   attempts: [{ activityType, score, correct, at }],
 * }
 */
function recentAttempts(state, limit = 8) {
  return Array.isArray(state?.attempts) ? state.attempts.slice(-limit) : [];
}

function recentAccuracy(state, limit = 8) {
  const attempts = recentAttempts(state, limit);
  if (!attempts.length) return null;
  return attempts.reduce((sum, attempt) => sum + Number(attempt.score || 0), 0) / attempts.length;
}

function applyMasteryResult(state, activityType, score, at = new Date().toISOString()) {
  const current = state || { total: 0, type_counts: {}, type_scores: {}, attempts: [] };
  const prevCount = current.type_counts?.[activityType] || 0;
  const prevAvg = current.type_scores?.[activityType] ?? score;
  const newAvg = prevCount === 0
    ? score
    : (prevAvg * prevCount + score) / (prevCount + 1);
  const attempts = [
    ...recentAttempts(current, 19),
    {
      activityType,
      score: Math.round(Number(score || 0) * 1000) / 1000,
      correct: Number(score || 0) >= 0.8,
      at,
    },
  ];

  return {
    ...current,
    total: Number(current.total || 0) + 1,
    type_counts: { ...(current.type_counts || {}), [activityType]: prevCount + 1 },
    type_scores: { ...(current.type_scores || {}), [activityType]: Math.round(newAvg * 1000) / 1000 },
    attempts,
    lastSeenAt: at,
  };
}

function calcCrown(state) {
  if (!state || state.total === 0) return 0;
  const types = Object.keys(state.type_counts || {});
  const scores = Object.values(state.type_scores || {});
  const avgScore = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const recent = recentAccuracy(state, 8);
  const recentFloor = recent ?? avgScore;
  const recentMisses = recentAttempts(state, 4).filter((attempt) => Number(attempt.score || 0) < 0.8).length;

  // Gold/proficient thresholds match the activity-type diversity the
  // generated curriculum can actually provide today, with recent performance
  // preventing stale accumulated success from hiding current weak areas.
  if (state.total >= 12 && types.length >= 4 && avgScore >= 0.90 && recentFloor >= 0.88 && recentMisses === 0) return 4;
  if (state.total >= 7  && types.length >= 3 && avgScore >= 0.84 && recentFloor >= 0.80 && recentMisses <= 1) return 3;
  if (state.total >= 3  && types.length >= 2 && avgScore >= 0.70 && recentFloor >= 0.65) return 2;
  if (state.total >= 1  && avgScore >= 0.50) return 1;
  return 0;
}

function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function defaultReviewRecord() {
  return { status: "pending", notes: "", updatedAt: null };
}

function normalizeReviewState(raw) {
  const source = raw && typeof raw === "object" && !Array.isArray(raw)
    ? (raw.reviews && typeof raw.reviews === "object" && !Array.isArray(raw.reviews) ? raw.reviews : raw)
    : {};

  const normalized = {};
  for (const [paraId, record] of Object.entries(source)) {
    if (!record || typeof record !== "object" || Array.isArray(record)) continue;
    const status = REVIEW_STATUSES.has(record.status) ? record.status : "pending";
    const notes = typeof record.notes === "string" ? record.notes : "";
    const updatedAt = typeof record.updatedAt === "string" ? record.updatedAt : null;
    normalized[paraId] = { status, notes, updatedAt };
  }
  return normalized;
}

function computeReviewPriority(item) {
  let score = 0;
  const reasons = [];
  const addReason = (text) => {
    if (reasons.length < 4 && !reasons.includes(text)) reasons.push(text);
  };

  if (HIGH_VALUE_TITLE_RE.test(item.title)) {
    score += 4;
    addReason("operationally critical topic");
  }
  if (item.blockTypes.includes("reference")) {
    score += 2;
    addReason("source references present");
  }
  if (item.blockTypes.includes("phraseology")) {
    score += 2;
    addReason("phraseology source text");
  }
  if (item.blockTypes.includes("example")) {
    score += 1;
    addReason("example-driven paragraph");
  }
  if (item.activityCount >= 8) {
    score += 2;
    addReason("dense activity bundle");
  } else if (item.activityCount >= 5) {
    score += 1;
  }
  if (item.questionCount >= 4) {
    score += 1;
    addReason("large quiz surface");
  }

  for (const type of item.activityTypes) {
    const weight = REVIEW_ACTIVITY_WEIGHTS[type] || 0;
    if (weight) {
      score += weight;
      addReason(REVIEW_ACTIVITY_REASONS[type] || type);
    }
  }

  const band = score >= 10 ? "high" : score >= 6 ? "medium" : "baseline";
  return { score, band, reasons };
}

function humanizeActivityType(type) {
  return String(type || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function compactText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function safeJsonParse(value, fallback = null) {
  try {
    return JSON.parse(value || "null") ?? fallback;
  } catch {
    return fallback;
  }
}

function blockSearchText(contentJson) {
  try {
    const blocks = Array.isArray(contentJson)
      ? contentJson
      : JSON.parse(contentJson || "[]");
    return compactText(
      blocks
        .filter((block) => block && typeof block === "object")
        .map((block) => block.content || "")
        .join(" "),
    );
  } catch {
    return "";
  }
}

function conceptLabel(conceptId) {
  return CONCEPT_RULES.find((rule) => rule.id === conceptId)?.label || humanizeActivityType(conceptId);
}

function conceptTagsForText({ title = "", text = "", activityType = "" } = {}) {
  const haystack = `${title} ${text}`;
  const tags = CONCEPT_RULES
    .filter((rule) => (
      rule.patterns.some((pattern) => pattern.test(haystack))
      || rule.activityTypes.includes(activityType)
    ))
    .map((rule) => ({ id: rule.id, label: rule.label }));

  if (!tags.length && activityType) {
    return [{ id: `mechanic-${activityType}`, label: humanizeActivityType(activityType) }];
  }

  return tags
    .filter((tag, index, arr) => arr.findIndex((item) => item.id === tag.id) === index)
    .slice(0, 4);
}

function conceptIssueScore(record = {}) {
  const misses = Number(record.misses || 0);
  const recoveries = Number(record.recoveries || 0);
  const unresolved = Math.max(0, misses - recoveries);
  const lastMissMs = record.lastMissAt ? Date.parse(record.lastMissAt) : 0;
  const recencyBoost = lastMissMs
    ? Math.max(0, 4 - ((Date.now() - lastMissMs) / (1000 * 60 * 60 * 24 * 7)))
    : 0;
  return Math.round((unresolved * 5 + misses * 1.2 + recencyBoost) * 10) / 10;
}

function daysSinceIso(value) {
  if (!value) return null;
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return null;
  return Math.max(0, (Date.now() - time) / (1000 * 60 * 60 * 24));
}

function reviewIntervalDays(crown) {
  if (crown >= 4) return 14;
  if (crown >= 3) return 7;
  if (crown >= 2) return 3;
  return 1;
}

function dueReviewProfile(state = {}) {
  const total = Number(state.total || 0);
  if (!total) return null;
  const crown = calcCrown(state);
  const recent = recentAccuracy(state);
  const daysSince = daysSinceIso(state.lastSeenAt);
  const interval = reviewIntervalDays(crown);
  const noDateDue = daysSince === null && total > 0;
  const ageDue = daysSince !== null && daysSince >= interval;
  const accuracyDue = recent !== null && recent < 0.85;
  if (!noDateDue && !ageDue && !accuracyDue) return null;

  const urgency = (accuracyDue ? 8 : 0)
    + (noDateDue ? 3 : 0)
    + (daysSince !== null ? Math.min(8, daysSince / Math.max(interval, 1) * 4) : 0)
    + Math.max(0, 4 - crown);
  const reason = accuracyDue
    ? "recent accuracy"
    : noDateDue
      ? "older progress"
      : `${Math.floor(daysSince)}d since review`;

  return {
    crown,
    recentScore: recent === null ? null : Math.round(recent * 100),
    daysSince: daysSince === null ? null : Math.round(daysSince * 10) / 10,
    interval,
    urgency: Math.round(urgency * 10) / 10,
    reason,
  };
}

function averageScoreForState(state) {
  const scores = Object.values(state?.type_scores || {}).filter((value) => Number.isFinite(Number(value)));
  if (!scores.length) return null;
  return scores.reduce((sum, value) => sum + Number(value), 0) / scores.length;
}

function computePracticeProfile(item, state = {}, options = {}) {
  const activityTypes = item.activityTypes || [];
  const typeCounts = state.type_counts || {};
  const typeScores = state.type_scores || {};
  const total = Number(state.total || 0);
  const crown = calcCrown(state);
  const avgScore = averageScoreForState(state);
  const contentWeight = Number(item.activityCount || 0) + Number(item.flashcardCount || 0) + Number(item.questionCount || 0);
  const unpracticedTypes = activityTypes.filter((type) => !typeCounts[type]);
  const weakTypes = Object.entries(typeScores)
    .filter(([, score]) => Number(score) < 0.82)
    .map(([type]) => type);

  const reasons = [];
  const addReason = (reason) => {
    if (reasons.length < 4 && reason && !reasons.includes(reason)) reasons.push(reason);
  };

  let score = Math.max(0, 4 - crown) * 3;
  if (total === 0) {
    score = 5 + Math.min(contentWeight, 8) * 0.35;
    addReason("not started");
  } else {
    if (avgScore !== null && avgScore < 0.7) {
      score += 6;
      addReason("low recent accuracy");
    } else if (avgScore !== null && avgScore < 0.85) {
      score += 3;
      addReason("accuracy needs reinforcement");
    }
    if (weakTypes.length) {
      score += Math.min(weakTypes.length, 3) * 3;
      addReason(`weak ${humanizeActivityType(weakTypes[0]).toLowerCase()}`);
    }
    if (unpracticedTypes.length) {
      score += Math.min(unpracticedTypes.length, 4);
      addReason(`unpracticed ${humanizeActivityType(unpracticedTypes[0]).toLowerCase()}`);
    }
  }

  if (options.isFocused) {
    score += 3;
    addReason("saved focus item");
  }
  if (contentWeight >= 14) {
    score += 2;
    addReason("large practice surface");
  } else if (contentWeight >= 8) {
    score += 1;
  }
  if (!reasons.length) addReason(crown >= 4 ? "maintenance" : "continue practice");

  const band = score >= 14 ? "needs-work" : score >= 9 ? "developing" : "steady";
  return {
    score: Math.round(score * 10) / 10,
    band,
    reasons,
    averageScore: avgScore === null ? null : Math.round(avgScore * 100),
    weakTypes,
    unpracticedTypes,
    total,
  };
}

function compareParagraphOrder(a, b) {
  return Number(a.chapter || 0) - Number(b.chapter || 0)
    || Number(a.section || 0) - Number(b.section || 0)
    || String(a.para_id || "").localeCompare(String(b.para_id || ""), undefined, { numeric: true });
}

function normalizePublishMode(value) {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, "_");

  if (normalized === "approved") return "approved_only";
  if (normalized === "flagged" || normalized === "soft") return "hide_flagged";
  if (normalized === "open") return "all";
  return PUBLISH_MODE_META[normalized] ? normalized : "hide_flagged";
}

function readPublishMode() {
  try {
    const params = new URLSearchParams(window.location.search);
    const queryMode = params.get("publish");
    if (queryMode) return normalizePublishMode(queryMode);
  } catch {}

  return normalizePublishMode(
    window.__ATC_PUBLISH_MODE__
    || import.meta.env.VITE_ATC_PUBLISH_MODE
    || "hide_flagged",
  );
}

function reviewStatusForParagraph(reviewState, paraId) {
  return reviewState?.[paraId]?.status || "pending";
}

function shouldPublishParagraph(paraId, reviewState, publishMode) {
  if (publishMode === "all") return true;

  const status = reviewStatusForParagraph(reviewState, paraId);
  if (publishMode === "approved_only") {
    return status === "approved";
  }
  return status !== "weak" && status !== "replace";
}

function withSourceRef(item, paraId, page, options = {}) {
  return {
    ...item,
    ...(buildFaaSourceRef(paraId, page, options) || {}),
  };
}

function normalizeSourceAssetLabel(value) {
  return String(value || "")
    .toUpperCase()
    .replace(/\s+/g, " ")
    .trim();
}

function sourceAssetLabelsFromContent(content) {
  const values = [
    content?.source_label,
    content?.source_ref,
    content?.table_ref,
    content?.figure_ref,
    content?.visual_ref,
    content?.image_asset,
    content?.question_text,
    content?.prompt,
    content?.instruction,
    content?.task,
  ];
  const labels = new Set();
  for (const value of values) {
    if (!value) continue;
    const text = Array.isArray(value) || typeof value === "object"
      ? JSON.stringify(value)
      : String(value);
    for (const match of text.matchAll(/\b(?:TBL|FIG)\s+\d{1,2}-\d{1,2}-\d{1,2}\b/gi)) {
      labels.add(normalizeSourceAssetLabel(match[0]));
    }
  }
  return labels;
}

// ─────────────────────────────────────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────────────────────────────────────

export default function useCurriculum() {
  const [dbReady, setDbReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [mastery, setMastery] = useState(loadMastery);
  const [focusList, setFocusList] = useState(loadFocusList);
  const [conceptMemory, setConceptMemory] = useState(loadConceptMemory);
  const [mistakeQueue, setMistakeQueue] = useState(loadMistakeQueue);
  const [reviewState, setReviewState] = useState({});
  const [reviewPersistence, setReviewPersistence] = useState({
    mode: "loading",
    apiBase: null,
    storagePath: null,
    updatedAt: null,
    error: null,
  });
  const publishMode = readPublishMode();

  const sqlRef = useRef(null);   // SQL.Database instance
  const reviewApiBaseRef = useRef(null);
  const sourceAssetsRef = useRef(null);

  // ── Load sql.js and curriculum.db ─────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        // 1. Load sql.js script
        await new Promise((resolve, reject) => {
          if (window.initSqlJs) return resolve();
          const s = document.createElement("script");
          s.src = SQLJS_SCRIPT_URL;
          s.onload = resolve;
          s.onerror = reject;
          document.head.appendChild(s);
        });

        // 2. Initialise sql.js with WASM
        const SQL = await window.initSqlJs({ locateFile: () => SQLJS_WASM_URL });

        // 3. Fetch curriculum.db as binary
        const buf  = await fetchDatabaseBinary();
        const db   = new SQL.Database(new Uint8Array(buf));

        if (!cancelled) {
          sqlRef.current = db;
          setDbReady(true);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadPersistedReviewState() {
      if (isStaticDeploy()) {
        const localReviewState = loadLegacyReviewState();
        setReviewState(localReviewState);
        setReviewPersistence({
          mode: "local_static",
          apiBase: null,
          storagePath: null,
          updatedAt: null,
          error: null,
        });
        return;
      }

      try {
        let payload = await requestReviewApi("/state", {}, reviewApiBaseRef);
        const legacyReviewState = loadLegacyReviewState();
        if (
          payload.reviewCount === 0
          && !hasLegacyReviewMigrationFlag()
          && Object.keys(legacyReviewState).length > 0
        ) {
          payload = await requestReviewApi(
            "/state",
            {
              method: "PUT",
              body: JSON.stringify({
                type: "atc_review_state",
                version: REVIEW_EXPORT_VERSION,
                reviews: legacyReviewState,
              }),
            },
            reviewApiBaseRef,
          );
          markLegacyReviewMigrated();
        }
        if (cancelled) return;
        setReviewState(normalizeReviewState(payload));
        setReviewPersistence({
          mode: "backend",
          apiBase: reviewApiBaseRef.current,
          storagePath: payload.storagePath || null,
          updatedAt: payload.updatedAt || null,
          error: null,
        });
      } catch (err) {
        if (cancelled) return;
        setReviewState({});
        setReviewPersistence({
          mode: "unavailable",
          apiBase: null,
          storagePath: null,
          updatedAt: null,
          error: err.message,
        });
      }
    }

    loadPersistedReviewState();
    return () => { cancelled = true; };
  }, []);

  // ── Helper: run a query and return rows as plain objects ──────────────────
  const query = useCallback((sql, params = []) => {
    const db = sqlRef.current;
    if (!db) return [];
    const perf = isPerfProbeEnabled();
    const startedAt = perf ? performance.now() : 0;
    const stmt = db.prepare(sql);
    stmt.bind(params);
    const rows = [];
    while (stmt.step()) rows.push(stmt.getAsObject());
    stmt.free();
    if (perf) {
      const elapsed = performance.now() - startedAt;
      if (elapsed >= 2) {
        console.log(`[perf:sql] ${elapsed.toFixed(1)}ms · ${rows.length} rows · ${compactSql(sql)}`);
      }
    }
    return rows;
  }, []);

  const isParagraphPublished = useCallback(
    (paraId) => shouldPublishParagraph(paraId, reviewState, publishMode),
    [publishMode, reviewState],
  );

  const publishConfig = {
    mode: publishMode,
    ...PUBLISH_MODE_META[publishMode],
    reviewPersistenceMode: reviewPersistence.mode,
    reviewPersistenceError: reviewPersistence.error,
  };

  const getSourceAssetsIndex = useCallback(() => {
    if (sourceAssetsRef.current) return sourceAssetsRef.current;
    const rows = query(`
      SELECT id, para_id, chapter, section, asset_type, label, title,
             source_url, source_page_url, pdf_url, html, image_url, alt_text
      FROM source_assets
      ORDER BY chapter, section, para_id, asset_type, label
    `);
    const byPara = {};
    const byLabel = {};
    for (const row of rows) {
      const item = {
        id: row.id,
        para_id: row.para_id,
        chapter: Number(row.chapter || 0),
        section: Number(row.section || 0),
        asset_type: row.asset_type,
        label: row.label,
        title: row.title,
        source_url: row.source_url,
        source_page_url: row.source_page_url,
        pdf_url: row.pdf_url,
        html: row.html,
        image_url: row.image_url,
        alt_text: row.alt_text,
      };
      byPara[item.para_id] = byPara[item.para_id] || [];
      byPara[item.para_id].push(item);
      const label = normalizeSourceAssetLabel(item.label);
      byLabel[label] = byLabel[label] || [];
      byLabel[label].push(item);
    }
    sourceAssetsRef.current = { byPara, byLabel };
    return sourceAssetsRef.current;
  }, [query]);

  const sourceAssetsForContent = useCallback((paraId, content = {}, options = {}) => {
    if (!paraId) return [];
    const index = getSourceAssetsIndex();
    const assets = index.byPara[paraId] || [];
    const labels = sourceAssetLabelsFromContent(content);
    if (labels.size) {
      const matched = [];
      const seen = new Set();
      for (const label of labels) {
        for (const asset of index.byLabel[label] || []) {
          if (seen.has(asset.id)) continue;
          seen.add(asset.id);
          matched.push(asset);
        }
      }
      return matched;
    }
    if (!assets.length) return [];
    return options.includeAll ? assets.slice(0, options.limit || 8) : [];
  }, [getSourceAssetsIndex]);

  function computeSectionMastery(chapter, section) {
    const paraRows = query(
      "SELECT para_id FROM paragraphs WHERE chapter=? AND section=?",
      [chapter, section]
    );
    const paraIds = paraRows.map(r => r.para_id).filter(isParagraphPublished);
    const crowns  = paraIds.map(pid => calcCrown(mastery[pid]));
    const maxCrown = Math.max(0, ...crowns);
    const avgCrown = crowns.length
      ? crowns.reduce((a, b) => a + b, 0) / crowns.length
      : 0;
    return { maxCrown, avgCrown: Math.round(avgCrown * 10) / 10 };
  }

  // ── Chapter / Section structure ───────────────────────────────────────────
  const getChapters = useCallback(() => {
    const sectionTitleRows = query(`
      SELECT p.chapter, p.section, p.title
      FROM paragraphs p
      JOIN (
        SELECT chapter, section, MIN(para_id) AS first_para
        FROM paragraphs
        GROUP BY chapter, section
      ) firsts
      ON firsts.chapter = p.chapter
      AND firsts.section = p.section
      AND firsts.first_para = p.para_id
      ORDER BY p.chapter, p.section
    `);
    const sectionFallbacks = Object.fromEntries(
      sectionTitleRows.map(row => [`${row.chapter}-${row.section}`, row.title])
    );

    const rows = query(`
      SELECT p.chapter, p.section, p.para_id,
             COALESCE(a.activity_count, 0) AS acts,
             COALESCE(a.activity_types, '') AS activity_types,
             COALESCE(f.flashcard_count, 0) AS fcs,
             COALESCE(q.question_count, 0) AS qs
      FROM paragraphs p
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS activity_count, GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM activities
        GROUP BY para_id
      ) a ON a.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS flashcard_count
        FROM flashcards
        WHERE ${PUBLISHED_FLASHCARD_FILTER_NO_ALIAS}
        GROUP BY para_id
      ) f ON f.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS question_count
        FROM quiz_questions
        GROUP BY para_id
      ) q ON q.para_id = p.para_id
      ORDER BY p.chapter, p.section
    `);

    const chapters = {};
    for (const row of rows) {
      if (!isParagraphPublished(row.para_id)) continue;

      const chapter = Number(row.chapter);
      const section = Number(row.section);
      const acts = Number(row.acts || 0);
      const fcs = Number(row.fcs || 0);
      const qs = Number(row.qs || 0);
      const activityTypes = splitCsv(row.activity_types);
      if (!chapters[chapter]) {
        chapters[chapter] = {
          chapter,
          title: CHAPTER_TITLES[chapter] || `Chapter ${chapter}`,
          sections: [],
          totalParas: 0,
          totalActs: 0,
          totalCards: 0,
          totalQuestions: 0,
        };
      }
      const key = `${chapter}-${section}`;
      let sectionRef = chapters[chapter].sections.find((item) => item.key === key);
      if (!sectionRef) {
        const sectionMastery = computeSectionMastery(chapter, section);
        sectionRef = {
          key,
          chapter,
          section,
          label: SECTION_LABELS[key] || sectionFallbacks[key] || `Section ${section}`,
          paras: 0,
          acts: 0,
          fcs: 0,
          qs: 0,
          activityTypes: [],
          ...sectionMastery,
        };
        chapters[chapter].sections.push(sectionRef);
      }
      sectionRef.paras += 1;
      sectionRef.acts += acts;
      sectionRef.fcs += fcs;
      sectionRef.qs += qs;
      sectionRef.activityTypes = [
        ...new Set([...(sectionRef.activityTypes || []), ...activityTypes]),
      ];
      chapters[chapter].totalParas += 1;
      chapters[chapter].totalActs  += acts;
      chapters[chapter].totalCards += fcs;
      chapters[chapter].totalQuestions += qs;
    }
    return Object.values(chapters).filter((chapter) => chapter.sections.length > 0);
  }, [isParagraphPublished, mastery, query]);

  // ── Mastery helpers ───────────────────────────────────────────────────────
  const getSectionMastery = useCallback((chapter, section) => (
    computeSectionMastery(chapter, section)
  ), [isParagraphPublished, query, mastery]);

  const getParaMastery = useCallback((paraId) => {
    const state = mastery[paraId] || { total: 0, type_counts: {}, type_scores: {} };
    return { ...state, crown: calcCrown(state) };
  }, [mastery]);

  const isParagraphFocused = useCallback(
    (paraId) => focusList.includes(paraId),
    [focusList],
  );

  const toggleFocusedParagraph = useCallback((paraId) => {
    let nextState = [];
    setFocusList((prev) => {
      nextState = prev.includes(paraId)
        ? prev.filter((id) => id !== paraId)
        : [...prev, paraId];
      saveFocusList(nextState);
      return nextState;
    });
    return nextState;
  }, []);

  const clearFocusList = useCallback(() => {
    setFocusList([]);
    saveFocusList([]);
  }, []);

  // ── Curriculum review helpers ────────────────────────────────────────────
  const applyReviewPayload = useCallback((payload) => {
    const normalized = normalizeReviewState(payload);
    setReviewState(normalized);
    setReviewPersistence({
      mode: "backend",
      apiBase: reviewApiBaseRef.current,
      storagePath: payload?.storagePath || null,
      updatedAt: payload?.updatedAt || null,
      error: null,
    });
    return normalized;
  }, []);

  const saveParagraphReview = useCallback(async (paraId, patch) => {
    if (isStaticDeploy()) {
      const next = normalizeReviewState({
        ...reviewState,
        [paraId]: {
          ...defaultReviewRecord(),
          ...(reviewState[paraId] || {}),
          ...patch,
        },
      });
      setReviewState(next);
      saveLocalReviewState(next);
      setReviewPersistence((current) => ({
        ...current,
        mode: "local_static",
        updatedAt: new Date().toISOString(),
        error: null,
      }));
      return { reviews: next, reviewCount: Object.keys(next).length };
    }

    const payload = await requestReviewApi(
      `/paragraphs/${encodeURIComponent(paraId)}`,
      {
        method: "PUT",
        body: JSON.stringify({
          ...defaultReviewRecord(),
          ...(reviewState[paraId] || {}),
          ...patch,
        }),
      },
      reviewApiBaseRef,
    );
    applyReviewPayload(payload);
    return payload;
  }, [applyReviewPayload, reviewState]);

  const exportReviewState = useCallback(() => ({
    type: "atc_review_export",
    version: REVIEW_EXPORT_VERSION,
    exportedAt: new Date().toISOString(),
    reviewCount: Object.keys(reviewState).length,
    reviews: normalizeReviewState(reviewState),
  }), [reviewState]);

  const importReviewState = useCallback(async (payload, options = {}) => {
    const { mode = "merge" } = options;
    const incoming = normalizeReviewState(payload);
    const next = mode === "replace"
      ? incoming
      : { ...reviewState, ...incoming };
    if (isStaticDeploy()) {
      saveLocalReviewState(next);
      setReviewState(next);
      setReviewPersistence((current) => ({
        ...current,
        mode: "local_static",
        updatedAt: new Date().toISOString(),
        error: null,
      }));
      return {
        importedCount: Object.keys(incoming).length,
        totalCount: Object.keys(next).length,
        mode,
      };
    }

    const savedPayload = await requestReviewApi(
      "/state",
      {
        method: "PUT",
        body: JSON.stringify({
          type: "atc_review_state",
          version: REVIEW_EXPORT_VERSION,
          reviews: next,
        }),
      },
      reviewApiBaseRef,
    );
    applyReviewPayload(savedPayload);
    return {
      importedCount: Object.keys(incoming).length,
      totalCount: Object.keys(next).length,
      mode,
    };
  }, [applyReviewPayload, reviewState]);

  const clearReviewState = useCallback(async () => {
    if (isStaticDeploy()) {
      saveLocalReviewState({});
      setReviewState({});
      setReviewPersistence((current) => ({
        ...current,
        mode: "local_static",
        updatedAt: new Date().toISOString(),
        error: null,
      }));
      return;
    }

    const payload = await requestReviewApi(
      "/state",
      { method: "DELETE" },
      reviewApiBaseRef,
    );
    applyReviewPayload(payload);
  }, [applyReviewPayload]);

  const getReviewQueue = useCallback(() => {
    const rows = query(`
      SELECT p.para_id, p.chapter, p.section, p.title, p.page, p.content_json,
             COUNT(DISTINCT a.id) AS activity_count,
             COUNT(DISTINCT f.id) AS flashcard_count,
             COUNT(DISTINCT q.id) AS question_count,
             GROUP_CONCAT(DISTINCT a.activity_type) AS activity_types,
             GROUP_CONCAT(DISTINCT q.question_type) AS question_types
      FROM paragraphs p
      LEFT JOIN activities a ON a.para_id = p.para_id
      LEFT JOIN flashcards f ON f.para_id = p.para_id AND ${PUBLISHED_FLASHCARD_FILTER}
      LEFT JOIN quiz_questions q ON q.para_id = p.para_id
      GROUP BY p.para_id, p.chapter, p.section, p.title, p.page, p.content_json
      ORDER BY p.chapter, p.section, p.para_id
    `);

    const statusRank = { pending: 3, weak: 2, replace: 2, approved: 1 };

    return rows
      .map((row) => {
        const blocks = JSON.parse(row.content_json || "[]");
        const blockTypes = [...new Set(
          blocks.map((block) => (block.block_type || "body")).filter(Boolean)
        )];
        const activityTypes = splitCsv(row.activity_types);
        const questionTypes = splitCsv(row.question_types);
        const review = {
          ...defaultReviewRecord(),
          ...(reviewState[row.para_id] || {}),
        };
        const priority = computeReviewPriority({
          title: row.title,
          activityCount: Number(row.activity_count || 0),
          questionCount: Number(row.question_count || 0),
          blockTypes,
          activityTypes,
        });

        return {
          para_id: row.para_id,
          chapter: Number(row.chapter),
          section: Number(row.section),
          title: row.title,
          page: Number(row.page || 0),
          activityCount: Number(row.activity_count || 0),
          flashcardCount: Number(row.flashcard_count || 0),
          questionCount: Number(row.question_count || 0),
          activityTypes,
          questionTypes,
          blockTypes,
          review,
          priority,
          sectionLabel: SECTION_LABELS[`${row.chapter}-${row.section}`] || `Section ${row.section}`,
          chapterLabel: CHAPTER_TITLES[row.chapter] || `Chapter ${row.chapter}`,
          sortWeight: statusRank[review.status] || 0,
          ...(buildFaaSourceRef(row.para_id, row.page, { title: row.title, blocks }) || {}),
        };
      })
      .sort((a, b) => (
        b.sortWeight - a.sortWeight
        || b.priority.score - a.priority.score
        || a.chapter - b.chapter
        || a.section - b.section
        || a.para_id.localeCompare(b.para_id, undefined, { numeric: true })
      ));
  }, [query, reviewState]);

  const getParagraphAudit = useCallback((paraId) => {
    const para = query(`
      SELECT para_id, chapter, section, title, page, content_json
      FROM paragraphs
      WHERE para_id = ?
    `, [paraId])[0];

    if (!para) return null;

    const blocks = JSON.parse(para.content_json || "[]");

    const activities = query(`
      SELECT id, activity_type, difficulty, generation_src, content_json
      FROM activities
      WHERE para_id = ?
      ORDER BY activity_type, id
    `, [paraId]).map((row) => withSourceRef({
      id: row.id,
      activity_type: row.activity_type,
      difficulty: Number(row.difficulty || 0),
      generation_src: row.generation_src,
      content: JSON.parse(row.content_json || "{}"),
    }, para.para_id, para.page, { title: para.title, blocks }));

    const flashcards = query(`
      SELECT id, card_type, front, back, generation_src
      FROM flashcards
      WHERE para_id = ?
        AND ${PUBLISHED_FLASHCARD_FILTER_NO_ALIAS}
      ORDER BY card_type, front
    `, [paraId]).map((row) => withSourceRef({
      id: row.id,
      card_type: row.card_type,
      front: row.front,
      back: row.back,
      generation_src: row.generation_src,
    }, para.para_id, para.page, { title: para.title, blocks }));

    const questions = query(`
      SELECT id, question_type, question_text, explanation, difficulty, generation_src
      FROM quiz_questions
      WHERE para_id = ?
      ORDER BY question_type, id
    `, [paraId]).map((row) => withSourceRef({
      id: row.id,
      question_type: row.question_type,
      question_text: row.question_text,
      explanation: row.explanation,
      difficulty: Number(row.difficulty || 0),
      generation_src: row.generation_src,
      choices: query(`
        SELECT id, choice_text, is_correct, sort_order
        FROM question_choices
        WHERE question_id = ?
        ORDER BY sort_order, id
        `, [row.id]).map((choice) => ({
          id: choice.id,
          choice_text: choice.choice_text,
          is_correct: Number(choice.is_correct) === 1,
          sort_order: Number(choice.sort_order || 0),
        })),
    }, para.para_id, para.page, { title: para.title, blocks }));

    return {
      para_id: para.para_id,
      chapter: Number(para.chapter),
      section: Number(para.section),
      title: para.title,
      page: Number(para.page || 0),
      blocks,
      activities,
      flashcards,
      questions,
      review: {
        ...defaultReviewRecord(),
        ...(reviewState[paraId] || {}),
      },
      ...(buildFaaSourceRef(para.para_id, para.page, { title: para.title, blocks }) || {}),
    };
  }, [query, reviewState]);

  const mapActivityRows = useCallback((rows) => rows
    .filter((row) => isParagraphPublished(row.para_id))
    .map((r) => {
      const content = safeJsonParse(r.content_json, {});
      const sourceAssets = sourceAssetsForContent(r.para_id, content, {
        includeAll: SOURCE_ASSET_ACTIVITY_TYPES.has(r.activity_type),
        limit: 6,
      });
      return withSourceRef({
        id:            r.id,
        para_id:       r.para_id,
        para_title:    r.para_title,
        activity_type: r.activity_type,
        difficulty:    r.difficulty,
        content,
        source_assets: sourceAssets,
        concepts:      conceptTagsForText({
          title: r.para_title,
          text: blockSearchText(r.para_content_json),
          activityType: r.activity_type,
        }),
      }, r.para_id, r.page, {
        title: r.para_title,
        blocks: safeJsonParse(r.para_content_json, []),
      });
    }), [isParagraphPublished, sourceAssetsForContent]);

  const mapQuestionRows = useCallback((rows) => {
    const publishedRows = rows.filter((row) => isParagraphPublished(row.para_id));
    const questionIds = publishedRows.map((row) => row.id);
    const choicesByQuestion = {};
    if (questionIds.length) {
      const placeholders = questionIds.map(() => "?").join(",");
      for (const choice of query(`
        SELECT question_id, choice_text, is_correct, sort_order
        FROM question_choices
        WHERE question_id IN (${placeholders})
        ORDER BY question_id, sort_order, id
      `, questionIds)) {
        const key = String(choice.question_id);
        choicesByQuestion[key] = choicesByQuestion[key] || [];
        choicesByQuestion[key].push({
          text: choice.choice_text,
          is_correct: Number(choice.is_correct) === 1,
        });
      }
    }

    return publishedRows
      .map((r) => {
        const choices = choicesByQuestion[String(r.id)] || [];
        if (choices.length < 2) return null;
        const paraText = blockSearchText(r.para_content_json);
        const questionText = compactText(r.question_text);
        return withSourceRef({
          id: `q:${r.id}`,
          quiz_question_id: r.id,
          para_id: r.para_id,
          para_title: r.para_title,
          activity_type: "knowledge_check",
          difficulty: Number(r.difficulty || 0),
          content: {
            question_text: questionText,
            choices,
            explanation: r.explanation,
          },
          concepts: conceptTagsForText({
            title: r.para_title,
            text: `${paraText} ${questionText}`,
            activityType: "knowledge_check",
          }),
        }, r.para_id, r.page, {
          title: r.para_title,
          blocks: safeJsonParse(r.para_content_json, []),
        });
      })
      .filter(Boolean);
  }, [isParagraphPublished, query]);

  const questionRowsForParagraphs = useCallback((paraIds) => {
    const ids = [...new Set((paraIds || []).map((paraId) => String(paraId || "").trim()).filter(Boolean))];
    if (!ids.length) return [];
    const placeholders = ids.map(() => "?").join(",");
    return query(`
      SELECT q.id, q.para_id, p.title para_title, q.question_type,
             q.question_text, q.explanation, q.difficulty,
             p.page, p.content_json AS para_content_json,
             p.chapter, p.section
      FROM quiz_questions q
      JOIN paragraphs p ON q.para_id = p.para_id
      WHERE q.para_id IN (${placeholders})
      ORDER BY p.chapter, p.section, p.para_id, q.question_type, q.id
    `, ids);
  }, [query]);

  // ── Build a session for a section ─────────────────────────────────────────
  const buildSession = useCallback((chapter, section, count = null) => {
    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      WHERE p.chapter = ? AND p.section = ? AND a.is_verified = 0
      ORDER BY p.para_id, a.activity_type
    `, [chapter, section]);

    const questionRows = query(`
      SELECT q.id, q.para_id, p.title para_title, q.question_type,
             q.question_text, q.explanation, q.difficulty,
             p.page, p.content_json AS para_content_json,
             p.chapter, p.section
      FROM quiz_questions q
      JOIN paragraphs p ON q.para_id = p.para_id
      WHERE p.chapter = ? AND p.section = ?
      ORDER BY p.para_id, q.question_type, q.id
    `, [chapter, section]);

    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRows),
    ];

    return buildSessionOrder(activities, mastery, count, { mode: "section" });
  }, [mapActivityRows, mapQuestionRows, query, mastery]);

  // ── Session for a specific paragraph ──────────────────────────────────────
  const buildParaSession = useCallback((paraId) => {
    if (!isParagraphPublished(paraId)) return [];

    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      WHERE a.para_id = ?
    `, [paraId]);

    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRowsForParagraphs([paraId])),
    ];

    return buildSessionOrder(activities, mastery, null, { mode: "paragraph" });
  }, [isParagraphPublished, mapActivityRows, mapQuestionRows, mastery, query, questionRowsForParagraphs]);

  const getSectionParagraphs = useCallback((chapter, section) => {
    const rows = query(`
      SELECT p.para_id, p.title, p.page, p.content_json,
             COALESCE(a.activity_count, 0) AS activity_count,
             COALESCE(a.activity_types, '') AS activity_types,
             COALESCE(f.flashcard_count, 0) AS flashcard_count,
             COALESCE(q.question_count, 0) AS question_count
      FROM paragraphs p
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS activity_count, GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM activities
        GROUP BY para_id
      ) a ON a.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS flashcard_count
        FROM flashcards
        WHERE ${PUBLISHED_FLASHCARD_FILTER_NO_ALIAS}
        GROUP BY para_id
      ) f ON f.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS question_count
        FROM quiz_questions
        GROUP BY para_id
      ) q ON q.para_id = p.para_id
      WHERE p.chapter = ? AND p.section = ?
      ORDER BY p.para_id
    `, [chapter, section]);

    return rows
      .filter((row) => isParagraphPublished(row.para_id))
      .map((row) => {
        const masteryState = mastery[row.para_id] || { total: 0, type_counts: {}, type_scores: {} };
        const crown = calcCrown(masteryState);
        const activityCount = Number(row.activity_count || 0);
        const flashcardCount = Number(row.flashcard_count || 0);
        const questionCount = Number(row.question_count || 0);
        const activityTypes = splitCsv(row.activity_types);
        const practice = computePracticeProfile({
          activityCount,
          flashcardCount,
          questionCount,
          activityTypes,
        }, masteryState, { isFocused: focusList.includes(row.para_id) });

        return withSourceRef({
          para_id: row.para_id,
          title: row.title,
          page: Number(row.page || 0),
          activityCount,
          flashcardCount,
          questionCount,
          activityTypes,
          crown,
          focusScore: practice.score,
          focusBand: practice.band,
          focusReasons: practice.reasons,
          averageScore: practice.averageScore,
          recentScore: recentAccuracy(masteryState) === null ? null : Math.round(recentAccuracy(masteryState) * 100),
          isFocused: focusList.includes(row.para_id),
        }, row.para_id, row.page, {
          title: row.title,
          blocks: JSON.parse(row.content_json || "[]"),
        });
      })
      .filter((row) => row.activityCount > 0 || row.questionCount > 0 || row.flashcardCount > 0);
  }, [focusList, isParagraphPublished, mastery, query]);

  const getFocusParagraphs = useCallback(() => {
    if (!focusList.length) return [];

    const placeholders = focusList.map(() => "?").join(",");
    const rows = query(`
      SELECT p.chapter, p.section, p.para_id, p.title, p.page, p.content_json,
             COALESCE(a.activity_count, 0) AS activity_count,
             COALESCE(a.activity_types, '') AS activity_types,
             COALESCE(f.flashcard_count, 0) AS flashcard_count,
             COALESCE(q.question_count, 0) AS question_count
      FROM paragraphs p
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS activity_count, GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM activities
        GROUP BY para_id
      ) a ON a.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS flashcard_count
        FROM flashcards
        WHERE ${PUBLISHED_FLASHCARD_FILTER_NO_ALIAS}
        GROUP BY para_id
      ) f ON f.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS question_count
        FROM quiz_questions
        GROUP BY para_id
      ) q ON q.para_id = p.para_id
      WHERE p.para_id IN (${placeholders})
      ORDER BY p.chapter, p.section, p.para_id
    `, focusList);

    return rows
      .filter((row) => isParagraphPublished(row.para_id))
      .map((row) => {
        const masteryState = mastery[row.para_id] || { total: 0, type_counts: {}, type_scores: {} };
        const crown = calcCrown(masteryState);
        const activityCount = Number(row.activity_count || 0);
        const flashcardCount = Number(row.flashcard_count || 0);
        const questionCount = Number(row.question_count || 0);
        const activityTypes = splitCsv(row.activity_types);
        const practice = computePracticeProfile({
          activityCount,
          flashcardCount,
          questionCount,
          activityTypes,
        }, masteryState, { isFocused: true });

        return withSourceRef({
          chapter: Number(row.chapter),
          section: Number(row.section),
          sectionLabel: SECTION_LABELS[`${row.chapter}-${row.section}`] || `Section ${row.section}`,
          chapterLabel: CHAPTER_TITLES[row.chapter] || `Chapter ${row.chapter}`,
          para_id: row.para_id,
          title: row.title,
          page: Number(row.page || 0),
          activityCount,
          flashcardCount,
          questionCount,
          activityTypes,
          crown,
          focusScore: practice.score,
          focusBand: practice.band,
          focusReasons: practice.reasons,
          averageScore: practice.averageScore,
          recentScore: recentAccuracy(masteryState) === null ? null : Math.round(recentAccuracy(masteryState) * 100),
          isFocused: true,
        }, row.para_id, row.page, {
          title: row.title,
          blocks: JSON.parse(row.content_json || "[]"),
        });
      })
      .filter((row) => row.activityCount > 0 || row.questionCount > 0 || row.flashcardCount > 0);
  }, [focusList, isParagraphPublished, mastery, query]);

  const buildFocusSession = useCallback((paraIds, count = null) => {
    const filteredParaIds = [...new Set((paraIds || []).filter((paraId) => isParagraphPublished(paraId)))];
    if (!filteredParaIds.length) return [];

    const placeholders = filteredParaIds.map(() => "?").join(",");
    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      WHERE a.para_id IN (${placeholders})
      ORDER BY p.chapter, p.section, p.para_id, a.activity_type
    `, filteredParaIds);

    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRowsForParagraphs(filteredParaIds)),
    ];

    return buildSessionOrder(activities, mastery, count, { mode: "focus" });
  }, [isParagraphPublished, mapActivityRows, mapQuestionRows, mastery, query, questionRowsForParagraphs]);

  const getPracticeQueue = useCallback((limit = 8) => {
    const rows = query(`
      SELECT p.para_id, p.chapter, p.section, p.title, p.page, p.content_json,
             COALESCE(a.activity_count, 0) AS activity_count,
             COALESCE(a.activity_types, '') AS activity_types,
             COALESCE(f.flashcard_count, 0) AS flashcard_count,
             COALESCE(q.question_count, 0) AS question_count
      FROM paragraphs p
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS activity_count, GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM activities
        GROUP BY para_id
      ) a ON a.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS flashcard_count
        FROM flashcards
        WHERE ${PUBLISHED_FLASHCARD_FILTER_NO_ALIAS}
        GROUP BY para_id
      ) f ON f.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS question_count
        FROM quiz_questions
        GROUP BY para_id
      ) q ON q.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id
    `);

    const candidates = rows
      .filter((row) => isParagraphPublished(row.para_id))
      .map((row) => {
        const activityCount = Number(row.activity_count || 0);
        const flashcardCount = Number(row.flashcard_count || 0);
        const questionCount = Number(row.question_count || 0);
        const activityTypes = splitCsv(row.activity_types);
        const state = mastery[row.para_id] || { total: 0, type_counts: {}, type_scores: {} };
        const crown = calcCrown(state);
        const practice = computePracticeProfile({
          activityCount,
          flashcardCount,
          questionCount,
          activityTypes,
        }, state, { isFocused: focusList.includes(row.para_id) });

        return withSourceRef({
          para_id: row.para_id,
          chapter: Number(row.chapter),
          section: Number(row.section),
          sectionLabel: SECTION_LABELS[`${row.chapter}-${row.section}`] || `Section ${row.section}`,
          chapterLabel: CHAPTER_TITLES[row.chapter] || `Chapter ${row.chapter}`,
          title: row.title,
          page: Number(row.page || 0),
          activityCount,
          flashcardCount,
          questionCount,
          activityTypes,
          crown,
          practiceScore: practice.score,
          focusScore: practice.score,
          focusBand: practice.band,
          focusReasons: practice.reasons,
          averageScore: practice.averageScore,
          recentScore: recentAccuracy(state) === null ? null : Math.round(recentAccuracy(state) * 100),
          isFocused: focusList.includes(row.para_id),
          attemptCount: practice.total,
        }, row.para_id, row.page, {
          title: row.title,
          blocks: JSON.parse(row.content_json || "[]"),
        });
      })
      .filter((row) => row.activityCount > 0 || row.questionCount > 0);

    const attempted = candidates.filter((item) => item.attemptCount > 0);
    const weakAttempted = attempted.filter((item) => (item.averageScore !== null && item.averageScore < 85) || item.crown < 3 || item.isFocused);
    const orderedNew = candidates
      .filter((item) => item.attemptCount === 0)
      .sort(compareParagraphOrder);
    const rankedWeak = weakAttempted.sort((a, b) => (
      b.practiceScore - a.practiceScore
      || compareParagraphOrder(a, b)
    ));

    const pool = rankedWeak.length >= Math.min(limit, 3)
      ? rankedWeak
      : [...rankedWeak, ...orderedNew];

    return pool
      .filter((item, index, arr) => arr.findIndex((candidate) => candidate.para_id === item.para_id) === index)
      .slice(0, limit);
  }, [focusList, isParagraphPublished, mastery, query]);

  const getConceptQueue = useCallback((limit = 6) => {
    const rows = query(`
      SELECT p.para_id, p.chapter, p.section, p.title, p.page, p.content_json,
             COALESCE(a.activity_count, 0) AS activity_count,
             COALESCE(a.activity_types, '') AS activity_types,
             COALESCE(q.question_count, 0) AS question_count
      FROM paragraphs p
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS activity_count, GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM activities
        GROUP BY para_id
      ) a ON a.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS question_count
        FROM quiz_questions
        GROUP BY para_id
      ) q ON q.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id
    `);

    const paragraphConcepts = rows
      .filter((row) => isParagraphPublished(row.para_id) && (Number(row.activity_count || 0) > 0 || Number(row.question_count || 0) > 0))
      .map((row) => {
        const text = blockSearchText(row.content_json);
        const activityTypes = splitCsv(row.activity_types);
        const concepts = [
          ...activityTypes.flatMap((activityType) => conceptTagsForText({
            title: row.title,
            text,
            activityType,
          })),
          ...(Number(row.question_count || 0) > 0 ? conceptTagsForText({
            title: row.title,
            text,
            activityType: "knowledge_check",
          }) : []),
        ];
        return {
          para_id: row.para_id,
          chapter: Number(row.chapter),
          section: Number(row.section),
          sectionLabel: SECTION_LABELS[`${row.chapter}-${row.section}`] || `Section ${row.section}`,
          title: row.title,
          page: Number(row.page || 0),
          activityCount: Number(row.activity_count || 0),
          questionCount: Number(row.question_count || 0),
          conceptIds: [...new Set(concepts.map((concept) => concept.id))],
        };
      });

    return Object.entries(conceptMemory)
      .map(([conceptId, record]) => {
        const score = conceptIssueScore(record);
        const matchedParagraphs = paragraphConcepts
          .filter((paragraph) => paragraph.conceptIds.includes(conceptId))
          .sort((a, b) => {
            const aMissed = record.paraIds?.includes(a.para_id) ? 1 : 0;
            const bMissed = record.paraIds?.includes(b.para_id) ? 1 : 0;
            return bMissed - aMissed || compareParagraphOrder(a, b);
          });
        return {
          id: conceptId,
          label: conceptLabel(conceptId),
          score,
          misses: Number(record.misses || 0),
          recoveries: Number(record.recoveries || 0),
          lastMissAt: record.lastMissAt,
          paragraphs: matchedParagraphs.slice(0, 5),
          paraIds: matchedParagraphs.map((paragraph) => paragraph.para_id),
        };
      })
      .filter((item) => item.score > 0 && item.paragraphs.length > 0)
      .sort((a, b) => b.score - a.score || a.label.localeCompare(b.label))
      .slice(0, limit);
  }, [conceptMemory, isParagraphPublished, query]);

  const buildConceptSession = useCallback((conceptIds = [], count = 12) => {
    const targetConceptIds = [...new Set((conceptIds || []).map((item) => String(item || "").trim()).filter(Boolean))];
    if (!targetConceptIds.length) return [];

    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json,
             p.chapter, p.section
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id, a.activity_type
    `);
    const questionRows = query(`
      SELECT q.id, q.para_id, p.title para_title, q.question_type,
             q.question_text, q.explanation, q.difficulty,
             p.page, p.content_json AS para_content_json,
             p.chapter, p.section
      FROM quiz_questions q
      JOIN paragraphs p ON q.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id, q.question_type, q.id
    `);

    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRows),
    ]
      .filter((activity) => activity.concepts.some((concept) => targetConceptIds.includes(concept.id)));

    const paraScores = {};
    for (const conceptId of targetConceptIds) {
      const memoryRecord = conceptMemory[conceptId] || {};
      const score = conceptIssueScore(memoryRecord);
      for (const paraId of memoryRecord.paraIds || []) {
        paraScores[paraId] = Math.max(paraScores[paraId] || 0, score);
      }
    }

    return buildSessionOrder(activities, mastery, count, { paraScores, mode: "concept" });
  }, [conceptMemory, mapActivityRows, mapQuestionRows, mastery, query]);

  const buildRecommendedSession = useCallback((count = 12) => {
    const queue = getPracticeQueue(10);
    const paraIds = queue.map((item) => item.para_id);
    if (!paraIds.length) return [];

    const placeholders = paraIds.map(() => "?").join(",");
    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      WHERE a.para_id IN (${placeholders})
      ORDER BY p.chapter, p.section, p.para_id, a.activity_type
    `, paraIds);

    const paraScores = Object.fromEntries(queue.map((item) => [item.para_id, item.practiceScore]));
    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRowsForParagraphs(paraIds)),
    ];

    return buildSessionOrder(activities, mastery, count, { paraScores, mode: "recommended" });
  }, [getPracticeQueue, mapActivityRows, mapQuestionRows, mastery, query, questionRowsForParagraphs]);

  const buildPracticeModeSession = useCallback((modeId, count = 10) => {
    if (modeId === "weak_areas") return buildRecommendedSession(count);

    const config = PRACTICE_MODE_CONFIG[modeId] || PRACTICE_MODE_CONFIG.diagnostic;
    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json,
             p.chapter, p.section
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id, a.activity_type
    `);
    const questionRows = query(`
      SELECT q.id, q.para_id, p.title para_title, q.question_type,
             q.question_text, q.explanation, q.difficulty,
             p.page, p.content_json AS para_content_json,
             p.chapter, p.section
      FROM quiz_questions q
      JOIN paragraphs p ON q.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id, q.question_type, q.id
    `);

    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRows),
    ]
      .filter((activity) => {
        const typeMatch = !config.activityTypes || config.activityTypes.includes(activity.activity_type);
        const conceptMatch = !config.conceptIds || activity.concepts.some((concept) => config.conceptIds.includes(concept.id));
        return typeMatch || conceptMatch;
      });

    const paraScores = {};
    for (const activity of activities) {
      const state = mastery[activity.para_id] || {};
      const avgScore = averageScoreForState(state);
      const weakBoost = avgScore !== null && avgScore < 0.85 ? 6 : 0;
      const newBoost = Number(state.total || 0) === 0 ? 2 : 0;
      const conceptBoost = Math.max(
        0,
        ...activity.concepts.map((concept) => conceptIssueScore(conceptMemory[concept.id] || {})),
      );
      paraScores[activity.para_id] = Math.max(paraScores[activity.para_id] || 0, weakBoost + newBoost + conceptBoost);
    }

    const modeCount = modeId === "diagnostic" ? Math.max(count, 10) : count;
    return buildSessionOrder(activities, mastery, modeCount, { paraScores, mode: "practice" });
  }, [buildRecommendedSession, conceptMemory, mapActivityRows, mapQuestionRows, mastery, query]);

  const getMistakeQueue = useCallback((limit = 8) => {
    const records = Object.values(mistakeQueue)
      .sort((a, b) => (
        Number(b.misses || 0) - Number(a.misses || 0)
        || String(b.lastMissAt || "").localeCompare(String(a.lastMissAt || ""))
      ))
      .slice(0, limit);
    if (!records.length) return [];

    const activityIds = records
      .map((record) => String(record.activityId || ""))
      .filter((id) => id && !id.startsWith("q:"));
    const questionIds = records
      .map((record) => String(record.activityId || ""))
      .filter((id) => id.startsWith("q:"))
      .map((id) => id.slice(2));
    const rows = activityIds.length
      ? query(`
        SELECT a.id, a.para_id, p.title para_title, p.chapter, p.section, p.page,
               a.activity_type, a.content_json, p.content_json AS para_content_json
        FROM activities a
        JOIN paragraphs p ON a.para_id = p.para_id
        WHERE a.id IN (${activityIds.map(() => "?").join(",")})
        ORDER BY p.chapter, p.section, p.para_id, a.activity_type
      `, activityIds)
      : [];
    const questionRows = questionIds.length
      ? query(`
        SELECT q.id, q.para_id, p.title para_title, p.chapter, p.section, p.page,
               q.question_text, q.question_type, p.content_json AS para_content_json
        FROM quiz_questions q
        JOIN paragraphs p ON q.para_id = p.para_id
        WHERE q.id IN (${questionIds.map(() => "?").join(",")})
        ORDER BY p.chapter, p.section, p.para_id, q.question_type, q.id
      `, questionIds)
      : [];
    const byId = Object.fromEntries(rows.map((row) => [row.id, row]));
    const questionById = Object.fromEntries(questionRows.map((row) => [`q:${row.id}`, row]));

    return records
      .map((record) => {
        const recordId = String(record.activityId || "");
        const questionRow = questionById[recordId];
        if (questionRow) {
          if (!isParagraphPublished(questionRow.para_id)) return null;
          const concepts = record.concepts?.length
            ? record.concepts
            : conceptTagsForText({
              title: questionRow.para_title,
              text: `${blockSearchText(questionRow.para_content_json)} ${questionRow.question_text}`,
              activityType: "knowledge_check",
            });
          return withSourceRef({
            activityId: recordId,
            para_id: questionRow.para_id,
            chapter: Number(questionRow.chapter),
            section: Number(questionRow.section),
            sectionLabel: SECTION_LABELS[`${questionRow.chapter}-${questionRow.section}`] || `Section ${questionRow.section}`,
            title: questionRow.para_title,
            activityType: "knowledge_check",
            questionText: questionRow.question_text,
            misses: Number(record.misses || 1),
            lastMissAt: record.lastMissAt,
            concepts,
          }, questionRow.para_id, questionRow.page, {
            title: questionRow.para_title,
            blocks: safeJsonParse(questionRow.para_content_json, []),
          });
        }

        const row = byId[recordId];
        if (!row || !isParagraphPublished(row.para_id)) return null;
        const content = safeJsonParse(row.content_json, {});
        const concepts = record.concepts?.length
          ? record.concepts
          : conceptTagsForText({
            title: row.para_title,
            text: blockSearchText(row.para_content_json),
            activityType: row.activity_type,
          });
        return withSourceRef({
          activityId: recordId,
          para_id: row.para_id,
          chapter: Number(row.chapter),
          section: Number(row.section),
          sectionLabel: SECTION_LABELS[`${row.chapter}-${row.section}`] || `Section ${row.section}`,
          title: row.para_title,
          activityType: row.activity_type,
          questionText: content.question_text || content.situation || content.prompt || content.clearance || content.target_phrase || row.activity_type,
          misses: Number(record.misses || 1),
          lastMissAt: record.lastMissAt,
          concepts,
        }, row.para_id, row.page, {
          title: row.para_title,
          blocks: safeJsonParse(row.para_content_json, []),
        });
      })
      .filter(Boolean);
  }, [isParagraphPublished, mistakeQueue, query]);

  const buildMistakeSession = useCallback((count = 6) => {
    const records = Object.values(mistakeQueue);
    if (!records.length) return [];

    const activityIds = records
      .map((record) => String(record.activityId || ""))
      .filter((id) => id && !id.startsWith("q:"));
    const questionIds = records
      .map((record) => String(record.activityId || ""))
      .filter((id) => id.startsWith("q:"))
      .map((id) => id.slice(2));
    const rows = activityIds.length
      ? query(`
        SELECT a.id, a.para_id, p.title para_title, a.activity_type,
               a.content_json, a.difficulty, p.page, p.content_json AS para_content_json
        FROM activities a
        JOIN paragraphs p ON a.para_id = p.para_id
        WHERE a.id IN (${activityIds.map(() => "?").join(",")})
        ORDER BY p.chapter, p.section, p.para_id, a.activity_type
      `, activityIds)
      : [];
    const questionRows = questionIds.length
      ? query(`
        SELECT q.id, q.para_id, p.title para_title, q.question_type,
               q.question_text, q.explanation, q.difficulty,
               p.page, p.content_json AS para_content_json,
               p.chapter, p.section
        FROM quiz_questions q
        JOIN paragraphs p ON q.para_id = p.para_id
        WHERE q.id IN (${questionIds.map(() => "?").join(",")})
        ORDER BY p.chapter, p.section, p.para_id, q.question_type, q.id
      `, questionIds)
      : [];
    const recordById = Object.fromEntries(records.map((record) => [record.activityId, record]));
    const paraScores = {};

    const activities = mapActivityRows(rows)
      .map((r) => {
        const record = recordById[r.id] || {};
        const concepts = record.concepts?.length
          ? record.concepts
          : r.concepts;
        paraScores[r.para_id] = Math.max(paraScores[r.para_id] || 0, Number(record.misses || 1) * 6);
        return { ...r, concepts };
      });
    const questionActivities = mapQuestionRows(questionRows).map((activity) => {
      const record = recordById[`q:${activity.quiz_question_id}`] || {};
      paraScores[activity.para_id] = Math.max(paraScores[activity.para_id] || 0, Number(record.misses || 1) * 6);
      return {
        ...activity,
        concepts: record.concepts?.length ? record.concepts : activity.concepts,
      };
    });

    return buildSessionOrder([...activities, ...questionActivities], mastery, count, { paraScores, mode: "missed" });
  }, [mapActivityRows, mapQuestionRows, mastery, mistakeQueue, query]);

  const getDueReviewQueue = useCallback((limit = 6) => {
    const rows = query(`
      SELECT p.para_id, p.chapter, p.section, p.title, p.page, p.content_json,
             COALESCE(a.activity_count, 0) AS activity_count,
             COALESCE(a.activity_types, '') AS activity_types,
             COALESCE(q.question_count, 0) AS question_count
      FROM paragraphs p
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS activity_count, GROUP_CONCAT(DISTINCT activity_type) AS activity_types
        FROM activities
        GROUP BY para_id
      ) a ON a.para_id = p.para_id
      LEFT JOIN (
        SELECT para_id, COUNT(*) AS question_count
        FROM quiz_questions
        GROUP BY para_id
      ) q ON q.para_id = p.para_id
      ORDER BY p.chapter, p.section, p.para_id
    `);

    return rows
      .filter((row) => isParagraphPublished(row.para_id) && (Number(row.activity_count || 0) > 0 || Number(row.question_count || 0) > 0))
      .map((row) => {
        const state = mastery[row.para_id];
        const due = dueReviewProfile(state);
        if (!due) return null;
        return withSourceRef({
          para_id: row.para_id,
          chapter: Number(row.chapter),
          section: Number(row.section),
          sectionLabel: SECTION_LABELS[`${row.chapter}-${row.section}`] || `Section ${row.section}`,
          title: row.title,
          page: Number(row.page || 0),
          activityCount: Number(row.activity_count || 0),
          questionCount: Number(row.question_count || 0),
          activityTypes: splitCsv(row.activity_types),
          dueReason: due.reason,
          dueScore: due.urgency,
          crown: due.crown,
          recentScore: due.recentScore,
          daysSince: due.daysSince,
        }, row.para_id, row.page, {
          title: row.title,
          blocks: JSON.parse(row.content_json || "[]"),
        });
      })
      .filter(Boolean)
      .sort((a, b) => b.dueScore - a.dueScore || compareParagraphOrder(a, b))
      .slice(0, limit);
  }, [isParagraphPublished, mastery, query]);

  const buildDueReviewSession = useCallback((count = 8) => {
    const queue = getDueReviewQueue(10);
    const paraIds = queue.map((item) => item.para_id);
    if (!paraIds.length) return [];

    const placeholders = paraIds.map(() => "?").join(",");
    const rows = query(`
      SELECT a.id, a.para_id, p.title para_title, a.activity_type,
             a.content_json, a.difficulty, p.page, p.content_json AS para_content_json
      FROM activities a
      JOIN paragraphs p ON a.para_id = p.para_id
      WHERE a.para_id IN (${placeholders})
      ORDER BY p.chapter, p.section, p.para_id, a.activity_type
    `, paraIds);
    const paraScores = Object.fromEntries(queue.map((item) => [item.para_id, item.dueScore]));

    const activities = [
      ...mapActivityRows(rows),
      ...mapQuestionRows(questionRowsForParagraphs(paraIds)),
    ];

    return buildSessionOrder(activities, mastery, count, { paraScores, mode: "due" });
  }, [getDueReviewQueue, mapActivityRows, mapQuestionRows, mastery, query, questionRowsForParagraphs]);

  // ── Flashcards for a section ───────────────────────────────────────────────
  const getFlashcards = useCallback((chapter, section) => {
    const rows = query(`
      SELECT f.id, f.para_id, p.title para_title, p.page, p.content_json AS para_content_json, f.front, f.back, f.card_type
      FROM flashcards f
      JOIN paragraphs p ON f.para_id = p.para_id
      WHERE p.chapter = ? AND p.section = ?
        AND ${PUBLISHED_FLASHCARD_FILTER}
      ORDER BY f.card_type, p.para_id
    `, [chapter, section]);
    return rows
      .filter((row) => isParagraphPublished(row.para_id))
      .map((row) => withSourceRef(row, row.para_id, row.page, {
      title: row.para_title,
      blocks: JSON.parse(row.para_content_json || "[]"),
    }));
  }, [isParagraphPublished, query]);

  const getParagraphFlashcards = useCallback((paraId) => {
    if (!isParagraphPublished(paraId)) return [];

    const rows = query(`
      SELECT f.id, f.para_id, p.title para_title, p.page, p.content_json AS para_content_json,
             f.front, f.back, f.card_type
      FROM flashcards f
      JOIN paragraphs p ON f.para_id = p.para_id
      WHERE f.para_id = ?
        AND ${PUBLISHED_FLASHCARD_FILTER}
      ORDER BY f.card_type, f.front
    `, [paraId]);

    return rows.map((row) => withSourceRef(row, row.para_id, row.page, {
      title: row.para_title,
      blocks: JSON.parse(row.para_content_json || "[]"),
    }));
  }, [isParagraphPublished, query]);

  const getAircraftRecognitionCards = useCallback(() => {
    const rows = query(`
      SELECT f.id, f.para_id, p.title para_title, p.page, p.content_json AS para_content_json,
             f.front, f.back, f.card_type, f.generation_src
      FROM flashcards f
      JOIN paragraphs p ON f.para_id = p.para_id
      WHERE f.generation_src = 'aircraft_jo7360'
      ORDER BY
        CASE f.card_type
          WHEN 'aircraft_designator' THEN 1
          WHEN 'aircraft_srs' THEN 2
          ELSE 9
        END,
        f.front
    `);

    const sourceRef = buildJo7360SourceRef();
    return rows.map((row) => ({
      ...row,
      ...sourceRef,
      para_title: "Aircraft Type Designators",
    }));
  }, [query]);

  // ── Record an activity result and update mastery ───────────────────────────
  const recordResult = useCallback((paraId, activityType, score, concepts = [], activityId = null) => {
    setMastery(prev => {
      const state = prev[paraId] || { total: 0, type_counts: {}, type_scores: {}, attempts: [] };
      const next = applyMasteryResult(state, activityType, score);
      const updated = { ...prev, [paraId]: next };
      saveMastery(updated);
      return updated;
    });

    const taggedConcepts = concepts.length
      ? concepts
      : (() => {
        const para = query(`
          SELECT title, content_json
          FROM paragraphs
          WHERE para_id = ?
        `, [paraId])[0];
        return conceptTagsForText({
          title: para?.title || "",
          text: blockSearchText(para?.content_json || "[]"),
          activityType,
        });
      })();

    if (!taggedConcepts.length) return;

    setConceptMemory((prev) => {
      const now = new Date().toISOString();
      const next = { ...prev };
      for (const concept of taggedConcepts) {
        const id = concept.id;
        const existing = next[id] || { misses: 0, recoveries: 0, lastMissAt: null, lastSeenAt: null, paraIds: [] };
        const paraIds = [...new Set([...(existing.paraIds || []), paraId])];
        const missed = Number(score) < 0.8;
        next[id] = {
          ...existing,
          misses: existing.misses + (missed ? 1 : 0),
          recoveries: existing.recoveries + (missed ? 0 : 1),
          lastMissAt: missed ? now : existing.lastMissAt,
          lastSeenAt: now,
          paraIds,
        };
      }
      saveConceptMemory(next);
      return next;
    });

    if (activityId) {
      setMistakeQueue((prev) => {
        const next = { ...prev };
        const id = String(activityId);
        if (Number(score) >= 0.8) {
          delete next[id];
        } else {
          const existing = next[id] || {
            activityId: id,
            paraId,
            activityType,
            misses: 0,
            lastMissAt: null,
            concepts: taggedConcepts,
          };
          next[id] = {
            ...existing,
            activityId: id,
            paraId,
            activityType,
            misses: Number(existing.misses || 0) + 1,
            lastMissAt: new Date().toISOString(),
            concepts: taggedConcepts,
          };
        }
        saveMistakeQueue(next);
        return next;
      });
    }
  }, [query]);

  // ── Crown changes after a session ─────────────────────────────────────────
  const getCrownChanges = useCallback((prevMastery, results) => {
    const changes = [];
    const simulated = {};
    for (const { paraId, activityType, score } of results) {
      const oldState = simulated[paraId] || prevMastery[paraId] || { total: 0, type_counts: {}, type_scores: {}, attempts: [] };
      const oldCrown = calcCrown(oldState);
      const newState = applyMasteryResult(oldState, activityType, score);
      simulated[paraId] = newState;
      const newCrown = calcCrown(newState);
      if (newCrown > oldCrown) {
        changes.push({ paraId, oldCrown, newCrown });
      } else if (newCrown < oldCrown) {
        changes.push({ paraId, oldCrown, newCrown, regressed: true });
      }
    }
    return changes;
  }, []);

  // ── Stats for dashboard ────────────────────────────────────────────────────
  const getStats = useCallback(() => {
    const paraRows = query("SELECT para_id FROM paragraphs");
    const publishedParaIds = paraRows.map((row) => row.para_id).filter(isParagraphPublished);
    const publishedParaSet = new Set(publishedParaIds);
    const paraCount = publishedParaIds.length;
    const hiddenParaCount = paraRows.length - paraCount;

    const actCount = query("SELECT para_id, COUNT(*) AS n FROM activities GROUP BY para_id")
      .reduce((sum, row) => sum + (publishedParaSet.has(row.para_id) ? Number(row.n || 0) : 0), 0);
    const fcCount = query(`
      SELECT para_id, COUNT(*) AS n
      FROM flashcards
      WHERE ${PUBLISHED_FLASHCARD_FILTER_NO_ALIAS}
      GROUP BY para_id
    `).reduce((sum, row) => sum + (publishedParaSet.has(row.para_id) ? Number(row.n || 0) : 0), 0);
    const questionCount = query("SELECT para_id, COUNT(*) AS n FROM quiz_questions GROUP BY para_id")
      .reduce((sum, row) => sum + (publishedParaSet.has(row.para_id) ? Number(row.n || 0) : 0), 0);

    const masteredParas  = Object.entries(mastery).filter(([paraId, s]) => publishedParaSet.has(paraId) && calcCrown(s) >= 4).length;
    const touchedParas   = Object.keys(mastery).filter((paraId) => publishedParaSet.has(paraId)).length;
    const totalActivities = Object.entries(mastery)
      .reduce((sum, [paraId, state]) => sum + (publishedParaSet.has(paraId) ? (state.total || 0) : 0), 0);

    return {
      paraCount,
      hiddenParaCount,
      actCount,
      fcCount,
      questionCount,
      masteredParas,
      touchedParas,
      totalActivities,
      focusCount: focusList.filter((paraId) => publishedParaSet.has(paraId)).length,
      publishMode,
    };
  }, [focusList, isParagraphPublished, mastery, publishMode, query]);

  return {
    loading: loading || reviewPersistence.mode === "loading",
    error,
    dbReady,
    mastery,
    publishConfig,
    // Data queries
    getChapters,
    buildSession,
    buildParaSession,
    buildFocusSession,
    buildRecommendedSession,
    buildConceptSession,
    buildPracticeModeSession,
    buildMistakeSession,
    buildDueReviewSession,
    getPracticeQueue,
    getConceptQueue,
    getMistakeQueue,
    getDueReviewQueue,
    getSectionParagraphs,
    getFocusParagraphs,
    getFlashcards,
    getParagraphFlashcards,
    getAircraftRecognitionCards,
    getParaMastery,
    getSectionMastery,
    getStats,
    getReviewQueue,
    getParagraphAudit,
    reviewState,
    reviewPersistence,
    focusList,
    exportReviewState,
    importReviewState,
    clearReviewState,
    // Progress
    recordResult,
    getCrownChanges,
    saveParagraphReview,
    isParagraphFocused,
    toggleFocusedParagraph,
    clearFocusList,
    conceptMemory,
    mistakeQueue,
    calcCrown,
  };
}


// ─────────────────────────────────────────────────────────────────────────────
// SESSION BUILDER (pure function, no DB access)
// ─────────────────────────────────────────────────────────────────────────────

function resolvedSessionCount(poolSize, requestedCount, mode = "section") {
  if (poolSize <= 0) return 0;
  const requested = Number(requestedCount);
  if (Number.isFinite(requested) && requested > 0) return Math.min(poolSize, Math.round(requested));
  if (poolSize <= 8) return poolSize;
  if (mode === "paragraph") return Math.min(poolSize, 12);
  if (mode === "missed") return Math.min(poolSize, 8);
  if (mode === "focus" || mode === "recommended" || mode === "due") return Math.min(poolSize, 12);
  if (mode === "practice" || mode === "concept") return Math.min(poolSize, 14);
  return Math.min(poolSize, 12);
}

function buildSessionOrder(activities, mastery, count, options = {}) {
  const pool = [...(activities || [])].filter(Boolean);
  const targetCount = resolvedSessionCount(pool.length, count, options.mode);
  if (!targetCount) return [];

  const scored = pool.map((act, index) => {
    const state = mastery[act.para_id] || { total: 0, type_counts: {}, type_scores: {}, attempts: [] };
    const typeCount = Number(state.type_counts?.[act.activity_type] || 0);
    const typeTotal = Object.values(state.type_counts || {}).reduce((sum, value) => sum + Number(value || 0), 0);
    const typeKinds = Math.max(Object.keys(state.type_counts || {}).length, 1);
    const meanTypeCount = typeTotal / typeKinds;
    const avgScore = averageScoreForState(state);
    const recent = recentAccuracy(state, 6);
    const crown = calcCrown(state);
    const typeScore = state.type_scores?.[act.activity_type];
    const paraBoost = Number(options.paraScores?.[act.para_id] || 0) / 3;
    const newParaBoost = Number(state.total || 0) === 0 ? 5 : 0;
    const weakParaBoost = avgScore !== null && avgScore < 0.72
      ? 4
      : avgScore !== null && avgScore < 0.85
        ? 2
        : 0;
    const recentWeakBoost = recent !== null && recent < 0.80 ? 2.5 : 0;
    const typeDeficitBoost = Math.max(0, meanTypeCount - typeCount) * 0.8 + (typeCount === 0 ? 2.2 : 0);
    const weakTypeBoost = Number.isFinite(Number(typeScore)) && Number(typeScore) < 0.82 ? 2.5 : 0;
    const lowCrownBoost = Math.max(0, 4 - crown) * 0.75;
    const difficulty = Number(act.difficulty || 0);
    const difficultyNudge = Number.isFinite(difficulty) ? Math.min(1, Math.max(0, difficulty) / 8) : 0;
    const stableTieBreak = ((index * 9301 + String(act.id || "").length * 49297) % 233) / 1000;

    return {
      act,
      baseScore: paraBoost
        + newParaBoost
        + weakParaBoost
        + recentWeakBoost
        + typeDeficitBoost
        + weakTypeBoost
        + lowCrownBoost
        + difficultyNudge
        + stableTieBreak,
    };
  });

  const selected = [];
  const remaining = [...scored];
  const usedPara = new Map();
  const usedType = new Map();
  const uniqueParaTarget = Math.min(targetCount, new Set(pool.map((act) => act.para_id)).size);

  while (selected.length < targetCount && remaining.length) {
    let bestIndex = 0;
    let bestScore = -Infinity;

    for (let i = 0; i < remaining.length; i += 1) {
      const candidate = remaining[i];
      const last = selected[selected.length - 1];
      const paraUses = usedPara.get(candidate.act.para_id) || 0;
      const typeUses = usedType.get(candidate.act.activity_type) || 0;
      const earlyDiversityPenalty = selected.length < uniqueParaTarget && paraUses > 0 ? 2.4 : 0;
      const score = candidate.baseScore
        - (last?.activity_type === candidate.act.activity_type ? 3.2 : 0)
        - (last?.para_id === candidate.act.para_id ? 3.6 : 0)
        - paraUses * 1.35
        - typeUses * 0.35
        - earlyDiversityPenalty;

      if (score > bestScore) {
        bestScore = score;
        bestIndex = i;
      }
    }

    const [picked] = remaining.splice(bestIndex, 1);
    selected.push(picked.act);
    usedPara.set(picked.act.para_id, (usedPara.get(picked.act.para_id) || 0) + 1);
    usedType.set(picked.act.activity_type, (usedType.get(picked.act.activity_type) || 0) + 1);
  }

  return selected;
}


// ─────────────────────────────────────────────────────────────────────────────
// EXPORT HELPERS
// ─────────────────────────────────────────────────────────────────────────────

export { calcCrown };

export const CROWN_ICONS  = ["◇", "♦", "♦♦", "♦♦♦", "♛"];
export const CROWN_LABELS = ["Not started", "Introduced", "Familiar", "Proficient", "Gold"];
export const CROWN_COLORS = ["#746f61", "#8ea59c", "#9aa68a", "#b78652", "#d8a21c"];
export { REVIEW_STATUS_META };
