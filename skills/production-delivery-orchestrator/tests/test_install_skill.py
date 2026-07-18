from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = SKILL_ROOT / "scripts" / "install_skill.py"
SKILL_NAME = "production-delivery-orchestrator"
START_MARKER = "<!-- production-delivery-orchestrator:start -->"
END_MARKER = "<!-- production-delivery-orchestrator:end -->"
REFERENCE_LINK_RE = re.compile(r"`(references/[A-Za-z0-9_.\-/]+\.md)`")


def run_installer(
    *args: str,
    installer: Path = INSTALLER,
    home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONUTF8": "1"}
    if home is not None:
        env.update({"HOME": str(home), "USERPROFILE": str(home)})
    return subprocess.run(
        [sys.executable, str(installer), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def load_installer_module() -> object:
    spec = importlib.util.spec_from_file_location("install_skill_test_module", INSTALLER)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载安装器模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallSkillIntegrationTest(unittest.TestCase):
    def _symlink_directory_or_skip(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"当前环境不支持目录符号链接：{error}")

    def _write_journal(
        self,
        installer: object,
        project: Path,
        state: str,
        records: list[dict[str, object]],
    ) -> Path:
        transaction = installer.InstallTransaction(project)
        transaction.backup_root.mkdir()
        payload = {
            "schema": 1,
            "skill": SKILL_NAME,
            "state": state,
            "backup_dir": str(transaction.backup_root),
            "records": records,
            "created_directories": [],
        }
        transaction.journal_path.write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return transaction.journal_path

    def test_configure_console_utf8_reconfigures_standard_streams_when_supported(self) -> None:
        installer = load_installer_module()
        stdout = mock.Mock()
        stderr = mock.Mock()

        with (
            mock.patch.object(installer.sys, "stdout", stdout),
            mock.patch.object(installer.sys, "stderr", stderr),
        ):
            installer.configure_console_utf8()

        stdout.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="backslashreplace"
        )
        stderr.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="backslashreplace"
        )

    def test_configure_console_utf8_tolerates_unconfigurable_streams(self) -> None:
        installer = load_installer_module()
        stdout = mock.Mock(reconfigure=mock.Mock(side_effect=ValueError("closed")))
        stderr = object()

        with (
            mock.patch.object(installer.sys, "stdout", stdout),
            mock.patch.object(installer.sys, "stderr", stderr),
        ):
            installer.configure_console_utf8()

        stdout.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="backslashreplace"
        )

    def test_dry_run_does_not_create_project_or_installation_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-dry-run-test-") as temp:
            project = Path(temp) / "not-created"
            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "all",
                "--bridges",
                "all",
                "--dry-run",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(project.exists())

    def test_user_scope_native_install_is_not_subject_to_project_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-user-scope-test-") as temp:
            home = Path(temp) / "home"
            result = run_installer(
                "--scope",
                "user",
                "--targets",
                "all",
                home=home,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for native_dir in (".codex", ".claude", ".agents"):
                installed = home / native_dir / "skills" / SKILL_NAME
                self.assertTrue((installed / "SKILL.md").is_file())

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

    def test_standard_bridge_cannot_follow_parent_symlink_outside_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-bridge-link-test-") as temp:
            root = Path(temp)
            project = root / "project"
            outside = root / "outside"
            project.mkdir()
            outside.mkdir()
            linked_parent = project / ".github"
            try:
                linked_parent.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"当前环境不支持目录符号链接：{error}")

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--bridges",
                "copilot",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("越出了项目目录", result.stderr)
            self.assertFalse((outside / "copilot-instructions.md").exists())
            self.assertFalse((project / ".agents").exists())

    def test_project_native_targets_cannot_follow_parent_symlink_outside_project(
        self,
    ) -> None:
        cases = (
            ("agents", ".agents", ()),
            ("codex", ".codex", ("--force",)),
            ("claude", ".claude", ("--dry-run",)),
        )
        for target, native_dir, mode_args in cases:
            with self.subTest(target=target, mode_args=mode_args):
                with tempfile.TemporaryDirectory(
                    prefix=f"pdo-native-{target}-link-test-"
                ) as temp:
                    root = Path(temp)
                    project = root / "project"
                    outside = root / "outside"
                    project.mkdir()
                    outside.mkdir()
                    self._symlink_directory_or_skip(project / native_dir, outside)

                    external_install = outside / "skills" / SKILL_NAME
                    sentinel = external_install / "sentinel.txt"
                    if "--force" in mode_args:
                        external_install.mkdir(parents=True)
                        sentinel.write_text("do not replace", encoding="utf-8")

                    result = run_installer(
                        "--scope",
                        "project",
                        "--project-dir",
                        str(project),
                        "--targets",
                        target,
                        *mode_args,
                    )

                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("越出了项目目录", result.stderr)
                    if sentinel.exists():
                        self.assertEqual(
                            sentinel.read_text(encoding="utf-8"), "do not replace"
                        )
                    else:
                        self.assertFalse(external_install.exists())

    def test_unsafe_project_native_target_fails_before_any_partial_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-native-preflight-test-") as temp:
            root = Path(temp)
            project = root / "project"
            outside = root / "outside"
            project.mkdir()
            outside.mkdir()
            self._symlink_directory_or_skip(project / ".claude", outside)

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "all",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("越出了项目目录", result.stderr)
            self.assertFalse((project / ".codex").exists())
            self.assertFalse((project / ".agents").exists())
            self.assertFalse((outside / "skills" / SKILL_NAME).exists())

    def test_standard_bridge_file_symlink_cannot_escape_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-bridge-file-link-test-") as temp:
            root = Path(temp)
            project = root / "project"
            outside = root / "outside.md"
            project.mkdir()
            outside.write_text("outside\n", encoding="utf-8")
            bridge = project / "AGENTS.md"
            try:
                bridge.symlink_to(outside)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"当前环境不支持文件符号链接：{error}")

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--bridges",
                "agents-md",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("越出了项目目录", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")
            self.assertFalse((project / ".agents").exists())

    def test_reversed_managed_markers_fail_before_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-marker-order-test-") as temp:
            project = Path(temp)
            bridge = project / "AGENTS.md"
            original = f"{END_MARKER}\ninvalid order\n{START_MARKER}\n"
            bridge.write_text(original, encoding="utf-8")

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--bridges",
                "agents-md",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("结束标记必须位于开始标记之后", result.stderr)
            self.assertEqual(bridge.read_text(encoding="utf-8"), original)
            self.assertFalse((project / ".agents").exists())

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

    def test_multi_target_failure_restores_every_prior_target_and_bridge(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-transaction-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            existing_skill = (
                project / ".codex" / "skills" / SKILL_NAME / "original.txt"
            )
            existing_skill.parent.mkdir(parents=True)
            existing_skill.write_text("keep codex installation", encoding="utf-8")
            bridge = project / "AGENTS.md"
            original_bridge = "# Existing project instructions\n"
            bridge.write_text(original_bridge, encoding="utf-8")

            original_update = installer.update_managed_file_transaction

            def fail_after_bridge(*args: object) -> None:
                original_update(*args)
                raise RuntimeError("simulated bridge write failure")

            argv = [
                str(INSTALLER),
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "all",
                "--bridges",
                "agents-md",
                "--force",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    installer, "update_managed_file_transaction", fail_after_bridge
                ),
                self.assertRaisesRegex(RuntimeError, "simulated bridge write failure"),
            ):
                installer.main()

            self.assertEqual(
                existing_skill.read_text(encoding="utf-8"), "keep codex installation"
            )
            self.assertFalse((project / ".claude").exists())
            self.assertFalse((project / ".agents").exists())
            self.assertEqual(bridge.read_text(encoding="utf-8"), original_bridge)
            self.assertFalse((project / installer.InstallTransaction.JOURNAL_FILE).exists())
            self.assertFalse((project / installer.InstallTransaction.BACKUP_DIR).exists())

    def test_recover_rolls_back_a_persisted_incomplete_transaction(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-recover-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            destination = project / ".agents" / "skills" / SKILL_NAME
            transaction = installer.InstallTransaction(project)
            transaction.begin()
            transaction.snapshot(destination, "directory")
            transaction.mark_applying()
            installer.copy_skill_transaction(SKILL_ROOT, destination, transaction)
            self.assertTrue((destination / "SKILL.md").is_file())

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--recover",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(destination.exists())
            self.assertFalse((project / ".agents").exists())
            self.assertFalse((project / installer.InstallTransaction.JOURNAL_FILE).exists())
            self.assertFalse((project / installer.InstallTransaction.BACKUP_DIR).exists())

    def test_existing_journal_blocks_new_install_without_destroying_recovery_data(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-existing-journal-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            journal = self._write_journal(installer, project, "prepared", [])
            original = journal.read_bytes()

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("请先使用 --recover", result.stderr)
            self.assertEqual(journal.read_bytes(), original)
            self.assertTrue((project / installer.InstallTransaction.BACKUP_DIR).is_dir())
            self.assertFalse((project / ".agents").exists())

    def test_recover_rejects_tampered_journal_before_touching_outside_path(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-tampered-journal-test-") as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            outside = root / "outside.txt"
            outside.write_text("must survive", encoding="utf-8")
            journal = self._write_journal(
                installer,
                project,
                "applying",
                [
                    {
                        "path": str(outside.absolute()),
                        "kind": "file",
                        "exists": False,
                        "backup": None,
                    }
                ],
            )

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--recover",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("越出事务根目录", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "must survive")
            self.assertTrue(journal.exists())

    def test_recover_rejects_missing_backup_before_touching_target(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-missing-backup-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            target = project / ".agents" / "skills" / SKILL_NAME
            target.parent.mkdir(parents=True)
            target.write_text("must survive", encoding="utf-8")
            journal = self._write_journal(
                installer,
                project,
                "applying",
                [
                    {
                        "path": str(target.absolute()),
                        "kind": "directory",
                        "exists": True,
                        "backup": "backups/00-directory",
                    }
                ],
            )

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--recover",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("事务备份不存在或不安全", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "must survive")
            self.assertTrue(journal.exists())

    def test_recover_rejects_tampered_journal_before_touching_unrelated_project_file(
        self,
    ) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-unrelated-journal-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            sentinel = project / "keep.txt"
            sentinel.write_text("must survive", encoding="utf-8")
            journal = self._write_journal(
                installer,
                project,
                "applying",
                [
                    {
                        "path": str(sentinel.absolute()),
                        "kind": "file",
                        "exists": False,
                        "backup": None,
                    }
                ],
            )

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--recover",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("不属于本次恢复计划", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must survive")
            self.assertTrue(journal.exists())

    def test_recover_requires_explicit_scope_and_target_plan(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-explicit-recovery-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            target = project / ".codex" / "skills" / SKILL_NAME
            target.mkdir(parents=True)
            sentinel = target / "keep.txt"
            sentinel.write_text("must survive", encoding="utf-8")
            journal = self._write_journal(
                installer,
                project,
                "applying",
                [
                    {
                        "path": str(target.absolute()),
                        "kind": "directory",
                        "exists": False,
                        "backup": None,
                    }
                ],
            )

            result = run_installer(
                "--project-dir",
                str(project),
                "--recover",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("必须显式提供", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must survive")
            self.assertTrue(journal.exists())

    def test_recover_committed_journal_only_cleans_transaction_records(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="pdo-committed-journal-test-") as temp:
            project = Path(temp) / "project"
            project.mkdir()
            journal = self._write_journal(installer, project, "committed", [])
            sentinel = project / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--recover",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(journal.exists())
            self.assertFalse((project / installer.InstallTransaction.BACKUP_DIR).exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_dangling_internal_bridge_symlink_is_rejected_before_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-dangling-bridge-test-") as temp:
            project = Path(temp)
            bridge = project / "AGENTS.md"
            try:
                bridge.symlink_to(project / "managed-instructions.md")
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"当前环境不支持文件符号链接：{error}")

            result = run_installer(
                "--scope",
                "project",
                "--project-dir",
                str(project),
                "--targets",
                "agents",
                "--bridges",
                "agents-md",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("符号链接", result.stderr)
            self.assertTrue(bridge.is_symlink())
            self.assertFalse((project / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
