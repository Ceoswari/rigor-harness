#!/usr/bin/env python3
"""Measure the comparator against a held-out reference set.

    python3 evaluate.py

This is a measurement, not a verification. It always exits 0: its job is to
report how often the comparator agrees with a careful reader on references it
was never built against, not to pass or fail a build.

The held-out set carries two columns written before this was ever run:
`truth`, the label a careful reader assigns, and `predicted_system`, the label
I expected this implementation to produce. Both are reported, because being
wrong in a way you predicted is a different kind of wrong from being
surprised.

Nothing in harness/ may be tuned to improve this number. A held-out set that
gets tuned on is just a second training set with a nicer name.
"""
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
HELDOUT = os.path.join(HERE, "fixtures", "heldout.json")
URL = "https://openai.github.io/openai-agents-python/tracing/"

# A conflict reported where none exists is the expensive error: it sends a
# reader to re-check a source that was right. Missing a reinforcement is
# cheaper. They are counted separately.
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


def main():
    with open(HELDOUT, encoding="utf-8") as fh:
        data = json.load(fh)
    body = open(PAGE, "rb").read()
    raw = {"url": URL, "http_status": None, "fetched_at": "held-out evaluation",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": os.path.relpath(PAGE, HERE)}
    record = to_source_record(raw)
    claims = extract(record["text"], set(data["focus_terms"]))

    rows, errors = [], {}
    correct = predicted_right = 0
    for ref in data["references"]:
        result = compare.compare_one(ref, claims)
        actual = result["classification"]
        ok = actual == ref["truth"]
        correct += ok
        predicted_right += actual == ref["predicted_system"]
        kind = error_kind(ref["truth"], actual)
        if kind:
            errors[kind] = errors.get(kind, 0) + 1
        rows.append({"id": ref["id"], "statement": ref["statement"],
                     "truth": ref["truth"], "predicted": ref["predicted_system"],
                     "actual": actual, "correct": ok, "error_kind": kind,
                     "evidence": (result.get("evidence") or {}).get("source_sentence"),
                     "why": ref["why"]})

    total = len(rows)
    print("Held-out evaluation: %d references the comparator was never built against\n" % total)
    print("%-5s %-14s %-14s %-14s %s" % ("id", "truth", "I predicted", "actual", ""))
    for r in rows:
        print("%-5s %-14s %-14s %-14s %s"
              % (r["id"], r["truth"], r["predicted"], r["actual"],
                 "ok" if r["correct"] else "MISS (%s)" % r["error_kind"]))
    print("\nAgreement with a careful reader : %d/%d (%.0f%%)"
          % (correct, total, 100.0 * correct / total))
    print("My advance prediction was right : %d/%d (%.0f%%)"
          % (predicted_right, total, 100.0 * predicted_right / total))
    if errors:
        print("Error breakdown                 : "
              + ", ".join("%s %d" % (k, v) for k, v in sorted(errors.items())))

    out = {"total": total, "correct": correct, "accuracy": round(correct / float(total), 3),
           "prediction_accuracy": round(predicted_right / float(total), 3),
           "errors": errors, "rows": rows,
           "source_sha256": raw["content_sha256"], "page": os.path.basename(PAGE)}
    path = os.path.join(HERE, "out", "heldout.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print("\nwrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
