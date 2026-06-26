import { useEffect, useState } from "react";
import SourceCitation from "./SourceCitation";

const ITEM_FLAGS_KEY = "atc_item_flags_v1";

const TYPE_LABELS = {
  phraseology_builder: "Phraseology builder",
  spot_the_error: "Spot the error",
  sequence_steps: "Sequence the steps",
  match_pairs: "Match pairs",
  readback_check: "Read-back check",
  situation_action: "Situation -> action",
  directive_check: "Directive check",
  conditional_rule_check: "Conditional rule",
  term_definition_check: "Term definition",
  document_control_check: "Document control",
  requirement_check: "Requirement check",
  scope_check: "Applicability check",
  capability_check: "System capability",
  reference_check: "Reference check",
  minima_rule_check: "Minima rule",
  list_membership: "List membership",
  table_lookup: "Table lookup",
  visual_interpretation: "Visual interpretation",
  example_check: "Example check",
  knowledge_check: "Knowledge check",
};

function loadItemFlags() {
  try {
    const raw = JSON.parse(localStorage.getItem(ITEM_FLAGS_KEY) || "{}");
    return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  } catch {
    return {};
  }
}

function saveItemFlags(state) {
  try {
    localStorage.setItem(ITEM_FLAGS_KEY, JSON.stringify(state));
  } catch {}
}

const TYPE_HELP = {
  phraseology_builder: "Build the controller transmission from operational context. Exact wording matters when the order prescribes phraseology.",
  spot_the_error: "Find the operationally meaningful error, not a harmless difference in example values.",
  sequence_steps: "Put required controller actions in the order the rule expects.",
  match_pairs: "Connect terms, roles, or conditions to their correct operational meanings.",
  readback_check: "Decide whether the readback preserves the required clearance or instruction.",
  situation_action: "Apply the paragraph to a realistic control situation.",
  directive_check: "Determine whether the instruction follows the controller directive.",
  conditional_rule_check: "Apply a rule that depends on stated conditions.",
  term_definition_check: "Use the definition precisely enough to apply it correctly.",
  document_control_check: "Check document-control and administrative requirements.",
  requirement_check: "Identify what the controller must, may, or must not do.",
  scope_check: "Decide whether the paragraph applies to this situation.",
  capability_check: "Reason about equipment, system, or facility capability limits.",
  reference_check: "Use the cited paragraph relationship correctly.",
  minima_rule_check: "Apply numeric minima or thresholds from the rule.",
  list_membership: "Recognize whether an item belongs in the required list.",
  table_lookup: "Use tabular information rather than memorizing isolated values.",
  visual_interpretation: "Interpret a figure, geometry, diagram, or layout rule.",
  example_check: "Evaluate whether the example reflects approved use, while keeping context in mind.",
  knowledge_check: "Answer from the substance of the paragraph.",
};

const CHOICE_ACTIVITY_TYPES = new Set([
  "readback_check",
  "situation_action",
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
]);
const SOURCE_LOOKUP_TYPES = new Set([
  "visual_interpretation",
  "table_lookup",
  "minima_rule_check",
]);
const ALWAYS_SHOW_FOCUS_TYPES = new Set([
  "phraseology_builder",
  "spot_the_error",
  "sequence_steps",
  "match_pairs",
  "readback_check",
]);

const SELF_CONTAINED_STATEMENT_TYPES = new Set([
  "scope_check",
  "requirement_check",
  "capability_check",
  "conditional_rule_check",
  "term_definition_check",
  "document_control_check",
  "minima_rule_check",
]);
const DIRECT_QUESTION_RE = /^(what|which|who|when|where|why|how|is|are|do|does|did|can|could|should|would|will|must|may)\b/i;

function sentenceCaseLead(text) {
  if (!text) return text;
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

function isTrueFalseActivity(activity) {
  const choices = activity?.content?.choices ?? [];
  if (choices.length !== 2) return false;
  const labels = new Set(choices.map((choice) => String(choice?.text ?? "").trim().toLowerCase()));
  return labels.has("true") && labels.has("false") && labels.size === 2;
}

function shuffle(items) {
  const next = [...items];
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [next[i], next[j]] = [next[j], next[i]];
  }
  return next;
}

function displayInstruction(activity) {
  if (!activity) return "";
  const instruction = activity.content.instruction || "";
  const hasQuestionText = Boolean(displayQuestionText(activity) || activity?.content?.prompt);
  if (!SELF_CONTAINED_STATEMENT_TYPES.has(activity.activity_type) || !isTrueFalseActivity(activity)) {
    if (
      activity.activity_type === "knowledge_check"
      && instruction.trim() === "Choose the best answer."
      && hasQuestionText
    ) {
      return "";
    }
    if (activity.activity_type === "list_membership" && hasQuestionText) {
      return "";
    }
    return instruction;
  }
  return "Is this statement operationally correct?";
}

function displayQuestionText(activity) {
  const questionText = activity?.content?.question_text;
  if (!questionText) {
    return questionText;
  }
  const underMatch = questionText.match(/^Under [^,]+,\s*(.+)$/i);
  if (underMatch) {
    const remainder = underMatch[1].trim();
    if (DIRECT_QUESTION_RE.test(remainder)) {
      return sentenceCaseLead(remainder);
    }
    if (isTrueFalseActivity(activity)) {
      return sentenceCaseLead(remainder.replace(/^(this|these|that|those)\s+/i, ""));
    }
    return sentenceCaseLead(remainder);
  }
  if (
    SELF_CONTAINED_STATEMENT_TYPES.has(activity.activity_type)
    && isTrueFalseActivity(activity)
    && !/^this order\b/i.test(questionText)
    && /^(this|these|that|those)\b/i.test(questionText)
  ) {
    return sentenceCaseLead(questionText.replace(/^(this|these|that|those)\s+/i, ""));
  }
  return questionText;
}

