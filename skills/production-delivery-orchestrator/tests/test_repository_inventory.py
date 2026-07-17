from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "repository_inventory.py"


def load_inventory_module() -> object:
    spec = importlib.util.spec_from_file_location("repository_inventory_test_module", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 repository_inventory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositoryInventoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory_script = load_inventory_module()

    def test_detects_stack_signals_languages_and_candidate_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-inventory-") as temp:
            root = Path(temp)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "index.ts").write_text("export {};\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_api.py").write_text("pass\n", encoding="utf-8")

            report = self.inventory_script.inventory(root)

        self.assertEqual(report["kind"], "optional_repository_inventory")
        self.assertFalse(report["truncated"])
        self.assertEqual(report["languages"], {"Python": 1, "TypeScript": 1})
        self.assertIn({"path": "package.json", "signal": "Node.js package"}, report["signals"])
        self.assertIn({"path": "pyproject.toml", "signal": "Python project"}, report["signals"])
        self.assertEqual(report["entry_candidates"], ["src/index.ts"])
        self.assertEqual(report["test_candidates"], ["tests/test_api.py"])

    def test_excludes_generated_directories_and_marks_bounded_scan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-inventory-limit-") as temp:
            root = Path(temp)
            (root / "a.py").write_text("pass\n", encoding="utf-8")
            (root / "b.py").write_text("pass\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.ts").write_text("export {};\n", encoding="utf-8")

            report = self.inventory_script.inventory(root, max_files=1)

        self.assertEqual(report["files_scanned"], 1)
        self.assertTrue(report["truncated"])
        self.assertNotIn("TypeScript", report["languages"])

    def test_exact_scan_limit_is_not_truncated_and_symlinks_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-inventory-links-") as temp:
            root = Path(temp)
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            linked_file = root / "linked.py"
            linked_directory = root / "linked-directory"
            try:
                linked_file.symlink_to(root / "main.py")
                linked_directory.symlink_to(root, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"当前平台不允许创建测试符号链接: {error}")

            report = self.inventory_script.inventory(root, max_files=1)

        self.assertEqual(report["files_scanned"], 1)
        self.assertFalse(report["truncated"])
        self.assertEqual(report["entry_candidates"], ["main.py"])

    def test_rejects_invalid_root_and_scan_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-inventory-invalid-") as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "不存在"):
                self.inventory_script.inventory(root / "missing")
            with self.assertRaisesRegex(ValueError, "至少为 1"):
                self.inventory_script.inventory(root, max_files=0)

            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--root", str(root), "--max-files", "0"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("至少为 1", result.stderr)

    def test_cli_outputs_portable_json_without_absolute_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-inventory-cli-") as temp:
            root = Path(temp) / "PrivateRepositoryName"
            root.mkdir()
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["entry_candidates"], ["main.py"])
        self.assertNotIn(str(root), result.stdout)


if __name__ == "__main__":
    unittest.main()
