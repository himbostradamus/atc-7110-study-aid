import { useMemo } from "react";
import { CROWN_ICONS, CROWN_COLORS } from "./useCurriculum";

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

const FOCUS_FILTERS = [
  { id: "all", label: "All" },
  { id: "needs_work", label: "Needs Work" },
  { id: "new", label: "New" },
  { id: "phraseology", label: "Phraseology" },
  { id: "tables_visuals", label: "Tables/Figures" },
  { id: "cards", label: "Cards" },
];

const FOCUS_BROWSER_CSS = `
.focus-browser{background:#30302e!important;color:#f1ead7!important;font-family:'Share Tech Mono',ui-monospace,monospace!important;}
.focus-browser *{box-sizing:border-box;font-family:'Share Tech Mono',ui-monospace,monospace!important;border-radius:2px!important;box-shadow:none!important}
.focus-browser-body,.focus-browser-header{max-width:1120px;margin-left:auto;margin-right:auto;background:#11120e;}
@media (max-width: 520px){
  .focus-browser{overflow-x:hidden}
  .focus-browser-header{padding:max(16px, env(safe-area-inset-top)) 12px 0!important;flex-direction:column;align-items:stretch!important}
  .focus-browser-actions{justify-content:flex-start!important}
  .focus-browser-actions button,.focus-browser-card-actions button,.focus-browser-card-actions a{min-height:44px!important}
  .focus-browser-body{padding:14px 12px 22px!important}
  .focus-browser input,.focus-browser select{font-size:16px!important;min-height:46px!important}
  .focus-browser-card-actions{display:grid!important;grid-template-columns:1fr!important}
  .focus-browser-card-actions button,.focus-browser-card-actions a{width:100%;min-width:0;justify-content:center}
}
`;

function focusItemMatchesFilter(item, filterId) {
  if (filterId === "all") return true;
  if (filterId === "needs_work") return item.focusBand === "needs-work" || item.crown < 2;
  if (filterId === "new") return item.crown === 0;
  if (filterId === "phraseology") return item.activityTypes.some((type) => PHRASEOLOGY_TYPES.has(type));
  if (filterId === "tables_visuals") return item.activityTypes.some((type) => TABLE_VISUAL_TYPES.has(type));
  if (filterId === "cards") return item.flashcardCount > 0;
  return true;
}

function CrownPill({ level }) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      minWidth: 28,
      height: 24,
      padding: "0 8px",
      borderRadius: 999,
      background: `${CROWN_COLORS[level] || "#27302a"}18`,
      border: `1px solid ${(CROWN_COLORS[level] || "#27302a")}55`,
      color: CROWN_COLORS[level] || "#27302a",
      fontFamily: "'Barlow Condensed', sans-serif",
      fontWeight: 700,
      fontSize: 11,
      letterSpacing: ".06em",
    }}>
      {CROWN_ICONS[level] || CROWN_ICONS[0]}
    </span>
  );
}

