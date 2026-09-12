"""The verifier has to count what the run declined to say.

Until Sep 12 2026 verification asked one question, whether the answers given
were correct, and never asked how many answers were withheld. A run that
represented a fraction of the page and declined on most references passed
cleanly. Kevin Ng's review is what surfaced it.

These tests pin the two properties that fix relies on: the numbers are
re-derived by the verifier rather than read off the pipeline, and the check
can actually fail.
"""
import hashlib
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import compare, verify
from harness.claims import extract
from harness.provenance import to_source_record

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(HERE, "fixture_tracing_page_2026-09-11.html")


def build_run():
    with open(os.path.join(ROOT, "fixtures", "references.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": "https://openai.github.io/openai-agents-python/tracing/",
           "http_status": None, "fetched_at": "test",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": "tests/"}
    record = to_source_record(raw)
    focus = set(data["focus_terms"])
    claims = extract(record["text"], focus)
    comparisons = compare.compare_all(data["references"], claims,
                                      compare.source_index(record["text"]))
    run = {"source": record, "claims": claims, "comparisons": comparisons,
           "focus_terms": sorted(focus), "limitations": []}
    return run, data


class TestCoverageIsReported(unittest.TestCase):

    def setUp(self):
        self.run, self.data = build_run()
        self.result = verify.verify(self.run, self.data["expectations"])

    def test_verification_carries_coverage_numbers(self):
        cov = self.result["coverage"]
        for key in ("material_sentences", "sentences_represented_by_a_claim",
                    "extraction_coverage", "references", "asserted", "declined",
                    "declined_by_reason"):
            self.assertIn(key, cov)

    def test_the_page_says_far_more_than_the_run_represents(self):
        """The point of the number: 8 claims is not the whole page."""
        cov = self.result["coverage"]
        self.assertGreater(cov["material_sentences"], len(self.run["claims"]))
        self.assertLess(cov["extraction_coverage"], 0.5)

    def test_asserted_plus_declined_accounts_for_every_reference(self):
        cov = self.result["coverage"]
        self.assertEqual(cov["asserted"] + cov["declined"], cov["references"])
        self.assertEqual(cov["references"], len(self.run["comparisons"]))

    def test_coverage_is_derived_not_taken_from_the_pipeline(self):
        """Planting a fake coverage figure in the run must not change the result."""
        lying = dict(self.run)
        lying["coverage"] = {"extraction_coverage": 1.0, "material_sentences": 1}
        result = verify.verify(lying, self.data["expectations"])
        self.assertEqual(result["coverage"]["material_sentences"],
                         self.result["coverage"]["material_sentences"])
        self.assertNotEqual(result["coverage"]["extraction_coverage"], 1.0)

    def test_material_sentence_count_does_not_come_from_the_claim_set(self):
        """Dropping claims must not shrink the page."""
        fewer = dict(self.run, claims=self.run["claims"][:1])
        result = verify.verify(fewer, self.data["expectations"])
        self.assertEqual(result["coverage"]["material_sentences"],
                         self.result["coverage"]["material_sentences"])
        self.assertLess(result["coverage"]["sentences_represented_by_a_claim"],
                        self.result["coverage"]["sentences_represented_by_a_claim"])


class TestDeclineFloorCanFail(unittest.TestCase):
    """A run that mostly declines must not be presentable as verified."""

    def test_clean_pilot_run_passes_the_floor(self):
        run, data = build_run()
        result = verify.verify(run, data["expectations"])
        self.assertNotIn("answers_more_often_than_it_declines", result["failed_checks"])

    def test_mostly_declining_run_fails_the_floor(self):
        run, data = build_run()
        run = dict(run)
        run["comparisons"] = [
            dict(c, classification="unrepresentable", reason="no_axis_for_statement",
                 evidence=None)
            for c in run["comparisons"]
        ]
        result = verify.verify(run, [])
        self.assertFalse(result["verified"])
        self.assertIn("answers_more_often_than_it_declines", result["failed_checks"])

    def test_the_failure_says_how_many_were_declined(self):
        run, data = build_run()
        run = dict(run)
        run["comparisons"] = [
            dict(c, classification="uncovered",
                 reason="subject_present_but_not_extracted", evidence=None)
            for c in run["comparisons"]
        ]
        result = verify.verify(run, [])
        detail = [c["detail"] for c in result["checks"]
                  if c["check"] == "answers_more_often_than_it_declines"][0]
        self.assertIn("Declined 3 of 3", detail)
        self.assertIn("subject_present_but_not_extracted", detail)


if __name__ == "__main__":
    unittest.main()
