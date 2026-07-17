from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parents[1]
RUNNER_PATH = EVAL_DIR / "run_evals.py"

SPEC = importlib.util.spec_from_file_location("production_delivery_evals", RUNNER_PATH)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class PortableReportPathTest(unittest.TestCase):
    def evaluation_args(self, **overrides: object) -> argparse.Namespace:
        values: dict[str, object] = {
            "baseline": None,
            "baseline_git_ref": RUNNER.DEFAULT_BASELINE_GIT_REF,
            "skill_relative_path": RUNNER.DEFAULT_SKILL_RELATIVE_PATH,
            "candidate": RUNNER.DEFAULT_CANDIDATE,
            "rubric": EVAL_DIR / "rubric.yaml",
            "cases": EVAL_DIR / "cases.yaml",
            "fixture": RUNNER.DEFAULT_FIXTURE,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_repo_paths_use_posix_relative_display_on_windows_and_unix(self) -> None:
        cases = (
            (
                r"C:\Users\alice\workspace\repo",
                r"C:\Users\alice\workspace\repo\evals\cases.yaml",
            ),
            ("/home/alice/workspace/repo", "/home/alice/workspace/repo/evals/cases.yaml"),
        )
        for repo_root, path in cases:
            with self.subTest(repo_root=repo_root):
                self.assertEqual(
                    RUNNER.display_path(path, repo_root=repo_root),
                    "evals/cases.yaml",
                )

    def test_external_windows_and_unix_paths_are_explicit_and_redacted(self) -> None:
        cases = (
            (
                r"C:\Users\PrivateWindowsUser\candidate",
                r"C:\Users\PrivateWindowsUser\candidate\references\contract.md",
                "PrivateWindowsUser",
            ),
            (
                "/home/private-unix-user/candidate",
                "/home/private-unix-user/candidate/references/contract.md",
                "private-unix-user",
            ),
        )
        for external_root, path, private_name in cases:
            with self.subTest(path=path):
                displayed = RUNNER.display_path(
                    path,
                    repo_root=r"D:\public\repo",
                    external_label="candidate",
                    external_root=external_root,
                )
                self.assertEqual(displayed, "external:candidate/references/contract.md")
                self.assertNotIn(private_name, displayed)

    def test_external_candidate_and_fixture_do_not_expose_their_host_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-portable-report-") as temp:
            private_root = Path(temp) / "PrivateFixtureOwner"
            candidate = private_root / "candidate"
            fixture = private_root / "fixture"
            shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
            shutil.copytree(RUNNER.DEFAULT_FIXTURE, fixture)

            report, exit_code = RUNNER.run_evaluation(
                self.evaluation_args(candidate=candidate, fixture=fixture)
            )
            serialized = json.dumps(report, ensure_ascii=False)
            markdown = RUNNER.render_markdown(report)

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["candidate"]["artifact"]["source"], "external:candidate")
        self.assertEqual(
            report["candidate"]["artifact"]["core_path"],
            "external:candidate/SKILL.md",
        )
        self.assertEqual(report["fixture"]["source"], "external:fixture")
        self.assertIn("- Candidate source：`external:candidate`", markdown)
        self.assertIn("- Fixture source：`external:fixture`", markdown)
        self.assertNotIn("PrivateFixtureOwner", serialized)
        self.assertNotIn(str(private_root), serialized)
        self.assertNotIn("PrivateFixtureOwner", markdown)
        self.assertNotIn(str(private_root), markdown)

    def test_json_and_markdown_reports_do_not_contain_absolute_repo_root(self) -> None:
        report, exit_code = RUNNER.run_evaluation(self.evaluation_args())
        serialized = json.dumps(report, ensure_ascii=False)
        markdown = RUNNER.render_markdown(report)
        repo_roots = {
            str(RUNNER.REPO_ROOT),
            str(RUNNER.REPO_ROOT).replace("\\", "/"),
        }

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            report["metadata"]["cases_file"],
            "evals/production-delivery-orchestrator/cases.yaml",
        )
        self.assertEqual(
            report["candidate"]["artifact"]["source"],
            "skills/production-delivery-orchestrator",
        )
        for repo_root in repo_roots:
            self.assertNotIn(repo_root, serialized)
            self.assertNotIn(repo_root, markdown)

    def test_fingerprint_depends_on_content_not_external_location(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-fingerprint-") as temp:
            root = Path(temp)
            reports = []
            fixtures = []
            for owner in ("PrivateOwnerOne", "PrivateOwnerTwo"):
                candidate = root / owner / "candidate"
                fixture = root / owner / "fixture"
                shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
                shutil.copytree(RUNNER.DEFAULT_FIXTURE, fixture)
                report, exit_code = RUNNER.run_evaluation(
                    self.evaluation_args(candidate=candidate, fixture=fixture)
                )
                self.assertEqual(exit_code, 0)
                reports.append(report)
                fixtures.append(fixture)

            self.assertEqual(
                reports[0]["metadata"]["input_hashes"],
                reports[1]["metadata"]["input_hashes"],
            )
            self.assertEqual(
                reports[0]["metadata"]["evaluation_fingerprint"],
                reports[1]["metadata"]["evaluation_fingerprint"],
            )

            fixture_source = fixtures[1] / "frontend" / "useVideoJob.ts"
            fixture_source.write_text(
                fixture_source.read_text(encoding="utf-8")
                + "\n// fingerprint content regression\n",
                encoding="utf-8",
            )
            changed_report, changed_exit_code = RUNNER.run_evaluation(
                self.evaluation_args(
                    candidate=root / "PrivateOwnerTwo" / "candidate",
                    fixture=fixtures[1],
                )
            )

        self.assertEqual(changed_exit_code, 0)
        self.assertNotEqual(
            reports[1]["metadata"]["evaluation_fingerprint"],
            changed_report["metadata"]["evaluation_fingerprint"],
        )

    def test_fixture_tree_hash_is_cross_platform_stable(self) -> None:
        self.assertEqual(
            RUNNER.sha256_directory(RUNNER.DEFAULT_FIXTURE),
            "ef8c26f857e4402278d45ed6d724b7ca636bcb1b89aaf4ac227d49e2430f5ef3",
        )

    def test_reference_rename_invalidates_artifact_tree_and_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-reference-rename-") as temp:
            candidate = Path(temp) / "candidate"
            shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
            before, before_exit = RUNNER.run_evaluation(
                self.evaluation_args(candidate=candidate)
            )

            references = candidate / "references"
            (references / "system-prompt.md").rename(
                references / "system-proxy.md"
            )
            after, after_exit = RUNNER.run_evaluation(
                self.evaluation_args(candidate=candidate)
            )

        self.assertEqual(before_exit, 0)
        self.assertEqual(after_exit, 0)
        self.assertNotEqual(
            before["candidate"]["artifact"]["tree_sha256"],
            after["candidate"]["artifact"]["tree_sha256"],
        )
        self.assertNotEqual(
            before["metadata"]["evaluation_fingerprint"],
            after["metadata"]["evaluation_fingerprint"],
        )

    def test_collaboration_contract_is_routed_and_detects_missing_ownership_rules(
        self,
    ) -> None:
        rubric = RUNNER.load_json_yaml(EVAL_DIR / "rubric.yaml")
        check = next(
            item
            for item in rubric["checks"]
            if item["id"] == "collaboration-merge-isolation"
        )
        fixture = RUNNER.analyze_fixture(RUNNER.DEFAULT_FIXTURE)
        current = RUNNER.load_artifact(RUNNER.DEFAULT_CANDIDATE, "current")
        self.assertTrue(
            RUNNER.evaluate_check(current, check, fixture, rubric).passed
        )

        with tempfile.TemporaryDirectory(prefix="pdo-collaboration-contract-") as temp:
            candidate = Path(temp) / "candidate"
            shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
            contract = candidate / "references" / "collaboration-contract.md"
            contract.write_text("只说明协作，不提供所有权或合并规则。\n", encoding="utf-8")
            weakened = RUNNER.load_artifact(candidate, "weakened")
            self.assertFalse(
                RUNNER.evaluate_check(weakened, check, fixture, rubric).passed
            )

    def test_adaptive_contract_is_routed_and_detects_missing_rigor_rules(self) -> None:
        rubric = RUNNER.load_json_yaml(EVAL_DIR / "rubric.yaml")
        check = next(
            item
            for item in rubric["checks"]
            if item["id"] == "adaptive-rigor-routing"
        )
        fixture = RUNNER.analyze_fixture(RUNNER.DEFAULT_FIXTURE)
        current = RUNNER.load_artifact(RUNNER.DEFAULT_CANDIDATE, "current")
        self.assertTrue(
            RUNNER.evaluate_check(current, check, fixture, rubric).passed
        )

        with tempfile.TemporaryDirectory(prefix="pdo-adaptive-contract-") as temp:
            candidate = Path(temp) / "candidate"
            shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
            contract = candidate / "references" / "adaptive-delivery-contract.md"
            contract.write_text("只要求所有任务运行扫描器和完整 TDD。\n", encoding="utf-8")
            weakened = RUNNER.load_artifact(candidate, "weakened")
            self.assertFalse(
                RUNNER.evaluate_check(weakened, check, fixture, rubric).passed
            )

    def test_validation_contract_is_routed_and_detects_missing_completion_gate(self) -> None:
        rubric = RUNNER.load_json_yaml(EVAL_DIR / "rubric.yaml")
        check = next(
            item
            for item in rubric["checks"]
            if item["id"] == "fresh-evidence-completion-gate"
        )
        fixture = RUNNER.analyze_fixture(RUNNER.DEFAULT_FIXTURE)
        current = RUNNER.load_artifact(RUNNER.DEFAULT_CANDIDATE, "current")
        self.assertTrue(
            RUNNER.evaluate_check(current, check, fixture, rubric).passed
        )

        with tempfile.TemporaryDirectory(prefix="pdo-validation-contract-") as temp:
            candidate = Path(temp) / "candidate"
            shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
            contract = candidate / "references" / "validation-contract.md"
            contract.write_text("只要求运行全部测试后宣布完成。\n", encoding="utf-8")
            weakened = RUNNER.load_artifact(candidate, "weakened")
            self.assertFalse(
                RUNNER.evaluate_check(weakened, check, fixture, rubric).passed
            )

    def test_discovery_contract_is_routed_and_detects_missing_experiment_rules(self) -> None:
        rubric = RUNNER.load_json_yaml(EVAL_DIR / "rubric.yaml")
        check = next(
            item
            for item in rubric["checks"]
            if item["id"] == "single-hypothesis-minimal-experiment"
        )
        fixture = RUNNER.analyze_fixture(RUNNER.DEFAULT_FIXTURE)
        current = RUNNER.load_artifact(RUNNER.DEFAULT_CANDIDATE, "current")
        self.assertTrue(
            RUNNER.evaluate_check(current, check, fixture, rubric).passed
        )

        with tempfile.TemporaryDirectory(prefix="pdo-discovery-contract-") as temp:
            candidate = Path(temp) / "candidate"
            shutil.copytree(RUNNER.DEFAULT_CANDIDATE, candidate)
            contract = candidate / "references" / "discovery-contract.md"
            contract.write_text("找到第一个匹配结果后立即修复。\n", encoding="utf-8")
            weakened = RUNNER.load_artifact(candidate, "weakened")
            self.assertFalse(
                RUNNER.evaluate_check(weakened, check, fixture, rubric).passed
            )

    def test_cli_summary_redacts_external_output_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-cli-summary-") as temp:
            private_output = Path(temp) / "PrivateReportOwner"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER_PATH),
                    "--output-dir",
                    str(private_output),
                    "--report-prefix",
                    "cli",
                ],
                cwd=RUNNER.REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONUTF8": "1",
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["json_report"], "external:report/cli.json")
        self.assertEqual(summary["markdown_report"], "external:report/cli.md")
        self.assertNotIn("PrivateReportOwner", result.stdout)
        self.assertNotIn(str(private_output), result.stdout)


if __name__ == "__main__":
    unittest.main()