const CSS = `
*{box-sizing:border-box;margin:0;padding:0;}
:root{
  --bg:#30302e;--surf:#11120e;--card:#11120e;--card2:#13140f;
  --b1:rgba(226,219,193,.22);--b2:rgba(226,219,193,.34);
  --amber:#d8a21c;--amber-d:rgba(216,162,28,.10);--amber-b:rgba(216,162,28,.34);
  --green:#9aa37f;--green-d:rgba(154,163,127,.12);--green-b:rgba(154,163,127,.34);
  --red:#bd766c;--red-d:rgba(189,118,108,.12);--red-b:rgba(189,118,108,.34);
  --blue:#9fb0aa;--blue-d:rgba(159,176,170,.12);
  --txt:#f1ead7;--txt2:#b7ae95;--txt3:#746f61;
  --font:'Share Tech Mono',ui-monospace,monospace;--mono:'Share Tech Mono',ui-monospace,monospace;--label:'Share Tech Mono',ui-monospace,monospace;
  --r:2px;
}
body{background:var(--bg);color:var(--txt);font-family:var(--font);-webkit-text-size-adjust:100%;}
button,a,.choice,.chip,.step,.pair-chip{touch-action:manipulation;}
.lp{display:flex;flex-direction:column;height:100vh;height:100dvh;max-width:720px;margin:0 auto;position:relative;overflow:hidden;background:var(--surf);border-left:1px solid var(--b1);border-right:1px solid var(--b1);}
.lp *{font-family:var(--mono)!important;box-shadow:none!important;border-radius:2px!important;}
.lp img{border-radius:0!important;}
.lp-topbar{padding:0 20px;height:44px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--b1);flex-shrink:0;}
.lp-back{background:none;border:none;color:var(--txt2);font-size:18px;cursor:pointer;padding:0 4px;}
.lp-count{font-family:var(--label);font-size:13px;color:var(--txt2);white-space:nowrap;font-weight:600;}
.lp-progress-meta{font-family:var(--label);font-size:11px;color:var(--txt2);letter-spacing:.06em;text-transform:uppercase;white-space:nowrap;}
.lp-progress-meta strong{color:var(--green);font-weight:700;}
.lp-end-save{height:28px;padding:0 9px;border-radius:7px;border:1px solid var(--b1);background:var(--card);color:var(--txt2);cursor:pointer;font-family:var(--label);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}
.lp-end-save:hover{border-color:var(--amber-b);color:var(--amber);background:var(--amber-d);}
.lp-sub{padding:10px 20px 0;display:flex;align-items:center;gap:8px;flex-shrink:0;min-width:0;}
.lp-badge{font-family:var(--label);font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#8fa1b8;white-space:nowrap;}
.lp-pararef{font-family:var(--label);font-size:11px;color:#536986;letter-spacing:.03em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;}
.lp-pararef::before{content:'· ';color:#27302a;}
.lp-source-link{color:#8b6d29;text-decoration:none;font-weight:700;letter-spacing:.04em;}
.lp-source-link:hover{text-decoration:underline;}
.lp-main{flex:1;overflow-y:auto;padding:10px 20px 8px;display:flex;flex-direction:column;gap:11px;}
.lp-session-note{border-left:2px solid var(--amber);padding:2px 0 2px 9px;color:#8c9c91;font-size:12px;line-height:1.45;}
.lp-session-note strong{display:block;font-family:var(--label);font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--amber);margin-bottom:2px;}
.lp-context{display:flex;align-items:center;justify-content:space-between;gap:10px;color:#5e748f;}
.lp-context-title{display:none;}
.lp-context-copy{font-size:11.5px;line-height:1.4;}
.lp-context-copy::before{content:'Focus: ';font-family:var(--label);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--txt3);}
.lp-context-meter{display:none;}
.lp-dot{width:8px;height:8px;border-radius:50%;background:var(--card2);border:1px solid var(--b1);}
.lp-dot.done{background:var(--txt3);border-color:var(--b1);}
.lp-dot.correct{background:var(--green);border-color:var(--green-b);}
.lp-dot.wrong{background:var(--red);border-color:var(--red-b);}
.lp-dot.current{background:var(--amber);border-color:var(--amber-b);}
.lookup-panel{background:rgba(13,17,15,.58);border:1px solid rgba(122,167,217,.18);border-radius:8px;padding:10px 11px;display:grid;gap:8px;}
.lookup-title{font-family:var(--label);font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--blue);}
.lookup-copy{display:none;}
.lookup-source-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;}
.lookup-source-card{border:1px solid rgba(122,167,217,.18);background:rgba(7,10,9,.36);border-radius:6px;padding:7px 8px;font-size:11px;line-height:1.4;color:var(--txt);}
.lookup-source-card>strong{display:block;font-family:var(--label);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--blue);margin-bottom:3px;}
.lookup-list{margin:0;padding-left:15px;color:#e4ece2;}
.lookup-list li{margin:2px 0;}
.lookup-list strong{font-weight:700;color:#9dc4ff;}
.lookup-steps{display:none;}
.lookup-step{border:1px solid rgba(122,167,217,.2);background:rgba(122,167,217,.07);border-radius:8px;padding:8px 9px;font-size:11px;line-height:1.4;color:#e4ece2;}
.lookup-step strong{display:block;font-family:var(--label);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--blue);margin-bottom:2px;}
.lp-instruction{font-size:13px;font-weight:500;line-height:1.45;color:#8fa1b8;}
.lp-instruction:empty{display:none;}
.atc-card{background:var(--card);border:1px solid var(--b1);border-radius:var(--r);padding:13px 15px 13px;font-family:var(--mono);font-size:13px;line-height:1.65;position:relative;margin-top:8px;}
.atc-tag{position:absolute;top:-9px;left:12px;background:var(--amber);color:#000;font-family:var(--label);font-size:8.5px;font-weight:700;letter-spacing:.12em;padding:2px 7px;border-radius:3px;text-transform:uppercase;}
.atc-card.situation{font-family:var(--font);font-size:13.5px;}
.atc-card.prompt-card{margin-top:0;background:transparent;border-color:rgba(36,61,92,.58);font-family:var(--font);font-size:16px;line-height:1.45;padding:12px 0 11px;border-left:none;border-right:none;border-radius:0;}
.atc-card.prompt-card .atc-tag{display:none;}
.atc-excerpt{font-size:11.5px;color:var(--txt2);font-style:italic;border-left:2px solid var(--b1);padding-left:10px;margin-top:10px;font-family:var(--font);line-height:1.55;}
.build-zone{min-height:52px;background:var(--card);border:1.5px solid var(--b1);border-radius:var(--r);padding:9px 11px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;transition:border-color .2s;}
.build-zone.active{border-color:var(--amber);}
.build-empty{color:var(--txt3);font-family:var(--mono);font-size:12px;}
.build-meta{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:8px;}
.build-hint{font-size:11.5px;color:var(--txt2);line-height:1.5;}
.build-clear{background:none;border:none;color:var(--txt2);cursor:pointer;font-family:var(--label);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:0;}
.build-clear:hover{color:var(--amber);}
.bank-label{font-family:var(--label);font-size:9.5px;letter-spacing:.1em;color:var(--txt3);text-transform:uppercase;margin-bottom:3px;}
.bank{display:flex;flex-wrap:wrap;gap:7px;}
.chip{display:inline-flex;align-items:center;height:33px;padding:0 11px;border-radius:7px;font-family:var(--mono);font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:all .14s;border:1.5px solid transparent;white-space:nowrap;}
.chip-bank{background:var(--card2);color:var(--txt);border-color:var(--b1);}
.chip-bank:hover{border-color:var(--amber);color:var(--amber);}
.chip-used{background:var(--card2);opacity:.2;pointer-events:none;cursor:default;border-color:var(--b1);}
.chip-built{background:var(--amber-d);color:var(--amber);border-color:var(--amber);}
.chip-token{background:var(--card2);color:var(--txt);border-color:var(--b1);}
.chip-token:hover{border-color:var(--red);color:var(--red);}
.chip-token-sel{background:var(--red-d);color:var(--red);border-color:var(--red);}
.step-list{display:flex;flex-direction:column;gap:8px;}
.step{display:flex;align-items:flex-start;gap:11px;background:var(--card);border:1.5px solid var(--b1);border-radius:var(--r);padding:11px 13px;cursor:pointer;transition:all .14s;}
.step:hover{border-color:var(--b2);}
.step.step-sel{border-color:var(--amber);background:var(--amber-d);}
.step-num{font-family:var(--label);font-size:13px;font-weight:700;color:var(--txt2);min-width:18px;padding-top:1px;}
.step.step-sel .step-num{color:var(--amber);}
.step-text{font-size:13px;line-height:1.45;flex:1;}
.step-hint{font-family:var(--label);font-size:10px;color:var(--txt2);letter-spacing:.04em;margin-top:3px;}
.pairs-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:start;}
.pair-col{display:flex;flex-direction:column;gap:7px;}
.pair-col-label{font-family:var(--label);font-size:9.5px;letter-spacing:.1em;color:var(--txt3);text-transform:uppercase;margin-bottom:1px;}
.pair-chip{background:var(--card);border:1.5px solid var(--b1);border-radius:8px;padding:9px 11px;font-size:12px;line-height:1.4;cursor:pointer;transition:all .14s;min-height:52px;display:flex;align-items:center;}
.pair-chip:hover{border-color:var(--b2);}
.pair-chip.pair-sel{border-color:var(--amber);background:var(--amber-d);color:var(--amber);}
.pair-chip.pair-matched{border-color:var(--green-b);background:var(--green-d);color:var(--green);cursor:default;}
.pair-chip.pair-wrong{border-color:var(--red);background:var(--red-d);animation:shake .35s ease-out;}
.pair-chip.pair-dim{opacity:.25;pointer-events:none;}
.choices{display:flex;flex-direction:column;gap:7px;}
.choice{background:rgba(17,22,20,.9);border:1px solid var(--b1);border-radius:8px;padding:12px 15px 12px 40px;font-size:13.5px;line-height:1.5;cursor:pointer;transition:all .14s;position:relative;}
.choice::before{content:'';position:absolute;left:13px;top:14px;width:15px;height:15px;border-radius:50%;border:1.5px solid var(--b2);transition:all .14s;}
.choice:hover{border-color:var(--b2);}
.choice.choice-sel{border-color:rgba(122,167,217,.8);background:rgba(122,167,217,.13);}
.choice.choice-sel::before{border-color:var(--blue);background:var(--blue);}
.lp-footer{padding:12px 20px 20px;flex-shrink:0;}
.lp-shortcuts{font-size:11px;color:var(--txt3);text-align:center;margin-top:8px;line-height:1.4;}
.lp-actions{display:grid;grid-template-columns:minmax(0,1fr) 120px;gap:8px;}
.btn{width:100%;height:49px;border:none;border-radius:var(--r);font-family:var(--label);font-size:14px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;cursor:pointer;transition:all .15s;}
.btn-check{background:var(--amber);color:#000;}
.btn-check:hover{filter:brightness(1.08);}
.btn-check:disabled{background:var(--card2);color:var(--txt3);cursor:default;}
.btn-giveup{background:transparent;color:var(--txt2);border:1.5px solid var(--b1);}
.btn-giveup:hover{border-color:var(--red-b);color:var(--red);background:var(--red-d);}
.btn-continue{background:var(--green);color:#000;}
.btn-continue:hover{filter:brightness(1.1);}
.btn-remediate{background:transparent;color:var(--amber);border:1.5px solid var(--amber-b);margin-bottom:8px;}
.btn-remediate:hover{background:var(--amber-d);}
.btn-flag{background:transparent;color:var(--txt2);border:1.5px solid var(--b1);margin-bottom:8px;}
.btn-flag:hover{background:var(--red-d);color:var(--red);border-color:var(--red-b);}
.btn-flag.active{background:var(--red-d);color:var(--red);border-color:var(--red-b);}
.feedback{position:absolute;bottom:0;left:0;right:0;border-top:1px solid;padding:18px 20px 22px;animation:slideUp .22s ease-out;z-index:10;}
@keyframes slideUp{from{transform:translateY(100%);opacity:0}to{transform:translateY(0);opacity:1}}
.feedback.fb-correct{background:#07150d;border-color:var(--green-b);}
.feedback.fb-wrong{background:#15080d;border-color:var(--red-b);}
.fb-title{font-family:var(--label);font-size:17px;font-weight:700;letter-spacing:.04em;margin-bottom:5px;}
.feedback.fb-correct .fb-title{color:var(--green);}
.feedback.fb-wrong .fb-title{color:var(--red);}
.fb-label{font-family:var(--label);font-size:9.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--txt3);margin-bottom:4px;}
.fb-explain{font-size:12px;color:var(--txt2);line-height:1.55;margin-bottom:13px;}
.fb-answer-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;}
.fb-answer{background:rgba(17,22,20,.9);border:1px solid var(--b1);border-radius:8px;padding:8px 9px;min-width:0;}
.fb-answer.correct{border-color:var(--green-b);background:rgba(57,195,111,.08);}
.fb-answer.user-wrong{border-color:var(--red-b);background:rgba(244,63,94,.08);}
.fb-answer-title{font-family:var(--label);font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--txt3);margin-bottom:3px;}
.fb-answer-text{font-size:11.5px;color:var(--txt);line-height:1.45;word-break:break-word;}
.fb-concepts{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;}
.fb-concept{border:1px solid var(--amber-b);background:var(--amber-d);color:var(--amber);border-radius:999px;padding:4px 8px;font-family:var(--label);font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;}
.lp-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:32px 24px;gap:18px;text-align:center;}
.lp-empty-title{font-family:var(--label);font-size:24px;font-weight:700;letter-spacing:.05em;color:var(--amber);}
.lp-empty-copy{font-size:14px;color:var(--txt2);line-height:1.6;max-width:320px;}
@keyframes shake{0%,100%{transform:translateX(0)}18%{transform:translateX(-9px)}36%{transform:translateX(7px)}54%{transform:translateX(-5px)}72%{transform:translateX(4px)}}
@keyframes slideIn{from{opacity:0;transform:translateX(28px)}to{opacity:1;transform:translateX(0)}}
.slide-in{animation:slideIn .28s ease-out;}
@media (max-width:520px){
  .lp{max-width:none}
  .lp-topbar{padding:env(safe-area-inset-top) 14px 0;gap:7px;height:auto;min-height:calc(44px + env(safe-area-inset-top))}
  .lp-back,.lp-end-save,.build-clear{min-height:40px;min-width:40px}
  .lp-progress-meta{display:none}
  .lp-sub{padding:9px 14px 0;align-items:flex-start;flex-wrap:wrap}
  .lp-pararef{font-size:10px;line-height:1.35;white-space:normal;overflow:visible;text-overflow:clip;flex:1 1 100%}
  .lp-pararef::before{content:''}
  .lp-source-link{display:inline-flex;align-items:center;min-height:40px;padding:0 8px;margin-left:-8px}
  .lp-main{padding:14px 14px 8px}
  .lookup-source-grid{grid-template-columns:1fr}
  .lp-context{grid-template-columns:1fr}
  .lp-context-meter{justify-content:flex-start;min-width:0}
  .pairs-grid{grid-template-columns:1fr}
  .lp-actions{grid-template-columns:1fr}
  .fb-answer-grid{grid-template-columns:1fr}
  .feedback{padding:15px 14px 18px;max-height:78vh;overflow:auto}
  .lp-footer{padding:10px 14px max(16px, env(safe-area-inset-bottom))}
  .chip{height:auto;min-height:40px;padding:6px 12px}
  .choice,.step,.pair-chip{min-height:44px}
}
`;

