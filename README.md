# rigor-harness

A small pipeline that ingests one public technical page, extracts a bounded set of
material claims with provenance, compares them against a reference set, classifies each
reference as reinforcing, conflicting, indeterminate, distinct or unrelated, and then
verifies its own run before reporting success.

Built for the Bounded Autonomous AI Systems Pilot (Kevin Ng, September 2026). Fixed
source: the OpenAI Agents SDK tracing page,
`https://openai.github.io/openai-agents-python/tracing/`.

**Start with the numbers.** Against the three supplied fixtures it passes every
acceptance test. Against 14 references chosen to stress it, it is right 3 times. Against
20 references sampled mechanically from the page, it is right 3 times and silent 17
times. All three numbers are reproducible below, and the last two matter more than the
first.

## Running it

Python 3.9 or newer. No dependencies, no virtualenv, no API key, no install step.

```bash
python3 run.py                    # fetch the live page, classify, verify, report
python3 run.py --inject-failure   # prove a failed check is reported, not hidden
python3 evaluate.py               # measure against both reference sets
python3 sample_references.py      # regenerate the mechanically sampled set
python3 -m unittest discover -s tests -v      # 37 tests, no network needed
```

`run.py` writes `out/run.json` and `out/report.md`, and exits 0 when verification passes
and 1 when it does not. To run offline against a saved copy of the page, add
`--offline-fixture tests/fixture_tracing_page.html`.

Committed samples: `docs/example-report.md` and `docs/evaluation-results.md`.

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
   own scope. When it cannot decide, it records which of the three kinds of not-knowing
   applies rather than reporting them all the same way. See below.
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

## Three ways of not answering

The first version had one label, `unrelated`, for everything it could not decide. Kevin
Ng's review caught what that hides, and the sampled evaluation showed the scale: 17 of 20
references came back `unrelated`, including sentences lifted verbatim off the page the
system had just read. The page was not silent. The system was, and it was reporting its
own limitation as a fact about the reference.

That is now three labels, each pointing at a different fix:

| label | meaning | what it implicates |
|---|---|---|
| `unrelated` | the source does not discuss this subject anywhere | nothing, this is a correct answer |
| `unrepresentable` | no predicate axis exists for this statement | the axis vocabulary in `claims.py` |
| `uncovered` | the page discusses it, but no extracted claim speaks to it | extraction recall, which is bounded at 8 and ranked by a heuristic |

Telling them apart needs something the comparator did not previously have, which is sight
of the whole page rather than only the claims that survived extraction. That is what
`compare.source_index()` supplies. Every declining result also carries a machine-readable
`reason`, and the verifier fails a run where one does not.

**What the split revealed.** The scores did not move, 3 of 14 and 3 of 20, which is the
honest result: declining with a reason is not a right answer, so it still counts as a miss.
What changed is the diagnosis. On the sampled set, **all 17 declines are
`no_axis_for_statement`, and not one is genuinely unrelated.** The bottleneck is the axis
vocabulary, in one identifiable place, rather than the comparison logic. Across both
evaluation sets exactly one reference is truly unrelated to the page, and it is the one
about Kubernetes.

## Verification

The verifier imports nothing from the extraction or comparison modules, including their
tokenizer. A verifier that reuses the classifier's own logic cannot catch the classifier's
own mistakes. It runs 10 checks: provenance present, claim set bounded, every claim verbatim in the
fetched source, every classification that asserts a relationship citing its source
sentence, every classification that declines recording why, every label being one the
verifier recognises, the near-duplicate references actually separated, and the three
fixture expectations.

The grounding check is the one that earns its keep. It re-reads each claim against the
fetched source text, so a fabricated or paraphrased claim fails the run even when every
other stage reports success.

## How good is it, really

Passing the three supplied fixtures is weak evidence, because the comparator was built
against those three. So there are two independent sets, and the difference between them
is the finding.

**Stress set** (`fixtures/heldout.json`, 14 references). Written after the implementation
was finished and before it was run against any of them, by me, knowing how the comparator
works and deliberately choosing cases likely to break it. Each carries the label a careful
reader assigns and the label I predicted in advance.

**Sampled set** (`fixtures/sampled.json`, 20 references). Generated by
`sample_references.py` using a fixed mechanical rule: every third eligible sentence on the
page, taken verbatim as a reference the page cannot disagree with, plus a copy with "not"
inserted after the first auxiliary. No judgement about which sentences were chosen, so it
measures the task rather than my sense of the system's weak points.

| | correct | asserted | asserted right | declined |
|---|---|---|---|---|
| Stress set | 3 of 14 (21%) | 7 | 2 | 7 (1 correct) |
| Sampled set | 3 of 20 (15%) | 3 | 3 | 17 (0 correct) |

The flat accuracy is nearly the same and it hides the real difference. An assertion is a
label claiming a relationship: reinforcing, conflicting or distinct.

