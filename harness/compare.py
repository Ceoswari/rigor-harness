"""Compare reference statements against extracted source claims.

**Why there are three ways of not answering.**

The first version of this module had one label, `unrelated`, for every case it
could not decide. Kevin Ng's review caught what that hides, and the
mechanically sampled evaluation set showed the scale of it: 17 of 20
references came back `unrelated`, including sentences lifted verbatim off the
page the system had just read. "Unrelated" was standing in for three different
situations that call for three different fixes:

  unrelated        The source genuinely says nothing about this subject. This
                   is a correct answer and needs no fix.

  unrepresentable  The reference states something the system has no predicate
                   axis for, so no proposition can be formed at all. This is a
                   limit of the vocabulary in claims.py, and the fix is either
                   another axis or a real inference model.

  uncovered        The source does discuss this subject, but no extracted
                   claim speaks to it. Extraction is bounded at 8 claims and
                   ranked by a heuristic, so this is a recall problem in
                   extraction, not a comparison problem.

Telling them apart needs one thing the comparator did not previously have:
sight of the whole source, not just the claims that survived extraction. That
is what the `source` index is for. Without it the two halves of the
distinction collapse back into `unrelated`, and the rationale says so rather
than pretending.
"""
from typing import Dict, List, Optional, Sequence, Set

from .claims import content_tokens, normalize, split_sentences

REINFORCING = "reinforcing"
CONFLICTING = "conflicting"
INDETERMINATE = "indeterminate"      # related and representable, evidence undecisive
DISTINCT = "distinct"                # same subject, different property
UNRELATED = "unrelated"              # the source does not discuss this subject
UNREPRESENTABLE = "unrepresentable"  # no axis exists for this statement
UNCOVERED = "uncovered"              # discussed by the source, missed by extraction

#: Labels that assert a relationship between reference and source.
DECIDED = (REINFORCING, CONFLICTING, DISTINCT)
#: Labels that decline, each for a different and recorded reason.
DECLINED = (INDETERMINATE, UNRELATED, UNREPRESENTABLE, UNCOVERED)

SUBJECT_OVERLAP_MIN = 0.34
SOURCE_PRESENCE_MIN = 0.34


def source_index(text: str) -> List[Set[str]]:
    """Token sets for the source's sentences.

    Used only to answer one question: does the page discuss this subject
    anywhere, whether or not a claim about it was extracted?
    """
    return [content_tokens(s) for s in split_sentences(text) if len(s) >= 15]


