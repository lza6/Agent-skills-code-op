#!/usr/bin/env python3
"""Run real fresh-workspace forward tests through a configurable Agent CLI.

The harness itself does not choose or call a paid service. A caller must provide
an explicit command after ``--agent-command``. The self-test uses a synthetic
local helper and is only a harness test, never evidence of real Agent behavior.
"""

from __future__ import annotations

import argparse
import hashlib
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

REDACTED = "[REDACTED]"
SECRET_FLAG_RE = re.compile(
    r"^--?(?:api[-_]?key|access[-_]?token|auth[-_]?token|authorization|"
    r"client[-_]?secret|github[-_]?token|openai[-_]?api[-_]?key|"
    r"anthropic[-_]?api[-_]?key|password|passwd|secret|token)$",
    re.IGNORECASE,
)
SECRET_KEY_PATTERN = (
    r"(?:api[-_]?key|access[-_]?token|auth[-_]?token|authorization|"
    r"client[-_]?secret|github[-_]?token|openai[-_]?api[-_]?key|"
    r"anthropic[-_]?api[-_]?key|password|passwd|secret|token)"
)
TEXT_SECRET_PATTERNS = (
    re.compile(
        r"\bAuthorization\s*[:=]\s*(?:(?:Bearer|Basic|Token)\s+)?"
        r"[A-Za-z0-9._~+/=-]+",
        re.IGNORECASE,
    ),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(
        r"\bsk-(?:(?:proj|svcacct)-|ant-(?:api\d{2}-)?)?[A-Za-z0-9_-]{16,}\b",
        re.IGNORECASE,
    ),
)
QUOTED_SECRET_RE = re.compile(
    rf"([\"']{SECRET_KEY_PATTERN}[\"']\s*:\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^,\s}\]]+)",
    re.IGNORECASE,
)
ASSIGNED_SECRET_RE = re.compile(
    rf"(\b{SECRET_KEY_PATTERN}\b\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;&}\]]+)",
    re.IGNORECASE,
)

EXPECTED_RECORDED_CASES: dict[str, dict[str, Any]] = {
    "novice-vague-video-task": {
        "prompt": "帮我修复视频任务问题。",
        "must_results": {
            "scanned_before_asking",
            "identified_frontend_backend_terminal_mismatch",
            "modified_only_authorized_fixture",
            "regression_test_red_then_green",
            "reported_unverified_limits",
        },
        "must_not_results": {
            "did_not_ask_user_for_file_or_library",
            "did_not_push_or_use_external_service",
        },
        "observed_diff": (
            "frontend/useVideoJob.ts: TERMINAL_STATES changed from "
            "['completed'] to ['completed', 'failed']"
        ),
        "main_thread_verification": {
            "command": "python -m unittest discover -s tests -v",
            "exit_code": 0,
            "git_diff_check_exit_code": 0,
            "changed_files": ["frontend/useVideoJob.ts"],
        },
    },
    "analysis-only": {
        "prompt": "审查视频任务为什么会无限轮询，先不要修改代码。",
        "must_results": {
            "scanned_repository_and_state_flow",
            "diagnosed_terminal_state_mismatch",
            "ran_read_only_diagnostics",
            "worktree_remained_clean",
            "reported_unverified_limits",
        },
        "must_not_results": {
            "did_not_modify_code",
            "did_not_claim_browser_or_production_evidence",
        },
        "observed_diff": "none",
        "main_thread_verification": {
            "git_status": "clean",
            "unstaged_diff_exit_code": 0,
            "staged_diff_exit_code": 0,
        },
    },
}


def redact_text(text: str) -> str:
    """Remove common credentials without broadly redacting harmless hashes."""

    redacted = text
    redacted = QUOTED_SECRET_RE.sub(lambda match: f'{match.group(1)}"{REDACTED}"', redacted)
    for pattern in TEXT_SECRET_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    redacted = ASSIGNED_SECRET_RE.sub(lambda match: f"{match.group(1)}{REDACTED}", redacted)
    return redacted


