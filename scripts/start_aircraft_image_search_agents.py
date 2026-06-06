#!/usr/bin/env python3
"""Prepare or launch claude-deepseek aircraft image search agents."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = REPO_ROOT / "backend/app/data/aircraft_image_search_workspace"
PROMPT_TEMPLATE = REPO_ROOT / "docs/aircraft-image-search-agent-prompt.md"


def slug_for_packet(packet_path: Path) -> str:
    stem = packet_path.stem.replace("aircraft_image_targets_", "")
    return stem


def read_packet(packet_path: Path) -> dict:
    return json.loads(packet_path.read_text(encoding="utf-8"))


def build_prompt(packet_path: Path, output_dir: Path) -> str:
    packet = read_packet(packet_path)
    type_list = ",".join(row["type_designator"] for row in packet.get("rows", []))
    base_prompt = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return f"""{base_prompt}

## Assigned Packet

Packet path:

```text
{packet_path.as_posix()}
```

Output directory:

```text
{output_dir.as_posix()}
```

Assigned type designators:

```text
{type_list}
```

Use this exact output directory. Do not write to the live frontend image manifest.
"""


def launch_agent(prompt_path: Path, log_path: Path) -> subprocess.Popen:
    env = os.environ.copy()
    log_handle = log_path.open("w", encoding="utf-8")
    agent_command = shlex.join(
        shlex.split(os.environ.get("ATC_AGENT_COMMAND", "claude-deepseek"))
    )
    claude_command = (
        f"{agent_command} --print --output-format stream-json "
        "--allowedTools Bash,View,Write,Edit,Glob,Grep,LS,BatchTool "
        f"< {shlex.quote(prompt_path.as_posix())}; "
        'status=$?; echo "__CLAUDE_EXIT_CODE__${status}"; exit "$status"'
    )
    return subprocess.Popen(
        [
            "bash",
            "-lc",
            f"tail -f /dev/null | script -qfec {shlex.quote(claude_command)} /dev/null",
        ],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        cwd=REPO_ROOT,
        env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-glob", default="aircraft_image_targets_*.json")
    parser.add_argument("--max-agents", type=int, default=4)
    parser.add_argument("--run", action="store_true", help="Launch claude-deepseek. Default only writes prompts and prints commands.")
    args = parser.parse_args()

    packets = sorted((WORKSPACE / "packets").glob(args.packet_glob))[: args.max_agents]
    if not packets:
        print("No packets found. Run scripts/export_aircraft_image_agent_packet.py first.")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processes = []
    for packet_path in packets:
        slug = slug_for_packet(packet_path)
        output_dir = WORKSPACE / "outputs" / slug
        output_dir.mkdir(parents=True, exist_ok=True)
        (WORKSPACE / "prompts").mkdir(parents=True, exist_ok=True)
        (WORKSPACE / "logs").mkdir(parents=True, exist_ok=True)
        prompt_path = WORKSPACE / "prompts" / f"{slug}_{timestamp}.md"
        log_path = WORKSPACE / "logs" / f"{slug}_{timestamp}.log"
        prompt_path.write_text(build_prompt(packet_path, output_dir), encoding="utf-8")

        if args.run:
            proc = launch_agent(prompt_path, log_path)
            processes.append((slug, proc.pid, log_path))
            print(f"started {slug} pid={proc.pid} log={log_path}")
        else:
            print(f"prompt={prompt_path}")
            print(f"dry-run command: claude-deepseek < {prompt_path} > {log_path} 2>&1")

    if processes:
        print("Agents launched:")
        for slug, pid, log_path in processes:
            print(f"{slug}: pid={pid} log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
