"""Regression tests for the watcher.

Bug 2026-09-08: EUR-Lex bot mitigation answers HTTP 200/202 with an empty body.
check_consolidations treated the empty page as "no findings" and went silently
blind. A blocked source must surface as an ERROR, never as a quiet no-op.

Run: py -m unittest tests.test_watch_regressions
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import watch  # noqa: E402


MANIFEST = {"documents": [
    {"id": "eu-2023-956", "celex": "02023R0956-20251020"},
]}


class BlockedResponseIsError(unittest.TestCase):
    def test_guarded_fetch_raises_on_tiny_body(self):
        with mock.patch.object(watch, "fetch_url", return_value=""):
            with self.assertRaises(RuntimeError):
                watch.guarded_fetch("https://example.invalid/x")

    def test_consolidation_check_reports_error_not_silence(self):
        with mock.patch.object(watch, "fetch_url", return_value=""):
            findings, errors = watch.check_consolidations(MANIFEST)
        self.assertEqual(findings, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("blocked or empty", errors[0])

    def test_real_page_still_yields_finding(self):
        page = "x" * 6000 + "02023R0956-20251020 02023R0956-20260215"
        with mock.patch.object(watch, "fetch_url", return_value=page):
            findings, errors = watch.check_consolidations(MANIFEST)
        self.assertEqual(errors, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["latest"], "20260215")


if __name__ == "__main__":
    unittest.main()
