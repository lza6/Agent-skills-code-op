from __future__ import annotations

import argparse
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
    def test_report_prefix_is_a_safe_file_name_only(self) -> None:
        self.assertEqual(MATRIX.HARNESS.validate_report_prefix("matrix-2026.07"), "matrix-2026.07")
        with tempfile.TemporaryDirectory(prefix="pdo-prefix-") as temp:
            report = {
                "generated_at": "2026-07-18T00:00:00+00:00",
                "mode": "probe_only",
                "status": "NOT_RUN",
                "skill": {"sha256": "a" * 64},
                "probes": [],
                "runs": [],
            }
            for unsafe in ("", ".hidden", "..", "report..old", "../escape", "nested/report", r"nested\\report", r"C:\\report"):
                with self.subTest(unsafe=unsafe):
                    with self.assertRaisesRegex(ValueError, "report-prefix"):
                        MATRIX.write_report(report, Path(temp), unsafe)

    def test_execution_prefix_reserves_space_for_profile_suffix(self) -> None:
        profiles = [{"id": "codex-cli"}]
        self.assertEqual(
            MATRIX.validate_execution_report_prefix("matrix", profiles), "matrix"
        )
        with self.assertRaisesRegex(ValueError, "report-prefix"):
            MATRIX.validate_execution_report_prefix("a" * 128, profiles)

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
            self.assertIn("allowed_env_keys", profile)
            self.assertIn("credential_sets", profile)

        self.assertEqual(
            profiles["codex-cli"]["credential_sets"], [["OPENAI_API_KEY"]]
        )
        self.assertEqual(
            profiles["codex-cli"]["host_config"],
            {"env_key": "CODEX_HOME", "default_dir": ".codex"},
        )
        self.assertIn("--bare", profiles["claude-code"]["agent_command"])
        self.assertEqual(
            profiles["claude-code"]["credential_sets"], [["ANTHROPIC_API_KEY"]]
        )
        self.assertEqual(
            profiles["claude-code"]["host_config"],
            {"env_key": "CLAUDE_CONFIG_DIR", "default_dir": ".claude"},
        )
        self.assertEqual(profiles["claude-code"]["host_config_remove_args"], ["--bare"])
        self.assertIn(
            [
                "GOOGLE_GENAI_USE_VERTEXAI",
                "GOOGLE_CLOUD_PROJECT",
                "GOOGLE_CLOUD_LOCATION",
                "GOOGLE_APPLICATION_CREDENTIALS",
            ],
            profiles["gemini-cli"]["credential_sets"],
        )
        self.assertIn("--skip-trust", profiles["gemini-cli"]["agent_command"])

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
                    "allowed_env_keys": [],
                    "credential_sets": [],
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
            "allowed_env_keys": [],
            "credential_sets": [],
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
            "allowed_env_keys": [],
            "credential_sets": [],
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
                    "allowed_env_keys": [],
                    "credential_sets": [],
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

    def test_probe_uses_minimal_environment_without_host_secrets(self) -> None:
        profile = {
            "id": "python-cli",
            "client": "Python",
            "observed_version": "1.2.3",
            "probe_command": [sys.executable, "-c", "print('probe-cli 1.2.3')"],
        }
        completed = subprocess.CompletedProcess(profile["probe_command"], 0, "probe-cli 1.2.3\n", "")
        with tempfile.TemporaryDirectory(prefix="pdo-probe-env-") as temp:
            with mock.patch.dict(
                os.environ,
                {"PATH": os.environ.get("PATH", ""), "HOST_PROBE_SECRET": "secret"},
                clear=True,
            ):
                with mock.patch.object(
                    MATRIX.HARNESS, "run_bounded_process", return_value=completed
                ) as bounded:
                    result = MATRIX.probe_profile(profile, Path(temp))

        self.assertEqual(result["status"], "AVAILABLE")
        environment = bounded.call_args.kwargs["env"]
        self.assertNotIn("HOST_PROBE_SECRET", environment)
        self.assertIn("HOME", environment)
        self.assertIn("CODEX_HOME", environment)
        self.assertIn("CLAUDE_CONFIG_DIR", environment)

    def test_profile_environment_filters_credentials_and_reports_missing_set(self) -> None:
        profile = {
            "id": "claude-code",
            "allowed_env_keys": ["ANTHROPIC_API_KEY"],
            "credential_sets": [["ANTHROPIC_API_KEY"]],
        }
        filtered, credential_ready = MATRIX.filter_profile_agent_env(
            profile,
            {
                "ANTHROPIC_API_KEY": "anthropic-secret",
                "GEMINI_API_KEY": "gemini-secret",
            },
        )
        self.assertEqual(filtered, {"ANTHROPIC_API_KEY": "anthropic-secret"})
        self.assertTrue(credential_ready)

        filtered, credential_ready = MATRIX.filter_profile_agent_env(
            profile, {"GEMINI_API_KEY": "gemini-secret"}
        )
        self.assertEqual(filtered, {})
        self.assertFalse(credential_ready)

    def test_host_client_config_resolution_exposes_only_supported_existing_root(self) -> None:
        profile = {
            "host_config": {"env_key": "CODEX_HOME", "default_dir": ".codex"}
        }
        with tempfile.TemporaryDirectory(prefix="pdo-host-config-") as temp:
            config_root = Path(temp) / ".codex"
            config_root.mkdir()
            with mock.patch.dict(
                os.environ,
                {"CODEX_HOME": str(config_root), "HOST_SECRET": "secret"},
                clear=True,
            ):
                resolved = MATRIX.resolve_host_client_config(profile)

        self.assertEqual(resolved, {"CODEX_HOME": str(config_root.resolve())})
        self.assertNotIn("HOST_SECRET", resolved or {})
        self.assertIsNone(MATRIX.resolve_host_client_config({"host_config": None}))

    def test_host_client_config_requires_all_execution_opt_ins(self) -> None:
        args = argparse.Namespace(
            profiles=PROFILE_PATH,
            clients=None,
            output_dir=Path(tempfile.gettempdir()),
            report_prefix="matrix",
            execute=False,
            allow_unsafe_host_execution=False,
            allow_host_client_config=True,
            allow_host_network_configuration=False,
            agent_env_file=None,
        )
        with mock.patch.object(MATRIX, "parse_args", return_value=args):
            with mock.patch.object(MATRIX, "load_profiles", return_value={}):
                self.assertEqual(MATRIX.main(), 1)

    def test_host_network_configuration_requires_all_execution_opt_ins(self) -> None:
        args = argparse.Namespace(
            profiles=PROFILE_PATH,
            clients=None,
            output_dir=Path(tempfile.gettempdir()),
            report_prefix="matrix",
            execute=False,
            allow_unsafe_host_execution=False,
            allow_host_client_config=False,
            allow_host_network_configuration=True,
            agent_env_file=None,
        )
        with mock.patch.object(MATRIX, "parse_args", return_value=args):
            with mock.patch.object(MATRIX, "load_profiles", return_value={}):
                self.assertEqual(MATRIX.main(), 1)

    def test_host_network_configuration_reads_only_proxy_keys(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "HTTPS_PROXY": "https://proxy.invalid",
                "NO_PROXY": "localhost",
                "HOST_SECRET": "secret",
            },
            clear=True,
        ):
            resolved = MATRIX.resolve_host_network_environment()
        self.assertEqual(
            resolved,
            {"HTTPS_PROXY": "https://proxy.invalid", "NO_PROXY": "localhost"},
        )
        self.assertNotIn("HOST_SECRET", resolved)

    def test_host_client_config_is_an_explicit_authentication_source(self) -> None:
        profile = {
            "id": "claude-code",
            "client": "Claude Code",
            "observed_version": "2.1.212",
            "configuration": "test",
            "agent_command": ["claude", "--bare", "{workspace}", "{skill_dir}", "{prompt}"],
            "allowed_env_keys": ["ANTHROPIC_API_KEY"],
            "credential_sets": [["ANTHROPIC_API_KEY"]],
            "host_config": {"env_key": "CLAUDE_CONFIG_DIR", "default_dir": ".claude"},
            "host_config_remove_args": ["--bare"],
        }
        with tempfile.TemporaryDirectory(prefix="pdo-host-auth-") as temp:
            args = argparse.Namespace(
                profiles=PROFILE_PATH,
                clients=None,
                output_dir=Path(temp),
                report_prefix="matrix",
                execute=True,
                allow_unsafe_host_execution=True,
                allow_host_client_config=True,
                allow_host_network_configuration=False,
                agent_env_file=None,
            )
            report_box: dict[str, object] = {}
            with mock.patch.object(MATRIX, "parse_args", return_value=args):
                with mock.patch.object(MATRIX, "load_profiles", return_value={profile["id"]: profile}):
                    with mock.patch.object(
                        MATRIX,
                        "probe_profile",
                        return_value={"id": profile["id"], "status": "AVAILABLE"},
                    ):
                        with mock.patch.object(MATRIX.HARNESS, "load_agent_env_file", return_value={}):
                            with mock.patch.object(
                                MATRIX,
                                "resolve_host_client_config",
                                return_value={"CLAUDE_CONFIG_DIR": "external-host-config"},
                            ):
                                with mock.patch.object(
                                    MATRIX,
                                    "execute_profile",
                                    return_value={"id": profile["id"], "status": "PASS"},
                                ) as execute:
                                    with mock.patch.object(
                                        MATRIX,
                                        "write_report",
                                        side_effect=lambda report, *_: report_box.update(report),
                                    ):
                                        with mock.patch.object(
                                            MATRIX.HARNESS,
                                            "skill_artifact_sha256",
                                            return_value="a" * 64,
                                        ):
                                            self.assertEqual(MATRIX.main(), 0)

        self.assertEqual(
            execute.call_args.args[3], {"CLAUDE_CONFIG_DIR": "external-host-config"}
        )
        self.assertEqual(execute.call_args.args[4], "host_config")
        self.assertNotIn("--bare", execute.call_args.args[0]["agent_command"])
        self.assertEqual(report_box["runs"][0]["authentication_source"], "host_config")
        self.assertEqual(report_box["runs"][0]["network_configuration_source"], "isolated")

    def test_missing_required_profile_credentials_is_not_run_without_agent_start(self) -> None:
        profile = {
            "id": "claude-code",
            "client": "Claude Code",
            "observed_version": "2.1.212",
            "configuration": "test",
            "agent_command": ["claude", "--bare", "{workspace}", "{skill_dir}", "{prompt}"],
            "allowed_env_keys": ["ANTHROPIC_API_KEY"],
            "credential_sets": [["ANTHROPIC_API_KEY"]],
        }
        with tempfile.TemporaryDirectory(prefix="pdo-missing-credential-") as temp:
            args = argparse.Namespace(
                profiles=PROFILE_PATH,
                clients=None,
                output_dir=Path(temp),
                report_prefix="matrix",
                execute=True,
                allow_unsafe_host_execution=True,
                allow_host_client_config=False,
                allow_host_network_configuration=False,
                agent_env_file=Path(temp) / "outside.env",
            )
            report_box: dict[str, object] = {}
            with mock.patch.object(MATRIX, "parse_args", return_value=args):
                with mock.patch.object(MATRIX, "load_profiles", return_value={profile["id"]: profile}):
                    with mock.patch.object(
                        MATRIX,
                        "probe_profile",
                        return_value={"id": profile["id"], "status": "AVAILABLE"},
                    ):
                        with mock.patch.object(MATRIX.HARNESS, "load_agent_env_file", return_value={}):
                            with mock.patch.object(MATRIX, "execute_profile") as execute:
                                with mock.patch.object(
                                    MATRIX, "write_report", side_effect=lambda report, *_: report_box.update(report)
                                ):
                                    with mock.patch.object(MATRIX.HARNESS, "skill_artifact_sha256", return_value="a" * 64):
                                        self.assertEqual(MATRIX.main(), 1)

        execute.assert_not_called()
        run = report_box["runs"][0]
        self.assertEqual(run["status"], "NOT_RUN")
        self.assertIn("认证", run["message"])

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
