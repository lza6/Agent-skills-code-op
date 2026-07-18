import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "production-audit-closure-2026-07-18.html"


class _ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if "id" in attributes and attributes["id"] is not None:
            self.ids.add(attributes["id"])
        if tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"])


class ProductionAuditReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = REPORT_PATH.read_text(encoding="utf-8")
        self.parser = _ReportParser()
        self.parser.feed(self.html)

    def test_report_has_required_handoff_sections_and_accessible_quiz_feedback(self) -> None:
        required_ids = {
            "context",
            "changes",
            "evidence",
            "limits",
            "workflow",
            "quiz",
            "quiz-result",
        }
        self.assertTrue(required_ids.issubset(self.parser.ids))
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn("至少答对 4 / 5 题", self.html)
        self.assertIn("const requiredToPass = 4", self.html)
        self.assertGreaterEqual(len(re.findall(r'data-correct="[^"]+"', self.html)), 5)
        self.assertIn("addEventListener(\"click\"", self.html)
        self.assertIn("正确答案：", self.html)
        self.assertIn("corrections.join", self.html)
        self.assertGreaterEqual(len(re.findall(r'data-explanation="[^"]+"', self.html)), 5)
        self.assertIn("quiz-feedback", self.html)
        self.assertIn("document.createElement", self.html)

    def test_report_links_resolve_to_versioned_repository_artifacts(self) -> None:
        for href in self.parser.hrefs:
            if href.startswith(("#", "https://", "http://", "mailto:")):
                continue
            target = (REPORT_PATH.parent / href).resolve()
            with self.subTest(href=href):
                self.assertTrue(target.is_file(), f"broken local report link: {href}")


if __name__ == "__main__":
    unittest.main()
