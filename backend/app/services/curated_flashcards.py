"""
Curated flashcard overrides.
"""

from __future__ import annotations

import copy
import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TABLE_1_2_1_MOCHI_CSV = DATA_DIR / "curated_flashcards_tbl_1_2_1_mochi_bidirectional.csv"
AIRCRAFT_DESIGNATORS_CSV = DATA_DIR / "curated_aircraft_designators.csv"
AIRCRAFT_WEIGHTED_ROWS_CSV = DATA_DIR / "curated_aircraft_jo7360_weighted_rows.csv"

LONG_REVERSE_FRONTS = {
    "Ambiguity−A disparity greater than a locally adapted distance exists between the position declared for a target by MEARTS and another facility’s computer declared position during interfacility handoff": "Which abbreviation is used for the MEARTS interfacility handoff Ambiguity-A disparity condition?",
    "Ambiguity−A disparity greater than a locally adapted distance exists between the position declared for a target by STARS and another facility’s computer declared position during interfacility handoff": "Which abbreviation is used for the STARS interfacility handoff Ambiguity-A disparity condition?",
}


def _append_unique(items: list[dict], seen: set[tuple[str, str]], front: str, back: str, card_type: str = "definition") -> None:
    key = (front, back)
    if key in seen:
        return
    seen.add(key)
    items.append({
        "front": front,
        "back": back,
        "card_type": card_type,
        "generation_source": "curated",
    })


def _append_aircraft_card(
    items: list[dict],
    seen: set[tuple[str, str]],
    front: str,
    back: str,
    card_type: str,
    generation_source: str,
) -> None:
    before = len(items)
    _append_unique(items, seen, front, back, card_type)
    if len(items) > before:
        items[-1]["generation_source"] = generation_source


def _default_generation_source(path: Path, payload: dict) -> str:
    explicit = payload.get("generation_source") or payload.get("generation_src")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    if "deepseek" in path.name.lower():
        return "deepseek"
    return "curated"


def _with_default_generation_source(override: dict, generation_source: str) -> dict:
    copied = copy.deepcopy(override)
    copied.setdefault("generation_source", generation_source)
    for item in copied.get("items", []):
        if isinstance(item, dict):
            item.setdefault("generation_source", copied["generation_source"])
    return copied


def _load_table_1_2_1_mochi_override() -> dict[str, dict]:
    if not TABLE_1_2_1_MOCHI_CSV.exists():
        return {}

    abbr_to_meanings: dict[str, list[str]] = {}

    with TABLE_1_2_1_MOCHI_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) != 2:
                continue
            left = row[0].strip()
            right = row[1].strip()
            if not left or not right:
                continue

            # The source CSV is bidirectional, so the shorter side is the table abbreviation.
            if len(left) > len(right):
                continue

            meanings = abbr_to_meanings.setdefault(left, [])
            if right not in meanings:
                meanings.append(right)

    items: list[dict] = []
    seen_cards: set[tuple[str, str]] = set()

    for abbr in sorted(abbr_to_meanings):
        meanings = abbr_to_meanings[abbr]
        if len(meanings) == 1:
            forward_front = f"What does {abbr} stand for?"
            forward_back = meanings[0]
        else:
            forward_front = f"What can {abbr} stand for in FAA Order JO 7110.65?"
            forward_back = "; ".join(meanings)
        _append_unique(items, seen_cards, forward_front, forward_back)

        for meaning in meanings:
            reverse_front = LONG_REVERSE_FRONTS.get(
                meaning,
                f"Which abbreviation stands for {meaning}?",
            )
            _append_unique(items, seen_cards, reverse_front, abbr)

    _append_unique(
        items,
        seen_cards,
        "When an abbreviation in TBL 1-2-1 has more than one listed meaning, how does a controller determine which meaning applies?",
        (
            "Use the operational context. For example, AAR paired with a numeric "
            "flow value means Airport Arrival Rate, while AAR in a route description "
            "means Adapted Arrival Route. List order does not determine meaning."
        ),
        "concept",
    )

    return {"1-2-6": {"replace_all": True, "items": items}}


