from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "tools" / "trace_coverage_baseline.py"
SPEC = importlib.util.spec_from_file_location("trace_coverage_baseline", SCRIPT_PATH)
assert SPEC and SPEC.loader
BASELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINE)


class TraceCoverageBaselineTest(unittest.TestCase):
    def test_parse_trace_counts_only_executed_source_lines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-trace-coverage-") as temp:
            cover = Path(temp) / "sample.cover"
            cover.write_text("    1: first\n       second\n    3: third\n", encoding="utf-8")
            self.assertEqual(BASELINE.parse_trace_counts(cover), {1, 3})

    def test_build_report_uses_relative_source_names_and_stable_ratio(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdo-trace-coverage-") as temp:
            root = Path(temp)
            source = root / "sample.py"
            source.write_text("first\nsecond\nthird\n", encoding="utf-8")
            cover = root / "sample.cover"
            cover.write_text("    1: first\n       second\n    3: third\n", encoding="utf-8")
            report = BASELINE.build_report(
                trace_dir=root,
                sources={"sample.py": source},
                cover_paths={"sample.py": cover},
            )
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["targets"][0]["source_lines"], 3)
        self.assertEqual(report["targets"][0]["executed_lines"], 2)
        self.assertEqual(report["targets"][0]["line_coverage"], 0.6667)

    def test_check_rejects_missing_or_regressed_target(self) -> None:
        baseline = {
            "schema": 1,
            "targets": [
                {
                    "path": "sample.py",
                    "minimum_line_coverage": 0.6667,
                }
            ],
        }
        self.assertEqual(
            BASELINE.baseline_errors(
                {"schema": 1, "targets": [{"path": "sample.py", "line_coverage": 0.7}]},
                baseline,
            ),
            [],
        )
        errors = BASELINE.baseline_errors(
            {"schema": 1, "targets": [{"path": "sample.py", "line_coverage": 0.6}]},
            baseline,
        )
        self.assertTrue(any("低于基线" in error for error in errors))
        self.assertTrue(
            BASELINE.baseline_errors({"schema": 1, "targets": []}, baseline)
        )

    def test_json_is_deterministic(self) -> None:
        payload = {"schema": 1, "targets": [{"path": "a.py", "line_coverage": 1.0}]}
        self.assertEqual(BASELINE.render_json(payload), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
