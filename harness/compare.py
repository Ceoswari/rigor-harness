"""Compare reference statements against extracted source claims."""
from typing import Dict, List, Optional

from .claims import content_tokens, normalize

REINFORCING = "reinforcing"
CONFLICTING = "conflicting"
UNRELATED = "unrelated"
DISTINCT = "distinct"          # related subject, different axis
INDETERMINATE = "indeterminate"  # related, but the evidence does not settle it

SUBJECT_OVERLAP_MIN = 0.34


def _overlap(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(min(len(sa), len(sb)))


def compare_one(reference: Dict, claims: List[Dict]) -> Dict:
    """Classify one reference against the extracted claim set.

    Every result carries the claim it was decided against, so the evidence
    behind a label is always recoverable (handoff section 3, invariant D).
    """
    ref_prop = normalize(reference["statement"])

    if ref_prop is None:
        ref_tokens = content_tokens(reference["statement"])
        best, best_score = None, 0.0
        for claim in claims:
            score = _overlap(sorted(ref_tokens), claim["subject"])
            if score > best_score:
                best, best_score = claim, score
        if best_score >= SUBJECT_OVERLAP_MIN:
            return _result(reference, DISTINCT, best, best_score,
                           "Shares subject matter but states no claim on a comparable axis.")
        return _result(reference, UNRELATED, None, best_score,
                       "No comparable proposition and no material subject overlap.")

    candidates = []
    for claim in claims:
        score = _overlap(ref_prop["subject"], claim["subject"])
        if score >= SUBJECT_OVERLAP_MIN:
            candidates.append((score, claim))
    if not candidates:
        return _result(reference, UNRELATED, None, 0.0,
                       "No source claim shares this reference's subject.")

    same_axis = [(s, c) for s, c in candidates if c["axis"] == ref_prop["axis"]]
    if not same_axis:
        score, claim = max(candidates, key=lambda pair: pair[0])
        return _result(reference, DISTINCT, claim, score,
                       "Same subject, but the source speaks to a different property.")

    score, claim = max(same_axis, key=lambda pair: pair[0])
    if claim["polarity"] == ref_prop["polarity"]:
        label, why = REINFORCING, "Same subject and axis, same polarity."
    else:
        label, why = CONFLICTING, "Same subject and axis, opposite polarity."

    ref_quals, claim_quals = set(ref_prop["qualifiers"]), set(claim["qualifiers"])
    if ref_quals and claim_quals and not (ref_quals & claim_quals):
        label = INDETERMINATE
        why = ("Polarity comparison is not decisive: the reference and the source "
               "claim are scoped by different qualifiers (%s vs %s)."
               % (sorted(ref_quals), sorted(claim_quals)))

    result = _result(reference, label, claim, score, why)
    result["reference_proposition"] = ref_prop
    return result


def _result(reference: Dict, label: str, claim: Optional[Dict],
            score: float, rationale: str) -> Dict:
    return {
        "reference_id": reference["id"],
        "reference_statement": reference["statement"],
        "classification": label,
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


def compare_all(references: List[Dict], claims: List[Dict]) -> List[Dict]:
    return [compare_one(ref, claims) for ref in references]
