/**
 * CurriculumMap.jsx
 * =================
 * Home screen: chapter accordion → section cards → start a lesson.
 *
 * Shows crown progress per section, activity/flashcard counts,
 * and lets students drill into any section or jump straight to
 * their weakest areas.
 */

import { useState, useMemo } from "react";
import { CROWN_ICONS, CROWN_COLORS, CROWN_LABELS, calcCrown } from "./useCurriculum";

const MAP_CSS = `
html,body,#root{margin:0;min-width:0;min-height:100%;background:#30302e;-webkit-text-size-adjust:100%}
*{box-sizing:border-box}
button,a{touch-action:manipulation}
.map-section-actions{grid-template-columns:repeat(auto-fit,minmax(92px,1fr))}
.map-shell{font-variant-ligatures:none}
.map-shell *{font-family:'Share Tech Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace!important;border-radius:2px!important;box-shadow:none!important}
.map-shell button,.map-shell input,.map-shell select{font:inherit}
.map-shell button{box-shadow:none!important}
@media (max-width: 760px){
  .map-shell{width:100%;overflow-x:hidden;min-height:100dvh!important}
  .map-header{padding:max(8px, env(safe-area-inset-top)) 8px 0!important}
  .map-header .map-topbar{width:100%!important;padding:14px 12px 0!important}
  .map-main{padding:12px 12px max(12px, env(safe-area-inset-bottom))!important;max-width:calc(100% - 16px)!important}
  .map-shell input,.map-shell select{font-size:16px!important;min-height:44px!important}
  .map-shell button{min-height:40px!important}
  .map-section-actions{grid-template-columns:1fr!important}
  .map-section-actions button{width:100%}
  .map-topbar{flex-direction:column;align-items:flex-start!important}
  .map-actions{justify-content:flex-start!important}
  .map-tools-menu{left:0!important;right:auto!important;width:min(210px,calc(100vw - 32px))!important;min-width:0!important}
  .map-next-action-orb{display:none!important}
  .map-next-action-row{flex-direction:column;align-items:stretch!important;gap:12px!important}
  .map-next-action-actions{width:100%;justify-content:space-between!important}
  .map-next-action-actions button:last-child{flex:1;min-width:0}
  .map-browse-header{align-items:flex-start!important;flex-direction:column!important}
  .map-browse-order{white-space:normal!important}
  .map-summary-stats{width:100%}
  .map-stats{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .map-home-tabs{flex-direction:column!important}
  .map-practice-grid{grid-template-columns:1fr!important}
  .map-aircraft-workspace{grid-template-columns:1fr!important}
  .map-aircraft-hero,.map-aircraft-controls{min-width:0!important;width:100%!important}
  .map-aircraft-controls{grid-template-columns:minmax(0,1fr)!important}
  .map-aircraft-hero-title{font-size:24px!important;overflow-wrap:anywhere}
  .map-aircraft-copy{max-width:none!important}
  .map-aircraft-review-grid{grid-template-columns:1fr!important}
  .map-aircraft-filter-grid{grid-template-columns:1fr!important}
  .map-aircraft-filter-grid label{min-width:0!important;width:100%!important}
  .map-aircraft-filter-grid select{width:100%!important;max-width:none!important}
  .map-chapter-header{align-items:flex-start!important;flex-wrap:wrap}
  .map-chapter-meta{width:100%;justify-content:flex-start!important}
}
`;

const MAP_THEME = {
  bg: "#30302e",
  bg2: "#30302e",
  paper: "#11120e",
  panel: "#11120e",
  panel2: "#13140f",
  inset: "#0a0b09",
  line: "rgba(226,219,193,.22)",
  line2: "rgba(226,219,193,.34)",
  text: "#f1ead7",
  muted: "#b7ae95",
  faint: "#746f61",
  amber: "#d8a21c",
  blue: "#9fb0aa",
  green: "#9aa37f",
  red: "#bd766c",
};

