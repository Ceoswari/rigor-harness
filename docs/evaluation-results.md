# Evaluation results

Measured 2026-09-12 against the September 11 copy of the source page (SHA-256 `816bf4a4d7b207d3`).

Two sets, because one number on its own would mislead. The stress set was written by me, knowing the implementation, choosing cases likely to break it. The sampled set was generated from the page by a fixed mechanical rule with no judgement about which sentences were chosen. Reproduce both with `python3 evaluate.py`.


| backend | set | correct | asserted | asserted right | declined |
|---|---|---|---|---|---|
| `rules` | stress | 3 of 14 (21%) | 7 | 2 | 7 |
| `rules` | sampled | 3 of 20 (15%) | 3 | 3 | 17 |
| `nli-claims` | stress | 6 of 14 (43%) | 11 | 6 | 3 |
| `nli-claims` | sampled | 8 of 20 (40%) | 12 | 8 | 8 |
| `nli-material` | stress | 8 of 14 (57%) | 14 | 8 | 0 |
| `nli-material` | sampled | 14 of 20 (70%) | 20 | 14 | 0 |


## rules/stress: 3 of 14 correct (21%)

Advance predictions correct: 7 of 14.

Declined to decide, by recorded reason: `no_axis_for_statement` 4, `subject_absent_from_source` 1, `subject_present_but_not_extracted` 2.

It asserted a relationship 7 times and was right 2 of those, so precision 29% against recall 21%.

Errors: false conflict 3, missed conflict 2, missed support 6.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| h01 | Agents SDK tracing is turned on unless you disable it. | reinforcing | conflicting |  | **miss** (false conflict) |
| h02 | Tracing is unavailable for organizations that use OpenAI's APIs under a Zero Data Retention policy. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| h03 | Sensitive data capture cannot be disabled in the Agents SDK. | conflicting | uncovered | `subject_present_but_not_extracted` | **miss** (missed conflict) |
| h04 | The trace_include_sensitive_data setting is True by default. | reinforcing | distinct |  | **miss** (missed support) |
| h05 | You can disable tracing for one run using RunConfig. | reinforcing | conflicting |  | **miss** (false conflict) |
| h06 | Tracing must be enabled manually before it will record anything. | conflicting | reinforcing |  | **miss** (missed conflict) |
| h07 | Kubernetes pods are evicted when a node runs out of memory. | unrelated | unrelated | `subject_absent_from_source` | ok |
| h08 | Traces are composed of spans. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| h09 | Tracing is disabled by default for organizations with Zero Data Retention. | indeterminate | conflicting |  | **miss** (false conflict) |
| h10 | Custom trace processors can push traces to other destinations. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| h11 | Tracing is enabled by default in the Agents SDK, so no setup is required. | reinforcing | reinforcing |  | ok |
| h12 | The SDK records spans for guardrails. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| h13 | Audio span data is captured by default. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| h14 | Tracing cannot be disabled globally. | conflicting | conflicting |  | ok |

## rules/sampled: 3 of 20 correct (15%)

Declined to decide, by recorded reason: `no_axis_for_statement` 17.

It asserted a relationship 3 times and was right 3 of those, so precision 100% against recall 15%.

Errors: missed conflict 7, missed support 10.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| s01 | The Agents SDK includes built-in tracing, collecting a comprehensive record of events during an agent run: LLM generations, tool calls, handoffs, guardrails, and even custom events that occur. | reinforcing | reinforcing |  | ok |
| s02 | You can globally disable tracing in code with set_tracing_disabled(True) | reinforcing | reinforcing |  | ok |
| s02n | You can not globally disable tracing in code with set_tracing_disabled(True) | conflicting | conflicting |  | ok |
| s03 | Traces represent a single end-to-end operation of a "workflow". | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s04 | For example, AgentSpanData contains information about the Agent, GenerationSpanData contains information about the LLM generation, etc. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s05 | Each model turn is wrapped in a turn_span(). | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s05n | Each model turn is not wrapped in a turn_span(). | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| s06 | Function tool calls are each wrapped in function_span() | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s06n | Function tool calls are not each wrapped in function_span() | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| s07 | Audio outputs (text-to-speech) are wrapped in a speech_span() | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s07n | Audio outputs (text-to-speech) are not wrapped in a speech_span() | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| s08 | You can set this name if you use trace, or you can configure the name and other properties with the RunConfig. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s08n | You can not set this name if you use trace, or you can configure the name and other properties with the RunConfig. | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| s09 | In addition, you can set up custom trace processors to push traces to other destinations (as a replacement, or secondary destination). | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s09n | In addition, you can not set up custom trace processors to push traces to other destinations (as a replacement, or secondary destination). | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| s10 | Sometimes, you might want multiple calls to run() to be part of a single trace. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s11 | You can use the trace() function to create a trace. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s11n | You can not use the trace() function to create a trace. | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| s12 | You can also manually call trace.start() and trace.finish(). | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| s12n | You can not also manually call trace.start() and trace.finish(). | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |

