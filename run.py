#!/usr/bin/env python3
"""One-command entry point for the rigor harness pilot.

    python3 run.py                    # normal run against the fixed source
    python3 run.py --inject-failure   # prove a failed check is reported, not hidden

Standard library only. No install step, no virtualenv, no API key.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness import compare, report, verify
from harness.claims import extract
from harness.provenance import SourceStore, fetch, to_source_record

DEFAULT_SOURCE = "https://openai.github.io/openai-agents-python/tracing/"
HERE = os.path.dirname(os.path.abspath(__file__))

LIMITATIONS = [
    "Comparison is lexical-semantic (subject overlap plus a polarity axis), not full "
    "natural-language inference. It separates opposed statements about the same "
    "property; it does not resolve paraphrase with no shared vocabulary.",
    "Claim extraction is bounded by the predicate axes declared in harness/claims.py. "
    "A claim on an axis not listed there is not extracted.",
    "Sentence splitting is heuristic and tuned for documentation pages rather than prose.",
    "The run reflects the source as fetched. A later edit to the page changes the content "
    "hash and produces a new revision rather than silently altering this run.",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rigor harness pilot")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--fixtures", default=os.path.join(HERE, "fixtures", "references.json"))
    parser.add_argument("--out", default=os.path.join(HERE, "out"))
    parser.add_argument("--store", default=os.path.join(HERE, "out", "sources.json"))
    parser.add_argument("--inject-failure", action="store_true",
                        help="Corrupt one expectation to demonstrate visible failure.")
    parser.add_argument("--offline-fixture", default=None,
                        help="Path to saved HTML, for reproducible offline runs.")
    args = parser.parse_args(argv)

    with open(args.fixtures, "r", encoding="utf-8") as fh:
        fixture_data = json.load(fh)

    if args.offline_fixture:
        with open(args.offline_fixture, "rb") as fh:
            body = fh.read()
        import hashlib, time
        # No HTTP request happened, so none is claimed: status is None and
        # fetch_mode says where the bytes actually came from.
        raw = {"url": args.source, "http_status": None,
               "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "content_sha256": hashlib.sha256(body).hexdigest(),
               "content_length": len(body), "etag": None, "last_modified": None,
               "content_type": "text/html", "_body": body,
               "fetch_mode": "offline_fixture",
               "fixture_path": os.path.relpath(args.offline_fixture, HERE)}
    else:
        raw = fetch(args.source)

    record = to_source_record(raw)
    store = SourceStore(args.store)
    upsert = store.upsert(record)
    store.save()

    focus = set(fixture_data.get("focus_terms", []))
    claims = extract(upsert["record"]["text"], focus)
    comparisons = compare.compare_all(fixture_data["references"], claims)

    expectations = list(fixture_data["expectations"])
    if args.inject_failure:
        expectations = [dict(e) for e in expectations]
        expectations[0]["expected"] = "conflicting"   # ref_a truly reinforces
        print("[inject-failure] ref_a expectation deliberately set to 'conflicting'.")

    run = {
        "source": upsert["record"],
        "store_action": upsert["action"],
        "content_changed": upsert["content_changed"],
        "sources_in_store": store.count(),
        "claims": claims,
        "comparisons": comparisons,
        "limitations": LIMITATIONS,
    }
    verification = verify.verify(run, expectations)

    json_path = report.write_json(run, verification, os.path.join(args.out, "run.json"))
    md_path = report.write_markdown(run, verification, os.path.join(args.out, "report.md"))

    print("source        : %s (%s, %d sources in store)"
          % (upsert["record"]["url"], upsert["action"], store.count()))
    print("claims        : %d extracted" % len(claims))
    for comp in comparisons:
        print("  %-7s -> %s" % (comp["reference_id"], comp["classification"]))
    print("verification  : %s" % verification["summary"])
    print("outputs       : %s | %s" % (json_path, md_path))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
