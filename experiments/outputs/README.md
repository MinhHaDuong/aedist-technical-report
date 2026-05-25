# Experiment outputs — active datasets

This directory now contains only active output datasets used by current
analysis and reporting workflows.

## Scope

- Keep: active experiment arms and batches that should be discoverable by
	measurements rebuild.
- Move out: retired sweeps and smoke/probe artifacts.

Archived outputs live in ../archive/outputs/ and are documented there.

## Current layout

- exp1_batch2/
- sota_exp3_arm1_batch1/
- sota_exp3_arm2_batch1/
- sota_exp3_arm3_batch1/
- sota_exp3_arm4_batch1/
- sota_exp3_DERIVATION_NOTICE.md

## Notes

- measurements rebuild reads record artifacts from experiments/outputs and
	experiments/derived. Archived outputs are intentionally outside that scope.
- Exp3 provenance and ledger policy is in sota_exp3_DERIVATION_NOTICE.md.
- Exp2 was arms 1 and 2 only, we are rewording
