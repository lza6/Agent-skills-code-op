"""Optional real-browser acceptance test for the local production-audit report.

Run through webapp-testing's server wrapper so this repository keeps no web runtime dependency:

python <with_server.py> --server "python -m http.server 8765 --directory docs/reports" --port 8765 -- python tools/tests/report_browser_smoke.py
"""

from __future__ import annotations

import os
import sys


REPORT_URL = os.environ.get(
    "PRODUCTION_AUDIT_REPORT_URL",
    "http://127.0.0.1:8765/production-audit-closure-2026-07-18.html",
)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright Python package is unavailable; install it only for this optional browser check.")
        return 2

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(REPORT_URL, wait_until="networkidle")

            correct_answers = {"q1": "b", "q2": "c", "q3": "a"}
            for name, value in correct_answers.items():
                page.locator(f'input[name="{name}"][value="{value}"]').check()
            page.locator('input[name="q5"][value="a"]').check()
            page.locator("#grade-quiz").click()
            failed_message = page.locator("#quiz-result").inner_text()
            assert failed_message.startswith("未通过：3 / 5")
            assert "正确答案：" in failed_message
            assert "partial：Claude 没有可用模型" in failed_message
            feedback = page.locator(".question.incorrect .quiz-feedback")
            assert feedback.count() == 2
            assert "说明：" in feedback.nth(1).inner_text()

            page.locator('input[name="q5"][value="c"]').check()
            page.locator("#grade-quiz").click()
            assert page.locator("#quiz-result").inner_text().startswith("通过：4 / 5")

            page.locator("#reset-quiz").click()
            assert page.locator("#quiz-result").inner_text() == ""
            assert page.locator(".quiz-feedback").count() == 0
        finally:
            browser.close()

    print("HTML report browser journey passed: fail feedback, pass feedback, reset.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
