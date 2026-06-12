#!/usr/bin/env python3
"""Prepare or launch one DeepSeek remediation agent per chapter."""

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
    / "remediation"
)
PROMPT_TEMPLATE = ROOT / "docs" / "content-remediation-agent-prompt.md"
HARNESS = ROOT / "docs" / "content-remediation-agent-harness.md"
DEFAULT_VENV = Path("/home/perfect-vacuum/python_env/python_environment/bin/activate")
DEFAULT_DEEPSEEK_SETUP = Path("/home/perfect-vacuum/scripts/use-deepseek-claude-code.sh")
DEFAULT_CLAUDE = Path(
    "/home/perfect-vacuum/.nvm/versions/node/v22.16.0/bin/claude"
)
LOCAL_AGENT_ENV = ROOT / ".env.agent.local"


def build_prompt(
    chapter: int,
    packet_path: Path,
    output_json: Path,
    output_markdown: Path,
) -> str:
    base = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    packet_display = packet_path.relative_to(ROOT)
    output_json_display = output_json.relative_to(ROOT)
    output_markdown_display = output_markdown.relative_to(ROOT)
    return f"""{base}

## Assigned Chapter

Chapter: `{chapter}`

Packet:

```text
{packet_display}
```

Required JSON manifest:

```text
{output_json_display}
```

Required Markdown summary:

```text
{output_markdown_display}
```

Validator command:

```bash
python scripts/validate_content_remediation_manifest.py \
  --packet {shlex.quote(str(packet_display))} \
  --manifest {shlex.quote(str(output_json_display))}
```

Read the harness at `{HARNESS}` before beginning. Use the exact output paths
above. Do not mark the manifest complete until every target item is reviewed and
the validator exits successfully.
"""


def launch_agent(prompt_path: Path, log_path: Path) -> subprocess.Popen:
    log_handle = log_path.open("w", encoding="utf-8")
    custom = os.environ.get("ATC_REMEDIATION_AGENT_COMMAND")
    if custom:
        setup = custom
    else:
        setup = (
            f"if [ -f {shlex.quote(str(LOCAL_AGENT_ENV))} ]; then "
            f"set -a; source {shlex.quote(str(LOCAL_AGENT_ENV))}; set +a; fi && "
            f"if [ -z \"$DEEPSEEK_API_KEY\" ]; then "
            f"source {shlex.quote(str(DEFAULT_VENV))}; fi && "
            f"source {shlex.quote(str(DEFAULT_DEEPSEEK_SETUP))} >/dev/null && "
            f"{shlex.quote(str(DEFAULT_CLAUDE))}"
        )
    allowed_tools = ",".join([
        "View",
        "Write(backend/app/data/question_authoring_workspace/remediation/**)",
        "Edit(backend/app/data/question_authoring_workspace/remediation/**)",
        "Glob",
        "Grep",
        "LS",
        "BatchTool",
        "Bash(python scripts/validate_content_remediation_manifest.py *)",
    ])
    disallowed_tools = ",".join([
        "Task",
        "TaskCreate",
        "TaskUpdate",
        "TaskList",
        "TaskGet",
        "AskUserQuestion",
        "WebFetch",
        "WebSearch",
        "NotebookEdit",
        "EnterPlanMode",
        "ExitPlanMode",
        "EnterWorktree",
        "ExitWorktree",
        "CronCreate",
        "CronDelete",
        "CronList",
        "ScheduleWakeup",
    ])
    command = (
        f"{setup} --print --verbose --output-format stream-json "
        f"--allowedTools {shlex.quote(allowed_tools)} "
        f"--disallowedTools {shlex.quote(disallowed_tools)} "
        f"< {shlex.quote(str(prompt_path))}; "
        'status=$?; echo "__CLAUDE_EXIT_CODE__${status}"; exit "$status"'
    )
    return subprocess.Popen(
        [
            "bash",
            "-lc",
            f"tail -f /dev/null | script -qfec {shlex.quote(command)} /dev/null",
        ],
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        cwd=ROOT,
        env=os.environ.copy(),
        start_new_session=True,
    )


