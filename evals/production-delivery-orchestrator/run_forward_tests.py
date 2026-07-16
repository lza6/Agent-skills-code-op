#!/usr/bin/env python3
"""Run real fresh-workspace forward tests through a configurable Agent CLI.

The harness itself does not choose or call a paid service. A caller must provide
an explicit command after ``--agent-command``. The self-test uses a synthetic
local helper and is only a harness test, never evidence of real Agent behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "production-delivery-orchestrator"
FIXTURE_DIR = EVAL_DIR / "fixtures" / "video-polling-state-machine"
TEST_COMMAND = [sys.executable, "tests/test_polling_contract.py", "-v"]
CASES = (
    {
        "id": "novice-vague-video-task",
        "prompt": "帮我修复视频任务问题。",
        "mode": "modify",
    },
    {
        "id": "analysis-only",
        "prompt": "审查视频任务为什么会无限轮询，先不要修改代码。",
        "mode": "read_only",
    },
)


def run(command: list[str], cwd: Path, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"},
        **kwargs,
    )


def init_fixture(workspace: Path) -> str:
    shutil.copytree(
        FIXTURE_DIR,
        workspace,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for command in (
        ["git", "init"],
        ["git", "config", "user.email", "forward-test@example.invalid"],
        ["git", "config", "user.name", "Forward Test"],
        ["git", "add", "."],
        ["git", "commit", "-m", "fixture baseline"],
    ):
        result = run(command, workspace)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
    return run(["git", "rev-parse", "HEAD"], workspace).stdout.strip()


def expand_command(template: list[str], workspace: Path, prompt: str) -> list[str]:
    values = {
        "workspace": str(workspace),
        "skill_dir": str(SKILL_DIR),
        "prompt": prompt,
    }
    return [part.format(**values) for part in template]


def evaluate_case(case: dict[str, str], command_template: list[str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"pdo-forward-{case['id']}-") as temp:
        workspace = Path(temp) / "repo"
        baseline_commit = init_fixture(workspace)
        before_test = run(TEST_COMMAND, workspace)
        command = expand_command(command_template, workspace, case["prompt"])
        agent = run(command, workspace, timeout=600)
        after_test = run(TEST_COMMAND, workspace)
        status = run(["git", "status", "--porcelain=v1", "--untracked-files=all"], workspace)
        diff = run(["git", "diff", "--no-ext-diff"], workspace)
        combined_output = f"{agent.stdout}\n{agent.stderr}"

        if case["mode"] == "modify":
            checks = {
                "agent_exit_zero": agent.returncode == 0,
                "fixture_red_before": before_test.returncode != 0,
                "fixture_green_after": after_test.returncode == 0,
                "failed_is_frontend_terminal": "['completed', 'failed']" in diff.stdout,
                "bounded_diff": all(
                    not line or line.endswith("frontend/useVideoJob.ts")
                    for line in status.stdout.splitlines()
                ),
            }
        else:
            checks = {
                "agent_exit_zero": agent.returncode == 0,
                "worktree_unchanged": not status.stdout.strip() and not diff.stdout.strip(),
                "diagnosis_mentions_polling": bool(re.search(r"轮询|poll", combined_output, re.I)),
                "diagnosis_mentions_terminal_mismatch": bool(
                    re.search(r"终态|terminal", combined_output, re.I)
                    and re.search(r"不一致|mismatch|failed", combined_output, re.I)
                ),
            }

        return {
            "id": case["id"],
            "prompt": case["prompt"],
            "mode": case["mode"],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "baseline_commit": baseline_commit,
            "agent_command": command,
            "agent_exit_code": agent.returncode,
            "raw_stdout": agent.stdout,
            "raw_stderr": agent.stderr,
            "before_test_exit_code": before_test.returncode,
            "after_test_exit_code": after_test.returncode,
            "git_status": status.stdout,
            "git_diff": diff.stdout,
        }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Production Delivery Orchestrator 真实 Forward-test",
        "",
        f"- 时间：`{report['generated_at']}`",
        f"- 客户端：`{report['client']}`",
        f"- 模型：`{report['model']}`",
        f"- 执行模式：`{report['execution_mode']}`",
        f"- 最终状态：**{report['status']}**",
        "",
        "> 只有使用真实 Agent 命令生成的报告才是行为证据；`--self-test` 只验证 harness。",
        "",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                f"## {case['status']} `{case['id']}`",
                "",
                f"- Prompt：{case['prompt']}",
                f"- Agent exit：`{case['agent_exit_code']}`",
                f"- 修复前测试：`{case['before_test_exit_code']}`",
                f"- 修复后测试：`{case['after_test_exit_code']}`",
                f"- 检查：`{case['checks']}`",
                "",
                "```diff",
                case["git_diff"].rstrip(),
                "```",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{prefix}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / f"{prefix}.md").write_text(render_markdown(report), encoding="utf-8")


def run_suite(args: argparse.Namespace, command_template: list[str]) -> int:
    cases = [evaluate_case(case, command_template) for case in CASES]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "real_agent_cli",
        "client": args.client,
        "model": args.model,
        "configuration": args.configuration,
        "status": "PASS" if all(case["status"] == "PASS" for case in cases) else "FAIL",
        "cases": cases,
    }
    write_report(report, args.output_dir, args.report_prefix)
    print(json.dumps({"status": report["status"], "cases": [c["status"] for c in cases]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


def verify_record(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = data.get("execution_mode") == "codex_collaboration_subagents"
    cases = data.get("cases", [])
    valid_cases = len(cases) >= 2 and all(
        case.get("status") == "PASS"
        and case.get("raw_final")
        and case.get("must_results")
        for case in cases
    )
    result = {"record": str(path), "status": "PASS" if required and valid_cases else "FAIL"}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="pdo-forward-harness-") as temp:
        helper = Path(temp) / "fake_agent.py"
        helper.write_text(
            """from pathlib import Path
import sys
prompt = sys.argv[1]
if '先不要修改' in prompt:
    print('轮询不会停止，因为 failed 终态与前端 terminal 状态不一致')
else:
    path = Path('frontend/useVideoJob.ts')
    text = path.read_text(encoding='utf-8')
    path.write_text(text.replace("['completed']", "['completed', 'failed']"), encoding='utf-8')
    print('已修复 failed 终态并运行验证')
""",
            encoding="utf-8",
        )
        args = argparse.Namespace(
            client="synthetic-local-helper",
            model="none",
            configuration="harness-self-test-only",
            output_dir=Path(temp) / "reports",
            report_prefix="self-test",
        )
        result = run_suite(args, [sys.executable, str(helper), "{prompt}"])
        print("注意：这是 synthetic harness self-test，不是真实 Agent forward-test。")
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="可配置真实 Agent CLI 的新上下文 forward-test")
    parser.add_argument("--client", default="custom-agent-cli")
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--configuration", default="unknown")
    parser.add_argument("--output-dir", type=Path, default=EVAL_DIR / "reports")
    parser.add_argument("--report-prefix", default="forward-latest")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify-record", type=Path)
    parser.add_argument(
        "--agent-command",
        nargs=argparse.REMAINDER,
        help="真实命令模板；支持 {workspace}、{skill_dir}、{prompt} 占位符，必须放在最后。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()
    if args.verify_record:
        return verify_record(args.verify_record)
    if not args.agent_command:
        print("未提供 --agent-command；真实 forward-test 状态为 NOT_RUN。", file=sys.stderr)
        return 2
    return run_suite(args, args.agent_command)


if __name__ == "__main__":
    raise SystemExit(main())