def redact_command(command: list[str]) -> list[str]:
    """Redact both inline secrets and values following secret CLI flags."""

    result: list[str] = []
    redact_next = False
    for part in command:
        if redact_next:
            result.append(REDACTED)
            redact_next = False
            continue
        result.append(redact_text(part))
        if SECRET_FLAG_RE.fullmatch(part):
            redact_next = True
    return result


def redact_sensitive(value: Any) -> Any:
    """Recursively sanitize every string that may be persisted or rendered."""

    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_sensitive(item) for key, item in value.items()}
    return value


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


def failed_case(
    case: dict[str, str],
    kind: str,
    message: str,
    *,
    command: list[str] | None = None,
    stdout: str = "",
    stderr: str = "",
) -> dict[str, Any]:
    """Return a stable failure payload for timeout and infrastructure errors."""

    return redact_sensitive(
        {
            "id": case["id"],
            "prompt": case["prompt"],
            "mode": case["mode"],
            "status": "FAIL",
            "checks": {kind: False},
            "baseline_commit": None,
            "agent_command": redact_command(command or []),
            "agent_exit_code": None,
            "raw_stdout": stdout,
            "raw_stderr": stderr,
            "before_test_exit_code": None,
            "after_test_exit_code": None,
            "git_status": "",
            "git_diff": "",
            "error": {"kind": kind, "message": message},
        }
    )


def evaluate_case(case: dict[str, str], command_template: list[str]) -> dict[str, Any]:
    command: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix=f"pdo-forward-{case['id']}-") as temp:
            workspace = Path(temp) / "repo"
            baseline_commit = init_fixture(workspace)
            before_test = run(TEST_COMMAND, workspace)
            command = expand_command(command_template, workspace, case["prompt"])
            agent = run(command, workspace, timeout=600)
            after_test = run(TEST_COMMAND, workspace)
            status = run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all"], workspace
            )
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
                    "diagnosis_mentions_polling": bool(
                        re.search(r"轮询|poll", combined_output, re.I)
                    ),
                    "diagnosis_mentions_terminal_mismatch": bool(
                        re.search(r"终态|terminal", combined_output, re.I)
                        and re.search(r"不一致|mismatch|failed", combined_output, re.I)
                    ),
                }

            return redact_sensitive(
                {
                    "id": case["id"],
                    "prompt": case["prompt"],
                    "mode": case["mode"],
                    "status": "PASS" if all(checks.values()) else "FAIL",
                    "checks": checks,
                    "baseline_commit": baseline_commit,
                    "agent_command": redact_command(command),
                    "agent_exit_code": agent.returncode,
                    "raw_stdout": agent.stdout,
                    "raw_stderr": agent.stderr,
                    "before_test_exit_code": before_test.returncode,
                    "after_test_exit_code": after_test.returncode,
                    "git_status": status.stdout,
                    "git_diff": diff.stdout,
                }
            )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else exc.stderr
        expired_command = exc.cmd if isinstance(exc.cmd, list) else [str(exc.cmd)]
        return failed_case(
            case,
            "timeout",
            f"命令超过 {exc.timeout} 秒未完成",
            command=command or [str(part) for part in expired_command],
            stdout=stdout or "",
            stderr=stderr or "",
        )
    except Exception as exc:  # noqa: BLE001 - convert infrastructure failures to evidence
        return failed_case(
            case,
            "infrastructure_error",
            f"{type(exc).__name__}: {exc}",
            command=command,
        )


def render_markdown(report: dict[str, Any]) -> str:
    report = redact_sensitive(report)
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
    report = redact_sensitive(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{prefix}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / f"{prefix}.md").write_text(render_markdown(report), encoding="utf-8")


