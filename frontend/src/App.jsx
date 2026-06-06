/**
 * App.jsx
 * =======
 * Top-level shell. Manages screen navigation:
 *
 *   loading  → Loading screen (sql.js + curriculum.db initialising)
 *   error    → Error screen
 *   map      → CurriculumMap (home)
 *   lesson   → LessonPlayer
 *   cards    → FlashcardDeck
 *   results  → SessionResults
 */

import { useEffect, useMemo, useState, useRef } from "react";
import useCurriculum, { CROWN_ICONS, CROWN_COLORS } from "./useCurriculum";
import CurriculumMap from "./CurriculumMap";
import LessonPlayer  from "./LessonPlayer";
import CurriculumReview from "./CurriculumReview";
import SectionBrowser from "./SectionBrowser";
import FocusListBrowser from "./FocusListBrowser";
import SourceCitation from "./SourceCitation";
import { assetUrl, isStaticDeploy } from "./assetPaths";

const FLASHCARD_MEMORY_KEY = "atc_flashcard_memory_v1";
const ITEM_FLAGS_KEY = "atc_item_flags_v1";
const MAP_VIEW_KEY = "atc_map_view_v1";
const SECTION_VIEW_KEY = "atc_section_view_v1";
const FOCUS_VIEW_KEY = "atc_focus_view_v1";
const AIRCRAFT_IMAGE_REVIEW_KEY = "atc_aircraft_image_review_v1";
const LEARNER_PROGRESS_KEYS = [
  "atc_mastery_v1",
  "atc_focus_list_v1",
  "atc_concept_memory_v1",
  "atc_mistake_queue_v1",
  FLASHCARD_MEMORY_KEY,
];

function loadMapViewState() {
  try {
    const raw = JSON.parse(localStorage.getItem(MAP_VIEW_KEY) || "{}");
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("bad map state");
    return {
      search: typeof raw.search === "string" ? raw.search : "",
      activeFilter: typeof raw.activeFilter === "string" ? raw.activeFilter : "all",
      activeHomeTab: typeof raw.activeHomeTab === "string" ? raw.activeHomeTab : "browse",
      showSuggestion: typeof raw.showSuggestion === "boolean" ? raw.showSuggestion : true,
      openChapters: raw.openChapters && typeof raw.openChapters === "object" && !Array.isArray(raw.openChapters)
        ? raw.openChapters
        : {},
    };
  } catch {
    return {
      search: "",
      activeFilter: "all",
      activeHomeTab: "browse",
      showSuggestion: true,
      openChapters: {},
    };
  }
}

function saveMapViewState(state) {
  try {
    localStorage.setItem(MAP_VIEW_KEY, JSON.stringify(state));
  } catch {}
}

function loadBrowserViewState(key, defaults) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || "{}");
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("bad browser state");
    return {
      ...defaults,
      ...Object.fromEntries(
        Object.keys(defaults).map((field) => [
          field,
          typeof raw[field] === typeof defaults[field] ? raw[field] : defaults[field],
        ]),
      ),
    };
  } catch {
    return defaults;
  }
}

function saveBrowserViewState(key, state) {
  try {
    localStorage.setItem(key, JSON.stringify(state));
  } catch {}
}

function isPerfProbeEnabled() {
  try {
    return new URLSearchParams(window.location.search).has("perf");
  } catch {
    return false;
  }
}

function probeTime(label, fn, thresholdMs = 1) {
  if (!isPerfProbeEnabled()) return fn();
  const startedAt = performance.now();
  const value = fn();
  const elapsed = performance.now() - startedAt;
  if (elapsed >= thresholdMs) {
    console.log(`[perf] ${label}: ${elapsed.toFixed(1)}ms`);
  }
  return value;
}

function countItemFlags() {
  try {
    const raw = JSON.parse(localStorage.getItem(ITEM_FLAGS_KEY) || "{}");
    return raw && typeof raw === "object" && !Array.isArray(raw) ? Object.keys(raw).length : 0;
  } catch {
    return 0;
  }
}

function loadItemFlags() {
  try {
    const raw = JSON.parse(localStorage.getItem(ITEM_FLAGS_KEY) || "{}");
    return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  } catch {
    return {};
  }
}

function saveItemFlags(flags) {
  try {
    localStorage.setItem(ITEM_FLAGS_KEY, JSON.stringify(flags));
  } catch {}
}

function loadAircraftImageReviewState() {
  try {
    const raw = JSON.parse(localStorage.getItem(AIRCRAFT_IMAGE_REVIEW_KEY) || "{}");
    return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  } catch {
    return {};
  }
}

function saveAircraftImageReviewState(state) {
  try {
    localStorage.setItem(AIRCRAFT_IMAGE_REVIEW_KEY, JSON.stringify(state));
  } catch {}
}

