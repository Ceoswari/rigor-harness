# Evaluation results

Measured 2026-09-12 against the September 11 copy of the source page (SHA-256 `816bf4a4d7b207d3`).

Two sets, because one number on its own would mislead. The stress set was written by me, knowing the implementation, choosing cases likely to break it. The sampled set was generated from the page by a fixed mechanical rule with no judgement about which sentences were chosen. Reproduce both with `python3 evaluate.py`.


| backend | set | correct | asserted | asserted right | declined |
|---|---|---|---|---|---|
| `rules` | stress | 3 of 14 (21%) | 7 | 2 | 7 |
| `rules` | sampled | 3 of 20 (15%) | 3 | 3 | 17 |
| `rules` | v2 | 10 of 28 (36%) | 2 | 2 | 26 |
| `nli-claims` | stress | 6 of 14 (43%) | 11 | 6 | 3 |
| `nli-claims` | sampled | 8 of 20 (40%) | 12 | 8 | 8 |
| `nli-claims` | v2 | 14 of 28 (50%) | 18 | 9 | 10 |
| `nli-material` | stress | 8 of 14 (57%) | 14 | 8 | 0 |
| `nli-material` | sampled | 14 of 20 (70%) | 20 | 14 | 0 |
| `nli-material` | v2 | 15 of 28 (54%) | 26 | 13 | 2 |


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

## rules/v2: 10 of 28 correct (36%)

Declined to decide, by recorded reason: `no_axis_for_statement` 16, `subject_absent_from_source` 8, `subject_present_but_not_extracted` 2.

It asserted a relationship 2 times and was right 2 of those, so precision 100% against recall 36%.

Errors: missed conflict 7, missed support 11.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| v01 | Using the Traces dashboard, you can debug, visualize, and monitor your workflows during development and in production. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v01n | Using the Traces dashboard, you can not debug, visualize, and monitor your workflows during development and in production. | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| v02 | You can disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True | reinforcing | reinforcing |  | ok |
| v02n | You can not disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True | conflicting | conflicting |  | ok |
| v03 | Must have the format trace_<32_alphanumeric>. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v04 | The entire Runner.{run, run_sync, run_streamed}() is wrapped in a trace(). | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v04n | The entire Runner.{run, run_sync, run_streamed}() is not wrapped in a trace(). | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| v05 | Each time an agent runs, it is wrapped in agent_span() | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v05n | Each time an agent runs, it is not wrapped in agent_span() | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| v06 | Guardrails are wrapped in guardrail_span() | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v06n | Guardrails are not wrapped in guardrail_span() | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| v07 | The SDK may parent related audio spans under a speech_group_span() | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v07n | The SDK may not parent related audio spans under a speech_group_span() | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| v08 | If you want a more compact hierarchy, disable the automatic task and turn spans for a run. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v09 | The default BatchTraceProcessor exports traces in the background every few seconds, or sooner when the in-memory queue reaches its size trigger, and also performs a final flush when the process exits. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v10 | You can do this by wrapping the entire code in a trace(). | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v10n | You can not do this by wrapping the entire code in a trace(). | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| v11 | Recommended: use the trace as a context manager, i.e. with trace(...) as my_trace. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v12 | The current trace is tracked via a Python contextvar. | reinforcing | unrepresentable | `no_axis_for_statement` | **miss** (missed support) |
| v12n | The current trace is not tracked via a Python contextvar. | conflicting | unrepresentable | `no_axis_for_statement` | **miss** (missed conflict) |
| u01 | The ZIP file format is a common archive and compression standard. | unrelated | unrelated | `subject_absent_from_source` | ok |
| u02 | This requires the compression.zstd module. | unrelated | unrelated | `subject_absent_from_source` | ok |
| u03 | This attribute is a workaround for legacy implementations which produce archives with names in the current locale encoding or code page (mostly on Windows). | unrelated | unrelated | `subject_absent_from_source` | ok |
| u04 | Use io.TextIOWrapper for reading compressed text files in universal newlines mode. | unrelated | unrelated | `subject_absent_from_source` | ok |
| u05 | ZipFile.write(filename, arcname=None, compress_type=None, compresslevel=None)¶ | unrelated | unrelated | `subject_absent_from_source` | ok |
| u06 | Debugging information is written to sys.stdout. | unrelated | unrelated | `subject_absent_from_source` | ok |
| u07 | Positional and keyword arguments are passed through to io.TextIOWrapper (except buffer, which is implied by the context). | unrelated | unrelated | `subject_absent_from_source` | ok |
| u08 | Changed in version 3.6.2: The filename parameter accepts a path-like object. | unrelated | unrelated | `subject_absent_from_source` | ok |

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

