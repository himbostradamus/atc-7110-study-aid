#!/usr/bin/env python3
"""Prepare or launch one DeepSeek content-expansion agent per chapter."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from export_content_remediation_packets import parse_chapters


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "expansion"
)
STAGING = ROOT / "backend" / "app" / "data" / "content_expansion_staging"
PROMPT_TEMPLATE = ROOT / "docs" / "content-expansion-agent-prompt.md"
HARNESS = ROOT / "docs" / "content-expansion-agent-harness.md"
WRITING_HARNESS = ROOT / "docs" / "question-writing-agent-harness.md"
DEFAULT_VENV = Path("/home/perfect-vacuum/python_env/python_environment/bin/activate")
DEFAULT_DEEPSEEK_SETUP = Path("/home/perfect-vacuum/scripts/use-deepseek-claude-code.sh")
DEFAULT_CLAUDE = Path("/home/perfect-vacuum/.nvm/versions/node/v22.16.0/bin/claude")
LOCAL_AGENT_ENV = ROOT / ".env.agent.local"


def build_prompt(chapter: int, packet: Path, output: Path) -> str:
    base = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    remediation = (
        ROOT / "backend" / "app" / "data" / "content_remediation"
        / f"chapter_{chapter:02d}.json"
    )
    return f"""{base}

## Assigned Chapter

Chapter: `{chapter}`

Source and current-content packet:

```text
{packet}
```

Prior remediation findings and generation guidance:

```text
{remediation}
```

Required staging output:

```text
{output}
```

Validator:

```bash
python scripts/validate_question_authoring_batch.py \
  {shlex.quote(str(output))} --db frontend/public/curriculum.db
```

Read `{HARNESS}` and `{WRITING_HARNESS}` before authoring. Write only the
assigned staging file. Finish the full chapter before exiting.
"""


def launch_agent(prompt_path: Path, log_path: Path) -> subprocess.Popen:
    log_handle = log_path.open("w", encoding="utf-8")
    custom = os.environ.get("ATC_EXPANSION_AGENT_COMMAND")
    setup = custom or (
        f"if [ -f {shlex.quote(str(LOCAL_AGENT_ENV))} ]; then "
        f"set -a; source {shlex.quote(str(LOCAL_AGENT_ENV))}; set +a; fi && "
        f"if [ -z \"$DEEPSEEK_API_KEY\" ]; then "
        f"source {shlex.quote(str(DEFAULT_VENV))}; fi && "
        f"source {shlex.quote(str(DEFAULT_DEEPSEEK_SETUP))} >/dev/null && "
        f"{shlex.quote(str(DEFAULT_CLAUDE))}"
    )
    command = (
        f"{setup} --print --verbose --output-format stream-json "
        "--allowedTools Bash,View,Write,Edit,Glob,Grep,LS,BatchTool "
        f"< {shlex.quote(str(prompt_path))}; "
        'status=$?; echo "__CLAUDE_EXIT_CODE__${status}"; exit "$status"'
    )
    return subprocess.Popen(
        ["bash", "-lc", f"tail -f /dev/null | script -qfec {shlex.quote(command)} /dev/null"],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        cwd=ROOT,
        env=os.environ.copy(),
        start_new_session=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-14")
    parser.add_argument("--pass-number", type=int, default=1)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompts_dir = WORKSPACE / "prompts"
    logs_dir = WORKSPACE / "logs"
    packets_dir = WORKSPACE / "packets"
    for directory in (prompts_dir, logs_dir, packets_dir, STAGING):
        directory.mkdir(parents=True, exist_ok=True)

    entries = []
    for chapter in parse_chapters(args.chapters):
        packet = packets_dir / f"chapter_{chapter:02d}.json"
        if not packet.exists():
            parser.error(f"missing expansion packet: {packet}")
        output = STAGING / f"chapter_{chapter:02d}_pass_{args.pass_number:02d}.json"
        if output.exists():
            parser.error(f"refusing to overwrite {output}")
        stem = f"chapter_{chapter:02d}_pass_{args.pass_number:02d}"
        prompt = prompts_dir / f"{stem}_{timestamp}.md"
        log = logs_dir / f"{stem}_{timestamp}.log"
        prompt.write_text(build_prompt(chapter, packet.resolve(), output.resolve()), encoding="utf-8")
        entry = {
            "chapter": chapter,
            "pass": args.pass_number,
            "packet": str(packet.resolve()),
            "prompt": str(prompt.resolve()),
            "log": str(log.resolve()),
            "output": str(output.resolve()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "pid": None,
        }
        if args.run:
            process = launch_agent(prompt, log)
            entry["pid"] = process.pid
            print(f"started chapter {chapter:02d} pid={process.pid} log={log}")
        else:
            print(f"prepared chapter {chapter:02d}: {prompt}")
        entries.append(entry)

    registry = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run": args.run,
        "agents": entries,
    }
    registry_path = WORKSPACE / f"agent_registry_{timestamp}.json"
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    (WORKSPACE / "latest_registry.json").write_text(
        json.dumps(registry, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"registry={registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
