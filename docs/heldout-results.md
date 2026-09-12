# Held-out evaluation results

Measured 2026-09-12 against `fixture_tracing_page_2026-09-11.html` (SHA-256 `816bf4a4d7b207d3`).

The 14 references in `fixtures/heldout.json` were written after the comparator was
finished and before it was run against any of them. `truth` is the label a careful
reader assigns. `I predicted` was written down in advance, before the first run.

**Agreement with a careful reader: 3 of 14 (21%).**
**Advance predictions correct: 9 of 14 (64%).**

Error breakdown: false conflict 3, missed conflict 2, missed support 6.

| id | reference | truth | I predicted | actual | |
|---|---|---|---|---|---|
| h01 | Agents SDK tracing is turned on unless you disable it. | reinforcing | conflicting | conflicting | **miss** (false conflict) |
| h02 | Tracing is unavailable for organizations that use OpenAI's APIs under a Zero Data Retention policy. | reinforcing | unrelated | distinct | **miss** (missed support) |
| h03 | Sensitive data capture cannot be disabled in the Agents SDK. | conflicting | conflicting | unrelated | **miss** (missed conflict) |
| h04 | The trace_include_sensitive_data setting is True by default. | reinforcing | distinct | distinct | **miss** (missed support) |
| h05 | You can disable tracing for one run using RunConfig. | reinforcing | reinforcing | conflicting | **miss** (false conflict) |
| h06 | Tracing must be enabled manually before it will record anything. | conflicting | reinforcing | reinforcing | **miss** (missed conflict) |
| h07 | Kubernetes pods are evicted when a node runs out of memory. | unrelated | unrelated | unrelated | ok |
| h08 | Traces are composed of spans. | reinforcing | unrelated | unrelated | **miss** (missed support) |
| h09 | Tracing is disabled by default for organizations with Zero Data Retention. | indeterminate | conflicting | conflicting | **miss** (false conflict) |
| h10 | Custom trace processors can push traces to other destinations. | reinforcing | unrelated | unrelated | **miss** (missed support) |
| h11 | Tracing is enabled by default in the Agents SDK, so no setup is required. | reinforcing | reinforcing | reinforcing | ok |
| h12 | The SDK records spans for guardrails. | reinforcing | unrelated | distinct | **miss** (missed support) |
| h13 | Audio span data is captured by default. | reinforcing | indeterminate | unrelated | **miss** (missed support) |
| h14 | Tracing cannot be disabled globally. | conflicting | conflicting | conflicting | ok |

## Reading this table

A false conflict is the expensive error, because it sends a reader to re-check a
source that was correct. There are three. Missed support, six of them, is the
cheap error: the system fails to notice agreement and says nothing.

Reproduce with `python3 evaluate.py`.
