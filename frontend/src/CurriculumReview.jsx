import { useEffect, useMemo, useRef, useState } from "react";
import { REVIEW_STATUS_META } from "./useCurriculum";
import SourceCitation from "./SourceCitation";

const REVIEW_STATUS_OPTIONS = new Set(["all", "pending", "approved", "weak", "replace"]);
const PRIORITY_OPTIONS = new Set(["all", "high", "medium", "baseline"]);
const FLAG_FILTER_OPTIONS = new Set(["all", "flagged", "unflagged"]);
const ITEM_FLAGS_KEY = "atc_item_flags_v1";

const CSS = `
*{box-sizing:border-box}
.qa-shell{min-height:100vh;background:radial-gradient(circle at 12% -8%, rgba(224,163,10,.07), transparent 280px), #050706;color:#e4ece2;font-family:'Barlow',sans-serif}
.qa-header{padding:20px 20px 0;display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.qa-header h1{font-family:'Barlow Condensed',sans-serif;font-size:24px;letter-spacing:.04em;color:#e0a30a}
.qa-sub{font-size:12px;color:#8c9c91;margin-top:4px;line-height:1.5;max-width:680px}
.qa-header-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.qa-btn{height:38px;padding:0 14px;border-radius:8px;border:1px solid rgba(219,229,216,.13);background:rgba(17,22,20,.92);color:#e4ece2;cursor:pointer;font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.qa-btn.qa-primary{background:#e0a30a;border:none;color:#000}
.qa-link-btn{text-decoration:none;display:inline-flex;align-items:center;justify-content:center}
.qa-body{padding:16px 20px 20px}
.qa-notice{border-radius:10px;padding:12px 14px;font-size:12px;line-height:1.6;margin-bottom:14px;border:1px solid}
.qa-notice.success{background:#07150d;border-color:rgba(57,195,111,.28);color:#a7d8b4}
.qa-notice.error{background:#15080d;border-color:rgba(244,63,94,.3);color:#e5a0ad}
.qa-banner{background:rgba(13,17,15,.92);border:1px solid rgba(219,229,216,.13);border-radius:10px;padding:13px 15px;font-size:12px;line-height:1.6;color:#8c9c91;margin-bottom:14px}
.qa-banner strong{color:#e0a30a;font-family:'Barlow Condensed',sans-serif;letter-spacing:.06em;text-transform:uppercase}
.qa-flag-panel{background:#140b10;border:1px solid rgba(244,63,94,.3);border-radius:10px;padding:13px 15px;margin-bottom:14px}
.qa-flag-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px}
.qa-flag-title{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#f43f5e}
.qa-flag-copy{font-size:12px;color:#c89aa6;line-height:1.5;margin-top:3px}
.qa-flag-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px}
.qa-flag-item{background:rgba(17,22,20,.92);border:1px solid rgba(244,63,94,.25);border-radius:9px;padding:10px 11px;text-align:left;cursor:pointer;color:#e4ece2}
.qa-flag-item:hover{border-color:#f43f5e}
.qa-flag-meta{font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#f43f5e;margin-bottom:4px}
.qa-flag-text{font-size:12px;line-height:1.45;color:#e4ece2}
.qa-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:14px}
.qa-stat{background:rgba(17,22,20,.92);border:1px solid rgba(219,229,216,.13);border-radius:10px;padding:12px 14px}
.qa-stat-value{font-family:'Barlow Condensed',sans-serif;font-size:24px;font-weight:700;color:#e4ece2}
.qa-stat-label{font-family:'Barlow Condensed',sans-serif;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#8c9c91;margin-top:3px}
.qa-controls{display:grid;grid-template-columns:minmax(0,2fr) repeat(4,minmax(0,1fr));gap:8px;margin-bottom:14px}
.qa-input,.qa-select,.qa-textarea{width:100%;background:rgba(13,17,15,.92);border:1px solid rgba(219,229,216,.13);border-radius:8px;color:#e4ece2;font-family:'Barlow',sans-serif}
.qa-input,.qa-select{height:40px;padding:0 12px;font-size:13px}
.qa-textarea{padding:10px 12px;font-size:13px;line-height:1.55;min-height:108px;resize:vertical}
.qa-layout{display:grid;grid-template-columns:340px minmax(0,1fr);gap:14px;align-items:start}
.qa-panel{background:rgba(13,17,15,.92);border:1px solid rgba(219,229,216,.13);border-radius:12px;overflow:hidden}
.qa-panel-head{padding:12px 14px;border-bottom:1px solid rgba(219,229,216,.13);display:flex;align-items:center;justify-content:space-between;gap:10px}
.qa-panel-title{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#e0a30a}
.qa-panel-copy{font-size:11px;color:#8c9c91}
.qa-queue{max-height:calc(100vh - 270px);overflow:auto;padding:10px}
.qa-queue-item{background:rgba(17,22,20,.92);border:1px solid rgba(219,229,216,.13);border-radius:10px;padding:11px 12px;cursor:pointer;transition:border-color .15s,transform .15s}
.qa-queue-item + .qa-queue-item{margin-top:8px}
.qa-queue-item:hover{border-color:rgba(219,229,216,.22)}
.qa-queue-item.is-selected{border-color:#e0a30a;transform:translateY(-1px)}
.qa-queue-top{display:flex;align-items:flex-start;gap:8px}
.qa-queue-copy{flex:1}
.qa-para{font-family:'Barlow Condensed',sans-serif;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#8c9c91}
.qa-queue-title{font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:700;line-height:1.25;color:#e4ece2;margin-top:2px}
.qa-queue-meta{font-size:11px;color:#8c9c91;margin-top:6px;line-height:1.5}
.qa-chip-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.qa-chip{display:inline-flex;align-items:center;height:23px;padding:0 8px;border-radius:999px;background:rgba(26,32,28,.92);border:1px solid rgba(219,229,216,.13);color:#8c9c91;font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.qa-detail{padding:14px}
.qa-detail-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
.qa-detail-title{font-family:'Barlow Condensed',sans-serif;font-size:24px;font-weight:700;letter-spacing:.03em;color:#e4ece2;line-height:1.1}
.qa-detail-sub{font-size:12px;color:#8c9c91;margin-top:6px}
.qa-status-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.qa-status-btn{height:34px;padding:0 12px;border-radius:8px;border:1px solid rgba(219,229,216,.13);background:rgba(17,22,20,.92);color:#e4ece2;cursor:pointer;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.qa-status-btn.is-active{border-color:currentColor;background:rgba(255,255,255,.04)}
.qa-note-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.qa-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}
.qa-section{background:rgba(17,22,20,.92);border:1px solid rgba(219,229,216,.13);border-radius:10px;padding:12px}
.qa-section h3{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#e0a30a;margin-bottom:10px}
.qa-count{font-size:11px;color:#8c9c91;margin-left:6px}
.qa-block,.qa-card{background:rgba(26,32,28,.92);border:1px solid rgba(219,229,216,.13);border-radius:9px;padding:10px 11px}
.qa-block + .qa-block,.qa-card + .qa-card{margin-top:8px}
.qa-block-label,.qa-card-meta{font-family:'Barlow Condensed',sans-serif;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#8c9c91;margin-bottom:6px}
.qa-card-title{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;color:#e4ece2}
.qa-card-copy{font-size:12px;line-height:1.6;color:#e4ece2}
.qa-card-copy + .qa-card-copy{margin-top:7px}
.qa-choice-list{margin-top:8px;display:flex;flex-direction:column;gap:6px}
.qa-choice{border:1px solid rgba(219,229,216,.13);border-radius:8px;padding:8px 10px;font-size:12px;line-height:1.5;background:rgba(13,17,15,.92);color:#e4ece2}
.qa-choice.is-correct{border-color:rgba(57,195,111,.4);background:rgba(57,195,111,.12);color:#a7d8b4}
.qa-mini-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:8px}
.qa-mini{border:1px solid rgba(219,229,216,.13);border-radius:8px;padding:8px 9px;font-size:11px;line-height:1.5;background:rgba(13,17,15,.92);color:#8c9c91}
.qa-json{margin-top:8px;background:rgba(7,10,9,.62);border:1px solid rgba(219,229,216,.13);border-radius:8px;padding:10px;color:#8c9c91;font-family:'Share Tech Mono',monospace;font-size:11px;line-height:1.55;white-space:pre-wrap;overflow:auto}
.qa-empty{padding:36px 18px;text-align:center;color:#8c9c91}
.qa-empty strong{display:block;font-family:'Barlow Condensed',sans-serif;font-size:18px;letter-spacing:.05em;color:#e0a30a;margin-bottom:8px}
@media (max-width: 960px){
  .qa-summary{grid-template-columns:repeat(2,minmax(0,1fr))}
  .qa-controls{grid-template-columns:1fr 1fr}
  .qa-layout{grid-template-columns:1fr}
  .qa-queue{max-height:none}
  .qa-grid{grid-template-columns:1fr}
}
`;

