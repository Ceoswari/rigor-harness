# rigor-harness

A small pipeline that ingests one public technical page, extracts a bounded set of
material claims with provenance, compares them against a reference set, classifies each
reference as reinforcing, conflicting, indeterminate, distinct or unrelated, and then
verifies its own run before reporting success.

Built for the Bounded Autonomous AI Systems Pilot (Kevin Ng, September 2026). Fixed
source: the OpenAI Agents SDK tracing page,
`https://openai.github.io/openai-agents-python/tracing/`.

**Start with the numbers.** The default rule-based comparator passes every acceptance
test but is right on only 10 of 28 references in the clean held-out set. An optional NLI
backend, after two fixes, passes the same acceptance tests and scores **25 of 28** on that
set, a set generated and committed before the fixes were written, with predictions made in
advance. Its first version scored 15 of 28, failed the pilot's own Reference A, and invented
conflicts between unrelated statements. How it got from one to the other, and what it still
gets wrong, is below.

## Running it

Python 3.9 or newer. No dependencies, no virtualenv, no API key, no install step.

```bash
python3 run.py                    # fetch the live page, classify, verify, report
python3 run.py --inject-failure   # prove a failed check is reported, not hidden
python3 evaluate.py               # measure against both reference sets
python3 sample_references.py      # regenerate the mechanically sampled set
python3 run.py --backend nli      # optional NLI backend, needs requirements-nli.txt
python3 -m unittest discover -s tests -v      # 68 tests, 10 skip without the NLI extras
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
own mistakes. It runs 11 checks: provenance present, claim set bounded, every claim verbatim in the
fetched source, every classification that asserts a relationship citing its source
sentence, every classification that declines recording why, every label being one the
verifier recognises, the run answering more often than it declines, the near-duplicate
references actually separated, and the three fixture expectations.

The grounding check is the one that earns its keep. It re-reads each claim against the
fetched source text, so a fabricated or paraphrased claim fails the run even when every
other stage reports success.

### Counting what the run did not say

Verification used to ask one question, whether the answers given were correct, and never
asked how many answers were withheld. That is how a system representing a fraction of the
page passed cleanly, and it is why neither the tests nor I caught the narrow coverage until
an unbiased evaluation set and Kevin Ng's review found it independently.

So every run now reports coverage, and the verifier derives it rather than reading it off
the pipeline. On the live page today: **extraction represents 7 of the page's 63 material
sentences, about 11%**. The verifier counts those 63 with its own sentence splitter and its
own notion of materiality, deliberately not shared with `harness/claims.py`, so the number
does not move when extraction's heuristics move. Planting a false coverage figure in the run
does not change what the verifier reports, and there is a test for that.

One coverage check can fail a run: `answers_more_often_than_it_declines`. The threshold is
not a quality bar, it is a floor against the specific failure mode above, being a run that
answers almost nothing and still reports success. Against the three pilot references the
system answers two and declines one, so it passes. Against the 20 sampled references it
would decline 17 and fail, which is the correct signal.

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

## An optional NLI backend

The rule-based comparator's declines all trace to one place: 17 of 17 on the sampled set
are statements that sit on none of its four hand-listed axes. That is a vocabulary limit,
and `REUSE_SCAN.md` named the obvious replacement, a natural language inference model with
no vocabulary to run out of. `harness/nli.py` implements it with
`cross-encoder/nli-deberta-v3-base`.

**It is a backend you switch on, not a replacement.** It needs torch and transformers, about
a gigabyte of wheels plus 700 MB of weights, which would end the repo's one real usability
property of cloning and running with nothing installed. So `--backend rules` stays the
default, `--backend nli` switches this on (see `requirements-nli.txt`), and both emit results
satisfying the same declared contract, `compare.RESULT_CONTRACT`. The deterministic verifier
runs unchanged against either.

**The confidence threshold was fixed at 0.50 before the backend was ever run**, and is pinned
by a test. It is not tuned against the evaluation sets, for the same reason two known bugs in
the rule-based comparator were left unfixed.

It was measured in two scopes. `claims` gives it the same 8 extracted claims the rule-based
comparator sees, which is the like-for-like comparison. `material` gives it all 62 material
sentences on the page, which tests whether extraction's 11% coverage was the real limit.

| backend | stress | sampled | precision on sampled | declines on sampled |
|---|---|---|---|---|
| `rules` | 3 of 14 | 3 of 20 | 100% (3 of 3) | 17 |
| `nli`, claims | 6 of 14 | 8 of 20 | 67% (8 of 12) | 8 |
| `nli`, material | 8 of 14 | 14 of 20 | 70% (14 of 20) | 0 |

Two things are true at once.

**It is much better at the task.** On the unbiased sample it goes from 3 correct to 14, and
widening scope from 8 claims to the whole page is worth almost as much as the model itself,
which confirms the coverage number was pointing at something real. It also fixes the
modality case the rule-based comparator got worst: "Tracing must be enabled manually before
it will record anything" is correctly a contradiction, where the rules called it support.

**It trades silence for confident error.** On the material scope every single error, 6 on
each set, is a false conflict, and it declines nothing at all. It calls the Kubernetes
reference, which has nothing to do with the page, a contradiction. The rule-based comparator
was right about that one. The rules backend is narrow and quiet when unsure; this one always
has an opinion.

**And it fails the pilot's own Reference A.** "OpenAI Agents SDK tracing is enabled by
default" comes back conflicting. The diagnosis has two parts:

1. The model scores the page's sentence "Tracing is enabled by default." against Reference A
   as neutral at 1.00, with zero entailment. In strict NLI terms that is correct, because the
   sentence never says whose tracing, so it cannot entail a claim that names the SDK. This is
   the missing decontextualization stage `REUSE_SCAN.md` named from Claimify, now showing up
   as a measured failure rather than a hypothetical one.
2. It scores an unrelated sentence, "The SDK omits that identifier from redacted spans for
   custom endpoints.", as a contradiction at 0.96. The backend keeps the single most confident
   verdict across premises, so that spurious contradiction wins.

**The verifier caught it without being changed.** `python3 run.py --backend nli` fails
verification on two checks: Reference A's expectation, and `beats_naive_overlap_baseline`,
because A and B now receive the same label. Collapsing two statements that differ by one word
into a single verdict is precisely the failure the pilot's fixtures exist to detect, and a
verifier written for a different backend detected it. That is the strongest evidence in this
repo that keeping the verifier independent of the pipeline was worth the duplication it costs.

As first built, the NLI backend was the better comparator and the worse system. The section
below is how that changed.

### Two fixes, judged on a set they were not designed against

The diagnosis above suggested two fixes. **Decontextualization:** give the model each
sentence with its page context ("In the OpenAI Agents SDK documentation on Tracing: Tracing
is enabled by default."), while evidence still cites the verbatim sentence so the grounding
check is unaffected. **A contradiction gate:** accept a contradiction only when the premise
shares enough of the reference's own topic, measured after removing the page's context words
and polarity words.

Both were designed by looking at failures on the stress set and the v1 sample, so neither set
can judge them. A new set had to exist first, and the order is recorded in git:

1. `369e8c7`: held-out **v2** generated by the same mechanical rule, at an offset disjoint from
   v1, plus 8 sentences from Python's zipfile docs whose truth is `unrelated`, which v1 lacked
   entirely. Predictions committed in the same commit, in `fixtures/heldout_v2_PREDICTIONS.md`.
   No backend had been scored on it.
2. `27e0496`: the unfixed system scored on v2, results committed on their own, row by row, in
   `fixtures/heldout_v2_UNFIXED_RESULTS.json`. The fixes existed only as uncommitted changes
   and were not loaded by that run.
3. Then the fixes, then the scoring below. With the fixes switched off, the evaluator
   reproduces step 2's numbers exactly, which is the check that nothing else moved.

**On v2, 28 references:**

| configuration | total | verbatim (12) | negated (8) | unrelated (8) | false conflicts on unrelated |
|---|---|---|---|---|---|
| `rules` | 10 | 1 | 1 | 8 | 0 |
| `nli`, whole page, unfixed | 15 | 5 | 8 | 2 | 6 |
| `nli`, whole page, **fixed** | **25** | 11 | 8 | 6 | **0** |
| `nli`, 8 claims, unfixed | 14 | 1 | 8 | 5 | 2 |
| `nli`, 8 claims, fixed | 10 | 1 | 1 | 8 | 0 |

**Against the predictions:**

| prediction | result | |
|---|---|---|
| `rules` scores 8 to 11 | 10 | held |
| unfixed NLI scores 16 to 20 | 15 | **missed**, one below |
| unfixed NLI invents at least 3 conflicts on unrelated | 6 | held |
| fixed NLI scores 21 to 25 | 25 | held, at the top |
| fixed NLI invents 0 or 1 conflicts on unrelated | 0 | held |
| the gate costs 0 to 2 true conflicts | 0 | held |
| Reference A comes back reinforcing | reinforcing, and all 11 checks pass | held |

**Two things were not predicted.**

The first is the more interesting. Reading only the 8 extracted claims, the fixes made the
score *drop*, from 14 to 10, and the negated sentences from 8 right to 1. That looks like a
regression and is not one. Seven of those eight earlier right answers were matched against
claims about something else, because the sentence that actually contradicts them is not among
the 8 claims. They were landing on the right label by accident. The gate blocked the accidental
matches and they now decline as `uncovered`, meaning the page discusses the subject and
extraction missed it, which is the true diagnosis. The old number was inflated by lucky
reasoning, and it took a fix to expose it.

The second is that two unrelated zipfile sentences now come back as *support*. The gate screens
contradictions only, so an entailment between unrelated statements passes straight through. The
third remaining miss is a verbatim sentence called a conflict because a different sentence on
the same topic appears to contradict it.

**What is and is not claimed.** The fixed backend's 25 of 28 on v2 is a clean measurement. Its
numbers on the stress set (10 of 14) and v1 sample (16 of 20) are higher than before, but the
fixes were designed from those sets' failures, so those two numbers are recorded and not
claimed as evidence.

`rules` remains the default backend now for one reason only, the gigabyte of dependencies. On
correctness the fixed NLI backend reading the whole page is better on every set, and it passes
the pilot's acceptance tests. `--nli-scope` defaults to the whole page, because the measurement
shows the 8-claim scope is the weak one.

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

**What I would build next.** Every item committed to after Kevin Ng's review is done, plus the
two NLI fixes. The remaining misses point at one more change: **extend the gate to entailment**,
so an unrelated statement cannot come back as support either. It is not built, because it was
designed after seeing v2, and scoring it on v2 would spend the only clean set this repo has.
It needs a v3, generated and committed with predictions before the change exists, which is the
same procedure v2 followed. Add a decontextualization stage so claims stand alone. Schedule
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
harness/nli.py              optional NLI backend, same result contract, off by default
requirements-nli.txt        the optional extras, pinned to the measured versions
fixtures/references.json    the three pilot references and their expectations
fixtures/heldout.json       14 stress references with truth and advance predictions
fixtures/sampled.json       20 references generated mechanically from the page (v1)
fixtures/heldout_v2.json    28 references, disjoint from v1, including 8 unrelated
fixtures/heldout_v2_PREDICTIONS.md       predictions committed before v2 was scored
fixtures/heldout_v2_UNFIXED_RESULTS.json v2 scores before the fixes, row by row
tests/                      68 tests, three saved source pages
REUSE_SCAN.md               the current-state scan, with benchmarks and sources
docs/example-report.md      committed sample of the human-readable output
docs/evaluation-results.md  committed scorecards for both sets
out/                        run artifacts, gitignored
```
