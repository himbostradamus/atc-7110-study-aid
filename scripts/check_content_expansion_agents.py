#!/usr/bin/env python3
"""Report process, output, coverage, and validation state for expansion agents."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = (
    ROOT
    / "backend"
    / "app"
    / "data"
    / "question_authoring_workspace"
    / "expansion"
    / "latest_registry.json"
)
FAMILIES = ("questions", "activities", "flashcards")


def process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def log_text(log_path: Path) -> str:
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="replace")


def exit_marker(text: str) -> str | None:
    marker = "__CLAUDE_EXIT_CODE__"
    position = text.rfind(marker)
    if position < 0:
        return None
    return text[position + len(marker) :].splitlines()[0].strip()


def final_result(text: str) -> str:
    result = ""
    for line in text.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "result" and isinstance(payload.get("result"), str):
            result = payload["result"]
    return result


def reviewed_ids(text: str) -> set[str]:
    result = final_result(text)
    marker = "REVIEWED_IDS:"
    if marker in result:
        return set(re.findall(r"\b\d+-\d+-\d+[A-Za-z0-9-]*\b", result.split(marker, 1)[1]))

    # Older prompts requested a complete review table but did not name the
    # marker. Accept the final explicit review report, not IDs seen in tool
    # output or source packets.
    assistant_texts: list[str] = []
    for line in text.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "assistant":
            continue
        message = payload.get("message")
        if not isinstance(message, dict):
            continue
        parts = message.get("content")
        if not isinstance(parts, list):
            continue
        assistant_texts.extend(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("type") == "text"
        )
    for assistant_text in reversed(assistant_texts):
        if "paragraphs reviewed" in assistant_text.lower():
            return set(re.findall(r"\b\d+-\d+-\d+[A-Za-z0-9-]*\b", assistant_text))
    return set()


def item_count(container: Any) -> int:
    if not isinstance(container, dict):
        return 0
    total = 0
    for payload in container.values():
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            total += len(payload["items"])
    return total


def inspect_output(output_path: Path, packet_path: Path) -> dict[str, Any]:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    source_ids = {
        str(paragraph.get("para_id"))
        for paragraph in packet.get("paragraphs", [])
        if paragraph.get("para_id")
    }
    result: dict[str, Any] = {
        "exists": output_path.exists(),
        "parse_error": None,
        "counts": {family: 0 for family in FAMILIES},
        "covered": 0,
        "source": len(source_ids),
        "unknown": [],
    }
    if not output_path.exists():
        return result

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        result["parse_error"] = str(exc)
        return result

    output_ids: set[str] = set()
    for family in FAMILIES:
        container = payload.get(family)
        result["counts"][family] = item_count(container)
        if isinstance(container, dict):
            for para_id, para_payload in container.items():
                if (
                    isinstance(para_payload, dict)
                    and isinstance(para_payload.get("items"), list)
                    and para_payload["items"]
                ):
                    output_ids.add(str(para_id))

    result["covered"] = len(output_ids & source_ids)
    result["source"] = len(source_ids)
    result["unknown"] = sorted(output_ids - source_ids)
    return result


def validate(output_path: Path, *, strict: bool) -> tuple[bool, str]:
    command = [
        sys.executable,
        "scripts/validate_question_authoring_batch.py",
        str(output_path),
        "--db",
        "frontend/public/curriculum.db",
    ]
    if strict:
        command.append("--strict")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    summary = lines[-1] if lines else f"validator exit {result.returncode}"
    return result.returncode == 0, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--fail-incomplete",
        action="store_true",
        help="Return nonzero while any agent is running or lacks valid content.",
    )
    args = parser.parse_args()
    if not args.registry.exists():
        parser.error(f"registry not found: {args.registry}")

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    failed = False
    incomplete = False
    for agent in registry.get("agents", []):
        pid = agent.get("pid")
        running = process_running(pid)
        output_path = Path(agent["output"])
        packet_path = Path(agent["packet"])
        text = log_text(Path(agent["log"]))
        marker = exit_marker(text)
        api_error = "API Error:" in text or '"authentication_error"' in text
        output = inspect_output(output_path, packet_path)
        counts = output["counts"]
        total = sum(counts.values())
        reviewed = reviewed_ids(text)
        review_complete = (
            not agent.get("require_reviewed_ids")
            or len(reviewed) == output["source"]
        )

        validator = "pending"
        valid = False
        if output["parse_error"]:
            validator = f"invalid JSON: {output['parse_error']}"
        elif output["unknown"]:
            validator = f"foreign paragraph IDs: {','.join(output['unknown'])}"
        elif not running and marker == "0" and not review_complete:
            validator = (
                f"incomplete review evidence: {len(reviewed)}/{output['source']} IDs"
            )
        elif not running and marker == "0" and total:
            valid, validator = validate(
                output_path,
                strict=int(agent.get("pass") or 1) >= 2,
            )
        elif not running:
            validator = "no completed content" if not total else "agent exited unsuccessfully"

        if not running and (marker != "0" or not total or not valid):
            failed = True
        if running or not valid:
            incomplete = True

        print(
            f"chapter {agent['chapter']:02d} "
            f"pid={pid or '-'} running={'yes' if running else 'no'} "
            f"exit={marker or '-'} api_error={'yes' if api_error else 'no'} "
            f"items=q{counts['questions']}/a{counts['activities']}/"
            f"c{counts['flashcards']} "
            f"paragraphs={output['covered']}/{output['source']} "
            f"review={len(reviewed)}/{output['source']} "
            f"validation={validator}"
        )

    if failed or (args.fail_incomplete and incomplete):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