function humanizeSlug(value) {
  return String(value || "")
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value) {
  if (!value) return "Not reviewed";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not reviewed";
  return date.toLocaleString();
}

function loadItemFlags() {
  try {
    const raw = JSON.parse(localStorage.getItem(ITEM_FLAGS_KEY) || "{}");
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
    return raw;
  } catch {
    return {};
  }
}

function saveItemFlags(flags) {
  try {
    localStorage.setItem(ITEM_FLAGS_KEY, JSON.stringify(flags));
  } catch {}
}

function flagsForPara(flags, paraId) {
  return Object.values(flags || {})
    .filter((flag) => flag?.paraId === paraId)
    .sort((a, b) => String(b.flaggedAt || "").localeCompare(String(a.flaggedAt || "")));
}

function formatFlagNote(flags) {
  if (!flags.length) return "";
  const lines = [
    "Learner item flag(s):",
    ...flags.map((flag) => (
      [
        `- ${flag.activityLabel || flag.activityType || "Activity"} (${flag.activityId}) flagged ${formatDate(flag.flaggedAt)}`,
        flag.itemText ? `  Prompt: ${flag.itemText}` : null,
        flag.correctAnswer ? `  Expected: ${flag.correctAnswer}` : null,
        flag.explanation ? `  Explanation shown: ${flag.explanation}` : null,
        flag.sourceUrl ? `  Source: ${flag.sourceUrl}` : null,
      ].filter(Boolean).join("\n")
    )),
  ];
  return lines.join("\n");
}