function PhraseologyBuilder({ content, built, onBuild, onRemove, onClear }) {
  const { word_bank: wordBank } = content;
  const usedSet = new Set(built);

  return (
    <>
      {content.situation && (
        <div className="atc-card situation">
          <span className="atc-tag">Situation</span>
          {content.situation}
        </div>
      )}
      <div className={`build-zone${built.length ? " active" : ""}`}>
        {built.length === 0 ? (
          <span className="build-empty">Tap words below to build the phrase...</span>
        ) : (
          built.map((idx, pos) => (
            <span
              key={`${idx}-${pos}`}
              className="chip chip-built"
              onClick={() => onRemove(pos)}
            >
              {wordBank[idx]}
            </span>
          ))
        )}
      </div>
      {built.length > 0 && (
        <div className="build-meta">
          <div className="build-hint">
            Tap a placed tile to remove it, or clear the whole transmission and rebuild.
          </div>
          <button className="build-clear" onClick={onClear}>
            Clear all
          </button>
        </div>
      )}
      <div>
        <div className="bank-label">Word bank - tap to use, tap again to remove</div>
        <div className="bank">
          {wordBank.map((word, i) => (
            <span
              key={`${word}-${i}`}
              className={`chip ${usedSet.has(i) ? "chip-used" : "chip-bank"}`}
              onClick={() => !usedSet.has(i) && onBuild(i)}
            >
              {word}
            </span>
          ))}
        </div>
      </div>
    </>
  );
}