function mapPanelStyle(extra = {}) {
  return {
    background: MAP_THEME.panel,
    border: `1px solid ${MAP_THEME.line}`,
    borderRadius: 2,
    ...extra,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// CROWN BADGE
// ─────────────────────────────────────────────────────────────────────────────
function CrownBadge({ level, size = "md" }) {
  const color = CROWN_COLORS[level] || CROWN_COLORS[0];
  const icon  = CROWN_ICONS[level]  || CROWN_ICONS[0];
  const sz    = size === "sm" ? { fontSize: 11, padding: "1px 6px" } : { fontSize: 13, padding: "2px 9px" };
  return (
    <span style={{
      ...sz, borderRadius: 2, fontFamily: "'Share Tech Mono', ui-monospace, monospace",
      fontWeight: 700, letterSpacing: ".04em",
      background: MAP_THEME.inset, color, border: `1px solid ${color}66`,
    }}>
      {icon}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRESS BAR
// ─────────────────────────────────────────────────────────────────────────────
function ProgressBar({ value, color = MAP_THEME.amber, height = 4 }) {
  return (
    <div style={{ height, background: "rgba(226,219,193,.13)", borderRadius: 0, overflow: "hidden" }}>
      <div style={{
        height: "100%", width: `${Math.min(100, value * 100)}%`,
        background: color, borderRadius: 0,
        transition: "width .4s cubic-bezier(.4,0,.2,1)",
      }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SECTION CARD
// ─────────────────────────────────────────────────────────────────────────────
function SectionCard({ sec, sectionSignals, onStart, onFlashcards, onFocus }) {
  const crown = sec.maxCrown || 0;
  const progress = sec.avgCrown / 4;
  const badges = buildSectionBadges(sec, sectionSignals);
  const activityCount = sec.activityCount ?? sec.acts ?? 0;
  const flashcardCount = sec.flashcardCount ?? sec.fcs ?? 0;
  const questionCount = sec.questionCount ?? sec.qs ?? 0;
  const hasContent = activityCount > 0 || flashcardCount > 0 || questionCount > 0;
  const drillCount = activityCount + questionCount;
  const hasDrillContent = drillCount > 0;
  const handleDefaultOpen = () => {
    if (!hasContent) return;
    if (hasDrillContent) onStart(sec);
    else if (flashcardCount > 0) onFlashcards(sec);
    else onFocus(sec);
  };
  const actionButtonBase = {
    minHeight: 31,
    borderRadius: 2,
    fontFamily: "'Share Tech Mono', ui-monospace, monospace",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: ".07em",
    textTransform: "uppercase",
    cursor: "pointer",
    whiteSpace: "nowrap",
  };

  return (
    <div style={{
      background: MAP_THEME.panel2,
      border: `1px solid ${crown > 0 ? "rgba(216,162,28,.36)" : MAP_THEME.line}`,
      borderRadius: 2,
      padding: "15px 15px 13px",
      opacity: hasContent ? 1 : 0.45,
      transition: "border-color .15s, background .15s",
      cursor: hasContent ? "pointer" : "default",
      minHeight: 184,
      display: "flex",
      flexDirection: "column",
    }}
      onMouseEnter={e => {
        if (!hasContent) return;
        e.currentTarget.style.borderColor = "rgba(216,162,28,.5)";
        e.currentTarget.style.background = "#161710";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = crown > 0 ? "rgba(216,162,28,.36)" : MAP_THEME.line;
        e.currentTarget.style.background = MAP_THEME.panel2;
      }}
      onClick={handleDefaultOpen}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: "'Share Tech Mono', ui-monospace, monospace", fontWeight: 700,
            fontSize: 13, letterSpacing: ".01em", color: MAP_THEME.text, lineHeight: 1.35,
          }}>
            {sec.label}
          </div>
          <div style={{
            fontFamily: "'Share Tech Mono', ui-monospace, monospace", fontSize: 10,
            color: MAP_THEME.faint, letterSpacing: ".06em", marginTop: 2,
          }}>
            {sec.paras} paragraph{sec.paras !== 1 ? "s" : ""}
          </div>
        </div>
        {crown > 0 && <CrownBadge level={crown} size="sm" />}
      </div>

      {/* Progress bar */}
      <ProgressBar value={progress} color={CROWN_COLORS[Math.max(1, crown)]} height={3} />

      {badges.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 8 }}>
          {badges.map((badge) => (
            <span key={badge.label} style={{
              height: 19,
              display: "inline-flex",
              alignItems: "center",
              padding: "0 6px",
              borderRadius: 2,
              background: `${badge.color}14`,
              border: `1px solid ${badge.color}38`,
              color: badge.color,
              fontFamily: "'Share Tech Mono', ui-monospace, monospace",
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: ".07em",
              textTransform: "uppercase",
            }}>
              {badge.label}
            </span>
          ))}
        </div>
      )}

      <div style={{ flex: 1 }} />

      {/* Footer: counts + actions */}
      {hasContent && (
        <div style={{
          marginTop: 10,
          display: "flex",
          gap: 6,
          flexWrap: "wrap",
          color: MAP_THEME.faint,
          fontFamily: "'Barlow Condensed',sans-serif",
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: ".07em",
          textTransform: "uppercase",
        }}>
          <span style={{ color: MAP_THEME.muted }}>Drill = activities + qs</span>
          <span>Recall = flashcards</span>
          <span>Target = paragraphs</span>
        </div>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
        gap: 7,
        marginTop: 10,
        paddingTop: 9,
        borderTop: `1px solid ${MAP_THEME.line}`,
      }}>
        {[
          { value: activityCount, label: "Activities" },
          { value: questionCount, label: "Qs" },
          { value: flashcardCount, label: "Cards" },
        ].map((item) => (
          <div key={item.label} style={{ minWidth: 0 }}>
            <div style={{
              fontFamily: "'Share Tech Mono', ui-monospace, monospace",
              fontSize: 14,
              fontWeight: 700,
              color: MAP_THEME.muted,
              lineHeight: 1,
            }}>
              {item.value || 0}
            </div>
            <div style={{
              marginTop: 3,
              fontFamily: "'Share Tech Mono', ui-monospace, monospace",
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: ".08em",
              color: MAP_THEME.faint,
              textTransform: "uppercase",
              whiteSpace: "nowrap",
            }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>

      <div style={{
        display: "grid",
        gap: 7,
        marginTop: 10,
      }} className="map-section-actions">
        {hasContent && hasDrillContent && (
          <button
            onClick={e => { e.stopPropagation(); onStart(sec); }}
            style={{
              ...actionButtonBase,
              background: MAP_THEME.amber,
              border: "none",
              color: "#000",
            }}
            title={`Drill ${drillCount} activities and questions from this section`}
          >Drill</button>
        )}
        {hasContent && !hasDrillContent && <div />}
        {hasContent && flashcardCount > 0 && (
          <button
            onClick={e => { e.stopPropagation(); onFlashcards(sec); }}
            style={{
              ...actionButtonBase,
              background: "none",
              border: `1px solid ${MAP_THEME.line2}`,
              color: MAP_THEME.faint,
            }}
            title={`Review ${flashcardCount} recall cards from this section`}
          >Recall</button>
        )}
        {hasContent && flashcardCount <= 0 && <div />}
        {hasContent && (
          <button
            onClick={e => { e.stopPropagation(); onFocus(sec); }}
            style={{
              ...actionButtonBase,
              background: "none",
              border: `1px solid ${MAP_THEME.line2}`,
              color: MAP_THEME.text,
            }}
            title="Target specific paragraphs or save issue areas"
          >Target</button>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CHAPTER ACCORDION
// ─────────────────────────────────────────────────────────────────────────────
function ChapterAccordion({
  chapter,
  sectionSignals,
  onStart,
  onFlashcards,
  onFocus,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
}) {
  const [localOpen, setLocalOpen] = useState(defaultOpen);
  const open = controlledOpen ?? localOpen;
  const setOpen = (nextValue) => {
    const resolved = typeof nextValue === "function" ? nextValue(open) : nextValue;
    if (controlledOpen === undefined) setLocalOpen(resolved);
    if (onOpenChange) onOpenChange(resolved);
  };

  const totalActs    = chapter.sections.reduce((s, x) => s + x.acts, 0);
  const totalCards = chapter.sections.reduce((s, x) => s + (x.fcs || 0), 0);
  const totalQuestions = chapter.sections.reduce((s, x) => s + (x.qs || 0), 0);
  const highestCrown = Math.max(0, ...chapter.sections.map(s => s.maxCrown || 0));
  const sectionsWithProgress = chapter.sections.filter(s => (s.avgCrown || 0) > 0).length;
  const progressPct = chapter.sections.length
    ? sectionsWithProgress / chapter.sections.length
    : 0;

  return (
    <div style={{ marginBottom: 12 }}>
      {/* Chapter header */}
      <div
        onClick={() => setOpen(o => !o)}
        className="map-chapter-header"
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "13px 15px", borderRadius: 2,
          background: open ? "#17150d" : MAP_THEME.panel,
          border: `1px solid ${open ? "rgba(216,162,28,.42)" : MAP_THEME.line}`,
          cursor: "pointer", userSelect: "none",
          transition: "background .15s",
        }}
      >
        <div style={{
          width: 26, height: 26, borderRadius: 2, background: MAP_THEME.inset,
          border: `1px solid ${MAP_THEME.line2}`, display: "flex", alignItems: "center",
          justifyContent: "center", fontFamily: "'Share Tech Mono', ui-monospace, monospace",
          fontSize: 11, fontWeight: 700, color: MAP_THEME.amber,
        }}>
          {chapter.chapter}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: "'Share Tech Mono', ui-monospace, monospace", fontWeight: 700,
            fontSize: 14, letterSpacing: ".03em", color: MAP_THEME.text,
          }}>
            Chapter {chapter.chapter} — {chapter.title}
          </div>
          <div style={{ marginTop: 5 }}>
            <ProgressBar value={progressPct} color={MAP_THEME.amber} height={3} />
          </div>
        </div>
        <div className="map-chapter-meta" style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {highestCrown > 0 && <CrownBadge level={highestCrown} size="sm" />}
          <span style={{
            fontFamily: "'Share Tech Mono', ui-monospace, monospace",
            fontSize: 10,
            color: MAP_THEME.muted,
            letterSpacing: ".06em",
            textTransform: "uppercase",
            background: MAP_THEME.inset,
            border: `1px solid ${MAP_THEME.line2}`,
            borderRadius: 2,
            padding: "4px 9px",
          }}>
            {totalActs} acts · {totalQuestions} qs · {totalCards} cards
          </span>
          <span style={{
            color: open ? MAP_THEME.amber : MAP_THEME.faint, fontSize: 14, transition: "transform .2s",
            transform: open ? "rotate(90deg)" : "rotate(0deg)", display: "block",
          }}>›</span>
        </div>
      </div>

      {/* Sections grid */}
      {open && (
        <div style={{
          background: "#0d0e0b", border: `1px solid ${open ? "rgba(216,162,28,.28)" : MAP_THEME.line}`, borderTop: "none",
          borderRadius: 2,
          padding: "12px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))",
          gap: 10,
        }}>
          {chapter.sections.map(sec => (
            <SectionCard
              key={sec.key}
              sec={sec}
              sectionSignals={sectionSignals}
              onStart={onStart}
              onFlashcards={onFlashcards}
              onFocus={onFocus}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// STATS STRIP
// ─────────────────────────────────────────────────────────────────────────────
function StatsStrip({ stats }) {
  const items = [
    { n: stats.paraCount,      label: "Paragraphs" },
    { n: stats.actCount,       label: "Activities"  },
    { n: stats.questionCount || 0, label: "Questions" },
    { n: stats.fcCount,        label: "Flashcards"  },
    { n: Math.max(0, stats.paraCount - stats.touchedParas), label: "New" },
    { n: stats.touchedParas,   label: "Studied"     },
    { n: stats.masteredParas,  label: "Mastered ♛"  },
  ];
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      flexWrap: "wrap",
      background: "rgba(13,17,15,.92)",
      border: "1px solid rgba(219,229,216,.13)",
      borderRadius: 2,
      padding: "7px 10px",
      marginBottom: 16,
    }} className="map-stats">
      <span style={{
        fontFamily: "'Barlow Condensed',sans-serif",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: ".09em",
        color: MAP_THEME.faint,
        textTransform: "uppercase",
        marginRight: 2,
      }}>
        Progress
      </span>
      {items.map((item, i) => (
        <div key={i} style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 8px",
          borderRadius: 2,
          background: MAP_THEME.inset,
          border: `1px solid ${MAP_THEME.line}`,
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700,
            fontSize: 12, color: i >= 3 ? MAP_THEME.amber : MAP_THEME.text,
          }}>{item.n}</div>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 9,
            color: MAP_THEME.muted,
            letterSpacing: ".07em",
            textTransform: "uppercase",
          }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}

function practicePanelStyle(accent = MAP_THEME.line2, extra = {}) {
  return {
    background: MAP_THEME.paper,
    border: `1px solid ${MAP_THEME.line}`,
    borderTop: `2px solid ${accent}`,
    borderRadius: 2,
    padding: 14,
    ...extra,
  };
}

function practiceHeaderStyle() {
  return {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 12,
  };
}

function practiceKickerStyle(color = MAP_THEME.amber) {
  return {
    fontFamily: "'Barlow Condensed',sans-serif",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: ".1em",
    color,
    textTransform: "uppercase",
  };
}

function practiceActionStyle(color = MAP_THEME.amber, filled = false) {
  return {
    height: 34,
    padding: "0 13px",
    borderRadius: 2,
    border: `1px solid ${filled ? color : `${color}55`}`,
    background: filled ? color : "transparent",
    color: filled ? "#11120e" : color,
    cursor: "pointer",
    fontFamily: "'Barlow Condensed',sans-serif",
    fontWeight: 700,
    fontSize: 11,
    letterSpacing: ".08em",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
  };
}

function practiceRowStyle(columns = "78px minmax(0,1fr) auto", accent = MAP_THEME.line) {
  return {
    display: "grid",
    gridTemplateColumns: columns,
    alignItems: "center",
    gap: 8,
    padding: "8px 10px",
    borderRadius: 2,
    background: MAP_THEME.panel2,
    border: `1px solid ${accent}`,
  };
}

function practiceChipStyle(color = MAP_THEME.muted) {
  return {
    height: 22,
    display: "inline-flex",
    alignItems: "center",
    padding: "0 7px",
    borderRadius: 2,
    background: MAP_THEME.inset,
    border: `1px solid ${color}44`,
    color,
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: ".05em",
    fontFamily: "'Barlow Condensed',sans-serif",
    fontWeight: 700,
  };
}

function PracticePanel({ queue = [], onStart }) {
  if (!queue.length) return null;
  return (
    <div style={practicePanelStyle(MAP_THEME.amber, { marginBottom: 0 })}>
      <div style={practiceHeaderStyle()}>
        <div>
          <div style={practiceKickerStyle(MAP_THEME.amber)}>
            Build Coverage
          </div>
          <div style={{ marginTop: 3, color: MAP_THEME.muted, fontSize: 12 }}>
            Continue through weak or unstudied paragraphs in 7110 order.
          </div>
        </div>
        <button
          onClick={onStart}
          style={practiceActionStyle(MAP_THEME.amber, true)}
        >
          Continue
        </button>
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        {queue.slice(0, 4).map((item) => (
          <div
            key={item.para_id}
            style={practiceRowStyle("82px minmax(0,1fr) auto")}
          >
            <div style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              color: MAP_THEME.text,
              letterSpacing: ".04em",
            }}>
              § {item.para_id}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: MAP_THEME.text, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {item.title}
              </div>
              <div style={{ color: MAP_THEME.muted, fontSize: 11, marginTop: 2 }}>
                {item.sectionLabel}
              </div>
            </div>
            <div style={{ display: "flex", gap: 5, alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap" }}>
              {(item.focusReasons || []).slice(0, 2).map((reason) => (
                <span key={reason} style={practiceChipStyle(MAP_THEME.muted)}>
                  {reason}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConceptPanel({ queue = [], onStart }) {
  if (!queue.length) return null;
  const accent = MAP_THEME.green;
  return (
    <div style={practicePanelStyle(accent, { marginBottom: queue.length ? 14 : 0 })}>
      <div style={practiceHeaderStyle()}>
        <div>
          <div style={practiceKickerStyle(accent)}>
            Transfer Weak Ideas
          </div>
          <div style={{ marginTop: 3, color: MAP_THEME.muted, fontSize: 12 }}>
            Re-test the same idea across contexts so it is not tied to one paragraph.
          </div>
        </div>
        <button
          onClick={() => onStart(queue.slice(0, 3).map((item) => item.id), 6)}
          style={practiceActionStyle(accent, true)}
        >
          Strengthen
        </button>
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        {queue.slice(0, 4).map((item) => (
          <div
            key={item.id}
            style={practiceRowStyle("minmax(0,1fr) auto")}
          >
            <div style={{ minWidth: 0 }}>
              <div style={{
                color: MAP_THEME.text,
                fontFamily: "'Barlow Condensed',sans-serif",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: ".04em",
                textTransform: "uppercase",
              }}>
                {item.label}
              </div>
              <div style={{ color: MAP_THEME.muted, fontSize: 11, marginTop: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {(item.paragraphs || []).slice(0, 2).map((paragraph) => `§ ${paragraph.para_id}`).join(" · ")}
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={practiceChipStyle(MAP_THEME.red)}>
                {item.misses} miss{item.misses === 1 ? "" : "es"}
              </span>
              <button
                onClick={() => onStart([item.id], 3)}
                style={{ ...practiceActionStyle(accent), height: 25, padding: "0 9px", fontSize: 10 }}
              >
                Drill
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PracticeModesPanel({ onStart }) {
  const modes = [
    {
      id: "diagnostic",
      label: "Find Gaps",
      detail: "A short mixed check when you do not know what to study next.",
      color: "#7aa7d9",
      count: 10,
    },
    {
      id: "weak_areas",
      label: "Repair Weak Areas",
      detail: "Adaptive practice from low crowns and low recent accuracy.",
      color: "#f43f5e",
      count: 8,
    },
    {
      id: "tables_minima",
      label: "Tables & Minima",
      detail: "Lookup discipline for numeric rules, minima, and source tables.",
      color: MAP_THEME.amber,
      count: 8,
    },
    {
      id: "phraseology",
      label: "Phraseology",
      detail: "Exact wording only where the order makes exact wording matter.",
      color: "#39c36f",
      count: 8,
    },
    {
      id: "scenarios",
      label: "Scenario Judgment",
      detail: "Choose what to do when the facts change.",
      color: "#fb923c",
      count: 8,
    },
    {
      id: "visuals",
      label: "Figures & Visuals",
      detail: "Practice extracting the rule from figures and diagrams.",
      color: "#818cf8",
      count: 6,
    },
  ];

  return (
    <div style={practicePanelStyle(MAP_THEME.amber, { marginBottom: 0 })}>
      <div style={{ ...practiceKickerStyle(MAP_THEME.amber), marginBottom: 10 }}>
        Isolate A Skill
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
        {modes.map((mode) => (
          <button
            key={mode.id}
            onClick={() => onStart(mode.id, mode.count, mode.label)}
            style={{
              textAlign: "left",
              background: MAP_THEME.panel2,
              border: `1px solid ${MAP_THEME.line}`,
              borderLeft: `2px solid ${mode.color}`,
              borderRadius: 2,
              padding: "10px 11px",
              cursor: "pointer",
              minHeight: 72,
              transition: "background .15s, border-color .15s",
            }}
            onMouseEnter={(event) => {
              event.currentTarget.style.background = "#171812";
              event.currentTarget.style.borderColor = MAP_THEME.line2;
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.background = MAP_THEME.panel2;
              event.currentTarget.style.borderColor = MAP_THEME.line;
            }}
          >
            <div style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: ".07em",
              color: mode.color,
              textTransform: "uppercase",
              marginBottom: 4,
            }}>
              {mode.label}
            </div>
            <div style={{ color: MAP_THEME.muted, fontSize: 11, lineHeight: 1.35 }}>
              {mode.detail}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function MissedItemsPanel({ queue = [], onStart }) {
  if (!queue.length) return null;
  const accent = MAP_THEME.red;
  return (
    <div style={practicePanelStyle(accent, { marginBottom: 16 })}>
      <div style={practiceHeaderStyle()}>
        <div>
          <div style={practiceKickerStyle(accent)}>
            Fix Recent Misses
          </div>
          <div style={{ marginTop: 3, color: MAP_THEME.muted, fontSize: 12 }}>
            Start here when available. Exact retries clear only after a correct answer.
          </div>
        </div>
        <button
          onClick={onStart}
          style={practiceActionStyle(accent, true)}
        >
          Fix
        </button>
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        {queue.slice(0, 3).map((item) => (
          <div key={item.activityId} style={practiceRowStyle("78px minmax(0,1fr) auto", `${accent}44`)}>
            <div style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              color: MAP_THEME.text,
              letterSpacing: ".04em",
            }}>
              § {item.para_id}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: MAP_THEME.text, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {item.title}
              </div>
              <div style={{ color: MAP_THEME.muted, fontSize: 11, marginTop: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {item.questionText}
              </div>
            </div>
            <span style={practiceChipStyle(accent)}>
              {item.misses}x
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DueReviewPanel({ queue = [], onStart }) {
  if (!queue.length) return null;
  const accent = MAP_THEME.blue;
  return (
    <div style={practicePanelStyle(accent, { marginBottom: 16 })}>
      <div style={practiceHeaderStyle()}>
        <div>
          <div style={practiceKickerStyle(accent)}>
            Refresh Memory
          </div>
          <div style={{ marginTop: 3, color: MAP_THEME.muted, fontSize: 12 }}>
            Keep older material alive before adding more new sections.
          </div>
        </div>
        <button
          onClick={onStart}
          style={practiceActionStyle(accent, true)}
        >
          Refresh
        </button>
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        {queue.slice(0, 3).map((item) => (
          <div key={item.para_id} style={practiceRowStyle("78px minmax(0,1fr) auto", `${accent}44`)}>
            <div style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              color: MAP_THEME.text,
              letterSpacing: ".04em",
            }}>
              § {item.para_id}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: MAP_THEME.text, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {item.title}
              </div>
              <div style={{ color: MAP_THEME.muted, fontSize: 11, marginTop: 2 }}>
                {item.dueReason}{item.recentScore !== null ? ` · recent ${item.recentScore}%` : ""}
              </div>
            </div>
            <span style={practiceChipStyle(accent)}>
              L{item.crown}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function NextActionPanel({ action, onStart, onDismiss }) {
  if (!action) return null;
  return (
    <div style={practicePanelStyle(action.color, {
      position: "relative",
      overflow: "hidden",
      padding: "11px 12px",
      marginBottom: 12,
    })}>
      <div className="map-next-action-orb" style={{
        position: "absolute",
        right: -30,
        top: -42,
        width: 112,
        height: 112,
        borderRadius: "50%",
        background: `${action.color}08`,
        filter: "blur(2px)",
      }} />
      <div className="map-next-action-row" style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".1em",
            color: action.color,
            textTransform: "uppercase",
            marginBottom: 3,
          }}>
            Next Step
          </div>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 17,
            fontWeight: 700,
            letterSpacing: ".03em",
            color: MAP_THEME.text,
            marginBottom: 2,
          }}>
            {action.label}
          </div>
          <div style={{ color: MAP_THEME.muted, fontSize: 12, lineHeight: 1.4, maxWidth: 620 }}>
            {action.detail}
          </div>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            marginTop: 7,
            height: 21,
            padding: "0 7px",
            borderRadius: 2,
            background: `${action.color}14`,
            border: `1px solid ${action.color}33`,
            color: action.color,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 9.5,
            fontWeight: 700,
            letterSpacing: ".07em",
            textTransform: "uppercase",
          }}>
            {action.reason}
          </div>
        </div>
        <div className="map-next-action-actions" style={{ display: "flex", alignItems: "center", gap: 8, position: "relative" }}>
          {onDismiss && (
            <button
              onClick={onDismiss}
              title="Hide suggestion"
              style={{
                width: 30,
                height: 30,
                borderRadius: 2,
                border: `1px solid ${MAP_THEME.line2}`,
                background: MAP_THEME.inset,
                color: MAP_THEME.faint,
                cursor: "pointer",
                fontSize: 14,
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
          <button
            onClick={() => onStart(action)}
            style={{ ...practiceActionStyle(action.color, true), height: 36 }}
          >
            {action.buttonLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function StudyPlanPanel({ plan = [] }) {
  if (!plan.length) return null;
  return (
    <div className="map-aircraft-workspace" style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
      gap: 8,
      margin: "-6px 0 16px",
    }}>
      {plan.map((step, index) => (
        <div key={step.key} style={{
          background: MAP_THEME.panel2,
          border: `1px solid ${MAP_THEME.line}`,
          borderTop: `2px solid ${step.color}`,
          borderRadius: 2,
          padding: "10px 11px",
          minHeight: 78,
          position: "relative",
          overflow: "hidden",
        }}>
          <div style={{
            position: "absolute",
            right: -18,
            top: -18,
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: `${step.color}08`,
          }} />
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".09em",
            textTransform: "uppercase",
            color: step.color,
            marginBottom: 5,
            position: "relative",
          }}>
            Step {index + 1}
          </div>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: ".04em",
            color: MAP_THEME.text,
            textTransform: "uppercase",
            position: "relative",
          }}>
            {step.label}
          </div>
          <div style={{
            marginTop: 3,
            color: MAP_THEME.muted,
            fontSize: 11,
            lineHeight: 1.35,
            position: "relative",
          }}>
            {step.detail}
          </div>
        </div>
      ))}
    </div>
  );
}

function PracticeWorkspaceToggle({
  open,
  onToggle,
  mistakeCount = 0,
  dueCount = 0,
  conceptCount = 0,
  practiceCount = 0,
}) {
  const totalSignals = mistakeCount + dueCount + conceptCount + practiceCount;
  return (
    <button
      onClick={onToggle}
      style={{
        width: "100%",
        minHeight: 48,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        background: MAP_THEME.paper,
        border: `1px solid ${open ? MAP_THEME.line2 : MAP_THEME.line}`,
        borderTop: `2px solid ${open ? MAP_THEME.amber : MAP_THEME.line}`,
        borderRadius: 2,
        padding: "10px 13px",
        color: MAP_THEME.text,
        cursor: "pointer",
        marginBottom: open ? 12 : 16,
        textAlign: "left",
      }}
    >
      <div>
        <div style={{
          fontFamily: "'Barlow Condensed',sans-serif",
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: ".09em",
          color: open ? MAP_THEME.amber : MAP_THEME.muted,
          textTransform: "uppercase",
        }}>
          {open ? "Hide Practice Workspace" : "Show Practice Workspace"}
        </div>
        <div style={{ marginTop: 3, fontSize: 12, color: MAP_THEME.muted, lineHeight: 1.4 }}>
          The loop is: fix misses, refresh older material, transfer weak ideas, then build new coverage.
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap", justifyContent: "flex-end" }}>
        {[
          { label: "Miss", value: mistakeCount, color: "#f43f5e" },
          { label: "Due", value: dueCount, color: "#7aa7d9" },
          { label: "Concept", value: conceptCount, color: "#39c36f" },
          { label: "Practice", value: practiceCount, color: MAP_THEME.amber },
        ].filter((item) => item.value > 0).slice(0, 4).map((item) => (
          <span key={item.label} style={{ ...practiceChipStyle(item.color), padding: "0 8px", whiteSpace: "nowrap" }}>
            {item.value} {item.label}
          </span>
        ))}
        {totalSignals === 0 && (
          <span style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            color: MAP_THEME.faint,
            letterSpacing: ".08em",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}>
            No active signals
          </span>
        )}
        <span style={{ color: open ? MAP_THEME.amber : MAP_THEME.faint, fontSize: 16 }}>
          {open ? "⌃" : "⌄"}
        </span>
      </div>
    </button>
  );
}

function BrowseHeader() {
  return (
    <div className="map-browse-header" style={{
      display: "flex",
      alignItems: "flex-end",
      justifyContent: "space-between",
      gap: 12,
      margin: "4px 0 12px",
    }}>
      <div>
        <div style={{
          fontFamily: "'Barlow Condensed',sans-serif",
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: ".06em",
          color: MAP_THEME.text,
          textTransform: "uppercase",
        }}>
          Browse the 7110
        </div>
        <div style={{ marginTop: 3, color: MAP_THEME.muted, fontSize: 12 }}>
          Navigate by chapter and section first. Filters narrow the map without changing FAA order.
        </div>
      </div>
      <div className="map-browse-order" style={{
        fontFamily: "'Barlow Condensed',sans-serif",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: ".08em",
        color: MAP_THEME.faint,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}>
        Default: 7110 order
      </div>
    </div>
  );
}

function BrowseSummary({ chapters = [], filteredCount = 0 }) {
  const sectionCount = chapters.reduce((sum, chapter) => sum + chapter.sections.length, 0);
  const activityCount = chapters.reduce((sum, chapter) => sum + (chapter.totalActs || 0), 0);
  const cardCount = chapters.reduce((sum, chapter) => sum + (chapter.totalCards || 0), 0);
  const questionCount = chapters.reduce((sum, chapter) => sum + (chapter.totalQuestions || 0), 0);
  return (
    <div style={mapPanelStyle({
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 12,
      flexWrap: "wrap",
      padding: "10px 12px",
      marginBottom: 12,
    })}>
      <div style={{ color: MAP_THEME.muted, fontSize: 12, lineHeight: 1.45 }}>
        Open a chapter to choose a section. Nothing is expanded by default so the page stays navigational.
      </div>
      <div className="map-summary-stats" style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
        {[
          { label: "Chapters", value: filteredCount || chapters.length },
          { label: "Sections", value: sectionCount },
          { label: "Acts", value: activityCount },
          { label: "Qs", value: questionCount },
          { label: "Cards", value: cardCount },
        ].map((item) => (
          <span key={item.label} style={{
            height: 23,
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            padding: "0 8px",
            borderRadius: 2,
            background: MAP_THEME.inset,
            border: `1px solid ${MAP_THEME.line}`,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".06em",
            textTransform: "uppercase",
            color: MAP_THEME.faint,
          }}>
            <strong style={{ color: MAP_THEME.text }}>{item.value}</strong> {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function PublicUseNotice() {
  return (
    <div style={mapPanelStyle({
      padding: "12px 14px",
      marginBottom: 16,
      borderColor: "rgba(224,163,10,.28)",
      background: "linear-gradient(135deg, rgba(224,163,10,.10), rgba(13,17,15,.92))",
      fontSize: 12,
      lineHeight: 1.6,
      color: MAP_THEME.muted,
    })}>
      <strong style={{
        color: MAP_THEME.amber,
        fontFamily: "'Barlow Condensed',sans-serif",
        letterSpacing: ".08em",
        textTransform: "uppercase",
      }}>
        Unofficial Study Aid:
      </strong>
      {" "}
      This platform is not affiliated with or endorsed by the FAA. It is not operational guidance,
      legal guidance, or a substitute for current FAA orders, facility directives, LOAs, training
      materials, or instructor/supervisor direction. Generated and curated items may contain errors;
      use source links to verify against current official material.
    </div>
  );
}

function HomeTabs({ activeTab, onChange, practiceSignals = 0 }) {
  const tabs = [
    { id: "browse", label: "Browse 7110", detail: "Chapter navigation" },
    { id: "practice", label: "Practice Workspace", detail: practiceSignals ? `${practiceSignals} active signals` : "Guided study loop" },
    { id: "aircraft", label: "Aircraft Recognition", detail: "Type designators + runway separation" },
  ];

  return (
    <div style={{
      display: "flex",
      alignItems: "stretch",
      gap: 6,
      margin: "0 0 16px",
      padding: 4,
      border: `1px solid ${MAP_THEME.line}`,
      borderRadius: 2,
      background: MAP_THEME.paper,
    }} className="map-home-tabs">
      {tabs.map((tab) => {
        const active = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            style={{
              flex: 1,
              minHeight: 44,
              textAlign: "left",
              borderRadius: 2,
              border: `1px solid ${active ? "rgba(216,162,28,.42)" : "transparent"}`,
              background: active ? "#18150d" : "transparent",
              color: MAP_THEME.text,
              cursor: "pointer",
              padding: "9px 11px",
            }}
          >
            <div style={{
              fontFamily: "'Share Tech Mono', ui-monospace, monospace",
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: ".08em",
              textTransform: "uppercase",
              color: active ? MAP_THEME.amber : MAP_THEME.muted,
            }}>
              {String(tabs.indexOf(tab) + 1).padStart(2, "0")} / {tab.label}
            </div>
            <div style={{ marginTop: 2, fontSize: 12, color: MAP_THEME.faint }}>
              {tab.detail}
            </div>
          </button>
        );
      })}
    </div>
  );
}

const AIRCRAFT_CARD_TYPE_OPTIONS = [
  { id: "aircraft_designator", label: "Designator → facts" },
  { id: "aircraft_model", label: "Aircraft → designator" },
  { id: "aircraft_srs", label: "Same runway separation" },
];
const DEFAULT_AIRCRAFT_CARD_TYPES = AIRCRAFT_CARD_TYPE_OPTIONS.map((item) => item.id);

const AIRCRAFT_GROUP_OPTIONS = [
  { id: "all", label: "All aircraft" },
  { id: "cessna", label: "Cessna family" },
  { id: "piper", label: "Piper family" },
  { id: "beechcraft", label: "Beechcraft family" },
  { id: "airline_transport", label: "Airline / transport" },
  { id: "business_jets", label: "Business jets" },
  { id: "helicopters", label: "Helicopters" },
  { id: "ga_light", label: "GA / light aircraft" },
  { id: "other_conversion", label: "Other / conversions" },
];

function aircraftCardFacets(card, facet) {
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

function aircraftCardMakers(card) {
  return aircraftCardFacets(card, "make").map((maker) => maker.toLowerCase());
}

function aircraftCardText(card) {
  return `${card?.front || ""} ${card?.back || ""}`.toLowerCase();
}

function aircraftCardMatchesGroup(card, group) {
  if (!group || group === "all") return true;
  const makers = aircraftCardMakers(card);
  const text = aircraftCardText(card);
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
    ].some((item) => aircraftCardMatchesGroup(card, item));
  }
  return true;
}

function uniqueAircraftFacet(cards, facet) {
  return [...new Set(cards.flatMap((card) => aircraftCardFacets(card, facet)))]
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

function aircraftCardMatches(card, filters) {
  if (filters.types.length && !filters.types.includes(card.card_type)) return false;
  if (!aircraftCardMatchesGroup(card, filters.group || "all")) return false;
  for (const facet of ["cwt", "srs", "wake"]) {
    if (filters[facet] !== "all" && !aircraftCardFacets(card, facet).includes(filters[facet])) return false;
  }
  return true;
}

function AircraftRecognitionWorkspace({
  cardCount = 0,
  aircraftCards = [],
  imageCandidateCount = 0,
  imageApprovedCount = 0,
  onOpenImageReview,
  onStartImages,
  onStart,
}) {
  const [filters, setFilters] = useState({
    types: DEFAULT_AIRCRAFT_CARD_TYPES,
    cwt: "all",
    srs: "all",
    wake: "all",
    group: "all",
    limit: "0",
    order: "shuffle",
    direction: "normal",
  });
  const facets = useMemo(() => ({
    cwt: uniqueAircraftFacet(aircraftCards, "cwt"),
    srs: uniqueAircraftFacet(aircraftCards, "srs"),
    wake: uniqueAircraftFacet(aircraftCards, "wake"),
  }), [aircraftCards]);
  const matchedCards = useMemo(() => {
    const matched = aircraftCards.filter((card) => aircraftCardMatches(card, filters));
    const limit = Number(filters.limit || 0);
    return limit > 0 ? matched.slice(0, limit) : matched;
  }, [aircraftCards, filters]);

  const updateFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  const toggleType = (typeId) => setFilters((current) => {
    const nextTypes = current.types.includes(typeId)
      ? current.types.filter((item) => item !== typeId)
      : [...current.types, typeId];
    return { ...current, types: nextTypes.length ? nextTypes : [typeId] };
  });
  const selectStyle = {
    width: "100%",
    height: 36,
    borderRadius: 6,
    border: `1px solid ${MAP_THEME.line2}`,
    background: MAP_THEME.inset,
    color: MAP_THEME.text,
    padding: "0 9px",
    fontFamily: "'Barlow',sans-serif",
    fontSize: 12,
    outline: "none",
  };
  const labelStyle = {
    display: "block",
    marginBottom: 5,
    fontFamily: "'Barlow Condensed',sans-serif",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: ".09em",
    textTransform: "uppercase",
    color: MAP_THEME.faint,
  };

  return (
    <div className="map-aircraft-workspace" style={{
      display: "grid",
      gridTemplateColumns: "1fr",
      gap: 14,
      alignItems: "start",
      marginBottom: 16,
    }}>
      <div className="map-aircraft-hero" style={{
        background: "linear-gradient(135deg, rgba(122,167,217,.1), rgba(13,17,15,.92) 44%, rgba(17,22,20,.95))",
        border: `1px solid ${MAP_THEME.line2}`,
        borderRadius: 2,
        padding: "14px 16px",
      }}>
        <div style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
        }}>
          <div style={{ minWidth: 240, flex: "1 1 520px" }}>
            <div style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: ".1em",
              textTransform: "uppercase",
              color: MAP_THEME.blue,
              marginBottom: 6,
            }}>
              Separate Workspace
            </div>
            <div className="map-aircraft-hero-title" style={{
              fontFamily: "'Barlow Condensed',sans-serif",
              fontSize: 25,
              fontWeight: 700,
              letterSpacing: ".03em",
              color: MAP_THEME.text,
              lineHeight: 1.05,
            }}>
              Aircraft Recognition
            </div>
            <div className="map-aircraft-copy" style={{
              marginTop: 7,
              maxWidth: 760,
              color: MAP_THEME.muted,
              fontSize: 13,
              lineHeight: 1.55,
            }}>
              Build focused decks for aircraft type designators, spoken names, wake categories, consolidated wake turbulence, and same-runway-separation categories.
            </div>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "flex-end", flex: "0 1 430px" }}>
            {[
              { label: "Type designators", color: "#7aa7d9" },
              { label: "Spoken aircraft names", color: "#39c36f" },
            { label: "Same runway separation", color: MAP_THEME.amber },
          ].map((item) => (
            <span key={item.label} style={{
              height: 25,
              display: "inline-flex",
              alignItems: "center",
              borderRadius: 2,
              border: `1px solid ${item.color}45`,
              background: `${item.color}14`,
              color: item.color,
              padding: "0 9px",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: ".08em",
              textTransform: "uppercase",
            }}>
              {item.label}
            </span>
          ))}
          </div>
        </div>
      </div>

      <div className="map-aircraft-controls" style={{
        background: MAP_THEME.panel,
        border: `1px solid ${MAP_THEME.line}`,
        borderRadius: 2,
        padding: 16,
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr)",
        gap: 18,
        alignItems: "start",
      }}>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 34,
            fontWeight: 700,
            color: MAP_THEME.text,
            lineHeight: 1,
          }}>
            {cardCount}
          </div>
          <div style={{
            marginTop: 5,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: ".09em",
            textTransform: "uppercase",
            color: MAP_THEME.faint,
          }}>
            Aircraft cards
          </div>
          <div style={{
            marginTop: 10,
            color: MAP_THEME.faint,
            fontSize: 12,
            lineHeight: 1.55,
          }}>
            Current subset: <strong style={{ color: MAP_THEME.text }}>{matchedCards.length}</strong> card{matchedCards.length === 1 ? "" : "s"}. Default order is shuffled; switch to ordered when you want a predictable JO 7360-style sweep.
            {imageCandidateCount > 0 && (
              <>
                <br />
                Images: <strong style={{ color: MAP_THEME.text }}>{imageApprovedCount}</strong> approved of {imageCandidateCount} candidate{imageCandidateCount === 1 ? "" : "s"}.
              </>
            )}
          </div>
          {(imageCandidateCount > 0 || onOpenImageReview) && (
            <div className="map-aircraft-review-grid" style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: 8,
              marginTop: 16,
            }}>
              <button
                onClick={onOpenImageReview}
                disabled={!onOpenImageReview}
                style={{
                  height: 40,
                  borderRadius: 2,
                  border: "1px solid rgba(129,140,248,.38)",
                  background: "rgba(129,140,248,.12)",
                  color: "#a5b4fc",
                  cursor: onOpenImageReview ? "pointer" : "default",
                  fontFamily: "'Barlow Condensed',sans-serif",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                }}
              >
                Review Images
              </button>
              <button
                onClick={onStartImages}
                disabled={imageApprovedCount <= 0}
                style={{
                  height: 40,
                  borderRadius: 2,
                  border: `1px solid ${imageApprovedCount > 0 ? "rgba(57,195,111,.42)" : "rgba(219,229,216,.13)"}`,
                  background: imageApprovedCount > 0 ? "rgba(57,195,111,.13)" : "rgba(7,10,9,.62)",
                  color: imageApprovedCount > 0 ? "#39c36f" : "#27302a",
                  cursor: imageApprovedCount > 0 ? "pointer" : "default",
                  fontFamily: "'Barlow Condensed',sans-serif",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                }}
              >
                Image Cards
              </button>
            </div>
          )}
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 0 }}>
          <div>
            <span style={labelStyle}>Card families</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {AIRCRAFT_CARD_TYPE_OPTIONS.map((item) => {
                const selected = filters.types.includes(item.id);
                return (
                  <button key={item.id} onClick={() => toggleType(item.id)} style={{
                    height: 28,
                    borderRadius: 2,
                    border: `1px solid ${selected ? "rgba(122,167,217,.44)" : MAP_THEME.line2}`,
                    background: selected ? "rgba(122,167,217,.11)" : MAP_THEME.inset,
                    color: selected ? MAP_THEME.blue : MAP_THEME.faint,
                    padding: "0 9px",
                    cursor: "pointer",
                    fontFamily: "'Barlow Condensed',sans-serif",
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: ".07em",
                    textTransform: "uppercase",
                  }}>
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="map-aircraft-filter-grid" style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            gap: 8,
            width: "100%",
          }}>
            {[
              ["group", "Aircraft Group"],
              ["cwt", "Consolidated Wake Turbulence"],
              ["srs", "Same Runway Separation"],
              ["wake", "Wake Turbulence"],
              ["limit", "Deck Size"],
            ].map(([key, label]) => (
              <label key={key}>
                <span style={labelStyle}>{label}</span>
                <select
                  value={filters[key]}
                  onChange={(event) => updateFilter(key, event.target.value)}
                  style={selectStyle}
                >
                  {key === "limit" ? (
                    <>
                      <option value="0">All matching</option>
                      <option value="25">25 cards</option>
                      <option value="50">50 cards</option>
                      <option value="100">100 cards</option>
                    </>
                  ) : key === "group" ? (
                    AIRCRAFT_GROUP_OPTIONS.map((option) => (
                      <option key={option.id} value={option.id}>{option.label}</option>
                    ))
                  ) : (
                    <>
                      <option value="all">All</option>
                      {(facets[key] || []).map((value) => (
                        <option key={value} value={value}>{value}</option>
                      ))}
                    </>
                  )}
                </select>
              </label>
            ))}
          </div>
          <div className="map-aircraft-filter-grid" style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 8,
            width: "100%",
          }}>
            <label>
              <span style={labelStyle}>Order</span>
              <select value={filters.order} onChange={(event) => updateFilter("order", event.target.value)} style={selectStyle}>
                <option value="shuffle">Shuffle</option>
                <option value="sequential">Sequential</option>
              </select>
            </label>
            <label>
              <span style={labelStyle}>Starting prompt</span>
              <select value={filters.direction} onChange={(event) => updateFilter("direction", event.target.value)} style={selectStyle}>
                <option value="normal">Identifier</option>
                <option value="reverse">Spoken name</option>
              </select>
            </label>
          </div>
          <button
            onClick={() => onStart({
              filters,
              order: filters.order,
              direction: filters.direction,
              promptMode: filters.direction === "reverse" ? "spoken" : "identifier",
              label: `Aircraft Recognition · ${matchedCards.length} Cards`,
            })}
            disabled={matchedCards.length <= 0}
            style={{
              width: "100%",
              height: 46,
              borderRadius: 2,
              border: "none",
              background: matchedCards.length > 0 ? MAP_THEME.blue : "rgba(219,229,216,.06)",
              color: matchedCards.length > 0 ? "#06101d" : "#27302a",
              cursor: matchedCards.length > 0 ? "pointer" : "default",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: ".08em",
              textTransform: "uppercase",
            }}
          >
            Study {matchedCards.length || 0} Cards
          </button>
        </div>
      </div>
    </div>
  );
}

function HeaderUtilities({
  stats,
  flaggedItemCount,
  onOpenFocus,
  onOpenReview,
  onResetProgress,
  onExportProgress,
  onImportProgress,
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((value) => !value)}
        style={{
          height: 34,
          padding: "0 12px",
          borderRadius: 6,
          cursor: "pointer",
          border: `1px solid ${MAP_THEME.line2}`,
          background: MAP_THEME.inset,
          color: MAP_THEME.text,
          fontFamily: "'Barlow Condensed',sans-serif",
          fontWeight: 700,
          fontSize: 11,
          letterSpacing: ".08em",
          textTransform: "uppercase",
        }}
      >
        Tools{stats?.focusCount || flaggedItemCount ? ` (${(stats?.focusCount || 0) + (flaggedItemCount || 0)})` : ""}
      </button>
      {open && (
        <div className="map-tools-menu" style={{
          position: "absolute",
          right: 0,
          top: 40,
          zIndex: 20,
          minWidth: 210,
          background: MAP_THEME.panel2,
          border: `1px solid ${MAP_THEME.line2}`,
          borderRadius: 2,
          padding: 8,
          boxShadow: "0 18px 42px rgba(0,0,0,.32)",
          display: "grid",
          gap: 7,
        }}>
          {onOpenFocus && (
            <button
              onClick={() => { setOpen(false); onOpenFocus(); }}
              style={utilityMenuButtonStyle()}
            >
              Issue Areas {stats?.focusCount ? `(${stats.focusCount})` : ""}
            </button>
          )}
          {onOpenReview && (
            <button
              onClick={() => { setOpen(false); onOpenReview(); }}
              style={utilityMenuButtonStyle()}
            >
              QA Review{flaggedItemCount ? ` (${flaggedItemCount})` : ""}
            </button>
          )}
          {onExportProgress && (
            <button
              onClick={() => { setOpen(false); onExportProgress(); }}
              style={utilityMenuButtonStyle()}
            >
              Export Progress
            </button>
          )}
          {onImportProgress && (
            <button
              onClick={() => { setOpen(false); onImportProgress(); }}
              style={utilityMenuButtonStyle()}
            >
              Import Progress
            </button>
          )}
          {onResetProgress && (
            <button
              onClick={() => { setOpen(false); onResetProgress(); }}
              style={{
                ...utilityMenuButtonStyle(),
                color: "#f43f5e",
                borderColor: "rgba(244,63,94,.28)",
                background: "rgba(244,63,94,.08)",
              }}
            >
              Reset Progress
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function utilityMenuButtonStyle() {
  return {
    height: 34,
    width: "100%",
    padding: "0 10px",
    borderRadius: 6,
    border: `1px solid ${MAP_THEME.line2}`,
    background: MAP_THEME.inset,
    color: MAP_THEME.text,
    cursor: "pointer",
    textAlign: "left",
    fontFamily: "'Barlow Condensed',sans-serif",
    fontWeight: 700,
    fontSize: 11,
    letterSpacing: ".08em",
    textTransform: "uppercase",
  };
}

const SECTION_FILTERS = [
  { id: "all", label: "All", detail: "7110 order" },
  { id: "new", label: "New", detail: "Unstarted sections" },
  { id: "weak", label: "Weak", detail: "Low crowns / recommended" },
  { id: "due", label: "Due", detail: "Scheduled review" },
  { id: "focused", label: "Focused", detail: "Manual list" },
  { id: "phraseology", label: "Phraseology", detail: "Wording / readbacks" },
  { id: "tables_visuals", label: "Tables + Figures", detail: "Tables, minima, visuals" },
  { id: "cards", label: "Cards", detail: "Flashcard coverage" },
];

const PHRASEOLOGY_TYPES = new Set([
  "phraseology_builder",
  "readback_check",
  "spot_the_error",
  "example_check",
]);

const TABLE_VISUAL_TYPES = new Set([
  "table_lookup",
  "minima_rule_check",
  "visual_interpretation",
]);

function buildSectionBadges(section, signals) {
  const badges = [];
  const add = (label, color) => {
    if (!badges.some((badge) => badge.label === label)) badges.push({ label, color });
  };

  const isNew = section.acts > 0 && (section.maxCrown || 0) === 0;
  if (isNew) {
    add("New", "#7aa7d9");
  } else if (signals?.weakSections?.has(section.key) || (section.acts > 0 && (section.avgCrown || 0) < 2.5)) {
    add("Weak", "#f43f5e");
  }
  if (signals?.dueSections?.has(section.key)) add("Due", "#7aa7d9");
  if (signals?.focusedSections?.has(section.key)) add("Focused", MAP_THEME.amber);
  if ((section.activityTypes || []).some((type) => PHRASEOLOGY_TYPES.has(type))) {
    add("Phraseology", "#39c36f");
  }
  if ((section.activityTypes || []).some((type) => TABLE_VISUAL_TYPES.has(type))) {
    add("Tables/Figures", "#818cf8");
  }
  return badges.slice(0, 3);
}

function sectionKeyForItem(item) {
  if (!item) return null;
  return `${item.chapter}-${item.section}`;
}

function sectionMatchesFilter(section, filterId, signals) {
  if (filterId === "all") return true;
  if (filterId === "new") return section.acts > 0 && (section.maxCrown || 0) === 0;
  if (filterId === "weak") {
    const hasProgress = (section.maxCrown || 0) > 0;
    return (hasProgress && signals.weakSections.has(section.key))
      || ((section.avgCrown || 0) > 0 && (section.avgCrown || 0) < 2.5);
  }
  if (filterId === "due") return signals.dueSections.has(section.key);
  if (filterId === "focused") return signals.focusedSections.has(section.key);
  if (filterId === "phraseology") {
    return (section.activityTypes || []).some((type) => PHRASEOLOGY_TYPES.has(type));
  }
  if (filterId === "tables_visuals") {
    return (section.activityTypes || []).some((type) => TABLE_VISUAL_TYPES.has(type));
  }
  if (filterId === "cards") return (section.fcs || 0) > 0;
  return true;
}

function SectionFilterBar({ filters, activeFilter, onChange }) {
  const [showAll, setShowAll] = useState(false);
  const primaryIds = new Set(["all", "new", "weak", "due"]);
  const visibleFilters = showAll ? filters : filters.filter((filter) => primaryIds.has(filter.id));
  const hiddenActive = !primaryIds.has(activeFilter);
  return (
    <div style={mapPanelStyle({
      padding: "9px 10px",
      marginBottom: 12,
    })}>
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 10,
        marginBottom: 8,
      }}>
        <div style={{
          fontFamily: "'Barlow Condensed',sans-serif",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: ".09em",
          color: MAP_THEME.amber,
          textTransform: "uppercase",
        }}>
          Navigate by Need
        </div>
        <div style={{ fontSize: 11, color: MAP_THEME.faint }}>
          FAA order stays fixed.
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
        {visibleFilters.map((filter) => {
          const active = filter.id === activeFilter;
          return (
            <button
              key={filter.id}
              onClick={() => onChange(filter.id)}
              disabled={filter.count === 0}
              title={filter.detail}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                minHeight: 31,
                borderRadius: 2,
                padding: "0 10px",
                border: `1px solid ${active ? "rgba(224,163,10,.55)" : MAP_THEME.line2}`,
                background: active ? "rgba(224,163,10,.11)" : MAP_THEME.inset,
                color: active ? MAP_THEME.amber : (filter.count === 0 ? "#27302a" : MAP_THEME.muted),
                cursor: filter.count === 0 ? "default" : "pointer",
                fontFamily: "'Barlow Condensed',sans-serif",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: ".06em",
                textTransform: "uppercase",
                opacity: filter.count === 0 ? 0.45 : 1,
              }}
            >
              <span>{filter.label}</span>
              <span style={{
                minWidth: 18,
                height: 18,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 2,
                background: active ? "rgba(224,163,10,.16)" : "rgba(219,229,216,.05)",
                color: active ? MAP_THEME.amber : MAP_THEME.faint,
                fontSize: 10,
              }}>
                {filter.count}
              </span>
            </button>
          );
        })}
        <button
          onClick={() => setShowAll((value) => !value)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            minHeight: 31,
            borderRadius: 2,
            padding: "0 10px",
            border: `1px solid ${hiddenActive ? "rgba(224,163,10,.55)" : MAP_THEME.line2}`,
            background: hiddenActive ? "rgba(224,163,10,.12)" : MAP_THEME.inset,
            color: hiddenActive ? MAP_THEME.amber : MAP_THEME.muted,
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: ".06em",
            textTransform: "uppercase",
          }}
        >
          {showAll ? "Fewer Filters" : "More Filters"}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function CurriculumMap({
  chapters,
  stats,
  practiceQueue,
  conceptQueue,
  mistakeQueue,
  dueReviewQueue,
  focusParagraphs,
  flaggedItemCount,
  nextAction,
  studyPlan,
  publishConfig,
  viewState = {},
  onViewStateChange,
  onStartNextAction,
  onStartRecommended,
  onStartDueReview,
  onStartMissedItems,
  onStartPracticeMode,
  onStartConceptReview,
  onStartLesson,
  onStartFlashcards,
  onOpenSection,
  onOpenFocus,
  onOpenReview,
  onResetProgress,
  onExportProgress,
  onImportProgress,
  aircraftCardCount = 0,
  aircraftCards = [],
  aircraftImageCandidateCount = 0,
  aircraftImageApprovedCount = 0,
  onOpenAircraftImageReview,
  onStartAircraftImages,
  onStartAircraftRecognition,
}) {
  const search = viewState.search || "";
  const activeFilter = viewState.activeFilter || "all";
  const activeHomeTab = viewState.activeHomeTab || "browse";
  const showSuggestion = viewState.showSuggestion !== false;
  const openChapters = viewState.openChapters || {};
  const patchViewState = (patch) => {
    if (onViewStateChange) onViewStateChange(patch);
  };
  const setSearch = (value) => patchViewState({ search: value });
  const setActiveFilter = (value) => patchViewState({ activeFilter: value });
  const setActiveHomeTab = (value) => patchViewState({ activeHomeTab: value });
  const setShowSuggestion = (value) => patchViewState({ showSuggestion: value });
  const setChapterOpen = (chapter, isOpen) => patchViewState((current) => ({
    openChapters: {
      ...(current.openChapters || {}),
      [String(chapter)]: isOpen,
    },
  }));

  const sectionSignals = useMemo(() => ({
    weakSections: new Set([
      ...(practiceQueue || []).map(sectionKeyForItem),
      ...(conceptQueue || []).flatMap((item) => (item.paragraphs || []).map(sectionKeyForItem)),
      ...(mistakeQueue || []).map(sectionKeyForItem),
    ].filter(Boolean)),
    dueSections: new Set((dueReviewQueue || []).map(sectionKeyForItem).filter(Boolean)),
    focusedSections: new Set((focusParagraphs || []).map(sectionKeyForItem).filter(Boolean)),
  }), [conceptQueue, dueReviewQueue, focusParagraphs, mistakeQueue, practiceQueue]);

  const sectionFilterCounts = useMemo(() => (
    Object.fromEntries(SECTION_FILTERS.map((filter) => [
      filter.id,
      chapters.reduce((sum, chapter) => (
        sum + chapter.sections.filter((section) => sectionMatchesFilter(section, filter.id, sectionSignals)).length
      ), 0),
    ]))
  ), [chapters, sectionSignals]);

  const filtersWithCounts = SECTION_FILTERS.map((filter) => ({
    ...filter,
    count: sectionFilterCounts[filter.id] || 0,
  }));

  const filtered = useMemo(() => {
    const filterId = sectionFilterCounts[activeFilter] === 0 ? "all" : activeFilter;
    const q = search.toLowerCase();
    return chapters.map(ch => ({
      ...ch,
      sections: ch.sections.filter((s) => {
        const matchesSearch = !search.trim()
          || s.label.toLowerCase().includes(q)
          || ch.title.toLowerCase().includes(q);
        return matchesSearch && sectionMatchesFilter(s, filterId, sectionSignals);
      }),
    })).filter(ch => ch.sections.length > 0);
  }, [activeFilter, chapters, search, sectionFilterCounts, sectionSignals]);
  const hasAdaptiveAlternatives = Boolean(
    practiceQueue?.length ||
    conceptQueue?.length ||
    mistakeQueue?.length ||
    dueReviewQueue?.length
  );
  const practiceSignalCount = (mistakeQueue?.length || 0)
    + (dueReviewQueue?.length || 0)
    + (conceptQueue?.length || 0)
    + (practiceQueue?.length || 0);

  return (
    <div className="map-shell" style={{
      fontFamily: "'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
      background: MAP_THEME.bg,
      minHeight: "100vh",
      color: MAP_THEME.text,
    }}>
      <style>{MAP_CSS}</style>
      {/* Top header */}
      <div className="map-header" style={{
        padding: "22px 20px 0",
      }}>
        <div style={{
          maxWidth: 1120,
          margin: "0 auto",
          background: MAP_THEME.paper,
          border: `1px solid ${MAP_THEME.line}`,
          borderBottom: "none",
          padding: "18px 18px 0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }} className="map-topbar">
          <div>
            <div style={{
              fontFamily: "'Share Tech Mono', ui-monospace, monospace", fontSize: 22,
              fontWeight: 700, letterSpacing: ".04em", color: MAP_THEME.amber,
            }}>ATC 7110.65</div>
            <div style={{ fontSize: 12, color: MAP_THEME.faint, marginTop: 2 }}>
              JO 7110.65BB Change 2 · Study Platform
            </div>
          </div>
          <div className="map-actions" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <HeaderUtilities
              stats={stats}
              flaggedItemCount={flaggedItemCount}
              onOpenFocus={onOpenFocus}
              onOpenReview={onOpenReview}
              onResetProgress={onResetProgress}
              onExportProgress={onExportProgress}
              onImportProgress={onImportProgress}
            />
            <div style={{
              background: MAP_THEME.amber, color: "#090a08", fontFamily: "'Share Tech Mono', ui-monospace, monospace",
              fontWeight: 700, fontSize: 11, letterSpacing: ".08em",
              padding: "4px 10px", borderRadius: 2, textTransform: "uppercase",
            }}>
              BB CHG 2
            </div>
          </div>
        </div>
      </div>

      <div className="map-main" style={{
        padding: "16px 18px 28px",
        maxWidth: 1120,
        margin: "0 auto 28px",
        background: MAP_THEME.paper,
        border: `1px solid ${MAP_THEME.line}`,
        borderTop: "none",
      }}>
        {publishConfig && (
          (stats?.hiddenParaCount > 0 || publishConfig.reviewPersistenceMode !== "backend") && (
          <div style={mapPanelStyle({
            padding: "12px 14px",
            marginBottom: 16,
            fontSize: 12,
            lineHeight: 1.6,
            color: MAP_THEME.muted,
          })}>
            <strong style={{
              color: MAP_THEME.amber,
              fontFamily: "'Barlow Condensed',sans-serif",
              letterSpacing: ".08em",
              textTransform: "uppercase",
            }}>
              Publish Mode:
            </strong>
            {" "}
            {publishConfig.label}. {publishConfig.description}
            {stats?.hiddenParaCount > 0 && (
              <>
                {" "}
                {stats.hiddenParaCount} paragraph{stats.hiddenParaCount === 1 ? "" : "s"} currently hidden from learner-facing study.
              </>
            )}
            {publishConfig.reviewPersistenceMode === "local_static" && (
              <>
                {" "}
                Static site mode: review edits are stored in this browser only.
              </>
            )}
            {publishConfig.reviewPersistenceMode !== "backend" && publishConfig.reviewPersistenceMode !== "local_static" && (
              <>
                {" "}
                Review-state backend unavailable: {publishConfig.reviewPersistenceError || "unknown error"}.
              </>
            )}
          </div>
          )
        )}

        {publishConfig?.reviewPersistenceMode === "local_static" && (
          <PublicUseNotice />
        )}

        {showSuggestion && (
          <NextActionPanel
            action={nextAction}
            onStart={onStartNextAction}
            onDismiss={() => setShowSuggestion(false)}
          />
        )}
        <HomeTabs
          activeTab={activeHomeTab}
          onChange={setActiveHomeTab}
          practiceSignals={practiceSignalCount}
        />

        {activeHomeTab === "practice" && (
          <>
            {stats && <StatsStrip stats={stats} />}
            <StudyPlanPanel plan={studyPlan} />
            {hasAdaptiveAlternatives && (
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                margin: "0 0 10px",
              }}>
                <div style={{
                  fontFamily: "'Barlow Condensed',sans-serif",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: ".09em",
                  color: MAP_THEME.faint,
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                }}>
                  Practice Options
                </div>
                <div style={{ flex: 1, height: 1, background: MAP_THEME.line }} />
                <div style={{
                  fontSize: 11,
                  color: MAP_THEME.faint,
                }}>
                  Override the recommendation when you want a specific drill.
                </div>
              </div>
            )}
            <MissedItemsPanel queue={mistakeQueue} onStart={onStartMissedItems} />
            <DueReviewPanel queue={dueReviewQueue} onStart={onStartDueReview} />
            <div
              className="map-practice-grid"
              style={{
                display: "grid",
                gridTemplateColumns: "1fr",
                gap: 12,
                alignItems: "start",
                marginBottom: 16,
              }}
            >
              <PracticeModesPanel onStart={onStartPracticeMode} />
              <ConceptPanel queue={conceptQueue} onStart={onStartConceptReview} />
              <PracticePanel queue={practiceQueue} onStart={onStartRecommended} />
            </div>
          </>
        )}

        {activeHomeTab === "browse" && (
          <>
            <BrowseHeader />
            <BrowseSummary chapters={filtered} filteredCount={filtered.length} />
            <SectionFilterBar
              filters={filtersWithCounts}
              activeFilter={sectionFilterCounts[activeFilter] === 0 ? "all" : activeFilter}
              onChange={setActiveFilter}
            />

            {/* Search */}
            <div style={mapPanelStyle({
              display: "flex", alignItems: "center", gap: 8,
              padding: "8px 12px", marginBottom: 16,
            })}>
              <span style={{ color: MAP_THEME.faint, fontSize: 13 }}>⌕</span>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search sections…"
                style={{
                  background: "none", border: "none", outline: "none",
                  color: MAP_THEME.text, fontFamily: "'Barlow',sans-serif", fontSize: 13,
                  flex: 1,
                }}
              />
              {search && (
                <button onClick={() => setSearch("")} style={{
                  background: "none", border: "none", color: MAP_THEME.faint,
                  cursor: "pointer", fontSize: 14, lineHeight: 1,
                }}>✕</button>
              )}
            </div>

            {/* Chapter accordions */}
          {filtered.map((ch, i) => (
              <ChapterAccordion
                key={ch.chapter}
                chapter={ch}
                sectionSignals={sectionSignals}
                onStart={onStartLesson}
                onFlashcards={onStartFlashcards}
                onFocus={onOpenSection}
                defaultOpen={false}
                open={Boolean(openChapters[String(ch.chapter)])}
                onOpenChange={(isOpen) => setChapterOpen(ch.chapter, isOpen)}
              />
            ))}

            {filtered.length === 0 && (
              <div style={{ textAlign: "center", color: MAP_THEME.faint, padding: 40, fontSize: 13 }}>
                No sections match "{search}"
              </div>
            )}

            {/* Crown legend */}
            <div style={mapPanelStyle({
              marginTop: 24, padding: "12px 16px",
            })}>
              <div style={{
                fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
                color: MAP_THEME.faint, letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 9,
              }}>Crown levels</div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {CROWN_ICONS.map((icon, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <CrownBadge level={i} size="sm" />
                    <span style={{
                      fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10,
                      color: MAP_THEME.faint,
                    }}>{CROWN_LABELS[i]}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {activeHomeTab === "aircraft" && (
          <AircraftRecognitionWorkspace
            cardCount={aircraftCardCount}
            aircraftCards={aircraftCards}
            imageCandidateCount={aircraftImageCandidateCount}
            imageApprovedCount={aircraftImageApprovedCount}
            onOpenImageReview={onOpenAircraftImageReview}
            onStartImages={onStartAircraftImages}
            onStart={onStartAircraftRecognition}
          />
        )}
      </div>
    </div>
  );
}
