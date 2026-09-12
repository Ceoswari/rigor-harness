# Reuse before build: current-state scan

Run 2026-09-12, after the first implementation was already working. That order is
backwards and worth saying out loud: handoff section 5 asks for this scan *before*
substantial custom development, and the first pass was written from working knowledge
instead. This document is the scan actually done, and it changed two decisions.

Each entry is what was checked, what it would replace, the evidence, and the call.

---

## 1. HTML main text extraction

**Would replace:** `harness/provenance.py`, the hand-written `HTMLParser` subclass.

**Checked:** trafilatura 2.2.0 and readability-lxml. Trafilatura publishes a benchmark
over 750 documents (2,236 text and 2,250 boilerplate segments): trafilatura 0.910
accuracy and 0.909 F-score, readability-lxml 0.820 and 0.801, goose3 0.821 and 0.793,
inscriptis 0.563, html_text 0.554. Trafilatura's own extractor falls back to jusText
and readability-lxml. Both install from pip with no compiled extensions and no browser.

**Call: BUILD for this pilot, ADOPT trafilatura the moment the source set grows.**
The pilot reads one known mkdocs page, and a zero-dependency repo means a reviewer runs
one command with nothing to install, which is worth more here than a general extractor.

**But the evidence cuts against me and I am recording that.** The first version of the
hand-rolled parser emitted every text node on its own line and truncated every sentence
containing inline code, which is precisely the class of bug a benchmarked library does
not have. If this were reading a corpus rather than one page, building it was the wrong
call.

## 2. Natural language inference for the comparison step

**Would replace:** `harness/compare.py` and most of `harness/claims.py`, the custom
polarity-axis comparator.

**Checked:** `cross-encoder/nli-deberta-v3-base`. About 0.2B parameters. It outputs
exactly three labels, entailment, contradiction and neutral, which map onto the pilot's
reinforcing, conflicting and unrelated almost one to one. Reported accuracy 92.38 on
SNLI and 90.04 on MNLI mismatched. Runs locally through `transformers` plus `torch`, or
`sentence_transformers`.

**Call: ADAPT, and this is the next build.** The held-out measurement in this repo gives
the honest reason. The rule-based comparator agrees with a careful reader on 3 of 14
held-out references, 21%. A model reporting 90% on MNLI is the obvious replacement, and
the pilot now has a baseline number for it to beat rather than an opinion.

**Why not immediately:** it pulls in torch, which is a large dependency for a pilot
whose selling point is one command, and a model gives a probabilistic answer where
invariant B wants a re-derivable one. The shape that follows from the scan is the model
doing classification and the existing deterministic verifier keeping its job, checking
that every claim is verbatim in the source and every label cites its sentence. A
capable but unreliable classifier, graded by something that cannot rationalize, is the
combination actually worth testing.

## 3. Claim extraction and fact-verification pipelines

**Would replace:** the whole pipeline shape.

**Checked:** Loki (MIT licence, five stages: split into claims, assess
check-worthiness, generate queries, crawl evidence, verify) which requires an OpenAI API
key and a Serper search key to run. OpenFactCheck, which decomposes into
`claim_processor`, `retriever` and `verifier` configured by YAML. Claimify, which
extracts decontextualized claims in four stages: sentence splitting, selection,
disambiguation, decomposition, and is exposed over MCP.

**Call: BORROW the decomposition, do not ADOPT the tools.** Both verification pipelines
are built to retrieve evidence from the open web. The pilot compares against a supplied
reference set and is explicitly meant to run without external services, so their
retrieval stage is the bulk of what they offer and it is the part not needed.

**This scan found a real defect.** Claimify separates disambiguation and decomposition
as their own stages, and this implementation has neither. The consequence is visible in
its own output: the extracted claim "These may contain sensitive data, so you can
disable capturing that data via RunConfig.trace_include_sensitive_data" begins with an
unresolved "These". The claim is not decontextualized, so it cannot stand on its own
away from the paragraph it came from. That is a named, fixable weakness that the scan
surfaced and reading the code had not.

## 4. Provenance

**Would replace:** the source-record fields in `harness/provenance.py`.

**Checked:** the `prov` Python library, an implementation of the W3C PROV data model
with serialization to PROV-N, PROV-O (RDF), PROV-XML and PROV-JSON, plus graph export.

**Call: BORROW the vocabulary, do not ADOPT the library.** PROV models a graph of
entities, activities and agents. The pilot needs one source record carrying a URL, a
content hash, timestamps and a revision count. Adopting a provenance graph for that is
the kind of complexity invariant C rules out. Reassess if runs ever need to be chained,
where the derivation graph is the actual question.

## 5. Agent frameworks, the Agents SDK, and MCP

**Checked against the task rather than a benchmark.** Ingestion, extraction and
comparison here are deterministic and reproducible by design, and a runtime agent loop
would add nondeterminism to exactly the part that most needs to be repeatable. No agent
is adopted.

MCP becomes relevant in one specific case, which is this harness being called as a tool
by something else rather than run as a CLI. Claimify shipping as an MCP server is the
pattern to copy if that day comes.

## What the scan changed

1. The next build is now specified with a number attached: replace the comparator with
   an NLI cross-encoder and beat 3 of 14, keeping the deterministic verifier.
2. A concrete defect was named that code review missed: claims are not decontextualized,
   so some carry unresolved references like "These".

## Sources

- [Trafilatura evaluation](https://trafilatura.readthedocs.io/en/stable/evaluation.html)
- [cross-encoder/nli-deberta-v3-base](https://huggingface.co/cross-encoder/nli-deberta-v3-base)
- [Loki / OpenFactVerification](https://github.com/Libr-AI/OpenFactVerification)
- [OpenFactCheck](https://arxiv.org/html/2408.11832v1)
- [Claimify (ClaimsMCP)](https://github.com/AdamGustavsson/ClaimsMCP)
- [prov on PyPI](https://pypi.org/project/prov/)
- [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)
