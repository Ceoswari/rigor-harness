"""Locks the held-out measurement in place.

This is a characterization test, not a quality bar. It records what the
comparator actually did on the held-out set on 2026-09-12, so that any future
change to harness/ has to consciously update this file rather than quietly
moving the number.

The recorded accuracy is 3 of 14. That is the honest baseline the next
implementation has to beat, and it is deliberately not hidden behind a
passing test suite.
"""
import hashlib
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import compare
from harness.claims import extract
from harness.provenance import to_source_record

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(HERE, "fixture_tracing_page_2026-09-11.html")

# Measured 2026-09-12. Update only with a deliberate note about what changed.
BASELINE = {
    "h01": "conflicting", "h02": "distinct", "h03": "unrelated",
    "h04": "distinct", "h05": "conflicting", "h06": "reinforcing",
    "h07": "unrelated", "h08": "unrelated", "h09": "conflicting",
    "h10": "unrelated", "h11": "reinforcing", "h12": "distinct",
    "h13": "unrelated", "h14": "conflicting",
}
BASELINE_CORRECT = 3


def build_claims(data):
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": "https://openai.github.io/openai-agents-python/tracing/",
           "http_status": None, "fetched_at": "test",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": "tests/"}
    record = to_source_record(raw)
    return extract(record["text"], set(data["focus_terms"]))


class TestHeldOutBaseline(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(ROOT, "fixtures", "heldout.json"), encoding="utf-8") as fh:
            self.data = json.load(fh)
        self.claims = build_claims(self.data)

    def test_labels_match_the_recorded_baseline(self):
        for ref in self.data["references"]:
            with self.subTest(ref=ref["id"]):
                actual = compare.compare_one(ref, self.claims)["classification"]
                self.assertEqual(actual, BASELINE[ref["id"]])

    def test_accuracy_is_still_three_of_fourteen(self):
        correct = sum(
            compare.compare_one(ref, self.claims)["classification"] == ref["truth"]
            for ref in self.data["references"])
        self.assertEqual(correct, BASELINE_CORRECT)

    def test_heldout_set_was_not_quietly_shrunk(self):
        self.assertEqual(len(self.data["references"]), 14)
        for ref in self.data["references"]:
            self.assertIn("truth", ref)
            self.assertIn("predicted_system", ref)


if __name__ == "__main__":
    unittest.main()
