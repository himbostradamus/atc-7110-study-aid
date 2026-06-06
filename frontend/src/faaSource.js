export const FAA_7110_PDF_URL =
  "https://www.faa.gov/documentLibrary/media/Order/7110.65BB_Bsc_w_Chg_1_and_2_dtd_1-22-26_Final.pdf";

export const FAA_JO_7360_1J_PDF_URL =
  "https://www.faa.gov/documentLibrary/media/Order/2024-04-29_FAA_Order_JO_7360.1J_Aircraft_Type_Designators--post.pdf";

const SOURCE_BLOCK_PRIORITY = [
  "phraseology",
  "example",
  "body",
  "note",
  "exception",
  "interpretation",
  "reference",
];

function collapseWhitespace(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

function clipText(value, max = 220) {
  const normalized = collapseWhitespace(value);
  if (!normalized) return null;
  if (normalized.length <= max) return normalized;
  return `${normalized.slice(0, max - 1).trimEnd()}…`;
}

function buildSourceBlocks(blocks) {
  if (!Array.isArray(blocks)) return [];
  return blocks
    .filter((block) => collapseWhitespace(block?.content))
    .slice(0, 8)
    .map((block) => ({
      block_type: block.block_type || "body",
      content: clipText(block.content, 720),
    }));
}

function pickSourceBlock(blocks) {
  if (!Array.isArray(blocks) || !blocks.length) return null;
  for (const blockType of SOURCE_BLOCK_PRIORITY) {
    const hit = blocks.find((block) => block?.block_type === blockType && collapseWhitespace(block?.content));
    if (hit) return hit;
  }
  return blocks.find((block) => collapseWhitespace(block?.content)) || null;
}

export function buildFaaSourceRef(paraId, page, options = {}) {
  const numericPage = Number(page || 0);
  if (!paraId) return null;

  const title = collapseWhitespace(options.title);
  const heading = title ? `${paraId}. ${title}` : `${paraId}`;
  const sourceBlock = pickSourceBlock(options.blocks);
  const sourceExcerpt = clipText(sourceBlock?.content || "");
  const sourceBlockType = sourceBlock?.block_type || null;

  return {
    source_label: numericPage
      ? `FAA JO 7110.65BB · ${paraId} · PDF page ${numericPage}`
      : `FAA JO 7110.65BB · ${paraId}`,
    source_url: numericPage
      ? `${FAA_7110_PDF_URL}#page=${numericPage}`
      : FAA_7110_PDF_URL,
    source_page: numericPage || null,
    source_heading: heading,
    source_locator: numericPage
      ? `Look for ${heading} on PDF page ${numericPage}.`
      : `Look for ${heading} in FAA JO 7110.65BB.`,
    source_excerpt: sourceExcerpt,
    source_blocks: buildSourceBlocks(options.blocks),
    source_block_type: sourceBlockType,
  };
}

export function buildJo7360SourceRef() {
  return {
    source_label: "FAA JO 7360.1J · Appendix A",
    source_url: `${FAA_JO_7360_1J_PDF_URL}#page=11`,
    source_page: 11,
    source_heading: "JO 7360.1J Appendix A. Aircraft Type Designators",
    source_locator: "Use Appendix A in FAA Order JO 7360.1J for aircraft type designators, wake/CWT categories, and same-runway-separation category data.",
    source_excerpt: "Aircraft recognition cards are JO 7360.1J-derived supporting material, not JO 7110.65 paragraph content.",
    source_blocks: [],
    source_block_type: "appendix",
  };
}
