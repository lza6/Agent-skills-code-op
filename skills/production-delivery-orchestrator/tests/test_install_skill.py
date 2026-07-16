from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = SKILL_ROOT / "scripts" / "install_skill.py"
SKILL_NAME = "production-delivery-orchestrator"
START_MARKER = "<!-- production-delivery-orchestrator:start -->"
REFERENCE_LINK_RE = re.compile(r"`(references/[A-Za-z0-9_.\-/]+\.md)`")


def run_installer(*args: str, installer: Path = INSTALLER) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(installer), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )


class InstallSkillIntegrationTest(unittest.TestCase):
    def test_real_project_install_bridges_and_replacement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-install-test-") as temp:
            project = Path(temp)
            common = (
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "all",
                "--bridges",
                "all",
            )

            first = run_installer(*common)
            self.assertEqual(first.returncode, 0, first.stderr)

            links = REFERENCE_LINK_RE.findall(
                (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
            )
            for base in (".codex", ".claude", ".agents"):
                installed = project / base / "skills" / SKILL_NAME
                self.assertTrue((installed / "SKILL.md").is_file())
                self.assertTrue((installed / "agents" / "openai.yaml").is_file())
                for link in links:
                    self.assertTrue((installed / Path(link)).is_file(), link)

            bridge_paths = (
                project / "AGENTS.md",
                project / "CLAUDE.md",
                project / "GEMINI.md",
                project / ".github" / "copilot-instructions.md",
                project / ".cursor" / "rules" / f"{SKILL_NAME}.mdc",
                project / ".windsurf" / "rules" / f"{SKILL_NAME}.md",
                project / ".clinerules" / f"{SKILL_NAME}.md",
            )
            for bridge in bridge_paths:
                content = bridge.read_text(encoding="utf-8")
                self.assertEqual(content.count(START_MARKER), 1, bridge)
                self.assertNotIn("完整读取\n`.agents", content)

            duplicate = run_installer(*common)
            self.assertEqual(duplicate.returncode, 1)
            replaced = run_installer(*common, "--force")
            self.assertEqual(replaced.returncode, 0, replaced.stderr)
            for bridge in bridge_paths:
                self.assertEqual(
                    bridge.read_text(encoding="utf-8").count(START_MARKER), 1
                )

    def test_custom_bridge_cannot_escape_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-escape-test-") as temp:
            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                temp,
                "--targets",
                "agents",
                "--custom-bridge",
                "../escape.md",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("越出了项目目录", result.stderr)

    def test_incomplete_source_is_rejected_before_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-source-test-") as temp:
            copied = Path(temp) / SKILL_NAME
            shutil.copytree(SKILL_ROOT, copied)
            missing = copied / "references" / "validation-contract.md"
            missing.unlink()
            project = Path(temp) / "target"
            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                installer=copied / "scripts" / "install_skill.py",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("技能源文件不完整", result.stderr)
            self.assertFalse((project / ".agents").exists())

    def test_force_refuses_non_directory_destination(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-file-target-test-") as temp:
            project = Path(temp)
            destination = project / ".agents" / "skills" / SKILL_NAME
            destination.parent.mkdir(parents=True)
            destination.write_text("do not delete", encoding="utf-8")
            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--force",
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(destination.read_text(encoding="utf-8"), "do not delete")


if __name__ == "__main__":
    unittest.main()
