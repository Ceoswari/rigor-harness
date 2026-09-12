#!/usr/bin/env python3
"""Measure the comparator against two reference sets it was not built on.

    python3 evaluate.py

This is a measurement, not a verification. It always exits 0: its job is to
report how often the comparator agrees with a careful reader, not to pass or
fail a build.

Two sets, and the difference between them matters:

  fixtures/heldout.json   A STRESS set. I wrote these knowing how the
                          comparator works and chose cases likely to break it,
                          recording in advance both the correct label and the
                          label I expected the system to produce. Its score is
                          a map of failure modes, not a measure of the task.

  fixtures/sampled.json   An UNBIASED sample, generated from the page by
                          sample_references.py using a fixed mechanical rule
                          with no judgement about which sentences are picked.
                          Verbatim page sentences (which the page cannot
                          disagree with) plus their negations.

Reporting only the stress number would overstate the failure. Reporting only
the sampled number would understate it. Both are printed.

Nothing in harness/ may be tuned to improve either. A set that gets tuned on
is just a training set with a nicer name.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness import compare
from harness.claims import extract
from harness.provenance import to_source_record

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "tests", "fixture_tracing_page_2026-09-11.html")
URL = "https://openai.github.io/openai-agents-python/tracing/"

SETS = [("stress", os.path.join(HERE, "fixtures", "heldout.json")),
        ("sampled", os.path.join(HERE, "fixtures", "sampled.json"))]

FALSE_CONFLICT = "false conflict"
MISSED_CONFLICT = "missed conflict"
MISSED_SUPPORT = "missed support"
OTHER = "other"


def error_kind(truth, actual):
    if truth == actual:
        return None
    if actual == "conflicting":
        return FALSE_CONFLICT
    if truth == "conflicting":
        return MISSED_CONFLICT
    if truth == "reinforcing":
        return MISSED_SUPPORT
    return OTHER


def build_claims(focus_terms):
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": URL, "http_status": None, "fetched_at": "evaluation",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture",
           "fixture_path": os.path.relpath(PAGE, HERE)}
    record = to_source_record(raw)
    return (extract(record["text"], set(focus_terms)),
            compare.source_index(record["text"]),
            raw["content_sha256"])


def score(path, compare_fn=None):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    claims, index, sha = build_claims(data["focus_terms"])
    if compare_fn is None:
        def compare_fn(ref, claims, index):
            return compare.compare_one(ref, claims, index)
    rows, errors, correct, predicted_right, predictions = [], {}, 0, 0, 0
    declines = {}
    for ref in data["references"]:
        result = compare_fn(ref, claims, index)
        actual = result["classification"]
        ok = actual == ref["truth"]
        if actual in compare.DECLINED:
            # Declining is usually still a miss: "I cannot express this" is not
            # the right answer. But it is a different failure from asserting
            # something false, so it is counted apart rather than hidden. Note
            # a decline can also be correct, when the reference really is
            # unrelated to the source.
            declines[result["reason"]] = declines.get(result["reason"], 0) + 1
        correct += ok
        if ref.get("predicted_system") not in (None, "unknown"):
            predictions += 1
            predicted_right += actual == ref["predicted_system"]
        kind = error_kind(ref["truth"], actual)
        if kind:
            errors[kind] = errors.get(kind, 0) + 1
        rows.append({"id": ref["id"], "statement": ref["statement"],
                     "truth": ref["truth"],
                     "predicted": ref.get("predicted_system", "unknown"),
                     "actual": actual, "correct": ok, "error_kind": kind,
                     "reason": result.get("reason")})
    total = len(rows)
    # An "opinion" is any label other than unrelated. Splitting these apart
    # matters: a system that is silent 17 times out of 20 and right when it
    # speaks is a different animal from one that guesses wrong, even though
    # flat accuracy scores them the same.
    opinions = [r for r in rows if r["actual"] in compare.DECIDED]
    opinions_right = sum(1 for r in opinions if r["correct"])
    precision = round(opinions_right / float(len(opinions)), 3) if opinions else None
    return {"total": total, "correct": correct,
            "opinions": len(opinions), "opinions_right": opinions_right,
            "precision": precision, "declines": declines,
            "declined": sum(declines.values()),
            "declined_right": sum(1 for r in rows
                                  if r["correct"] and r["actual"] in compare.DECLINED),
            "wrong_assertions": sum(1 for r in rows
                                    if not r["correct"] and r["actual"] in compare.DECIDED),
            "accuracy": round(correct / float(total), 3),
            "predictions_made": predictions, "predictions_right": predicted_right,
            "errors": errors, "rows": rows, "source_sha256": sha,
            "note": data.get("note", "")}


def render(name, res):
    lines = ["", "## %s: %d of %d correct (%.0f%%)"
             % (name, res["correct"], res["total"], 100 * res["accuracy"]), ""]
    if res["predictions_made"]:
        lines.append("Advance predictions correct: %d of %d.\n"
                     % (res["predictions_right"], res["predictions_made"]))
    if res["declines"]:
        lines.append("Declined to decide, by recorded reason: "
                     + ", ".join("`%s` %d" % (k, v)
                                 for k, v in sorted(res["declines"].items())) + ".\n")
    if res["opinions"]:
        lines.append("It asserted a relationship %d times and was right "
                     "%d of those, so precision %.0f%% against recall %.0f%%.\n"
                     % (res["opinions"], res["opinions_right"],
                        100 * res["precision"], 100 * res["accuracy"]))
    if res["errors"]:
        lines.append("Errors: " + ", ".join("%s %d" % (k, v)
                                            for k, v in sorted(res["errors"].items())) + ".\n")
    lines.append("| id | reference | truth | actual | reason | |")
    lines.append("|---|---|---|---|---|---|")
    for r in res["rows"]:
        lines.append("| %s | %s | %s | %s | %s | %s |"
                     % (r["id"], r["statement"].replace("|", "\\|"), r["truth"], r["actual"],
                        "`%s`" % r["reason"] if r["reason"] else "",
                        "ok" if r["correct"] else "**miss** (%s)" % r["error_kind"]))
    return lines


def configurations(which):
    """Which comparison backends to measure, in order.

    'rules' needs nothing installed and is the baseline every other number is
    compared against. The nli configurations need torch and transformers.
    """
    configs = [("rules", None)]
    if which in ("nli", "all"):
        from harness import nli
        comparator = nli.NliComparator()
        text = page_text()
        focus = set(json.load(open(SETS[0][1], encoding="utf-8"))["focus_terms"])
        sentences = nli.material_sentences(text, focus)
        configs.append(("nli-claims", lambda ref, claims, index:
                        comparator.compare_one(ref, claims, index)))
        configs.append(("nli-material", lambda ref, claims, index:
                        comparator.compare_one(ref, claims, index, sentences)))
        print("nli backend: %s, %d material sentences in scope\n"
              % (comparator.model_name, len(sentences)))
    if which == "nli":
        configs = [c for c in configs if c[0] != "rules"] or configs
    return configs


def page_text():
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": URL, "http_status": None, "fetched_at": "evaluation",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": "tests/"}
    return to_source_record(raw)["text"]


def main():
    parser = argparse.ArgumentParser(description="Measure the comparison backends")
    parser.add_argument("--backend", choices=("rules", "nli", "all"), default="rules",
                        help="'rules' is the zero-install baseline. 'all' measures "
                             "every backend on the same frozen sets.")
    args = parser.parse_args()

    configs = configurations(args.backend)
    results = {}
    for config_name, fn in configs:
        for name, path in SETS:
            results["%s/%s" % (config_name, name)] = score(path, fn)
            res = results["%s/%s" % (config_name, name)]
            print("%-14s %-8s %2d/%2d correct (%3.0f%%)  asserted %d (right %d, wrong %d)"
                  "  declined %d (right %d)"
                  % (config_name, name, res["correct"], res["total"],
                     100 * res["accuracy"], res["opinions"], res["opinions_right"],
                     res["wrong_assertions"], res["declined"], res["declined_right"]))

    baseline = {n: results.get("rules/%s" % n) for n, _ in SETS}
    doc = ["# Evaluation results", "",
           "Measured 2026-09-12 against the September 11 copy of the source page "
           "(SHA-256 `%s`)." % list(results.values())[0]["source_sha256"][:16], "",
           "Two sets, because one number on its own would mislead. The stress set was "
           "written by me, knowing the implementation, choosing cases likely to break it. "
           "The sampled set was generated from the page by a fixed mechanical rule with no "
           "judgement about which sentences were chosen. Reproduce both with "
           "`python3 evaluate.py`.", ""]
    doc += ["", "| backend | set | correct | asserted | asserted right | declined |",
            "|---|---|---|---|---|---|"]
    for key in results:
        config_name, set_name = key.split("/")
        r = results[key]
        doc.append("| `%s` | %s | %d of %d (%.0f%%) | %d | %d | %d |"
                   % (config_name, set_name, r["correct"], r["total"],
                      100 * r["accuracy"], r["opinions"], r["opinions_right"],
                      r["declined"]))
    doc.append("")
    for key in results:
        doc += render(key, results[key])
    doc += ["", "## Reading these", "",
            "A false conflict is the expensive error: it sends a reader to re-check a source "
            "that was right. A missed reinforcement is the cheap one: the system fails to "
            "notice agreement and stays quiet. The sampled set is dominated by missed "
            "reinforcements, which says the system is more often silent than wrong.", "",
            "The gap between the two sets is the useful part. On sentences chosen to break "
            "it, the comparator produces confident wrong answers including false conflicts. "
            "On sentences drawn without bias, it mostly declines to answer at all. Its real "
            "coverage is narrow: it has an opinion only when a sentence lands on one of the "
            "four predicate axes declared in harness/claims.py.", ""]
    os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
    with open(os.path.join(HERE, "docs", "evaluation-results.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(doc))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "evaluation.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=True)
    print("\nwrote docs/evaluation-results.md and out/evaluation.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