def _overlap(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(min(len(sa), len(sb)))


def _discussed(subject: Sequence[str], index: Optional[List[Set[str]]]) -> float:
    """Best subject overlap against any sentence in the source."""
    if not index:
        return 0.0
    return max((_overlap(subject, sorted(tokens)) for tokens in index), default=0.0)


def _undecided_without_index(reference: Dict, score: float, what: str) -> Dict:
    return _result(reference, UNRELATED, None, score,
                   "No source claim shares this reference's subject. Whether the "
                   "page discusses it elsewhere was not checked, because no source "
                   "index was supplied, so %s cannot be separated from genuinely "
                   "unrelated here." % what,
                   reason="no_source_index")


def compare_one(reference: Dict, claims: List[Dict],
                source: Optional[List[Set[str]]] = None) -> Dict:
    """Classify one reference against the extracted claim set.

    `source` is the index from source_index(). Pass it whenever the full
    source text is available: without it, `unrepresentable` and `uncovered`
    both collapse into `unrelated`.

    Every result carries the claim it was decided against, so the evidence
    behind a label is always recoverable (handoff section 3, invariant D).
    Every result that declines carries a `reason` saying which kind of
    not-knowing it is.
    """
    ref_prop = normalize(reference["statement"])

    if ref_prop is None:
        # Nothing on a declared axis, so no proposition exists to compare.
        # The question left is whether the page talks about this at all.
        ref_tokens = sorted(content_tokens(reference["statement"]))
        presence = _discussed(ref_tokens, source)
        best, best_score = None, 0.0
        for claim in claims:
            score = _overlap(ref_tokens, claim["subject"])
            if score > best_score:
                best, best_score = claim, score
        if source is None:
            if best_score >= SUBJECT_OVERLAP_MIN:
                return _result(reference, UNREPRESENTABLE, best, best_score,
                               "The source discusses this subject, but the reference "
                               "states no claim on any axis the system can express.",
                               reason="no_axis_for_statement")
            return _result(reference, UNRELATED, None, best_score,
                           "No comparable proposition and no material subject overlap.",
                           reason="subject_absent_from_source")
        if presence >= SOURCE_PRESENCE_MIN:
            return _result(reference, UNREPRESENTABLE, best, max(best_score, presence),
                           "The source discusses this subject, but the reference states "
                           "no claim on any axis the system can express, so no "
                           "proposition could be formed to compare.",
                           reason="no_axis_for_statement")
        return _result(reference, UNRELATED, None, presence,
                       "The source does not discuss this subject, and the reference "
                       "states no claim on a comparable axis.",
                       reason="subject_absent_from_source")

    candidates = []
    for claim in claims:
        score = _overlap(ref_prop["subject"], claim["subject"])
        if score >= SUBJECT_OVERLAP_MIN:
            candidates.append((score, claim))

    if not candidates:
        # Representable, but nothing extracted speaks to it. Whether that is
        # the page's silence or extraction's is the distinction that matters.
        if source is None:
            return _undecided_without_index(reference, 0.0, "an extraction gap")
        presence = _discussed(ref_prop["subject"], source)
        if presence >= SOURCE_PRESENCE_MIN:
            return _result(reference, UNCOVERED, None, presence,
                           "The source discusses this subject, but no extracted claim "
                           "speaks to it. Extraction is bounded and ranked, so this is "
                           "a gap in what was extracted rather than a statement about "
                           "the reference.",
                           reason="subject_present_but_not_extracted")
        return _result(reference, UNRELATED, None, presence,
                       "No source claim shares this reference's subject, and the page "
                       "does not discuss it elsewhere.",
                       reason="subject_absent_from_source")

    same_axis = [(s, c) for s, c in candidates if c["axis"] == ref_prop["axis"]]
    if not same_axis:
        score, claim = max(candidates, key=lambda pair: pair[0])
        return _result(reference, DISTINCT, claim, score,
                       "Same subject, but the source speaks to a different property.")

    # Scope before overlap. "Tracing is enabled by default" is not
    # contradicted by "you can disable tracing for a single run", so a claim
    # carrying the reference's own qualifiers is preferred over one that
    # merely shares more words.
    ref_quals = set(ref_prop["qualifiers"])
    score, claim = max(
        same_axis,
        key=lambda pair: (len(ref_quals & set(pair[1]["qualifiers"])), pair[0]))
    claim_quals = set(claim["qualifiers"])

    reason = None
    if claim["polarity"] == ref_prop["polarity"]:
        label, why = REINFORCING, "Same subject and axis, same polarity."
    else:
        label, why = CONFLICTING, "Same subject and axis, opposite polarity."

    if ref_quals and not (ref_quals & claim_quals):
        label = INDETERMINATE
        reason = "scope_mismatch"
        why = ("Polarity comparison is not decisive: the reference is scoped %s "
               "and no source claim on this axis carries that scope (closest "
               "is scoped %s)." % (sorted(ref_quals), sorted(claim_quals) or "not at all"))

    result = _result(reference, label, claim, score, why, reason=reason)
    result["reference_proposition"] = ref_prop
    return result


def _result(reference: Dict, label: str, claim: Optional[Dict], score: float,
            rationale: str, reason: Optional[str] = None) -> Dict:
    return {
        "reference_id": reference["id"],
        "reference_statement": reference["statement"],
        "classification": label,
        "decided": label in DECIDED,
        "reason": reason,
        "subject_overlap": round(score, 3),
        "rationale": rationale,
        "evidence": None if claim is None else {
            "claim_id": claim.get("claim_id"),
            "source_sentence": claim["text"],
            "axis": claim["axis"],
            "polarity": claim["polarity"],
            "marker": claim["marker"],
            "qualifiers": claim["qualifiers"],
        },
    }


def compare_all(references: List[Dict], claims: List[Dict],
                source: Optional[List[Set[str]]] = None) -> List[Dict]:
    return [compare_one(ref, claims, source) for ref in references]