def _load_aircraft_designator_overrides() -> dict[str, dict]:
    if not AIRCRAFT_DESIGNATORS_CSV.exists():
        return {}

    rows: list[dict] = []
    with AIRCRAFT_DESIGNATORS_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            icao = (row.get("ICAO") or "").strip()
            spoken = (row.get("SpokenName") or "").strip()
            srs = (row.get("SRS") or "").strip()
            cwt = (row.get("CWT") or "").strip()
            manufacturer = (row.get("Manufacturer") or "").strip()
            if not icao or not spoken:
                continue
            rows.append({
                "icao": icao,
                "spoken": spoken,
                "cwt": cwt,
                "srs": srs,
                "manufacturer": manufacturer,
            })

    if not rows:
        return {}

    spoken_to_rows: dict[str, list[dict]] = {}
    for row in rows:
        spoken_to_rows.setdefault(row["spoken"], []).append(row)

    type_items: list[dict] = []
    srs_items: list[dict] = []
    seen_cards: set[tuple[str, str]] = set()
    generation_source = "aircraft_jo7360"

    for row in sorted(rows, key=lambda item: item["icao"]):
        facts = [
            row["spoken"],
            f"Mfr {row['manufacturer']}" if row["manufacturer"] else "",
            f"CWT {row['cwt']}" if row["cwt"] else "",
            f"SRS {row['srs']}" if row["srs"] else "",
            "JO 7360.1K Appendix A",
        ]
        _append_aircraft_card(
            type_items,
            seen_cards,
            row["icao"],
            " · ".join(part for part in facts if part),
            "aircraft_designator",
            generation_source,
        )

        if row["srs"]:
            _append_aircraft_card(
                srs_items,
                seen_cards,
                f"{row['icao']} · SRS",
                f"{row['srs']} · {row['spoken']} · JO 7360.1K Appendix A",
                "aircraft_srs",
                generation_source,
            )

    for spoken in sorted(spoken_to_rows):
        entries = []
        for row in sorted(spoken_to_rows[spoken], key=lambda item: item["icao"]):
            details = [
                row["icao"],
                f"CWT {row['cwt']}" if row["cwt"] else "",
                f"SRS {row['srs']}" if row["srs"] else "",
            ]
            entries.append(" · ".join(part for part in details if part))
        _append_aircraft_card(
            type_items,
            seen_cards,
            spoken,
            f"{'; '.join(entries)} · JO 7360.1K Appendix A",
            "aircraft_designator",
            generation_source,
        )

    return {
        "2-3-6": {
            "replace_all": False,
            "generation_source": generation_source,
            "items": type_items,
        },
        "3-9-6": {
            "replace_all": False,
            "generation_source": generation_source,
            "items": srs_items,
        },
    }


def _clean_aircraft_value(value: str) -> str:
    return " ".join(str(value or "").replace("~", "").split())


def _trailing_manufacturer_start(value: str) -> int:
    stripped = value.rstrip()
    end = len(stripped)
    start_of_phrase: Optional[int] = None

    while end > 0:
        token_start = stripped.rfind(" ", 0, end) + 1
        token = stripped[token_start:end].strip(" .()/-+&'")
        is_manufacturer_word = (
            bool(token)
            and token.upper() == token
            and any(character.isalpha() for character in token)
            and not any(character.isdigit() for character in token)
        )
        if not is_manufacturer_word:
            break
        start_of_phrase = token_start
        end = token_start - 1
        while end > 0 and stripped[end] == " ":
            end -= 1

    return start_of_phrase if start_of_phrase is not None else len(stripped)


def _normalize_aircraft_maker(value: str) -> str:
    maker = _clean_aircraft_value(value).strip(" ,;")
    if not maker:
        return ""
    title = maker.title()
    aliases = {
        "Beech": "Beechcraft",
        "Beech Aircraft": "Beechcraft",
        "Hawker Beechcraft": "Beechcraft",
        "Raytheon": "Beechcraft",
        "Piper Aircraft": "Piper",
        "Piper": "Piper",
        "Cessna": "Cessna",
        "Mcdonnell Douglas": "McDonnell Douglas",
        "Md Helicopters": "MD Helicopters",
    }
    return aliases.get(title, title)


def _weighted_manufacturers(value: str) -> list[str]:
    cleaned = _clean_aircraft_value(value).replace(" ; ", "; ")
    if not cleaned:
        return []

    makers: list[str] = []
    seen: set[str] = set()
    semicolon_parts = [part.strip() for part in cleaned.split(";") if part.strip()]
    if len(semicolon_parts) > 1:
        candidates = [
            part.split(",", 1)[0].strip()
            for part in semicolon_parts
            if "," in part
        ]
    else:
        candidates = []
        for comma_index, character in enumerate(cleaned):
            if character != ",":
                continue
            before_comma = cleaned[:comma_index].rstrip()
            maker_start = _trailing_manufacturer_start(before_comma)
            candidates.append(before_comma[maker_start:].strip())

    for candidate in candidates:
        maker = _normalize_aircraft_maker(candidate)
        if not maker or maker in seen:
            continue
        seen.add(maker)
        makers.append(maker)
        if len(makers) == 5:
            break
    return makers


