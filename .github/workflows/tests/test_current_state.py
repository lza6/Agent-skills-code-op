from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
README_PATH = REPO_ROOT / "README.md"
METADATA_PATH = REPO_ROOT / "release" / "metadata.json"
RELEASE_NOTE_PATH = REPO_ROOT / "docs" / "releases" / "v1.7.0.md"
WORKFLOW_STATUS_PATH = REPO_ROOT / "workflow_status.md"
CURRENT_STATE_PATH = REPO_ROOT / "docs" / "current-state.md"

STABLE_TAG = "v1.7.0"
RELEASE_COMMIT = "80b416ecd73d953dc0ead66c9996b142d21a7ecd"
MAIN_ACTION_RUN = "29639353470"
TAG_ACTION_RUN = "29639416337"
RELEASE_ASSET_SHA256 = "199f9fc66dd8739238c100588b3a1616838597ae5bd7cb0f41b724da6bf17c99"


def markdown_section(markdown: str, heading_prefix: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading_prefix)}[^\n]*\n(?P<section>.*?)(?=^## |\Z)",
        markdown,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"缺少当前段：{heading_prefix}")
    return match.group(0)


class CurrentStateConsistencyTest(unittest.TestCase):
    """Lock only the live release facts, never historic audits or main HEAD."""

    def setUp(self) -> None:
        self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        self.readme = README_PATH.read_text(encoding="utf-8")
        self.release_note = RELEASE_NOTE_PATH.read_text(encoding="utf-8")
        self.workflow_release = markdown_section(
            WORKFLOW_STATUS_PATH.read_text(encoding="utf-8"),
            "当前 v1.7.0 发布闭环",
        )
        self.current_state = CURRENT_STATE_PATH.read_text(encoding="utf-8")

    def test_metadata_readme_and_current_page_use_the_stable_tag(self) -> None:
        self.assertEqual(self.metadata["version"], "1.7.0")
        self.assertEqual(self.metadata["tag"], STABLE_TAG)
        self.assertEqual(self.metadata["release_notes"], "docs/releases/v1.7.0.md")
        self.assertTrue((REPO_ROOT / self.metadata["release_notes"]).is_file())
        self.assertIn("默认锁定稳定版 `v1.7.0`", self.readme)
        self.assertIn("docs/current-state.md", self.readme)
        self.assertIn(f"`{STABLE_TAG}`", self.current_state)
        self.assertIn(f"tree/{STABLE_TAG}", self.current_state)

    def test_release_provenance_facts_agree_with_the_current_page(self) -> None:
        release_facts = (
            RELEASE_COMMIT,
            MAIN_ACTION_RUN,
            TAG_ACTION_RUN,
            RELEASE_ASSET_SHA256,
        )
        for fact in release_facts:
            with self.subTest(fact=fact):
                self.assertIn(fact, self.release_note)
                self.assertIn(fact, self.current_state)

        for link in (
            "https://github.com/lza6/Agent-skills-code-op/releases/tag/v1.7.0",
            f"https://github.com/lza6/Agent-skills-code-op/actions/runs/{MAIN_ACTION_RUN}",
            f"https://github.com/lza6/Agent-skills-code-op/actions/runs/{TAG_ACTION_RUN}",
        ):
            with self.subTest(link=link):
                self.assertIn(link, self.current_state)

    def test_workflow_current_segment_and_page_preserve_release_and_r5_status(self) -> None:
        for fact in (RELEASE_COMMIT, TAG_ACTION_RUN, RELEASE_ASSET_SHA256):
            with self.subTest(fact=fact):
                self.assertIn(fact, self.workflow_release)
                self.assertIn(fact, self.current_state)

        for milestone in range(1, 5):
            self.assertRegex(
                self.workflow_release,
                rf"\| R{milestone} \| .*? \| passed \|",
            )
        self.assertRegex(self.workflow_release, r"\| R5 \| .*? \| partial \|")
        self.assertIn("R5：partial", self.current_state)

    def test_real_cli_matrix_is_partial_not_a_cross_client_pass(self) -> None:
        release_matrix_facts = (
            "Codex CLI `0.144.5` 在 hardened runner 的三条 fixture 用户旅程均 PASS",
            "Claude Code `2.1.212` 已实际执行",
            "Gemini CLI `0.51.0`",
            "完整三客户端真实行为矩阵仍未完成",
        )
        for fact in release_matrix_facts:
            with self.subTest(fact=fact):
                self.assertIn(fact, self.release_note)

        page_matrix_facts = (
            "Codex CLI `0.144.5`：新 hardened runner 的 `3/3 PASS`",
            "Claude Code `2.1.212`：实际执行但本机 OAuth 账户没有可用模型",
            "Gemini CLI `0.51.0`：未提供隔离 API/Vertex 凭证",
            "不是跨客户端通过，也不是技能行为失败",
        )
        for fact in page_matrix_facts:
            with self.subTest(fact=fact):
                self.assertIn(fact, self.current_state)

        for fact in (
            "默认实跑仅接受仓库外的 `--agent-env-file`",
            "`--execute --allow-unsafe-host-execution --allow-host-client-config`",
            "`--allow-host-network-configuration`",
            "Gemini 没有 host-config fallback",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, self.current_state)

    def test_registry_scope_and_historical_boundary_are_explicit(self) -> None:
        self.assertIn(
            "当前 CLI profile 配置包含基于本机 `--help` 核对的 Codex CLI、Claude Code 和 Gemini CLI 命令模板",
            self.readme,
        )
        self.assertIn("[技能 registry](../skills/registry.json)", self.current_state)
        self.assertIn("当前包含一个技能 `production-delivery-orchestrator`", self.current_state)
        self.assertIn("Codex CLI、Claude Code、Gemini CLI 三个命令模板", self.current_state)
        self.assertIn(RELEASE_COMMIT, self.current_state)
        self.assertIn(MAIN_ACTION_RUN, self.current_state)
        self.assertIn(
            f"https://github.com/lza6/Agent-skills-code-op/actions/runs/{MAIN_ACTION_RUN}",
            self.current_state,
        )
        self.assertIn("不把 `main` HEAD 视为固定发布事实", self.current_state)
        self.assertIn("历史审计和历史 release 说明不是本页的 current-state", self.current_state)


if __name__ == "__main__":
    unittest.main()
