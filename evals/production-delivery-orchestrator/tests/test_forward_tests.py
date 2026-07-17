from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


EVAL_DIR = Path(__file__).resolve().parents[1]
HARNESS_PATH = EVAL_DIR / "run_forward_tests.py"
RECORDED_RUN = EVAL_DIR / "reports" / "forward-tests.json"

SPEC = importlib.util.spec_from_file_location("production_forward_tests", HARNESS_PATH)
assert SPEC and SPEC.loader
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class ForwardTestHarnessTest(unittest.TestCase):
    def copy_skill_fixture(self, destination: Path) -> Path:
        skill_dir = destination / "production-delivery-orchestrator"
        shutil.copytree(HARNESS.SKILL_DIR, skill_dir)
        return skill_dir

    def valid_record_for(self, skill_dir: Path) -> dict[str, object]:
        record = json.loads(RECORDED_RUN.read_text(encoding="utf-8"))
        artifact_hash = HARNESS.skill_artifact_sha256(skill_dir)
        record["candidate"]["skill_sha256_at_execution"] = artifact_hash
        record["candidate"]["current_skill_sha256_when_recorded"] = artifact_hash
        return record

    def legacy_raw_artifact_hash(self, skill_dir: Path) -> str:
        digest = hashlib.sha256()
        digest.update(b"production-delivery-orchestrator-artifact-v1\0")
        for path in HARNESS.skill_artifact_files(skill_dir):
            relative_path = path.relative_to(skill_dir).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(len(relative_path).to_bytes(8, byteorder="big"))
            digest.update(relative_path)
            digest.update(len(content).to_bytes(8, byteorder="big"))
            digest.update(content)
        return digest.hexdigest()

    def test_redacts_text_commands_and_persisted_reports(self) -> None:
        secrets = {
            "authorization": "auth-secret-1234567890",
            "bearer": "bearer-secret-1234567890",
            "github": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            "github_pat": "github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            "openai": "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            "anthropic": "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            "assigned": "assigned-secret-1234567890",
            "password": "hunter2-secret-value",
        }
        text = "\n".join(
            [
                f"Authorization: Bearer {secrets['authorization']}",
                f"Bearer {secrets['bearer']}",
                secrets["github"],
                secrets["github_pat"],
                secrets["openai"],
                secrets["anthropic"],
                f"OPENAI_API_KEY={secrets['assigned']}",
                f'{{"password": "{secrets["password"]}"}}',
            ]
        )
        redacted = HARNESS.redact_text(text)
        for secret in secrets.values():
            self.assertNotIn(secret, redacted)
        self.assertIn(HARNESS.REDACTED, redacted)

        command = [
            "agent",
            "--api-key",
            secrets["assigned"],
            "--header",
            f"Authorization: Bearer {secrets['authorization']}",
        ]
        command_text = " ".join(HARNESS.redact_command(command))
        self.assertNotIn(secrets["assigned"], command_text)
        self.assertNotIn(secrets["authorization"], command_text)

        report = {
            "generated_at": "2026-07-17T00:00:00+00:00",
            "client": f"client TOKEN={secrets['assigned']}",
            "model": "synthetic",
            "execution_mode": "synthetic_test",
            "status": "FAIL",
            "raw_stdout": f"Bearer {secrets['bearer']}",
            "raw_stderr": f"ANTHROPIC_API_KEY={secrets['anthropic']}",
            "cases": [
                {
                    "id": "synthetic",
                    "prompt": "synthetic",
                    "status": "FAIL",
                    "agent_exit_code": 1,
                    "before_test_exit_code": 1,
                    "after_test_exit_code": 1,
                    "checks": {"synthetic": False},
                    "git_diff": f"+Authorization: Bearer {secrets['authorization']}",
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="pdo-redaction-test-") as temp:
            output_dir = Path(temp)
            HARNESS.write_report(report, output_dir, "redacted")
            persisted = (output_dir / "redacted.json").read_text(encoding="utf-8")
            persisted += (output_dir / "redacted.md").read_text(encoding="utf-8")
        for secret in secrets.values():
            self.assertNotIn(secret, persisted)

    def test_redacts_ephemeral_workspace_and_skill_paths_from_reports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-forward-paths-") as temp:
            workspace = Path(temp) / "repo"
            payload = {
                "agent_command": [
                    "agent",
                    "--workspace",
                    str(workspace),
                    "read",
                    str(HARNESS.SKILL_DIR / "SKILL.md"),
                ],
                "raw_stdout": f"used {workspace} and {HARNESS.SKILL_DIR}",
            }
            redacted = HARNESS.redact_runtime_paths(payload, workspace)

        rendered = json.dumps(redacted, ensure_ascii=False)
        self.assertNotIn(str(workspace), rendered)
        self.assertNotIn(str(HARNESS.SKILL_DIR), rendered)
        self.assertIn("{workspace}", rendered)
        self.assertIn("{skill_dir}", rendered)

    def test_agent_environment_is_minimal_and_explicit_values_are_redacted(self) -> None:
        opaque_secret = "opaque-aws-secret-value-not-matched-by-a-regex"
        with tempfile.TemporaryDirectory(prefix="pdo-agent-env-") as temp:
            workspace = Path(temp) / "repo"
            workspace.mkdir()
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": os.environ.get("PATH", ""),
                    "OPENAI_API_KEY": "host-openai-secret",
                    "AWS_SECRET_ACCESS_KEY": opaque_secret,
                },
                clear=True,
            ):
                environment = HARNESS.isolated_agent_environment(
                    workspace, {"CUSTOM_AGENT_TOKEN": opaque_secret}
                )

        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)
        self.assertEqual(environment["CUSTOM_AGENT_TOKEN"], opaque_secret)
        self.assertNotEqual(environment["HOME"], str(workspace / ".agent-home"))
        self.assertIn(".agent-home", environment["HOME"])
        rendered = json.dumps(
            HARNESS.redact_runtime_paths(
                {"raw_stdout": f"AWS_SECRET_ACCESS_KEY={opaque_secret}"},
                secret_values=(opaque_secret,),
            ),
            ensure_ascii=False,
        )
        self.assertNotIn(opaque_secret, rendered)
        self.assertIn(HARNESS.REDACTED, rendered)

    def test_explicit_agent_environment_file_cannot_override_controlled_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-agent-env-file-") as temp:
            env_file = Path(temp) / "agent.env"
            env_file.write_text("CUSTOM_AGENT_TOKEN=abc\n", encoding="utf-8")
            self.assertEqual(
                HARNESS.load_agent_env_file(env_file), {"CUSTOM_AGENT_TOKEN": "abc"}
            )
            env_file.write_text("HOME=C:/host\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "受控变量"):
                HARNESS.load_agent_env_file(env_file)

    def test_real_agent_command_requires_explicit_unsafe_host_opt_in(self) -> None:
        args = argparse.Namespace(
            self_test=False,
            verify_record=None,
            agent_command=["agent", "{prompt}"],
            allow_unsafe_host_execution=False,
            agent_env_file=None,
        )
        stderr = io.StringIO()
        with mock.patch.object(HARNESS, "parse_args", return_value=args):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(HARNESS.main(), 2)
        self.assertIn("拒绝在未确认的宿主环境", stderr.getvalue())

    def test_rejects_missing_or_forged_record_fields(self) -> None:
        original = json.loads(RECORDED_RUN.read_text(encoding="utf-8"))
        artifact_hash = HARNESS.skill_artifact_sha256(HARNESS.SKILL_DIR)
        original["candidate"]["skill_sha256_at_execution"] = artifact_hash
        original["candidate"]["current_skill_sha256_when_recorded"] = artifact_hash
        self.assertEqual(HARNESS.validate_record(original), [])
        mutations = []

        missing_candidate = json.loads(json.dumps(original))
        del missing_candidate["candidate"]
        mutations.append(missing_candidate)

        forged_prompt = json.loads(json.dumps(original))
        forged_prompt["cases"][0]["prompt"] = "不同的提示词"
        mutations.append(forged_prompt)

        false_result = json.loads(json.dumps(original))
        false_result["cases"][0]["must_results"]["scanned_before_asking"] = False
        mutations.append(false_result)

        missing_evidence = json.loads(json.dumps(original))
        del missing_evidence["cases"][1]["main_thread_verification"]
        mutations.append(missing_evidence)

        forged_diff = json.loads(json.dumps(original))
        forged_diff["cases"][0]["observed_diff"] = "none"
        mutations.append(forged_diff)

        unavailable_execution_hash = json.loads(json.dumps(original))
        unavailable_execution_hash["candidate"]["skill_sha256_at_execution"] = (
            "unavailable - the runtime did not expose a read-time artifact hash"
        )
        mutations.append(unavailable_execution_hash)

        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                self.assertTrue(HARNESS.validate_record(mutation))

        unavailable_errors = HARNESS.validate_record(unavailable_execution_hash)
        self.assertTrue(any("unavailable" in error for error in unavailable_errors))

        with tempfile.TemporaryDirectory(prefix="pdo-bad-record-") as temp:
            path = Path(temp) / "record.json"
            path.write_text(json.dumps(missing_candidate), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(HARNESS.verify_record(path), 1)

    def test_matching_artifact_record_passes_and_content_change_is_stale(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-content-") as temp:
            skill_dir = self.copy_skill_fixture(Path(temp))
            record = self.valid_record_for(skill_dir)

            with mock.patch.object(HARNESS, "SKILL_DIR", skill_dir):
                self.assertEqual(HARNESS.validate_record(record), [])

                routed_reference = skill_dir / "references" / "discovery-contract.md"
                routed_reference.write_text(
                    routed_reference.read_text(encoding="utf-8")
                    + "\n<!-- artifact freshness regression -->\n",
                    encoding="utf-8",
                )
                errors = HARNESS.validate_record(record)

        self.assertTrue(errors)
        self.assertTrue(any("陈旧" in error or "不匹配" in error for error in errors))

    def test_artifact_hash_ignores_platform_cache_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-cache-") as temp:
            skill_dir = self.copy_skill_fixture(Path(temp))
            original_hash = HARNESS.skill_artifact_sha256(skill_dir)

            cache_dir = skill_dir / "references" / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "generated.pyc").write_bytes(b"platform-specific bytecode")
            (skill_dir / ".DS_Store").write_bytes(b"platform metadata")
            (skill_dir / "scripts" / "standalone.pyc").write_bytes(b"bytecode")

            self.assertEqual(HARNESS.skill_artifact_sha256(skill_dir), original_hash)

    def test_fixture_stages_an_intact_skill_copy_inside_the_git_baseline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-staged-skill-") as temp:
            workspace = Path(temp) / "repo"
            baseline = HARNESS.init_fixture(workspace)
            staged_skill = workspace / ".forward-skill"
            status = HARNESS.run(["git", "status", "--porcelain=v1"], workspace)
            staged_skill_exists = (staged_skill / "SKILL.md").is_file()
            staged_skill_hash = HARNESS.skill_artifact_sha256(staged_skill)

        self.assertRegex(baseline, r"^[0-9a-f]{40}$")
        self.assertTrue(staged_skill_exists)
        self.assertEqual(staged_skill_hash, HARNESS.skill_artifact_sha256(HARNESS.SKILL_DIR))
        self.assertEqual(status.stdout, "")

    def test_utf8_text_eol_variants_have_the_same_artifact_hash(self) -> None:
        hashes: list[str] = []
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-eol-") as temp:
            root = Path(temp)
            for index, content in enumerate(
                (b"alpha\nbeta\n", b"alpha\r\nbeta\r\n", b"alpha\rbeta\r")
            ):
                skill_dir = root / f"skill-{index}"
                skill_dir.mkdir()
                (skill_dir / "contract.md").write_bytes(content)
                hashes.append(HARNESS.skill_artifact_sha256(skill_dir))

        self.assertEqual(len(set(hashes)), 1)

    def test_real_text_content_change_changes_artifact_hash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-text-change-") as temp:
            skill_dir = Path(temp) / "skill"
            skill_dir.mkdir()
            contract = skill_dir / "contract.md"
            contract.write_bytes(b"alpha\r\nbeta\r\n")
            original_hash = HARNESS.skill_artifact_sha256(skill_dir)
            contract.write_bytes(b"alpha\r\ngamma\r\n")

            self.assertNotEqual(
                HARNESS.skill_artifact_sha256(skill_dir), original_hash
            )

    def test_binary_content_is_not_eol_normalized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-binary-") as temp:
            skill_dir = Path(temp) / "skill"
            skill_dir.mkdir()
            artifact = skill_dir / "asset.bin"
            original = b"\x89PNG\r\n\x1a\n\0binary\rpayload"
            normalized_eol = original.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            artifact.write_bytes(original)
            original_hash = HARNESS.skill_artifact_sha256(skill_dir)
            artifact.write_bytes(normalized_eol)

            self.assertNotEqual(
                HARNESS.skill_artifact_sha256(skill_dir), original_hash
            )

    def test_legacy_raw_byte_hash_is_rejected_after_canonicalization(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-legacy-") as temp:
            skill_dir = self.copy_skill_fixture(Path(temp))
            record = self.valid_record_for(skill_dir)
            legacy_hash = self.legacy_raw_artifact_hash(skill_dir)
            record["candidate"]["skill_sha256_at_execution"] = legacy_hash
            record["candidate"]["current_skill_sha256_when_recorded"] = legacy_hash

            with mock.patch.object(HARNESS, "SKILL_DIR", skill_dir):
                errors = HARNESS.validate_record(record)
            canonical_hash = HARNESS.skill_artifact_sha256(skill_dir)

        self.assertNotEqual(legacy_hash, canonical_hash)
        self.assertTrue(any("陈旧" in error or "不匹配" in error for error in errors))

    def test_artifact_hash_fails_closed_for_behavioral_symlinks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-artifact-symlink-") as temp:
            root = Path(temp)
            skill_dir = self.copy_skill_fixture(root)
            target = root / "external-contract.md"
            target.write_text("# External contract\n", encoding="utf-8")
            link = skill_dir / "references" / "linked-contract.md"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"当前平台不允许创建测试符号链接: {exc}")

            with self.assertRaisesRegex(OSError, "符号链接"):
                HARNESS.skill_artifact_sha256(skill_dir)

    def test_added_deleted_or_renamed_reference_invalidates_old_record(self) -> None:
        def add_reference(skill_dir: Path) -> None:
            (skill_dir / "references" / "new-contract.md").write_text(
                "# New contract\n", encoding="utf-8"
            )

        def delete_reference(skill_dir: Path) -> None:
            (skill_dir / "references" / "outcome-contract.md").unlink()

        def rename_reference(skill_dir: Path) -> None:
            source = skill_dir / "references" / "outcome-contract.md"
            source.rename(skill_dir / "references" / "renamed-outcome-contract.md")

        for name, mutate in (
            ("added", add_reference),
            ("deleted", delete_reference),
            ("renamed", rename_reference),
        ):
            with self.subTest(change=name):
                with tempfile.TemporaryDirectory(prefix=f"pdo-artifact-{name}-") as temp:
                    skill_dir = self.copy_skill_fixture(Path(temp))
                    record = self.valid_record_for(skill_dir)
                    with mock.patch.object(HARNESS, "SKILL_DIR", skill_dir):
                        self.assertEqual(HARNESS.validate_record(record), [])
                        mutate(skill_dir)
                        errors = HARNESS.validate_record(record)

                self.assertTrue(errors)
                self.assertTrue(
                    any("陈旧" in error or "不匹配" in error for error in errors)
                )

    def test_current_record_matches_strict_verification_result(self) -> None:
        record = json.loads(RECORDED_RUN.read_text(encoding="utf-8"))
        current_hash = HARNESS.skill_artifact_sha256(HARNESS.SKILL_DIR)
        candidate = record.get("candidate", {})
        hash_is_current = (
            candidate.get("skill_sha256_at_execution") == current_hash
            and candidate.get("current_skill_sha256_when_recorded") == current_hash
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = HARNESS.verify_record(RECORDED_RUN)
        payload = json.loads(output.getvalue())
        if hash_is_current:
            self.assertEqual(result, 0)
            self.assertEqual(payload["status"], "PASS")
        else:
            self.assertEqual(result, 1)
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(
                any("陈旧" in error or "不匹配" in error for error in payload["errors"])
            )

    def test_cli_reconfigures_cp1252_stdout_to_utf8(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-cp1252-output-") as temp:
            invalid_record = Path(temp) / "invalid-record.json"
            invalid_record.write_text("[]\n", encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "cp1252:strict"
            result = subprocess.run(
                [
                    sys.executable,
                    str(HARNESS_PATH),
                    "--verify-record",
                    str(invalid_record),
                ],
                check=False,
                capture_output=True,
                env=environment,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(payload["status"], "FAIL")
        self.assertIn("根记录必须是对象", payload["errors"])
        self.assertNotIn(b"UnicodeEncodeError", result.stderr)

    def test_no_agent_command_returns_not_run_exit_two(self) -> None:
        args = argparse.Namespace(self_test=False, verify_record=None, agent_command=None)
        stderr = io.StringIO()
        with mock.patch.object(HARNESS, "parse_args", return_value=args):
            with contextlib.redirect_stderr(stderr):
                result = HARNESS.main()
        self.assertEqual(result, 2)
        self.assertIn("NOT_RUN", stderr.getvalue())

    def test_timeout_and_infrastructure_errors_are_structured_and_redacted(self) -> None:
        case = HARNESS.CASES[0]
        timeout_secret = "timeout-secret-1234567890"
        before = subprocess.CompletedProcess(HARNESS.TEST_COMMAND, 1, "", "")
        timeout = subprocess.TimeoutExpired(
            ["agent", "--token", timeout_secret],
            600,
            output=f"Bearer {timeout_secret}",
            stderr=f"OPENAI_API_KEY={timeout_secret}",
        )
        with mock.patch.object(HARNESS, "init_fixture", return_value="abcdef0"):
            with mock.patch.object(HARNESS, "skill_artifact_sha256", return_value="hash"):
                with mock.patch.object(HARNESS, "run", return_value=before):
                    with mock.patch.object(HARNESS, "run_agent", side_effect=timeout):
                        result = HARNESS.evaluate_case(
                            case, ["agent", "--token", timeout_secret]
                        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["error"]["kind"], "timeout")
        self.assertNotIn(timeout_secret, json.dumps(result, ensure_ascii=False))

        infrastructure_secret = "infra-secret-1234567890"
        with mock.patch.object(
            HARNESS,
            "init_fixture",
            side_effect=RuntimeError(f"ANTHROPIC_API_KEY={infrastructure_secret}"),
        ):
            result = HARNESS.evaluate_case(case, ["missing-agent"])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["error"]["kind"], "infrastructure_error")
        self.assertNotIn(infrastructure_secret, json.dumps(result, ensure_ascii=False))

    def test_self_test_is_explicitly_synthetic(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = HARNESS.self_test()
        self.assertEqual(result, 0)
        self.assertIn("synthetic harness self-test", output.getvalue())
        self.assertIn("不是真实 Agent forward-test", output.getvalue())


if __name__ == "__main__":
    unittest.main()