## nli-claims/v2: 14 of 28 correct (50%)

Declined to decide, by recorded reason: `model_found_no_relation` 5, `subject_present_but_not_extracted` 5.

It asserted a relationship 18 times and was right 9 of those, so precision 50% against recall 50%.

Errors: false conflict 8, missed support 5, other 1.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| v01 | Using the Traces dashboard, you can debug, visualize, and monitor your workflows during development and in production. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v01n | Using the Traces dashboard, you can not debug, visualize, and monitor your workflows during development and in production. | conflicting | conflicting |  | ok |
| v02 | You can disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True | reinforcing | reinforcing |  | ok |
| v02n | You can not disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True | conflicting | conflicting |  | ok |
| v03 | Must have the format trace_<32_alphanumeric>. | reinforcing | conflicting |  | **miss** (false conflict) |
| v04 | The entire Runner.{run, run_sync, run_streamed}() is wrapped in a trace(). | reinforcing | conflicting |  | **miss** (false conflict) |
| v04n | The entire Runner.{run, run_sync, run_streamed}() is not wrapped in a trace(). | conflicting | conflicting |  | ok |
| v05 | Each time an agent runs, it is wrapped in agent_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| v05n | Each time an agent runs, it is not wrapped in agent_span() | conflicting | conflicting |  | ok |
| v06 | Guardrails are wrapped in guardrail_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| v06n | Guardrails are not wrapped in guardrail_span() | conflicting | conflicting |  | ok |
| v07 | The SDK may parent related audio spans under a speech_group_span() | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v07n | The SDK may not parent related audio spans under a speech_group_span() | conflicting | conflicting |  | ok |
| v08 | If you want a more compact hierarchy, disable the automatic task and turn spans for a run. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v09 | The default BatchTraceProcessor exports traces in the background every few seconds, or sooner when the in-memory queue reaches its size trigger, and also performs a final flush when the process exits. | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v10 | You can do this by wrapping the entire code in a trace(). | reinforcing | uncovered | `subject_present_but_not_extracted` | **miss** (missed support) |
| v10n | You can not do this by wrapping the entire code in a trace(). | conflicting | conflicting |  | ok |
| v11 | Recommended: use the trace as a context manager, i.e. with trace(...) as my_trace. | reinforcing | conflicting |  | **miss** (false conflict) |
| v12 | The current trace is tracked via a Python contextvar. | reinforcing | conflicting |  | **miss** (false conflict) |
| v12n | The current trace is not tracked via a Python contextvar. | conflicting | conflicting |  | ok |
| u01 | The ZIP file format is a common archive and compression standard. | unrelated | unrelated | `model_found_no_relation` | ok |
| u02 | This requires the compression.zstd module. | unrelated | conflicting |  | **miss** (false conflict) |
| u03 | This attribute is a workaround for legacy implementations which produce archives with names in the current locale encoding or code page (mostly on Windows). | unrelated | unrelated | `model_found_no_relation` | ok |
| u04 | Use io.TextIOWrapper for reading compressed text files in universal newlines mode. | unrelated | conflicting |  | **miss** (false conflict) |
| u05 | ZipFile.write(filename, arcname=None, compress_type=None, compresslevel=None)¶ | unrelated | reinforcing |  | **miss** (other) |
| u06 | Debugging information is written to sys.stdout. | unrelated | unrelated | `model_found_no_relation` | ok |
| u07 | Positional and keyword arguments are passed through to io.TextIOWrapper (except buffer, which is implied by the context). | unrelated | unrelated | `model_found_no_relation` | ok |
| u08 | Changed in version 3.6.2: The filename parameter accepts a path-like object. | unrelated | unrelated | `model_found_no_relation` | ok |

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

## nli-material/v2: 15 of 28 correct (54%)

Declined to decide, by recorded reason: `model_found_no_relation` 2.

It asserted a relationship 26 times and was right 13 of those, so precision 50% against recall 54%.

