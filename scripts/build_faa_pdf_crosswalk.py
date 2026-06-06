#!/usr/bin/env python3
"""
Build a direct-link crosswalk for FAA PDFs such as JO 7110.65BB.

It captures two distinct navigation concepts:
  1. PDF page labels, e.g. 1-2-4, embedded in the PDF itself.
  2. FAA paragraph headings, e.g. 1-2-4. REFERENCES, found by text extraction.

Outputs:
  - crosswalk CSV: one row per physical PDF page
  - lookup CSV: one row per page-label or paragraph-key hit

Examples:
  python build_faa_pdf_crosswalk.py 7110.65BB.pdf --find 1-2-4
  python build_faa_pdf_crosswalk.py 7110.65BB.pdf --base-url "https://...Final.pdf"
  python build_faa_pdf_crosswalk.py 7110.65BB.pdf --download-url "https://...Final.pdf"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import logging
import urllib.request
import warnings
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

DEFAULT_URL = (
    "https://www.faa.gov/documentLibrary/media/Order/"
    "7110.65BB_Bsc_w_Chg_1_and_2_dtd_1-22-26_Final.pdf"
)

DASHES = str.maketrans({"–": "-", "−": "-", "—": "-"})

# FAA paragraph headings normally begin at line start and look like:
#   3-10-5. LANDING CLEARANCE
#   5-5-4. MINIMA
# Use a cautious heading title requirement to avoid table-of-contents bodies.
PARA_HEADING_RE = re.compile(
    r"(?m)^\s*(?P<num>\d{1,2}[-–−]\d{1,2}[-–−]\d{1,3})\.\s+"
    r"(?P<title>[A-Z][A-Z0-9 ,;:/()\-'\"&]+?)\s*$"
)

# This is only a fallback for PDFs without usable embedded page labels.
FOOTER_LABEL_RE = re.compile(
    r"\b("
    r"\d{1,2}[-–−]\d{1,2}[-–−]\d{1,3}"
    r"|E of C[-–−]\d{1,3}"
    r"|TBL[-–−]\d{1,3}"
    r"|[ivxlcdm]{1,10}"
    r")\b",
    re.IGNORECASE,
)


def norm(s: str | None) -> str:
    return (s or "").translate(DASHES).strip()


def direct_url(base_url: str, physical_page: int) -> str:
    return f"{base_url}#page={physical_page}"


def download(url: str, path: Path) -> None:
    print(f"Downloading {url} -> {path}", file=sys.stderr)
    urllib.request.urlretrieve(url, path)


def safe_page_labels(reader: PdfReader) -> list[str]:
    """Return embedded page labels, suppressing pypdf warnings from odd label ranges."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            labels = list(reader.page_labels)
        except Exception:
            labels = []
    return [norm(x) for x in labels]


def extract_text(reader: PdfReader, page_index: int) -> str:
    try:
        return reader.pages[page_index].extract_text() or ""
    except Exception:
        return ""


def fallback_label_from_text(text: str) -> str:
    """Heuristic fallback when embedded PDF page labels are unavailable."""
    t = norm(text)
    zones = [t[:600], t[-1200:]]
    candidates: list[str] = []
    for z in zones:
        candidates.extend(norm(m.group(1)) for m in FOOTER_LABEL_RE.finditer(z))
    return candidates[-1] if candidates else ""


def find_paragraph_headings(text: str) -> list[tuple[str, str]]:
    t = norm(text)
    out = []
    for m in PARA_HEADING_RE.finditer(t):
        num = norm(m.group("num"))
        title = " ".join(norm(m.group("title")).split())
        # Ignore common false hits from body examples with all-caps fragments.
        if len(title) >= 3:
            out.append((num, title))
    # Preserve first occurrence order but dedupe exact pairs.
    seen = set()
    deduped = []
    for item in out:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def build(pdf_path: Path, base_url: str) -> tuple[list[dict], list[dict]]:
    reader = PdfReader(str(pdf_path))
    labels = safe_page_labels(reader)
    n = len(reader.pages)
    rows: list[dict] = []
    lookup: list[dict] = []

    for page_index in range(n):
        physical = page_index + 1
        text = extract_text(reader, page_index)
        embedded_label = labels[page_index] if page_index < len(labels) else ""
        label = embedded_label or fallback_label_from_text(text)
        paragraphs = find_paragraph_headings(text)
        para_nums = ";".join(num for num, _title in paragraphs)
        para_titles = ";".join(f"{num}. {_title}" for num, _title in paragraphs)
        url = direct_url(base_url, physical)

        row = {
            "physical_page_1based": physical,
            "pdf_page_index_0based": page_index,
            "page_label": label,
            "paragraph_numbers_found": para_nums,
            "paragraph_headings_found": para_titles,
            "url": url,
        }
        rows.append(row)

        if label:
            lookup.append(
                {
                    "key": label,
                    "kind": "page_label",
                    "physical_page_1based": physical,
                    "page_label": label,
                    "title_or_heading": "",
                    "url": url,
                }
            )

        for num, title in paragraphs:
            lookup.append(
                {
                    "key": num,
                    "kind": "paragraph_heading",
                    "physical_page_1based": physical,
                    "page_label": label,
                    "title_or_heading": title,
                    "url": url,
                }
            )

    return rows, lookup


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def print_hits(lookup: list[dict], key: str) -> None:
    k = norm(key)
    hits = [r for r in lookup if norm(r["key"]) == k]
    if not hits:
        print(f"No exact hit for {key!r}.")
        return
    print(f"Exact hits for {key!r}:")
    for r in hits:
        heading = f" - {r['title_or_heading']}" if r["title_or_heading"] else ""
        print(
            f"  {r['kind']}: PDF page {r['physical_page_1based']} "
            f"(label {r['page_label']!r}){heading}\n"
            f"    {r['url']}"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="?", type=Path, default=Path("7110.65BB.pdf"))
    ap.add_argument("--download-url", default="", help="Download the PDF first if the local path does not exist.")
    ap.add_argument("--base-url", default=DEFAULT_URL, help="Base URL used for generated #page links.")
    ap.add_argument("--out-prefix", default="faa_7110_65bb", help="Output filename prefix.")
    ap.add_argument("--find", default="", help="Exact page label or paragraph number to look up, e.g. 1-2-4.")
    args = ap.parse_args()

    if not args.pdf.exists():
        url = args.download_url or args.base_url
        download(url, args.pdf)

    rows, lookup = build(args.pdf, args.base_url)

    crosswalk_path = Path(f"{args.out_prefix}_crosswalk.csv")
    lookup_path = Path(f"{args.out_prefix}_lookup.csv")

    write_csv(
        crosswalk_path,
        rows,
        [
            "physical_page_1based",
            "pdf_page_index_0based",
            "page_label",
            "paragraph_numbers_found",
            "paragraph_headings_found",
            "url",
        ],
    )
    write_csv(
        lookup_path,
        lookup,
        ["key", "kind", "physical_page_1based", "page_label", "title_or_heading", "url"],
    )

    print(f"Wrote {crosswalk_path} ({len(rows)} pages)")
    print(f"Wrote {lookup_path} ({len(lookup)} lookup rows)")

    if args.find:
        print_hits(lookup, args.find)


if __name__ == "__main__":
    main()
