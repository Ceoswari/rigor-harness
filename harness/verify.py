"""Independent verification of a run.

This module is deliberately deterministic and shares no logic with extraction
or comparison. It re-derives what it checks from the run artefacts rather than
trusting any field the pipeline set about itself.

That separation is the point. Handoff invariant B says a run is not successful
because the thing that produced it says so, and a verifier that reuses the
classifier's own reasoning cannot catch the classifier's own mistakes.
"""
from typing import Dict, List

from .claims import content_tokens


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

    decided = [c for c in comparisons if c["classification"] != "unrelated"]
    cited = all(c.get("evidence") and c["evidence"].get("source_sentence") for c in decided)
    checks.append(_check(
        "classifications_cite_evidence",
        cited,
        "Every non-unrelated classification names the source sentence behind it.",
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
        "checks": checks,
        "failed_checks": [c["check"] for c in failed],
        "summary": ("All %d verification checks passed." % len(checks)) if not failed
        else ("%d of %d verification checks FAILED: %s"
              % (len(failed), len(checks), ", ".join(c["check"] for c in failed))),
    }