def _split_weighted_model_entries(value: str) -> list[str]:
    cleaned = _clean_aircraft_value(value).replace(" ; ", "; ")
    semicolon_parts = [part.strip() for part in cleaned.split(";") if part.strip()]
    if len(semicolon_parts) > 1:
        entries: list[str] = []
        for part in semicolon_parts:
            if "," not in part:
                entries.append(part)
                continue
            maker, models = part.split(",", 1)
            maker = _clean_aircraft_value(maker)
            models = _clean_aircraft_value(models)
            split_models = re.split(rf"\s+{re.escape(maker)}\s*,\s*", models, flags=re.I) if maker else [models]
            for model in split_models:
                model = _clean_aircraft_value(model)
                if not model:
                    continue
                if re.fullmatch(r"\d+[A-Z]?", model, flags=re.I):
                    model = f"{_normalize_aircraft_maker(maker) or maker} {model}".strip()
                entries.append(model)
        return entries

    commas = [index for index, character in enumerate(cleaned) if character == ","]
    if not commas:
        return [cleaned] if cleaned else []

    entries: list[str] = []
    for index, comma_index in enumerate(commas):
        model_start = comma_index + 1
        before_comma = cleaned[:comma_index].rstrip()
        maker_start = _trailing_manufacturer_start(before_comma)
        maker = _normalize_aircraft_maker(before_comma[maker_start:].strip())
        if index + 1 < len(commas):
            next_comma = commas[index + 1]
            before_next = cleaned[:next_comma].rstrip()
            model_end = _trailing_manufacturer_start(before_next)
            next_maker_start = _trailing_manufacturer_start(before_next)
            next_maker = _normalize_aircraft_maker(before_next[next_maker_start:].strip())
            maker = next_maker or maker
        else:
            model_end = len(cleaned)
        entry = cleaned[model_start:model_end].strip()
        if re.fullmatch(r"\d+[A-Z]?", entry, flags=re.I) and maker:
            entry = f"{maker} {entry}"
        if entry:
            entries.append(entry)
    return entries


def _compact_model_label(value: str, max_len: int = 76) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for part in _split_weighted_model_entries(value):
        short = part.strip()
        if "," in short:
            before_comma, after_comma = short.split(",", 1)
            short = after_comma.strip()
            if re.fullmatch(r"\d+[A-Z]?", short, flags=re.I):
                maker_start = _trailing_manufacturer_start(before_comma)
                maker = _normalize_aircraft_maker(before_comma[maker_start:].strip())
                if maker:
                    short = f"{maker} {short}"
        short = _clean_aircraft_value(short)
        if not short or short in seen:
            continue
        seen.add(short)
        parts.append(short)
        if len(parts) == 2:
            break

    label = " / ".join(parts) if parts else _clean_aircraft_value(value)
    if len(label) <= max_len:
        return label
    return f"{label[:max_len - 1].rstrip()}…"


def _weighted_back(row: dict, include_models: bool = True) -> str:
    parts = []
    if include_models:
        parts.append(_compact_model_label(row.get("manufacturer_model", ""), 96))
    if row.get("wtc"):
        parts.append(f"Wake {row['wtc']}")
    if row.get("cwt"):
        parts.append(f"CWT {row['cwt']}")
    if row.get("srs"):
        parts.append(f"SRS {row['srs']}")
    if row.get("engine_aircraft_class"):
        parts.append(f"Engine {row['engine_aircraft_class']}")
    if row.get("lahso"):
        parts.append(f"LAHSO {row['lahso']}")
    if row.get("makers"):
        parts.append(f"Mfr {' / '.join(row['makers'])}")
    parts.append("JO 7360.1K Appendix A")
    return " · ".join(_clean_aircraft_value(part) for part in parts if _clean_aircraft_value(part))


def _load_weighted_aircraft_designator_overrides() -> dict[str, dict]:
    if not AIRCRAFT_WEIGHTED_ROWS_CSV.exists():
        return {}

    rows: list[dict] = []
    with AIRCRAFT_WEIGHTED_ROWS_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            designator = _clean_aircraft_value(row.get("type_designator", ""))
            models = _clean_aircraft_value(row.get("manufacturer_model", ""))
            if not designator or not models:
                continue
            rows.append({
                "designator": designator,
                "models": models,
                "model_label": _compact_model_label(models),
                "family": _clean_aircraft_value(row.get("group", "")).title(),
                "makers": _weighted_manufacturers(models),
                "description": _clean_aircraft_value(row.get("description", "")),
                "engine_aircraft_class": _clean_aircraft_value(row.get("engine_aircraft_class", "")),
                "wtc": _clean_aircraft_value(row.get("wtc", "")),
                "cwt": _clean_aircraft_value(row.get("cwt", "")),
                "srs": _clean_aircraft_value(row.get("srs", "")),
                "lahso": _clean_aircraft_value(row.get("lahso", "")),
                "manufacturer_model": models,
            })

    if not rows:
        return {}

    generation_source = "aircraft_jo7360"
    type_items: list[dict] = []
    srs_items: list[dict] = []
    seen_cards: set[tuple[str, str]] = set()

    for row in sorted(rows, key=lambda item: item["designator"]):
        _append_aircraft_card(
            type_items,
            seen_cards,
            row["designator"],
            _weighted_back(row),
            "aircraft_designator",
            generation_source,
        )
        _append_aircraft_card(
            type_items,
            seen_cards,
            row["model_label"],
            f"{row['designator']} · {_weighted_back(row, include_models=False)}",
            "aircraft_model",
            generation_source,
        )
        if row["srs"]:
            srs_parts = [
                row["srs"],
                row["model_label"],
                f"Mfr {' / '.join(row['makers'])}" if row.get("makers") else "",
                "JO 7360.1K Appendix A",
            ]
            _append_aircraft_card(
                srs_items,
                seen_cards,
                f"{row['designator']} · SRS",
                " · ".join(part for part in srs_parts if part),
                "aircraft_srs",
                generation_source,
            )

    return {
        "2-3-6": {
            "replace_all": False,
            "generation_source": generation_source,
            "items": type_items,
        },
        "3-9-6": {
            "replace_all": False,
            "generation_source": generation_source,
            "items": srs_items,
        },
    }