function statusColor(status) {
  return REVIEW_STATUS_META[status]?.color || "#8c9c91";
}

function priorityLabel(priority) {
  if (priority?.band === "high") return "High";
  if (priority?.band === "medium") return "Medium";
  return "Baseline";
}

function summarizePayload(payload) {
  const extra = { ...payload };
  delete extra.instruction;
  delete extra.explanation;
  delete extra.question_text;
  delete extra.prompt;
  delete extra.clearance;
  delete extra.situation;
  delete extra.para_context;
  delete extra.target_phrase;
  delete extra.word_bank;
  delete extra.correct_sequence;
  delete extra.original_phrase;
  delete extra.display_text;
  delete extra.tokens;
  delete extra.correct_token;
  delete extra.error_index;
  delete extra.steps;
  delete extra.pairs;
  delete extra.choices;
  const keys = Object.keys(extra);
  if (!keys.length) return null;
  return JSON.stringify(extra, null, 2);
}

function readReviewUrlState() {
  const params = new URLSearchParams(window.location.search);
  const statusFilter = params.get("review_status");
  const chapterFilter = params.get("review_chapter");
  const priorityFilter = params.get("review_priority");
  const flagFilter = params.get("review_flags");

  return {
    search: params.get("review_q") || "",
    statusFilter: REVIEW_STATUS_OPTIONS.has(statusFilter) ? statusFilter : "pending",
    chapterFilter: chapterFilter || "all",
    priorityFilter: PRIORITY_OPTIONS.has(priorityFilter) ? priorityFilter : "all",
    flagFilter: FLAG_FILTER_OPTIONS.has(flagFilter) ? flagFilter : "all",
    selectedParaId: params.get("review_para") || null,
  };
}

function buildReviewUrl({ search, statusFilter, chapterFilter, priorityFilter, flagFilter, selectedParaId }) {
  const url = new URL(window.location.href);
  url.searchParams.set("screen", "review");

  if (search) url.searchParams.set("review_q", search);
  else url.searchParams.delete("review_q");

  if (statusFilter && statusFilter !== "pending") url.searchParams.set("review_status", statusFilter);
  else url.searchParams.delete("review_status");

  if (chapterFilter && chapterFilter !== "all") url.searchParams.set("review_chapter", chapterFilter);
  else url.searchParams.delete("review_chapter");

  if (priorityFilter && priorityFilter !== "all") url.searchParams.set("review_priority", priorityFilter);
  else url.searchParams.delete("review_priority");

  if (flagFilter && flagFilter !== "all") url.searchParams.set("review_flags", flagFilter);
  else url.searchParams.delete("review_flags");

  if (selectedParaId) url.searchParams.set("review_para", selectedParaId);
  else url.searchParams.delete("review_para");

  return `${url.pathname}${url.search}${url.hash}`;
}

function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }

  return new Promise((resolve, reject) => {
    try {
      const el = document.createElement("textarea");
      el.value = text;
      el.setAttribute("readonly", "");
      el.style.position = "absolute";
      el.style.left = "-9999px";
      document.body.appendChild(el);
      el.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(el);
      if (!ok) throw new Error("Copy command was rejected");
      resolve();
    } catch (error) {
      reject(error);
    }
  });
}

function SummaryCard({ value, label }) {
  return (
    <div className="qa-stat">
      <div className="qa-stat-value">{value}</div>
      <div className="qa-stat-label">{label}</div>
    </div>
  );
}

function QueueItem({ item, selected, onSelect, flagCount = 0 }) {
  return (
    <div
      className={`qa-queue-item${selected ? " is-selected" : ""}`}
      onClick={() => onSelect(item.para_id)}
    >
      <div className="qa-queue-top">
        <div className="qa-queue-copy">
          <div className="qa-para">{item.para_id} · {item.chapterLabel}</div>
          <div className="qa-queue-title">{item.title}</div>
        </div>
        <span
          className="qa-chip"
          style={{ color: statusColor(item.review.status), borderColor: `${statusColor(item.review.status)}55` }}
        >
          {REVIEW_STATUS_META[item.review.status]?.label || "Pending"}
        </span>
      </div>

      <div className="qa-queue-meta">
        {item.sectionLabel}
        {item.page ? ` · page ${item.page}` : ""}
        <br />
        {item.activityCount} activities · {item.questionCount} questions · {item.flashcardCount} cards
      </div>

      <div className="qa-chip-row">
        {flagCount > 0 && (
          <span className="qa-chip" style={{ color: "#f43f5e", borderColor: "rgba(244,63,94,.45)" }}>
            {flagCount} learner flag{flagCount === 1 ? "" : "s"}
          </span>
        )}
        <span className="qa-chip">Priority {item.priority.score}</span>
        <span className="qa-chip">{priorityLabel(item.priority)}</span>
        {item.priority.reasons.slice(0, 2).map((reason) => (
          <span key={reason} className="qa-chip">{reason}</span>
        ))}
      </div>
    </div>
  );
}

