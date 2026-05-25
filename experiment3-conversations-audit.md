# Experiment 3 Conversations Audit

## Scope

- Batch: sota experiment 3, batch 1
- Arms: 2 and 4
- Models: anthropic, mistral, openai, qwen
- Repetitions: 5
- Total audited conversations: 40

## Data audited

For each of the 40 conversations, this audit cross-checked:

- Ledger: `summary.json` row (`status`, `turns`, `class_trace`, `total_cost_usd`, `wall_s`)
- Raw prompt transcript: `*_turn_XX.user.txt`
- Raw model outputs: `*_turn_XX.raw.json`
- Turn classifier outputs: `*_turn_XX.classification.json`
- Runtime metadata when available: `*_turn_XX.record.json`

## Audit criteria

- Provider reliability: run reaches `status=pass` and produces turn artifacts.
- Flow integrity: report appears by/after the verify turn when verify is requested.
- Timing risk flags:
  - `WARN_EARLY_REPORT`: first `report` class appears on turn 1 while verify turn is 2+.
  - `WARN_NO_RECORD_JSON`: no `*.record.json` files but other raw artifacts exist.
- Hard failure:
  - `FAIL_PROVIDER`: `status=error` with no usable turn outputs.

## Executive summary

- Total rows audited: 40
- Pass: 35
- Error: 5
- Hard failures: 5 (`FAIL_PROVIDER`, all anthropic in arm 2)
- Flow break where verify turn had no report after it: 0
- Ledger/classifier turn-count mismatch on pass rows: 0
- Early-report timing risk rows: 18
- Missing record-json telemetry on pass rows: 4 (all arm4 run01)

Interpretation:

- Main reliability issue is concentrated provider failure in arm 2 anthropic (5/5 repeats).
- Among successful runs, the conversation flow is broadly intact (verify turn still followed by a report).
- Timing drift is common: many runs produce report-class output before verify turn. This is a protocol-risk signal, not always a failure, because some prompts still allow incremental reporting.

## By arm/model

- Arm 2: 15 pass, 5 error
- Arm 4: 20 pass, 0 error
- Anthropic overall: 5 pass, 5 error
- Mistral: 10 pass, 0 error
- OpenAI: 10 pass, 0 error
- Qwen: 10 pass, 0 error

## Cost and runtime signal (pass rows)

- Arm 2 cost (`total_cost_usd`): mean 0.3717, median 0.2445, max 0.7410
- Arm 4 cost (`total_cost_usd`): mean 1.3773, median 0.8619, max 5.3639

Arm 4 has substantially higher spend variance. No direct evidence of budget-triggered truncation in pass rows, but this is where cost pressure concentrates.

## Notable anomalies

1. Provider failure cluster (high severity)
   - All five anthropic runs in arm 2 fail before usable phase-B turn outputs.
   - Evidence pattern: `status=error`, `turns=0`, `class_trace=n/a`, only phase-A artifacts present.

2. Early report timing drift (medium severity)
   - 18 pass rows produce first report on turn 1 while verify is turn 2+.
   - Example evidence: arm4/run01/qwen turn 1 output already contains full inventory/table while prompt specifies a discovery turn.
   - Risk: reduced separation between discovery and verify-polish phases.

3. Telemetry incompleteness (low severity)
   - 4 pass rows (all arm4/run01) lack `*.record.json` even though `*.raw.json` and classifications exist.
   - This is an observability gap, not a conversational failure.

4. Edge-case turn sequence (low severity)
   - arm4/run04/anthropic has class trace `no_report,no_report,report,no_report`.
   - Verify marker string not detected in prompts; still contains a report before stop.

## Per-conversation verdict table (all 40)

Legend: `A2` = arm2, `A4` = arm4.

|Arm|Run|Model|Status|Turns|Verify turn|First report turn|Class trace|record.json count|Verdict flags|Comment|
|---|---:|---|---|---:|---:|---:|---|---:|---|---|
|A2|01|anthropic|error|0|-|-|n/a|0|FAIL_PROVIDER|phase-a failure|
|A2|01|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|01|openai|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A2|01|qwen|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A2|02|anthropic|error|0|-|-|n/a|0|FAIL_PROVIDER|phase-a failure|
|A2|02|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|02|openai|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|02|qwen|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A2|03|anthropic|error|0|-|-|n/a|0|FAIL_PROVIDER|phase-a failure|
|A2|03|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|03|openai|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|03|qwen|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|04|anthropic|error|0|-|-|n/a|0|FAIL_PROVIDER|phase-a failure|
|A2|04|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|04|openai|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|04|qwen|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A2|05|anthropic|error|0|-|-|n/a|0|FAIL_PROVIDER|phase-a failure|
|A2|05|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A2|05|openai|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A2|05|qwen|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A4|01|anthropic|pass|3|3|2|no_report,report,report|0|WARN_NO_RECORD_JSON|ok|
|A4|01|mistral|pass|4|4|3|no_report,no_report,report,report|0|WARN_NO_RECORD_JSON|ok|
|A4|01|openai|pass|3|3|2|no_report,report,report|0|WARN_NO_RECORD_JSON|ok|
|A4|01|qwen|pass|2|2|1|report,report|0|WARN_EARLY_REPORT,WARN_NO_RECORD_JSON|ok|
|A4|02|anthropic|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|02|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|02|openai|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A4|02|qwen|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A4|03|anthropic|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A4|03|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|03|openai|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|03|qwen|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A4|04|anthropic|pass|4|-|3|no_report,no_report,report,no_report|4|PASS|ok|
|A4|04|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|04|openai|pass|3|3|2|no_report,report,report|3|PASS|ok|
|A4|04|qwen|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|05|anthropic|pass|4|4|3|no_report,no_report,report,report|4|PASS|ok|
|A4|05|mistral|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|
|A4|05|openai|pass|4|4|3|no_report,no_report,report,report|4|PASS|ok|
|A4|05|qwen|pass|2|2|1|report,report|2|WARN_EARLY_REPORT|ok|

## Conclusion

Normality verdict for this 40-run scope:

- 31/40 are clean pass by this audit (`PASS` or only observability warning).
- 5/40 are hard provider failures (`FAIL_PROVIDER`, all anthropic arm2).
- 18/40 show early-report timing drift risk (often still pass and verify-complete).

Overall: execution is mostly functional but not fully "normal" due to concentrated provider failure and frequent early-report drift relative to the intended staged-turn protocol.