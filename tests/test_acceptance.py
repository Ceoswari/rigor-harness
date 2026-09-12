"""Acceptance tests mapped to the handoff's section 4 criteria.

Run: python3 -m unittest discover -s tests -v
Network is not required; tests run against a saved copy of the source page.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import compare, verify
from harness.claims import extract, normalize
from harness.provenance import SourceStore, to_source_record

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURE_HTML = os.path.join(HERE, "fixture_tracing_page.html")
SOURCE_URL = "https://openai.github.io/openai-agents-python/tracing/"


def build_raw():
    import hashlib
    with open(FIXTURE_HTML, "rb") as fh:
        body = fh.read()
    return {"url": SOURCE_URL, "http_status": 200,
            "fetched_at": "2026-09-04T00:00:00Z",
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "content_length": len(body), "etag": None, "last_modified": None,
            "content_type": "text/html", "_body": body}


def load_fixtures():
    with open(os.path.join(ROOT, "fixtures", "references.json"), encoding="utf-8") as fh:
        return json.load(fh)


def build_run():
    data = load_fixtures()
    record = to_source_record(build_raw())
    claims = extract(record["text"], set(data["focus_terms"]))
    comparisons = compare.compare_all(data["references"], claims,
                                      compare.source_index(record["text"]))
    return {"source": record, "claims": claims, "comparisons": comparisons,
            "limitations": []}, data


class TestProvenance(unittest.TestCase):
    """Criterion 2: source provenance preserved."""

    def test_source_record_carries_identity_and_version(self):
        record = to_source_record(build_raw())
        self.assertEqual(record["url"], SOURCE_URL)
        self.assertEqual(len(record["content_sha256"]), 64)
        self.assertTrue(record["first_seen_at"])
        self.assertTrue(record["source_id"].startswith("src_"))

    def test_source_id_is_stable_across_fetches(self):
        self.assertEqual(to_source_record(build_raw())["source_id"],
                         to_source_record(build_raw())["source_id"])


class TestIdempotency(unittest.TestCase):
    """Criterion 4: re-ingesting does not duplicate the source."""

    def test_reingest_updates_rather_than_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sources.json")
            store = SourceStore(path)
            first = store.upsert(to_source_record(build_raw()))
            second = store.upsert(to_source_record(build_raw()))
            self.assertEqual(first["action"], "created")
            self.assertEqual(second["action"], "updated")
            self.assertFalse(second["content_changed"])
            self.assertEqual(store.count(), 1)

    def test_changed_content_bumps_revision_without_new_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceStore(os.path.join(tmp, "sources.json"))
            store.upsert(to_source_record(build_raw()))
            edited = to_source_record(build_raw())
            edited["content_sha256"] = "0" * 64
            result = store.upsert(edited)
            self.assertTrue(result["content_changed"])
            self.assertEqual(result["record"]["revision_count"], 2)
            self.assertEqual(store.count(), 1)


class TestExtraction(unittest.TestCase):
    """Criterion 3: bounded, material claims rather than a page dump."""

    def test_extraction_is_bounded(self):
        run, _ = build_run()
        self.assertGreater(len(run["claims"]), 0)
        self.assertLessEqual(len(run["claims"]), 8)

    def test_claims_are_verbatim_from_source(self):
        run, _ = build_run()
        for claim in run["claims"]:
            self.assertIn(claim["text"], run["source"]["text"])

    def test_polarity_is_read_not_guessed(self):
        enabled = normalize("Tracing is enabled by default.")
        disabled = normalize("Tracing is disabled by default.")
        self.assertEqual(enabled["axis"], disabled["axis"])
        self.assertEqual(enabled["subject"], disabled["subject"])
        self.assertEqual(enabled["polarity"], -disabled["polarity"])

    def test_negation_flips_polarity(self):
        self.assertEqual(normalize("Tracing is not enabled by default.")["polarity"], -1)


class TestClassification(unittest.TestCase):
    """Criteria 5, 6, 7: reinforcement, conflict and unrelated detection."""

    def setUp(self):
        self.run, self.data = build_run()
        self.by_ref = {c["reference_id"]: c for c in self.run["comparisons"]}

    def test_reference_a_reinforces(self):
        self.assertEqual(self.by_ref["ref_a"]["classification"], "reinforcing")

    def test_reference_b_conflicts(self):
        self.assertEqual(self.by_ref["ref_b"]["classification"], "conflicting")

    def test_reference_c_is_unrelated(self):
        self.assertEqual(self.by_ref["ref_c"]["classification"], "unrelated")

    def test_conflict_is_not_merged_as_compatible(self):
        self.assertNotIn(self.by_ref["ref_b"]["classification"],
                         ("reinforcing", "distinct"))

    def test_decided_classifications_carry_source_evidence(self):
        for ref in ("ref_a", "ref_b"):
            evidence = self.by_ref[ref]["evidence"]
            self.assertIsNotNone(evidence)
            self.assertIn(evidence["source_sentence"], self.run["source"]["text"])

    def test_not_keyword_matching(self):
        """ref_a and ref_b are near-identical yet land on opposite labels."""
        from harness.claims import content_tokens
        ta = content_tokens(self.by_ref["ref_a"]["reference_statement"])
        tb = content_tokens(self.by_ref["ref_b"]["reference_statement"])
        overlap = len(ta & tb) / float(min(len(ta), len(tb)))
        self.assertGreaterEqual(overlap, 0.6)
        self.assertNotEqual(self.by_ref["ref_a"]["classification"],
                            self.by_ref["ref_b"]["classification"])


class TestVerification(unittest.TestCase):
    """Criterion 8: a failed expectation is reported, not absorbed."""

    def test_clean_run_verifies(self):
        run, data = build_run()
        result = verify.verify(run, data["expectations"])
        self.assertTrue(result["verified"], result["summary"])

    def test_injected_failure_is_visible(self):
        run, data = build_run()
        broken = [dict(e) for e in data["expectations"]]
        broken[0]["expected"] = "conflicting"
        result = verify.verify(run, broken)
        self.assertFalse(result["verified"])
        self.assertIn("expectation_ref_a", result["failed_checks"])
        self.assertIn("FAILED", result["summary"])

    def test_verifier_does_not_trust_pipeline_self_report(self):
        """Fabricated claim text is caught because grounding is re-derived."""
        run, data = build_run()
        run["claims"][0] = dict(run["claims"][0],
                                text="Tracing is disabled by default in all cases.")
        result = verify.verify(run, data["expectations"])
        self.assertFalse(result["verified"])
        self.assertIn("claims_grounded_in_source", result["failed_checks"])


if __name__ == "__main__":
    unittest.main()
