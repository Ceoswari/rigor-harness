"""Independent verification of a run.

This module is deliberately deterministic and imports nothing from extraction
or comparison. It re-derives what it checks from the run artefacts rather than
trusting any field the pipeline set about itself.

That separation is the point. Handoff invariant B says a run is not successful
because the thing that produced it says so, and a verifier that reuses the
classifier's own reasoning cannot catch the classifier's own mistakes.
"""
import re
from typing import Dict, List

# Kept separate from harness.claims on purpose: the verifier does not import
# the pipeline's own tokenizer, so a bug there cannot hide itself here.
_STOP = {"a", "an", "the", "is", "are", "be", "by", "of", "to", "in", "on",
         "it", "and", "or", "for", "with"}


def content_tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower())
            if t not in _STOP and len(t) > 1}


# Deliberately duplicated rather than imported from harness.compare. This
# module's whole value is that it does not share code with the pipeline it
# checks, so it carries its own copy of the label vocabulary and will fail
# loudly if the comparator starts emitting labels this list has never heard of.
DECIDING_LABELS = ("reinforcing", "conflicting", "distinct")
DECLINING_LABELS = ("indeterminate", "unrelated", "unrepresentable", "uncovered")

# Coverage bounds for what counts as a "material" source sentence. Kept here,
# and deliberately not shared with harness/claims.py, so the verifier's count
# of what the page says does not move when extraction's heuristics move.
MATERIAL_MIN_CHARS = 40
MATERIAL_MAX_CHARS = 300


def _sentences(text: str) -> List[str]:
    """The verifier's own sentence split. Independent of the extractor's."""
    out = []
    for line in text.split("\n"):
        for piece in re.split(r"(?<=[.!?])\s+", line.strip()):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


def _material_sentences(text: str, focus: set) -> List[str]:
    """Sentences a reader would consider substantive claims about the topic.

    Deliberately generous: any prose sentence in the length band that mentions
    a focus term. Over-counting here is the safe direction, because it makes
    coverage look worse rather than better.
    """
    material = []
    for sentence in _sentences(text):
        if not (MATERIAL_MIN_CHARS <= len(sentence) <= MATERIAL_MAX_CHARS):
            continue
        if not sentence[:1].isupper() or sentence.endswith(":"):
            continue
        low = sentence.lower()
        if any(term in low for term in focus):
            material.append(sentence)
    return material


def _check(check_id: str, passed: bool, detail: str) -> Dict:
    return {"check": check_id, "passed": bool(passed), "detail": detail}


