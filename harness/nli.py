"""An optional comparison backend built on a natural language inference model.

**Why this exists.** The rule-based comparator in compare.py agrees with a
careful reader on 3 of 14 stress references and 3 of 20 sampled ones, and it
represents 11% of the source page. Its declines are concentrated in one place:
17 of 17 on the sampled set are `no_axis_for_statement`, meaning the statement
sits outside the four predicate axes hand-listed in claims.py. That is a
vocabulary limit, not a logic bug, and no amount of rule-writing fixes the
general case.

An NLI model has no such vocabulary. It takes a premise and a hypothesis and
returns entailment, contradiction or neutral, which map onto this pilot's
labels almost one to one.

**Why it is optional rather than a replacement.** The repo's one real
usability property is that it clones and runs with nothing to install. This
backend needs torch and transformers and downloads roughly a gigabyte of model
weights. So the rule-based comparator remains the default, this switches on
with `--backend nli`, and both are measured against the same frozen sets. The
comparison is the point; replacing one with the other would throw away the
baseline.

**The threshold is declared here, before any measurement, and is not tuned.**
MIN_CONFIDENCE below was chosen a priori. Tuning it against the held-out sets
would turn them into training sets, which is the same reason two known bugs in
compare.py were left unfixed. If it turns out to be a bad threshold, that is a
finding to report, not a knob to turn.
"""
from typing import Dict, List, Optional, Sequence, Set

from .claims import content_tokens
from .compare import (CONFLICTING, DECIDED, REINFORCING, SOURCE_PRESENCE_MIN,
                      UNCOVERED, UNRELATED, _discussed)

MODEL_NAME = "cross-encoder/nli-deberta-v3-base"

#: Minimum probability before the model's verdict is treated as an assertion.
#: Declared before measurement. Not tuned against any evaluation set.
MIN_CONFIDENCE = 0.50

#: How many premise/hypothesis pairs to score at once.
BATCH_SIZE = 16


def material_sentences(text: str, focus: Set[str],
                       min_chars: int = 40, max_chars: int = 300) -> List[str]:
    """Prose sentences on the page that mention a focus term.

    Used for scope="material". Intentionally a superset of what extraction
    keeps, since the question this scope answers is what the system misses by
    only ever looking at 8 ranked claims.
    """
    from .claims import split_sentences
    out = []
    for sentence in split_sentences(text):
        if not (min_chars <= len(sentence) <= max_chars):
            continue
        if not sentence[:1].isupper() or sentence.endswith(":"):
            continue
        if any(term in sentence.lower() for term in focus):
            out.append(sentence)
    return out


class ModelUnavailable(RuntimeError):
    """Raised when the optional dependencies or weights are missing."""


