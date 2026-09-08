"""Regression: fetch --refresh clobbered the Turkish law's PDF-extracted text with the
mevzuat.gov.tr JavaScript shell page (2026-09-09). non_eurlex documents are manual-path
only and must never be auto-fetched.

Run: py -m unittest tests.test_fetch_regressions
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import fetch  # noqa: E402


class NonEurlexIsNeverFetched(unittest.TestCase):
    def test_non_eurlex_doc_is_skipped(self):
        doc = {"id": "tr-7552", "jurisdiction": "TR",
               "source_url": "https://www.mevzuat.gov.tr/whatever",
               "flags": ["non_eurlex"]}
        res = fetch.fetch_doc(doc)
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("skipped"))

    def test_turkish_corpus_still_holds_the_law(self):
        txt = (Path(__file__).resolve().parent.parent / "corpus" / "tr" / "tr-7552.txt")
        content = txt.read_text(encoding="utf-8")
        self.assertGreater(content.count("MADDE"), 15, "PDF-extracted text was clobbered")


if __name__ == "__main__":
    unittest.main()
