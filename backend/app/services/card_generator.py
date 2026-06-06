"""
Local flashcard generator.

This keeps the backend card-generation path usable without external API calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .local_generation import (
    joined_blocks,
    meaningful_body_sentences,
    normalise_ws,
    phraseology_lines_from_blocks,
    sentence_split,
)

log = logging.getLogger(__name__)


@dataclass
class GeneratedCard:
    front: str
    back: str
    card_type: str
    source_block_type: str
    generation_source: str = "local_auto"
    is_verified: bool = False


async def generate_cards_for_paragraph(
    para_id: str,
    para_title: str,
    blocks: list[dict],
    max_cards: int = 5,
) -> list[GeneratedCard]:
    """
    Generate flashcards for one paragraph without external API calls.
    """
    if not blocks:
        log.warning("No content blocks for %s, skipping card generation", para_id)
        return []

    cards: list[GeneratedCard] = []
    seen_fronts: set[str] = set()

    def add_card(front: str, back: str, card_type: str, source_block_type: str) -> None:
        if len(cards) >= max_cards:
            return
        front = normalise_ws(front)
        back = normalise_ws(back)
        if not front or not back or front in seen_fronts:
            return
        seen_fronts.add(front)
        cards.append(
            GeneratedCard(
                front=front,
                back=back[:320],
                card_type=card_type,
                source_block_type=source_block_type,
            )
        )

    for line in phraseology_lines_from_blocks(blocks)[:2]:
        add_card(
            front=f"State the phraseology for {para_title}.",
            back=line,
            card_type="phraseology",
            source_block_type="phraseology",
        )

    body_sentences = meaningful_body_sentences(blocks)
    if body_sentences:
        add_card(
            front=f"§{para_id} ({para_title}): What is the rule?",
            back=body_sentences[0],
            card_type="definition",
            source_block_type="body",
        )

    if len(body_sentences) > 1:
        add_card(
            front=f"When does {para_title.lower()} apply?",
            back=body_sentences[1],
            card_type="procedure",
            source_block_type="body",
        )

    note_text = joined_blocks(blocks, "note")
    note_sentences = sentence_split(note_text)
    if note_sentences:
        add_card(
            front=note_sentences[0],
            back=f"TRUE — {note_sentences[0]}",
            card_type="true_false",
            source_block_type="note",
        )

    example_text = joined_blocks(blocks, "example")
    example_sentences = sentence_split(example_text)
    if example_sentences:
        add_card(
            front=f"How would you apply {para_title} in practice?",
            back=example_sentences[0],
            card_type="application",
            source_block_type="example",
        )

    log.info("Generated %s local cards for %s", len(cards), para_id)
    return cards


async def generate_cards_for_chapter(
    paragraphs: list[dict],
    on_progress: Optional[callable] = None,
    skip_para_ids: Optional[set[str]] = None,
) -> dict[str, list[GeneratedCard]]:
    """
    Generate cards for all paragraphs in a chapter.
    """
    import asyncio

    skip = skip_para_ids or set()
    results: dict[str, list[GeneratedCard]] = {}
    total = len(paragraphs)

    for para in paragraphs:
        para_id = para.get("para_id", "")
        if para_id in skip:
            continue

        cards = await generate_cards_for_paragraph(
            para_id=para_id,
            para_title=para.get("title", ""),
            blocks=para.get("blocks", []),
        )
        results[para_id] = cards

        if on_progress:
            on_progress(para_id, len(cards), total)

        await asyncio.sleep(0)

    return results