def verify(run: Dict, expectations: List[Dict]) -> Dict:
    """Return a verification report. Never mutates the run."""
    checks: List[Dict] = []
    source = run.get("source", {})
    claims = run.get("claims", [])
    comparisons = run.get("comparisons", [])

    checks.append(_check(
        "provenance_present",
        bool(source.get("url")) and bool(source.get("content_sha256"))
        and bool(source.get("first_seen_at")),
        "Source record carries url, content hash and first-seen timestamp.",
    ))

    checks.append(_check(
        "claims_bounded",
        0 < len(claims) <= 12,
        "Extracted %d claims; a bounded set is 1-12." % len(claims),
    ))

    grounded = all(
        c["text"].strip() and c["text"].strip() in source.get("text", "")
        for c in claims
    )
    checks.append(_check(
        "claims_grounded_in_source",
        grounded,
        "Every extracted claim sentence appears verbatim in the fetched source text.",
    ))

    decided = [c for c in comparisons if c["classification"] in DECIDING_LABELS]
    cited = all(c.get("evidence") and c["evidence"].get("source_sentence") for c in decided)
    checks.append(_check(
        "classifications_cite_evidence",
        cited,
        "Every classification asserting a relationship names the source sentence "
        "behind it (%d of %d comparisons assert one)." % (len(decided), len(comparisons)),
    ))

    # A declined result has to say which kind of not-knowing it is. Collapsing
    # them into one bare label is the defect this check exists to prevent:
    # "the source says nothing about this" and "the system cannot express
    # this" were reported identically until Sep 12 2026.
    declined = [c for c in comparisons if c["classification"] in DECLINING_LABELS]
    reasoned = all(c.get("reason") for c in declined)
    checks.append(_check(
        "declined_results_name_a_reason",
        reasoned,
        "Every comparison that declines to decide records why (%d of %d declined)."
        % (len(declined), len(comparisons)),
    ))

    known = all(c["classification"] in DECIDING_LABELS + DECLINING_LABELS
                for c in comparisons)
    checks.append(_check(
        "labels_are_in_the_known_vocabulary",
        known,
        "Every classification is one the verifier recognises.",
    ))

    # Re-derive what a surface-similarity baseline would conclude.
    # The discriminating claim is about the REFERENCES, not about any one
    # reference against its matched sentence: ref_a and ref_b differ by a
    # single token, so any overlap-based comparator must give them the same
    # label. Giving them different labels is the thing to evidence.
    near_duplicate_pairs = []
    for i in range(len(comparisons)):
        for j in range(i + 1, len(comparisons)):
            a, b = comparisons[i], comparisons[j]
            ta = content_tokens(a["reference_statement"])
            tb = content_tokens(b["reference_statement"])
            if not ta or not tb:
                continue
            overlap = len(ta & tb) / float(min(len(ta), len(tb)))
            if overlap >= 0.6:
                near_duplicate_pairs.append((a, b, overlap))

    discriminated = [
        (a, b, o) for a, b, o in near_duplicate_pairs
        if a["classification"] != b["classification"]
    ]
    if not near_duplicate_pairs:
        checks.append(_check(
            "beats_naive_overlap_baseline", True,
            "Not applicable: no near-duplicate reference pair in this fixture set.",
        ))
    else:
        detail_bits = ", ".join(
            "%s/%s overlap %.2f -> %s vs %s"
            % (a["reference_id"], b["reference_id"], o,
               a["classification"], b["classification"])
            for a, b, o in near_duplicate_pairs
        )
        checks.append(_check(
            "beats_naive_overlap_baseline",
            len(discriminated) > 0,
            "Near-duplicate references separated by classification (%s). A "
            "surface-similarity comparator scores these pairs as the same "
            "statement and cannot split them." % detail_bits,
        ))

    # Coverage. Invariant B says a run is not successful because the thing
    # that produced it says so, and until now this verifier only asked whether
    # the answers given were correct. It never counted the answers withheld, so
    # a system that represented a fraction of the page and declined on most
    # references passed cleanly. These numbers are re-derived here rather than
    # read off the pipeline.
    focus = set(run.get("focus_terms") or [])
    material = _material_sentences(source.get("text", ""), focus)
    claim_texts = {c.get("text", "").strip() for c in claims}
    represented = [s for s in material if s in claim_texts]
    extraction_coverage = (len(represented) / float(len(material))) if material else None

    declined_by_reason = {}
    for c in declined:
        declined_by_reason[c.get("reason") or "unspecified"] = \
            declined_by_reason.get(c.get("reason") or "unspecified", 0) + 1

    coverage = {
        "material_sentences": len(material),
        "sentences_represented_by_a_claim": len(represented),
        "extraction_coverage": None if extraction_coverage is None
        else round(extraction_coverage, 3),
        "references": len(comparisons),
        "asserted": len(decided),
        "declined": len(declined),
        "declined_by_reason": declined_by_reason,
    }

    # This one can fail, on purpose. The threshold is not a quality bar, it is
    # a floor against one specific failure mode: a run that answers almost
    # nothing and still reports success. If more than half the references are
    # declined, the run has not really compared anything and should not be
    # presented as verified.
    mostly_declined = len(comparisons) > 0 and len(declined) * 2 > len(comparisons)
    checks.append(_check(
        "answers_more_often_than_it_declines",
        not mostly_declined,
        "Declined %d of %d references%s. Extraction represents %s of the page's %d "
        "material sentences." % (
            len(declined), len(comparisons),
            (" (" + ", ".join("%s %d" % kv for kv in sorted(declined_by_reason.items())) + ")")
            if declined_by_reason else "",
            "none" if extraction_coverage is None
            else "%d (%.0f%%)" % (len(represented), 100 * extraction_coverage),
            len(material)),
    ))

    by_ref = {c["reference_id"]: c["classification"] for c in comparisons}
    for exp in expectations:
        actual = by_ref.get(exp["reference_id"])
        checks.append(_check(
            "expectation_%s" % exp["reference_id"],
            actual == exp["expected"],
            "Expected %r for %s, got %r." % (exp["expected"], exp["reference_id"], actual),
        ))

    failed = [c for c in checks if not c["passed"]]
    return {
        "verified": len(failed) == 0,
        "coverage": coverage,
        "checks": checks,
        "failed_checks": [c["check"] for c in failed],
        "summary": ("All %d verification checks passed." % len(checks)) if not failed
        else ("%d of %d verification checks FAILED: %s"
              % (len(failed), len(checks), ", ".join(c["check"] for c in failed))),
    }
