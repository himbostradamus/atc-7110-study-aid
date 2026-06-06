#!/usr/bin/env python3
"""Audit JO 7360 aircraft flashcard facts for weak or generic labels."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


GENERIC_MAKERS = {
    "aero commander",
    "airbus",
    "beechcraft",
    "bell",
    "boeing",
    "bombardier",
    "canadair",
    "cessna",
    "cirrus",
    "dassault",
    "de havilland canada",
    "embraer",
    "gulfstream",
    "learjet",
    "mcdonnell douglas",
    "mooney",
    "pilatus",
    "piper",
    "piper aircraft",
}


def clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def pieces(back: str) -> list[str]:
    return [clean(part) for part in re.split(r"\n|·", back or "") if clean(part)]


def first_model_fact(back: str) -> str:
    for part in pieces(back):
        if re.match(r"^(Mfr|CWT|SRS|Wake|Engine|LAHSO|JO\s*7360)", part, flags=re.I):
            continue
        if re.fullmatch(r"[A-Z0-9]{2,5}", part, flags=re.I):
            continue
        return part
    return ""


def load_weighted_labels(path: Path) -> dict[str, str]:
    labels = {}
    if not path.exists():
        return labels
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            designator = clean(row.get("type_designator")).upper()
            models = clean(row.get("manufacturer_model"))
            if not designator or not models:
                continue
            model_parts = []
            for entry in expanded_model_entries(models):
                entry = clean(entry)
                if not entry:
                    continue
                if "," in entry:
                    before_comma, after_comma = entry.split(",", 1)
                    label = clean(after_comma)
                    if re.fullmatch(r"\d+[A-Z]?", label, flags=re.I):
                        maker_match = re.search(r"([A-Z][A-Z0-9 .&/-]*)$", before_comma.strip())
                        if maker_match:
                            label = f"{maker_match.group(1).title()} {label}"
                else:
                    label = entry
                model_parts.append(clean(label))
                if len(model_parts) == 2:
                    break
            labels[designator] = " / ".join(model_parts) if model_parts else models
    return labels


def expanded_model_entries(value: str) -> list[str]:
    cleaned = clean(value).replace(" ; ", "; ")
    entries = []
    for part in [item.strip() for item in cleaned.split(";") if item.strip()]:
        if "," not in part:
            entries.append(part)
            continue
        maker, models = part.split(",", 1)
        maker = clean(maker)
        split_models = re.split(rf"\s+{re.escape(maker)}\s*,\s*", clean(models), flags=re.I) if maker else [models]
        for model in split_models:
            model = clean(model)
            if not model:
                continue
            if re.fullmatch(r"\d+[A-Z]?", model, flags=re.I):
                model = f"{maker.title()} {model}".strip()
            entries.append(model)
    return entries


def audit(db_path: Path, weighted_rows: Path) -> list[dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT id, front, back, card_type
        FROM flashcards
        WHERE generation_src = 'aircraft_jo7360'
          AND card_type = 'aircraft_designator'
        ORDER BY front, id
        """
    ).fetchall()
    con.close()

    weighted_labels = load_weighted_labels(weighted_rows)
    by_key = defaultdict(list)
    for row in rows:
        by_key[(row["card_type"], row["front"])].append(dict(row))

    findings = []
    for (_, front), cards in by_key.items():
        if not re.fullmatch(r"[A-Z0-9]{2,5}", front or ""):
            continue
        for card in cards:
            model = first_model_fact(card["back"])
            reasons = []
            if not model:
                reasons.append("missing_model_label")
            elif model.lower() in GENERIC_MAKERS:
                reasons.append("generic_manufacturer_as_model")
            if len(cards) > 1:
                reasons.append("duplicate_designator_card")
            if reasons:
                findings.append({
                    "type_designator": front,
                    "card_id": card["id"],
                    "current_model_label": model,
                    "suggested_model_label": weighted_labels.get(front, ""),
                    "reasons": reasons,
                    "back": card["back"],
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("frontend/public/curriculum.db"))
    parser.add_argument("--weighted-rows", type=Path, default=Path("backend/app/data/curated_aircraft_jo7360_weighted_rows.csv"))
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    findings = audit(args.db, args.weighted_rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"findings": findings}, indent=2) + "\n", encoding="utf-8")
    for item in findings[:80]:
        print(f"{item['type_designator']}: {', '.join(item['reasons'])} current={item['current_model_label']!r} suggested={item['suggested_model_label']!r}")
    print(f"Findings: {len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
