import { useEffect, useState } from "react";

const SOURCE_CITATION_CSS = `
.source-citation,.source-citation *,.source-drawer,.source-drawer *{font-family:'Share Tech Mono',ui-monospace,monospace!important;border-radius:2px!important;box-shadow:none!important}
.source-drawer-panel{background:#11120e!important;color:#f1ead7!important;border-color:rgba(226,219,193,.22)!important}
.source-asset-table{overflow:auto;max-width:100%;border:1px solid rgba(226,219,193,.16);background:rgba(241,234,215,.03);padding:8px}
.source-asset-table table{width:max-content;min-width:100%;border-collapse:collapse;color:#f1ead7;font-size:11px;line-height:1.35}
.source-asset-table td,.source-asset-table th{border:1px solid rgba(226,219,193,.28);padding:5px 7px;vertical-align:top}
.source-asset-table p{margin:0 0 4px}
.source-asset-image{display:block;max-width:100%;height:auto;border:1px solid rgba(226,219,193,.18);background:#f1ead7}
@media (max-width: 520px){
  .source-citation-actions button,.source-citation-actions a{min-height:44px;touch-action:manipulation}
  .source-drawer{justify-content:stretch!important}
  .source-drawer-panel{
    width:100vw!important;
    padding:max(16px, env(safe-area-inset-top)) 14px max(18px, env(safe-area-inset-bottom))!important;
    border-left:none!important;
  }
  .source-drawer-header{gap:10px!important}
  .source-drawer-close{min-height:44px!important}
  .source-drawer-actions{display:grid!important;grid-template-columns:1fr!important}
  .source-drawer-actions a,.source-drawer-actions button{min-height:44px!important;width:100%;justify-content:center}
}
`;

function copySourceUrl(url) {
  if (!url) return;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(url).catch(() => {});
  }
}

