"""The optional NLI backend.

Most of these run with nothing installed, because the property that matters
most is a contract rather than a model: an NLI result must be shaped exactly
like a rule-based one, so the verifier and the report cannot tell which backend
produced a run. If they could, the deterministic verifier would stop being an
independent check the moment the backend changed.

The tests that need torch and transformers skip themselves when those are
absent, which is the normal state of this repo.
"""
import hashlib
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import compare, nli, verify
from harness.claims import extract
from harness.provenance import to_source_record

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(HERE, "fixture_tracing_page_2026-09-11.html")

try:  # pragma: no cover - depends on environment
    import torch  # noqa: F401
    import transformers  # noqa: F401
    HAVE_MODEL_DEPS = True
except ImportError:
    HAVE_MODEL_DEPS = False


def page_and_claims():
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
    return record, extract(record["text"], focus), focus, data


class TestResultContract(unittest.TestCase):
    """Both backends must be indistinguishable downstream."""

    def setUp(self):
        self.record, self.claims, self.focus, self.data = page_and_claims()
        self.reference = self.data["references"][0]

    def test_both_backends_satisfy_the_declared_result_contract(self):
        """The contract is stated in compare.RESULT_CONTRACT, not inferred.

        Defining it as "whatever the rule-based backend emits" would make any
        diagnostic field that backend adds into a requirement for every other
        one. The rules backend adds `reference_proposition` and the NLI backend
        has no equivalent, because it never parses a proposition.
        """
        rules_result = compare.compare_one(self.reference, self.claims,
                                           compare.source_index(self.record["text"]))
        nli_result = nli._result(self.reference, compare.REINFORCING, self.claims[0],
                                 0.91, "because", sentence=self.claims[0]["text"])
        for name, result in (("rules", rules_result), ("nli", nli_result)):
            with self.subTest(backend=name):
                missing = set(compare.RESULT_CONTRACT) - set(result)
                self.assertEqual(missing, set(), "missing contract keys: %s" % missing)

    def test_nli_results_use_the_same_label_vocabulary(self):
        nli_result = nli._result(self.reference, compare.CONFLICTING, self.claims[0],
                                 0.8, "because", sentence=self.claims[0]["text"])
        self.assertIn(nli_result["classification"],
                      verify.DECIDING_LABELS + verify.DECLINING_LABELS)

    def test_verifier_accepts_an_nli_run_unchanged(self):
        comparisons = [
            nli._result(self.data["references"][0], compare.REINFORCING,
                        self.claims[1], 0.95, "entails",
                        sentence=self.claims[1]["text"]),
            nli._result(self.data["references"][1], compare.CONFLICTING,
                        self.claims[1], 0.93, "contradicts",
                        sentence=self.claims[1]["text"]),
            nli._result(self.data["references"][2], compare.UNRELATED, None, 0.1,
                        "no relation", reason="model_found_no_relation"),
        ]
        run = {"source": self.record, "claims": self.claims,
               "comparisons": comparisons, "focus_terms": sorted(self.focus),
               "limitations": []}
        result = verify.verify(run, self.data["expectations"])
        self.assertTrue(result["verified"], result["summary"])

    def test_declining_nli_results_still_carry_a_reason(self):
        run = {"source": self.record, "claims": self.claims, "focus_terms": [],
               "comparisons": [nli._result(self.reference, compare.UNRELATED, None,
                                           0.05, "nothing matched")]}
        result = verify.verify(run, [])
        self.assertIn("declined_results_name_a_reason", result["failed_checks"])


class TestMaterialScope(unittest.TestCase):

    def test_material_sentences_exceed_the_bounded_claim_set(self):
        """The premise of scope='material': extraction only sees a fraction."""
        record, claims, focus, _ = page_and_claims()
        sentences = nli.material_sentences(record["text"], focus)
        self.assertGreater(len(sentences), len(claims) * 3)

    def test_threshold_is_declared_not_derived(self):
        """Guards the discipline, not the behaviour.

        MIN_CONFIDENCE was chosen before the backend was ever measured. If a
        future change tunes it against the frozen evaluation sets, those sets
        stop being evidence, so the value is pinned here deliberately.
        """
        self.assertEqual(nli.MIN_CONFIDENCE, 0.50)


