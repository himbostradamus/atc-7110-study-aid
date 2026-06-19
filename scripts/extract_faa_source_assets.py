#!/usr/bin/env python3
"""Extract exact FAA JO 7110.65 tables and figures from the official HTML.

The app should not redraw or paraphrase source visuals when the FAA already
publishes the table/figure. This script captures the official HTML table markup
and figure image URLs, attaches each asset to the active 7110 paragraph, and
upserts the result into curriculum.db for source-drawer rendering.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "frontend" / "public" / "curriculum.db"
DEFAULT_OUT = ROOT / "backend" / "app" / "data" / "faa_7110_65bb_source_assets.json"
FAA_HTML_BASE = "https://www.faa.gov/air_traffic/publications/atpubs/atc_html/"
FAA_PDF_URL = "https://www.faa.gov/documentLibrary/media/Order/7110.65BB_Bsc_w_Chg_1_and_2_dtd_1-22-26_Final.pdf"
USER_AGENT = "atc-7110-study-aid-source-asset-extractor/1.0"

PARA_ID_RE = re.compile(r"^\d{1,2}-\d{1,2}-\d{1,2}$")
TABLE_LABEL_RE = re.compile(r"\bTBL\s+\d{1,2}-\d{1,2}-\d{1,2}\b", re.I)
FIGURE_LABEL_RE = re.compile(r"\bFIG\s+\d{1,2}-\d{1,2}-\d{1,2}\b", re.I)
CHAPTER_SECTION_RE = re.compile(r"chap(\d+)_section_(\d+)\.html$")


@dataclass(frozen=True)
class SourceAsset:
    id: str
    para_id: str
    chapter: int
    section: int
    asset_type: str
    label: str
    title: str
    source_url: str
    source_page_url: str
    pdf_url: str | None
    html: str | None
    image_url: str | None
    alt_text: str | None


SCHEMA = """
CREATE TABLE IF NOT EXISTS source_assets (
    id              TEXT PRIMARY KEY,
    para_id         TEXT NOT NULL,
    chapter         INTEGER NOT NULL,
    section         INTEGER NOT NULL,
    asset_type      TEXT NOT NULL,
    label           TEXT NOT NULL,
    title           TEXT,
    source_url      TEXT NOT NULL,
    source_page_url TEXT NOT NULL,
    pdf_url         TEXT,
    html            TEXT,
    image_url       TEXT,
    alt_text        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(label, source_url)
);
CREATE INDEX IF NOT EXISTS idx_source_assets_para ON source_assets(para_id);
CREATE INDEX IF NOT EXISTS idx_source_assets_label ON source_assets(label);
"""


def collapse(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def asset_id(label: str, source_url: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "asset"
    digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:10]
    return f"faa-7110bb-{base}-{digest}"


def clean_title(raw_text: str, label: str) -> str:
    text = collapse(raw_text)
    text = re.sub(re.escape(label), "", text, flags=re.I).strip(" -:·")
    return text or label


def normalize_label(match: re.Match[str]) -> str:
    return re.sub(r"\s+", " ", match.group(0).upper())


def anchor_for(tag: Tag | None) -> str | None:
    if not tag:
        return None
    if tag.get("id"):
        return str(tag["id"])
    anchor = tag.find("a", id=True)
    if isinstance(anchor, Tag):
        return str(anchor["id"])
    return None


def paragraph_for(tag: Tag) -> str | None:
    current = tag.find_previous(class_="paragraph-title")
    if not isinstance(current, Tag):
        return None
    para_id = str(current.get("id") or "").strip()
    return para_id if PARA_ID_RE.match(para_id) else None


def sanitize_fragment(fragment: str, page_url: str) -> str:
    soup = BeautifulSoup(fragment, "html.parser")
    for bad in soup(["script", "style", "iframe", "object", "embed"]):
        bad.decompose()
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)
        for key, value in attrs.items():
            lower = key.lower()
            if lower.startswith("on"):
                del tag.attrs[key]
            elif lower in {"src", "href"}:
                tag.attrs[key] = urljoin(page_url, str(value)).replace(" ", "%20")
    return str(soup)


def previous_caption(table: Tag) -> Tag | None:
    for sibling in table.previous_siblings:
        if isinstance(sibling, Tag):
            if TABLE_LABEL_RE.search(collapse(sibling.get_text(" "))):
                return sibling
            if sibling.name in {"h1", "h2", "h3", "h4"} or "paragraph-title" in (sibling.get("class") or []):
                return None
    return None


def first_meaningful_text(table: Tag) -> str:
    for cell in table.find_all(["th", "td"]):
        text = collapse(cell.get_text(" "))
        if text:
            return text[:120]
    return ""


def source_url(page_url: str, tag: Tag | None) -> str:
    anchor = anchor_for(tag)
    return f"{page_url}#{anchor}" if anchor else page_url


def extract_tables(soup: BeautifulSoup, page_url: str, chapter: int, section: int, known_paras: set[str]) -> Iterable[SourceAsset]:
    generated_counts: dict[str, int] = {}
    for table in soup.find_all("table"):
        if not isinstance(table, Tag):
            continue
        para_id = paragraph_for(table)
        if not para_id or para_id not in known_paras:
            continue

        caption = previous_caption(table)
        caption_text = collapse(caption.get_text(" ")) if caption else ""
        match = TABLE_LABEL_RE.search(caption_text)
        if match:
            label = normalize_label(match)
            title = clean_title(caption_text, label)
            url = source_url(page_url, caption)
            html = sanitize_fragment(f"{caption}{table}", page_url)
        else:
            generated_counts[para_id] = generated_counts.get(para_id, 0) + 1
            label = f"TABLE {para_id} #{generated_counts[para_id]}"
            title = first_meaningful_text(table) or "FAA source table"
            url = source_url(page_url, table)
            html = sanitize_fragment(str(table), page_url)

        yield SourceAsset(
            id=asset_id(label, url),
            para_id=para_id,
            chapter=chapter,
            section=section,
            asset_type="table",
            label=label,
            title=title,
            source_url=url,
            source_page_url=page_url,
            pdf_url=None,
            html=html,
            image_url=None,
            alt_text=None,
        )


def extract_figures(soup: BeautifulSoup, page_url: str, chapter: int, section: int, known_paras: set[str]) -> Iterable[SourceAsset]:
    seen_urls: set[str] = set()

    for figure in soup.find_all("figure"):
        if not isinstance(figure, Tag):
            continue
        figure_text = collapse(figure.get_text(" "))
        match = FIGURE_LABEL_RE.search(figure_text)
        img = figure.find("img")
        if not match or not isinstance(img, Tag) or not img.get("src"):
            continue
        para_id = paragraph_for(figure)
        if not para_id or para_id not in known_paras:
            continue

        label = normalize_label(match)
        title = clean_title(figure_text, label)
        url = source_url(page_url, figure)
        image_url = urljoin(page_url, str(img["src"])).replace(" ", "%20")
        seen_urls.add(url)
        yield SourceAsset(
            id=asset_id(label, url),
            para_id=para_id,
            chapter=chapter,
            section=section,
            asset_type="figure",
            label=label,
            title=title,
            source_url=url,
            source_page_url=page_url,
            pdf_url=None,
            html=sanitize_fragment(str(figure), page_url),
            image_url=image_url,
            alt_text=collapse(img.get("alt") or title),
        )

    for heading in soup.find_all(["h3", "h4", "h5", "p"]):
        if not isinstance(heading, Tag):
            continue
        heading_text = collapse(heading.get_text(" "))
        match = FIGURE_LABEL_RE.search(heading_text)
        if not match:
            continue

        img = heading.find_next("img")
        if not isinstance(img, Tag) or not img.get("src"):
            continue
        next_para_heading = heading.find_next(class_="paragraph-title")
        if isinstance(next_para_heading, Tag) and next_para_heading.sourceline and img.sourceline:
            if next_para_heading.sourceline < img.sourceline:
                continue

        para_id = paragraph_for(heading)
        if not para_id or para_id not in known_paras:
            continue

        label = normalize_label(match)
        title = clean_title(heading_text, label)
        url = source_url(page_url, heading)
        if url in seen_urls:
            continue
        image_url = urljoin(page_url, str(img["src"])).replace(" ", "%20")
        html = sanitize_fragment(f"{heading}{img.parent if isinstance(img.parent, Tag) else img}", page_url)
        yield SourceAsset(
            id=asset_id(label, url),
            para_id=para_id,
            chapter=chapter,
            section=section,
            asset_type="figure",
            label=label,
            title=title,
            source_url=url,
            source_page_url=page_url,
            pdf_url=None,
            html=html,
            image_url=image_url,
            alt_text=collapse(img.get("alt") or title),
        )


def html_section_urls(session: requests.Session) -> list[tuple[int, int, str]]:
    response = session.get(FAA_HTML_BASE, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    urls: dict[tuple[int, int], str] = {}
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        match = CHAPTER_SECTION_RE.search(href)
        if not match:
            continue
        chapter, section = int(match.group(1)), int(match.group(2))
        urls[(chapter, section)] = urljoin(FAA_HTML_BASE, href)
    return [(chapter, section, url) for (chapter, section), url in sorted(urls.items())]


def known_paragraphs(db_path: Path) -> set[str]:
    db = sqlite3.connect(db_path)
    try:
        return {row[0] for row in db.execute("SELECT para_id FROM paragraphs")}
    finally:
        db.close()


def load_pdf_urls() -> dict[str, str]:
    lookup_path = ROOT / "backend" / "app" / "data" / "faa_7110_65bb_v2_lookup.csv"
    if not lookup_path.exists():
        return {}
    import csv

    urls: dict[str, str] = {}
    with lookup_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("kind") == "paragraph_heading" and row.get("key") and row.get("url"):
                urls.setdefault(row["key"], row["url"])
    return urls


def attach_pdf_urls(assets: list[SourceAsset]) -> list[SourceAsset]:
    pdf_urls = load_pdf_urls()
    attached: list[SourceAsset] = []
    for asset in assets:
        data = asdict(asset)
        data["pdf_url"] = pdf_urls.get(asset.para_id) or f"{FAA_PDF_URL}"
        attached.append(SourceAsset(**data))
    return attached


def extract_assets(db_path: Path, sleep_seconds: float) -> list[SourceAsset]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    known_paras = known_paragraphs(db_path)
    assets: dict[str, SourceAsset] = {}

    for chapter, section, url in html_section_urls(session):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for asset in [*extract_tables(soup, url, chapter, section, known_paras), *extract_figures(soup, url, chapter, section, known_paras)]:
            assets[asset.id] = asset
        if sleep_seconds:
            time.sleep(sleep_seconds)

    return attach_pdf_urls(sorted(assets.values(), key=lambda item: (item.chapter, item.section, item.para_id, item.asset_type, item.label)))


def write_manifest(path: Path, assets: list[SourceAsset]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "FAA JO 7110.65BB Change 2 official HTML",
        "source_base_url": FAA_HTML_BASE,
        "asset_count": len(assets),
        "assets": [asdict(asset) for asset in assets],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def upsert_db(db_path: Path, assets: list[SourceAsset]) -> None:
    db = sqlite3.connect(db_path)
    try:
        db.executescript(SCHEMA)
        db.execute("DELETE FROM source_assets")
        db.executemany(
            """
            INSERT INTO source_assets (
                id, para_id, chapter, section, asset_type, label, title,
                source_url, source_page_url, pdf_url, html, image_url, alt_text
            ) VALUES (
                :id, :para_id, :chapter, :section, :asset_type, :label, :title,
                :source_url, :source_page_url, :pdf_url, :html, :image_url, :alt_text
            )
            """,
            [asdict(asset) for asset in assets],
        )
        db.execute(
            """
            UPDATE paragraphs
            SET has_visual = 1
            WHERE para_id IN (SELECT DISTINCT para_id FROM source_assets)
            """
        )
        db.commit()
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sleep", type=float, default=0.05, help="Polite delay between FAA HTML requests")
    parser.add_argument("--no-db", action="store_true", help="Only write the JSON manifest")
    args = parser.parse_args()

    assets = extract_assets(args.db, args.sleep)
    write_manifest(args.out, assets)
    if not args.no_db:
        upsert_db(args.db, assets)

    counts: dict[str, int] = {}
    for asset in assets:
        counts[asset.asset_type] = counts.get(asset.asset_type, 0) + 1
    print(f"Extracted {len(assets)} FAA source assets: {counts}")
    print(f"Manifest: {args.out}")
    if not args.no_db:
        print(f"Updated DB: {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