function parseAircraftImageManifest(text) {
  return String(text || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function aircraftImageKey(image) {
  return image?.sha256 || `${image?.type_designator || "aircraft"}:${image?.public_path || image?.source_page || ""}`;
}

function imageReviewStatus(image, reviewState) {
  const key = aircraftImageKey(image);
  return reviewState?.[key]?.identity_status || image?.identity_status || "not_reviewed";
}

const GENERIC_AIRCRAFT_MAKERS = new Set([
  "aero commander",
  "airbus",
  "beechcraft",
  "bell",
  "boeing",
  "bombardier",
  "canadair",
  "cessna",
  "cirrus",
  "dassault",
  "de havilland canada",
  "embraer",
  "gulfstream",
  "learjet",
  "mcdonnell douglas",
  "mooney",
  "pilatus",
  "piper",
  "piper aircraft",
]);

function aircraftBackPieces(back) {
  return String(back || "")
    .split(/\n|·/)
    .map((line) => line.trim().replace(/\s+/g, " "))
    .filter(Boolean);
}

function isAircraftFactLabel(piece) {
  return /^(mfr|cwt|srs|wake|engine|lahso|jo\s*7360|image:|license:|credit:)/i.test(piece);
}

function firstAircraftModelFact(back) {
  return aircraftBackPieces(back).find((piece) => (
    !isAircraftFactLabel(piece) &&
    !looksLikeAircraftIdentifier(piece) &&
    !looksLikeAircraftCategoryToken(piece)
  )) || "";
}

function isGenericAircraftMaker(value) {
  return GENERIC_AIRCRAFT_MAKERS.has(String(value || "").trim().toLowerCase());
}

function aircraftFactRichness(card) {
  const firstFact = firstAircraftModelFact(card?.back);
  let score = 0;
  if (firstFact && !isGenericAircraftMaker(firstFact)) score += 10;
  if (/\bWake\s+/i.test(card?.back || "")) score += 2;
  if (/\bEngine\s+/i.test(card?.back || "")) score += 2;
  if (/\bLAHSO\s+/i.test(card?.back || "")) score += 1;
  return score;
}

function modelLabelByDesignatorFromCards(aircraftCards) {
  const map = new Map();
  for (const card of aircraftCards) {
    if (card?.card_type !== "aircraft_model") continue;
    const designator = aircraftBackPieces(card.back)[0];
    if (looksLikeAircraftIdentifier(designator) && card.front && !isGenericAircraftMaker(card.front)) {
      map.set(designator.toUpperCase(), card.front);
    }
  }
  return map;
}

function replaceWeakAircraftModelFact(back, fallbackModelLabel) {
  if (!fallbackModelLabel) return back;
  const pieces = aircraftBackPieces(back);
  const modelIndex = pieces.findIndex((piece) => !isAircraftFactLabel(piece) && !looksLikeAircraftIdentifier(piece));
  if (modelIndex === -1) return `${fallbackModelLabel} · ${pieces.join(" · ")}`;
  if (!isGenericAircraftMaker(pieces[modelIndex])) return back;
  const next = [...pieces];
  next[modelIndex] = fallbackModelLabel;
  return next.join(" · ");
}

function buildAircraftImageCards(images, reviewState, aircraftCards) {
  const aircraftByDesignator = new Map();
  for (const card of aircraftCards.filter((item) => item.card_type === "aircraft_designator")) {
    if (!looksLikeAircraftIdentifier(card.front)) continue;
    const key = card.front.toUpperCase();
    const existing = aircraftByDesignator.get(key);
    if (!existing || aircraftFactRichness(card) > aircraftFactRichness(existing)) {
      aircraftByDesignator.set(key, card);
    }
  }
  const modelLabelByDesignator = modelLabelByDesignatorFromCards(aircraftCards);

  return images
    .filter((image) => imageReviewStatus(image, reviewState) === "approved")
    .map((image) => {
      const designator = String(image.type_designator || "").toUpperCase();
      const aircraftCard = aircraftByDesignator.get(designator);
      const modelLabel = modelLabelByDesignator.get(designator);
      const facts = replaceWeakAircraftModelFact(aircraftCard?.back || image.manufacturer_model || "", modelLabel);
      return {
        id: `aircraft-image:${aircraftImageKey(image)}`,
        para_id: "JO 7360.1J",
        para_title: "Aircraft Image Recognition",
        front: "Identify this aircraft type/designator.",
        back: `${image.type_designator}\n${facts}`,
        card_type: "aircraft_image",
        generation_src: "aircraft_image_manifest",
        image_public_path: image.public_path,
        image_alt: `${image.type_designator} aircraft candidate`,
        source_label: image.source ? `${image.source} · ${image.license_short_name || "license metadata"}` : "Aircraft image source",
        source_url: image.source_page,
        source_heading: image.file_title,
        source_locator: "Image source page and license metadata from the aircraft image manifest. Verify identity and reuse terms before treating this as learner-facing material.",
        source_excerpt: [image.artist || image.credit, image.license_short_name].filter(Boolean).join(" · "),
      };
    });
}

function loadFlashcardMemory() {
  try {
    const raw = JSON.parse(localStorage.getItem(FLASHCARD_MEMORY_KEY) || "{}");
    return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  } catch {
    return {};
  }
}

function saveFlashcardMemory(state) {
  try {
    localStorage.setItem(FLASHCARD_MEMORY_KEY, JSON.stringify(state));
  } catch {}
}

function shuffleDeck(items) {
  const next = [...items];
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [next[i], next[j]] = [next[j], next[i]];
  }
  return next;
}

function cardKey(card, fallbackIndex) {
  return card?.id || `${card?.para_id || "card"}-${card?.front || fallbackIndex}`;
}

function aircraftFacets(card, facet) {
  if (facet === "cardType") return [card?.card_type || ""].filter(Boolean);
  const text = `${card?.front || ""} · ${card?.back || ""}`;
  const patterns = {
    cwt: /\bCWT\s+([^·;\n]+)/i,
    srs: /\bSRS\s+([^·;\n]+)/i,
    wake: /\bWake\s+([^·;\n]+)/i,
    make: /\bMfr\s+([^·;\n]+)/i,
  };
  const match = text.match(patterns[facet]);
  if (!match) return [];
  return match[1]
    .split("/")
    .map((value) => value.trim())
    .filter(Boolean);
}

function aircraftMakers(card) {
  return aircraftFacets(card, "make").map((maker) => maker.toLowerCase());
}

function aircraftText(card) {
  return `${card?.front || ""} ${card?.back || ""}`.toLowerCase();
}

function aircraftMatchesGroup(card, group) {
  if (!group || group === "all") return true;
  const makers = aircraftMakers(card);
  const text = aircraftText(card);
  const hasMaker = (...needles) => makers.some((maker) => needles.some((needle) => maker.includes(needle)));

  if (group === "cessna") return hasMaker("cessna", "reims", "aviones colombia", "aicsa", "chincul", "soloy");
  if (group === "piper") return hasMaker("piper", "chincul", "colemill");
  if (group === "beechcraft") return hasMaker("beech", "beechcraft", "raytheon", "hawker beechcraft");
  if (group === "airline_transport") return hasMaker("boeing", "airbus", "mcdonnell douglas", "embraer", "bombardier", "canadair", "british aerospace");
  if (group === "business_jets") return hasMaker("gulfstream", "learjet", "gates learjet", "cessna", "dassault", "hawker", "beechcraft", "bombardier", "embraer", "iai", "pilatus");
  if (group === "helicopters") return (
    hasMaker("bell", "sikorsky", "eurocopter", "airbus helicopters", "agusta", "agustawestland", "leonardo", "md helicopters", "hughes", "aerospatiale")
    || /\bhelicopter\b|\b[12]\s*t\s*\/\s*s\b/.test(text)
  );
  if (group === "ga_light") return (
    hasMaker("cessna", "piper", "beech", "beechcraft", "cirrus", "mooney", "diamond", "socata", "pilatus", "american", "grumman", "van")
    || /\bwake light\b/.test(text)
  );
  if (group === "other_conversion") {
    return ![
      "cessna",
      "piper",
      "beechcraft",
      "airline_transport",
      "business_jets",
      "helicopters",
      "ga_light",
    ].some((item) => aircraftMatchesGroup(card, item));
  }
  return true;
}

function cardMatchesAircraftFilters(card, filters = {}) {
  const types = filters.types || [];
  if (types.length && !types.includes(card?.card_type)) return false;
  if (!aircraftMatchesGroup(card, filters.group || "all")) return false;
  for (const facet of ["cwt", "srs", "wake"]) {
    const selected = filters[facet];
    if (selected && selected !== "all" && !aircraftFacets(card, facet).includes(selected)) return false;
  }
  return true;
}

function applyAircraftCardFilters(cards, filters = {}) {
  const filtered = cards.filter((card) => cardMatchesAircraftFilters(card, filters));
  const limit = Number(filters.limit || 0);
  return limit > 0 ? filtered.slice(0, limit) : filtered;
}

function isAircraftStudyCard(card) {
  return card?.generation_src === "aircraft_jo7360" || card?.card_type === "aircraft_image";
}

function cleanAircraftFact(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function looksLikeAircraftIdentifier(value) {
  return /^[A-Z0-9]{2,4}$/i.test(cleanAircraftFact(value));
}

function looksLikeAircraftCategoryToken(value) {
  const clean = cleanAircraftFact(value).toUpperCase();
  return /^(I|II|III|IV|V|VI|VII|VIII|IX|X|A|B|C|D|E|F|LIGHT|SMALL|LARGE|HEAVY|SUPER)$/.test(clean);
}

function firstUnlabeledAircraftFact(pieces) {
  return pieces.find((piece) => (
    !/^(mfr|cwt|srs|wake|engine|lahso|jo\s*7360|image:|license:|credit:)/i.test(piece)
  )) || "";
}

function firstMeaningfulAircraftModelFact(pieces) {
  return pieces.find((piece) => (
    !/^(mfr|cwt|srs|wake|engine|lahso|jo\s*7360|image:|license:|credit:)/i.test(piece) &&
    !looksLikeAircraftIdentifier(piece) &&
    !looksLikeAircraftCategoryToken(piece) &&
    !isGenericAircraftImagePrompt(piece)
  )) || "";
}

function isGenericAircraftImagePrompt(value) {
  return /^identify this aircraft(?: type\/designator)?\.?$/i.test(cleanAircraftFact(value));
}

function aircraftIdentifiersFromBack(pieces) {
  const identifiers = [];
  for (const group of String(pieces.join(";") || "").split(";")) {
    const first = cleanAircraftFact(group.split("·")[0]);
    if (looksLikeAircraftIdentifier(first)) identifiers.push(first.toUpperCase());
  }
  return [...new Set(identifiers)];
}

function parseAircraftFacts(card) {
  const pieces = String(card?.back || "")
    .split(/\n|·/)
    .map(cleanAircraftFact)
    .filter(Boolean);
  const front = cleanAircraftFact(card?.front);
  const factPieces = card?.card_type === "aircraft_image" ? pieces.slice(1) : pieces;
  const valueAfter = (label) => {
    const match = factPieces.find((piece) => piece.toLowerCase().startsWith(`${label.toLowerCase()} `));
    return match ? cleanAircraftFact(match.slice(label.length)) : "";
  };
  const firstFact = firstUnlabeledAircraftFact(factPieces);
  const firstModelFact = firstMeaningfulAircraftModelFact(factPieces);
  const backIdentifiers = aircraftIdentifiersFromBack(factPieces);
  const frontIsIdentifier = looksLikeAircraftIdentifier(front);
  const identifier = (() => {
    if (card?.card_type === "aircraft_image") return cleanAircraftFact(pieces[0] || front);
    if (card?.card_type === "aircraft_srs") return cleanAircraftFact(front.split("·")[0]);
    if (frontIsIdentifier) return front.toUpperCase();
    return backIdentifiers.join("; ");
  })();
  const spokenName = (() => {
    if (card?.card_type === "aircraft_srs") {
      return card?.aircraft_full_facts || valueAfter("Mfr") || valueAfter("CWT") || valueAfter("Wake") || valueAfter("Engine")
        ? firstModelFact
        : "";
    }
    if (card?.card_type === "aircraft_image") {
      return firstModelFact;
    }
    if (card?.card_type === "aircraft_model") return front;
    if (!frontIsIdentifier) return front;
    return firstModelFact;
  })();
  const srs = valueAfter("SRS") || (card?.card_type === "aircraft_srs" ? firstFact : "");

  return {
    identifier,
    spokenName: cleanAircraftFact(spokenName),
    manufacturer: valueAfter("Mfr"),
    cwt: valueAfter("CWT"),
    srs: cleanAircraftFact(srs),
    wake: valueAfter("Wake"),
    engine: valueAfter("Engine"),
    lahso: valueAfter("LAHSO"),
    imageTitle: cleanAircraftFact((factPieces.find((piece) => /^image:/i.test(piece)) || "").replace(/^image:\s*/i, "")),
    license: cleanAircraftFact((factPieces.find((piece) => /^license:/i.test(piece)) || "").replace(/^license:\s*/i, "")),
    credit: cleanAircraftFact((factPieces.find((piece) => /^credit:/i.test(piece)) || "").replace(/^credit:\s*/i, "")),
    source: factPieces.find((piece) => /^jo\s*7360/i.test(piece)) || "JO 7360.1J Appendix A",
  };
}

function aircraftPromptOptions(card) {
  if (!isAircraftStudyCard(card)) return [];
  const facts = parseAircraftFacts(card);
  const options = [];
  if (card?.image_public_path) options.push({ id: "image", label: "Image" });
  if (facts.identifier) options.push({ id: "identifier", label: "Identifier" });
  if (facts.spokenName) options.push({ id: "spoken", label: "Spoken name" });
  return options;
}

function normalizeAircraftPromptMode(card, mode) {
  const options = aircraftPromptOptions(card);
  if (!options.length) return "identifier";
  return options.some((option) => option.id === mode) ? mode : options[0].id;
}

const AIRCRAFT_MISSING_FACT_TEXT = "Not listed in local aircraft data";

function buildAircraftRevealSteps(card, promptMode) {
  if (Array.isArray(card?.aircraft_fact_records) && card.aircraft_fact_records.length > 1) {
    return card.aircraft_fact_records.flatMap((record) => {
      const facts = parseAircraftFacts({
        ...card,
        front: record.id,
        back: record.back,
        card_type: "aircraft_designator",
        aircraft_fact_records: null,
      });
      return [
        [`${record.id} spoken name`, facts.spokenName],
        [`${record.id} manufacturer`, facts.manufacturer],
        [`${record.id} CWT`, facts.cwt],
        [`${record.id} SRS`, facts.srs],
        [`${record.id} wake`, facts.wake],
        [`${record.id} engine/class`, facts.engine],
        [`${record.id} LAHSO`, facts.lahso],
      ]
        .filter(([, value]) => value)
        .map(([label, value]) => ({ label, value }));
    });
  }

  const facts = parseAircraftFacts(card);
  return [
    [promptMode === "identifier" ? null : "Identifier", facts.identifier],
    [promptMode === "spoken" ? null : "Spoken name", facts.spokenName],
    ["Manufacturer", facts.manufacturer],
    ["Consolidated wake turbulence", facts.cwt],
    ["Same runway separation", facts.srs],
    ["Wake turbulence", facts.wake],
    ["Engine/class", facts.engine],
    ["LAHSO", facts.lahso],
  ]
    .filter(([label]) => label)
    .map(([label, value]) => ({
      label,
      value: value || AIRCRAFT_MISSING_FACT_TEXT,
      missing: !value,
    }));
}

function aircraftFlagPayload(card, promptMode) {
  const facts = parseAircraftFacts(card);
  return {
    activityId: `flashcard:${card?.id || `${facts.identifier}:${promptMode}`}`,
    activityType: "aircraft_flashcard",
    activityLabel: "Aircraft flashcard",
    paraId: card?.para_id || "JO 7360.1J",
    paraTitle: card?.para_title || "Aircraft Type Designators",
    itemText: `${promptMode}: ${promptMode === "spoken" ? facts.spokenName : promptMode === "image" ? card?.image_alt || "aircraft image" : facts.identifier}`,
    correctAnswer: [
      facts.identifier,
      facts.spokenName,
      facts.manufacturer ? `Mfr ${facts.manufacturer}` : null,
      facts.cwt ? `CWT ${facts.cwt}` : null,
      facts.srs ? `SRS ${facts.srs}` : null,
    ].filter(Boolean).join(" · "),
    explanation: "Aircraft recognition flashcard sourced from JO 7360.1J metadata.",
    sourceUrl: card?.source_url || null,
    flaggedAt: new Date().toISOString(),
  };
}

function aircraftCardIdentifiers(card) {
  const facts = parseAircraftFacts(card);
  const ids = String(facts.identifier || "")
    .split(";")
    .map((item) => cleanAircraftFact(item).toUpperCase())
    .filter(looksLikeAircraftIdentifier);
  return [...new Set(ids)];
}

function enrichAircraftCards(cards, allCards) {
  const designatorBackById = new Map();
  for (const card of allCards) {
    if (card?.card_type !== "aircraft_designator") continue;
    const facts = parseAircraftFacts(card);
    if (looksLikeAircraftIdentifier(facts.identifier)) {
      const key = facts.identifier.toUpperCase();
      const existing = designatorBackById.get(key);
      const candidate = {
        back: card.back,
        score: aircraftFactRichness(card),
      };
      if (!existing || candidate.score > existing.score) {
        designatorBackById.set(key, candidate);
      }
    }
  }

  const normalized = cards.flatMap((card) => {
    if (!isAircraftStudyCard(card) || card?.card_type === "aircraft_image") return card;
    const ids = aircraftCardIdentifiers(card);
    if (!ids.length) return card;
    const enrichedRecords = ids
      .map((id) => ({ id, back: designatorBackById.get(id)?.back }))
      .filter((record) => record.back);
    if (!enrichedRecords.length) return card;
    if (enrichedRecords.length > 1) {
      return enrichedRecords.map((record) => ({
        ...card,
        id: `${card.id || "aircraft"}:${record.id}`,
        front: record.id,
        back: record.back,
        card_type: "aircraft_designator",
        aircraft_full_facts: true,
        aircraft_fact_records: null,
        srs_drill: false,
      }));
    }
    const shouldReplaceBack = card?.card_type === "aircraft_srs";
    const enrichedBack = shouldReplaceBack && enrichedRecords.length === 1
      ? enrichedRecords[0].back
      : card.back;
    return {
      ...card,
      back: enrichedBack,
      aircraft_full_facts: true,
      aircraft_fact_records: enrichedRecords,
      srs_drill: card?.card_type === "aircraft_srs",
    };
  });

  const seen = new Set();
  return normalized.filter((card) => {
    if (!isAircraftStudyCard(card) || card?.card_type === "aircraft_image") return true;
    const facts = parseAircraftFacts(card);
    const ids = aircraftCardIdentifiers(card).join(";");
    const mode = card?.srs_drill || card?.card_type === "aircraft_srs" ? "srs" : "facts";
    const key = [
      mode,
      ids || facts.identifier,
      facts.spokenName,
      facts.manufacturer,
      facts.cwt,
      facts.srs,
      facts.wake,
      facts.engine,
      facts.lahso,
    ].join("|").toUpperCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function readInitialScreen() {
  const params = new URLSearchParams(window.location.search);
  return params.get("screen") === "review" ? "review" : "map";
}

function writeScreenToUrl(screen) {
  const url = new URL(window.location.href);
  if (screen === "review") url.searchParams.set("screen", "review");
  else url.searchParams.delete("screen");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// LOADING SCREEN
// ─────────────────────────────────────────────────────────────────────────────
function LoadingScreen() {
  return (
    <div style={{
      background: "#30302e",
      minHeight: "100vh",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 16,
      fontFamily: "'Share Tech Mono', ui-monospace, monospace",
    }}>
      <div style={{ fontSize: 32, color: "#d8a21c", letterSpacing: ".06em" }}>ATC 7110.65</div>
      <div style={{ display: "flex", gap: 6 }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 8, height: 8, borderRadius: 2, background: "#d8a21c",
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
      <style>{`@keyframes pulse{0%,100%{opacity:.2}50%{opacity:1}}`}</style>
      <div style={{ fontSize: 11, color: "#746f61", letterSpacing: ".08em" }}>
        Loading curriculum database…
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ERROR SCREEN
// ─────────────────────────────────────────────────────────────────────────────
function ErrorScreen({ error }) {
  return (
    <div style={{
      background: "#30302e",
      minHeight: "100vh", color: "#f1ead7",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: 32, gap: 16, textAlign: "center",
      fontFamily: "'Share Tech Mono', ui-monospace, monospace",
    }}>
      <div style={{ fontSize: 28, color: "#bd766c" }}>!</div>
      <div style={{ fontSize: 18, color: "#bd766c" }}>
        Could not load curriculum
      </div>
      <div style={{ fontSize: 13, color: "#b7ae95", maxWidth: 360, lineHeight: 1.6 }}>
        {error}
      </div>
      <div style={{
        background: "#11120e", border: "1px solid rgba(226,219,193,.22)", borderRadius: 2,
        padding: "12px 16px", fontSize: 12, color: "#b7ae95",
        textAlign: "left",
        lineHeight: 1.7,
      }}>
        Make sure curriculum.db is in the public/ directory<br />
        and the dev server is running.
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FLASHCARD DECK  (simple front/back flip mode)
// ─────────────────────────────────────────────────────────────────────────────
const FLASHCARD_DECK_CSS = `
.fc-deck{background:#30302e!important;color:#f1ead7!important;font-family:'Share Tech Mono',ui-monospace,monospace!important;}
.fc-deck *{font-family:'Share Tech Mono',ui-monospace,monospace!important;border-radius:2px!important;box-shadow:none!important}
.fc-deck img{border-radius:0!important}
.fc-deck button{letter-spacing:.08em}
@media (max-width: 520px){
  .fc-deck{overflow-x:hidden}
  .fc-header{padding:0 12px!important}
  .fc-back{min-width:44px!important;min-height:44px!important;display:inline-flex!important;align-items:center!important;justify-content:center!important}
  .fc-controls{padding:8px 12px 0!important}
  .fc-controls button{min-height:44px!important;font-size:12px!important;touch-action:manipulation}
  .fc-controls .fc-prev{margin-left:0!important}
  .fc-sub{padding:8px 12px 0!important;align-items:flex-start!important;flex-wrap:wrap}
  .fc-source-meta{margin-left:0!important;width:100%;justify-content:flex-start;flex-wrap:wrap}
  .fc-source-link{min-height:40px!important;display:inline-flex!important;align-items:center!important;padding:0 8px!important;margin-left:-8px}
  .fc-card-body{padding:12px!important}
  .fc-aircraft-fact{grid-template-columns:1fr!important;gap:5px!important}
  .fc-aircraft-rating{grid-template-columns:1fr 1fr!important}
  .fc-aircraft-rating button:last-child{grid-column:1 / -1}
  .fc-rating-row{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .fc-rating-row button{min-width:0;min-height:48px}
  .fc-aircraft-rating button{min-height:48px}
  .fc-rating-pad{padding-bottom:max(20px, env(safe-area-inset-bottom))!important}
}
`;

function FlashcardDeck({ cards, sectionLabel, onBack, initialOptions = {} }) {
  const [idx, setIdx]       = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [ratings, setRatings] = useState({});
  const [cardMemory, setCardMemory] = useState(loadFlashcardMemory);
  const [itemFlags, setItemFlags] = useState(loadItemFlags);
  const [orderMode, setOrderMode] = useState(initialOptions.order || "sequential");
  const [direction, setDirection] = useState(initialOptions.direction || "normal");
  const [aircraftPromptMode, setAircraftPromptMode] = useState(initialOptions.promptMode || "identifier");
  const [aircraftRevealedIndices, setAircraftRevealedIndices] = useState([]);
  const [deckCards, setDeckCards] = useState(() => (
    initialOptions.order === "shuffle" ? shuffleDeck(cards) : cards
  ));

  useEffect(() => {
    const nextOrder = initialOptions.order || "sequential";
    const nextDirection = initialOptions.direction || "normal";
    setOrderMode(nextOrder);
    setDirection(nextDirection);
    setAircraftPromptMode(initialOptions.promptMode || "identifier");
    setDeckCards(nextOrder === "shuffle" ? shuffleDeck(cards) : cards);
    setIdx(0);
    setFlipped(false);
    setAircraftRevealedIndices([]);
    setRatings({});
  }, [cards, initialOptions.order, initialOptions.direction, initialOptions.promptMode]);

  const card  = deckCards[idx];
  const total = deckCards.length;
  const isAircraftDeck = cards.some(isAircraftStudyCard);
  const isAircraftCard = isAircraftStudyCard(card);
  const aircraftFacts = isAircraftCard ? parseAircraftFacts(card) : null;
  const aircraftPrompts = isAircraftCard ? aircraftPromptOptions(card) : [];
  const activeAircraftPromptMode = isAircraftCard
    ? normalizeAircraftPromptMode(card, aircraftPromptMode)
    : aircraftPromptMode;
  const aircraftRevealSteps = isAircraftCard
    ? buildAircraftRevealSteps(card, activeAircraftPromptMode)
    : [];
  const aircraftRevealedSet = new Set(aircraftRevealedIndices);
  const aircraftRevealCount = aircraftRevealedSet.size;
  const aircraftAllRevealed = isAircraftCard && aircraftRevealSteps.length > 0 && aircraftRevealCount >= aircraftRevealSteps.length;
  const aircraftFlagKey = card?.id ? `flashcard:${card.id}` : null;
  const aircraftFlagged = aircraftFlagKey ? Boolean(itemFlags[aircraftFlagKey]) : false;
  const displayCard = useMemo(() => {
    if (!card || isAircraftStudyCard(card) || direction !== "reverse") return card;
    return {
      ...card,
      front: card.back,
      back: card.front,
    };
  }, [card, direction]);

  useEffect(() => {
    setFlipped(false);
    setAircraftRevealedIndices([]);
  }, [idx, activeAircraftPromptMode]);

  function resetDeck(nextOrder = orderMode, sourceCards = cards, keepRatings = false) {
    setDeckCards(nextOrder === "shuffle" ? shuffleDeck(sourceCards) : sourceCards);
    setOrderMode(nextOrder);
    setIdx(0);
    setFlipped(false);
    setAircraftRevealedIndices([]);
    if (!keepRatings) setRatings({});
  }

  function rate(r) {
    const reviewedAt = new Date().toISOString();
    const key = cardKey(card, idx);
    setRatings(prev => ({ ...prev, [key]: r }));
    if (card?.id) {
      setCardMemory((prev) => {
        const previous = prev[card.id] || {};
        const next = {
          ...prev,
          [card.id]: {
            cardId: card.id,
            paraId: card.para_id,
            rating: r,
            lastReviewedAt: reviewedAt,
            reviewCount: Number(previous.reviewCount || 0) + 1,
            againCount: Number(previous.againCount || 0) + (r === "again" ? 1 : 0),
          },
        };
        saveFlashcardMemory(next);
        return next;
      });
    }
    setFlipped(false);
    setAircraftRevealedIndices([]);
    setTimeout(() => setIdx(i => i + 1), 200);
  }

  function handleSkip() {
    setFlipped(false);
    setAircraftRevealedIndices([]);
    setIdx((i) => Math.min(i + 1, total));
  }

  function handlePrevious() {
    setFlipped(false);
    setAircraftRevealedIndices([]);
    setIdx((i) => Math.max(0, i - 1));
  }

  function handleReviewAgainOnly() {
    const againCards = deckCards.filter((item, index) => ratings[cardKey(item, index)] === "again");
    if (!againCards.length) return;
    resetDeck(orderMode, againCards, false);
  }

  function revealNextAircraftStep() {
    setAircraftRevealedIndices((current) => {
      const revealed = new Set(current);
      const nextIndex = aircraftRevealSteps.findIndex((_, index) => !revealed.has(index));
      if (nextIndex === -1) return current;
      return [...revealed, nextIndex].sort((a, b) => a - b);
    });
  }

  function revealAircraftStep(stepIndex) {
    setAircraftRevealedIndices((current) => {
      if (current.includes(stepIndex)) return current;
      return [...current, stepIndex].sort((a, b) => a - b);
    });
  }

  function cycleAircraftPrompt() {
    if (!aircraftPrompts.length) return;
    const index = aircraftPrompts.findIndex((option) => option.id === activeAircraftPromptMode);
    const next = aircraftPrompts[(index + 1) % aircraftPrompts.length];
    setAircraftPromptMode(next.id);
  }

  function toggleAircraftFlag() {
    if (!aircraftFlagKey || !card) return;
    setItemFlags((prev) => {
      const next = { ...prev };
      if (next[aircraftFlagKey]) delete next[aircraftFlagKey];
      else next[aircraftFlagKey] = aircraftFlagPayload(card, activeAircraftPromptMode);
      saveItemFlags(next);
      return next;
    });
  }

  const ratingCounts = Object.values(ratings).reduce((acc, rating) => {
    acc[rating] = (acc[rating] || 0) + 1;
    return acc;
  }, {});

  useEffect(() => {
    function handleKeyDown(event) {
      const tag = event.target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (event.key === "Escape") {
        event.preventDefault();
        onBack();
        return;
      }
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        if (isAircraftCard) revealNextAircraftStep();
        else if (!flipped) setFlipped(true);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        handleSkip();
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        handlePrevious();
        return;
      }
      if (isAircraftCard && event.key.toLowerCase() === "f") {
        event.preventDefault();
        toggleAircraftFlag();
        return;
      }
      if (isAircraftCard && aircraftAllRevealed && ["1", "2"].includes(event.key)) {
        event.preventDefault();
        rate(event.key === "1" ? "again" : "good");
        return;
      }
      if (!isAircraftCard && flipped && ["1", "2", "3", "4"].includes(event.key)) {
        event.preventDefault();
        const rating = { 1: "again", 2: "hard", 3: "good", 4: "easy" }[event.key];
        rate(rating);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [flipped, idx, onBack, total, isAircraftCard, aircraftAllRevealed, aircraftRevealSteps.length, aircraftFlagged]);

  if (idx >= total) {
    const correct = Object.values(ratings).filter(r => r === "good" || r === "easy").length;
    return (
      <div style={{
        background: "radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706",
        minHeight: "100vh", color: "#e4ece2",
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", padding: 24, gap: 16,
        fontFamily: "'Barlow', sans-serif",
      }}>
        <div style={{ fontSize: 44 }}>✓</div>
        <div style={{
          fontFamily: "'Barlow Condensed',sans-serif", fontSize: 22,
          fontWeight: 700, color: "#39c36f",
        }}>Deck complete</div>
        <div style={{ color: "#8c9c91", fontSize: 14 }}>
          {isAircraftDeck ? `${correct}/${total} marked right` : `${correct}/${total} marked good or easy`}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", marginTop: 12 }}>
          {(ratingCounts.again || 0) > 0 && (
            <button onClick={handleReviewAgainOnly} style={{
              background: "rgba(244,63,94,.14)", color: "#f43f5e", border: "1px solid rgba(244,63,94,.35)",
              borderRadius: 10, padding: "13px 22px", cursor: "pointer",
              fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
              fontSize: 14, letterSpacing: ".07em", textTransform: "uppercase",
            }}>Review again only</button>
          )}
          <button onClick={() => resetDeck(orderMode)} style={{
            background: "rgba(13,17,15,.92)", color: "#7aa7d9", border: "1px solid rgba(219,229,216,.13)",
            borderRadius: 10, padding: "13px 22px", cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
            fontSize: 14, letterSpacing: ".07em", textTransform: "uppercase",
          }}>Restart deck</button>
          <button onClick={onBack} style={{
            background: "#e0a30a", color: "#000", border: "none",
            borderRadius: 10, padding: "13px 28px", cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
            fontSize: 14, letterSpacing: ".07em", textTransform: "uppercase",
          }}>Back to map</button>
        </div>
      </div>
    );
  }
  const currentMemory = card?.id ? cardMemory[card.id] : null;

  return (
    <div className="fc-deck" style={{
      background: "radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706",
      minHeight: "100dvh", color: "#e4ece2",
      display: "flex", flexDirection: "column", fontFamily: "'Barlow', sans-serif",
    }}>
      <style>{FLASHCARD_DECK_CSS}</style>
      {/* Header */}
      <div className="fc-header" style={{
        padding: "0 20px", height: 52, display: "flex", alignItems: "center",
        gap: 10, borderBottom: "1px solid rgba(219,229,216,.13)",
      }}>
        <button className="fc-back" onClick={onBack} style={{
          background: "none", border: "none", color: "#8c9c91",
          fontSize: 18, cursor: "pointer", padding: "0 4px",
        }}>‹</button>
        <div style={{ flex: 1, height: 5, background: "rgba(219,229,216,.08)", borderRadius: 3, overflow: "hidden" }}>
          <div style={{
            height: "100%", background: "#e0a30a",
            width: `${(idx / total) * 100}%`, borderRadius: 3,
            transition: "width .4s ease",
          }} />
        </div>
        <span style={{
          fontFamily: "'Barlow Condensed',sans-serif", fontSize: 13,
          color: "#8c9c91",
        }}>{idx + 1}/{total}</span>
      </div>

      <div className="fc-controls" style={{
        padding: "8px 20px 0",
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        alignItems: "center",
      }}>
        {[
          { id: "sequential", label: "Order" },
          { id: "shuffle", label: "Shuffle" },
        ].map((item) => (
          <button key={item.id} onClick={() => resetDeck(item.id)} style={{
            height: 28,
            padding: "0 10px",
            borderRadius: 7,
            border: `1px solid ${orderMode === item.id ? "rgba(122,167,217,.45)" : "rgba(219,229,216,.14)"}`,
            background: orderMode === item.id ? "rgba(122,167,217,.12)" : "rgba(7,10,9,.62)",
            color: orderMode === item.id ? "#7aa7d9" : "#8c9c91",
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>{item.label}</button>
        ))}
        {isAircraftCard ? (
          <button onClick={cycleAircraftPrompt} style={{
            height: 28,
            padding: "0 10px",
            borderRadius: 7,
            border: "1px solid rgba(57,195,111,.42)",
            background: "rgba(57,195,111,.1)",
            color: "#39c36f",
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>Prompt: {aircraftPrompts.find((option) => option.id === activeAircraftPromptMode)?.label || "Aircraft"}</button>
        ) : (
          <button onClick={() => {
            setDirection((current) => current === "reverse" ? "normal" : "reverse");
            setFlipped(false);
          }} style={{
            height: 28,
            padding: "0 10px",
            borderRadius: 7,
            border: `1px solid ${direction === "reverse" ? "rgba(57,195,111,.42)" : "rgba(219,229,216,.14)"}`,
            background: direction === "reverse" ? "rgba(57,195,111,.1)" : "rgba(7,10,9,.62)",
            color: direction === "reverse" ? "#39c36f" : "#8c9c91",
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>Reverse</button>
        )}
        <button className="fc-prev" onClick={handlePrevious} disabled={idx === 0} style={{
          height: 28,
          padding: "0 10px",
          borderRadius: 7,
          border: "1px solid rgba(219,229,216,.14)",
          background: "rgba(7,10,9,.62)",
          color: idx === 0 ? "#27302a" : "#8c9c91",
          cursor: idx === 0 ? "default" : "pointer",
          fontFamily: "'Barlow Condensed',sans-serif",
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: ".08em",
          textTransform: "uppercase",
          marginLeft: "auto",
        }}>Previous</button>
        <button onClick={handleSkip} style={{
          height: 28,
          padding: "0 10px",
          borderRadius: 7,
          border: "1px solid rgba(219,229,216,.14)",
          background: "rgba(7,10,9,.62)",
          color: "#8c9c91",
          cursor: "pointer",
          fontFamily: "'Barlow Condensed',sans-serif",
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: ".08em",
          textTransform: "uppercase",
        }}>Skip</button>
      </div>

      {/* Sub-header */}
      <div className="fc-sub" style={{ padding: "8px 20px 0", display: "flex", gap: 8, alignItems: "center" }}>
        <span style={{
          fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10, fontWeight: 700,
          letterSpacing: ".1em", textTransform: "uppercase", padding: "3px 9px",
          borderRadius: 4, background: "rgba(224,163,10,.1)", color: "#e0a30a",
          border: "1px solid rgba(224,163,10,.28)",
        }}>{isAircraftCard ? "Aircraft Cards" : "Flashcards"}</span>
        <span style={{
          fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
          color: "#536157", letterSpacing: ".08em", textTransform: "uppercase",
        }}>
          {isAircraftDeck
            ? `${Object.keys(ratings).length} reviewed · ${ratingCounts.again || 0} wrong · ${(ratingCounts.good || 0) + (ratingCounts.easy || 0)} right`
            : `${Object.keys(ratings).length} reviewed · ${ratingCounts.again || 0} again · ${(ratingCounts.good || 0) + (ratingCounts.easy || 0)} solid`}
        </span>
        {currentMemory && (
          <span style={{
            fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
            color: currentMemory.rating === "again" ? "#ef476f" : "#8c9c91",
            letterSpacing: ".08em", textTransform: "uppercase",
          }}>
            Last: {currentMemory.rating} · {currentMemory.reviewCount}x
          </span>
        )}
        <span className="fc-source-meta" style={{
          fontFamily: "'Barlow Condensed',sans-serif", fontSize: 11,
          color: "#8c9c91", marginLeft: "auto",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span>§ {displayCard?.para_id}</span>
          {displayCard?.source_url && (
            <a
              className="fc-source-link"
              href={displayCard.source_url}
              target="_blank"
              rel="noreferrer"
              style={{
                color: "#e0a30a",
                textDecoration: "none",
                fontWeight: 700,
                letterSpacing: ".04em",
              }}
            >
              {displayCard.source_label?.startsWith("FAA JO 7360") ? "JO 7360.1J ↗" : "FAA Source ↗"}
            </a>
          )}
        </span>
      </div>

      {/* Card */}
      <div className="fc-card-body" style={{ flex: 1, padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        {isAircraftCard ? (
          <>
            <div style={{
              background: "rgba(17,22,20,.92)",
              border: "1px solid rgba(219,229,216,.14)",
              borderRadius: 8,
              padding: activeAircraftPromptMode === "image" ? 8 : "20px 18px",
              color: "#e4ece2",
            }}>
              {activeAircraftPromptMode === "image" && displayCard?.image_public_path ? (
                <img
                  src={displayCard.image_public_path}
                  alt={displayCard.image_alt || "Aircraft image"}
                  style={{
                    width: "100%",
                    maxHeight: "52vh",
                    objectFit: "contain",
                    borderRadius: 8,
                    background: "rgba(7,10,9,.62)",
                    display: "block",
                  }}
                />
              ) : (
                <>
                  <div style={{
                    fontFamily: "'Barlow Condensed',sans-serif",
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: ".09em",
                    textTransform: "uppercase",
                    color: "#7aa7d9",
                    marginBottom: 8,
                  }}>
                    Starting prompt · {aircraftPrompts.find((option) => option.id === activeAircraftPromptMode)?.label || "Aircraft"}
                  </div>
                  <div style={{
                    fontFamily: activeAircraftPromptMode === "identifier" ? "'Share Tech Mono',monospace" : "'Barlow',sans-serif",
                    fontSize: activeAircraftPromptMode === "identifier" ? 42 : 26,
                    lineHeight: 1.15,
                    color: "#f4f8f2",
                    letterSpacing: activeAircraftPromptMode === "identifier" ? ".04em" : 0,
                  }}>
                    {activeAircraftPromptMode === "spoken" ? aircraftFacts?.spokenName : aircraftFacts?.identifier}
                  </div>
                </>
              )}
            </div>

            <button
              onClick={revealNextAircraftStep}
              disabled={aircraftAllRevealed}
              style={{
                background: aircraftAllRevealed ? "rgba(57,195,111,.09)" : "rgba(7,10,9,.62)",
                border: `1px ${aircraftAllRevealed ? "solid" : "dashed"} ${aircraftAllRevealed ? "rgba(57,195,111,.3)" : "rgba(219,229,216,.18)"}`,
                borderRadius: 8,
                padding: "13px 14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                cursor: aircraftAllRevealed ? "default" : "pointer",
                color: aircraftAllRevealed ? "#39c36f" : "#536157",
                fontFamily: "'Barlow Condensed',sans-serif",
                fontSize: 12,
                letterSpacing: ".05em",
                textTransform: "uppercase",
              }}
            >
              {aircraftAllRevealed
                ? "All facts revealed"
                : `Reveal next: ${aircraftRevealSteps.find((_, index) => !aircraftRevealedSet.has(index))?.label || "fact"} (${aircraftRevealCount}/${aircraftRevealSteps.length})`}
              {!aircraftAllRevealed && <span style={{ color: "#27302a" }}>Space / Enter</span>}
            </button>

            <div style={{ display: "grid", gap: 8 }}>
              {aircraftRevealSteps.map((step, stepIndex) => {
                const revealed = aircraftRevealedSet.has(stepIndex);
                return (
                <button className="fc-aircraft-fact" key={`${step.label}-${stepIndex}`} onClick={() => revealAircraftStep(stepIndex)} style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(110px, 170px) 1fr",
                  gap: 12,
                  alignItems: "start",
                  textAlign: "left",
                  background: revealed
                    ? (step.missing ? "rgba(224,163,10,.07)" : "rgba(57,195,111,.08)")
                    : "rgba(7,10,9,.62)",
                  border: `1px solid ${revealed ? (step.missing ? "rgba(224,163,10,.22)" : "rgba(57,195,111,.24)") : "rgba(219,229,216,.13)"}`,
                  borderRadius: 8,
                  padding: "11px 12px",
                  cursor: revealed ? "default" : "pointer",
                }}>
                  <div style={{
                    fontFamily: "'Barlow Condensed',sans-serif",
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: ".08em",
                    textTransform: "uppercase",
                    color: revealed ? (step.missing ? "#e0a30a" : "#39c36f") : "#7aa7d9",
                  }}>{step.label}</div>
                  <div style={{
                    fontFamily: "'Share Tech Mono',monospace",
                    fontSize: 13,
                    color: revealed ? (step.missing ? "#8c9c91" : "#e4ece2") : "#8c9c91",
                    lineHeight: 1.45,
                  }}>{revealed ? step.value : `Tap to reveal ${step.label.toLowerCase()}`}</div>
                </button>
              );
              })}
            </div>
          </>
        ) : (
          <>
            {/* Front */}
            <div style={{
              background: "rgba(17,22,20,.92)", border: "1px solid rgba(219,229,216,.14)", borderRadius: 8,
              padding: displayCard?.image_public_path ? 8 : 16,
              fontSize: 14, lineHeight: 1.55, color: "#e4ece2",
              fontWeight: 500,
            }}>
              {displayCard?.image_public_path && (
                <img
                  src={displayCard.image_public_path}
                  alt={displayCard.image_alt || "Aircraft image"}
                  style={{
                    width: "100%",
                    maxHeight: "52vh",
                    objectFit: "contain",
                    borderRadius: 8,
                    background: "rgba(7,10,9,.62)",
                    display: "block",
                    marginBottom: 10,
                  }}
                />
              )}
              <div style={{ padding: displayCard?.image_public_path ? "0 8px 6px" : 0 }}>
                {displayCard?.front}
              </div>
            </div>

            {/* Back (tap to reveal) */}
            {!flipped ? (
              <div
                onClick={() => setFlipped(true)}
                style={{
                  background: "rgba(7,10,9,.62)", border: "1px dashed rgba(219,229,216,.18)", borderRadius: 8,
                  padding: "14px", display: "flex", alignItems: "center", justifyContent: "center",
                  gap: 8, cursor: "pointer", color: "#536157",
                  fontFamily: "'Barlow Condensed',sans-serif", fontSize: 12, letterSpacing: ".05em",
                  textTransform: "uppercase",
                }}
              >
                <span>Tap to reveal answer</span>
                <span style={{ color: "#27302a" }}>Space / Enter</span>
              </div>
            ) : (
              <div style={{
                background: "rgba(57,195,111,.08)", border: "1px solid rgba(57,195,111,.26)",
                borderRadius: 8, padding: "14px",
              }}>
                <div style={{
                  fontFamily: "'Share Tech Mono', monospace", fontSize: 13,
                  color: "#e4ece2", lineHeight: 1.65, whiteSpace: "pre-wrap",
                }}>
                  {displayCard?.back}
                </div>
              </div>
            )}
          </>
        )}

        {displayCard?.source_url && (
          <SourceCitation source={displayCard} compact />
        )}
      </div>

      {/* Rating buttons */}
      {isAircraftCard && aircraftAllRevealed && (
        <div className="fc-rating-pad" style={{ padding: "8px 20px 20px" }}>
          <div className="fc-aircraft-rating" style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 8 }}>
            <button onClick={() => rate("again")} style={{
              height: 46,
              background: "rgba(244,63,94,.14)",
              border: "1.5px solid rgba(244,63,94,.4)",
              borderRadius: 8,
              color: "#f43f5e",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 12,
              letterSpacing: ".06em",
              textTransform: "uppercase",
              cursor: "pointer",
            }}>1 · Wrong</button>
            <button onClick={() => rate("good")} style={{
              height: 46,
              background: "rgba(57,195,111,.14)",
              border: "1.5px solid rgba(57,195,111,.42)",
              borderRadius: 8,
              color: "#39c36f",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 12,
              letterSpacing: ".06em",
              textTransform: "uppercase",
              cursor: "pointer",
            }}>2 · Right</button>
            <button onClick={toggleAircraftFlag} style={{
              height: 46,
              minWidth: 86,
              background: aircraftFlagged ? "rgba(224,163,10,.16)" : "rgba(122,167,217,.1)",
              border: `1.5px solid ${aircraftFlagged ? "rgba(224,163,10,.45)" : "rgba(122,167,217,.28)"}`,
              borderRadius: 8,
              color: aircraftFlagged ? "#e0a30a" : "#7aa7d9",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 12,
              letterSpacing: ".06em",
              textTransform: "uppercase",
              cursor: "pointer",
            }}>{aircraftFlagged ? "Flagged" : "F · Flag"}</button>
          </div>
          <div style={{
            marginTop: 8,
            textAlign: "center",
            fontSize: 11,
            color: "#27302a",
          }}>
            Space reveals facts. 1 marks wrong. 2 marks right. F flags for review.
          </div>
        </div>
      )}
      {!isAircraftCard && flipped && (
        <div className="fc-rating-pad" style={{ padding: "8px 20px 20px" }}>
          <div className="fc-rating-row" style={{ display: "flex", gap: 8 }}>
          {[
            { r: "again",  label: "Again",  color: "#f43f5e", key: "1" },
            { r: "hard",   label: "Hard",   color: "#f97316", key: "2" },
            { r: "good",   label: "Good",   color: "#39c36f", key: "3" },
            { r: "easy",   label: "Easy",   color: "#e0a30a", key: "4" },
          ].map(({ r, label, color, key }) => (
            <button key={r} onClick={() => rate(r)} style={{
              flex: 1, height: 44, background: `${color}14`, border: `1.5px solid ${color}40`,
              borderRadius: 8, color, fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700, fontSize: 12, letterSpacing: ".05em",
              textTransform: "uppercase", cursor: "pointer",
            }}>{key} · {label}</button>
          ))}
          </div>
          <div style={{
            marginTop: 8,
            textAlign: "center",
            fontSize: 11,
            color: "#27302a",
          }}>
            Space reveals. 1-4 rates. Esc returns to the map.
          </div>
        </div>
      )}
    </div>
  );
}

function AircraftImageReview({ images = [], reviewState = {}, onSetStatus, onBack }) {
  const [exportMessage, setExportMessage] = useState("");
  const reviewedCount = images.filter((image) => imageReviewStatus(image, reviewState) !== "not_reviewed").length;
  const approvedCount = images.filter((image) => imageReviewStatus(image, reviewState) === "approved").length;
  const buttonStyle = (color) => ({
    height: 34,
    borderRadius: 8,
    border: `1px solid ${color}55`,
    background: `${color}18`,
    color,
    cursor: "pointer",
    padding: "0 10px",
    fontFamily: "'Barlow Condensed',sans-serif",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: ".07em",
    textTransform: "uppercase",
  });
  const exportReviewPayload = () => ({
    version: 1,
    exported_at: new Date().toISOString(),
    storage_key: AIRCRAFT_IMAGE_REVIEW_KEY,
    summary: {
      candidates: images.length,
      reviewed: reviewedCount,
      approved: approvedCount,
    },
    decisions: reviewState,
    candidates: images.map((image) => ({
      key: aircraftImageKey(image),
      type_designator: image.type_designator,
      aircraft_group: image.aircraft_group,
      manufacturer_model: image.manufacturer_model,
      file_title: image.file_title,
      source_page: image.source_page,
      public_path: image.public_path,
      license_short_name: image.license_short_name,
      status: imageReviewStatus(image, reviewState),
    })),
  });
  const handleCopyReview = async () => {
    const text = JSON.stringify(exportReviewPayload(), null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setExportMessage("Copied review JSON.");
    } catch {
      setExportMessage("Clipboard blocked; use Download Review instead.");
    }
  };
  const handleDownloadReview = () => {
    const blob = new Blob([JSON.stringify(exportReviewPayload(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aircraft-image-review.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setExportMessage("Downloaded aircraft-image-review.json.");
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706",
      color: "#e4ece2",
      fontFamily: "'Barlow',sans-serif",
      padding: "18px 20px 28px",
    }}>
      <div style={{ maxWidth: 1120, margin: "0 auto" }}>
        <button
          onClick={onBack}
          style={{
            background: "none",
            border: "none",
            color: "#8c9c91",
            cursor: "pointer",
            padding: 0,
            marginBottom: 12,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}
        >
          ‹ Back
        </button>
        <div style={{
          background: "linear-gradient(135deg, rgba(122,167,217,.12), rgba(13,17,15,.92))",
          border: "1px solid rgba(219,229,216,.13)",
          borderRadius: 14,
          padding: 16,
          marginBottom: 14,
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 26,
            fontWeight: 700,
            color: "#e0a30a",
            letterSpacing: ".04em",
          }}>
            Aircraft Image Review
          </div>
          <div style={{ marginTop: 6, color: "#8c9c91", fontSize: 13, lineHeight: 1.6 }}>
            Review downloaded image candidates before they become learner-facing image cards. Only `approved` images appear in Aircraft Recognition study.
          </div>
          <div style={{
            marginTop: 12,
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            alignItems: "center",
            flexWrap: "wrap",
          }}>
            <div style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontSize: 11,
              color: "#8c9c91",
              letterSpacing: ".08em",
              textTransform: "uppercase",
            }}>
              {images.length} candidates · {reviewedCount} reviewed · {approvedCount} approved
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              {exportMessage && (
                <span style={{
                  color: "#8c9c91",
                  fontSize: 12,
                }}>
                  {exportMessage}
                </span>
              )}
              <button onClick={handleCopyReview} style={buttonStyle("#7aa7d9")}>Copy Review JSON</button>
              <button onClick={handleDownloadReview} style={buttonStyle("#e0a30a")}>Download Review</button>
            </div>
          </div>
        </div>

        {images.length === 0 ? (
          <div style={{
            background: "rgba(13,17,15,.92)",
            border: "1px solid rgba(219,229,216,.13)",
            borderRadius: 12,
            padding: 24,
            color: "#8c9c91",
            fontSize: 13,
            lineHeight: 1.7,
          }}>
            No image manifest rows found. Run `python3 scripts/collect_aircraft_images.py --types BE20 --per-type 1` to collect candidates.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 12 }}>
            {images.map((image) => {
              const key = aircraftImageKey(image);
              const status = imageReviewStatus(image, reviewState);
              return (
                <div key={key} style={{
                  background: "rgba(13,17,15,.92)",
                  border: `1px solid ${status === "approved" ? "rgba(57,195,111,.42)" : "rgba(219,229,216,.13)"}`,
                  borderRadius: 12,
                  overflow: "hidden",
                }}>
                  {image.public_path && (
                    <img
                      src={image.public_path}
                      alt={`${image.type_designator} candidate`}
                      style={{ width: "100%", height: 210, objectFit: "cover", background: "rgba(7,10,9,.62)", display: "block" }}
                    />
                  )}
                  <div style={{ padding: 12 }}>
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 8,
                      alignItems: "flex-start",
                      marginBottom: 8,
                    }}>
                      <div>
                        <div style={{
                          fontFamily: "'Barlow Condensed',sans-serif",
                          fontSize: 20,
                          fontWeight: 700,
                          color: "#e4ece2",
                          letterSpacing: ".04em",
                        }}>
                          {image.type_designator}
                        </div>
                        <div style={{ color: "#8c9c91", fontSize: 12, lineHeight: 1.4 }}>
                          {image.aircraft_group} · {image.license_short_name || "license metadata"}
                          {" · "}
                          {image.status === "metadata_only" ? "remote thumbnail" : "local file"}
                        </div>
                      </div>
                      <span style={{
                        borderRadius: 999,
                        padding: "4px 8px",
                        background: status === "approved" ? "rgba(57,195,111,.14)" : "rgba(122,167,217,.11)",
                        border: `1px solid ${status === "approved" ? "rgba(57,195,111,.35)" : "rgba(122,167,217,.25)"}`,
                        color: status === "approved" ? "#39c36f" : "#7aa7d9",
                        fontFamily: "'Barlow Condensed',sans-serif",
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: ".08em",
                        textTransform: "uppercase",
                      }}>
                        {status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <div style={{
                      color: "#8c9c91",
                      fontSize: 12,
                      lineHeight: 1.5,
                      maxHeight: 74,
                      overflow: "auto",
                      marginBottom: 10,
                    }}>
                      {image.manufacturer_model}
                    </div>
                    <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 10 }}>
                      <button onClick={() => onSetStatus(key, "approved")} style={buttonStyle("#39c36f")}>Approve</button>
                      <button onClick={() => onSetStatus(key, "wrong_aircraft")} style={buttonStyle("#f43f5e")}>Wrong Aircraft</button>
                      <button
                        onClick={() => onSetStatus(key, "not_recognition_image")}
                        title="This is not a useful exterior aircraft-recognition image, such as a cockpit, logo, detail, cabin, or ambiguous multi-aircraft scene."
                        style={buttonStyle("#fb7185")}
                      >
                        Not Recognition
                      </button>
                      <button onClick={() => onSetStatus(key, "bad_angle")} style={buttonStyle("#f97316")}>Bad Angle</button>
                      <button
                        onClick={() => onSetStatus(key, "bad_crop")}
                        title="The source image is usable, but the platform's displayed crop/framing makes it suboptimal."
                        style={buttonStyle("#e0a30a")}
                      >
                        Bad App Crop
                      </button>
                      <button onClick={() => onSetStatus(key, "license_hold")} style={buttonStyle("#818cf8")}>License Hold</button>
                    </div>
                    {image.source_page && (
                      <a
                        href={image.source_page}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          color: "#e0a30a",
                          fontFamily: "'Barlow Condensed',sans-serif",
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: ".08em",
                          textTransform: "uppercase",
                          textDecoration: "none",
                        }}
                      >
                        Open Source Page ↗
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSION RESULTS
// ─────────────────────────────────────────────────────────────────────────────
function suggestedModeForResults(results = []) {
  const missedTypes = results
    .filter((result) => !result.correct)
    .map((result) => result.activityType);
  if (!missedTypes.length) return null;

  const hasAny = (types) => missedTypes.some((type) => types.includes(type));
  if (hasAny(["table_lookup", "minima_rule_check"])) {
    return { id: "tables_minima", label: "Tables & Minima", count: 6 };
  }
  if (hasAny(["phraseology_builder", "readback_check", "spot_the_error", "example_check"])) {
    return { id: "phraseology", label: "Phraseology", count: 6 };
  }
  if (hasAny(["visual_interpretation"])) {
    return { id: "visuals", label: "Figures & Visuals", count: 4 };
  }
  if (hasAny(["situation_action", "conditional_rule_check", "capability_check", "requirement_check"])) {
    return { id: "scenarios", label: "Scenario Judgment", count: 6 };
  }
  return { id: "weak_areas", label: "Weak Areas", count: 6 };
}

function humanizeActivityType(type) {
  return String(type || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function resolveNextAction({
  mistakeQueue = [],
  dueReviewQueue = [],
  conceptQueue = [],
  practiceQueue = [],
}) {
  if (mistakeQueue.length > 0) {
    return {
      type: "missed_items",
      label: "Retry missed items",
      detail: "Start with exact activities you recently missed. Correct answers clear them from the queue.",
      reason: `${mistakeQueue.length} missed item${mistakeQueue.length === 1 ? "" : "s"} waiting`,
      buttonLabel: "Review misses",
      count: 6,
      color: "#f43f5e",
    };
  }

  if (dueReviewQueue.length > 0) {
    return {
      type: "due_review",
      label: "Refresh due material",
      detail: "Review material that is aging out or showing weaker recent accuracy.",
      reason: `${dueReviewQueue.length} paragraph${dueReviewQueue.length === 1 ? "" : "s"} due`,
      buttonLabel: "Refresh",
      count: 8,
      color: "#7aa7d9",
    };
  }

  if (conceptQueue.length > 0) {
    const conceptIds = conceptQueue.slice(0, 3).map((item) => item.id);
    const conceptNames = conceptQueue.slice(0, 2).map((item) => item.label).join(" and ");
    return {
      type: "concept_review",
      label: "Drill weak concepts",
      detail: `Practice grouped around ${conceptNames || "recently missed concepts"}, across sections where possible.`,
      reason: `${conceptQueue.length} weak concept${conceptQueue.length === 1 ? "" : "s"} detected`,
      buttonLabel: "Drill concepts",
      concept_ids: conceptIds,
      count: 6,
      color: "#39c36f",
    };
  }

  if (practiceQueue.length > 0) {
    return {
      type: "recommended",
      label: "Continue targeted practice",
      detail: "Work through low-crown and low-confidence paragraphs in 7110 order.",
      reason: `${practiceQueue.length} targeted paragraph${practiceQueue.length === 1 ? "" : "s"} ready`,
      buttonLabel: "Practice",
      color: "#e0a30a",
    };
  }

  return {
    type: "practice_mode",
    mode_id: "diagnostic",
    label: "Run a diagnostic",
    detail: "Take a mixed check so the platform can identify what needs work next.",
    reason: "No active misses or due review",
    buttonLabel: "Start diagnostic",
    count: 10,
    color: "#7aa7d9",
  };
}

function buildStudyPlan({
  nextAction,
  mistakeQueue = [],
  dueReviewQueue = [],
  conceptQueue = [],
  practiceQueue = [],
}) {
  const plan = [];
  if (nextAction) {
    plan.push({
      key: "primary",
      label: nextAction.label,
      detail: nextAction.reason,
      color: nextAction.color,
    });
  }
  if (mistakeQueue.length > 0 && nextAction?.type !== "missed_items") {
    plan.push({
      key: "missed",
      label: "Clean up misses",
      detail: `${mistakeQueue.length} exact retr${mistakeQueue.length === 1 ? "y" : "ies"}`,
      color: "#f43f5e",
    });
  }
  if (dueReviewQueue.length > 0 && nextAction?.type !== "due_review") {
    plan.push({
      key: "due",
      label: "Refresh due review",
      detail: `${dueReviewQueue.length} paragraph${dueReviewQueue.length === 1 ? "" : "s"}`,
      color: "#7aa7d9",
    });
  }
  if (conceptQueue.length > 0 && nextAction?.type !== "concept_review") {
    plan.push({
      key: "concepts",
      label: "Drill weak concepts",
      detail: conceptQueue.slice(0, 2).map((item) => item.label).join(" / "),
      color: "#39c36f",
    });
  }
  if (practiceQueue.length > 0 && plan.length < 3) {
    plan.push({
      key: "targeted",
      label: "Continue 7110-order practice",
      detail: `${practiceQueue.length} targeted paragraph${practiceQueue.length === 1 ? "" : "s"}`,
      color: "#e0a30a",
    });
  }
  return plan.slice(0, 3);
}

function sessionMetaForTarget(target = {}) {
  if (target.type === "missed_items") {
    return {
      title: "Missed Item Review",
      reason: "Retry exact activities you missed recently. Correct answers remove them from the missed queue.",
      mode: "Remediation",
    };
  }
  if (target.type === "due_review") {
    return {
      title: "Due Review",
      reason: "Refresh material that is aging out or showing weaker recent accuracy.",
      mode: "Spaced Review",
    };
  }
  if (target.type === "concept_review") {
    return {
      title: target.label || "Concept Drill",
      reason: "Practice grouped by concept so the same operating idea is tested across different paragraphs.",
      mode: "Concept Drill",
    };
  }
  if (target.type === "practice_mode") {
    return {
      title: target.label || "Practice Mode",
      reason: "Targeted activity selection for a specific skill family instead of a section-by-section pass.",
      mode: "Skill Focus",
    };
  }
  if (target.type === "focus_list") {
    return {
      title: "Focus List",
      reason: "Material you manually marked for extra attention.",
      mode: "Manual Focus",
    };
  }
  if (target.type === "recommended") {
    return {
      title: "Recommended Practice",
      reason: "Adaptive practice from low-crown, low-confidence, or unstudied material in 7110 order.",
      mode: "Adaptive",
    };
  }
  if (target.para_id) {
    return {
      title: `§ ${target.para_id}`,
      reason: target.title || "Paragraph-specific practice.",
      mode: "Paragraph",
    };
  }
  if (target.label) {
    return {
      title: target.label,
      reason: "Adaptive mix of activities and quiz questions, weighted toward weak, new, and under-practiced paragraph areas.",
      mode: "Section",
    };
  }
  return {
    title: "Lesson",
    reason: "Answer each prompt by applying the rule, not merely recognizing wording.",
    mode: "Practice",
  };
}

function SessionResults({
  results,
  crownChanges,
  missedConcepts = [],
  onHome,
  onRepeat,
  onReviewMissedItems,
  onSaveMissedToFocus,
  onReviewMissedConcepts,
  onStartPracticeMode,
}) {
  const [savedFocusCount, setSavedFocusCount] = useState(null);
  const total   = results.length;
  const correct = results.filter(r => r.correct).length;
  const pct     = total ? Math.round(correct / total * 100) : 0;
  const suggestedMode = suggestedModeForResults(results);
  const missedItems = results.filter((result) => !result.correct);
  const typeStats = Object.values(results.reduce((acc, result) => {
    const key = result.activityType || "unknown";
    if (!acc[key]) {
      acc[key] = {
        type: key,
        label: result.activityLabel || humanizeActivityType(key),
        total: 0,
        correct: 0,
      };
    }
    acc[key].total += 1;
    if (result.correct) acc[key].correct += 1;
    return acc;
  }, {})).sort((a, b) => (
    (a.correct / a.total) - (b.correct / b.total)
    || b.total - a.total
    || a.label.localeCompare(b.label)
  ));

  return (
    <div style={{
      background: "radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706",
      minHeight: "100vh", color: "#e4ece2",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "32px 24px", gap: 18,
      fontFamily: "'Barlow', sans-serif",
    }}>
      <div style={{ fontSize: 52 }}>{pct >= 80 ? "🎯" : pct >= 50 ? "✈️" : "📡"}</div>
      <div style={{ textAlign: "center" }}>
        <div style={{
          fontFamily: "'Barlow Condensed',sans-serif", fontSize: 26,
          fontWeight: 700, letterSpacing: ".05em", color: "#e0a30a",
        }}>
          {pct >= 80 ? "Outstanding" : pct >= 60 ? "Good work" : "Keep studying"}
        </div>
        <div style={{ fontSize: 14, color: "#8c9c91", marginTop: 6 }}>
          {correct}/{total} correct · {pct}%
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: "flex", gap: 14 }}>
        {[
          { n: correct, label: "Correct", color: "#39c36f" },
          { n: total - correct, label: "Mistakes", color: "#f43f5e" },
          { n: total, label: "Items", color: "#e0a30a" },
        ].map(({ n, label, color }) => (
          <div key={label} style={{
            background: "rgba(17,22,20,.92)", border: "1px solid rgba(219,229,216,.13)",
            borderRadius: 10, padding: "13px 18px", minWidth: 85, textAlign: "center",
          }}>
            <div style={{ fontFamily: "'Barlow Condensed',sans-serif", fontSize: 22, fontWeight: 700, color }}>{n}</div>
            <div style={{ fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10, color: "#536157", letterSpacing: ".08em", textTransform: "uppercase", marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Crown changes */}
      {crownChanges?.length > 0 && (
        <div style={{
          background: "rgba(17,22,20,.92)", border: "1px solid rgba(219,229,216,.13)", borderRadius: 10,
          padding: "13px 16px", width: "100%",
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
            color: "#536157", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 9,
          }}>Crown progress</div>
          {crownChanges.map((cc, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 9, fontSize: 12, padding: "2px 0" }}>
              <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontSize: 11, color: "#536157" }}>{cc.paraId}</span>
              <span style={{ color: CROWN_COLORS[cc.oldCrown] }}>{CROWN_ICONS[cc.oldCrown]}</span>
              <span style={{ color: "#27302a" }}>→</span>
              <span style={{ color: CROWN_COLORS[cc.newCrown], fontWeight: 600 }}>{CROWN_ICONS[cc.newCrown]}</span>
              <span style={{ fontSize: 11, color: cc.regressed ? "#f43f5e" : "#536157", marginLeft: 4 }}>
                {cc.regressed ? `Level ${cc.newCrown}: needs review` : `Level ${cc.newCrown} unlocked`}
              </span>
            </div>
          ))}
        </div>
      )}

      {missedConcepts.length > 0 && (
        <div style={{
          background: "rgba(17,22,20,.92)", border: "1px solid rgba(219,229,216,.13)", borderRadius: 10,
          padding: "13px 16px", width: "100%",
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
            color: "#536157", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 9,
          }}>Missed concepts</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {missedConcepts.map((concept) => (
              <span key={concept.id} style={{
                border: "1px solid rgba(224,163,10,.28)",
                background: "rgba(224,163,10,.1)",
                color: "#e0a30a",
                borderRadius: 999,
                padding: "5px 9px",
                fontFamily: "'Barlow Condensed',sans-serif",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: ".06em",
                textTransform: "uppercase",
              }}>
                {concept.label}
              </span>
            ))}
          </div>
        </div>
      )}

      {missedItems.length > 0 && (
        <div style={{
          background: "rgba(17,22,20,.92)", border: "1px solid rgba(244,63,94,.28)", borderRadius: 10,
          padding: "13px 16px", width: "100%",
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
            color: "#f43f5e", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 9,
          }}>Missed items</div>
          <div style={{ display: "grid", gap: 7 }}>
            {missedItems.slice(0, 5).map((item) => (
              <div key={item.activityId || `${item.paraId}-${item.activityType}`} style={{
                display: "grid",
                gridTemplateColumns: "80px minmax(0,1fr) auto",
                alignItems: "center",
                gap: 8,
                padding: "8px 10px",
                borderRadius: 8,
                background: "rgba(13,17,15,.92)",
                border: "1px solid rgba(219,229,216,.13)",
              }}>
                <div style={{
                  fontFamily: "'Barlow Condensed',sans-serif",
                  fontWeight: 700,
                  color: "#e4ece2",
                  letterSpacing: ".04em",
                }}>
                  § {item.paraId}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{
                    color: "#e4ece2",
                    fontSize: 13,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}>
                    {item.paraTitle || item.activityLabel || item.activityType}
                  </div>
                  <div style={{ color: "#8c9c91", fontSize: 11, marginTop: 2 }}>
                    {item.activityLabel || item.activityType}
                  </div>
                </div>
                {item.source_url && (
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: "#e0a30a",
                      textDecoration: "none",
                      fontFamily: "'Barlow Condensed',sans-serif",
                      fontWeight: 700,
                      fontSize: 10,
                      letterSpacing: ".07em",
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Source ↗
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {typeStats.length > 1 && (
        <div style={{
          background: "rgba(17,22,20,.92)", border: "1px solid rgba(219,229,216,.13)", borderRadius: 10,
          padding: "13px 16px", width: "100%",
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
            color: "#536157", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 9,
          }}>Activity mix</div>
          <div style={{ display: "grid", gap: 7 }}>
            {typeStats.slice(0, 5).map((stat) => {
              const rate = stat.total ? stat.correct / stat.total : 0;
              const color = rate >= 0.8 ? "#39c36f" : rate >= 0.5 ? "#e0a30a" : "#f43f5e";
              return (
                <div key={stat.type} style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(0,1fr) 56px",
                  alignItems: "center",
                  gap: 10,
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 8,
                      marginBottom: 4,
                    }}>
                      <span style={{
                        color: "#e4ece2",
                        fontFamily: "'Barlow Condensed',sans-serif",
                        fontSize: 12,
                        fontWeight: 700,
                        letterSpacing: ".06em",
                        textTransform: "uppercase",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}>
                        {stat.label}
                      </span>
                    </div>
                    <div style={{ height: 5, background: "rgba(13,17,15,.92)", borderRadius: 999, overflow: "hidden" }}>
                      <div style={{
                        height: "100%",
                        width: `${Math.round(rate * 100)}%`,
                        background: color,
                        borderRadius: 999,
                      }} />
                    </div>
                  </div>
                  <div style={{
                    color,
                    fontFamily: "'Barlow Condensed',sans-serif",
                    fontWeight: 700,
                    fontSize: 12,
                    textAlign: "right",
                  }}>
                    {stat.correct}/{stat.total}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
        gap: 10,
        width: "100%",
        marginTop: 4,
      }}>
        {missedItems.length > 0 && (
          <button onClick={onReviewMissedItems} style={{
            flex: 1, height: 48, background: "#f43f5e", border: "none",
            borderRadius: 10, color: "#fff", cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
            fontSize: 13, letterSpacing: ".06em", textTransform: "uppercase",
          }}>Retry missed</button>
        )}
        {missedItems.length > 0 && onSaveMissedToFocus && (
          <button
            onClick={() => setSavedFocusCount(onSaveMissedToFocus())}
            style={{
              flex: 1, height: 48, background: savedFocusCount !== null ? "rgba(57,195,111,.14)" : "rgba(17,22,20,.92)",
              border: `1px solid ${savedFocusCount !== null ? "rgba(57,195,111,.45)" : "rgba(219,229,216,.18)"}`,
              borderRadius: 10, color: savedFocusCount !== null ? "#39c36f" : "#e4ece2", cursor: "pointer",
              fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
              fontSize: 13, letterSpacing: ".06em", textTransform: "uppercase",
            }}
          >
            {savedFocusCount === null ? "Save to focus" : `${savedFocusCount} saved`}
          </button>
        )}
        {missedConcepts.length > 0 && (
          <button onClick={onReviewMissedConcepts} style={{
            flex: 1, height: 48, background: "#e0a30a", border: "none",
            borderRadius: 10, color: "#000", cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
            fontSize: 13, letterSpacing: ".06em", textTransform: "uppercase",
          }}>Drill concepts</button>
        )}
        {suggestedMode && (
          <button onClick={() => onStartPracticeMode(suggestedMode.id, suggestedMode.count)} style={{
            flex: 1, height: 48, background: "rgba(17,22,20,.92)", border: "1px solid rgba(224,163,10,.4)",
            borderRadius: 10, color: "#e0a30a", cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
            fontSize: 13, letterSpacing: ".06em", textTransform: "uppercase",
          }}>Practice {suggestedMode.label}</button>
        )}
        <button onClick={onRepeat} style={{
          flex: 1, height: 48, background: "rgba(17,22,20,.92)", border: "1px solid rgba(219,229,216,.18)",
          borderRadius: 10, color: "#e4ece2", cursor: "pointer",
          fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
          fontSize: 13, letterSpacing: ".06em", textTransform: "uppercase",
        }}>Study again</button>
        <button onClick={onHome} style={{
          flex: 1, height: 48, background: "#39c36f", border: "none",
          borderRadius: 10, color: "#000", cursor: "pointer",
          fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
          fontSize: 13, letterSpacing: ".06em", textTransform: "uppercase",
        }}>Back to map</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// APP SHELL
// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  const curriculum   = useCurriculum();
  const staticDeploy = isStaticDeploy();
  const [screen, setScreen]           = useState(readInitialScreen);
  const [mapViewState, setMapViewState] = useState(loadMapViewState);
  const [sectionViewState, setSectionViewState] = useState(() => loadBrowserViewState(
    SECTION_VIEW_KEY,
    { search: "", sortMode: "order", activeFilter: "all" },
  ));
  const [focusViewState, setFocusViewState] = useState(() => loadBrowserViewState(
    FOCUS_VIEW_KEY,
    { search: "", sortMode: "section", activeFilter: "all" },
  ));
  const [activeSection, setActiveSection] = useState(null);
  const [activeTarget, setActiveTarget]   = useState(null);
  const [activeOrigin, setActiveOrigin]   = useState("map");
  const [focusBackScreen, setFocusBackScreen] = useState("map");
  const [session, setSession]         = useState([]);
  const [sessionMeta, setSessionMeta] = useState(null);
  const [flashcards, setFlashcards]   = useState([]);
  const [flashcardOptions, setFlashcardOptions] = useState({});
  const [sessionResults, setSessionResults] = useState([]);
  const [aircraftImages, setAircraftImages] = useState([]);
  const [aircraftImageReview, setAircraftImageReview] = useState(loadAircraftImageReviewState);
  const prevMasteryRef = useRef(null);
  const scrollPositionsRef = useRef({});

  useEffect(() => {
    writeScreenToUrl(screen);
  }, [screen]);

  useEffect(() => {
    const savedY = scrollPositionsRef.current[screen] || 0;
    const restore = window.setTimeout(() => window.scrollTo(0, savedY), 0);
    const remember = () => {
      scrollPositionsRef.current[screen] = window.scrollY || 0;
    };
    window.addEventListener("scroll", remember, { passive: true });
    return () => {
      window.clearTimeout(restore);
      remember();
      window.removeEventListener("scroll", remember);
    };
  }, [screen]);

  useEffect(() => {
    saveMapViewState(mapViewState);
  }, [mapViewState]);

  useEffect(() => {
    saveBrowserViewState(SECTION_VIEW_KEY, sectionViewState);
  }, [sectionViewState]);

  useEffect(() => {
    saveBrowserViewState(FOCUS_VIEW_KEY, focusViewState);
  }, [focusViewState]);

  useEffect(() => {
    saveAircraftImageReviewState(aircraftImageReview);
  }, [aircraftImageReview]);

  useEffect(() => {
    if (staticDeploy) {
      setAircraftImages([]);
      return undefined;
    }
    let cancelled = false;
    fetch(assetUrl("aircraft-images/manifest.jsonl"))
      .then((response) => response.ok ? response.text() : "")
      .then((text) => {
        if (!cancelled) setAircraftImages(parseAircraftImageManifest(text));
      })
      .catch(() => {
        if (!cancelled) setAircraftImages([]);
    });
    return () => { cancelled = true; };
  }, [staticDeploy]);

  function updateMapViewState(patch) {
    setMapViewState((current) => ({
      ...current,
      ...(typeof patch === "function" ? patch(current) : patch),
    }));
  }

  function updateSectionViewState(patch) {
    setSectionViewState((current) => ({
      ...current,
      ...(typeof patch === "function" ? patch(current) : patch),
    }));
  }

  function updateFocusViewState(patch) {
    setFocusViewState((current) => ({
      ...current,
      ...(typeof patch === "function" ? patch(current) : patch),
    }));
  }

  const chapters = useMemo(() => (
    curriculum.dbReady ? probeTime("getChapters", () => curriculum.getChapters()) : []
  ), [curriculum.dbReady, curriculum.getChapters]);
  const stats = useMemo(() => (
    curriculum.dbReady ? probeTime("getStats", () => curriculum.getStats()) : null
  ), [curriculum.dbReady, curriculum.getStats]);
  const practiceQueue = useMemo(() => (
    curriculum.dbReady ? probeTime("getPracticeQueue", () => curriculum.getPracticeQueue(6)) : []
  ), [curriculum.dbReady, curriculum.getPracticeQueue]);
  const conceptQueue = useMemo(() => (
    curriculum.dbReady ? probeTime("getConceptQueue", () => curriculum.getConceptQueue(6)) : []
  ), [curriculum.dbReady, curriculum.getConceptQueue]);
  const mistakeQueue = useMemo(() => (
    curriculum.dbReady ? probeTime("getMistakeQueue", () => curriculum.getMistakeQueue(6)) : []
  ), [curriculum.dbReady, curriculum.getMistakeQueue]);
  const dueReviewQueue = useMemo(() => (
    curriculum.dbReady ? probeTime("getDueReviewQueue", () => curriculum.getDueReviewQueue(6)) : []
  ), [curriculum.dbReady, curriculum.getDueReviewQueue]);
  const focusParagraphs = useMemo(() => (
    curriculum.dbReady ? probeTime("getFocusParagraphs", () => curriculum.getFocusParagraphs()) : []
  ), [curriculum.dbReady, curriculum.getFocusParagraphs]);
  const aircraftRecognitionCards = useMemo(() => (
    curriculum.dbReady ? probeTime("getAircraftRecognitionCards", () => curriculum.getAircraftRecognitionCards()) : []
  ), [curriculum.dbReady, curriculum.getAircraftRecognitionCards]);
  const aircraftImageCards = useMemo(() => (
    buildAircraftImageCards(
      aircraftImages,
      staticDeploy ? {} : aircraftImageReview,
      aircraftRecognitionCards,
    )
  ), [aircraftImageReview, aircraftImages, aircraftRecognitionCards, staticDeploy]);
  const flaggedItemCount = useMemo(() => countItemFlags(), [screen]);
  const nextAction = useMemo(() => (
    curriculum.dbReady
      ? resolveNextAction({ mistakeQueue, dueReviewQueue, conceptQueue, practiceQueue })
      : null
  ), [conceptQueue, curriculum.dbReady, dueReviewQueue, mistakeQueue, practiceQueue]);
  const studyPlan = useMemo(() => (
    curriculum.dbReady
      ? buildStudyPlan({ nextAction, mistakeQueue, dueReviewQueue, conceptQueue, practiceQueue })
      : []
  ), [conceptQueue, curriculum.dbReady, dueReviewQueue, mistakeQueue, nextAction, practiceQueue]);

  // ── Start a lesson ────────────────────────────────────────────────────────
  function handleStartLesson(target, origin = "map") {
    const conceptReviewCount = target?.count
      ?? Math.min(6, Math.max(3, (target?.concept_ids?.length || 1) * 2));
    const acts = target?.type === "recommended"
      ? curriculum.buildRecommendedSession(12)
      : target?.type === "due_review"
        ? curriculum.buildDueReviewSession(target.count || 8)
      : target?.type === "practice_mode"
        ? curriculum.buildPracticeModeSession(target.mode_id, target.count || 10)
      : target?.type === "missed_items"
        ? curriculum.buildMistakeSession(target.count || 6)
      : target?.type === "concept_review"
        ? curriculum.buildConceptSession(target.concept_ids, conceptReviewCount)
      : target?.type === "focus_list"
        ? curriculum.buildFocusSession(target.para_ids, target.count)
        : target?.para_id
          ? curriculum.buildParaSession(target.para_id)
          : curriculum.buildSession(target.chapter, target.section, target.count);
    if (!acts.length) return;
    prevMasteryRef.current = { ...curriculum.mastery };
    setSession(acts);
    setSessionMeta(sessionMetaForTarget(target));
    if (target?.chapter && target?.section && !target?.type) setActiveSection(target);
    setActiveTarget(target);
    setActiveOrigin(origin);
    setScreen("lesson");
  }

  function handleStartNextAction(action = nextAction) {
    if (!action) return;
    if (action.type === "missed_items") {
      handleStartLesson({ type: "missed_items", label: action.label, count: action.count || 6 }, "map");
      return;
    }
    if (action.type === "due_review") {
      handleStartLesson({ type: "due_review", label: action.label, count: action.count || 8 }, "map");
      return;
    }
    if (action.type === "concept_review") {
      handleStartLesson({
        type: "concept_review",
        label: action.label,
        concept_ids: action.concept_ids || [],
        count: action.count || 6,
      }, "map");
      return;
    }
    if (action.type === "practice_mode") {
      handleStartLesson({
        type: "practice_mode",
        mode_id: action.mode_id || "diagnostic",
        label: action.label,
        count: action.count || 10,
      }, "map");
      return;
    }
    handleStartLesson({ type: "recommended", label: action.label || "Recommended Practice" }, "map");
  }

  // ── Start flashcards ──────────────────────────────────────────────────────
  function handleStartFlashcards(target, origin = "map") {
    const cards = target?.para_id
      ? curriculum.getParagraphFlashcards(target.para_id)
      : curriculum.getFlashcards(target.chapter, target.section);
    if (!cards.length) return;
    setFlashcards(cards);
    setFlashcardOptions({});
    if (target?.chapter && target?.section) setActiveSection(target);
    setActiveTarget(target);
    setActiveOrigin(origin);
    setScreen("cards");
  }

  function handleStartAircraftRecognition(options = {}) {
    const allCards = curriculum.getAircraftRecognitionCards();
    const cards = enrichAircraftCards(applyAircraftCardFilters(allCards, options.filters || {}), allCards);
    if (!cards.length) return;
    setFlashcards(cards);
    setFlashcardOptions({
      order: options.order || "shuffle",
      direction: options.direction || "normal",
      promptMode: options.promptMode || (options.direction === "reverse" ? "spoken" : "identifier"),
    });
    setActiveTarget({ label: options.label || "Aircraft Recognition", title: "Aircraft Recognition" });
    setActiveOrigin("map");
    setScreen("cards");
  }

  function handleStartAircraftImages() {
    if (!aircraftImageCards.length) return;
    setFlashcards(aircraftImageCards);
    setFlashcardOptions({ order: "shuffle", direction: "normal", promptMode: "image" });
    setActiveTarget({ label: "Aircraft Image Recognition", title: "Aircraft Image Recognition" });
    setActiveOrigin("map");
    setScreen("cards");
  }

  function handleSetAircraftImageStatus(key, status) {
    setAircraftImageReview((current) => ({
      ...current,
      [key]: {
        ...(current[key] || {}),
        identity_status: status,
        reviewed_at: new Date().toISOString(),
      },
    }));
  }

  function handleOpenSection(sec) {
    if (sec?.chapter) {
      updateMapViewState((current) => ({
        openChapters: {
          ...current.openChapters,
          [String(sec.chapter)]: true,
        },
      }));
    }
    setActiveSection(sec);
    setScreen("section");
  }

  function handleOpenFocus(backScreen = "map") {
    setFocusBackScreen(backScreen);
    setScreen("focus");
  }

  function handleResetLearnerProgress() {
    const confirmed = window.confirm(
      "Reset local learner progress? This clears crowns, focus list, missed queue, concept memory, and flashcard ratings on this browser. QA review state is not cleared.",
    );
    if (!confirmed) return;
    LEARNER_PROGRESS_KEYS.forEach((key) => localStorage.removeItem(key));
    window.location.reload();
  }

  function resolveReturnScreen() {
    if (activeOrigin === "focus") return "focus";
    if (activeOrigin === "section") return "section";
    return "map";
  }

  // ── Session complete ──────────────────────────────────────────────────────
  function handleSessionComplete(results) {
    // Record all results
    results.forEach(({ activityId, paraId, activityType, score, concepts }) => {
      curriculum.recordResult(paraId, activityType, score, concepts || [], activityId);
    });

    // Compute crown changes
    const changes = curriculum.getCrownChanges(prevMasteryRef.current || {}, results);
    const missedConcepts = results
      .filter((result) => !result.correct)
      .flatMap((result) => result.concepts || [])
      .filter((concept, index, arr) => arr.findIndex((item) => item.id === concept.id) === index);
    setSessionResults({ results, crownChanges: changes, missedConcepts });
    setScreen("results");
  }

  // ─── Screens ──────────────────────────────────────────────────────────────

  if (curriculum.loading) return <LoadingScreen />;
  if (curriculum.error)   return <ErrorScreen error={curriculum.error} />;

  if (screen === "lesson") {
    return (
      <LessonPlayer
        session={session}
        sessionMeta={sessionMeta}
        onBack={() => setScreen(resolveReturnScreen())}
        onComplete={handleSessionComplete}
        onRemediate={(conceptIds) => handleStartLesson({
          type: "concept_review",
          label: "Concept Remediation",
          concept_ids: conceptIds,
          count: 3,
        }, "map")}
      />
    );
  }

  if (screen === "cards") {
    return (
      <FlashcardDeck
        cards={flashcards}
        sectionLabel={activeTarget?.label || activeTarget?.title}
        initialOptions={flashcardOptions}
        onBack={() => setScreen(resolveReturnScreen())}
      />
    );
  }

  if (screen === "aircraft_image_review" && !staticDeploy) {
    return (
      <AircraftImageReview
        images={aircraftImages}
        reviewState={aircraftImageReview}
        onSetStatus={handleSetAircraftImageStatus}
        onBack={() => setScreen("map")}
      />
    );
  }

  if (screen === "results") {
    return (
      <SessionResults
        results={sessionResults.results || []}
        crownChanges={sessionResults.crownChanges || []}
        missedConcepts={sessionResults.missedConcepts || []}
        onHome={() => setScreen("map")}
        onReviewMissedItems={() => handleStartLesson({
          type: "missed_items",
          label: "Missed Items",
          count: Math.min(6, Math.max(2, (sessionResults.results || []).filter((result) => !result.correct).length)),
        }, "map")}
        onSaveMissedToFocus={() => {
          const missedParaIds = [
            ...new Set((sessionResults.results || [])
              .filter((result) => !result.correct)
              .map((result) => result.paraId)
              .filter(Boolean)),
          ];
          let added = 0;
          for (const paraId of missedParaIds) {
            if (!curriculum.isParagraphFocused(paraId)) {
              curriculum.toggleFocusedParagraph(paraId);
              added += 1;
            }
          }
          return added;
        }}
        onReviewMissedConcepts={() => {
          const conceptIds = (sessionResults.missedConcepts || []).map((concept) => concept.id);
          const missedCount = (sessionResults.results || []).filter((result) => !result.correct).length;
          handleStartLesson({
            type: "concept_review",
            label: "Missed Concepts",
            concept_ids: conceptIds,
            count: Math.min(6, Math.max(2, missedCount * 2)),
          }, "map");
        }}
        onStartPracticeMode={(modeId, count) => handleStartLesson({
          type: "practice_mode",
          mode_id: modeId,
          label: "Practice Mode",
          count,
        }, "map")}
        onRepeat={() => {
          if (activeTarget) handleStartLesson(activeTarget, activeOrigin || "map");
          else setScreen("map");
        }}
      />
    );
  }

  if (screen === "section") {
    const paragraphs = activeSection
      ? curriculum.getSectionParagraphs(activeSection.chapter, activeSection.section)
      : [];
    return (
      <SectionBrowser
        section={activeSection}
        paragraphs={paragraphs}
        onBack={() => setScreen("map")}
        onStudySection={(target) => handleStartLesson(target, "section")}
        onCardsSection={(target) => handleStartFlashcards(target, "section")}
        onStudyParagraph={(target) => handleStartLesson(target, "section")}
        onCardsParagraph={(target) => handleStartFlashcards(target, "section")}
        onToggleFocus={(item) => curriculum.toggleFocusedParagraph(item.para_id)}
        onOpenFocus={() => handleOpenFocus("section")}
        focusCount={stats?.focusCount || 0}
        viewState={sectionViewState}
        onViewStateChange={updateSectionViewState}
      />
    );
  }

  if (screen === "focus") {
    const paragraphs = curriculum.getFocusParagraphs();
    return (
      <FocusListBrowser
        paragraphs={paragraphs}
        onBack={() => setScreen(focusBackScreen)}
        onStudyList={() => handleStartLesson({
          type: "focus_list",
          label: "Focus List",
          para_ids: paragraphs.map((item) => item.para_id),
        }, "focus")}
        onStudyParagraph={(target) => handleStartLesson(target, "focus")}
        onCardsParagraph={(target) => handleStartFlashcards(target, "focus")}
        onRemoveParagraph={(item) => curriculum.toggleFocusedParagraph(item.para_id)}
        onClear={() => curriculum.clearFocusList()}
        viewState={focusViewState}
        onViewStateChange={updateFocusViewState}
      />
    );
  }

  if (screen === "review" && !staticDeploy) {
    return (
      <CurriculumReview
        curriculum={curriculum}
        onBack={() => setScreen("map")}
      />
    );
  }

  return (
    <CurriculumMap
      chapters={chapters}
      stats={stats}
      practiceQueue={practiceQueue}
      conceptQueue={conceptQueue}
      mistakeQueue={mistakeQueue}
      dueReviewQueue={dueReviewQueue}
      focusParagraphs={focusParagraphs}
      flaggedItemCount={flaggedItemCount}
      nextAction={nextAction}
      studyPlan={studyPlan}
      publishConfig={curriculum.publishConfig}
      viewState={mapViewState}
      onViewStateChange={updateMapViewState}
      onStartNextAction={handleStartNextAction}
      onStartRecommended={() => handleStartLesson({ type: "recommended", label: "Recommended Practice" }, "map")}
      onStartDueReview={() => handleStartLesson({
        type: "due_review",
        label: "Due Review",
        count: 8,
      }, "map")}
      onStartMissedItems={() => handleStartLesson({
        type: "missed_items",
        label: "Missed Items",
        count: 6,
      }, "map")}
      onStartPracticeMode={(modeId, count) => handleStartLesson({
        type: "practice_mode",
        mode_id: modeId,
        label: "Practice Mode",
        count,
      }, "map")}
      onStartConceptReview={(conceptIds, count = 6) => handleStartLesson({
        type: "concept_review",
        label: "Missed Concepts",
        concept_ids: conceptIds,
        count,
      }, "map")}
      onStartLesson={handleStartLesson}
      onStartFlashcards={handleStartFlashcards}
      onOpenSection={handleOpenSection}
      onOpenFocus={() => handleOpenFocus("map")}
      onOpenReview={staticDeploy ? null : () => setScreen("review")}
      onResetProgress={handleResetLearnerProgress}
      aircraftCardCount={aircraftRecognitionCards.length}
      aircraftCards={aircraftRecognitionCards}
      aircraftImageCandidateCount={staticDeploy ? 0 : aircraftImages.length}
      aircraftImageApprovedCount={aircraftImageCards.length}
      onOpenAircraftImageReview={staticDeploy ? null : () => setScreen("aircraft_image_review")}
      onStartAircraftImages={handleStartAircraftImages}
      onStartAircraftRecognition={handleStartAircraftRecognition}
    />
  );
}