function SpotTheError({ content, selected, onSelect }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {content.tokens.map((token, i) => (
        <span
          key={`${token}-${i}`}
          className={`chip ${selected === i ? "chip-token-sel" : "chip-token"}`}
          onClick={() => onSelect(i === selected ? null : i)}
        >
          {token}
        </span>
      ))}
    </div>
  );
}

function SequenceSteps({ content, order, selectedIdx, onTap }) {
  const stepMap = Object.fromEntries(content.steps.map((step) => [step.id, step.text]));

  return (
    <div className="step-list">
      {order.map((id, i) => (
        <div
          key={id}
          className={`step${selectedIdx === i ? " step-sel" : ""}`}
          onClick={() => onTap(i)}
        >
          <span className="step-num">{i + 1}</span>
          <div>
            <div className="step-text">{stepMap[id]}</div>
            {selectedIdx !== null && selectedIdx !== i && (
              <div className="step-hint">Tap to place here</div>
            )}
          </div>
        </div>
      ))}
      {selectedIdx === null && (
        <p style={{ fontSize: 11.5, color: "var(--txt2)", marginTop: 2 }}>
          Tap a step to select, then tap its destination to swap.
        </p>
      )}
    </div>
  );
}

function MatchPairs({
  content,
  shuffledDefs,
  matchSel,
  matched,
  wrongFlash,
  onTermTap,
  onDefTap,
}) {
  const terms = content.pairs.map((pair) => pair.term);

  return (
    <div className="pairs-grid">
      <div className="pair-col">
        <div className="pair-col-label">Terms</div>
        {terms.map((term) => {
          let cls = "pair-chip";
          if (matched[term]) cls += " pair-matched";
          else if (matchSel === term) cls += " pair-sel";
          return (
            <div
              key={term}
              className={cls}
              onClick={() => !matched[term] && onTermTap(term)}
            >
              {term}
            </div>
          );
        })}
      </div>
      <div className="pair-col">
        <div className="pair-col-label">Definitions</div>
        {shuffledDefs.map((definition) => {
          const isMatched = Object.values(matched).includes(definition);
          let cls = "pair-chip";
          if (isMatched) cls += " pair-matched";
          else if (wrongFlash === definition) cls += " pair-wrong";
          else if (!matchSel && !isMatched) cls += " pair-dim";
          return (
            <div
              key={definition}
              className={cls}
              onClick={() => matchSel && !isMatched && onDefTap(definition)}
            >
              {definition}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function buildChoiceOrder(choices = []) {
  const order = choices.map((_, index) => index);
  if (choices.length <= 2) return order;
  return shuffle(order);
}

function LookupValue({ value }) {
  if (!value) return null;
  if (Array.isArray(value)) {
    return (
      <ul className="lookup-list">
        {value.map((item, index) => (
          <li key={`${String(item)}-${index}`}>{item}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    return (
      <ul className="lookup-list">
        {Object.entries(value).map(([key, item]) => (
          <li key={key}><strong>{sentenceCaseLead(key.replaceAll("_", " "))}:</strong> {item}</li>
        ))}
      </ul>
    );
  }
  return <span>{value}</span>;
}

function SourceLookupPanel({ activity, content }) {
  const title = activity.activity_type === "visual_interpretation"
    ? "Figure / Diagram Interpretation"
    : activity.activity_type === "table_lookup"
      ? "Table Lookup"
      : "Minima Rule Check";
  const sourceLabel = content.source_label || content.table_ref || content.figure_ref || content.visual_ref;
  const sourceKind = content.source_kind
    ? sentenceCaseLead(String(content.source_kind).replaceAll("_", " "))
    : title;
  const given = content.given || content.lookup_context || content.scenario_facts;
  const task = content.task || content.lookup_decision || content.decision_prompt;
  return (
    <div className="lookup-panel">
      <div>
        <div className="lookup-title">{title}</div>
        <div className="lookup-copy">
          Treat this as a source-use exercise. Use the cited table, figure, or rule to make the operational decision.
        </div>
      </div>
      {(sourceLabel || given || task) && (
        <div className="lookup-source-grid">
          <div className="lookup-source-card">
            <strong>Source</strong>
            <LookupValue value={sourceLabel ? `${sourceLabel} · ${sourceKind}` : sourceKind} />
          </div>
          {given && (
            <div className="lookup-source-card">
              <strong>Given</strong>
              <LookupValue value={given} />
            </div>
          )}
          {task && (
            <div className="lookup-source-card">
              <strong>Decision</strong>
              <LookupValue value={task} />
            </div>
          )}
        </div>
      )}
      <div className="lookup-steps">
        <div className="lookup-step"><strong>1. Condition</strong>What facts trigger the rule?</div>
        <div className="lookup-step"><strong>2. Source</strong>Which table, figure, or minimum controls?</div>
        <div className="lookup-step"><strong>3. Apply</strong>Choose the answer that follows from that source.</div>
      </div>
      <SourceCitation source={activity} compact defaultOpen={false} />
    </div>
  );
}

function ChoiceActivity({ activity, content, choiceOrder, questionTextOverride, selected, onSelect }) {
  const {
    clearance,
    question_text: storedQuestionText,
    prompt,
    situation,
  } = content;
  const questionText = questionTextOverride || storedQuestionText;
  const choices = choiceOrder.map((index) => content.choices[index]).filter(Boolean);

  return (
    <>
      {SOURCE_LOOKUP_TYPES.has(activity?.activity_type) && (
        <SourceLookupPanel activity={activity} content={content} />
      )}
      {!SOURCE_LOOKUP_TYPES.has(activity?.activity_type) && activity?.source_assets?.length > 0 && (
        <SourceCitation source={activity} compact defaultOpen={false} />
      )}
      {clearance && (
        <div className="atc-card">
          <span className="atc-tag">Clearance</span>
          {clearance}
        </div>
      )}
      {(questionText || prompt) && (
        <div className="atc-card situation prompt-card">
          <span className="atc-tag">Question</span>
          {questionText || prompt}
        </div>
      )}
      {situation && (
        <div className="atc-card situation">
          <span className="atc-tag">Situation</span>
          {situation}
        </div>
      )}
      <div className="choices">
        {choices.map((choice, i) => (
          <div
            key={`${choice.text}-${i}`}
            className={`choice${selected === i ? " choice-sel" : ""}`}
            onClick={() => onSelect(i)}
          >
            {choices.length > 2 && (
              <span style={{
                position: "absolute",
                left: 17,
                top: 13,
                zIndex: 1,
                color: selected === i ? "#e4ece2" : "#8c9c91",
                fontFamily: "var(--label)",
                fontSize: 10,
                fontWeight: 700,
              }}>
                {i + 1}
              </span>
            )}
            {choice.text}
          </div>
        ))}
      </div>
    </>
  );
}

function scoreActivity(activity, state) {
  const { activity_type: type, content } = activity;

  if (type === "phraseology_builder") {
    const wordBank = content.word_bank || [];
    const builtWords = state.built.map((idx) => wordBank[idx]).filter(Boolean);
    const targetWords = String(content.target_phrase || "").split(/\s+/).filter(Boolean);
    const correct =
      builtWords.length === targetWords.length &&
      builtWords.every((word, i) => word === targetWords[i]);
    const matches = builtWords.filter((word, i) => word === targetWords[i]).length;
    return {
      correct,
      score: targetWords.length ? (correct ? 1 : matches / targetWords.length) : 0,
      explanation: content.explanation,
    };
  }

  if (type === "spot_the_error") {
    const correct = state.spotSel === content.error_index;
    return {
      correct,
      score: correct ? 1 : 0,
      explanation: content.explanation,
    };
  }

  if (type === "sequence_steps") {
    const correct =
      JSON.stringify(state.seqOrder) === JSON.stringify(content.correct_order);
    return {
      correct,
      score: correct ? 1 : 0,
      explanation: content.explanation,
    };
  }

  if (type === "match_pairs") {
    const correct = Object.keys(state.matched).length === content.pairs.length;
    return {
      correct,
      score: correct ? 1 : 0,
      explanation:
        content.explanation || "You matched each term to its correct definition.",
    };
  }

  if (CHOICE_ACTIVITY_TYPES.has(type)) {
    const originalIndex = state.choiceOrder?.[state.choiceSel] ?? state.choiceSel;
    const correct = content.choices[originalIndex]?.is_correct === true;
    return {
      correct,
      score: correct ? 1 : 0,
      explanation: content.explanation,
    };
  }

  return { correct: false, score: 0, explanation: "" };
}

function answerSummary(activity, state) {
  if (!activity) return null;
  const { activity_type: type, content } = activity;

  if (type === "phraseology_builder") {
    const wordBank = content.word_bank || [];
    return {
      user: state.built.map((idx) => wordBank[idx]).filter(Boolean).join(" "),
      correct: content.target_phrase || "",
    };
  }

  if (type === "spot_the_error") {
    return {
      user: state.spotSel === null ? "" : content.tokens?.[state.spotSel],
      correct: content.tokens?.[content.error_index],
    };
  }

  if (type === "sequence_steps") {
    const stepMap = Object.fromEntries((content.steps || []).map((step) => [step.id, step.text]));
    return {
      user: (state.seqOrder || []).map((id, index) => `${index + 1}. ${stepMap[id] || id}`).join(" "),
      correct: (content.correct_order || []).map((id, index) => `${index + 1}. ${stepMap[id] || id}`).join(" "),
    };
  }

  if (type === "match_pairs") {
    return {
      user: `${Object.keys(state.matched || {}).length} of ${(content.pairs || []).length} pairs matched`,
      correct: "All listed terms matched to their definitions.",
    };
  }

  if (CHOICE_ACTIVITY_TYPES.has(type)) {
    const originalIndex = state.choiceOrder?.[state.choiceSel] ?? state.choiceSel;
    return {
      user: content.choices?.[originalIndex]?.text || "",
      correct: content.choices?.find((choice) => choice.is_correct === true)?.text || "",
    };
  }

  return null;
}

function ActivityContext({ activity, idx, total, results }) {
  const help = TYPE_HELP[activity.activity_type] || "Apply the paragraph to the prompt.";
  if (!ALWAYS_SHOW_FOCUS_TYPES.has(activity.activity_type) && !SOURCE_LOOKUP_TYPES.has(activity.activity_type)) {
    return null;
  }
  const visibleDots = total <= 12
    ? Array.from({ length: total }, (_, index) => index)
    : Array.from({ length: 12 }, (_, index) => Math.floor(index * total / 12));

  return (
    <div className="lp-context">
      <div>
        <div className="lp-context-title">What this tests</div>
        <div className="lp-context-copy">{help}</div>
      </div>
      <div className="lp-context-meter" title={`${idx + 1} of ${total}`}>
        {visibleDots.map((position, dotIndex) => {
          const result = results[position];
          const isDone = position < idx;
          const isCurrent = position === idx || (total > 12 && dotIndex === Math.floor(idx / total * 12));
          return (
            <span
              key={`${position}-${dotIndex}`}
              className={`lp-dot${isDone ? " done" : ""}${result?.correct ? " correct" : ""}${result && !result.correct ? " wrong" : ""}${isCurrent ? " current" : ""}`}
            />
          );
        })}
      </div>
    </div>
  );
}

export default function LessonPlayer({ session = [], sessionMeta, onBack, onComplete, onRemediate }) {
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState("answering");
  const [feedback, setFeedback] = useState(null);
  const [results, setResults] = useState([]);
  const [animKey, setAnimKey] = useState(0);
  const [built, setBuilt] = useState([]);
  const [spotSel, setSpotSel] = useState(null);
  const [seqOrder, setSeqOrder] = useState([]);
  const [seqSel, setSeqSel] = useState(null);
  const [matchSel, setMatchSel] = useState(null);
  const [matched, setMatched] = useState({});
  const [shuffledDefs, setShuffledDefs] = useState([]);
  const [choiceOrder, setChoiceOrder] = useState([]);
  const [wrongFlash, setWrongFlash] = useState(null);
  const [choiceSel, setChoiceSel] = useState(null);
  const [itemFlags, setItemFlags] = useState(loadItemFlags);

  const activity = session[idx];
  const progress = session.length ? (idx / session.length) * 100 : 0;

  useEffect(() => {
    setIdx(0);
    setPhase("answering");
    setFeedback(null);
    setResults([]);
  }, [session]);

  useEffect(() => {
    const current = session[idx];
    if (!current) return;

    setBuilt([]);
    setSpotSel(null);
    setSeqOrder(current.content.steps ? current.content.steps.map((step) => step.id) : []);
    setSeqSel(null);
    setMatchSel(null);
    setMatched({});
    setShuffledDefs(
      current.content.pairs
        ? shuffle(current.content.pairs.map((pair) => pair.definition))
        : []
    );
    setChoiceOrder(
      CHOICE_ACTIVITY_TYPES.has(current.activity_type)
        ? buildChoiceOrder(current.content.choices || [])
        : []
    );
    setWrongFlash(null);
    setChoiceSel(null);
    setFeedback(null);
    setPhase("answering");
    setAnimKey((value) => value + 1);
  }, [idx, session]);

  const canSubmit = (() => {
    if (!activity || phase !== "answering") return false;

    if (activity.activity_type === "phraseology_builder") {
      return built.length > 0;
    }
    if (activity.activity_type === "spot_the_error") {
      return spotSel !== null;
    }
    if (activity.activity_type === "sequence_steps") {
      return true;
    }
    if (activity.activity_type === "match_pairs") {
      return Object.keys(matched).length === activity.content.pairs.length;
    }
    if (CHOICE_ACTIVITY_TYPES.has(activity.activity_type)) {
      return choiceSel !== null;
    }
    return false;
  })();

  const correctSoFar = results.filter((result) => result.correct).length + (feedback?.correct ? 1 : 0);
  const answeredCount = results.length + (feedback?.result ? 1 : 0);
  const remainingCount = Math.max(0, session.length - answeredCount);

  function showFeedback(stateOverride, options = {}) {
    if (!activity) return;

    const state = stateOverride || { built, spotSel, seqOrder, matched, choiceSel, choiceOrder };
    const scored = scoreActivity(activity, state);
    const correct = options.forceIncorrect ? false : scored.correct;
    const score = options.forceIncorrect ? 0 : scored.score;
    const explanation = scored.explanation;
    const answers = options.userAnswerOverride
      ? { ...(answerSummary(activity, state) || {}), user: options.userAnswerOverride }
      : answerSummary(activity, state);
    const result = {
      activityId: activity.id,
      paraId: activity.para_id,
      paraTitle: activity.para_title,
      activityType: activity.activity_type,
      activityLabel: TYPE_LABELS[activity.activity_type] || activity.activity_type,
      concepts: activity.concepts || [],
      source_url: activity.source_url,
      source_heading: activity.source_heading,
      source_locator: activity.source_locator,
      source_excerpt: activity.source_excerpt,
      score,
      correct,
    };

    setFeedback({ correct, explanation, answers, result });
    setPhase("feedback");
  }

  function handleSubmit() {
    showFeedback();
  }

  function handleGiveUp() {
    showFeedback(undefined, {
      forceIncorrect: true,
      userAnswerOverride: "I don't know",
    });
  }

  function handleContinue() {
    if (!feedback?.result) return;

    const nextResults = [...results, feedback.result];
    if (idx + 1 >= session.length) {
      setResults(nextResults);
      if (onComplete) onComplete(nextResults);
      return;
    }

    setResults(nextResults);
    setIdx((value) => value + 1);
  }

  function handleRemediate() {
    if (!feedback?.result || !activity?.concepts?.length || !onRemediate) return;
    setResults((current) => [...current, feedback.result]);
    onRemediate(activity.concepts.map((concept) => concept.id));
  }

  function handleTermTap(term) {
    setMatchSel((selected) => (selected === term ? null : term));
  }

  function handleDefTap(definition) {
    if (!matchSel || !activity) return;

    const pair = activity.content.pairs.find((item) => item.term === matchSel);
    if (pair && pair.definition === definition) {
      setMatched((current) => ({ ...current, [matchSel]: definition }));
      setMatchSel(null);
      return;
    }

    setWrongFlash(definition);
    setTimeout(() => {
      setWrongFlash(null);
      setMatchSel(null);
    }, 500);
  }

  function handleSeqTap(i) {
    if (seqSel === null) {
      setSeqSel(i);
      return;
    }
    if (seqSel === i) {
      setSeqSel(null);
      return;
    }

    const next = [...seqOrder];
    [next[seqSel], next[i]] = [next[i], next[seqSel]];
    setSeqOrder(next);
    setSeqSel(null);
  }

  function handleBack() {
    const hasProgress = results.length > 0 || Boolean(feedback?.result);
    if (!hasProgress) {
      onBack();
      return;
    }
    const shouldLeave = window.confirm("Leave this lesson? Your current session results will not be saved.");
    if (shouldLeave) onBack();
  }

  function handleEndAndSave() {
    const savedResults = feedback?.result
      ? [...results, feedback.result]
      : [...results];
    if (!savedResults.length) return;
    const shouldEnd = window.confirm("End this lesson and save completed answers?");
    if (shouldEnd && onComplete) onComplete(savedResults);
  }

  function toggleFlagItem() {
    if (!activity?.id) return;
    setItemFlags((current) => {
      const next = { ...current };
      if (next[activity.id]) {
        delete next[activity.id];
      } else {
        const content = activity.content || {};
        next[activity.id] = {
          activityId: activity.id,
          paraId: activity.para_id,
          paraTitle: activity.para_title,
          activityType: activity.activity_type,
          activityLabel: TYPE_LABELS[activity.activity_type] || activity.activity_type,
          itemText: content.question_text || content.prompt || content.instruction || content.clearance || content.situation || content.target_phrase || null,
          userAnswer: feedback?.answers?.user || null,
          correctAnswer: feedback?.answers?.correct || null,
          explanation: feedback?.explanation || content.explanation || null,
          sourceUrl: activity.source_url || null,
          flaggedAt: new Date().toISOString(),
        };
      }
      saveItemFlags(next);
      return next;
    });
  }

  useEffect(() => {
    function handleKeyDown(event) {
      const tag = event.target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;

      if (event.key === "Enter") {
        if (phase === "answering" && canSubmit) {
          event.preventDefault();
          handleSubmit();
        } else if (phase === "feedback") {
          event.preventDefault();
          handleContinue();
        }
        return;
      }

      if (phase === "answering" && event.key.toLowerCase() === "i") {
        event.preventDefault();
        handleGiveUp();
        return;
      }

      if (
        phase === "answering"
        && CHOICE_ACTIVITY_TYPES.has(activity?.activity_type)
        && /^[1-9]$/.test(event.key)
      ) {
        const index = Number(event.key) - 1;
        if (index >= 0 && index < choiceOrder.length) {
          event.preventDefault();
          setChoiceSel(index);
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activity, canSubmit, choiceOrder.length, phase, feedback, results]);

  if (!session.length) {
    return (
      <>
        <style>{CSS}</style>
        <div className="lp">
          <div className="lp-empty">
            <div className="lp-empty-title">No Activities</div>
            <div className="lp-empty-copy">
              This section does not have a usable lesson session yet.
            </div>
            <button className="btn btn-continue" onClick={onBack}>
              Back to map
            </button>
          </div>
        </div>
      </>
    );
  }

  if (!activity) return null;

  return (
    <>
      <style>{CSS}</style>
      <div className="lp">
        <div className="lp-topbar">
          <button className="lp-back" onClick={handleBack} title="Leave lesson">‹</button>
          <span className="lp-count">{idx + 1} / {session.length}</span>
          <div
            style={{
              flex: 1,
              height: 5,
              background: "var(--card2)",
              borderRadius: 3,
              overflow: "hidden",
              margin: "0 4px",
            }}
          >
            <div
              style={{
                height: "100%",
                background: "var(--amber)",
                width: `${progress}%`,
                borderRadius: 3,
                transition: "width .5s ease",
              }}
            />
          </div>
          {answeredCount > 0 && (
            <span className="lp-progress-meta">
              <strong>{correctSoFar}</strong> correct · {remainingCount} left
            </span>
          )}
          {answeredCount > 0 && (
            <button className="lp-end-save" onClick={handleEndAndSave}>
              End & Save
            </button>
          )}
        </div>
        <div className="lp-sub">
          <span className="lp-badge">{TYPE_LABELS[activity.activity_type] || activity.activity_type}</span>
          <span className="lp-pararef">
            § {activity.para_id} · {activity.para_title}
            {activity.source_url && (
              <>
                {" · "}
                <a
                  className="lp-source-link"
                  href={activity.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  FAA Source ↗
                </a>
              </>
            )}
          </span>
        </div>
        <div className="lp-main" key={animKey}>
          <div className="slide-in" style={{ display: "contents" }}>
            {idx === 0 && sessionMeta?.reason && sessionMeta?.mode !== "Paragraph" && (
              <div className="lp-session-note">
                <strong>{sessionMeta.mode || "Practice brief"}</strong>
                {sessionMeta.reason}
              </div>
            )}
            <ActivityContext activity={activity} idx={idx} total={session.length} results={results} />
            <p className="lp-instruction">{displayInstruction(activity)}</p>
            {activity.activity_type === "phraseology_builder" && (
              <PhraseologyBuilder
                content={activity.content}
                built={built}
                onBuild={(i) => setBuilt((current) => [...current, i])}
                onRemove={(pos) => setBuilt((current) => current.filter((_, j) => j !== pos))}
                onClear={() => setBuilt([])}
              />
            )}
            {activity.activity_type === "spot_the_error" && (
              <SpotTheError
                content={activity.content}
                selected={spotSel}
                onSelect={setSpotSel}
              />
            )}
            {activity.activity_type === "sequence_steps" && (
              <SequenceSteps
                content={activity.content}
                order={seqOrder}
                selectedIdx={seqSel}
                onTap={handleSeqTap}
              />
            )}
            {activity.activity_type === "match_pairs" && (
              <MatchPairs
                content={activity.content}
                shuffledDefs={shuffledDefs}
                matchSel={matchSel}
                matched={matched}
                wrongFlash={wrongFlash}
                onTermTap={handleTermTap}
                onDefTap={handleDefTap}
              />
            )}
            {CHOICE_ACTIVITY_TYPES.has(activity.activity_type) && (
              <ChoiceActivity
                activity={activity}
                content={activity.content}
                choiceOrder={choiceOrder}
                questionTextOverride={displayQuestionText(activity)}
                selected={choiceSel}
                onSelect={setChoiceSel}
              />
            )}
          </div>
        </div>
        {phase === "answering" && (
          <div className="lp-footer">
            <div className="lp-actions">
              <button className="btn btn-check" disabled={!canSubmit} onClick={handleSubmit}>
                {activity.activity_type === "match_pairs"
                  ? (canSubmit ? "Check" : `Match all ${activity.content.pairs.length} pairs`)
                  : "Check"}
              </button>
              <button className="btn btn-giveup" onClick={handleGiveUp}>
                I don't know
              </button>
            </div>
            <div className="lp-shortcuts">
              Press Enter to check. Press I for I don't know. For multiple choice, press 1-{Math.max(1, choiceOrder.length || 1)} to select.
            </div>
          </div>
        )}
        {phase === "feedback" && feedback && (
          <>
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "rgba(5,7,6,.52)",
                zIndex: 9,
              }}
            />
            <div className={`feedback ${feedback.correct ? "fb-correct" : "fb-wrong"}`}>
              <div className="fb-title">{feedback.correct ? "Correct" : "Not quite"}</div>
              {feedback.answers?.correct && (
                <div className="fb-answer-grid">
                  <div className={`fb-answer${feedback.correct ? "" : " user-wrong"}`}>
                    <div className="fb-answer-title">Your answer</div>
                    <div className="fb-answer-text">{feedback.answers.user || "No answer"}</div>
                  </div>
                  <div className="fb-answer correct">
                    <div className="fb-answer-title">Rule answer</div>
                    <div className="fb-answer-text">{feedback.answers.correct}</div>
                  </div>
                </div>
              )}
              {feedback.explanation && (
                <>
                  <div className="fb-label">Operating principle</div>
                  <div className="fb-explain">{feedback.explanation}</div>
                </>
              )}
              {!feedback.correct && activity.concepts?.length > 0 && (
                <div className="fb-concepts">
                  {activity.concepts.slice(0, 3).map((concept) => (
                    <span className="fb-concept" key={concept.id}>{concept.label}</span>
                  ))}
                </div>
              )}
              <SourceCitation source={activity} compact style="feedback" />
              {!feedback.correct && activity.concepts?.length > 0 && onRemediate && (
                <button
                  className="btn btn-remediate"
                  onClick={handleRemediate}
                >
                  Transfer this concept
                </button>
              )}
              <button
                className={`btn btn-flag${itemFlags[activity.id] ? " active" : ""}`}
                onClick={toggleFlagItem}
              >
                {itemFlags[activity.id] ? "Item flagged" : "Flag item for review"}
              </button>
              <button className="btn btn-continue" onClick={handleContinue}>
                {idx + 1 >= session.length ? "Finish and review" : "Next item"}
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
