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

const PARAGRAPH_FILTERS = [
  { id: "all", label: "All" },
  { id: "needs_work", label: "Needs Work" },
  { id: "new", label: "New" },
  { id: "focused", label: "Focused" },
  { id: "phraseology", label: "Phraseology" },
  { id: "tables_visuals", label: "Tables/Figures" },
  { id: "cards", label: "Cards" },
];

const SECTION_BROWSER_CSS = `
.section-browser{background:#30302e!important;color:#f1ead7!important;font-family:'Share Tech Mono',ui-monospace,monospace!important;}
.section-browser *{box-sizing:border-box;font-family:'Share Tech Mono',ui-monospace,monospace!important;border-radius:2px!important;box-shadow:none!important}
.section-browser-body,.section-browser-header{max-width:1120px;margin-left:auto;margin-right:auto;background:#11120e;}
@media (max-width: 520px){
  .section-browser{overflow-x:hidden}
  .section-browser-header{padding:max(16px, env(safe-area-inset-top)) 12px 0!important;flex-direction:column;align-items:stretch!important}
  .section-browser-actions{justify-content:flex-start!important}
  .section-browser-actions button,.section-browser-card-actions button,.section-browser-card-actions a{min-height:44px!important}
  .section-browser-body{padding:14px 12px 22px!important}
  .section-browser input,.section-browser select{font-size:16px!important;min-height:46px!important}
  .section-browser-card-actions{display:grid!important;grid-template-columns:1fr!important}
  .section-browser-card-actions button,.section-browser-card-actions a{width:100%;min-width:0;justify-content:center}
}
`;

function paragraphMatchesFilter(item, filterId) {
  if (filterId === "all") return true;
  if (filterId === "needs_work") return item.focusBand === "needs-work" || item.crown < 2;
  if (filterId === "new") return item.crown === 0;
  if (filterId === "focused") return Boolean(item.isFocused);
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

function SectionSummary({ paragraphs }) {
  const stats = [
    { label: "Needs Work", value: paragraphs.filter((item) => paragraphMatchesFilter(item, "needs_work")).length, color: "#f43f5e" },
    { label: "New", value: paragraphs.filter((item) => paragraphMatchesFilter(item, "new")).length, color: "#7aa7d9" },
    { label: "Focused", value: paragraphs.filter((item) => paragraphMatchesFilter(item, "focused")).length, color: "#e0a30a" },
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
      {stats.map((stat) => (
        <div key={stat.label} style={{
          background: "rgba(13,17,15,.92)",
          border: `1px solid ${stat.color}33`,
          borderRadius: 10,
          padding: "10px 12px",
        }}>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 20,
            fontWeight: 700,
            color: stat.color,
          }}>
            {stat.value}
          </div>
          <div style={{
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".08em",
            color: "#8c9c91",
            textTransform: "uppercase",
          }}>
            {stat.label}
          </div>
        </div>
      ))}
    </div>
  );
}

function ParagraphCard({ item, onStudy, onCards, onToggleFocus }) {
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
      </div>

      <div className="section-browser-card-actions" style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
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
          Drill Paragraph
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
            Cards
          </button>
        )}
        <button
          onClick={() => onToggleFocus(item)}
          style={{
            height: 34,
            padding: "0 12px",
            borderRadius: 8,
            border: `1px solid ${item.isFocused ? "#e0a30a" : "rgba(219,229,216,.18)"}`,
            background: item.isFocused ? "rgba(224,163,10,.12)" : "rgba(17,22,20,.92)",
            color: item.isFocused ? "#e0a30a" : "#e4ece2",
            cursor: "pointer",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: ".07em",
            textTransform: "uppercase",
          }}
        >
          {item.isFocused ? "Saved" : "Save Focus"}
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

