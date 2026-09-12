#!/usr/bin/env python3
"""Generate an unbiased reference sample from the source page.

    python3 sample_references.py > fixtures/sampled.json

The held-out set in fixtures/heldout.json is a STRESS set: I wrote it knowing
how the comparator works, and I picked cases likely to break it. That makes
its score a measure of where the system fails, not a measure of the task.

This set is different. References are produced by a fixed mechanical rule with
no judgement applied to which sentences are chosen:

  1. Split the page into sentences.
  2. Keep sentences 40 to 200 characters long that mention a focus term and
     read as prose (start with a capital, do not end in a colon).
  3. Take every 3rd survivor, up to 12.
  4. For each, emit the sentence VERBATIM as a reference whose truth is
     'reinforcing'. The page cannot disagree with its own sentence.
  5. Where the sentence contains an auxiliary (is/are/can/will/may/does),
     insert 'not' after the first one and emit that as a reference whose
     truth is 'conflicting'.

Whatever comes out is kept. Nothing is dropped for being inconvenient, and
nothing in harness/ may be tuned against the result.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness.claims import split_sentences
from harness.provenance import to_source_record

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "tests", "fixture_tracing_page_2026-09-11.html")
FOCUS = ["tracing", "traces", "trace", "spans", "span", "sdk", "agents",
         "sensitive", "data", "workflow"]
AUX = re.compile(r"\b(is|are|can|will|may|does)\b")
STRIDE = 3
LIMIT = 12


def page_text():
    with open(PAGE, "rb") as fh:
        body = fh.read()
    raw = {"url": "https://openai.github.io/openai-agents-python/tracing/",
           "http_status": None, "fetched_at": "sampling",
           "content_sha256": hashlib.sha256(body).hexdigest(),
           "content_length": len(body), "etag": None, "last_modified": None,
           "content_type": "text/html", "_body": body,
           "fetch_mode": "offline_fixture", "fixture_path": "tests/"}
    return to_source_record(raw)["text"]


def eligible(sentence):
    if not (40 <= len(sentence) <= 200):
        return False
    if sentence.endswith(":") or not sentence[:1].isupper():
        return False
    low = sentence.lower()
    return any(term in low for term in FOCUS)


def negate(sentence):
    match = AUX.search(sentence)
    if not match:
        return None
    return sentence[:match.end()] + " not" + sentence[match.end():]


def main():
    sentences = [s for s in split_sentences(page_text()) if eligible(s)]
    picked, seen = [], set()
    for sentence in sentences[::STRIDE]:
        if sentence in seen:
            continue
        seen.add(sentence)
        picked.append(sentence)
        if len(picked) == LIMIT:
            break

    refs, expectations = [], []
    for i, sentence in enumerate(picked, 1):
        rid = "s%02d" % i
        refs.append({"id": rid, "statement": sentence, "truth": "reinforcing",
                     "predicted_system": "unknown",
                     "why": "Verbatim sentence from the source page."})
        expectations.append({"reference_id": rid, "expected": "reinforcing"})
        flipped = negate(sentence)
        if flipped:
            refs.append({"id": rid + "n", "statement": flipped,
                         "truth": "conflicting", "predicted_system": "unknown",
                         "why": "Same sentence with 'not' inserted after the first auxiliary."})
            expectations.append({"reference_id": rid + "n", "expected": "conflicting"})

    out = {
        "note": ("Mechanically sampled from the source page by sample_references.py. "
                 "No judgement was applied to which sentences were chosen, so this "
                 "measures the task rather than the system's known weak points. "
                 "Compare against fixtures/heldout.json, which is a stress set."),
        "procedure": {"stride": STRIDE, "limit": LIMIT,
                      "length_range": [40, 200], "page": os.path.basename(PAGE)},
        "focus_terms": FOCUS,
        "references": refs,
        "expectations": expectations,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
