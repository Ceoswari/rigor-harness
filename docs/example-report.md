# Rigor harness run

**Status:** VERIFIED

## Source

- URL: https://openai.github.io/openai-agents-python/tracing/
- Fetched: 2026-09-11T22:15:28Z (HTTP 200)
- Content SHA-256: `816bf4a4d7b207d3`
- Revision count: 1

## Extracted claims (8)

- **clm_01** (enablement, polarity -1) [per_run]: You can disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True
- **clm_02** (enablement, polarity +1) [by_default]: Tracing is enabled by default.
- **clm_03** (enablement, polarity -1): These may contain sensitive data, so you can disable capturing that data via RunConfig.trace_include_sensitive_data.
- **clm_04** (inclusion, polarity -1): The SDK omits that identifier from redacted spans for custom endpoints.
- **clm_05** (enablement, polarity +1): When using non-OpenAI models, you can provide an OpenAI API key to the tracing exporter to enable free tracing in the OpenAI Traces dashboard without disabling tracing.
- **clm_06** (enablement, polarity -1) [globally]: You can globally disable tracing by setting the env var OPENAI_AGENTS_DISABLE_TRACING=1
- **clm_07** (enablement, polarity -1) [globally]: You can globally disable tracing in code with set_tracing_disabled(True)
- **clm_08** (inclusion, polarity +1): The Agents SDK includes built-in tracing, collecting a comprehensive record of events during an agent run: LLM generations, tool calls, handoffs, guardrails, and even custom events that occur.

## Comparisons

### ref_b: CONFLICTING

> OpenAI Agents SDK tracing is disabled by default.

Same subject and axis, opposite polarity.

Evidence (clm_02): Tracing is enabled by default.

### ref_a: REINFORCING

> OpenAI Agents SDK tracing is enabled by default.

Same subject and axis, same polarity.

Evidence (clm_02): Tracing is enabled by default.

### ref_c: UNRELATED

> The billing subsystem retries failed invoice exports every six hours.

No comparable proposition and no material subject overlap.

## Verification

All 8 verification checks passed.

- [PASS] **provenance_present** Source record carries url, content hash and first-seen timestamp.
- [PASS] **claims_bounded** Extracted 8 claims; a bounded set is 1-12.
- [PASS] **claims_grounded_in_source** Every extracted claim sentence appears verbatim in the fetched source text.
- [PASS] **classifications_cite_evidence** Every non-unrelated classification names the source sentence behind it.
- [PASS] **beats_naive_overlap_baseline** Near-duplicate references separated by classification (ref_a/ref_b overlap 0.83 -> reinforcing vs conflicting). A surface-similarity comparator scores these pairs as the same statement and cannot split them.
- [PASS] **expectation_ref_a** Expected 'reinforcing' for ref_a, got 'reinforcing'.
- [PASS] **expectation_ref_b** Expected 'conflicting' for ref_b, got 'conflicting'.
- [PASS] **expectation_ref_c** Expected 'unrelated' for ref_c, got 'unrelated'.

## Material limitations

- Comparison is lexical-semantic (subject overlap plus a polarity axis), not full natural-language inference. It separates opposed statements about the same property; it does not resolve paraphrase with no shared vocabulary.
- Claim extraction is bounded by the predicate axes declared in harness/claims.py. A claim on an axis not listed there is not extracted.
- Sentence splitting is heuristic and tuned for documentation pages rather than prose.
- The run reflects the source as fetched. A later edit to the page changes the content hash and produces a new revision rather than silently altering this run.