export default function SectionBrowser({
  section,
  paragraphs,
  onBack,
  onStudySection,
  onCardsSection,
  onStudyParagraph,
  onCardsParagraph,
  onToggleFocus,
  onOpenFocus,
  focusCount,
  viewState = {},
  onViewStateChange,
}) {
  const search = viewState.search || "";
  const sortMode = viewState.sortMode || "order";
  const activeFilter = viewState.activeFilter || "all";
  const patchViewState = (patch) => {
    if (onViewStateChange) onViewStateChange(patch);
  };
  const setSearch = (value) => patchViewState({ search: value });
  const setSortMode = (value) => patchViewState({ sortMode: value });
  const setActiveFilter = (value) => patchViewState({ activeFilter: value });

  const filterCounts = useMemo(() => (
    Object.fromEntries(PARAGRAPH_FILTERS.map((filter) => [
      filter.id,
      paragraphs.filter((item) => paragraphMatchesFilter(item, filter.id)).length,
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
          || item.activityTypes.some((type) => type.toLowerCase().replaceAll("_", " ").includes(needle))
        ));

    items = items.filter((item) => paragraphMatchesFilter(item, filterId));

    if (sortMode === "content") {
      items.sort((a, b) => (
        (b.activityCount + b.flashcardCount + b.questionCount) - (a.activityCount + a.flashcardCount + a.questionCount)
        || b.focusScore - a.focusScore
        || a.para_id.localeCompare(b.para_id, undefined, { numeric: true })
      ));
    } else if (sortMode === "order") {
      items.sort((a, b) => a.para_id.localeCompare(b.para_id, undefined, { numeric: true }));
    } else {
      items.sort((a, b) => (
        b.focusScore - a.focusScore
        || a.crown - b.crown
        || a.para_id.localeCompare(b.para_id, undefined, { numeric: true })
      ));
    }
    return items;
  }, [activeFilter, filterCounts, paragraphs, search, sortMode]);

  const filtersWithCounts = PARAGRAPH_FILTERS.map((filter) => ({
    ...filter,
    count: filterCounts[filter.id] || 0,
  }));

  const totalCards = paragraphs.reduce((sum, item) => sum + item.flashcardCount, 0);

  return (
    <div className="section-browser" style={{
      background: "radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706",
      minHeight: "100vh",
      color: "#e4ece2",
      fontFamily: "'Barlow', sans-serif",
    }}>
      <style>{SECTION_BROWSER_CSS}</style>
      <div className="section-browser-header" style={{
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
            Section Focus
          </div>
          <div style={{
            marginTop: 4,
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 24,
            fontWeight: 700,
            letterSpacing: ".04em",
            color: "#e0a30a",
          }}>
            {section?.label}
          </div>
          <div style={{ marginTop: 6, fontSize: 13, color: "#8c9c91", lineHeight: 1.6, maxWidth: 720 }}>
            Drill a specific paragraph instead of pulling a mixed section session. This is the targeted path for issue areas you identify later.
          </div>
        </div>
        <div className="section-browser-actions" style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <div style={{
            alignSelf: "center",
            color: "#8c9c91",
            fontFamily: "'Barlow Condensed',sans-serif",
            fontSize: 11,
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}>
            Focus list {focusCount}
          </div>
          {onOpenFocus && (
            <button
              onClick={onOpenFocus}
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
              Open Focus List
            </button>
          )}
          {totalCards > 0 && (
            <button
              onClick={() => onCardsSection(section)}
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
              Review Cards
            </button>
          )}
          <button
            onClick={() => onStudySection(section)}
            style={{
              height: 36,
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
            Study Whole Section
          </button>
        </div>
      </div>

      <div className="section-browser-body" style={{ padding: "16px 20px 24px" }}>
        <SectionSummary paragraphs={paragraphs} />
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
            placeholder="Search paragraph id, title, or activity type…"
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
            <option value="order">Sort: Paragraph Order</option>
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
          {paragraphs.length} paragraph{paragraphs.length === 1 ? "" : "s"} with published learner-facing content in this section.
          {" "}
          Paragraph order matches the 7110.65 organization. Use <strong style={{ color: "#e0a30a" }}>Practice Need</strong> when you want the weak-area view.
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          {filtered.map((item) => (
            <ParagraphCard
              key={item.para_id}
              item={item}
              onStudy={onStudyParagraph}
              onCards={onCardsParagraph}
              onToggleFocus={onToggleFocus}
            />
          ))}
        </div>

        {filtered.length === 0 && (
          <div style={{
            textAlign: "center",
            color: "#8c9c91",
            padding: "40px 16px",
            fontSize: 13,
          }}>
            No paragraphs match that search.
          </div>
        )}
      </div>
    </div>
  );
}
