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

from .claims import AXES, content_tokens
from .compare import (CONFLICTING, DECIDED, REINFORCING, SOURCE_PRESENCE_MIN,
                      SUBJECT_OVERLAP_MIN, UNCOVERED, UNRELATED, _discussed)

MODEL_NAME = "cross-encoder/nli-deberta-v3-base"

#: Minimum probability before the model's verdict is treated as an assertion.
#: Declared before measurement. Not tuned against any evaluation set.
MIN_CONFIDENCE = 0.50

#: How many premise/hypothesis pairs to score at once.
BATCH_SIZE = 16

# ---------------------------------------------------------------------------
# The two fixes, added 2026-09-12 after held-out set v2 and its predictions
# were committed and pushed, and after the unfixed backend was scored on v2.
# Both were designed from failures seen on the stress set and v1 sample, which
# is exactly why neither of those sets may be used to judge them. Every
# constant below was set before v2 was scored with the fixes in place.
# ---------------------------------------------------------------------------

#: Fix 1, decontextualization. A sentence like "Tracing is enabled by
#: default." never says whose tracing, so a strict inference model will not
#: let it entail "OpenAI Agents SDK tracing is enabled by default". Prefixing
#: the page's own context restores what a human reader already knows from
#: where the sentence sits. Only the model sees the prefix. Evidence still
#: cites the verbatim sentence, so the verifier's grounding check is unchanged.
DECONTEXTUALIZE = True

#: Fix 2, the contradiction gate. The model will call two statements about
#: different things a contradiction at high confidence ("The SDK omits that
#: identifier from redacted spans" against "tracing is enabled by default",
#: 0.96). A contradiction is only accepted when the premise shares enough of
#: the reference's topic. Overlap is measured after removing the page's context
#: words, which every premise shares and which would otherwise let everything
#: through, and after removing polarity words, which differ by design in a real
#: contradiction. The threshold reuses SUBJECT_OVERLAP_MIN rather than
#: introducing a new number.
GATE_CONTRADICTIONS = True
GATE_MIN = SUBJECT_OVERLAP_MIN

_POLARITY_WORDS = set()
for _positive, _negative in AXES.values():
    _POLARITY_WORDS |= _positive | _negative


def context_prefix(title: Optional[str]) -> str:
    """Turn a page title into a short phrase the model can read."""
    if not title:
        return ""
    parts = [p.strip() for p in title.split(" - ") if p.strip()]
    if len(parts) == 2:
        return "In the %s documentation on %s: " % (parts[1], parts[0])
    return "From the page titled \"%s\": " % title


def topical_overlap(reference: str, premise: str, title: Optional[str]) -> Optional[float]:
    """Share of the reference's own topic words that the premise also contains.

    Returns None when the reference has no topic words left once context and
    polarity are removed. In that case the gate cannot judge, and it does not
    block. "Tracing is disabled." would otherwise lose every conflict it has.
    """
    shared = content_tokens(title or "")
    ref_words = content_tokens(reference) - shared - _POLARITY_WORDS
    if not ref_words:
        return None
    premise_words = content_tokens(premise) - shared - _POLARITY_WORDS
    return len(ref_words & premise_words) / float(len(ref_words))


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
                 min_confidence: float = MIN_CONFIDENCE,
                 decontextualize: bool = DECONTEXTUALIZE,
                 gate_contradictions: bool = GATE_CONTRADICTIONS) -> None:
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
        self.decontextualize = decontextualize
        self.gate_contradictions = gate_contradictions
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
                    sentences: Optional[List[str]] = None,
                    title: Optional[str] = None) -> Dict:
        """Classify one reference. Premises are claims, or sentences if given.

        `title` is the source page's title. It is only used when the fixes are
        switched on: as context for decontextualization, and as the set of
        words every premise shares, for the contradiction gate.
        """
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

        prefix = context_prefix(title) if self.decontextualize else ""
        scores = self._score([(prefix + p["text"], hypothesis) for p in premises])

        best = None
        gated = 0
        for premise, score in zip(premises, scores):
            for label, key in ((REINFORCING, "entailment"),
                               (CONFLICTING, "contradiction")):
                prob = score.get(key, 0.0)
                if prob < self.min_confidence:
                    continue
                if label == CONFLICTING and self.gate_contradictions:
                    # Judged on the verbatim sentence, never the prefixed one.
                    overlap = topical_overlap(hypothesis, premise["text"], title)
                    if overlap is not None and overlap < GATE_MIN:
                        gated += 1
                        continue
                if best is None or prob > best[1]:
                    best = (label, prob, premise, key)

        if best is None:
            # The model read every premise and found no relation in either
            # direction. Whether that is the page's silence or extraction's
            # depends on what it was allowed to read.
            strongest = max(
                (max(s.get("entailment", 0.0), s.get("contradiction", 0.0))
                 for s in scores), default=0.0)
            gate_note = ("" if not gated else
                         " %d contradiction(s) above threshold were set aside because "
                         "the premise did not share the reference's topic." % gated)
            if scope == "claims":
                presence = _discussed(sorted(content_tokens(hypothesis)), source)
                if presence >= SOURCE_PRESENCE_MIN:
                    return _result(
                        reference, UNCOVERED, None, strongest,
                        "No extracted claim entails or contradicts this, though the "
                        "page discusses the subject. Strongest non-neutral score was "
                        "%.2f, below the %.2f threshold.%s"
                        % (strongest, self.min_confidence, gate_note),
                        reason="subject_present_but_not_extracted", scope=scope,
                        gated=gated)
            return _result(
                reference, UNRELATED, None, strongest,
                "No premise entails or contradicts this. Strongest non-neutral score "
                "was %.2f, below the %.2f threshold.%s"
                % (strongest, self.min_confidence, gate_note),
                reason="model_found_no_relation", scope=scope, gated=gated)

        label, prob, premise, key = best
        return _result(
            reference, label, premise["claim"], prob,
            "The model reads the source sentence as %s of this reference, at %.2f "
            "confidence." % ("an entailment" if key == "entailment"
                             else "a contradiction", prob),
            scope=scope, sentence=premise["text"], gated=gated)

    def compare_all(self, references: List[Dict], claims: List[Dict],
                    source: Optional[List[Set[str]]] = None,
                    sentences: Optional[List[str]] = None,
                    title: Optional[str] = None) -> List[Dict]:
        return [self.compare_one(ref, claims, source, sentences, title)
                for ref in references]


def _result(reference: Dict, label: str, claim: Optional[Dict], confidence: float,
            rationale: str, reason: Optional[str] = None,
            scope: str = "claims", sentence: Optional[str] = None,
            gated: int = 0) -> Dict:
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
        "gated_contradictions": gated,
        "subject_overlap": None,
        "rationale": rationale,
        "evidence": evidence,
    }