@unittest.skipUnless(HAVE_MODEL_DEPS, "torch and transformers are not installed")
class TestAgainstTheRealModel(unittest.TestCase):
    """Only runs where the optional dependencies exist."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.comparator = nli.NliComparator()
        except nli.ModelUnavailable as exc:
            raise unittest.SkipTest(str(exc))
        cls.record, cls.claims, cls.focus, cls.data = page_and_claims()
        cls.index = compare.source_index(cls.record["text"])

    def test_it_fails_the_pilots_own_reference_a(self):
        """Recorded because it is the most important thing this backend does wrong.

        This test originally asserted the opposite. That was an assumption
        written before the backend had been run, and it was false.

        Two causes, both diagnosed on 2026-09-12:

        1. The model scores "Tracing is enabled by default." against "OpenAI
           Agents SDK tracing is enabled by default." as neutral at 1.00, zero
           entailment. Strictly it is right: the sentence never says whose
           tracing, so it cannot entail a claim naming the SDK. This is the
           missing decontextualization stage REUSE_SCAN.md named from
           Claimify, now showing up as a measured failure.
        2. It scores an unrelated sentence, "The SDK omits that identifier from
           redacted spans for custom endpoints.", as a contradiction at 0.96.
           The backend keeps the single most confident verdict across premises,
           so that one spurious contradiction wins.

        Reference B still comes out right, because "enabled by default"
        contradicting "disabled by default" survives the missing context.
        """
        by_id = {r["id"]: self.comparator.compare_one(r, self.claims, self.index)
                 for r in self.data["references"]}
        self.assertEqual(by_id["ref_a"]["classification"], compare.CONFLICTING)
        self.assertEqual(by_id["ref_b"]["classification"], compare.CONFLICTING)

    def test_every_assertion_cites_a_sentence_from_the_source(self):
        for ref in self.data["references"]:
            result = self.comparator.compare_one(ref, self.claims, self.index)
            if result["classification"] in compare.DECIDED:
                self.assertIn(result["evidence"]["source_sentence"],
                              self.record["text"])


@unittest.skipUnless(HAVE_MODEL_DEPS, "torch and transformers are not installed")
class TestMeasuredBaseline(unittest.TestCase):
    """Records what the NLI backend scored on 2026-09-12.

    Skipped wherever the optional dependencies are absent, which is the normal
    state of this repo, so these numbers live in the README as well. They are
    recorded rather than asserted as a quality bar: the point is that a later
    change has to update them deliberately.

        rules         stress  3/14   sampled  3/20
        nli-claims    stress  6/14   sampled  8/20
        nli-material  stress  8/14   sampled 14/20

    Every NLI error on the material scope is a false conflict, and it declines
    nothing at all. That is the trade this backend makes, and it is the reason
    the rule-based comparator is still the default.
    """

    MEASURED = {("nli-claims", "heldout.json"): 6, ("nli-claims", "sampled.json"): 8,
                ("nli-material", "heldout.json"): 8, ("nli-material", "sampled.json"): 14}

    @classmethod
    def setUpClass(cls):
        try:
            cls.comparator = nli.NliComparator()
        except nli.ModelUnavailable as exc:
            raise unittest.SkipTest(str(exc))
        cls.record, cls.claims, cls.focus, _ = page_and_claims()
        cls.index = compare.source_index(cls.record["text"])
        cls.sentences = nli.material_sentences(cls.record["text"], cls.focus)

    def _score(self, fixture, scope):
        with open(os.path.join(ROOT, "fixtures", fixture), encoding="utf-8") as fh:
            data = json.load(fh)
        sentences = self.sentences if scope == "nli-material" else None
        correct = 0
        for ref in data["references"]:
            result = self.comparator.compare_one(ref, self.claims, self.index, sentences)
            correct += result["classification"] == ref["truth"]
        return correct

    def test_measured_scores_still_hold(self):
        for (scope, fixture), expected in self.MEASURED.items():
            with self.subTest(scope=scope, fixture=fixture):
                self.assertEqual(self._score(fixture, scope), expected)

    def test_it_beats_the_rule_based_baseline_on_both_sets(self):
        """The bar set before this backend was written: beat 3 and 3."""
        self.assertGreater(self._score("heldout.json", "nli-material"), 3)
        self.assertGreater(self._score("sampled.json", "nli-material"), 3)

    def test_it_asserts_a_contradiction_between_unrelated_statements(self):
        """The cost of the recall, pinned so it cannot be forgotten.

        The Kubernetes reference has nothing to do with the page. The
        rule-based comparator calls it unrelated, correctly. This one calls it
        a conflict.
        """
        with open(os.path.join(ROOT, "fixtures", "heldout.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        kubernetes = [r for r in data["references"] if r["id"] == "h07"][0]
        result = self.comparator.compare_one(kubernetes, self.claims, self.index)
        self.assertEqual(result["classification"], compare.CONFLICTING)
        self.assertEqual(kubernetes["truth"], "unrelated")


if __name__ == "__main__":
    unittest.main()