**On sentences picked to break it, it answers confidently and wrongly.** Nine opinions,
two right, including three false conflicts. A false conflict is the expensive error,
because it sends a reader to re-check a source that was correct.

**On sentences drawn without bias, it barely answers at all.** Three assertions out of
twenty, and all three correct. Seventeen times it declines, every one of them because the
statement sits on no axis it can express, including sentences lifted verbatim off the page
it just read.

So the honest characterization is that its coverage is narrow and its confidence is
miscalibrated at the edges, rather than that it is inaccurate. It has an opinion
only when a sentence lands on one of four predicate axes hand-listed in
`harness/claims.py`, which most prose does not. When it stays inside that envelope it is
reliable. When pushed outside it, it does not fall silent, it guesses.

Full tables in `docs/evaluation-results.md`. Reproduce with `python3 evaluate.py`.

**Two of the stress failures are a few lines each and are deliberately not fixed.**
Subject overlap divides by the shorter subject, so a claim whose subject is only "tracing"
scores a perfect match against nearly any sentence mentioning tracing, and one reference
missed the 0.34 overlap threshold by a hundredth. Patching them after seeing the results
would raise the number and destroy the only honest measurement here, because a set that
gets tuned against is a training set with a nicer name.
`tests/test_evaluation_baseline.py` locks both measurements so neither can move quietly.

## What this cost in supervision

The pilot question is how much useful work gets done without Kevin managing the
implementation, so the supervision actually required is part of the result rather than an
aside.

**The tests did not catch the defects. Reading did.** The first implementation passed its
entire suite while truncating every sentence containing inline code, ranking claims so the
most material one could fall out of the set, reading negation across whole sentences, and
running a verifier that imported the very module it claimed independence from. A green
suite written by the same process that wrote the code certifies very little.

**Upstream reality caught one that reading missed.** The page changed between September 4
and September 11, the key sentence dropped out of the bounded claim set, and the run
failed. That failure surfacing rather than passing silently is the single best piece of
evidence in this repo, and nobody designed the test that produced it.

**Two of the four deliverables here exist because a human asked one question.** The first
pass wrote the reuse scan from working knowledge without looking anything up, and graded
the comparator on the same three fixtures it was built against. Both were presented as
complete. `REUSE_SCAN.md`, the held-out set, the sampled set and this section were all
produced after Caleb asked whether the work had actually answered what was asked, rather
than merely satisfying the acceptance criteria as written. That question came from the
human, not from the system, and the system had already reported success.

That is the honest measure of autonomy on this pilot. The build ran with very little
supervision. The judgement about whether the build had answered the question did not.

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
  reports 90.04 on MNLI mismatched. The rule-based comparator it would replace scores 21% and 15% on the two sets.
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

**Known limitations.** Comparison is lexical and structural, not inference, and the two
evaluation sets put numbers on what that costs: narrow coverage, and confident errors on
exactly the cases that fall outside it. Extraction only sees the four predicate axes declared
in `harness/claims.py`. Claims are not decontextualized, so some carry unresolved references.
Sentence splitting is tuned for documentation pages rather than prose. Materiality ranking is
a heuristic, and the September 11 drift showed that a bounded set plus a heuristic ranking is
where this design is most fragile.

**What I would build next, in order.** The `unrelated` split described above is done, and it
was the first item. Next is a coverage number in the verifier: the run should report what
share of the page's material sentences it could not represent at all, because right now the
verifier checks whether its answers are correct and never counts what it declined to say,
which is exactly how this got past me. Then replace the comparator with an NLI cross-encoder
while keeping the deterministic verifier unchanged, and measure it against both sets, where
it has to beat 3 of 14 and 3 of 20. Add a decontextualization stage so claims stand alone. Schedule
the run so upstream drift is caught on a cadence rather than by accident, and diff claims
between revisions so the report says what changed rather than only that the hash changed.

## Layout

```
run.py                      one-command entry point
evaluate.py                 measures both reference sets, reports rather than passes
sample_references.py        generates the unbiased set by a fixed rule, no cherry-picking
harness/provenance.py       fetch, text extraction, source record, idempotent store
harness/claims.py           sentence to proposition, materiality ranking, bounded extraction
harness/compare.py          reference against claims, scope before polarity
harness/verify.py           independent checks, imports nothing from the pipeline
harness/report.py           JSON and Markdown output
fixtures/references.json    the three pilot references and their expectations
fixtures/heldout.json       14 stress references with truth and advance predictions
fixtures/sampled.json       20 references generated mechanically from the page
tests/                      37 tests, two saved copies of the source page
REUSE_SCAN.md               the current-state scan, with benchmarks and sources
docs/example-report.md      committed sample of the human-readable output
docs/evaluation-results.md  committed scorecards for both sets
out/                        run artifacts, gitignored
```
