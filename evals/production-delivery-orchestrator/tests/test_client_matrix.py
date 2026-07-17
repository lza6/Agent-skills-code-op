from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


EVAL_DIR = Path(__file__).resolve().parents[1]
MATRIX_PATH = EVAL_DIR / "run_client_matrix.py"
PROFILE_PATH = EVAL_DIR / "client-profiles.json"

SPEC = importlib.util.spec_from_file_location("production_client_matrix", MATRIX_PATH)
assert SPEC and SPEC.loader
MATRIX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATRIX)


class ClientMatrixTest(unittest.TestCase):
    def test_default_profiles_are_complete_and_use_isolated_placeholders(self) -> None:
        profiles = MATRIX.load_profiles(PROFILE_PATH)
        self.assertEqual(set(profiles), {"codex-cli", "claude-code", "gemini-cli"})
        for profile in profiles.values():
            command = " ".join(profile["agent_command"])
            self.assertIn("{workspace}", command)
            self.assertIn("{skill_dir}", command)
            self.assertIn("{prompt}", command)
            self.assertNotIn("--dangerously", command)
            self.assertNotIn("--yolo", command)
            self.assertNotIn("--add-dir", command)
            self.assertNotIn("--include-directories", command)

    def test_rejects_missing_and_unknown_command_placeholders(self) -> None:
        base = {
            "version": 1,
            "profiles": [
                {
                    "id": "synthetic-cli",
                    "client": "Synthetic CLI",
                    "observed_version": "1.0.0",
                    "executables": {"windows": "synthetic.cmd", "posix": "synthetic"},
                    "probe_args": ["--version"],
                    "configuration": "test only",
                    "agent_args": [
                        "{workspace}",
                        "{skill_dir}",
                        "{unknown}",
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="pdo-client-profiles-") as temp:
            profile_path = Path(temp) / "profiles.json"
            profile_path.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "未知占位符"):
                MATRIX.load_profiles(profile_path)

            base["profiles"][0]["agent_args"] = [
                "{workspace}",
                "{skill_dir}",
            ]
            profile_path.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "缺少占位符"):
                MATRIX.load_profiles(profile_path)

    def test_probe_reports_a_local_executable_without_calling_an_agent(self) -> None:
        profile = {
            "id": "python-cli",
            "client": "Python",
            "observed_version": "1.2.3",
            "probe_command": [sys.executable, "-c", "print('probe-cli 1.2.3')"],
            "configuration": "test",
            "agent_command": [sys.executable, "{workspace}", "{skill_dir}", "{prompt}"],
        }
        result = MATRIX.probe_profile(profile)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["output"], "probe-cli 1.2.3")

        mismatched = {**profile, "observed_version": "1.2.30"}
        mismatch = MATRIX.probe_profile(mismatched)
        self.assertEqual(mismatch["status"], "VERSION_MISMATCH")
        self.assertIn("复核 CLI 参数", mismatch["message"])

        prerelease = {
            **profile,
            "probe_command": [
                sys.executable,
                "-c",
                "print('probe-cli 1.2.3-rc.1')",
            ],
        }
        prerelease_result = MATRIX.probe_profile(prerelease)
        self.assertEqual(prerelease_result["status"], "VERSION_MISMATCH")
        self.assertIsNone(prerelease_result["actual_version"])

    def test_platform_command_resolution_uses_cmd_only_on_windows(self) -> None:
        source = {
            "id": "synthetic-cli",
            "client": "Synthetic CLI",
            "observed_version": "1.2.3",
            "executables": {"windows": "synthetic.cmd", "posix": "synthetic"},
            "probe_args": ["--version"],
            "configuration": "test",
            "agent_args": ["{workspace}", "{skill_dir}", "{prompt}"],
        }
        with mock.patch.object(MATRIX.sys, "platform", "win32"):
            self.assertEqual(MATRIX.validate_profile(source)["probe_command"][0], "synthetic.cmd")
        with mock.patch.object(MATRIX.sys, "platform", "linux"):
            self.assertEqual(MATRIX.validate_profile(source)["probe_command"][0], "synthetic")

    def test_main_probe_only_writes_not_run_report_without_an_agent_call(self) -> None:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        profile = {
            "version": 1,
            "profiles": [
                {
                    "id": "python-cli",
                    "client": "Python",
                    "observed_version": version,
                    "executables": {"windows": sys.executable, "posix": sys.executable},
                    "probe_args": ["--version"],
                    "configuration": "test only",
                    "agent_args": ["{workspace}", "{skill_dir}", "{prompt}"],
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="pdo-matrix-main-") as temp:
            root = Path(temp)
            profile_path = root / "profiles.json"
            output_dir = root / "report"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(MATRIX_PATH),
                    "--profiles",
                    str(profile_path),
                    "--output-dir",
                    str(output_dir),
                    "--execute",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONUTF8": "1"},
            )
            report = json.loads((output_dir / "client-matrix.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "NOT_RUN")
        self.assertEqual(report["mode"], "execution_blocked")
        self.assertEqual(report["status"], "NOT_RUN")
        self.assertEqual(report["runs"][0]["status"], "NOT_RUN")
        self.assertIn("未确认非隔离宿主执行", report["runs"][0]["message"])

    def test_matrix_report_marks_probe_only_as_not_run(self) -> None:
        report = {
            "generated_at": "2026-07-17T00:00:00+00:00",
            "mode": "probe_only",
            "status": "NOT_RUN",
            "skill": {"sha256": "a" * 64},
            "probes": [
                {
                    "id": "codex-cli",
                    "status": "AVAILABLE",
                    "observed_version": "0.144.5",
                }
            ],
            "runs": [],
        }
        markdown = MATRIX.render_markdown(report)
        self.assertIn("NOT_RUN", markdown)
        self.assertIn("不是任何模型行为通过的证据", markdown)

    def test_cli_summary_path_is_repo_relative_or_explicitly_external(self) -> None:
        in_repo = EVAL_DIR / "reports" / "client-matrix" / "probe.json"
        self.assertEqual(
            MATRIX.display_report_path(in_repo),
            "evals/production-delivery-orchestrator/reports/client-matrix/probe.json",
        )
        with tempfile.TemporaryDirectory(prefix="pdo-external-report-") as temp:
            external = Path(temp) / "probe.json"
            self.assertEqual(MATRIX.display_report_path(external), "external:report/probe.json")


if __name__ == "__main__":
    unittest.main()
