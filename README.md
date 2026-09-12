# rigor-harness

A small pipeline that ingests one public technical page, extracts a bounded set of
material claims with provenance, compares them against a reference set, classifies each
reference as reinforcing, conflicting, indeterminate, distinct or unrelated, and then
verifies its own run before reporting success.

Built for the Bounded Autonomous AI Systems Pilot (Kevin Ng, September 2026). Fixed
source: the OpenAI Agents SDK tracing page,
`https://openai.github.io/openai-agents-python/tracing/`.

**Start with the two honest numbers.** Against the three supplied fixtures it passes
every acceptance test. Against 14 held-out references it was never built to handle, it
agrees with a careful reader 3 times out of 14. Both numbers are reproducible below, and
the second one is the more useful of the two.

## Running it

Python 3.9 or newer. No dependencies, no virtualenv, no API key, no install step.

```bash
python3 run.py                    # fetch the live page, classify, verify, report
python3 run.py --inject-failure   # prove a failed check is reported, not hidden
python3 evaluate.py               # measure against the held-out reference set
python3 -m unittest discover -s tests -v      # 32 tests, no network needed
```

`run.py` writes `out/run.json` and `out/report.md`, and exits 0 when verification passes
and 1 when it does not. To run offline against a saved copy of the page, add
`--offline-fixture tests/fixture_tracing_page.html`.

Committed samples: `docs/example-report.md` and `docs/heldout-results.md`.

## What it does, in order

1. `harness/provenance.py` fetches the URL and records url, HTTP status, fetch timestamp,
   SHA-256 of the exact bytes, content length, ETag and Last-Modified. It extracts visible
   prose one block element per line, so inline code stays inside its sentence and code
   examples are dropped.
2. The same module stores the source in a JSON store keyed on a URL-derived `source_id`.
   Re-ingesting the same URL updates that record and never creates a second copy. When the
   content hash changes, `revision_count` increments, so a changed page is a new revision
   of one source rather than a new source.
3. `harness/claims.py` normalizes sentences into propositions of the shape
   (subject, predicate axis, polarity, qualifiers), ranks them by materiality, and keeps
   the top 8.
4. `harness/compare.py` classifies each reference against those claims, matching on
   subject and axis, then on polarity, and preferring a claim that shares the reference's
   own scope.
5. `harness/verify.py` re-derives its checks from the run artifacts and decides whether the
   run is verified.
6. `harness/report.py` writes the JSON and the Markdown report.

## The one design decision that matters

