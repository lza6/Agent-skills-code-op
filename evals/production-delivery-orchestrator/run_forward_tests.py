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
import stat
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
    {
        "id": "ambiguous-user-visible-retry",
        "prompt": (
            "视频任务上游失败后应该自动重试，还是让用户手动重试？"
            "先不要修改。请基于仓库现状给出推荐和两到三个用户可见结果选项。"
        ),
        "mode": "result_options",
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

ARTIFACT_HASH_DOMAIN = b"production-delivery-orchestrator-artifact-v2\0"
ARTIFACT_BINARY_KIND = b"B"
ARTIFACT_UTF8_TEXT_KIND = b"T"
ARTIFACT_IGNORED_DIRECTORIES = {"__pycache__"}
ARTIFACT_IGNORED_FILES = {".DS_Store"}
ARTIFACT_IGNORED_SUFFIXES = {".pyc"}
SAFE_AGENT_ENV_KEYS = (
    "PATH",
    "PATHEXT",
    "ComSpec",
    "SystemRoot",
    "WINDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
)
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RESERVED_AGENT_ENV_KEYS = {
    *SAFE_AGENT_ENV_KEYS,
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "TMP",
    "TEMP",
    "PYTHONUTF8",
}


def skill_artifact_files(skill_dir: Path) -> list[Path]:
    """Return deterministic regular files that form the complete skill artifact."""

    if not skill_dir.is_dir():
        raise FileNotFoundError(f"技能目录不存在或不是目录: {skill_dir}")

    files: list[Path] = []

    def raise_walk_error(error: OSError) -> None:
        raise error

    for root, directory_names, file_names in os.walk(
        skill_dir, topdown=True, onerror=raise_walk_error, followlinks=False
    ):
        root_path = Path(root)
        included_directories: list[str] = []
        for name in directory_names:
            if name in ARTIFACT_IGNORED_DIRECTORIES:
                continue
            path = root_path / name
            if path.is_symlink():
                raise OSError(f"完整技能 artifact 不允许符号链接目录: {path}")
            included_directories.append(name)
        directory_names[:] = included_directories
        for name in file_names:
            path = root_path / name
            if (
                name in ARTIFACT_IGNORED_FILES
                or path.suffix.lower() in ARTIFACT_IGNORED_SUFFIXES
            ):
                continue
            if path.is_symlink():
                raise OSError(f"完整技能 artifact 不允许符号链接文件: {path}")
            if stat.S_ISREG(path.lstat().st_mode):
                files.append(path)

    return sorted(files, key=lambda path: path.relative_to(skill_dir).as_posix())


def canonical_artifact_content(content: bytes) -> tuple[bytes, bytes]:
    """Return an explicit content kind and deterministic bytes for artifact hashing.

    Strict UTF-8 without NUL is text and has CRLF/CR normalized to LF. Content that
    is not strict UTF-8, or contains NUL, is binary and remains byte-for-byte exact.
    The kind tag is hashed too, so text and binary framing cannot collide.
    """

    if b"\0" in content:
        return ARTIFACT_BINARY_KIND, content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return ARTIFACT_BINARY_KIND, content
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return ARTIFACT_UTF8_TEXT_KIND, normalized.encode("utf-8")


def skill_artifact_sha256(skill_dir: Path) -> str:
    """Hash complete relative paths and canonical content with length framing."""

    digest = hashlib.sha256()
    digest.update(ARTIFACT_HASH_DOMAIN)
    for path in skill_artifact_files(skill_dir):
        relative_path = path.relative_to(skill_dir).as_posix().encode("utf-8")
        content_kind, content = canonical_artifact_content(path.read_bytes())
        digest.update(len(relative_path).to_bytes(8, byteorder="big"))
        digest.update(relative_path)
        digest.update(content_kind)
        digest.update(len(content).to_bytes(8, byteorder="big"))
        digest.update(content)
    return digest.hexdigest()


def configure_utf8_stdio() -> None:
    """Make CLI output independent of the Windows console's legacy code page."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            # Some embedded or already-detached streams cannot be reconfigured.
            # Their owner remains responsible for supplying a Unicode-capable stream.
            continue


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


def redact_runtime_paths(
    value: Any,
    workspace: Path | None = None,
    secret_values: tuple[str, ...] = (),
) -> Any:
    """Replace ephemeral and host-local paths before a forward-test report is saved."""

    replacements = {
        str(SKILL_DIR): "{skill_dir}",
        SKILL_DIR.as_posix(): "{skill_dir}",
    }
    if workspace is not None:
        runtime_home = workspace.parent / ".agent-home"
        runtime_temp = workspace.parent / ".agent-temp"
        replacements.update(
            {
                str(workspace): "{workspace}",
                workspace.as_posix(): "{workspace}",
                str(runtime_home): "{agent_home}",
                runtime_home.as_posix(): "{agent_home}",
                str(runtime_temp): "{agent_temp}",
                runtime_temp.as_posix(): "{agent_temp}",
            }
        )
    if isinstance(value, str):
        redacted = redact_text(value)
        for secret in secret_values:
            if secret:
                redacted = redacted.replace(secret, REDACTED)
        for source, target in replacements.items():
            redacted = redacted.replace(source, target)
        return redacted
    if isinstance(value, list):
        return [redact_runtime_paths(item, workspace, secret_values) for item in value]
    if isinstance(value, tuple):
        return [redact_runtime_paths(item, workspace, secret_values) for item in value]
    if isinstance(value, dict):
        return {
            key: redact_runtime_paths(item, workspace, secret_values)
            for key, item in value.items()
        }
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


def isolated_agent_environment(workspace: Path, extra_env: dict[str, str] | None) -> dict[str, str]:
    """Create a minimal per-fixture environment instead of inheriting host secrets."""

    home = workspace.parent / ".agent-home"
    temp = workspace.parent / ".agent-temp"
    home.mkdir(exist_ok=True)
    temp.mkdir(exist_ok=True)
    environment = {
        key: os.environ[key] for key in SAFE_AGENT_ENV_KEYS if key in os.environ
    }
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(home / "AppData" / "Local"),
            "TMP": str(temp),
            "TEMP": str(temp),
            "PYTHONUTF8": "1",
        }
    )
    if extra_env:
        environment.update(extra_env)
    return environment


def run_agent(
    command: list[str], cwd: Path, agent_env: dict[str, str] | None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=isolated_agent_environment(cwd, agent_env),
        timeout=600,
    )


def init_fixture(workspace: Path) -> str:
    shutil.copytree(
        FIXTURE_DIR,
        workspace,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    staged_skill = workspace / ".forward-skill"
    shutil.copytree(
        SKILL_DIR,
        staged_skill,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    if skill_artifact_sha256(staged_skill) != skill_artifact_sha256(SKILL_DIR):
        raise RuntimeError("暂存到 fixture 的完整技能 artifact SHA-256 不匹配")
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


def expand_command(
    template: list[str], workspace: Path, prompt: str, skill_dir: Path = SKILL_DIR
) -> list[str]:
    values = {
        "workspace": str(workspace),
        "skill_dir": str(skill_dir),
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
    workspace: Path | None = None,
    secret_values: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return a stable failure payload for timeout and infrastructure errors."""

    return redact_runtime_paths(
        redact_sensitive(
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
        ),
        workspace,
        secret_values,
    )


def evaluate_case(
    case: dict[str, str],
    command_template: list[str],
    agent_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    command: list[str] = []
    workspace: Path | None = None
    secret_values = tuple((agent_env or {}).values())
    try:
        with tempfile.TemporaryDirectory(prefix=f"pdo-forward-{case['id']}-") as temp:
            workspace = Path(temp) / "repo"
            baseline_commit = init_fixture(workspace)
            staged_skill = workspace / ".forward-skill"
            staged_skill_hash_before = skill_artifact_sha256(staged_skill)
            before_test = run(TEST_COMMAND, workspace)
            command = expand_command(
                command_template, workspace, case["prompt"], staged_skill
            )
            agent = run_agent(command, workspace, agent_env)
            after_test = run(TEST_COMMAND, workspace)
            status = run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all"], workspace
            )
            diff = run(["git", "diff", "--no-ext-diff"], workspace)
            combined_output = f"{agent.stdout}\n{agent.stderr}"
            try:
                staged_skill_unchanged = (
                    skill_artifact_sha256(staged_skill) == staged_skill_hash_before
                )
            except OSError:
                staged_skill_unchanged = False

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
                    "staged_skill_unchanged": staged_skill_unchanged,
                }
            elif case["mode"] == "read_only":
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
                    "staged_skill_unchanged": staged_skill_unchanged,
                }
            else:
                checks = {
                    "agent_exit_zero": agent.returncode == 0,
                    "worktree_unchanged": not status.stdout.strip() and not diff.stdout.strip(),
                    "offers_recommended_result_options": bool(
                        re.search(r"推荐|建议", combined_output)
                        and re.search(r"自动重试", combined_output)
                        and re.search(r"手动重试", combined_output)
                    ),
                    "uses_repository_evidence": bool(
                        re.search(r"仓库|状态|轮询|failed|终态", combined_output, re.I)
                    ),
                    "staged_skill_unchanged": staged_skill_unchanged,
                }

            return redact_runtime_paths(
                redact_sensitive(
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
                ),
                workspace,
                secret_values,
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
            workspace=workspace,
            secret_values=secret_values,
        )
    except Exception as exc:  # noqa: BLE001 - convert infrastructure failures to evidence
        return failed_case(
            case,
            "infrastructure_error",
            f"{type(exc).__name__}: {exc}",
            command=command,
            workspace=workspace,
            secret_values=secret_values,
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
    candidate = report.get("candidate")
    if isinstance(candidate, dict):
        lines.extend(
            [
                "- 执行前技能 SHA-256："
                f"`{candidate.get('skill_sha256_at_execution', 'unknown')}`",
                "- 执行后技能 SHA-256："
                f"`{candidate.get('skill_sha256_after_execution', 'unknown')}`",
                "",
            ]
        )
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


def run_suite(
    args: argparse.Namespace,
    command_template: list[str],
    agent_env: dict[str, str] | None = None,
) -> int:
    try:
        skill_hash_before = skill_artifact_sha256(SKILL_DIR)
    except OSError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": {
                        "kind": "skill_artifact_hash_error",
                        "message": redact_text(f"{type(exc).__name__}: {exc}"),
                    },
                },
                ensure_ascii=False,
            )
        )
        return 1
    cases = [evaluate_case(case, command_template, agent_env) for case in CASES]
    try:
        skill_hash_after = skill_artifact_sha256(SKILL_DIR)
    except OSError as exc:
        skill_hash_after = f"unavailable: {type(exc).__name__}"
    skill_unchanged = skill_hash_after == skill_hash_before
    report = redact_sensitive(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_mode": "real_agent_cli",
            "client": args.client,
            "model": args.model,
            "configuration": args.configuration,
            "candidate": {
                "skill_path": "skills/production-delivery-orchestrator",
                "skill_sha256_at_execution": skill_hash_before,
                "skill_sha256_after_execution": skill_hash_after,
                "skill_unchanged": skill_unchanged,
            },
            "status": (
                "PASS"
                if all(case["status"] == "PASS" for case in cases) and skill_unchanged
                else "FAIL"
            ),
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
        execution_hash_valid = isinstance(execution_hash, str) and bool(
            re.fullmatch(r"[0-9a-f]{64}", execution_hash)
        )
        if not execution_hash_valid:
            errors.append(
                "candidate.skill_sha256_at_execution 必须是执行时完整技能 artifact 的 SHA-256；"
                "unavailable 不能作为严格 PASS 证据"
            )
        current_hash = candidate.get("current_skill_sha256_when_recorded")
        current_hash_valid = isinstance(current_hash, str) and bool(
            re.fullmatch(r"[0-9a-f]{64}", current_hash)
        )
        if not current_hash_valid:
            errors.append("candidate.current_skill_sha256_when_recorded 无效")
        try:
            actual_hash = skill_artifact_sha256(SKILL_DIR)
        except OSError as exc:
            errors.append(
                "无法计算当前完整技能 artifact SHA-256: "
                f"{type(exc).__name__}: {redact_text(str(exc))}"
            )
        else:
            if execution_hash_valid and execution_hash != actual_hash:
                errors.append(
                    "candidate.skill_sha256_at_execution 已陈旧或与当前完整技能 artifact 不匹配"
                )
            if current_hash_valid and current_hash != actual_hash:
                errors.append(
                    "candidate.current_skill_sha256_when_recorded 已陈旧或与当前完整技能 "
                    "artifact 不匹配"
                )
            if (
                execution_hash_valid
                and current_hash_valid
                and execution_hash != current_hash
            ):
                errors.append("candidate 的执行时与记录时完整技能 artifact hash 不匹配")

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
import os
import sys
prompt = sys.argv[1]
Path(os.environ['HOME']).joinpath('client-state').write_text('synthetic runtime state', encoding='utf-8')
if '自动重试，还是让用户手动重试' in prompt:
    print('仓库当前没有自动重试策略；推荐：失败后展示手动重试。选项：自动重试，或手动重试。')
elif '先不要修改' in prompt:
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


def load_agent_env_file(path: Path | None) -> dict[str, str]:
    """Read explicit runtime credentials without inheriting the host environment."""

    if path is None:
        return {}
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"无法读取 agent 环境文件: {type(exc).__name__}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not ENV_NAME_RE.fullmatch(key):
            raise ValueError(f"agent 环境文件第 {line_number} 行必须是 KEY=VALUE")
        if key in RESERVED_AGENT_ENV_KEYS:
            raise ValueError(f"agent 环境文件不得覆盖受控变量: {key}")
        if key in values:
            raise ValueError(f"agent 环境文件不得重复变量: {key}")
        values[key] = value
    return values


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
    parser.add_argument(
        "--agent-env-file",
        type=Path,
        help="仅传给 Agent 子进程的 KEY=VALUE 文件；内容不会写入报告。",
    )
    parser.add_argument(
        "--allow-unsafe-host-execution",
        action="store_true",
        help="确认当前命令不在 OS/容器沙箱中执行真实 Agent；优先在外部沙箱中运行。",
    )
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    if args.self_test:
        return self_test()
    if args.verify_record:
        return verify_record(args.verify_record)
    if not args.agent_command:
        print("未提供 --agent-command；真实 forward-test 状态为 NOT_RUN。", file=sys.stderr)
        return 2
    if not args.allow_unsafe_host_execution:
        print(
            "拒绝在未确认的宿主环境执行真实 Agent；请使用外部 OS/容器沙箱，"
            "或明确传入 --allow-unsafe-host-execution。",
            file=sys.stderr,
        )
        return 2
    try:
        agent_env = load_agent_env_file(args.agent_env_file)
    except ValueError as error:
        print(f"agent 环境文件无效：{error}", file=sys.stderr)
        return 1
    return run_suite(args, args.agent_command, agent_env)


if __name__ == "__main__":
    raise SystemExit(main())
