from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "tools" / "generate_dependency_inventory.py"
INVENTORY_PATH = REPO_ROOT / "docs" / "dependency-inventory.json"


def load_inventory_module() -> object:
    spec = importlib.util.spec_from_file_location("dependency_inventory_test_module", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 generate_dependency_inventory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DependencyInventoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = load_inventory_module()

    def test_generated_inventory_matches_committed_file_and_declares_stdlib_only(self) -> None:
        expected = self.inventory.build_inventory(REPO_ROOT)
        actual = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

        self.assertEqual(actual, expected)
        self.assertEqual(actual["schema"], 1)
        self.assertEqual(actual["dependency_manifests"], [])
        self.assertEqual(actual["python"], {"third_party_dependencies": "none", "runtime": "stdlib-only"})

    def test_all_tracked_action_references_are_full_commit_shas(self) -> None:
        inventory = self.inventory.build_inventory(REPO_ROOT)
        self.assertTrue(inventory["github_actions"])
        for action in inventory["github_actions"]:
            with self.subTest(action=action["action"], workflow=action["workflow"]):
                self.assertRegex(action["sha"], self.inventory.FULL_SHA_PATTERN)

    def test_check_detects_tracked_workflow_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dependency-inventory-") as temp:
            root = Path(temp)
            workflow = root / ".github" / "workflows" / "checks.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "name: checks\nsteps:\n  - uses: actions/checkout@" + "a" * 40 + "\n",
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", ".github/workflows/checks.yml"], check=True)
            output = root / "docs" / "dependency-inventory.json"
            self.inventory.write_inventory(root, output)
            self.assertTrue(self.inventory.inventory_matches(root, output))

            workflow.write_text(
                "name: checks\nsteps:\n  - uses: actions/setup-python@" + "b" * 40 + "\n",
                encoding="utf-8",
                newline="\n",
            )
            self.assertFalse(self.inventory.inventory_matches(root, output))

    def test_rejects_flow_style_action_use_instead_of_omitting_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dependency-inventory-flow-") as temp:
            root = Path(temp)
            workflow = root / ".github" / "workflows" / "checks.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "name: checks\nsteps:\n  - { uses: actions/checkout@v4 }\n",
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", ".github/workflows/checks.yml"], check=True)
            with self.assertRaisesRegex(ValueError, "flow-style"):
                self.inventory.build_inventory(root)


if __name__ == "__main__":
    unittest.main()
