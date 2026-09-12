"""Locks both evaluation measurements in place.

Characterization tests, not quality bars. Any future change to harness/ has to
update this file deliberately rather than quietly moving a number.

**Updated 2026-09-12 (evening), and the reason matters.** Kevin Ng's review
found that `unrelated` was doing double duty, covering both "the source says
nothing about this" and "the system cannot express this claim". The comparator
now splits those, so the recorded labels below changed.

What did NOT change is the score: still 3 of 14 and 3 of 20. That is the
honest outcome. Declining with a stated reason is not a right answer, so it is
still counted as a miss. The split improves diagnosis, not correctness, and
the numbers are recorded here unchanged to keep that visible.

Stress set  : 3 of 14 correct. 7 assertions, 2 right. 7 declines, one of which
              (the Kubernetes reference) is correct, because that reference
              really is unrelated to the page.
Sampled set : 3 of 20 correct. 3 assertions, 3 right. 17 declines, every one
              of them because no axis exists for the statement.
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

STRESS_LABELS = {
    "h01": "conflicting", "h02": "unrepresentable", "h03": "uncovered",
    "h04": "distinct", "h05": "conflicting", "h06": "reinforcing",
    "h07": "unrelated", "h08": "unrepresentable", "h09": "conflicting",
    "h10": "unrepresentable", "h11": "reinforcing", "h12": "unrepresentable",
    "h13": "uncovered", "h14": "conflicting",
}
SAMPLED_ASSERTED = {"s01": "reinforcing", "s02": "reinforcing", "s02n": "conflicting"}

BASELINE = {
    "heldout.json": {"correct": 3, "total": 14, "asserted": 7, "asserted_right": 2,
                     "declined": 7},
    "sampled.json": {"correct": 3, "total": 20, "asserted": 3, "asserted_right": 3,
                     "declined": 17},
}

# The single genuine "the page does not discuss this" case across both sets.
ONLY_TRUE_UNRELATED = "h07"


def load(name):
    with open(os.path.join(ROOT, "fixtures", name), encoding="utf-8") as fh:
        return json.load(fh)


def context(data):
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": "https://openai.github.io/openai-agents-python/tracing/",
           "http_status": None, "fetched_at": "test",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": "tests/"}
    record = to_source_record(raw)
    return (extract(record["text"], set(data["focus_terms"])),
            compare.source_index(record["text"]))


def measure(name):
    data = load(name)
    claims, index = context(data)
    results, totals = {}, {"correct": 0, "total": len(data["references"]),
                           "asserted": 0, "asserted_right": 0, "declined": 0}
    for ref in data["references"]:
        r = compare.compare_one(ref, claims, index)
        results[ref["id"]] = r
        ok = r["classification"] == ref["truth"]
        totals["correct"] += ok
        if r["classification"] in compare.DECIDED:
            totals["asserted"] += 1
            totals["asserted_right"] += ok
        else:
            totals["declined"] += 1
    return results, totals


class TestStressBaseline(unittest.TestCase):

    def test_every_label_matches_the_record(self):
        results, _ = measure("heldout.json")
        for ref_id, expected in STRESS_LABELS.items():
            with self.subTest(ref=ref_id):
                self.assertEqual(results[ref_id]["classification"], expected)

    def test_totals_match_the_record(self):
        _, totals = measure("heldout.json")
        self.assertEqual(totals, BASELINE["heldout.json"])


class TestSampledBaseline(unittest.TestCase):

    def test_only_three_references_get_an_assertion(self):
        results, _ = measure("sampled.json")
        asserted = {k: v["classification"] for k, v in results.items()
                    if v["classification"] in compare.DECIDED}
        self.assertEqual(asserted, SAMPLED_ASSERTED)

    def test_totals_match_the_record(self):
        _, totals = measure("sampled.json")
        self.assertEqual(totals, BASELINE["sampled.json"])

    def test_every_decline_is_a_missing_axis_not_an_unrelated_page(self):
        """The finding worth keeping: the page is not silent, the system is."""
        results, _ = measure("sampled.json")
        reasons = {r["reason"] for r in results.values()
                   if r["classification"] in compare.DECLINED}
        self.assertEqual(reasons, {"no_axis_for_statement"})

    def test_sampled_set_is_machine_generated_and_intact(self):
        data = load("sampled.json")
        self.assertEqual(len(data["references"]), 20)
        self.assertEqual(data["procedure"]["stride"], 3)


class TestDeclineReasons(unittest.TestCase):
    """Across both sets, only one reference is genuinely unrelated."""

    def test_only_one_reference_is_truly_unrelated(self):
        unrelated = []
        for name in ("heldout.json", "sampled.json"):
            results, _ = measure(name)
            unrelated += [k for k, v in results.items()
                          if v["classification"] == "unrelated"]
        self.assertEqual(unrelated, [ONLY_TRUE_UNRELATED])

    def test_every_decline_records_a_reason(self):
        for name in ("heldout.json", "sampled.json"):
            results, _ = measure(name)
            for ref_id, r in results.items():
                if r["classification"] in compare.DECLINED:
                    with self.subTest(set=name, ref=ref_id):
                        self.assertTrue(r["reason"], "declined with no reason")


if __name__ == "__main__":
    unittest.main()