function FlaggedItemsPanel({ flags, onSelectPara, onClearAll }) {
  const items = Object.values(flags || {})
    .filter((flag) => flag?.paraId)
    .sort((a, b) => String(b.flaggedAt || "").localeCompare(String(a.flaggedAt || "")));
  if (!items.length) return null;

  return (
    <div className="qa-flag-panel">
      <div className="qa-flag-head">
        <div>
          <div className="qa-flag-title">Learner-Flagged Items</div>
          <div className="qa-flag-copy">
            These are local item-level flags raised from lesson feedback. Convert them into paragraph review notes/statuses before clearing.
          </div>
        </div>
        <button className="qa-btn" onClick={onClearAll}>Clear Flags</button>
      </div>
      <div className="qa-flag-grid">
        {items.slice(0, 8).map((flag) => (
          <button
            key={flag.activityId}
            className="qa-flag-item"
            onClick={() => onSelectPara(flag.paraId)}
          >
            <div className="qa-flag-meta">
              {flag.paraId} · {flag.activityLabel || humanizeSlug(flag.activityType)}
            </div>
            <div className="qa-flag-text">{flag.paraTitle || "Flagged activity"}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function SourceBlock({ block }) {
  return (
    <div className="qa-block">
      <div className="qa-block-label">{humanizeSlug(block.block_type || "body")}</div>
      <div className="qa-card-copy">{block.content}</div>
    </div>
  );
}

function ActivityCard({ activity }) {
  const payload = activity.content || {};
  const extraJson = summarizePayload(payload);
  const orderedPhrase = Array.isArray(payload.correct_sequence) && Array.isArray(payload.word_bank)
    ? payload.correct_sequence.map((idx) => payload.word_bank[idx]).join(" ")
    : "";

  return (
    <div className="qa-card">
      <div className="qa-card-meta">
        {humanizeSlug(activity.activity_type)}
        {" · "}
        difficulty {activity.difficulty || 0}
        {" · "}
        {activity.generation_src || "local"}
      </div>
      {payload.instruction && <div className="qa-card-copy"><strong>Instruction:</strong> {payload.instruction}</div>}
      {payload.question_text && <div className="qa-card-copy"><strong>Question:</strong> {payload.question_text}</div>}
      {payload.prompt && <div className="qa-card-copy"><strong>Prompt:</strong> {payload.prompt}</div>}
      {payload.clearance && <div className="qa-card-copy"><strong>Clearance:</strong> {payload.clearance}</div>}
      {payload.situation && <div className="qa-card-copy"><strong>Situation:</strong> {payload.situation}</div>}
      {payload.para_context && <div className="qa-card-copy"><strong>Context:</strong> {payload.para_context}</div>}
      {payload.target_phrase && <div className="qa-card-copy"><strong>Target phrase:</strong> {payload.target_phrase}</div>}
      {orderedPhrase && <div className="qa-card-copy"><strong>Correct build:</strong> {orderedPhrase}</div>}
      {payload.original_phrase && <div className="qa-card-copy"><strong>Original phrase:</strong> {payload.original_phrase}</div>}
      {payload.display_text && <div className="qa-card-copy"><strong>Displayed phrase:</strong> {payload.display_text}</div>}
      {Array.isArray(payload.word_bank) && payload.word_bank.length > 0 && (
        <div className="qa-mini-grid">
          {payload.word_bank.map((token, idx) => (
            <div key={`${token}-${idx}`} className="qa-mini">{token}</div>
          ))}
        </div>
      )}
      {Array.isArray(payload.steps) && payload.steps.length > 0 && (
        <div className="qa-mini-grid">
          {payload.steps.map((step) => (
            <div key={step.id || step.text} className="qa-mini">{step.text}</div>
          ))}
        </div>
      )}
      {Array.isArray(payload.pairs) && payload.pairs.length > 0 && (
        <div className="qa-mini-grid">
          {payload.pairs.map((pair) => (
            <div key={`${pair.term}-${pair.definition}`} className="qa-mini">
              <strong>{pair.term}</strong>
              <br />
              {pair.definition}
            </div>
          ))}
        </div>
      )}
      {Array.isArray(payload.choices) && payload.choices.length > 0 && (
        <div className="qa-choice-list">
          {payload.choices.map((choice, idx) => (
            <div
              key={`${choice.text}-${idx}`}
              className={`qa-choice${choice.is_correct ? " is-correct" : ""}`}
            >
              {choice.text}
            </div>
          ))}
        </div>
      )}
      {payload.explanation && <div className="qa-card-copy"><strong>Explanation:</strong> {payload.explanation}</div>}
      <SourceCitation source={activity} compact />
      {extraJson && <pre className="qa-json">{extraJson}</pre>}
    </div>
  );
}

function FlashcardCard({ card }) {
  return (
    <div className="qa-card">
      <div className="qa-card-meta">{humanizeSlug(card.card_type)} · {card.generation_src || "local"}</div>
      <div className="qa-card-copy"><strong>Front:</strong> {card.front}</div>
      <div className="qa-card-copy"><strong>Back:</strong> {card.back}</div>
      <SourceCitation source={card} compact />
    </div>
  );
}

function QuestionCard({ question }) {
  return (
    <div className="qa-card">
      <div className="qa-card-meta">
        {humanizeSlug(question.question_type)}
        {" · "}
        difficulty {question.difficulty || 0}
        {" · "}
        {question.generation_src || "local_auto"}
      </div>
      <div className="qa-card-copy"><strong>Question:</strong> {question.question_text}</div>
      {question.choices?.length > 0 && (
        <div className="qa-choice-list">
          {question.choices.map((choice) => (
            <div
              key={choice.id}
              className={`qa-choice${choice.is_correct ? " is-correct" : ""}`}
            >
              {choice.choice_text}
            </div>
          ))}
        </div>
      )}
      {question.explanation && <div className="qa-card-copy"><strong>Explanation:</strong> {question.explanation}</div>}
      <SourceCitation source={question} compact />
    </div>
  );
}

export default function CurriculumReview({ curriculum, onBack }) {
  const routeStateRef = useRef(readReviewUrlState());
  const fileInputRef = useRef(null);
  const [search, setSearch] = useState(() => routeStateRef.current.search);
  const [statusFilter, setStatusFilter] = useState(() => routeStateRef.current.statusFilter);
  const [chapterFilter, setChapterFilter] = useState(() => routeStateRef.current.chapterFilter);
  const [priorityFilter, setPriorityFilter] = useState(() => routeStateRef.current.priorityFilter);
  const [flagFilter, setFlagFilter] = useState(() => routeStateRef.current.flagFilter);
  const [selectedParaId, setSelectedParaId] = useState(() => routeStateRef.current.selectedParaId);
  const [noteDraft, setNoteDraft] = useState("");
  const [notice, setNotice] = useState(null);
  const [importMode, setImportMode] = useState("merge");
  const [itemFlags, setItemFlags] = useState(loadItemFlags);

  const allQueue = useMemo(
    () => curriculum.getReviewQueue(),
    [curriculum.getReviewQueue],
  );

  const flagCountsByPara = useMemo(() => {
    const counts = {};
    for (const flag of Object.values(itemFlags || {})) {
      if (!flag?.paraId) continue;
      counts[flag.paraId] = (counts[flag.paraId] || 0) + 1;
    }
    return counts;
  }, [itemFlags]);

  const filteredQueue = useMemo(() => {
    const query = search.trim().toLowerCase();
    return allQueue.filter((item) => {
      const flagCount = flagCountsByPara[item.para_id] || 0;
      if (statusFilter !== "all" && item.review.status !== statusFilter) return false;
      if (chapterFilter !== "all" && String(item.chapter) !== chapterFilter) return false;
      if (priorityFilter !== "all" && item.priority.band !== priorityFilter) return false;
      if (flagFilter === "flagged" && flagCount === 0) return false;
      if (flagFilter === "unflagged" && flagCount > 0) return false;
      if (!query) return true;
      return (
        item.para_id.toLowerCase().includes(query)
        || item.title.toLowerCase().includes(query)
        || item.sectionLabel.toLowerCase().includes(query)
        || item.priority.reasons.some((reason) => reason.toLowerCase().includes(query))
        || flagsForPara(itemFlags, item.para_id).some((flag) => (
          String(flag.activityLabel || flag.activityType || "").toLowerCase().includes(query)
          || String(flag.itemText || "").toLowerCase().includes(query)
          || String(flag.correctAnswer || "").toLowerCase().includes(query)
        ))
      );
    });
  }, [allQueue, chapterFilter, flagCountsByPara, flagFilter, itemFlags, priorityFilter, search, statusFilter]);

  useEffect(() => {
    if (!filteredQueue.length) {
      setSelectedParaId(null);
      return;
    }
    if (!selectedParaId || !filteredQueue.some((item) => item.para_id === selectedParaId)) {
      setSelectedParaId(filteredQueue[0].para_id);
    }
  }, [filteredQueue, selectedParaId]);

  const selectedQueueItem = useMemo(
    () => filteredQueue.find((item) => item.para_id === selectedParaId)
      || allQueue.find((item) => item.para_id === selectedParaId)
      || null,
    [allQueue, filteredQueue, selectedParaId],
  );

  const detail = useMemo(
    () => (selectedParaId ? curriculum.getParagraphAudit(selectedParaId) : null),
    [curriculum.getParagraphAudit, selectedParaId],
  );
  const selectedFlags = useMemo(
    () => flagsForPara(itemFlags, selectedParaId),
    [itemFlags, selectedParaId],
  );

  useEffect(() => {
    setNoteDraft(detail?.review?.notes || "");
  }, [detail?.review?.notes, selectedParaId]);

  useEffect(() => {
    const nextUrl = buildReviewUrl({
      search,
      statusFilter,
      chapterFilter,
      priorityFilter,
      flagFilter,
      selectedParaId,
    });
    window.history.replaceState({}, "", nextUrl);
  }, [chapterFilter, flagFilter, priorityFilter, search, selectedParaId, statusFilter]);

  const summary = useMemo(() => {
    const counts = {
      total: allQueue.length,
      pending: 0,
      approved: 0,
      flagged: 0,
      learnerFlags: Object.keys(itemFlags || {}).length,
      highPriorityPending: 0,
    };
    for (const item of allQueue) {
      if (item.review.status === "pending") counts.pending += 1;
      if (item.review.status === "approved") counts.approved += 1;
      if (item.review.status === "weak" || item.review.status === "replace") counts.flagged += 1;
      if (item.review.status === "pending" && item.priority.band === "high") {
        counts.highPriorityPending += 1;
      }
    }
    return counts;
  }, [allQueue, itemFlags]);

  const chapterOptions = useMemo(
    () => [...new Set(allQueue.map((item) => item.chapter))].sort((a, b) => a - b),
    [allQueue],
  );

  const nextPending = useMemo(() => {
    if (!filteredQueue.length) return null;
    const start = Math.max(0, filteredQueue.findIndex((item) => item.para_id === selectedParaId));
    for (let idx = start + 1; idx < filteredQueue.length; idx += 1) {
      if (filteredQueue[idx].review.status === "pending") return filteredQueue[idx];
    }
    return filteredQueue.find((item) => item.review.status === "pending") || null;
  }, [filteredQueue, selectedParaId]);

  const shareUrl = useMemo(() => {
    const path = buildReviewUrl({
      search,
      statusFilter,
      chapterFilter,
      priorityFilter,
      flagFilter,
      selectedParaId,
    });
    return `${window.location.origin}${path}`;
  }, [chapterFilter, flagFilter, priorityFilter, search, selectedParaId, statusFilter]);

  function saveNotes() {
    if (!selectedParaId) return Promise.resolve();
    return curriculum.saveParagraphReview(selectedParaId, { notes: noteDraft })
      .then(() => setNotice({ tone: "success", text: `Saved notes for ${selectedParaId}.` }))
      .catch((error) => setNotice({ tone: "error", text: `Could not save notes: ${error.message}` }));
  }

  function updateStatus(status) {
    if (!selectedParaId) return Promise.resolve();
    return curriculum.saveParagraphReview(selectedParaId, { status, notes: noteDraft })
      .then(() => setNotice({ tone: "success", text: `Marked ${selectedParaId} as ${status}.` }))
      .catch((error) => setNotice({ tone: "error", text: `Could not update review status: ${error.message}` }));
  }

  function resetReview() {
    if (!selectedParaId) return Promise.resolve();
    setNoteDraft("");
    return curriculum.saveParagraphReview(selectedParaId, {
      status: "pending",
      notes: "",
    })
      .then(() => setNotice({ tone: "success", text: `Cleared review state for ${selectedParaId}.` }))
      .catch((error) => setNotice({ tone: "error", text: `Could not clear review state: ${error.message}` }));
  }

  function clearAllItemFlags() {
    const ok = window.confirm("Clear all local learner item flags? This does not change paragraph QA review notes.");
    if (!ok) return;
    setItemFlags({});
    saveItemFlags({});
    setNotice({ tone: "success", text: "Cleared local learner item flags." });
  }

  function clearSelectedFlags() {
    if (!selectedParaId || !selectedFlags.length) return;
    const next = { ...itemFlags };
    for (const flag of selectedFlags) delete next[flag.activityId];
    setItemFlags(next);
    saveItemFlags(next);
    setNotice({ tone: "success", text: `Cleared ${selectedFlags.length} learner flag${selectedFlags.length === 1 ? "" : "s"} for ${selectedParaId}.` });
  }

  function appendSelectedFlagsToNotes() {
    if (!selectedFlags.length) return;
    const flagNote = formatFlagNote(selectedFlags);
    setNoteDraft((current) => (
      current.trim()
        ? `${current.trim()}\n\n${flagNote}`
        : flagNote
    ));
    setNotice({ tone: "success", text: "Appended learner flags to the note draft. Save notes to persist them." });
  }

  async function convertSelectedFlagsToReview() {
    if (!selectedParaId || !selectedFlags.length) return;
    const flagNote = formatFlagNote(selectedFlags);
    const nextNotes = noteDraft.trim()
      ? `${noteDraft.trim()}\n\n${flagNote}`
      : flagNote;
    try {
      await curriculum.saveParagraphReview(selectedParaId, { status: "weak", notes: nextNotes });
      setNoteDraft(nextNotes);
      const next = { ...itemFlags };
      for (const flag of selectedFlags) delete next[flag.activityId];
      setItemFlags(next);
      saveItemFlags(next);
      setNotice({
        tone: "success",
        text: `Converted ${selectedFlags.length} learner flag${selectedFlags.length === 1 ? "" : "s"} into persisted QA review notes for ${selectedParaId}.`,
      });
    } catch (error) {
      setNotice({ tone: "error", text: `Could not convert learner flags: ${error.message}` });
    }
  }

  async function handleCopyLink() {
    try {
      await copyTextToClipboard(shareUrl);
      setNotice({ tone: "success", text: "Copied a deep link to the current review state." });
    } catch (error) {
      setNotice({ tone: "error", text: `Could not copy link: ${error.message}` });
    }
  }

  function handleExport() {
    try {
      const payload = curriculum.exportReviewState();
      const stamp = payload.exportedAt.slice(0, 19).replace(/[:T]/g, "-");
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `atc-review-export-${stamp}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(objectUrl);
      setNotice({ tone: "success", text: `Exported ${payload.reviewCount} review records.` });
    } catch (error) {
      setNotice({ tone: "error", text: `Could not export review data: ${error.message}` });
    }
  }

  function beginImport(mode) {
    setImportMode(mode);
    fileInputRef.current?.click();
  }

  async function handleImport(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    try {
      const text = await file.text();
      const payload = JSON.parse(text);

      if (importMode === "replace") {
        const ok = window.confirm("Replace all local review notes and statuses with the contents of this file?");
        if (!ok) return;
      }

      const result = await curriculum.importReviewState(payload, { mode: importMode });
      setNotice({
        tone: "success",
        text: `${importMode === "replace" ? "Replaced" : "Merged"} ${result.importedCount} review records. Stored total: ${result.totalCount}.`,
      });
    } catch (error) {
      setNotice({ tone: "error", text: `Could not import review data: ${error.message}` });
    }
  }

  return (
    <div className="qa-shell">
      <style>{CSS}</style>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json,.json"
        style={{ display: "none" }}
        onChange={handleImport}
      />

      <div className="qa-header">
        <div>
          <h1>Curriculum QA</h1>
          <div className="qa-sub">
            Review the shipped curriculum paragraph by paragraph, inspect parsed source text,
            and persist approved, weak, or replace decisions in repo-backed review state instead of browser storage.
          </div>
        </div>
        <div className="qa-header-actions">
          {nextPending && (
            <button className="qa-btn" onClick={() => setSelectedParaId(nextPending.para_id)}>
              Next Pending
            </button>
          )}
          <button className="qa-btn" onClick={handleCopyLink}>Copy Link</button>
          <button className="qa-btn" onClick={handleExport}>Export Reviews</button>
          <button className="qa-btn" onClick={() => beginImport("merge")}>Import Merge</button>
          <button className="qa-btn" onClick={() => beginImport("replace")}>Import Replace</button>
          <button className="qa-btn qa-primary" onClick={onBack}>Back To Map</button>
        </div>
      </div>

      <div className="qa-body">
        {notice && (
          <div className={`qa-notice ${notice.tone || "success"}`}>
            {notice.text}
          </div>
        )}

        <div className="qa-banner">
          <strong>Trust failsafe:</strong> learner-facing activities, flashcards, and quiz questions now expose a direct FAA source link that opens the official 7110.65BB PDF at the paragraph page, with heading and excerpt cues so users can verify the curriculum against the order itself.
          <br />
          <strong>Review storage:</strong>{" "}
          {curriculum.reviewPersistence.mode === "backend"
            ? `persisting to ${curriculum.reviewPersistence.storagePath || "the backend review store"}`
            : curriculum.reviewPersistence.mode === "local_static"
              ? "static site mode; review edits are stored in this browser only"
            : `backend review persistence is unavailable: ${curriculum.reviewPersistence.error || "unknown error"}`}
        </div>

        <div className="qa-summary">
          <SummaryCard value={summary.total} label="Paragraphs" />
          <SummaryCard value={summary.pending} label="Pending Review" />
          <SummaryCard value={summary.flagged} label="Flagged" />
          <SummaryCard value={summary.learnerFlags} label="Learner Item Flags" />
        </div>

        <FlaggedItemsPanel
          flags={itemFlags}
          onSelectPara={setSelectedParaId}
          onClearAll={clearAllItemFlags}
        />

        <div className="qa-controls">
          <input
            className="qa-input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search para id, title, section, or reason…"
          />
          <select className="qa-select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="weak">Weak</option>
            <option value="replace">Replace</option>
          </select>
          <select className="qa-select" value={chapterFilter} onChange={(event) => setChapterFilter(event.target.value)}>
            <option value="all">All chapters</option>
            {chapterOptions.map((chapter) => (
              <option key={chapter} value={String(chapter)}>Chapter {chapter}</option>
            ))}
          </select>
          <select className="qa-select" value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
            <option value="all">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="baseline">Baseline</option>
          </select>
          <select className="qa-select" value={flagFilter} onChange={(event) => setFlagFilter(event.target.value)}>
            <option value="all">All flag states</option>
            <option value="flagged">Learner flagged</option>
            <option value="unflagged">No learner flags</option>
          </select>
        </div>

        <div className="qa-layout">
          <div className="qa-panel">
            <div className="qa-panel-head">
              <div>
                <div className="qa-panel-title">Review Queue</div>
                <div className="qa-panel-copy">{filteredQueue.length} paragraphs in the current filter</div>
              </div>
            </div>
            <div className="qa-queue">
              {filteredQueue.length === 0 ? (
                <div className="qa-empty">
                  <strong>No paragraphs match</strong>
                  Adjust the filters or search to continue reviewing.
                </div>
              ) : (
                filteredQueue.map((item) => (
                  <QueueItem
                    key={item.para_id}
                    item={item}
                    selected={item.para_id === selectedParaId}
                    onSelect={setSelectedParaId}
                    flagCount={flagCountsByPara[item.para_id] || 0}
                  />
                ))
              )}
            </div>
          </div>

          <div className="qa-panel">
            <div className="qa-panel-head">
              <div>
                <div className="qa-panel-title">Paragraph Detail</div>
                <div className="qa-panel-copy">Full source blocks plus generated learning assets</div>
              </div>
            </div>

            {!detail || !selectedQueueItem ? (
              <div className="qa-empty">
                <strong>Select a paragraph</strong>
                Choose a review target from the queue to inspect its source blocks and generated content.
              </div>
            ) : (
              <div className="qa-detail">
                <div className="qa-detail-head">
                  <div>
                    <div className="qa-para">
                      {detail.para_id} · Chapter {detail.chapter} · {selectedQueueItem.sectionLabel}
                      {detail.page ? ` · page ${detail.page}` : ""}
                    </div>
                    <div className="qa-detail-title">{detail.title}</div>
                    <div className="qa-detail-sub">
                      Priority {selectedQueueItem.priority.score} · {priorityLabel(selectedQueueItem.priority)}
                      {" · "}
                      {detail.activities.length} activities · {detail.questions.length} questions · {detail.flashcards.length} cards
                      <br />
                      Last review: {formatDate(detail.review.updatedAt)}
                    </div>
                  </div>
                  <div className="qa-chip-row">
                    <span
                      className="qa-chip"
                      style={{ color: statusColor(detail.review.status), borderColor: `${statusColor(detail.review.status)}55` }}
                    >
                      {REVIEW_STATUS_META[detail.review.status]?.label || "Pending"}
                    </span>
                    {selectedQueueItem.priority.reasons.map((reason) => (
                      <span key={reason} className="qa-chip">{reason}</span>
                    ))}
                  </div>
                </div>

                <SourceCitation source={detail} />

                {selectedFlags.length > 0 && (
                  <div className="qa-flag-panel" style={{ marginTop: 14 }}>
                    <div className="qa-flag-head">
                      <div>
                        <div className="qa-flag-title">
                          {selectedFlags.length} Learner Flag{selectedFlags.length === 1 ? "" : "s"} On This Paragraph
                        </div>
                        <div className="qa-flag-copy">
                          Append these to the formal notes, mark the paragraph weak/replace if appropriate, then clear the local flags.
                        </div>
                      </div>
                      <div className="qa-header-actions">
                        <button className="qa-btn" onClick={appendSelectedFlagsToNotes}>Append To Notes</button>
                        <button className="qa-btn qa-primary" onClick={convertSelectedFlagsToReview}>Convert To Weak Review</button>
                        <button className="qa-btn" onClick={clearSelectedFlags}>Clear Paragraph Flags</button>
                      </div>
                    </div>
                    <div className="qa-flag-grid">
                      {selectedFlags.map((flag) => (
                        <div key={flag.activityId} className="qa-flag-item" style={{ cursor: "default" }}>
                          <div className="qa-flag-meta">
                            {flag.activityLabel || humanizeSlug(flag.activityType)} · {formatDate(flag.flaggedAt)}
                          </div>
                          <div className="qa-flag-text">
                            {flag.itemText || flag.activityId}
                            {flag.correctAnswer && (
                              <>
                                <br />
                                <strong>Expected:</strong> {flag.correctAnswer}
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="qa-status-row">
                  {Object.entries(REVIEW_STATUS_META).map(([status, meta]) => (
                    <button
                      key={status}
                      className={`qa-status-btn${detail.review.status === status ? " is-active" : ""}`}
                      style={{ color: meta.color }}
                      onClick={() => updateStatus(status)}
                    >
                      Mark {meta.label}
                    </button>
                  ))}
                </div>

                <div style={{ marginTop: 14 }}>
                  <textarea
                    className="qa-textarea"
                    value={noteDraft}
                    onChange={(event) => setNoteDraft(event.target.value)}
                    placeholder="Add reviewer notes, examples of weak wording, or replacement guidance…"
                  />
                  <div className="qa-note-actions">
                    <button className="qa-btn" onClick={saveNotes}>Save Notes</button>
                    <button className="qa-btn" onClick={resetReview}>Clear Review</button>
                  </div>
                </div>

                <div className="qa-grid">
                  <div className="qa-section">
                    <h3>Parsed 7110 Blocks <span className="qa-count">{detail.blocks.length}</span></h3>
                    {detail.blocks.map((block, idx) => (
                      <SourceBlock key={`${block.block_type}-${idx}`} block={block} />
                    ))}
                  </div>

                  <div className="qa-section">
                    <h3>Activities <span className="qa-count">{detail.activities.length}</span></h3>
                    {detail.activities.map((activity) => (
                      <ActivityCard key={activity.id} activity={activity} />
                    ))}
                  </div>

                  <div className="qa-section">
                    <h3>Quiz Questions <span className="qa-count">{detail.questions.length}</span></h3>
                    {detail.questions.map((question) => (
                      <QuestionCard key={question.id} question={question} />
                    ))}
                  </div>

                  <div className="qa-section">
                    <h3>Flashcards <span className="qa-count">{detail.flashcards.length}</span></h3>
                    {detail.flashcards.map((card) => (
                      <FlashcardCard key={card.id} card={card} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
