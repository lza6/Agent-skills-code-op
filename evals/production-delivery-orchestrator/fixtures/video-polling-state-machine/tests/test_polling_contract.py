from pathlib import Path
import unittest


class PollingContractTest(unittest.TestCase):
    def test_frontend_and_backend_agree_on_terminal_states(self):
        root = Path(__file__).parents[1]
        frontend = (root / "frontend" / "useVideoJob.ts").read_text(encoding="utf-8")
        backend = (root / "backend" / "video_jobs.py").read_text(encoding="utf-8")

        self.assertIn('"failed"', backend)
        self.assertIn("['completed', 'failed']", frontend)


if __name__ == "__main__":
    unittest.main()
