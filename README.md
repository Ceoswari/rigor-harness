# rigor-harness

A small pipeline that ingests one public technical page, extracts a bounded set of
material claims with provenance, compares them against a reference set, classifies each
reference as reinforcing, conflicting, indeterminate, distinct or unrelated, and then
verifies its own run before reporting success.

Built for the Bounded Autonomous AI Systems Pilot (Kevin Ng, September 2026). Fixed
source: the OpenAI Agents SDK tracing page,
`https://openai.github.io/openai-agents-python/tracing/`.

## Running it

Python 3.9 or newer. No dependencies, no virtualenv, no API key, no install step.

```bash
python3 run.py
```

That fetches the live page and writes two outputs: `out/run.json` (machine readable) and
`out/report.md` (human readable). Exit status is 0 when verification passes and 1 when it
does not.

To prove a failed check is reported rather than absorbed:

```bash
python3 run.py --inject-failure
```

This corrupts one expectation on purpose. The run prints the failed check, the report says
NOT VERIFIED, and the exit status is 1.

To run offline against a saved copy of the page:

```bash
python3 run.py --offline-fixture tests/fixture_tracing_page.html
```

Tests (29, none requiring network):

```bash
python3 -m unittest discover -s tests -v
```

A committed sample of the human-readable output is in `docs/example-report.md`.

## What it does, in order

1. `harness/provenance.py` fetches the URL and records url, HTTP status, fetch timestamp,
   SHA-256 of the exact bytes, content length, ETag and Last-Modified. It extracts visible
   prose one block element per line, so inline code stays inside its sentence and code
   examples are dropped.
2. The same module stores the source in a JSON store keyed on a URL-derived `source_id`.
   Re-ingesting the same URL updates that record. It never creates a second copy. When the
   content hash changes, `revision_count` increments and the run is a new revision of one
   source rather than a new source.
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

## Reuse before build

A brief scan from working knowledge, not a research exercise.

**ADOPT.** The Python standard library does the whole job: `urllib` for fetching,
`html.parser` for extraction, `hashlib` for content addressing, `json` for storage,
`argparse` for the CLI, `unittest` for tests. Zero dependencies is a real feature here,
because a reviewer can clone and run with one command and nothing to install. Claude Code
(Opus 5) was adopted as the build environment.

**ADOPT, considered and declined for this slice.** An agent framework, the OpenAI Agents
SDK included, adds a runtime loop this task does not have: ingestion and comparison are
deterministic, so an agent would add nondeterminism to the one part that most needs to be
reproducible. A vector store is not justified by three reference statements. `trafilatura`
or `readability-lxml` would beat the hand-rolled HTML extractor on a broad corpus, and I
would adopt one the moment the source set grows past a handful of documentation pages.

**BORROW.** Content addressing as version identity is git's idea. The upsert-on-stable-key
pattern is ordinary ETL practice. The provenance field shape follows W3C PROV loosely
(entity, generation time, derivation). The proposition structure borrows from stance
detection and natural language inference.

**BUILD.** Two pieces are custom, and both are justified by the fixtures. The polarity-axis
comparator exists because no off-the-shelf similarity measure separates Reference A from
Reference B. The independent verifier exists because invariant B asks that a run not be
called successful on the pipeline's own say-so.

## Implementation note

**What the run actually demonstrated.** The most useful evidence in this pilot was not a
passing test. The page changed upstream between September 4 and September 11. The pipeline
kept passing against the saved copy and failed against the live page, and the verification
step reported the failure instead of presenting the run as successful. The cause was real:
claims are ranked and truncated to a bounded set, and on the new page "Tracing is enabled
by default." fell out of the set, so both comparisons resolved against the wrong sentence.
Both page versions are now committed as test fixtures and both verify.

**What did not work in the first pass.** Four defects, all found by reading the code and
the output rather than by the tests, which passed throughout:

- The HTML extractor emitted every text node on its own line, so every sentence containing
  inline code was truncated. Half the extracted claims were fragments ending in "via" or
  "by setting".
- Claim ranking rewarded long sentences for mentioning more focus terms, which is what
  pushed the single most material claim on the page out of the bounded set.
- Negation was searched across the whole sentence, so "Disabling tracing prevents new
  spans, but it does not discard buffered data" was read as positive. Negation is now
  scoped to the words immediately before the axis word.
- The verifier imported the extractor's tokenizer while its docstring claimed
  independence. It now has its own.

**Where human intervention was required.** Caleb set the scope, made the build-versus-reuse
calls, reviewed the output and decided what shipped. The implementation, the debugging and
the tests were done by Claude Code under that direction. That division is the honest answer
to the question this pilot is testing, and it is worth stating plainly rather than implying
a human wrote the Python.

**Known limitations.** Comparison is lexical and structural, not full natural language
inference: it separates opposed statements about the same property, and it will not resolve
a paraphrase that shares no vocabulary. Extraction only sees the four predicate axes
declared in `harness/claims.py`. Sentence splitting is tuned for documentation pages rather
than prose. The materiality ranking is a heuristic, and the September 11 drift showed that
a bounded set plus a heuristic ranking is exactly where this design is most fragile.

**What I would build next, in order.** First, replace the rule-based comparator with a
natural language inference model or an LLM classifier, while keeping the deterministic
verifier unchanged as the independent check. That is the combination worth testing: a
capable but unreliable classifier, graded by something that cannot rationalize. Second,
schedule the run so upstream drift is caught on a cadence rather than by accident, and
diff claims between revisions so the report says what changed rather than only that the
hash changed. Third, and only if the source set actually grows, adopt a real extraction
library and drop the hand-rolled parser.

## Layout

```
run.py                    one-command entry point
harness/provenance.py     fetch, text extraction, source record, idempotent store
harness/claims.py         sentence to proposition, materiality ranking, bounded extraction
harness/compare.py        reference against claims, scope before polarity
harness/verify.py         independent checks, imports nothing from the pipeline
harness/report.py         JSON and Markdown output
fixtures/references.json  the three pilot references and their expectations
tests/                    29 tests, two saved copies of the source page
docs/example-report.md    committed sample of the human-readable output
out/                      run artifacts, gitignored
```