function sourceBlockLabel(value) {
  return String(value || "body")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function SourceCitation({ source, compact = false, style = "panel", defaultOpen = null }) {
  const sourceBlocks = Array.isArray(source?.source_blocks) ? source.source_blocks : [];
  const sourceAssets = Array.isArray(source?.source_assets) ? source.source_assets : [];
  const hasContext = Boolean(source?.source_heading || source?.source_locator || source?.source_excerpt || sourceBlocks.length || sourceAssets.length);
  const [open, setOpen] = useState(defaultOpen ?? !compact);
  const [drawerOpen, setDrawerOpen] = useState(false);
  useEffect(() => {
    if (!drawerOpen) return undefined;
    function handleKeyDown(event) {
      if (event.key === "Escape") setDrawerOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [drawerOpen]);

  if (!source?.source_url) return null;
  const palette = style === "feedback"
    ? {
        border: "rgba(219,229,216,.18)",
        bg: "rgba(7,10,9,.36)",
        heading: "#e0a30a",
        text: "#8c9c91",
        link: "#e0a30a",
      }
    : {
        border: "rgba(219,229,216,.13)",
        bg: "rgba(13,17,15,.92)",
        heading: "#e0a30a",
        text: "#8c9c91",
        link: "#e0a30a",
      };
  const sourceText = `${source.source_label || ""} ${source.source_url || ""}`;
  const isFaaSource = /\bfaa\.gov\b/i.test(sourceText) || /\bFAA\s+JO\b/i.test(sourceText);
  const sourceKindLabel = isFaaSource ? "FAA Source Check" : "Source Check";
  const sourceDrawerLabel = isFaaSource ? "FAA source drawer" : "source drawer";
  const openSourceLabel = isFaaSource ? "Open Official PDF" : "Open Source";

  return (
    <div
      className="source-citation"
      style={{
        marginTop: compact ? 8 : 10,
        padding: compact ? "8px 10px" : "10px 11px",
        borderRadius: 8,
        border: `1px solid ${palette.border}`,
        background: palette.bg,
      }}
    >
      <style>{SOURCE_CITATION_CSS}</style>
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          marginBottom: source.source_heading || source.source_locator || source.source_excerpt ? 6 : 0,
        }}
      >
        <div
          style={{
            fontFamily: "'Barlow Condensed', sans-serif",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: ".08em",
            textTransform: "uppercase",
            color: palette.heading,
          }}
        >
          {style === "feedback"
            ? (isFaaSource ? "Verify Against FAA Source" : "Verify Against Source")
            : (source.source_label || (isFaaSource ? "FAA Source" : "Source"))}
        </div>
        <div className="source-citation-actions" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {hasContext && (
            <button
              onClick={() => setDrawerOpen(true)}
              style={{
                background: "none",
                border: "none",
                color: palette.link,
                cursor: "pointer",
                fontFamily: "'Barlow Condensed', sans-serif",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: ".05em",
                textTransform: "uppercase",
                padding: 0,
              }}
            >
              Source Drawer
            </button>
          )}
          {hasContext && (
            <button
              onClick={() => setOpen((value) => !value)}
              style={{
                background: "none",
                border: "none",
                color: palette.text,
                cursor: "pointer",
                fontFamily: "'Barlow Condensed', sans-serif",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: ".05em",
                textTransform: "uppercase",
                padding: 0,
              }}
            >
              {open ? "Hide Snippet" : "Show Snippet"}
            </button>
          )}
          <button
            onClick={() => copySourceUrl(source.source_url)}
            style={{
              background: "none",
              border: "none",
              color: palette.text,
              cursor: "pointer",
              fontFamily: "'Barlow Condensed', sans-serif",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: ".05em",
              textTransform: "uppercase",
              padding: 0,
            }}
          >
            Copy Link
          </button>
          <a
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            style={{
              color: palette.link,
              textDecoration: "none",
              fontFamily: "'Barlow Condensed', sans-serif",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: ".05em",
              textTransform: "uppercase",
            }}
          >
            {style === "feedback" ? "Check Source ↗" : (isFaaSource ? "Open PDF ↗" : "Open Source ↗")}
          </a>
        </div>
      </div>
      {style === "feedback" && (
        <div style={{ fontSize: 11, lineHeight: 1.5, color: palette.text, marginBottom: 5 }}>
          Official sources, facility directives, LOAs, and instructor or supervisor guidance control if generated material is thin, ambiguous, or context-dependent.
        </div>
      )}
      {hasContext && !open && (
        <div style={{ fontSize: 11, lineHeight: 1.55, color: palette.text }}>
          {source.source_heading || source.source_locator || "Source context available."}
        </div>
      )}
      {open && source.source_heading && (
        <div style={{ fontSize: 12, lineHeight: 1.55, color: "#e4ece2", fontWeight: 600 }}>
          {source.source_heading}
        </div>
      )}
      {open && source.source_locator && (
        <div style={{ fontSize: 11, lineHeight: 1.55, color: palette.text, marginTop: 4 }}>
          {source.source_locator}
        </div>
      )}
      {open && source.source_excerpt && (
        <div style={{
          fontSize: 11,
          lineHeight: 1.6,
          color: palette.text,
          marginTop: 6,
          maxHeight: compact ? 110 : 180,
          overflow: "auto",
          paddingRight: 4,
        }}>
          {source.source_excerpt}
        </div>
      )}
      {open && sourceAssets.length > 0 && (
        <div style={{ fontSize: 11, lineHeight: 1.55, color: palette.text, marginTop: 7 }}>
          {sourceAssets.length} official FAA {sourceAssets.length === 1 ? "asset" : "assets"} available in the source drawer.
        </div>
      )}
      {drawerOpen && (
        <div
          className="source-drawer"
          role="dialog"
          aria-modal="true"
          aria-label={sourceDrawerLabel}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 2000,
            display: "flex",
            justifyContent: "flex-end",
            background: "rgba(5,7,6,.68)",
          }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDrawerOpen(false);
          }}
        >
          <div
            className="source-drawer-panel"
            style={{
              width: "min(560px, 94vw)",
              height: "100%",
              background: "rgba(13,17,15,.92)",
              borderLeft: "1px solid rgba(219,229,216,.22)",
              boxShadow: "-18px 0 60px rgba(0,0,0,.42)",
              padding: 18,
              overflow: "auto",
            }}
          >
            <div className="source-drawer-header" style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 14,
              borderBottom: "1px solid rgba(219,229,216,.13)",
              paddingBottom: 14,
              marginBottom: 14,
            }}>
              <div>
                <div style={{
                  fontFamily: "'Barlow Condensed', sans-serif",
                  color: "#e0a30a",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: ".1em",
                  textTransform: "uppercase",
                }}>
                  {sourceKindLabel}
                </div>
                <div style={{
                  color: "#e4ece2",
                  fontFamily: "'Barlow Condensed', sans-serif",
                  fontSize: 22,
                  fontWeight: 700,
                  lineHeight: 1.15,
                  marginTop: 4,
                }}>
                  {source.source_heading || source.source_label || "FAA JO 7110.65BB"}
                </div>
                {source.source_label && (
                  <div style={{ color: "#8c9c91", fontSize: 12, marginTop: 6, lineHeight: 1.5 }}>
                    {source.source_label}
                  </div>
                )}
              </div>
              <button
                className="source-drawer-close"
                onClick={() => setDrawerOpen(false)}
                style={{
                  height: 34,
                  padding: "0 11px",
                  borderRadius: 8,
                  border: "1px solid rgba(219,229,216,.13)",
                  background: "rgba(17,22,20,.92)",
                  color: "#e4ece2",
                  cursor: "pointer",
                  fontFamily: "'Barlow Condensed', sans-serif",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: ".07em",
                  textTransform: "uppercase",
                }}
              >
                Close
              </button>
            </div>

            <div style={{
              border: "1px solid rgba(224,163,10,.25)",
              background: "rgba(224,163,10,.08)",
              borderRadius: 10,
              padding: "11px 12px",
              color: "#e4ece2",
              fontSize: 12,
              lineHeight: 1.55,
              marginBottom: 12,
            }}>
              <strong style={{ color: "#e0a30a" }}>How to verify:</strong>{" "}
              {source.source_locator || (isFaaSource
                ? "Open the FAA PDF and confirm the paragraph text against the cited section."
                : "Open the source page and confirm the material against the cited metadata.")}
            </div>

            {source.source_excerpt && (
              <div style={{
                border: "1px solid rgba(219,229,216,.13)",
                background: "rgba(17,22,20,.92)",
                borderRadius: 10,
                padding: "12px 13px",
                marginBottom: 12,
              }}>
                <div style={{
                  fontFamily: "'Barlow Condensed', sans-serif",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                  color: "#7aa7d9",
                  marginBottom: 7,
                }}>
                  Primary Excerpt
                </div>
                <div style={{ color: "#e4ece2", fontSize: 12, lineHeight: 1.65 }}>
                  {source.source_excerpt}
                </div>
              </div>
            )}

            {sourceBlocks.length > 0 && (
              <div style={{ display: "grid", gap: 8, marginBottom: 14 }}>
                {sourceBlocks.map((block, index) => (
                  <div
                    key={`${block.block_type}-${index}`}
                    style={{
                      border: "1px solid rgba(219,229,216,.13)",
                      background: "rgba(17,22,20,.92)",
                      borderRadius: 10,
                      padding: "11px 12px",
                    }}
                  >
                    <div style={{
                      fontFamily: "'Barlow Condensed', sans-serif",
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: ".08em",
                      textTransform: "uppercase",
                      color: "#8c9c91",
                      marginBottom: 6,
                    }}>
                      {sourceBlockLabel(block.block_type)}
                    </div>
                    <div style={{ color: "#e4ece2", fontSize: 12, lineHeight: 1.6 }}>
                      {block.content}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {sourceAssets.length > 0 && (
              <div style={{ display: "grid", gap: 10, marginBottom: 14 }}>
                <div style={{
                  fontFamily: "'Barlow Condensed', sans-serif",
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                  color: "#e0a30a",
                }}>
                  Official FAA Tables / Figures
                </div>
                {sourceAssets.map((asset) => (
                  <div
                    key={asset.id || `${asset.label}-${asset.source_url}`}
                    style={{
                      border: "1px solid rgba(219,229,216,.13)",
                      background: "rgba(17,22,20,.92)",
                      borderRadius: 10,
                      padding: "11px 12px",
                    }}
                  >
                    <div style={{
                      display: "flex",
                      alignItems: "baseline",
                      justifyContent: "space-between",
                      gap: 10,
                      flexWrap: "wrap",
                      marginBottom: 8,
                    }}>
                      <div>
                        <div style={{
                          fontFamily: "'Barlow Condensed', sans-serif",
                          fontSize: 10,
                          fontWeight: 700,
                          letterSpacing: ".08em",
                          textTransform: "uppercase",
                          color: "#7aa7d9",
                        }}>
                          {asset.label || asset.asset_type}
                        </div>
                        {asset.title && (
                          <div style={{ color: "#e4ece2", fontSize: 13, lineHeight: 1.35, marginTop: 3 }}>
                            {asset.title}
                          </div>
                        )}
                      </div>
                      {asset.source_url && (
                        <a
                          href={asset.source_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            color: "#e0a30a",
                            textDecoration: "none",
                            fontFamily: "'Barlow Condensed', sans-serif",
                            fontSize: 11,
                            fontWeight: 700,
                            letterSpacing: ".05em",
                            textTransform: "uppercase",
                          }}
                        >
                          Open Asset ↗
                        </a>
                      )}
                    </div>
                    {asset.image_url ? (
                      <img
                        className="source-asset-image"
                        src={asset.image_url}
                        alt={asset.alt_text || asset.title || asset.label || "FAA figure"}
                        loading="lazy"
                      />
                    ) : asset.html ? (
                      <div
                        className="source-asset-table"
                        dangerouslySetInnerHTML={{ __html: asset.html }}
                      />
                    ) : (
                      <div style={{ color: "#8c9c91", fontSize: 12, lineHeight: 1.55 }}>
                        Asset metadata is available, but no renderable table or image was captured.
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="source-drawer-actions" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <a
                href={source.source_url}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: 38,
                  padding: "0 14px",
                  borderRadius: 8,
                  background: "#e0a30a",
                  color: "#000",
                  textDecoration: "none",
                  fontFamily: "'Barlow Condensed', sans-serif",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: ".07em",
                  textTransform: "uppercase",
                }}
              >
                {openSourceLabel}
              </a>
              <button
                onClick={() => copySourceUrl(source.source_url)}
                style={{
                  height: 38,
                  padding: "0 14px",
                  borderRadius: 8,
                  border: "1px solid rgba(219,229,216,.13)",
                  background: "rgba(17,22,20,.92)",
                  color: "#e4ece2",
                  cursor: "pointer",
                  fontFamily: "'Barlow Condensed', sans-serif",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: ".07em",
                  textTransform: "uppercase",
                }}
              >
                Copy Link
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
