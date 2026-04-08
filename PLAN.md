# Plan: Distinguish refusals from qualitative in ResultSummary.status

## Problem

`_evaluate_qualitative()` in evaluate.py labels every orphan JSON (no CSV
companion) as `status="qualitative"`. That conflates two different things:

- **qualitative**: the prompt intentionally asked for non-table output
  (frontier_scenarios, frontier_skill)
- **refusal**: the prompt asked for a table, but the model refused or
  produced no usable output

Currently 50 records in measurements.jsonl have `status="qualitative"`.
Nearly all are actually refusals or empty responses from table-asking
experiments (census, frontier, rag, multiturn, web).

## Design

### Status vocabulary (ResultSummary.status)

| Value | Meaning |
|-------|---------|
| `ok` | CSV extracted and scored (existing, unchanged) |
| `refusal` | **New.** Prompt asked for a table; model declined or produced no parseable table |
| `empty` | **New.** Response field was missing or blank |
| `qualitative` | Prompt intentionally asked for non-table output |

No dotfiles. The status lives in the existing `.record.json` status field.

### Classification logic

In `_evaluate_qualitative()` (evaluate.py:291), after reading the JSON:

1. Check the response text (same logic extract.py uses: `response` field or
   joined assistant turns).
2. If response is empty/missing → `status="empty"`.
3. If response has content → `status="refusal"` (the model answered but
   produced nothing extractable).
4. `status="qualitative"` is **never auto-assigned** from the orphan-JSON
   path. It is reserved for experiments where the prompt was qualitative
   by design. Those experiments (scenarios, skill_plans) live under
   `experiments/qualitative/` and are not processed by the Makefile's
   extract→evaluate pipeline.

### Changes

1. **`src/aedist/schema.py`** (~line 151)
   - Update the `status` field description to document the vocabulary:
     `"ok | refusal | empty | qualitative"`.

2. **`src/aedist/evaluate.py`** (`_evaluate_qualitative`, ~line 291)
   - Read the response text from the JSON (handle both `response` string
     and `turns` list, same as extract.py lines 304-311).
   - If response is empty → `ResultSummary(status="empty")`.
   - Otherwise → `ResultSummary(status="refusal")`.

3. **`tests/test_evaluate.py`** (or equivalent)
   - Add tests for `_evaluate_qualitative` covering:
     - JSON with prose response (no CSV) → status="refusal"
     - JSON with empty/missing response → status="empty"
     - JSON with multiturn format, no CSV → status="refusal"

4. **Rebuild measurements**
   - Delete existing `.record.json` files for the affected runs.
   - `make -C experiments rebuild-measurements` to regenerate with
     new statuses.
   - Verify: grep measurements.jsonl — expect 0 "qualitative" records
     (since no frontier_scenarios/frontier_skill JSONs exist on disk),
     multiple "refusal" and "empty" records.

### Files touched

- `src/aedist/schema.py` — doc string only
- `src/aedist/evaluate.py` — ~10 lines in `_evaluate_qualitative`
- `tests/test_evaluate.py` — new test cases
- `experiments/outputs/**/*.record.json` — regenerated (not hand-edited)
- `measurements.jsonl` — regenerated
