#!/usr/bin/env python3
"""Report process and report-validation state for expansion audit agents."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = (
    ROOT
    / "backend"
    / "app"
    / "data"
    / "question_authoring_workspace"
    / "expansion_audits"
    / "latest_registry.json"
)


def process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def log_state(log_path: Path) -> tuple[str | None, bool]:
    if not log_path.exists():
        return None, False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    marker = "__CLAUDE_EXIT_CODE__"
    position = text.rfind(marker)
    exit_code = None
    if position >= 0:
        exit_code = text[position + len(marker) :].splitlines()[0].strip()
    api_error = "API Error:" in text or '"authentication_error"' in text
    return exit_code, api_error


def validate(batch: Path, report: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_content_expansion_audit.py",
            "--batch",
            str(batch),
            "--report",
            str(report),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return result.returncode == 0, (
        lines[-1] if lines else f"validator exit {result.returncode}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--fail-incomplete", action="store_true")
    args = parser.parse_args()
    if not args.registry.exists():
        parser.error(f"registry not found: {args.registry}")

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    failed = False
    incomplete = False
    for agent in registry.get("agents", []):
        running = process_running(agent.get("pid"))
        exit_code, api_error = log_state(Path(agent["log"]))
        report_json = Path(agent["report_json"])
        report_md = Path(agent["report_md"])
        valid = False
        if report_json.exists() and not running:
            valid, validation = validate(Path(agent["batch"]), report_json)
        elif report_json.exists():
            validation = "pending"
        else:
            validation = "no report"

        if not running and (
            exit_code != "0"
            or not report_json.exists()
            or not report_md.exists()
            or not valid
        ):
            failed = True
        if running or not valid:
            incomplete = True

        verdict = "-"
        findings = "-"
        if report_json.exists():
            try:
                report = json.loads(report_json.read_text(encoding="utf-8"))
                verdict = str(report.get("verdict") or "-")
                report_findings = report.get("findings")
                findings = str(len(report_findings)) if isinstance(report_findings, list) else "?"
            except json.JSONDecodeError:
                validation = "invalid JSON"

        print(
            f"chapter {agent['chapter']:02d} pid={agent.get('pid') or '-'} "
            f"running={'yes' if running else 'no'} exit={exit_code or '-'} "
            f"api_error={'yes' if api_error else 'no'} "
            f"json={'yes' if report_json.exists() else 'no'} "
            f"md={'yes' if report_md.exists() else 'no'} "
            f"verdict={verdict} findings={findings} validation={validation}"
        )

    if failed or (args.fail_incomplete and incomplete):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