_GENERIC_AIRCRAFT_MAKERS = {
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


def _aircraft_item_quality(item: dict) -> int:
    if item.get("generation_source") != "aircraft_jo7360":
        return 0
    if item.get("card_type") != "aircraft_designator":
        return 0

    back = str(item.get("back") or "")
    first_fact = ""
    for part in re.split(r"\n|·", back):
        part = _clean_aircraft_value(part)
        if not part or re.match(r"^(Mfr|CWT|SRS|Wake|Engine|LAHSO|JO\s*7360)", part, flags=re.I):
            continue
        if re.fullmatch(r"[A-Z0-9]{2,5}", part, flags=re.I):
            continue
        first_fact = part
        break

    score = 0
    if first_fact and first_fact.lower() not in _GENERIC_AIRCRAFT_MAKERS:
        score += 10
    if re.search(r"\bWake\s+", back, flags=re.I):
        score += 2
    if re.search(r"\bEngine\s+", back, flags=re.I):
        score += 2
    if re.search(r"\bLAHSO\s+", back, flags=re.I):
        score += 1
    return score


@lru_cache(maxsize=1)
def load_curated_flashcard_overrides() -> dict[str, dict]:
    merged: dict[str, dict] = {}

    for path in sorted(DATA_DIR.glob("curated_flashcards_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        section = payload.get("flashcards", {})
        if not isinstance(section, dict):
            continue
        generation_source = _default_generation_source(path, payload)
        for para_id, override in section.items():
            if not isinstance(override, dict):
                continue
            override = _with_default_generation_source(override, generation_source)
            if override.get("replace_all") or para_id not in merged:
                merged[para_id] = copy.deepcopy(override)
                continue

            combined = copy.deepcopy(merged[para_id])
            items = combined.setdefault("items", [])
            items.extend(copy.deepcopy(override.get("items", [])))
            merged[para_id] = combined

    for para_id, override in _load_table_1_2_1_mochi_override().items():
        merged[para_id] = copy.deepcopy(override)

    for para_id, override in _load_aircraft_designator_overrides().items():
        if para_id not in merged:
            merged[para_id] = copy.deepcopy(override)
            continue
        combined = copy.deepcopy(merged[para_id])
        combined.setdefault("items", []).extend(copy.deepcopy(override.get("items", [])))
        merged[para_id] = combined

    for para_id, override in _load_weighted_aircraft_designator_overrides().items():
        if para_id not in merged:
            merged[para_id] = copy.deepcopy(override)
            continue
        combined = copy.deepcopy(merged[para_id])
        combined.setdefault("items", []).extend(copy.deepcopy(override.get("items", [])))
        merged[para_id] = combined

    for override in merged.values():
        items = override.get("items", [])
        if not isinstance(items, list):
            continue
        deduped: list[dict] = []
        seen_index: dict[tuple[str, str], int] = {}
        for item in items:
            if not isinstance(item, dict):
                deduped.append(item)
                continue
            key = (str(item.get("card_type") or ""), str(item.get("front") or ""))
            if key in seen_index:
                existing_index = seen_index[key]
                existing = deduped[existing_index]
                if isinstance(existing, dict) and _aircraft_item_quality(item) > _aircraft_item_quality(existing):
                    deduped[existing_index] = item
                continue
            seen_index[key] = len(deduped)
            deduped.append(item)
        override["items"] = deduped

    return merged


def get_curated_flashcard_override(para_id: str) -> Optional[dict]:
    override = load_curated_flashcard_overrides().get(para_id)
    return copy.deepcopy(override) if override else None
