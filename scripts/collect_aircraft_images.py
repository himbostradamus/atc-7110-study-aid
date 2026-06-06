#!/usr/bin/env python3
"""
Collect auditable aircraft image candidates for JO 7360-derived cards.

Default source is Wikimedia Commons because the API exposes stable file pages,
license metadata, author/credit metadata, and file URLs without an API key.

This script verifies download/image integrity only. It does not prove aircraft
identity. Treat the manifest as a review queue before showing images to learners.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "atc-study-aid-aircraft-image-collector/0.1 (local educational image manifest builder)"
IMAGE_MIME_PREFIX = "image/"
OBVIOUS_NON_RECOGNITION_TITLE_PATTERNS = [
    r"\b3[- ]?view\b",
    r"\baftermath\b",
    r"\baircraft tails\b",
    r"\bblueprint\b",
    r"\bboneyard\b",
    r"\bcabin\b",
    r"\bcockpit\b",
    r"\bcrash\b",
    r"\bdiagram\b",
    r"\bdrawing\b",
    r"\bfamily v\d",
    r"\binterior\b",
    r"\bhangar inside\b",
    r"\bline drawing\b",
    r"\blogo\b",
    r"\bpanel\b",
    r"\blavatory\b",
    r"\bburning wheels\b",
    r"\bsimulator\b",
    r"\bsvg\b",
    r"\bwreck\b",
]


@dataclass
class AircraftRow:
    rank: str
    type_designator: str
    group: str
    description: str
    engine_aircraft_class: str
    wtc: str
    cwt: str
    srs: str
    lahso: str
    manufacturer_model: str


@dataclass
class CandidateImage:
    type_designator: str
    aircraft_group: str
    manufacturer_model: str
    query: str
    source: str
    source_page: str
    file_title: str
    image_url: str
    thumb_url: str
    license_short_name: str
    license_url: str
    artist: str
    credit: str
    width: int
    height: int
    mime: str
    local_path: str
    public_path: str
    sha256: str
    status: str
    reason: str
    identity_status: str = "not_reviewed"
    identity_notes: str = ""


class RateLimited(RuntimeError):
    """Raised when Commons starts returning HTTP 429 for a packet."""

    def __init__(self, candidates: list[CandidateImage] | None = None):
        super().__init__("rate_limited")
        self.candidates = candidates or []


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value.replace("~", "")).strip()


def title_case_group(value: str) -> str:
    return clean_text(value).title()


def compact_model_label(value: str, max_len: int = 90) -> str:
    cleaned = clean_text(value).replace(" ; ", "; ")
    parts = [part.strip() for part in cleaned.split(";") if part.strip()]
    if not parts:
        parts = [cleaned] if cleaned else []
    labels: list[str] = []
    seen: set[str] = set()
    for part in parts:
        label = part.split(",", 1)[1].strip() if "," in part else part
        label = clean_text(label)
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) == 2:
            break
    label = " / ".join(labels) if labels else cleaned
    return label if len(label) <= max_len else f"{label[:max_len - 1].rstrip()}..."


def first_manufacturer_model(value: str) -> tuple[str, str]:
    cleaned = clean_text(value).replace(" ; ", "; ")
    first = next((part.strip() for part in cleaned.split(";") if part.strip()), cleaned)
    if "," not in first:
        return "", first
    manufacturer, model = first.split(",", 1)
    return clean_text(manufacturer), clean_text(model)


def simplified_model_terms(model: str) -> list[str]:
    cleaned = clean_text(re.sub(r"\([^)]*\)", " ", model))
    candidates = [cleaned]
    compact = re.search(r"\b([A-Z]{0,3}\d{2,4}[A-Z]?)\b", cleaned, re.I)
    if compact:
        candidates.append(compact.group(1))
    spaced = re.search(r"\b([A-Z]{0,3})\s*([0-9]{2,4}[A-Z]?)\b", cleaned, re.I)
    if spaced:
        candidates.append(f"{spaced.group(1)} {spaced.group(2)}".strip())
    out: list[str] = []
    for candidate in candidates:
        candidate = clean_text(candidate)
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def read_aircraft_rows(path: Path, limit: int = 0, type_filter: set[str] | None = None) -> list[AircraftRow]:
    rows: list[AircraftRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            designator = clean_text(raw.get("type_designator") or raw.get("jo_type_designator") or "")
            models = clean_text(raw.get("manufacturer_model") or "")
            if not designator or not models:
                continue
            if type_filter and designator not in type_filter:
                continue
            rows.append(
                AircraftRow(
                    rank=clean_text(raw.get("rank") or raw.get("priority_rank") or ""),
                    type_designator=designator,
                    group=title_case_group(raw.get("group") or raw.get("requested_type") or ""),
                    description=clean_text(raw.get("description") or ""),
                    engine_aircraft_class=clean_text(raw.get("engine_aircraft_class") or ""),
                    wtc=clean_text(raw.get("wtc") or ""),
                    cwt=clean_text(raw.get("cwt") or ""),
                    srs=clean_text(raw.get("srs") or ""),
                    lahso=clean_text(raw.get("lahso") or ""),
                    manufacturer_model=models,
                )
            )
            if limit and len(rows) >= limit:
                break
    return rows


def spoken_name_to_model(spoken_name: str) -> str:
    cleaned = clean_text(spoken_name)
    cleaned = re.sub(r"\bHeavy\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\(or[^)]*\)", "", cleaned, flags=re.I)
    replacements = [
        ("Seven Seventy-Seven", "777"),
        ("Seven Sixty-Seven", "767"),
        ("Seven Fifty-Seven", "757"),
        ("Seven Forty-Seven", "747"),
        ("Seven Thirty-Seven", "737"),
        ("Three Forty", "340"),
        ("Three Twenty", "320"),
        ("Three Nineteen", "319"),
        ("Three Hundred", "300"),
        ("D-C Ten", "DC-10"),
        ("M-D Eleven", "MD-11"),
        ("M-D Eighty", "MD-80"),
        ("F-Sixteen", "F-16"),
        ("C-R-J Nine", "CRJ-900"),
        ("C-R-J One", "CRJ-100"),
    ]
    for old, new in replacements:
        cleaned = re.sub(re.escape(old), new, cleaned, flags=re.I)
    return clean_text(cleaned)


def read_spoken_aircraft_rows(path: Path, limit: int = 0, type_filter: set[str] | None = None) -> list[AircraftRow]:
    rows: list[AircraftRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            designator = clean_text(raw.get("ICAO") or "")
            spoken = clean_text(raw.get("SpokenName") or "")
            manufacturer = clean_text(raw.get("Manufacturer") or "")
            if not designator or not spoken:
                continue
            if type_filter and designator not in type_filter:
                continue
            model = spoken_name_to_model(spoken)
            rows.append(
                AircraftRow(
                    rank="",
                    type_designator=designator,
                    group=manufacturer or "Common",
                    description="",
                    engine_aircraft_class="",
                    wtc="",
                    cwt=clean_text(raw.get("CWT") or ""),
                    srs=clean_text(raw.get("SRS") or ""),
                    lahso="",
                    manufacturer_model=f"{manufacturer}, {model}" if manufacturer else model,
                )
            )
            if limit and len(rows) >= limit:
                break
    return rows


def merge_aircraft_rows(primary_rows: list[AircraftRow], fallback_rows: list[AircraftRow]) -> list[AircraftRow]:
    merged: dict[str, AircraftRow] = {}
    for row in fallback_rows:
        merged[row.type_designator] = row
    for row in primary_rows:
        merged[row.type_designator] = row
    return list(merged.values())


def query_strings(row: AircraftRow) -> list[str]:
    manufacturer, model = first_manufacturer_model(row.manufacturer_model)
    compact_label = compact_model_label(row.manufacturer_model)
    aircraft_kind = "helicopter" if "helicopter" in row.description.lower() else "aircraft"
    raw_queries = [
        *[f'"{term}" aircraft' for term in designator_model_terms(row.type_designator)],
        *[f'{manufacturer} "{term}" aircraft' for term in designator_model_terms(row.type_designator) if manufacturer],
        f'"{row.type_designator}" aircraft',
        f'"{model}" {manufacturer} aircraft' if manufacturer and model else "",
        f'{manufacturer} {model} aircraft' if manufacturer and model else "",
        f'"{compact_label}" aircraft' if compact_label else "",
        f'{manufacturer} {model} {aircraft_kind}' if manufacturer and model else "",
    ]
    for term in simplified_model_terms(model):
        raw_queries.append(f"{manufacturer} {term} aircraft" if manufacturer else f"{term} aircraft")
    queries: list[str] = []
    for query in raw_queries:
        query = clean_text(query)
        if query and query not in queries:
            queries.append(query)
    return queries


def designator_model_terms(designator: str) -> list[str]:
    exact = {
        "A306": ["Airbus A300-600"],
        "A319": ["Airbus A319"],
        "A320": ["Airbus A320"],
        "A342": ["Airbus A340-200"],
        "A343": ["Airbus A340-300"],
        "AC68": ["Aero Commander 680"],
        "B06": ["Bell 206"],
        "B732": ["Boeing 737-200", "Boeing 737-2", "737-200 Advanced"],
        "B738": ["Boeing 737-800"],
        "B744": ["Boeing 747-400"],
        "B752": ["Boeing 757-200"],
        "B762": ["Boeing 767-200"],
        "B763": ["Boeing 767-300"],
        "B772": ["Boeing 777-200", "Boeing 777-200ER", "Boeing 777-2"],
        "B773": ["Boeing 777-300"],
        "BE20": ["Beechcraft King Air 200"],
        "BE36": ["Beechcraft Bonanza 36"],
        "BE40": ["Beechcraft 400 Beechjet"],
        "BE58": ["Beechcraft Baron 58"],
        "C172": ["Cessna 172"],
        "C208": ["Cessna 208 Caravan"],
        "C310": ["Cessna 310"],
        "C421": ["Cessna 421"],
        "C550": ["Cessna Citation II", "Cessna Citation 550"],
        "C82T": ["Cessna T182 Turbo Skylane"],
        "C120": ["Cessna 120"],
        "C140": ["Cessna 140"],
        "C150": ["Cessna 150"],
        "C152": ["Cessna 152"],
        "C162": ["Cessna 162 Skycatcher"],
        "C175": ["Cessna 175 Skylark"],
        "C177": ["Cessna 177 Cardinal"],
        "C180": ["Cessna 180 Skywagon"],
        "C182": ["Cessna 182 Skylane"],
        "C185": ["Cessna 185 Skywagon"],
        "C188": ["Cessna 188 AgWagon"],
        "C190": ["Cessna 190"],
        "C195": ["Cessna 195"],
        "C205": ["Cessna 205"],
        "C206": ["Cessna 206 Stationair"],
        "C207": ["Cessna 207 Skywagon"],
        "C210": ["Cessna 210 Centurion"],
        "C240": ["Cessna T240 TTx", "Cessna Corvalis TTx"],
        "C303": ["Cessna T303 Crusader"],
        "CL60": ["Bombardier Challenger 600", "Canadair CL-600"],
        "CRJ1": ["Bombardier CRJ100", "Canadair CRJ-100"],
        "CRJ9": ["Bombardier CRJ900", "Bombardier CRJ-900LR", "Canadair CRJ-900"],
        "DC10": ["McDonnell Douglas DC-10"],
        "DH8D": ["De Havilland Dash 8 Q400", "DHC-8-400"],
        "F16": ["F-16 Fighting Falcon"],
        "FA20": ["Dassault Falcon 20"],
        "GLF4": ["Gulfstream IV", "Gulfstream G-IV"],
        "LJ35": ["Learjet 35"],
        "M20P": ["Mooney M20"],
        "MD11": ["McDonnell Douglas MD-11"],
        "MD81": ["McDonnell Douglas MD-81", "McDonnell Douglas MD-80"],
        "P28A": ["Piper PA-28 Cherokee"],
        "PA31": ["Piper PA-31 Navajo"],
        "PA34": ["Piper PA-34 Seneca"],
        "PA46": ["Piper PA-46 Malibu"],
        "PAY3": ["Piper PA-31T Cheyenne"],
        "PC12": ["Pilatus PC-12"],
        "SR22": ["Cirrus SR22"],
    }
    return exact.get(clean_text(designator).upper(), [])


def commons_search(query: str, limit: int, thumb_width: int, retries: int, rate_limit_sleep: float) -> list[dict]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo|info",
        "inprop": "url",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": thumb_width,
    }
    for attempt in range(retries + 1):
        response = requests.get(COMMONS_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            return list(response.json().get("query", {}).get("pages", {}).values())
        if attempt < retries:
            time.sleep(rate_limit_sleep)
    raise RuntimeError("rate_limited")


def clean_html(value: str) -> str:
    return clean_text(value)


def extmetadata(imageinfo: dict, key: str) -> str:
    return clean_html(imageinfo.get("extmetadata", {}).get(key, {}).get("value", ""))


def page_url_from_title(title: str) -> str:
    return "https://commons.wikimedia.org/wiki/" + quote(title.replace(" ", "_"), safe="/:_")


def is_obvious_non_recognition_title(title: str) -> bool:
    title = clean_text(title).lower()
    return any(re.search(pattern, title, flags=re.I) for pattern in OBVIOUS_NON_RECOGNITION_TITLE_PATTERNS)


def is_target_title_mismatch(designator: str, title: str) -> bool:
    title = clean_text(title).lower()
    designator = clean_text(designator).upper()
    mismatch_patterns = {
        "A342": [r"a340-3", r"a340-5", r"a340-6"],
        "A343": [r"a340-2", r"a340-5", r"a340-6"],
        "B732": [r"737-3", r"737 ?300", r"737-4", r"737 ?400", r"737-5", r"737 ?500", r"737-6", r"737 ?600", r"737-7", r"737 ?700", r"737-8", r"737 ?800", r"737-9", r"737 ?900", r"737 max", r"b738", r"\bp-8\b", r"poseidon"],
        "B762": [r"767-3", r"767-4"],
        "B763": [r"767-2", r"767-4"],
        "B772": [r"777-3", r"777 ?300", r"777-8", r"777 ?800", r"777-9", r"777 ?900"],
        "B773": [r"777-2", r"777 ?200", r"777-8", r"777 ?800", r"777-9", r"777 ?900"],
        "C120": [r"rafale", r"f-15", r"eagle", r"cessna 140"],
        "C140": [r"cessna 120"],
        "C150": [r"\bc152\b"],
        "C152": [r"\bc150\b"],
        "C162": [r"rafale", r"f-15", r"eagle"],
        "C175": [r"rafale", r"f-15", r"eagle"],
        "C180": [r"cn-235", r"persuader"],
        "C182": [r"helicopter"],
        "C185": [r"inarijärvi"],
        "C190": [r"cessna ?195"],
        "C205": [r"cessna\.?206", r"cessna 206"],
        "C207": [r"cessna\.?206", r"cessna 206"],
        "C210": [r"maintenance center"],
        "C421": [r"cessna ?335", r"cessna ?402", r"cessna ?414", r"chancellor"],
        "C82S": [r"\bc-82s?\b", r"\bc82s\b"],
        "CRJ1": [r"crj-7", r"crj 7", r"crj-9", r"crj 9", r"crj-1000", r"crj 1000"],
        "CRJ9": [r"crj-1", r"crj 1", r"crj-2", r"crj 2", r"crj-7", r"crj 7", r"crj-1000", r"crj 1000"],
    }
    return any(re.search(pattern, title, flags=re.I) for pattern in mismatch_patterns.get(designator, []))


def ext_from_mime_or_url(mime: str, url: str) -> str:
    ext = mimetypes.guess_extension(mime or "") or ""
    if ext == ".jpe":
        ext = ".jpg"
    if ext:
        return ext
    match = re.search(r"\.(jpg|jpeg|png|webp)(?:\?|$)", url, re.I)
    return f".{match.group(1).lower()}" if match else ".img"


def download_and_validate(
    url: str,
    dest_dir: Path,
    min_width: int,
    min_height: int,
    retries: int,
    rate_limit_sleep: float,
) -> tuple[Path, str, int, int, str]:
    for attempt in range(retries + 1):
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=45)
        if response.status_code != 429:
            break
        if attempt < retries:
            time.sleep(rate_limit_sleep)
    else:
        raise RuntimeError("rate_limited")

    if response.status_code == 429:
        raise RuntimeError("rate_limited")
    response.raise_for_status()
    mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if mime and not mime.startswith(IMAGE_MIME_PREFIX):
        raise ValueError(f"not an image content-type: {mime}")

    content = response.content
    sha = hashlib.sha256(content).hexdigest()
    path = dest_dir / f"{sha[:16]}{ext_from_mime_or_url(mime, url)}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)

    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        width, height = image.size
        fmt = image.format or ""

    if width < min_width or height < min_height:
        raise ValueError(f"image too small: {width}x{height}")
    return path, sha, width, height, mime or fmt


def public_path_for(local_path: Path, public_root: Path) -> str:
    try:
        return "/" + local_path.relative_to(public_root).as_posix()
    except ValueError:
        return local_path.as_posix()


def candidates_for_row(
    row: AircraftRow,
    output_dir: Path,
    public_root: Path,
    per_type: int,
    search_limit: int,
    thumb_width: int,
    min_width: int,
    min_height: int,
    sleep_seconds: float,
    metadata_only: bool,
    include_obvious_nonrecognition: bool,
    retries: int,
    rate_limit_sleep: float,
    max_queries_per_type: int,
    stop_on_rate_limit: bool,
) -> list[CandidateImage]:
    accepted: list[CandidateImage] = []
    seen_urls: set[str] = set()
    for query_index, query in enumerate(query_strings(row), 1):
        if max_queries_per_type and query_index > max_queries_per_type:
            break
        if len(accepted) >= per_type:
            break
        try:
            pages = commons_search(query, search_limit, thumb_width, retries, rate_limit_sleep)
        except Exception as exc:
            print(f"WARN search failed for {row.type_designator} query={query!r}: {exc}", file=sys.stderr)
            if str(exc) == "rate_limited":
                if stop_on_rate_limit:
                    raise RateLimited(accepted)
                return accepted
            continue
        time.sleep(sleep_seconds)

        for page in pages:
            if len(accepted) >= per_type:
                break
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            imageinfo = infos[0]
            image_url = imageinfo.get("url") or ""
            thumb_url = imageinfo.get("thumburl") or image_url
            mime = (imageinfo.get("mime") or "").lower()
            if not image_url or image_url in seen_urls:
                continue
            if mime and not mime.startswith(IMAGE_MIME_PREFIX):
                continue
            seen_urls.add(image_url)

            title = page.get("title", "")
            if not include_obvious_nonrecognition and is_obvious_non_recognition_title(title):
                continue
            if not include_obvious_nonrecognition and is_target_title_mismatch(row.type_designator, title):
                continue
            if metadata_only:
                accepted.append(
                    CandidateImage(
                        type_designator=row.type_designator,
                        aircraft_group=row.group,
                        manufacturer_model=row.manufacturer_model,
                        query=query,
                        source="Wikimedia Commons",
                        source_page=page_url_from_title(title),
                        file_title=title,
                        image_url=image_url,
                        thumb_url=thumb_url,
                        license_short_name=extmetadata(imageinfo, "LicenseShortName"),
                        license_url=extmetadata(imageinfo, "LicenseUrl"),
                        artist=extmetadata(imageinfo, "Artist"),
                        credit=extmetadata(imageinfo, "Credit"),
                        width=int(imageinfo.get("width") or 0),
                        height=int(imageinfo.get("height") or 0),
                        mime=mime,
                        local_path="",
                        public_path=thumb_url,
                        sha256=hashlib.sha256(image_url.encode("utf-8")).hexdigest(),
                        status="metadata_only",
                        reason="candidate_metadata_collected_without_download",
                    )
                )
                continue

            try:
                time.sleep(sleep_seconds)
                local_path, sha, width, height, actual_mime = download_and_validate(
                    thumb_url or image_url,
                    output_dir / "images" / row.type_designator,
                    min_width,
                    min_height,
                    retries,
                    rate_limit_sleep,
                )
                accepted.append(
                    CandidateImage(
                        type_designator=row.type_designator,
                        aircraft_group=row.group,
                        manufacturer_model=row.manufacturer_model,
                        query=query,
                        source="Wikimedia Commons",
                        source_page=page_url_from_title(title),
                        file_title=title,
                        image_url=image_url,
                        thumb_url=thumb_url,
                        license_short_name=extmetadata(imageinfo, "LicenseShortName"),
                        license_url=extmetadata(imageinfo, "LicenseUrl"),
                        artist=extmetadata(imageinfo, "Artist"),
                        credit=extmetadata(imageinfo, "Credit"),
                        width=width,
                        height=height,
                        mime=actual_mime,
                        local_path=local_path.as_posix(),
                        public_path=public_path_for(local_path, public_root),
                        sha256=sha,
                        status="download_verified",
                        reason="opened_with_pillow_and_met_min_dimensions",
                    )
                )
            except Exception as exc:
                print(f"WARN rejected {row.type_designator} {title}: {exc}", file=sys.stderr)
                if str(exc) == "rate_limited":
                    if stop_on_rate_limit:
                        raise RateLimited(accepted)
                    return accepted
    return accepted


def write_manifest(records: list[CandidateImage], failures: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "manifest.jsonl"
    csv_path = output_dir / "manifest.csv"
    jsonl_path.write_text(
        "".join(json.dumps(asdict(record), ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    if records:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(records[0]).keys()))
            writer.writeheader()
            for record in records:
                writer.writerow(asdict(record))
    else:
        csv_path.write_text("", encoding="utf-8")
    (output_dir / "failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")


def read_existing_manifest(output_dir: Path) -> list[CandidateImage]:
    path = output_dir / "manifest.jsonl"
    if not path.exists():
        return []
    records: list[CandidateImage] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            records.append(CandidateImage(**{
                field: raw.get(field, "")
                for field in CandidateImage.__dataclass_fields__
            }))
        except Exception as exc:
            print(f"WARN skipped existing manifest row: {exc}", file=sys.stderr)
    return records


def image_identity(record: CandidateImage) -> str:
    return record.image_url or record.source_page or record.public_path or record.sha256


def merge_records(existing: list[CandidateImage], incoming: list[CandidateImage]) -> list[CandidateImage]:
    merged: list[CandidateImage] = []
    seen: set[str] = set()
    for record in [*existing, *incoming]:
        key = image_identity(record)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(record)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect aircraft image candidates from Wikimedia Commons.")
    parser.add_argument("--input", type=Path, default=Path("backend/app/data/curated_aircraft_jo7360_weighted_rows.csv"))
    parser.add_argument("--spoken-input", type=Path, default=Path("backend/app/data/curated_aircraft_designators.csv"))
    parser.add_argument("--output", type=Path, default=Path("frontend/public/aircraft-images"))
    parser.add_argument("--per-type", type=int, default=2)
    parser.add_argument("--search-limit", type=int, default=6)
    parser.add_argument("--thumb-width", type=int, default=640)
    parser.add_argument("--min-width", type=int, default=640)
    parser.add_argument("--min-height", type=int, default=360)
    parser.add_argument("--limit-types", type=int, default=0)
    parser.add_argument("--types", default="", help="Comma-separated JO 7360 type designators to collect.")
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--metadata-only", action="store_true", help="Collect source/thumbnail metadata without downloading files.")
    parser.add_argument("--append", action="store_true", help="Append to the existing manifest and dedupe by source image URL.")
    parser.add_argument("--include-obvious-nonrecognition", action="store_true", help="Keep obvious non-recognition titles such as line drawings, cockpits, logos, and wrecks.")
    parser.add_argument("--retries", type=int, default=0, help="Retry Commons search requests after HTTP 429.")
    parser.add_argument("--rate-limit-sleep", type=float, default=20.0, help="Seconds to wait between HTTP 429 retries.")
    parser.add_argument("--max-queries-per-type", type=int, default=0, help="Limit query attempts per aircraft type; useful for obscure variant batches.")
    parser.add_argument("--stop-on-rate-limit", action="store_true", help="Stop the packet after Commons returns HTTP 429, preserving partial output.")
    args = parser.parse_args()

    type_filter = {value.strip().upper() for value in args.types.split(",") if value.strip()}
    weighted_rows = read_aircraft_rows(args.input, type_filter=type_filter or None)
    spoken_rows = read_spoken_aircraft_rows(args.spoken_input, type_filter=type_filter or None)
    rows = merge_aircraft_rows(spoken_rows, weighted_rows)
    if args.limit_types:
        rows = rows[: args.limit_types]
    records: list[CandidateImage] = read_existing_manifest(args.output) if args.append else []
    initial_record_count = len(records)
    failures: list[dict] = []
    for index, row in enumerate(rows, 1):
        print(f"[{index}/{len(rows)}] {row.type_designator} {compact_model_label(row.manufacturer_model)}", flush=True)
        rate_limited = False
        try:
            candidates = candidates_for_row(
                row=row,
                output_dir=args.output,
                public_root=Path("frontend/public"),
                per_type=args.per_type,
                search_limit=args.search_limit,
                thumb_width=args.thumb_width,
                min_width=args.min_width,
                min_height=args.min_height,
                sleep_seconds=args.sleep,
                metadata_only=args.metadata_only,
                include_obvious_nonrecognition=args.include_obvious_nonrecognition,
                retries=args.retries,
                rate_limit_sleep=args.rate_limit_sleep,
                max_queries_per_type=args.max_queries_per_type,
                stop_on_rate_limit=args.stop_on_rate_limit,
            )
        except RateLimited as exc:
            candidates = exc.candidates
            rate_limited = True
        records = merge_records(records, candidates)
        if len(candidates) < args.per_type:
            failures.append({
                "type_designator": row.type_designator,
                "manufacturer_model": row.manufacturer_model,
                "accepted": len(candidates),
                "wanted": args.per_type,
                "queries": query_strings(row),
                "rate_limited": rate_limited,
            })
        write_manifest(records, failures, args.output)
        if rate_limited:
            print("Stopped early after Commons returned rate_limited; rerun later to continue.", file=sys.stderr, flush=True)
            break

    if args.append:
        print(f"Kept {initial_record_count} existing records; added {len(records) - initial_record_count} new unique records", flush=True)
    print(f"Wrote {len(records)} image records to {args.output}", flush=True)
    print(f"Shortfalls: {len(failures)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
