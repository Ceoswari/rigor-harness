"""Tests for the one-command surface, the failure path, and page drift.

The acceptance tests in test_acceptance.py check the pipeline's internals.
These check the things a reviewer actually exercises: the documented command,
what happens when a check fails, and whether the harness still works when the
upstream page changes under it.

Run: python3 -m unittest discover -s tests -v
No network required.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run as runner
from harness import compare
from harness.claims import extract, normalize
from harness.provenance import to_source_record
from tests.test_acceptance import build_raw, load_fixtures

HERE = os.path.dirname(os.path.abspath(__file__))

# Two captures of the same URL: the page as first ingested, and the page as it
# stood on Sep 11 2026 after OpenAI edited it. Both must work.
PAGE_VERSIONS = {
    "2026-09-04": os.path.join(HERE, "fixture_tracing_page.html"),
    "2026-09-11": os.path.join(HERE, "fixture_tracing_page_2026-09-11.html"),
}


def invoke(tmp, fixture, extra=None):
    """Run the real CLI entry point against a saved page copy."""
    argv = ["--offline-fixture", fixture,
            "--out", tmp, "--store", os.path.join(tmp, "sources.json")]
    argv += extra or []
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = runner.main(argv)
    with open(os.path.join(tmp, "run.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    with open(os.path.join(tmp, "report.md"), encoding="utf-8") as fh:
        report = fh.read()
    return code, payload, report, buf.getvalue()


class TestOneCommandRun(unittest.TestCase):
    """Criteria 1 and 9: one command, two output surfaces."""

    def test_documented_command_produces_both_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, report, _ = invoke(tmp, PAGE_VERSIONS["2026-09-04"])
            self.assertEqual(code, 0)
            for key in ("source", "claims", "comparisons", "verification"):
                self.assertIn(key, payload)
            self.assertIn("**Status:** VERIFIED", report)
            self.assertIn("https://openai.github.io/openai-agents-python/tracing/", report)
            self.assertIn("## Material limitations", report)

    def test_exit_code_reports_failure_to_the_shell(self):
        """A caller that only reads the exit status still learns the truth."""
        with tempfile.TemporaryDirectory() as tmp:
            code, _, report, _ = invoke(tmp, PAGE_VERSIONS["2026-09-04"],
                                        ["--inject-failure"])
            self.assertEqual(code, 1)
            self.assertIn("**Status:** NOT VERIFIED", report)
            self.assertIn("[FAIL]", report)

    def test_offline_run_does_not_claim_an_http_fetch(self):
        """Provenance must not report a request that never happened."""
        with tempfile.TemporaryDirectory() as tmp:
            _, payload, report, _ = invoke(tmp, PAGE_VERSIONS["2026-09-04"])
            self.assertEqual(payload["source"]["fetch_mode"], "offline_fixture")
            self.assertIsNone(payload["source"]["http_status"])
            self.assertIn("no network request", report)


class TestPageDrift(unittest.TestCase):
    """The upstream page is not frozen. Both captured versions must verify."""

    def test_both_page_versions_verify(self):
        for label, path in PAGE_VERSIONS.items():
            with self.subTest(version=label), tempfile.TemporaryDirectory() as tmp:
                code, payload, _, _ = invoke(tmp, path)
                self.assertEqual(code, 0, "%s failed verification" % label)
                by_ref = {c["reference_id"]: c["classification"]
                          for c in payload["comparisons"]}
                self.assertEqual(by_ref["ref_a"], "reinforcing")
                self.assertEqual(by_ref["ref_b"], "conflicting")
                self.assertEqual(by_ref["ref_c"], "unrelated")

    def test_default_claim_survives_ranking_in_both_versions(self):
        """The regression that broke the Sep 11 page.

        Claims are ranked and truncated to a bounded set. When ranking
        rewarded long sentences, "Tracing is enabled by default." fell out of
        the set and both comparisons resolved against the wrong sentence.
        """
        for label, path in PAGE_VERSIONS.items():
            with self.subTest(version=label), tempfile.TemporaryDirectory() as tmp:
                _, payload, _, _ = invoke(tmp, path)
                texts = [c["text"] for c in payload["claims"]]
                self.assertIn("Tracing is enabled by default.", texts)
                for comp in payload["comparisons"]:
                    if comp["reference_id"] in ("ref_a", "ref_b"):
                        self.assertEqual(comp["evidence"]["source_sentence"],
                                         "Tracing is enabled by default.")


class TestSentenceIntegrity(unittest.TestCase):
    """Inline code must not cut a sentence in half."""

    def test_claim_text_includes_inline_code(self):
        record = to_source_record(build_raw())
        claims = extract(record["text"], set(load_fixtures()["focus_terms"]))
        env_claims = [c for c in claims if "env var" in c["text"]]
        self.assertTrue(env_claims, "expected the env-var claim to be extracted")
        self.assertIn("OPENAI_AGENTS_DISABLE_TRACING", env_claims[0]["text"])

    def test_no_claim_ends_mid_sentence_on_a_preposition(self):
        record = to_source_record(build_raw())
        claims = extract(record["text"], set(load_fixtures()["focus_terms"]))
        for claim in claims:
            self.assertFalse(
                claim["text"].rstrip().endswith((" via", " with", " by", " to", " the")),
                "claim truncated at inline markup: %r" % claim["text"])


class TestNegationScope(unittest.TestCase):
    """Negation belongs to the verb it precedes, not to the whole sentence."""

    def test_negation_next_to_the_marker_flips_polarity(self):
        self.assertEqual(normalize("Tracing is not enabled by default.")["polarity"], -1)

    def test_distant_negation_does_not_flip_polarity(self):
        sentence = ("Disabling tracing prevents the default provider from creating "
                    "new traces and spans, but it does not discard data that its "
                    "processors already buffered.")
        self.assertEqual(normalize(sentence)["polarity"], -1)


class TestScopedComparison(unittest.TestCase):
    """A per-run switch does not contradict a statement about the default."""

    def test_per_run_claim_does_not_conflict_with_a_default_claim(self):
        claims = extract(
            "You can disable tracing for a single run by setting "
            "RunConfig.tracing_disabled to True.\n", {"tracing"})
        self.assertTrue(claims)
        # Stated without the SDK name so subject overlap is unambiguous: the
        # point under test is the scope rule, not the overlap threshold.
        result = compare.compare_one(
            {"id": "ref_a", "statement": "Tracing is enabled by default."}, claims)
        self.assertEqual(result["classification"], "indeterminate")
        self.assertIn("scope", result["rationale"])
        self.assertNotEqual(result["classification"], "conflicting")

    def test_default_claim_is_preferred_over_a_better_word_overlap(self):
        claims = extract(
            "You can disable tracing for a single run by setting "
            "agents.run.RunConfig.tracing_disabled to True.\n"
            "Tracing is enabled by default.\n", {"tracing", "agents", "sdk"})
        result = compare.compare_one(
            {"id": "ref_a", "statement": "OpenAI Agents SDK tracing is enabled by default."},
            claims)
        self.assertEqual(result["classification"], "reinforcing")
        self.assertEqual(result["evidence"]["source_sentence"],
                         "Tracing is enabled by default.")


class TestDeduplication(unittest.TestCase):
    """Restating the same proposition must not fill the bounded claim set."""

    def test_repeated_proposition_is_extracted_once(self):
        text = "\n".join(["Tracing is enabled by default."] * 5)
        claims = extract(text, {"tracing"})
        self.assertEqual(len(claims), 1)


if __name__ == "__main__":
    unittest.main()