Errors: false conflict 13.

| id | reference | truth | actual | reason | |
|---|---|---|---|---|---|
| v01 | Using the Traces dashboard, you can debug, visualize, and monitor your workflows during development and in production. | reinforcing | conflicting |  | **miss** (false conflict) |
| v01n | Using the Traces dashboard, you can not debug, visualize, and monitor your workflows during development and in production. | conflicting | conflicting |  | ok |
| v02 | You can disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True | reinforcing | reinforcing |  | ok |
| v02n | You can not disable tracing for a single run by setting agents.run.RunConfig.tracing_disabled to True | conflicting | conflicting |  | ok |
| v03 | Must have the format trace_<32_alphanumeric>. | reinforcing | conflicting |  | **miss** (false conflict) |
| v04 | The entire Runner.{run, run_sync, run_streamed}() is wrapped in a trace(). | reinforcing | conflicting |  | **miss** (false conflict) |
| v04n | The entire Runner.{run, run_sync, run_streamed}() is not wrapped in a trace(). | conflicting | conflicting |  | ok |
| v05 | Each time an agent runs, it is wrapped in agent_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| v05n | Each time an agent runs, it is not wrapped in agent_span() | conflicting | conflicting |  | ok |
| v06 | Guardrails are wrapped in guardrail_span() | reinforcing | conflicting |  | **miss** (false conflict) |
| v06n | Guardrails are not wrapped in guardrail_span() | conflicting | conflicting |  | ok |
| v07 | The SDK may parent related audio spans under a speech_group_span() | reinforcing | reinforcing |  | ok |
| v07n | The SDK may not parent related audio spans under a speech_group_span() | conflicting | conflicting |  | ok |
| v08 | If you want a more compact hierarchy, disable the automatic task and turn spans for a run. | reinforcing | reinforcing |  | ok |
| v09 | The default BatchTraceProcessor exports traces in the background every few seconds, or sooner when the in-memory queue reaches its size trigger, and also performs a final flush when the process exits. | reinforcing | reinforcing |  | ok |
| v10 | You can do this by wrapping the entire code in a trace(). | reinforcing | reinforcing |  | ok |
| v10n | You can not do this by wrapping the entire code in a trace(). | conflicting | conflicting |  | ok |
| v11 | Recommended: use the trace as a context manager, i.e. with trace(...) as my_trace. | reinforcing | conflicting |  | **miss** (false conflict) |
| v12 | The current trace is tracked via a Python contextvar. | reinforcing | conflicting |  | **miss** (false conflict) |
| v12n | The current trace is not tracked via a Python contextvar. | conflicting | conflicting |  | ok |
| u01 | The ZIP file format is a common archive and compression standard. | unrelated | conflicting |  | **miss** (false conflict) |
| u02 | This requires the compression.zstd module. | unrelated | conflicting |  | **miss** (false conflict) |
| u03 | This attribute is a workaround for legacy implementations which produce archives with names in the current locale encoding or code page (mostly on Windows). | unrelated | unrelated | `model_found_no_relation` | ok |
| u04 | Use io.TextIOWrapper for reading compressed text files in universal newlines mode. | unrelated | conflicting |  | **miss** (false conflict) |
| u05 | ZipFile.write(filename, arcname=None, compress_type=None, compresslevel=None)¶ | unrelated | conflicting |  | **miss** (false conflict) |
| u06 | Debugging information is written to sys.stdout. | unrelated | conflicting |  | **miss** (false conflict) |
| u07 | Positional and keyword arguments are passed through to io.TextIOWrapper (except buffer, which is implied by the context). | unrelated | unrelated | `model_found_no_relation` | ok |
| u08 | Changed in version 3.6.2: The filename parameter accepts a path-like object. | unrelated | conflicting |  | **miss** (false conflict) |

## Reading these

A false conflict is the expensive error: it sends a reader to re-check a source that was right. A missed reinforcement is the cheap one: the system fails to notice agreement and stays quiet. The sampled set is dominated by missed reinforcements, which says the system is more often silent than wrong.

The gap between the two sets is the useful part. On sentences chosen to break it, the comparator produces confident wrong answers including false conflicts. On sentences drawn without bias, it mostly declines to answer at all. Its real coverage is narrow: it has an opinion only when a sentence lands on one of the four predicate axes declared in harness/claims.py.
