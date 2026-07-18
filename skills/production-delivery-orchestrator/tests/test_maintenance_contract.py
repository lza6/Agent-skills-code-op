import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
ENTRY_PATH = SKILL_ROOT / "SKILL.md"
CONTRACT_PATH = SKILL_ROOT / "references" / "maintenance-contract.md"


class MaintenanceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = ENTRY_PATH.read_text(encoding="utf-8")

    def test_entry_routes_deep_maintenance_to_the_contract(self) -> None:
        self.assertIn("references/maintenance-contract.md", self.entry)
        self.assertIn("事实可能已过时", self.entry)

    def test_contract_requires_freshness_check_before_implementation(self) -> None:
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        for required_text in (
            "先读后改",
            "git status --short",
            "文档事实新鲜度",
            "不适用",
            "不得把历史结果、静态评测、安装成功或 mock 当作当前运行证据",
            "独立只读 Critic",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, contract)


if __name__ == "__main__":
    unittest.main()
