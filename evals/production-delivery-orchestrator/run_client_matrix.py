#!/usr/bin/env python3
"""Probe and, only when explicitly requested, run real CLI forward-test profiles.

The default mode checks whether each configured client is installed. ``--execute``
then runs the existing isolated fixture suite once per selected client.  It is
deliberately opt-in because it may consume a provider quota or subscription.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
HARNESS_PATH = EVAL_DIR / "run_forward_tests.py"
DEFAULT_PROFILES = EVAL_DIR / "client-profiles.json"
DEFAULT_OUTPUT_DIR = EVAL_DIR / "reports" / "client-matrix"
PROFILE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
REQUIRED_PLACEHOLDERS = {"workspace", "skill_dir", "prompt"}
SEMVER_RE = re.compile(r"(?<![0-9A-Za-z.+-])(\d+\.\d+\.\d+)(?![0-9A-Za-z.+-])")


def load_harness() -> Any:
    spec = importlib.util.spec_from_file_location("production_forward_tests", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 forward-test harness: {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HARNESS = load_harness()


def require_string_list(value: Any, field: str, profile_id: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ValueError(f"profile {profile_id}.{field} 必须是非空字符串数组")
    return value


def current_platform_key() -> str:
    return "windows" if sys.platform.startswith("win") else "posix"


def validate_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("profile 必须是对象")
    profile_id = value.get("id")
    if not isinstance(profile_id, str) or not PROFILE_ID_RE.fullmatch(profile_id):
        raise ValueError("profile.id 必须是小写 kebab-case")
    for field in ("client", "observed_version", "configuration"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"profile {profile_id}.{field} 必须是非空字符串")
    if not SEMVER_RE.fullmatch(value["observed_version"].strip()):
        raise ValueError(f"profile {profile_id}.observed_version 必须是三段式版本号")
    executables = value.get("executables")
    if not isinstance(executables, dict) or set(executables) != {"windows", "posix"}:
        raise ValueError(f"profile {profile_id}.executables 必须包含 windows 和 posix")
    if any(not isinstance(item, str) or not item for item in executables.values()):
        raise ValueError(f"profile {profile_id}.executables 的值必须是非空字符串")
    probe_args = require_string_list(value.get("probe_args"), "probe_args", profile_id)
    agent_args = require_string_list(value.get("agent_args"), "agent_args", profile_id)
    placeholders = {
        placeholder
        for part in agent_args
        for placeholder in PLACEHOLDER_RE.findall(part)
    }
    unknown = placeholders - REQUIRED_PLACEHOLDERS
    if unknown:
        raise ValueError(f"profile {profile_id}.agent_args 存在未知占位符: {sorted(unknown)}")
    missing = REQUIRED_PLACEHOLDERS - placeholders
    if missing:
        raise ValueError(f"profile {profile_id}.agent_args 缺少占位符: {sorted(missing)}")
    executable = executables[current_platform_key()]
    return {
        "id": profile_id,
        "client": value["client"].strip(),
        "observed_version": value["observed_version"].strip(),
        "probe_command": [executable, *probe_args],
        "configuration": value["configuration"].strip(),
        "agent_command": [executable, *agent_args],
    }


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取 profile 配置 {path}: {type(error).__name__}: {error}") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("profile 配置 version 必须为 1")
    values = data.get("profiles")
    if not isinstance(values, list) or not values:
        raise ValueError("profile 配置 profiles 必须是非空数组")
    profiles = [validate_profile(value) for value in values]
    profile_ids = [profile["id"] for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("profile 配置不得有重复 id")
    return {profile["id"]: profile for profile in profiles}


def probe_profile(profile: dict[str, Any]) -> dict[str, Any]:
    command = profile["probe_command"]
    executable = shutil.which(command[0])
    base = {
        "id": profile["id"],
        "client": profile["client"],
        "observed_version": profile["observed_version"],
        "command": HARNESS.redact_command(command),
    }
    if executable is None:
        return {**base, "status": "UNAVAILABLE", "message": f"找不到命令: {command[0]}"}
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            **base,
            "status": "PROBE_FAILED",
            "message": HARNESS.redact_text(f"{type(error).__name__}: {error}"),
        }
    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        return {
            **base,
            "status": "PROBE_FAILED",
            "exit_code": completed.returncode,
            "output": HARNESS.redact_text(output),
        }
    match = SEMVER_RE.search(output)
    actual_version = match.group(1) if match else None
    if actual_version != profile["observed_version"]:
        return {
            **base,
            "status": "VERSION_MISMATCH",
            "exit_code": completed.returncode,
            "output": HARNESS.redact_text(output),
            "actual_version": actual_version,
            "message": "本机版本与经核对的 profile 不一致；先复核 CLI 参数再执行真实样本。",
        }
    return {
        **base,
        "status": "AVAILABLE",
        "exit_code": completed.returncode,
        "output": HARNESS.redact_text(output),
        "actual_version": actual_version,
    }


def execute_profile(
    profile: dict[str, Any],
    output_dir: Path,
    report_prefix: str,
    agent_env: dict[str, str],
) -> dict[str, Any]:
    profile_args = argparse.Namespace(
        client=profile["client"],
        model="unknown (client profile does not infer the model)",
        configuration=profile["configuration"],
        output_dir=output_dir,
        report_prefix=f"{report_prefix}-{profile['id']}",
    )
    result = HARNESS.run_suite(profile_args, profile["agent_command"], agent_env)
    report_path = output_dir / f"{profile_args.report_prefix}.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "id": profile["id"],
            "status": "FAIL",
            "message": HARNESS.redact_text(f"未生成可读报告: {type(error).__name__}: {error}"),
        }
    return {
        "id": profile["id"],
        "status": report.get("status", "FAIL"),
        "exit_code": result,
        "report": report_path.name,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Production Delivery Orchestrator 跨 CLI Forward-test 矩阵",
        "",
        f"- 时间：`{report['generated_at']}`",
        f"- 模式：`{report['mode']}`",
        f"- 技能 SHA-256：`{report['skill']['sha256']}`",
        f"- 最终状态：**{report['status']}**",
        "",
        "> `NOT_RUN` 表示只完成了本地 CLI 探测；它不是任何模型行为通过的证据。",
        "",
        "| Profile | 本机探测 | 观察版本 | 本次执行 | 证据 |",
        "|---|---|---|---|---|",
    ]
    run_map = {item["id"]: item for item in report["runs"]}
    for probe in report["probes"]:
        run = run_map.get(probe["id"], {})
        lines.append(
            "| {id} | {probe} | {version} | {run} | {evidence} |".format(
                id=probe["id"],
                probe=probe["status"],
                version=probe["observed_version"],
                run=run.get("status", "NOT_RUN"),
                evidence=run.get("report", run.get("message", "-")),
            )
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_report = HARNESS.redact_sensitive(report)
    (output_dir / f"{prefix}.json").write_text(
        json.dumps(safe_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / f"{prefix}.md").write_text(render_markdown(safe_report), encoding="utf-8")


def display_report_path(path: Path) -> str:
    """Avoid exposing a host-local path in the CLI summary."""

    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return f"external:report/{path.name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="跨 CLI 真实 forward-test 矩阵")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--clients", nargs="+", help="要测试的 profile id；默认全部")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-prefix", default="client-matrix")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行真实 Agent CLI；还必须明确传入 --allow-unsafe-host-execution。",
    )
    parser.add_argument(
        "--allow-unsafe-host-execution",
        action="store_true",
        help="确认当前不是 OS/容器沙箱；优先在外部沙箱中运行真实样本。",
    )
    parser.add_argument(
        "--agent-env-file",
        type=Path,
        help="仅传入 Agent 子进程的 KEY=VALUE 文件；其值会从持久化报告中脱敏。",
    )
    return parser.parse_args()


def main() -> int:
    HARNESS.configure_utf8_stdio()
    args = parse_args()
    try:
        profiles = load_profiles(args.profiles)
        selected_ids = args.clients or list(profiles)
        unknown = [profile_id for profile_id in selected_ids if profile_id not in profiles]
        if unknown:
            raise ValueError(f"未知 profile: {', '.join(unknown)}")
        selected = [profiles[profile_id] for profile_id in selected_ids]
    except ValueError as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False))
        return 1

    probes = [probe_profile(profile) for profile in selected]
    runs: list[dict[str, Any]] = []
    execution_authorized = args.execute and args.allow_unsafe_host_execution
    agent_env: dict[str, str] = {}
    if execution_authorized:
        try:
            agent_env = HARNESS.load_agent_env_file(args.agent_env_file)
        except ValueError as error:
            print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False))
            return 1
    if args.execute and not args.allow_unsafe_host_execution:
        runs = [
            {
                "id": profile["id"],
                "status": "NOT_RUN",
                "message": "未确认非隔离宿主执行；未调用真实 Agent",
            }
            for profile in selected
        ]
    elif execution_authorized:
        for profile, probe in zip(selected, probes, strict=True):
            if probe["status"] != "AVAILABLE":
                runs.append(
                    {
                        "id": profile["id"],
                        "status": "NOT_RUN",
                        "message": "本机探测失败，未调用真实 Agent",
                    }
                )
                continue
            runs.append(
                execute_profile(
                    profile, args.output_dir, args.report_prefix, agent_env
                )
            )

    if not execution_authorized:
        status = "NOT_RUN"
    elif all(run.get("status") == "PASS" for run in runs) and len(runs) == len(selected):
        status = "PASS"
    elif any(run.get("status") == "FAIL" for run in runs):
        status = "FAIL"
    else:
        status = "PARTIAL"
    report = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": (
            "real_agent_cli"
            if execution_authorized
            else "execution_blocked" if args.execute else "probe_only"
        ),
        "status": status,
        "skill": {
            "path": "skills/production-delivery-orchestrator",
            "sha256": HARNESS.skill_artifact_sha256(HARNESS.SKILL_DIR),
        },
        "probes": probes,
        "runs": runs,
    }
    write_report(report, args.output_dir, args.report_prefix)
    print(
        json.dumps(
            {
                "status": status,
                "report": display_report_path(
                    args.output_dir / f"{args.report_prefix}.json"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "PASS" else 2 if status == "NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