## nli-claims/stress: 6 of 14 correct (43%)

Advance predictions correct: 4 of 14.

Declined to decide, by recorded reason: `subject_present_but_not_extracted` 3.

It asserted a relationship 11 times and was right 6 of those, so precision 55% against recall 43%.

Errors: false conflict 5, missed support 3.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| h01 | Agents SDK tracing is turned on unless you disable it. | reinforcing | reinforcing |  | ok |
| h02 | Tracing is unavailable for organizations that use OpenAI's APIs under a Zero Data Retention policy. | reinforcing | conflicting |  | **miss** (false conflict) |
| h03 | Sensitive data capture cannot be disabled in the Agents SDK. | conflicting | conflicting |  | ok |
| h04 | The trace_include_sensitive_data setting is True by default. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| h05 | You can disable tracing for one run using RunConfig. | reinforcing | reinforcing |  | ok |
| h06 | Tracing must be enabled manually before it will record anything. | conflicting | conflicting |  | ok |
| h07 | Kubernetes pods are evicted when a node runs out of memory. | unrelated | conflicting |  | **miss** (false conflict) |
| h08 | Traces are composed of spans. | reinforcing | reinforcing |  | ok |
| h09 | Tracing is disabled by default for organizations with Zero Data Retention. | indeterminate | conflicting |  | **miss** (false conflict) |
| h10 | Custom trace processors can push traces to other destinations. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| h11 | Tracing is enabled by default in the Agents SDK, so no setup is required. | reinforcing | conflicting |  | **miss** (false conflict) |
| h12 | The SDK records spans for guardrails. | reinforcing | conflicting |  | **miss** (false conflict) |
| h13 | Audio span data is captured by default. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| h14 | Tracing cannot be disabled globally. | conflicting | conflicting |  | ok |

## nli-claims/sampled: 8 of 20 correct (40%)

Declined to decide, by recorded reason: `subject_present_but_not_extracted` 8.

It asserted a relationship 12 times and was right 8 of those, so precision 67% against recall 40%.

Errors: false conflict 3, missed conflict 3, missed support 6.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| s01 | The Agents SDK includes built-in tracing, collecting a comprehensive record of events during an agent run: LLM generations, tool calls, handoffs, guardrails, and even custom events that occur. | reinforcing | reinforcing |  | ok |
| s02 | You can globally disable tracing in code with set_tracing_disabled(True) | reinforcing | reinforcing |  | ok |
| s02n | You can not globally disable tracing in code with set_tracing_disabled(True) | conflicting | conflicting |  | ok |
| s03 | Traces represent a single end-to-end operation of a "workflow". | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| s04 | For example, AgentSpanData contains information about the Agent, GenerationSpanData contains information about the LLM generation, etc. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| s05 | Each model turn is wrapped in a turn_span(). | reinforcing | conflicting |  | **miss** (false conflict) |
| s05n | Each model turn is not wrapped in a turn_span(). | conflicting | conflicting |  | ok |
| s06 | Function tool calls are each wrapped in function_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| s06n | Function tool calls are not each wrapped in function_span() | conflicting | reinforcing |  | **miss** (missed conflict) |
| s07 | Audio outputs (text-to-speech) are wrapped in a speech_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| s07n | Audio outputs (text-to-speech) are not wrapped in a speech_span() | conflicting | conflicting |  | ok |
| s08 | You can set this name if you use trace, or you can configure the name and other properties with the RunConfig. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| s08n | You can not set this name if you use trace, or you can configure the name and other properties with the RunConfig. | conflicting | conflicting |  | ok |
| s09 | In addition, you can set up custom trace processors to push traces to other destinations (as a replacement, or secondary destination). | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| s09n | In addition, you can not set up custom trace processors to push traces to other destinations (as a replacement, or secondary destination). | conflicting | uncovered | `subject_present_but_not_extracted` | **miss** (missed conflict) |
| s10 | Sometimes, you might want multiple calls to run() to be part of a single trace. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| s11 | You can use the trace() function to create a trace. | reinforcing | reinforcing |  | ok |
| s11n | You can not use the trace() function to create a trace. | conflicting | conflicting |  | ok |
| s12 | You can also manually call trace.start() and trace.finish(). | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| s12n | You can not also manually call trace.start() and trace.finish(). | conflicting | uncovered | `subject_present_but_not_extracted` | **miss** (missed conflict) |

## nli-material/stress: 8 of 14 correct (57%)

Advance predictions correct: 5 of 14.

It asserted a relationship 14 times and was right 8 of those, so precision 57% against recall 57%.

