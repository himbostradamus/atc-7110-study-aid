#!/usr/bin/env python3
"""Report process, output, and validation state for remediation agents."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "remediation" / "latest_registry.json"
)


def process_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def exit_marker(log_path: Path) -> str | None:
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    marker = "__CLAUDE_EXIT_CODE__"
    position = text.rfind(marker)
    if position < 0:
        return None
    return text[position + len(marker):].splitlines()[0].strip()


def api_error(log_path: Path) -> bool:
    if not log_path.exists():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return "API Error:" in text or '"authentication_error"' in text


def validate(packet: Path, manifest: Path) -> str:
    result = subprocess.run(
        [
            "python",
            "scripts/validate_content_remediation_manifest.py",
            "--packet",
            str(packet),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    summary = result.stdout.strip().splitlines()
    return summary[-1] if summary else f"validator exit {result.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    if not args.registry.exists():
        parser.error(f"registry not found: {args.registry}")
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    for agent in registry.get("agents", []):
        pid = agent.get("pid")
        log_path = Path(agent["log"])
        manifest = Path(agent["output_json"])
        running = process_running(pid)
        marker = exit_marker(log_path)
        failed_api = api_error(log_path)
        if manifest.exists():
            result = validate(Path(agent["packet"]), manifest)
        else:
            result = "no manifest"
        print(
            f"chapter {agent['chapter']:02d} "
            f"pid={pid or '-'} running={'yes' if running else 'no'} "
            f"exit={marker or '-'} api_error={'yes' if failed_api else 'no'} "
            f"output={'yes' if manifest.exists() else 'no'} "
            f"{result}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
