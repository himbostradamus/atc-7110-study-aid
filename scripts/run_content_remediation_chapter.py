#!/usr/bin/env python3
"""Run bounded remediation shards sequentially for one chapter, then merge."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (
    ROOT / "backend" / "app" / "data" / "question_authoring_workspace"
    / "remediation"
)
PROMPT_TEMPLATE = ROOT / "docs" / "content-remediation-agent-prompt.md"
HARNESS = ROOT / "docs" / "content-remediation-agent-harness.md"
DEFAULT_VENV = Path("/home/perfect-vacuum/python_env/python_environment/bin/activate")
DEFAULT_DEEPSEEK_SETUP = Path("/home/perfect-vacuum/scripts/use-deepseek-claude-code.sh")
DEFAULT_CLAUDE = Path("/home/perfect-vacuum/.nvm/versions/node/v22.16.0/bin/claude")
LOCAL_AGENT_ENV = ROOT / ".env.agent.local"


def agent_setup() -> str:
    custom = os.environ.get("ATC_REMEDIATION_AGENT_COMMAND")
    if custom:
        return custom
    return (
        f"if [ -f {shlex.quote(str(LOCAL_AGENT_ENV))} ]; then "
        f"set -a; source {shlex.quote(str(LOCAL_AGENT_ENV))}; set +a; fi && "
        f"if [ -z \"$DEEPSEEK_API_KEY\" ]; then "
        f"source {shlex.quote(str(DEFAULT_VENV))}; fi && "
        f"source {shlex.quote(str(DEFAULT_DEEPSEEK_SETUP))} >/dev/null && "
        f"{shlex.quote(str(DEFAULT_CLAUDE))}"
    )


def build_prompt(
    chapter: int,
    shard_path: Path,
    output_json: Path,
    output_markdown: Path,
) -> str:
    base = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    shard = json.loads(shard_path.read_text(encoding="utf-8"))
    metadata = shard["shard"]
    shard_display = shard_path.relative_to(ROOT)
    output_json_display = output_json.relative_to(ROOT)
    output_markdown_display = output_markdown.relative_to(ROOT)
    return f"""{base}

## Assigned Chapter Shard

Chapter: `{chapter}`
Shard: `{metadata['index']} of {metadata['count']}`
Paragraphs represented: `{', '.join(metadata['paragraph_ids'])}`

This is a bounded continuation of the full chapter review. Review every target
in this shard only. Do not attempt to read the full chapter packet or synthesize
the final chapter report; the orchestrator will merge validated shard outputs.

Packet:

```text
{shard_display}
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
  --packet {shlex.quote(str(shard_display))} \
  --manifest {shlex.quote(str(output_json_display))}
```

Read the harness at `{HARNESS}` before beginning. Use the exact output paths.
Write the JSON manifest before the Markdown summary, validate it, and finish
only after the validator exits successfully.
"""


def run_agent(prompt_path: Path, log_path: Path) -> int:
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
        f"{agent_setup()} --print --verbose --output-format stream-json "
        f"--allowedTools {shlex.quote(allowed_tools)} "
        f"--disallowedTools {shlex.quote(disallowed_tools)} "
        f"< {shlex.quote(str(prompt_path))}; "
        'status=$?; echo "__CLAUDE_EXIT_CODE__${status}"; exit "$status"'
    )
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.run(
            ["bash", "-lc", f"tail -f /dev/null | script -qfec {shlex.quote(command)} /dev/null"],
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return process.returncode


def validate(shard_path: Path, manifest_path: Path) -> bool:
    result = subprocess.run(
        [
            "python",
            "scripts/validate_content_remediation_manifest.py",
            "--packet",
            str(shard_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--shard-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=2)
    args = parser.parse_args()

    shard_paths = sorted(args.shard_dir.glob("chapter_*_shard_*.json"))
    if not shard_paths:
        parser.error(f"no shards found in {args.shard_dir}")
    manifests_dir = args.output_json.parent / "shards"
    prompts_dir = WORKSPACE / "prompts" / "shards"
    logs_dir = WORKSPACE / "logs" / "shards"
    for directory in (manifests_dir, prompts_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for shard_path in shard_paths:
        stem = shard_path.stem
        manifest_path = manifests_dir / f"{stem}_pass_{args.pass_number:02d}.json"
        markdown_path = manifests_dir / f"{stem}_pass_{args.pass_number:02d}.md"
        if manifest_path.exists() and validate(shard_path, manifest_path):
            print(f"{stem}: existing manifest valid; skipping", flush=True)
            continue
        manifest_path.unlink(missing_ok=True)
        markdown_path.unlink(missing_ok=True)
        completed = False
        for attempt in range(1, args.attempts + 1):
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            prompt_path = prompts_dir / f"{stem}_attempt_{attempt}_{timestamp}.md"
            log_path = logs_dir / f"{stem}_attempt_{attempt}_{timestamp}.log"
            prompt_path.write_text(
                build_prompt(args.chapter, shard_path.resolve(), manifest_path.resolve(), markdown_path.resolve()),
                encoding="utf-8",
            )
            print(f"{stem}: attempt {attempt}", flush=True)
            run_agent(prompt_path, log_path)
            if manifest_path.exists() and validate(shard_path, manifest_path):
                completed = True
                break
            manifest_path.unlink(missing_ok=True)
            markdown_path.unlink(missing_ok=True)
        if not completed:
            print(f"{stem}: failed after {args.attempts} attempt(s)", flush=True)
            return 1

    merge = subprocess.run(
        [
            "python",
            "scripts/merge_content_remediation_shards.py",
            "--packet",
            str(args.packet),
            "--shard-dir",
            str(args.shard_dir),
            "--manifest-dir",
            str(manifests_dir),
            "--pass-number",
            str(args.pass_number),
            "--out-json",
            str(args.output_json),
            "--out-markdown",
            str(args.output_markdown),
        ],
        cwd=ROOT,
        check=False,
    )
    return merge.returncode


if __name__ == "__main__":
    raise SystemExit(main())