function FocusSummary({ paragraphs }) {
  const summary = [
    { label: "Saved", value: paragraphs.length, color: "#e0a30a" },
    { label: "Needs Work", value: paragraphs.filter((item) => focusItemMatchesFilter(item, "needs_work")).length, color: "#f43f5e" },
    { label: "New", value: paragraphs.filter((item) => focusItemMatchesFilter(item, "new")).length, color: "#7aa7d9" },
    { label: "Questions", value: paragraphs.reduce((sum, item) => sum + item.questionCount, 0), color: "#8c9c91" },
    { label: "Cards", value: paragraphs.reduce((sum, item) => sum + item.flashcardCount, 0), color: "#39c36f" },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
      gap: 8,
      marginBottom: 14,
    }}>
      {summary.map((item) => (
        <div key={item.label} style={{
          background: "rgba(13,17,15,.92)",
          border: `1px solid ${item.color}33`,
          borderRadius: 10,
          padding: "10px 12px",
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 20,
            fontWeight: 700,
            color: item.color,
          }}>
            {item.value}
          </div>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".08em",
            color: "#8c9c91",
            textTransform: "uppercase",
          }}>
            {item.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function FilterChips({ filters, activeFilter, onChange }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginBottom: 14 }}>
      {filters.map((filter) => {
        const active = filter.id === activeFilter;
        return (
          <button
            key={filter.id}
            onClick={() => onChange(filter.id)}
            disabled={filter.count === 0}
            style={{
              minHeight: 30,
              display: "inline-flex",
              alignItems: "center",
              gap: 7,
              borderRadius: 999,
              border: `1px solid ${active ? "#e0a30a" : "rgba(219,229,216,.18)"}`,
              background: active ? "rgba(224,163,10,.12)" : "rgba(13,17,15,.92)",
              color: active ? "#e0a30a" : (filter.count === 0 ? "#27302a" : "#8c9c91"),
              padding: "0 10px",
              cursor: filter.count === 0 ? "default" : "pointer",
              opacity: filter.count === 0 ? 0.45 : 1,
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 11,
              letterSpacing: ".06em",
              textTransform: "uppercase",
            }}
          >
            <span>{filter.label}</span>
            <span style={{
              minWidth: 18,
              height: 18,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 999,
              background: active ? "rgba(224,163,10,.16)" : "rgba(26,32,28,.92)",
              color: active ? "#e0a30a" : "#8c9c91",
              fontSize: 10,
            }}>
              {filter.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function FocusCard({ item, onStudy, onCards, onRemove }) {
  const bandColor = item.focusBand === "needs-work"
    ? "#f43f5e"
    : item.focusBand === "developing"
      ? "#e0a30a"
      : "#7aa7d9";

  return (
    <div style={{
      background: "rgba(17,22,20,.92)",
      border: "1px solid rgba(219,229,216,.13)",
      borderRadius: 12,
      padding: "14px 15px",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 11,
            color: "#8c9c91",
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>
            {item.para_id}
            {" · "}
            Chapter {item.chapter} / {item.sectionLabel}
            {item.page ? ` · page ${item.page}` : ""}
          </div>
          <div style={{
            marginTop: 4,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 16,
            fontWeight: 700,
            color: "#e4ece2",
            lineHeight: 1.2,
          }}>
            {item.title}
          </div>
          <div style={{
            marginTop: 4,
            fontSize: 12,
            color: "#8c9c91",
            lineHeight: 1.5,
          }}>
            {item.chapterLabel}
          </div>
        </div>
        <CrownPill level={item.crown} />
      </div>

      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
        marginTop: 10,
      }}>
        <span style={{
          height: 23,
          padding: "0 8px",
          borderRadius: 999,
          display: "inline-flex",
          alignItems: "center",
          border: `1px solid ${bandColor}55`,
          color: bandColor,
          background: `${bandColor}16`,
          fontFamily: "'Barlow Condensed',sans-serif",
          fontWeight: 700,
          fontSize: 10,
          letterSpacing: ".06em",
          textTransform: "uppercase",
        }}>
          {item.focusBand === "needs-work" ? "Needs Work" : item.focusBand === "developing" ? "Developing" : "Steady"}
        </span>
        <span style={{
          height: 23,
          padding: "0 8px",
          borderRadius: 999,
          display: "inline-flex",
          alignItems: "center",
          border: "1px solid rgba(219,229,216,.13)",
          color: "#8c9c91",
          background: "rgba(26,32,28,.92)",
          fontFamily: "'Barlow Condensed',sans-serif",
          fontWeight: 700,
          fontSize: 10,
          letterSpacing: ".06em",
          textTransform: "uppercase",
        }}>
          Need {item.focusScore}
        </span>
        {item.activityTypes.slice(0, 3).map((type) => (
          <span
            key={type}
            style={{
              height: 23,
              padding: "0 8px",
              borderRadius: 999,
              display: "inline-flex",
              alignItems: "center",
              border: "1px solid rgba(219,229,216,.13)",
              color: "#8c9c91",
              background: "rgba(26,32,28,.92)",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 10,
              letterSpacing: ".06em",
              textTransform: "uppercase",
            }}
          >
            {type.replaceAll("_", " ")}
          </span>
        ))}
      </div>

      <div style={{
        marginTop: 10,
        fontSize: 12,
        color: "#8c9c91",
        lineHeight: 1.6,
      }}>
        {item.activityCount} activities · {item.questionCount} questions · {item.flashcardCount} cards
        <span style={{ display: "block", marginTop: 3 }}>
          Drill applies this issue area. Cards rebuild recall.
        </span>
      </div>

      <div className="focus-browser-card-actions" style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <button
          onClick={() => onStudy(item)}
          style={{
            height: 34,
            padding: "0 12px",
            borderRadius: 8,
            border: "none",
            background: "#e0a30a",
            color: "#000",
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: ".07em",
            textTransform: "uppercase",
          }}
        >
          Drill Rule
        </button>
        {item.flashcardCount > 0 && (
          <button
            onClick={() => onCards(item)}
            style={{
              height: 34,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid rgba(219,229,216,.18)",
              background: "rgba(17,22,20,.92)",
              color: "#e4ece2",
              cursor: "pointer",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 11,
              letterSpacing: ".07em",
              textTransform: "uppercase",
            }}
          >
            Recall Cards
          </button>
        )}
        <button
          onClick={() => onRemove(item)}
          style={{
            height: 34,
            padding: "0 12px",
            borderRadius: 8,
            border: "1px solid rgba(219,229,216,.18)",
            background: "rgba(17,22,20,.92)",
            color: "#e4ece2",
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: ".07em",
            textTransform: "uppercase",
          }}
        >
          Remove Area
        </button>
        {item.source_url && (
          <a
            href={item.source_url}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: 34,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid rgba(219,229,216,.18)",
              background: "rgba(13,17,15,.92)",
              color: "#e0a30a",
              textDecoration: "none",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 11,
              letterSpacing: ".07em",
              textTransform: "uppercase",
            }}
          >
            FAA Source ↗
          </a>
        )}
      </div>
    </div>
  );
}

export default function FocusListBrowser({
  paragraphs,
  onBack,
  onStudyList,
  onStudyParagraph,
  onCardsParagraph,
  onRemoveParagraph,
  onClear,
  viewState = {},
  onViewStateChange,
}) {
  const search = viewState.search || "";
  const sortMode = viewState.sortMode || "section";
  const activeFilter = viewState.activeFilter || "all";
  const patchViewState = (patch) => {
    if (onViewStateChange) onViewStateChange(patch);
  };
  const setSearch = (value) => patchViewState({ search: value });
  const setSortMode = (value) => patchViewState({ sortMode: value });
  const setActiveFilter = (value) => patchViewState({ activeFilter: value });

  const filterCounts = useMemo(() => (
    Object.fromEntries(FOCUS_FILTERS.map((filter) => [
      filter.id,
      paragraphs.filter((item) => focusItemMatchesFilter(item, filter.id)).length,
    ]))
  ), [paragraphs]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filterId = filterCounts[activeFilter] === 0 ? "all" : activeFilter;
    let items = !needle
      ? [...paragraphs]
      : paragraphs.filter((item) => (
          item.para_id.toLowerCase().includes(needle)
          || item.title.toLowerCase().includes(needle)
          || item.chapterLabel.toLowerCase().includes(needle)
          || item.sectionLabel.toLowerCase().includes(needle)
          || item.activityTypes.some((type) => type.toLowerCase().replaceAll("_", " ").includes(needle))
        ));
    items = items.filter((item) => focusItemMatchesFilter(item, filterId));

    if (sortMode === "content") {
      items.sort((a, b) => (
        (b.activityCount + b.flashcardCount + b.questionCount) - (a.activityCount + a.flashcardCount + a.questionCount)
        || b.focusScore - a.focusScore
        || a.para_id.localeCompare(b.para_id, undefined, { numeric: true })
      ));
    } else if (sortMode === "section") {
      items.sort((a, b) => (
        a.chapter - b.chapter
        || a.section - b.section
        || a.para_id.localeCompare(b.para_id, undefined, { numeric: true })
      ));
    } else {
      items.sort((a, b) => (
        b.focusScore - a.focusScore
        || a.crown - b.crown
        || a.para_id.localeCompare(b.para_id, undefined, { numeric: true })
      ));
    }

    return items;
  }, [activeFilter, filterCounts, paragraphs, search, sortMode]);

  const filtersWithCounts = FOCUS_FILTERS.map((filter) => ({
    ...filter,
    count: filterCounts[filter.id] || 0,
  }));

  const totalCards = paragraphs.reduce((sum, item) => sum + item.flashcardCount, 0);

  return (
    <div className="focus-browser" style={{
      background: "radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706",
      minHeight: "100vh",
      color: "#e4ece2",
      fontFamily: "'Barlow', sans-serif",
    }}>
      <style>{FOCUS_BROWSER_CSS}</style>
      <div className="focus-browser-header" style={{
        padding: "18px 20px 0",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 12,
      }}>
        <div>
          <button
            onClick={onBack}
            style={{
              background: "none",
              border: "none",
              color: "#8c9c91",
              cursor: "pointer",
              padding: 0,
              marginBottom: 10,
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
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 11,
            color: "#8c9c91",
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>
            Saved Issue Areas
          </div>
          <div style={{
            marginTop: 4,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 24,
            fontWeight: 700,
            letterSpacing: ".04em",
            color: "#e0a30a",
          }}>
            Issue Areas
          </div>
          <div style={{ marginTop: 6, fontSize: 13, color: "#8c9c91", lineHeight: 1.6, maxWidth: 720 }}>
            Saved paragraphs are your manual repair list. Use it for weak spots you want to revisit independent of chapter order.
          </div>
        </div>
        <div className="focus-browser-actions" style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <div style={{
            alignSelf: "center",
            color: "#8c9c91",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 11,
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>
            {paragraphs.length} saved
          </div>
          {paragraphs.length > 0 && (
            <button
              onClick={onClear}
              style={{
                height: 36,
                padding: "0 12px",
                borderRadius: 8,
                border: "1px solid rgba(219,229,216,.18)",
                background: "rgba(17,22,20,.92)",
                color: "#e4ece2",
                cursor: "pointer",
                fontFamily: "'Barlow Condensed',sans-serif",
                fontWeight: 700,
                fontSize: 11,
                letterSpacing: ".07em",
                textTransform: "uppercase",
              }}
            >
              Clear Areas
            </button>
          )}
          <button
            onClick={onStudyList}
            disabled={!paragraphs.length}
            style={{
              height: 36,
              padding: "0 12px",
              borderRadius: 8,
              border: "none",
              background: paragraphs.length ? "#e0a30a" : "rgba(219,229,216,.06)",
              color: paragraphs.length ? "#000" : "#8c9c91",
              cursor: paragraphs.length ? "pointer" : "not-allowed",
              fontFamily: "'Barlow Condensed',sans-serif",
              fontWeight: 700,
              fontSize: 11,
              letterSpacing: ".07em",
              textTransform: "uppercase",
            }}
          >
            Drill Issue Areas
          </button>
        </div>
      </div>

      <div className="focus-browser-body" style={{ padding: "16px 20px 24px" }}>
        <FocusSummary paragraphs={paragraphs} />
        <FilterChips
          filters={filtersWithCounts}
          activeFilter={filterCounts[activeFilter] === 0 ? "all" : activeFilter}
          onChange={setActiveFilter}
        />

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 8,
          marginBottom: 14,
        }}>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search paragraph id, title, chapter, or activity type…"
            style={{
              height: 42,
              borderRadius: 8,
              border: "1px solid rgba(219,229,216,.13)",
              background: "rgba(13,17,15,.92)",
              color: "#e4ece2",
              padding: "0 12px",
              fontFamily: "'Barlow',sans-serif",
              fontSize: 13,
            }}
          />
          <select
            value={sortMode}
            onChange={(event) => setSortMode(event.target.value)}
            style={{
              height: 42,
              borderRadius: 8,
              border: "1px solid rgba(219,229,216,.13)",
              background: "rgba(13,17,15,.92)",
              color: "#e4ece2",
              padding: "0 12px",
              fontFamily: "'Barlow',sans-serif",
              fontSize: 13,
            }}
          >
            <option value="section">Sort: Section Order</option>
            <option value="focus">Sort: Practice Need</option>
            <option value="content">Sort: Most Content</option>
          </select>
        </div>

        <div style={{
          background: "rgba(13,17,15,.92)",
          border: "1px solid rgba(219,229,216,.13)",
          borderRadius: 10,
          padding: "12px 14px",
          marginBottom: 14,
          fontSize: 12,
          lineHeight: 1.6,
          color: "#8c9c91",
        }}>
          {paragraphs.length} saved paragraph{paragraphs.length === 1 ? "" : "s"} currently published for learner-facing study.
          {" "}
          {totalCards > 0 ? `${totalCards} recall cards are available across this list.` : "No recall cards are published for these saved paragraphs yet."}
        </div>

        {paragraphs.length === 0 ? (
          <div style={{
            background: "rgba(13,17,15,.92)",
            border: "1px solid rgba(219,229,216,.13)",
            borderRadius: 10,
            padding: "32px 18px",
            textAlign: "center",
            color: "#8c9c91",
            fontSize: 13,
            lineHeight: 1.7,
          }}>
            Nothing is saved yet. Use <strong style={{ color: "#e0a30a" }}>Save Issue Area</strong> on a paragraph inside any section browser to build your cross-section repair list.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {filtered.map((item) => (
              <FocusCard
                key={item.para_id}
                item={item}
                onStudy={onStudyParagraph}
                onCards={onCardsParagraph}
                onRemove={onRemoveParagraph}
              />
            ))}
          </div>
        )}

        {paragraphs.length > 0 && filtered.length === 0 && (
          <div style={{
            textAlign: "center",
            color: "#8c9c91",
            padding: "40px 16px",
            fontSize: 13,
          }}>
            No saved paragraphs match that search.
          </div>
        )}
      </div>
    </div>
  );
}
