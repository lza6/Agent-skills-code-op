from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
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

    def test_rejects_missing_or_forged_record_fields(self) -> None:
        original = json.loads(RECORDED_RUN.read_text(encoding="utf-8"))
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

        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                self.assertTrue(HARNESS.validate_record(mutation))

        with tempfile.TemporaryDirectory(prefix="pdo-bad-record-") as temp:
            path = Path(temp) / "record.json"
            path.write_text(json.dumps(missing_candidate), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(HARNESS.verify_record(path), 1)

    def test_current_record_passes_strict_verification(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = HARNESS.verify_record(RECORDED_RUN)
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PASS")

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
            with mock.patch.object(HARNESS, "run", side_effect=[before, timeout]):
                result = HARNESS.evaluate_case(case, ["agent", "--token", timeout_secret])
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