class NliComparator:
    """Compares references against source sentences using an NLI model.

    Two scopes, and the difference between them is the experiment:

      scope="claims"    premises are the bounded set of extracted claims, the
                        same input the rule-based comparator sees. This is the
                        like-for-like comparison.
      scope="material"  premises are every material sentence on the page. This
                        tests whether the 11% extraction coverage, rather than
                        the comparison logic, is what limits the system.
    """

    def __init__(self, model_name: str = MODEL_NAME,
                 min_confidence: float = MIN_CONFIDENCE) -> None:
        try:
            import torch
            from transformers import (AutoModelForSequenceClassification,
                                      AutoTokenizer)
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ModelUnavailable(
                "The nli backend needs torch and transformers. They are "
                "deliberately not required by the rest of this repo. Install "
                "them into a virtualenv, then rerun with --backend nli."
            ) from exc

        self._torch = torch
        self.model_name = model_name
        self.min_confidence = min_confidence
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
        except Exception as exc:  # pragma: no cover - network/cache dependent
            raise ModelUnavailable(
                "Could not load %r. The weights download on first use and need "
                "network access. Underlying error: %s" % (model_name, exc)) from exc
        self._model.eval()
        # Read the label order off the model config rather than assuming it.
        self._id2label = {int(k): v.lower()
                          for k, v in self._model.config.id2label.items()}

    def _score(self, pairs: Sequence) -> List[Dict[str, float]]:
        """Return {label: probability} for each (premise, hypothesis) pair."""
        out: List[Dict[str, float]] = []
        torch = self._torch
        with torch.no_grad():
            for start in range(0, len(pairs), BATCH_SIZE):
                batch = pairs[start:start + BATCH_SIZE]
                encoded = self._tokenizer(
                    [p for p, _ in batch], [h for _, h in batch],
                    padding=True, truncation=True, max_length=256,
                    return_tensors="pt")
                logits = self._model(**encoded).logits
                probs = torch.softmax(logits, dim=-1)
                for row in probs:
                    out.append({self._id2label[i]: float(row[i])
                                for i in range(len(row))})
        return out

    def compare_one(self, reference: Dict, claims: List[Dict],
                    source: Optional[List[Set[str]]] = None,
                    sentences: Optional[List[str]] = None) -> Dict:
        """Classify one reference. Premises are claims, or sentences if given."""
        hypothesis = reference["statement"]
        if sentences is not None:
            premises = [{"text": s, "claim": None} for s in sentences]
            scope = "material"
        else:
            premises = [{"text": c["text"], "claim": c} for c in claims]
            scope = "claims"

        if not premises:
            return _result(reference, UNRELATED, None, 0.0,
                           "No premises were available to compare against.",
                           reason="no_premises", scope=scope)

        scores = self._score([(p["text"], hypothesis) for p in premises])

        best = None
        for premise, score in zip(premises, scores):
            for label, key in ((REINFORCING, "entailment"),
                               (CONFLICTING, "contradiction")):
                prob = score.get(key, 0.0)
                if prob >= self.min_confidence and (best is None or prob > best[1]):
                    best = (label, prob, premise, key)

        if best is None:
            # The model read every premise and found no relation in either
            # direction. Whether that is the page's silence or extraction's
            # depends on what it was allowed to read.
            strongest = max(
                (max(s.get("entailment", 0.0), s.get("contradiction", 0.0))
                 for s in scores), default=0.0)
            if scope == "claims":
                presence = _discussed(sorted(content_tokens(hypothesis)), source)
                if presence >= SOURCE_PRESENCE_MIN:
                    return _result(
                        reference, UNCOVERED, None, strongest,
                        "No extracted claim entails or contradicts this, though the "
                        "page discusses the subject. Strongest non-neutral score was "
                        "%.2f, below the %.2f threshold." % (strongest, self.min_confidence),
                        reason="subject_present_but_not_extracted", scope=scope)
            return _result(
                reference, UNRELATED, None, strongest,
                "No premise entails or contradicts this. Strongest non-neutral score "
                "was %.2f, below the %.2f threshold." % (strongest, self.min_confidence),
                reason="model_found_no_relation", scope=scope)

        label, prob, premise, key = best
        return _result(
            reference, label, premise["claim"], prob,
            "The model reads the source sentence as %s of this reference, at %.2f "
            "confidence." % ("an entailment" if key == "entailment"
                             else "a contradiction", prob),
            scope=scope, sentence=premise["text"])

    def compare_all(self, references: List[Dict], claims: List[Dict],
                    source: Optional[List[Set[str]]] = None,
                    sentences: Optional[List[str]] = None) -> List[Dict]:
        return [self.compare_one(ref, claims, source, sentences)
                for ref in references]


def _result(reference: Dict, label: str, claim: Optional[Dict], confidence: float,
            rationale: str, reason: Optional[str] = None,
            scope: str = "claims", sentence: Optional[str] = None) -> Dict:
    """Same shape as compare._result, so downstream code cannot tell them apart.

    The verifier and the report must work identically for either backend,
    including the grounding check that reads every cited sentence back out of
    the source.
    """
    evidence = None
    if sentence is not None or claim is not None:
        evidence = {
            "claim_id": claim.get("claim_id") if claim else None,
            "source_sentence": sentence if sentence is not None else claim["text"],
            "axis": claim["axis"] if claim else None,
            "polarity": claim["polarity"] if claim else None,
            "marker": claim["marker"] if claim else None,
            "qualifiers": claim["qualifiers"] if claim else [],
        }
    return {
        "reference_id": reference["id"],
        "reference_statement": reference["statement"],
        "classification": label,
        "decided": label in DECIDED,
        "reason": reason,
        "backend": "nli",
        "scope": scope,
        "confidence": round(confidence, 3),
        "subject_overlap": None,
        "rationale": rationale,
        "evidence": evidence,
    }