Reference A ("tracing is enabled by default") and Reference B ("tracing is disabled by
default") share every content word but one. Their token overlap is 0.83. Any comparator
built on string similarity, embeddings or keyword matching scores them as near-identical
and will call the conflicting one supporting evidence. That is the failure the pilot
fixtures are designed to catch.

So claims are not compared as text. Each sentence is reduced to a proposition: which
subject it is about, which predicate axis it sits on (enablement, inclusion, requirement,
truth), which side of that axis it takes, and what scope qualifies it (by default,
globally, per run). A conflict is then a structural fact, being the same subject and axis
with opposite polarity, rather than a similarity score below a threshold.

Scope is checked before polarity. "You can disable tracing for a single run" does not
contradict "tracing is enabled by default", so when a reference is scoped and no claim on
that axis carries the same scope, the result is `indeterminate` rather than a false
conflict.

## Verification

The verifier imports nothing from the extraction or comparison modules, including their
tokenizer. A verifier that reuses the classifier's own logic cannot catch the classifier's
own mistakes. It runs 8 checks: provenance present, claim set bounded, every claim verbatim
in the fetched source, every decided classification citing its source sentence, the
near-duplicate references actually separated, and the three fixture expectations.

The grounding check is the one that earns its keep. It re-reads each claim against the
fetched source text, so a fabricated or paraphrased claim fails the run even when every
other stage reports success.

## How good is it, really

Passing the three supplied fixtures is weak evidence, because the comparator was built
against those three fixtures. So there is a held-out set: 14 references in
`fixtures/heldout.json`, written after the implementation was finished and before it was
run against any of them. Each one carries the label a careful reader would assign, and the
label I expected this implementation to produce, both recorded in advance.

**Result: 3 of 14 correct, 21%. My advance predictions were right 9 of 14, 64%.**
Three false conflicts, two missed conflicts, six missed reinforcements. Full table in
`docs/heldout-results.md`.

The failures are informative rather than random:

- **No natural language inference.** Six misses are true statements lifted from the page
  that sit on no declared axis, like "Traces are composed of spans." The system has no way
  to confirm them, so it says nothing.
- **Modality is invisible.** "Tracing must be enabled manually before it will record
  anything" contradicts the page, and the comparator calls it reinforcing, because it reads
  the word "enabled" and not the claim about what is required. Calling a contradiction
  support is the worst failure in the set.
- **Two are arithmetic, not conceptual.** Subject overlap divides by the shorter subject,
  so a claim whose subject is just "tracing" scores 1.0 against nearly any sentence
  mentioning tracing, which is how a plain restatement of the per-run claim came out as a
  conflict. And one reference missed the 0.34 overlap threshold by a hundredth.

**Those last two are not fixed, deliberately.** They are a few lines each, and fixing them
would raise the number. It would also destroy the only honest measurement in this repo,
because a held-out set tuned against is just a second training set with a nicer name. The
21% stands as the baseline the next implementation has to beat. `tests/test_heldout_baseline.py`
locks the measurement so no future change can move it quietly.

## Reuse before build

The full scan, with benchmark numbers and sources, is in `REUSE_SCAN.md`. It was run after
the first implementation rather than before it, which is the wrong order and is noted there.
Summary:

- **HTML extraction.** BUILD for this pilot, ADOPT trafilatura if the source set ever grows.
  Trafilatura benchmarks at 0.910 accuracy against readability-lxml at 0.820 over 750
  documents. The evidence cuts against my call: the hand-rolled parser's first version
  truncated every sentence containing inline code, which is exactly what a benchmarked
  library gets right.
- **Comparison.** ADAPT an NLI cross-encoder, and this is the next build.
  `cross-encoder/nli-deberta-v3-base` is about 0.2B parameters, outputs entailment,
  contradiction and neutral, which map onto this pilot's labels almost one to one, and
  reports 90.04 on MNLI mismatched. The rule-based comparator it would replace scores 21%.
- **Fact-verification pipelines.** BORROW the stage decomposition from Loki, OpenFactCheck
  and Claimify, do not adopt them. They are built to retrieve evidence from the open web,
  and the pilot compares against a supplied reference set with no external services. The
  scan did surface a real defect: Claimify treats decontextualization as its own stage and
  this implementation has none, which is why an extracted claim still begins "These may
  contain sensitive data".
- **Provenance.** BORROW the W3C PROV vocabulary, do not adopt the `prov` library. One
  source record with a hash does not need a serializable provenance graph.
- **Agent frameworks and MCP.** Not adopted. Ingestion and comparison are deterministic,
  and an agent loop adds nondeterminism to the part that most needs to be reproducible.
- **ADOPT, plainly.** The Python standard library, and Claude Code as the build environment.

## Implementation note

**What the run actually demonstrated.** The most useful evidence here was not a passing
test. The page changed upstream between September 4 and September 11. The pipeline kept
passing against the saved copy and failed against the live page, and the verification step
reported the failure instead of presenting the run as successful. The cause was real:
claims are ranked and truncated to a bounded set, and on the new page "Tracing is enabled
by default." fell out of the set, so both comparisons resolved against the wrong sentence.
Both page versions are now committed fixtures and both verify.

**What did not work in the first pass.** Four defects, all found by reading the code and
the output rather than by the tests, which passed throughout:

- The HTML extractor emitted every text node on its own line, so every sentence containing
  inline code was truncated. Half the extracted claims were fragments ending in "via" or
  "by setting".
- Claim ranking rewarded long sentences for mentioning more focus terms, which pushed the
  single most material claim on the page out of the bounded set.
- Negation was searched across the whole sentence, so "Disabling tracing prevents new
  spans, but it does not discard buffered data" was read as positive. Negation is now
  scoped to the words immediately before the axis word.
- The verifier imported the extractor's tokenizer while its docstring claimed independence.

**Where human intervention was required.** Caleb set the scope, made the build-versus-reuse
calls, reviewed the output and decided what shipped, including the decision to leave the
two held-out failures unfixed. The implementation, the debugging and the tests were done by
Claude Code under that direction. That division is the honest answer to the question this
pilot is testing, and it is worth stating plainly rather than implying a human wrote the
Python.

**Known limitations.** Comparison is lexical and structural, not inference, and the held-out
set puts a number on what that costs. Extraction only sees the four predicate axes declared
in `harness/claims.py`. Claims are not decontextualized, so some carry unresolved references.
Sentence splitting is tuned for documentation pages rather than prose. Materiality ranking is
a heuristic, and the September 11 drift showed that a bounded set plus a heuristic ranking is
where this design is most fragile.

**What I would build next, in order.** Replace the comparator with an NLI cross-encoder while
keeping the deterministic verifier unchanged, and measure it against the same held-out set,
where it has to beat 3 of 14. Add a decontextualization stage so claims stand alone. Schedule
the run so upstream drift is caught on a cadence rather than by accident, and diff claims
between revisions so the report says what changed rather than only that the hash changed.

## Layout

```
run.py                      one-command entry point
evaluate.py                 held-out measurement, reports rather than passes or fails
harness/provenance.py       fetch, text extraction, source record, idempotent store
harness/claims.py           sentence to proposition, materiality ranking, bounded extraction
harness/compare.py          reference against claims, scope before polarity
harness/verify.py           independent checks, imports nothing from the pipeline
harness/report.py           JSON and Markdown output
fixtures/references.json    the three pilot references and their expectations
fixtures/heldout.json       14 held-out references with truth and advance predictions
tests/                      32 tests, two saved copies of the source page
REUSE_SCAN.md               the current-state scan, with benchmarks and sources
docs/example-report.md      committed sample of the human-readable output
docs/heldout-results.md     committed held-out scorecard
out/                        run artifacts, gitignored
```