def launch_chapter_worker(
    chapter: int,
    pass_number: int,
    packet_path: Path,
    shard_dir: Path,
    output_json: Path,
    output_markdown: Path,
    log_path: Path,
) -> subprocess.Popen:
    log_handle = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        [
            "python",
            "scripts/run_content_remediation_chapter.py",
            "--chapter",
            str(chapter),
            "--pass-number",
            str(pass_number),
            "--packet",
            str(packet_path),
            "--shard-dir",
            str(shard_dir),
            "--output-json",
            str(output_json),
            "--output-markdown",
            str(output_markdown),
        ],
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
    parser.add_argument("--target-source", default="question_agent")
    parser.add_argument("--packet-dir", type=Path)
    parser.add_argument("--shard-dir", type=Path)
    parser.add_argument("--output-namespace")
    parser.add_argument("--sharded", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    namespace = args.output_namespace
    if namespace is None and args.target_source != "question_agent":
        namespace = args.target_source
    packet_dir = args.packet_dir
    if packet_dir is None:
        packet_dir = WORKSPACE / "packets"
        if args.target_source != "question_agent":
            packet_dir = packet_dir / args.target_source
    shard_root = args.shard_dir
    if shard_root is None:
        shard_root = WORKSPACE / "packet_shards" / args.target_source

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompts_dir = WORKSPACE / "prompts"
    logs_dir = WORKSPACE / "logs"
    outputs_dir = WORKSPACE / "outputs"
    for directory in (prompts_dir, logs_dir, outputs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    registry_entries = []
    for chapter in parse_chapters(args.chapters):
        packet_path = packet_dir / f"chapter_{chapter:02d}.json"
        if not packet_path.exists():
            parser.error(
                f"packet missing for chapter {chapter}: {packet_path}; "
                "run export_content_remediation_packets.py first"
            )
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet_source = str(packet.get("target_generation_source") or "")
        if packet_source != args.target_source:
            parser.error(
                f"packet source mismatch for chapter {chapter}: "
                f"expected {args.target_source}, found {packet_source or '<missing>'}"
            )
        chapter_dir = outputs_dir
        if namespace:
            chapter_dir = chapter_dir / namespace
        chapter_dir = chapter_dir / f"chapter_{chapter:02d}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        stem = f"chapter_{chapter:02d}_pass_{args.pass_number:02d}"
        output_json = chapter_dir / f"{stem}.json"
        output_markdown = chapter_dir / f"{stem}.md"
        if output_json.exists() or output_markdown.exists():
            parser.error(f"refusing to overwrite existing output for {stem}")
        artifact_stem = f"{namespace}_{stem}" if namespace else stem
        prompt_path = prompts_dir / f"{artifact_stem}_{timestamp}.md"
        log_path = logs_dir / f"{artifact_stem}_{timestamp}.log"
        if args.sharded:
            chapter_shards = shard_root / f"chapter_{chapter:02d}"
            if not any(chapter_shards.glob("chapter_*_shard_*.json")):
                parser.error(
                    f"shards missing for chapter {chapter}: {chapter_shards}; "
                    "run shard_content_remediation_packets.py first"
                )
            prompt_path.write_text(
                "Sequential bounded chapter worker.\n"
                f"Chapter: {chapter}\n"
                f"Shard directory: {chapter_shards.resolve()}\n",
                encoding="utf-8",
            )
        else:
            chapter_shards = None
            prompt_path.write_text(
                build_prompt(
                    chapter,
                    packet_path.resolve(),
                    output_json.resolve(),
                    output_markdown.resolve(),
                ),
                encoding="utf-8",
            )

        entry = {
            "chapter": chapter,
            "pass": args.pass_number,
            "target_generation_source": args.target_source,
            "output_namespace": namespace,
            "packet": str(packet_path.resolve()),
            "prompt": str(prompt_path.resolve()),
            "log": str(log_path.resolve()),
            "output_json": str(output_json.resolve()),
            "output_markdown": str(output_markdown.resolve()),
            "sharded": args.sharded,
            "shard_dir": str(chapter_shards.resolve()) if chapter_shards else None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "pid": None,
        }
        if args.run:
            if args.sharded:
                process = launch_chapter_worker(
                    chapter,
                    args.pass_number,
                    packet_path.resolve(),
                    chapter_shards.resolve(),
                    output_json.resolve(),
                    output_markdown.resolve(),
                    log_path,
                )
            else:
                process = launch_agent(prompt_path, log_path)
            entry["pid"] = process.pid
            print(f"started chapter {chapter:02d} pid={process.pid} log={log_path}")
        else:
            print(f"prepared chapter {chapter:02d}: {prompt_path}")
        registry_entries.append(entry)

    registry = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run": args.run,
        "target_generation_source": args.target_source,
        "output_namespace": namespace,
        "agents": registry_entries,
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