Errors: false conflict 6.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| h01 | Agents SDK tracing is turned on unless you disable it. | reinforcing | conflicting |  | **miss** (false conflict) |
| h02 | Tracing is unavailable for organizations that use OpenAI's APIs under a Zero Data Retention policy. | reinforcing | conflicting |  | **miss** (false conflict) |
| h03 | Sensitive data capture cannot be disabled in the Agents SDK. | conflicting | conflicting |  | ok |
| h04 | The trace_include_sensitive_data setting is True by default. | reinforcing | reinforcing |  | ok |
| h05 | You can disable tracing for one run using RunConfig. | reinforcing | reinforcing |  | ok |
| h06 | Tracing must be enabled manually before it will record anything. | conflicting | conflicting |  | ok |
| h07 | Kubernetes pods are evicted when a node runs out of memory. | unrelated | conflicting |  | **miss** (false conflict) |
| h08 | Traces are composed of spans. | reinforcing | reinforcing |  | ok |
| h09 | Tracing is disabled by default for organizations with Zero Data Retention. | indeterminate | conflicting |  | **miss** (false conflict) |
| h10 | Custom trace processors can push traces to other destinations. | reinforcing | reinforcing |  | ok |
| h11 | Tracing is enabled by default in the Agents SDK, so no setup is required. | reinforcing | conflicting |  | **miss** (false conflict) |
| h12 | The SDK records spans for guardrails. | reinforcing | conflicting |  | **miss** (false conflict) |
| h13 | Audio span data is captured by default. | reinforcing | reinforcing |  | ok |
| h14 | Tracing cannot be disabled globally. | conflicting | conflicting |  | ok |

## nli-material/sampled: 14 of 20 correct (70%)

It asserted a relationship 20 times and was right 14 of those, so precision 70% against recall 70%.

Errors: false conflict 6.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| s01 | The Agents SDK includes built-in tracing, collecting a comprehensive record of events during an agent run: LLM generations, tool calls, handoffs, guardrails, and even custom events that occur. | reinforcing | conflicting |  | **miss** (false conflict) |
| s02 | You can globally disable tracing in code with set_tracing_disabled(True) | reinforcing | reinforcing |  | ok |
| s02n | You can not globally disable tracing in code with set_tracing_disabled(True) | conflicting | conflicting |  | ok |
| s03 | Traces represent a single end-to-end operation of a "workflow". | reinforcing | conflicting |  | **miss** (false conflict) |
| s04 | For example, AgentSpanData contains information about the Agent, GenerationSpanData contains information about the LLM generation, etc. | reinforcing | reinforcing |  | ok |
| s05 | Each model turn is wrapped in a turn_span(). | reinforcing | conflicting |  | **miss** (false conflict) |
| s05n | Each model turn is not wrapped in a turn_span(). | conflicting | conflicting |  | ok |
| s06 | Function tool calls are each wrapped in function_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| s06n | Function tool calls are not each wrapped in function_span() | conflicting | conflicting |  | ok |
| s07 | Audio outputs (text-to-speech) are wrapped in a speech_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| s07n | Audio outputs (text-to-speech) are not wrapped in a speech_span() | conflicting | conflicting |  | ok |
| s08 | You can set this name if you use trace, or you can configure the name and other properties with the RunConfig. | reinforcing | reinforcing |  | ok |
| s08n | You can not set this name if you use trace, or you can configure the name and other properties with the RunConfig. | conflicting | conflicting |  | ok |
| s09 | In addition, you can set up custom trace processors to push traces to other destinations (as a replacement, or secondary destination). | reinforcing | reinforcing |  | ok |
| s09n | In addition, you can not set up custom trace processors to push traces to other destinations (as a replacement, or secondary destination). | conflicting | conflicting |  | ok |
| s10 | Sometimes, you might want multiple calls to run() to be part of a single trace. | reinforcing | reinforcing |  | ok |
| s11 | You can use the trace() function to create a trace. | reinforcing | conflicting |  | **miss** (false conflict) |
| s11n | You can not use the trace() function to create a trace. | conflicting | conflicting |  | ok |
| s12 | You can also manually call trace.start() and trace.finish(). | reinforcing | reinforcing |  | ok |
| s12n | You can not also manually call trace.start() and trace.finish(). | conflicting | conflicting |  | ok |

## Reading these

A false conflict is the expensive error: it sends a reader to re-check a source that was right. A missed reinforcement is the cheap one: the system fails to notice agreement and stays quiet. The sampled set is dominated by missed reinforcements, which says the system is more often silent than wrong.

The gap between the two sets is the useful part. On sentences chosen to break it, the comparator produces confident wrong answers including false conflicts. On sentences drawn without bias, it mostly declines to answer at all. Its real coverage is narrow: it has an opinion only when a sentence lands on one of the four predicate axes declared in harness/claims.py.