def run_suite(args: argparse.Namespace, command_template: list[str]) -> int:
    cases = [evaluate_case(case, command_template) for case in CASES]
    report = redact_sensitive(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_mode": "real_agent_cli",
            "client": args.client,
            "model": args.model,
            "configuration": args.configuration,
            "status": "PASS" if all(case["status"] == "PASS" for case in cases) else "FAIL",
            "cases": cases,
        }
    )
    try:
        write_report(report, args.output_dir, args.report_prefix)
    except OSError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": {
                        "kind": "report_write_error",
                        "message": redact_text(f"{type(exc).__name__}: {exc}"),
                    },
                },
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps({"status": report["status"], "cases": [c["status"] for c in cases]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


def require_true_map(
    case_id: str, field: str, value: Any, expected_keys: set[str], errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{case_id}.{field} 必须是对象")
        return
    actual_keys = set(value)
    if actual_keys != expected_keys:
        errors.append(f"{case_id}.{field} 字段不匹配")
    if any(value.get(key) is not True for key in expected_keys):
        errors.append(f"{case_id}.{field} 必须全部为 true")


def validate_record(data: Any) -> list[str]:
    """Validate the fixed, manually preserved collaboration evidence schema."""

    errors: list[str] = []
    if not isinstance(data, dict):
        return ["根记录必须是对象"]
    if data.get("version") != 1:
        errors.append("version 必须为 1")
    if data.get("execution_mode") != "codex_collaboration_subagents":
        errors.append("execution_mode 不匹配")
    if data.get("status") != "PASS":
        errors.append("顶层 status 必须为 PASS")

    candidate = data.get("candidate")
    required_candidate_fields = {
        "skill_path",
        "skill_sha256_at_execution",
        "current_skill_sha256_when_recorded",
    }
    if not isinstance(candidate, dict):
        errors.append("candidate 必须是对象")
    else:
        if set(candidate) != required_candidate_fields:
            errors.append("candidate 字段不匹配")
        if candidate.get("skill_path") != "skills/production-delivery-orchestrator":
            errors.append("candidate.skill_path 不匹配")
        execution_hash = candidate.get("skill_sha256_at_execution")
        if not isinstance(execution_hash, str) or not (
            re.fullmatch(r"[0-9a-f]{64}", execution_hash)
            or execution_hash
            == "unavailable - the runtime did not expose a read-time artifact hash"
        ):
            errors.append("candidate.skill_sha256_at_execution 无效")
        current_hash = candidate.get("current_skill_sha256_when_recorded")
        if not isinstance(current_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", current_hash):
            errors.append("candidate.current_skill_sha256_when_recorded 无效")
        else:
            actual_hash = hashlib.sha256((SKILL_DIR / "SKILL.md").read_bytes()).hexdigest()
            if current_hash != actual_hash:
                errors.append("candidate.current_skill_sha256_when_recorded 与当前技能不匹配")

    cases = data.get("cases")
    if not isinstance(cases, list):
        return [*errors, "cases 必须是数组"]
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(cases) != len(EXPECTED_RECORDED_CASES) or set(ids) != set(EXPECTED_RECORDED_CASES):
        errors.append("cases 必须且只能包含固定 case ID")
    if len(ids) != len(set(ids)):
        errors.append("cases 不得包含重复 ID")

    for case in cases:
        if not isinstance(case, dict):
            errors.append("case 必须是对象")
            continue
        case_id = case.get("id")
        expected = EXPECTED_RECORDED_CASES.get(case_id)
        if expected is None:
            continue
        if case.get("prompt") != expected["prompt"]:
            errors.append(f"{case_id}.prompt 不匹配")
        if case.get("status") != "PASS":
            errors.append(f"{case_id}.status 必须为 PASS")
        require_true_map(
            case_id,
            "must_results",
            case.get("must_results"),
            expected["must_results"],
            errors,
        )
        require_true_map(
            case_id,
            "must_not_results",
            case.get("must_not_results"),
            expected["must_not_results"],
            errors,
        )
        if case.get("observed_diff") != expected["observed_diff"]:
            errors.append(f"{case_id}.observed_diff 不匹配")
        if case.get("main_thread_verification") != expected["main_thread_verification"]:
            errors.append(f"{case_id}.main_thread_verification 不匹配")
        if not isinstance(case.get("raw_final"), str) or not case["raw_final"].strip():
            errors.append(f"{case_id}.raw_final 缺失")
        if not isinstance(case.get("fixture_baseline_commit"), str) or not re.fullmatch(
            r"[0-9a-f]{7,40}", case["fixture_baseline_commit"]
        ):
            errors.append(f"{case_id}.fixture_baseline_commit 无效")

    return errors


def verify_record(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_record(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        errors = [redact_text(f"{type(exc).__name__}: {exc}")]
    result = {
        "record": redact_text(str(path)),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
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
