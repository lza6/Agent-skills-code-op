from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "tools" / "build_skill_registry.py"
REGISTRY_PATH = REPO_ROOT / "skills" / "registry.json"


def load_registry_module() -> object:
    spec = importlib.util.spec_from_file_location("skill_registry_test_module", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 build_skill_registry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_skill(root: Path, directory: str, name: str, description: str) -> None:
    skill_dir = root / "skills" / directory
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
        newline="\n",
    )


class SkillRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry_module()

    def test_builds_name_sorted_portable_registry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-registry-") as temp:
            root = Path(temp)
            write_skill(root, "zeta", "zeta", "Zeta automation")
            write_skill(root, "alpha", "alpha", "Alpha delivery")

            registry = self.registry.build_registry(root)

        self.assertEqual(registry["schema"], 1)
        self.assertEqual([entry["name"] for entry in registry["skills"]], ["alpha", "zeta"])
        self.assertEqual(
            registry["skills"][0],
            {
                "description": "Alpha delivery",
                "name": "alpha",
                "path": "skills/alpha/SKILL.md",
            },
        )
        self.assertNotIn(str(root), json.dumps(registry, ensure_ascii=False))

    def test_committed_registry_matches_the_current_single_skill(self) -> None:
        expected = self.registry.build_registry(REPO_ROOT)
        actual = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

        self.assertEqual(actual, expected)
        self.assertEqual(
            [entry["name"] for entry in actual["skills"]],
            ["production-delivery-orchestrator"],
        )

    def test_rejects_invalid_frontmatter_and_duplicate_skill_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-registry-invalid-") as temp:
            root = Path(temp)
            malformed = root / "skills" / "broken" / "SKILL.md"
            malformed.parent.mkdir(parents=True)
            malformed.write_text("name: broken\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frontmatter"):
                self.registry.build_registry(root)

            malformed.unlink()
            write_skill(root, "one", "same-name", "First")
            write_skill(root, "two", "same-name", "Second")
            with self.assertRaisesRegex(ValueError, "重复"):
                self.registry.build_registry(root)

    def test_check_detects_registry_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-registry-check-") as temp:
            root = Path(temp)
            output = root / "skills" / "registry.json"
            write_skill(root, "alpha", "alpha", "Alpha delivery")
            self.registry.write_registry(root, output)
            self.assertTrue(self.registry.registry_matches(root, output))

            write_skill(root, "beta", "beta", "Beta delivery")
            self.assertFalse(self.registry.registry_matches(root, output))

            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--root", str(root), "--output", str(output), "--check"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("漂移", result.stderr)

    def test_query_returns_stable_relevant_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-registry-query-") as temp:
            root = Path(temp)
            write_skill(root, "zeta", "zeta", "Unrelated automation")
            write_skill(root, "alpha", "alpha-delivery", "Production delivery workflow")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--query",
                    "delivery production",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["query"], "delivery production")
        self.assertEqual([entry["name"] for entry in report["skills"]], ["alpha-delivery"])


if __name__ == "__main__":
    unittest.main()
