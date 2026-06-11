#!/usr/bin/env python3
"""Refresh selected aircraft classification fields from FAA JO 7360.1K."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTED = ROOT / "backend" / "app" / "data" / "curated_aircraft_jo7360_weighted_rows.csv"
DEFAULT_SPOKEN = ROOT / "backend" / "app" / "data" / "curated_aircraft_designators.csv"
VALID_CLASSES = {
    "Airship",
    "Amphibian",
    "Balloon",
    "Fixed-wing",
    "Glider",
    "Gyroplane",
    "Helicopter",
    "Tiltrotor",
}
ROW_RE = re.compile(
    r"^\s*(?P<designator>[A-Z0-9]{2,4})\*?\s+@?"
    r"(?P<class>Airship|Amphibian|Balloon|Fixed-wing|Glider|Gyroplane|Helicopter|Tiltrotor)"
    r"\s+(?P<engine>\S+)\s+(?P<wtc>Light/Medium|Light|Medium|Heavy|Super)"
    r"\s+(?P<cwt>[A-I])\s+(?P<srs>III|II|I)(?:\s+(?P<lahso>\d+))?(?:\s|$)"
)
C_ROW_RE = re.compile(
    r"^(?P<prefix>.*?)"
    r"(?P<designator>[A-Z0-9]{2,4})\*?\s+@?\$?"
    r"(?P<class>Airship|Amphibian|Balloon|Fixed-wing|Glider|Gyroplane|Helicopter|Tiltrotor)"
    r"\s+(?P<engine>\S+)\s+(?P<wtc>Light/Medium|Light|Medium|Heavy|Super)"
    r"\s+(?P<cwt>[A-I])\s+(?P<srs>III|II|I)(?:\s+\d+)?(?:\s|$)"
)


def source_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "order.txt"
        subprocess.run(
            ["pdftotext", "-layout", str(path), str(output)],
            check=True,
        )
        return output.read_text(encoding="utf-8", errors="replace")


def clean(value: str) -> str:
    return " ".join(str(value or "").replace("~", "").split())


def parse_appendix_a(text: str) -> dict[str, dict[str, str]]:
    start = text.rfind("Appendix A. Decode")
    end = text.rfind("Appendix B. Encode")
    if start < 0 or end < 0:
        raise SystemExit("Could not locate Appendix A boundaries in JO 7360 source.")

    rows: dict[str, dict[str, str]] = {}
    for line in text[start:end].splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        designator = match.group("designator")
        aircraft_class = match.group("class")
        rows[designator] = {
            "description": aircraft_class,
            "engine_aircraft_class": clean(match.group("engine")),
            "wtc": clean(match.group("wtc")),
            "cwt": clean(match.group("cwt")),
            "srs": clean(match.group("srs")),
            "lahso": clean(match.group("lahso") or ""),
        }
    if len(rows) < 1_000:
        raise SystemExit(f"Parsed only {len(rows)} Appendix A rows; expected at least 1,000.")
    return rows


def parse_appendix_c_models(text: str) -> dict[str, list[str]]:
    start = text.rfind("Appendix C. Decode")
    end = text.rfind("Appendix D. Decode")
    if start < 0 or end < 0:
        raise SystemExit("Could not locate Appendix C boundaries in JO 7360 source.")

    models: dict[str, list[str]] = {}
    active: tuple[str, str] | None = None
    pending_manufacturers: list[str] = []

    def add(designator: str, model: str, manufacturer: str) -> None:
        if not designator or not model or not manufacturer:
            return
        entry = f"{manufacturer}, {model}"
        bucket = models.setdefault(designator, [])
        if entry not in bucket:
            bucket.append(entry)

    def continuation_manufacturer(line: str) -> str:
        value = clean(line)
        if not value or len(value) > 42:
            return ""
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}|[A-Z]-\d+", value):
            return ""
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9 &'()./-]+", value):
            return ""
        if value in {
            "APPENDIX C", "CLASS", "ENGINE", "MANUFACTURER",
            "MODEL", "NUMBER-", "WEIGHT", "CWT SRS LAHSO",
        } or value.startswith("JO 7360"):
            return ""
        return value

    for line in text[start:end].splitlines():
        match = C_ROW_RE.match(line)
        if not match:
            manufacturer = continuation_manufacturer(line)
            if manufacturer:
                pending_manufacturers.append(manufacturer)
            continue

        prefix_parts = [
            clean(part) for part in re.split(r"\s{2,}", match.group("prefix").rstrip())
            if clean(part)
        ]
        model = prefix_parts[0] if prefix_parts else ""
        manufacturer = " ".join(prefix_parts[1:]) if len(prefix_parts) > 1 else ""

        if pending_manufacturers:
            target = (match.group("designator"), model) if not manufacturer else active
            if target:
                for pending in pending_manufacturers:
                    add(target[0], target[1], pending)
            pending_manufacturers = []

        active = (match.group("designator"), model)
        if manufacturer:
            add(active[0], active[1], manufacturer)

    if active:
        for pending in pending_manufacturers:
            add(active[0], active[1], pending)
    return models


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_weighted(
    path: Path,
    appendix: dict[str, dict[str, str]],
    models: dict[str, list[str]],
    *,
    drop_missing: bool,
) -> tuple[int, list[str]]:
    fieldnames, rows = read_csv(path)
    missing: list[str] = []
    changed = 0
    retained = []
    for row in rows:
        designator = clean(row.get("type_designator", "")).rstrip("*")
        current = appendix.get(designator)
        if not current:
            missing.append(designator)
            if not drop_missing:
                retained.append(row)
            continue
        before = tuple(row.get(key, "") for key in (*current, "manufacturer_model"))
        row.update(current)
        if models.get(designator):
            row["manufacturer_model"] = " ; ".join(models[designator])
        changed += before != tuple(row.get(key, "") for key in (*current, "manufacturer_model"))
        retained.append(row)
    if missing and not drop_missing:
        return changed, sorted(set(missing))
    write_csv(path, fieldnames, retained)
    return changed, []


def update_spoken(
    path: Path,
    appendix: dict[str, dict[str, str]],
    *,
    drop_missing: bool,
) -> tuple[int, list[str]]:
    fieldnames, rows = read_csv(path)
    missing: list[str] = []
    changed = 0
    retained = []
    for row in rows:
        designator = clean(row.get("ICAO", "")).rstrip("*")
        current = appendix.get(designator)
        if not current:
            missing.append(designator)
            if not drop_missing:
                retained.append(row)
            continue
        updates = {
            "CWT": current["cwt"],
            "SRS": current["srs"],
        }
        before = tuple(row.get(key, "") for key in updates)
        row.update(updates)
        changed += before != tuple(row.get(key, "") for key in updates)
        retained.append(row)
    if missing and not drop_missing:
        return changed, sorted(set(missing))
    write_csv(path, fieldnames, retained)
    return changed, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="JO 7360.1K PDF or pdftotext -layout output")
    parser.add_argument("--weighted", type=Path, default=DEFAULT_WEIGHTED)
    parser.add_argument("--spoken", type=Path, default=DEFAULT_SPOKEN)
    parser.add_argument(
        "--drop-missing",
        action="store_true",
        help="Remove selected designators that no longer appear in the current order.",
    )
    args = parser.parse_args()

    text = source_text(args.source)
    appendix = parse_appendix_a(text)
    models = parse_appendix_c_models(text)
    weighted_changed, weighted_missing = update_weighted(
        args.weighted, appendix, models, drop_missing=args.drop_missing
    )
    spoken_changed, spoken_missing = update_spoken(
        args.spoken, appendix, drop_missing=args.drop_missing
    )
    missing = sorted(set(weighted_missing + spoken_missing))
    if missing:
        print("Unmatched selected designators: " + ", ".join(missing))
        return 1
    print(
        f"Parsed {len(appendix)} JO 7360.1K designators and "
        f"{len(models)} model groups; "
        f"updated {weighted_changed} weighted rows and {spoken_changed} spoken rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
