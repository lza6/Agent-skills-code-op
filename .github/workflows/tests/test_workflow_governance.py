from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOW_PATHS = (
    WORKFLOW_DIR / "release.yml",
    WORKFLOW_DIR / "skill-evals.yml",
)
USES_PATTERN = re.compile(
    r"^\s*-\s+uses:\s+(?P<action>[^@\s]+)@(?P<ref>[^\s#]+)", re.MULTILINE
)
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
CREDENTIAL_PATTERNS = (
    re.compile(r"gh" + r"[pousr]_" + r"[A-Za-z0-9]{20,}"),
    re.compile(r"github" + r"_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----"),
    re.compile(r"sk" + r"-(?:proj-)?[A-Za-z0-9_-]{20,}"),
)
SENSITIVE_SOURCE_ROOTS = (
    REPO_ROOT / ".github",
    REPO_ROOT / "release",
    REPO_ROOT / "skills" / "production-delivery-orchestrator",
)


def job_block(workflow: str, job_name: str) -> str:
    match = re.search(
        rf"^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"缺少 jobs.{job_name}")
    return match.group(0)


class WorkflowGovernanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.release = (WORKFLOW_DIR / "release.yml").read_text(encoding="utf-8")
        self.skill_evals = (WORKFLOW_DIR / "skill-evals.yml").read_text(
            encoding="utf-8"
        )

    def test_all_actions_are_pinned_to_full_commit_shas(self) -> None:
        for workflow_path in WORKFLOW_PATHS:
            workflow = workflow_path.read_text(encoding="utf-8")
            matches = list(USES_PATTERN.finditer(workflow))
            self.assertTrue(matches, workflow_path)
            for match in matches:
                with self.subTest(workflow=workflow_path.name, action=match["action"]):
                    self.assertRegex(match["ref"], SHA_PATTERN)

    def test_release_publish_depends_on_its_own_quality_job(self) -> None:
        self.assertIn('tags:\n      - "v*"', self.release)
        self.assertNotIn("workflow_run", self.release)

        quality = job_block(self.release, "quality")
        publish = job_block(self.release, "publish")
        self.assertRegex(quality, r"(?m)^    permissions:\n      contents: read$")
        self.assertNotRegex(quality, r"(?m)^\s+(?:contents|attestations|id-token): write$")
        self.assertRegex(publish, r"(?m)^    needs: quality$")
        self.assertNotIn("skill-evals", publish)
        self.assertRegex(
            publish,
            r"(?m)^    permissions:\n      contents: write\n      attestations: write\n      id-token: write$",
        )
        self.assertNotIn("Build and verify deterministic release artifacts", quality)
        self.assertLess(
            self.release.index("  publish:"),
            self.release.index("Build and verify deterministic release artifacts"),
        )

    def test_workflow_default_permissions_and_quality_token_scope_are_minimal(self) -> None:
        for workflow_path in WORKFLOW_PATHS:
            workflow = workflow_path.read_text(encoding="utf-8")
            header = workflow.split("jobs:\n", 1)[0]
            self.assertRegex(header, r"(?m)^permissions:\n  contents: read$")

        quality = job_block(self.release, "quality")
        self.assertNotIn("github.token", quality)
        self.assertNotIn("secrets.", quality)

    def test_changed_range_whitespace_checks_cover_pull_requests_and_pushes(self) -> None:
        for workflow_name, workflow in (
            ("release.yml", self.release),
            ("skill-evals.yml", self.skill_evals),
        ):
            with self.subTest(workflow=workflow_name):
                self.assertIn("github.event.pull_request.base.sha", workflow)
                self.assertIn("github.event.before", workflow)
                self.assertIn("github.ref_type", workflow)
                self.assertIn('git diff --check "$base_sha" "$head_sha"', workflow)
                self.assertIn('git rev-parse "${head_sha}^{}"', workflow)
                self.assertNotRegex(
                    workflow,
                    r"(?m)^\s*run:\s+git diff --check\s*$",
                )

    def test_sensitive_delivery_sources_have_no_known_credential_patterns(self) -> None:
        findings: list[str] = []
        for root in SENSITIVE_SOURCE_ROOTS:
            for path in root.rglob("*"):
                if not path.is_file() or "tests" in path.parts:
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for pattern in CREDENTIAL_PATTERNS:
                    if pattern.search(content):
                        findings.append(str(path.relative_to(REPO_ROOT)))
                        break
        self.assertEqual(findings, [])

    def test_credential_scanner_patterns_detect_representative_values(self) -> None:
        representative_values = (
            "ghp_" + "a" * 36,
            "github_pat_" + "a" * 82,
            "AKIA" + "A" * 16,
            "-----BEGIN PRIVATE KEY-----",
            "sk-proj-" + "a" * 32,
        )
        for value in representative_values:
            with self.subTest(value=value[:8]):
                self.assertTrue(any(pattern.search(value) for pattern in CREDENTIAL_PATTERNS))


if __name__ == "__main__":
    unittest.main()
