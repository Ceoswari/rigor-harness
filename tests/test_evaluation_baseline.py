"""Locks both evaluation measurements in place.

Characterization tests, not quality bars. They record what the comparator
actually did on 2026-09-12 so that any future change to harness/ has to
consciously update this file rather than quietly moving a number.

Stress set  : 3 of 14 correct, 9 opinions offered, 2 of those right.
Sampled set : 3 of 20 correct, 3 opinions offered, 3 of those right.

The sampled number is the lower of the two and that is not a mistake. The
system declines to answer most of the page's own sentences.
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
    "h01": "conflicting", "h02": "distinct", "h03": "unrelated",
    "h04": "distinct", "h05": "conflicting", "h06": "reinforcing",
    "h07": "unrelated", "h08": "unrelated", "h09": "conflicting",
    "h10": "unrelated", "h11": "reinforcing", "h12": "distinct",
    "h13": "unrelated", "h14": "conflicting",
}
SAMPLED_OPINIONS = {"s01": "reinforcing", "s02": "reinforcing", "s02n": "conflicting"}

BASELINE = {
    "heldout.json": {"correct": 3, "total": 14, "opinions": 9, "opinions_right": 2},
    "sampled.json": {"correct": 3, "total": 20, "opinions": 3, "opinions_right": 3},
}


def load(name):
    with open(os.path.join(ROOT, "fixtures", name), encoding="utf-8") as fh:
        return json.load(fh)


def claims_for(data):
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": "https://openai.github.io/openai-agents-python/tracing/",
           "http_status": None, "fetched_at": "test",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": "tests/"}
    return extract(to_source_record(raw)["text"], set(data["focus_terms"]))


def measure(name):
    data = load(name)
    claims = claims_for(data)
    labels, correct, opinions, opinions_right = {}, 0, 0, 0
    for ref in data["references"]:
        actual = compare.compare_one(ref, claims)["classification"]
        labels[ref["id"]] = actual
        ok = actual == ref["truth"]
        correct += ok
        if actual != "unrelated":
            opinions += 1
            opinions_right += ok
    return labels, {"correct": correct, "total": len(data["references"]),
                    "opinions": opinions, "opinions_right": opinions_right}


class TestStressBaseline(unittest.TestCase):

    def test_every_label_matches_the_record(self):
        labels, _ = measure("heldout.json")
        for ref_id, expected in STRESS_LABELS.items():
            with self.subTest(ref=ref_id):
                self.assertEqual(labels[ref_id], expected)

    def test_totals_match_the_record(self):
        _, totals = measure("heldout.json")
        self.assertEqual(totals, BASELINE["heldout.json"])


class TestSampledBaseline(unittest.TestCase):

    def test_only_three_sentences_get_an_opinion(self):
        labels, _ = measure("sampled.json")
        opinionated = {k: v for k, v in labels.items() if v != "unrelated"}
        self.assertEqual(opinionated, SAMPLED_OPINIONS)

    def test_totals_match_the_record(self):
        _, totals = measure("sampled.json")
        self.assertEqual(totals, BASELINE["sampled.json"])

    def test_sampled_set_is_machine_generated_and_intact(self):
        data = load("sampled.json")
        self.assertEqual(len(data["references"]), 20)
        self.assertEqual(data["procedure"]["stride"], 3)
        for ref in data["references"]:
            self.assertEqual(ref["predicted_system"], "unknown")


if __name__ == "__main__":
    unittest.main()
