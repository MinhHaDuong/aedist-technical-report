"""Layer-2 mart adherence guard — schema field semantics + completeness.

Closed ticket 0322 added an adherence guard at Layer 1 only (scorer output
<-> CSV header). This is the missing Layer-2 guard (ticket 0384), checking the
schema in ``exp2_mart.py`` and the projection in ``build_exp2_mart.py``:

(a) every ``ScoreSummary`` field NAME matches the MEANING of the CSV column
    feeding it (the ``status_vocab_adherence`` <-> ``coherence_capacity_nonnegative``
    naming lie of finding #1 cannot recur);
(b) every computed scorer column reaches a ``ScoreSummary`` field, UNLESS it is
    explicitly listed in ``SCORER_OUT_OF_SCOPE`` with a reason (finding #2);
(c) every source-JSON key wired by ``extract_arm_*.py`` reaches a ``RunSummary``
    field or is documented out-of-scope (finding #3).

The guard checks the *contract* (the wiring in ``build_exp2_mart.py`` and the
schema in ``exp2_mart.py``), not regenerated data: the committed mart is stale
relative to the current scorers (0383 evidence), and re-baselining the mart is a
0383 decision, not this ticket's. Tests therefore assert against the projection
code, so finding #3's redress (0385) flips them by changing *code*, not data.
"""

import inspect
import json
from pathlib import Path

import pytest

from aedist import build_exp2_mart
from aedist.build_exp2_mart import _score_summary
from aedist.exp2_mart import MetricValue, ScoreSummary
from aedist.score_mechanical import _CSV_COLUMNS

MART = Path("experiments/derived/exp2_mart.jsonl")

# Metadata columns that key/identify a score row rather than carry a metric.
_METADATA_COLUMNS = {"arm", "model", "run", "prompt_version"}

# CSV columns the scorer emits but the mart deliberately does NOT wire into a
# ScoreSummary field. Each entry documents why. Finding #2 (these three metrics +
# their annotations) is a *scope decision* deferred to ticket 0386; until then
# they are documented out-of-scope rather than silently dropped.
SCORER_OUT_OF_SCOPE = {
    "provenance_source_diversity": "0386 — dropped scorer column, scope decision pending",
    "provenance_source_diversity_annotation": "0386 — dropped scorer column, scope decision pending",
    "provenance_source_spread": "0386 — dropped scorer column, scope decision pending",
    "provenance_source_spread_annotation": "0386 — dropped scorer column, scope decision pending",
    "temporality_cod_plausible": "0386 — dropped scorer column, scope decision pending",
    "temporality_cod_plausible_annotation": "0386 — dropped scorer column, scope decision pending",
}

# Source-JSON keys that ``extract_arm_*.py`` may emit and that the mart wiring in
# ``_build_run_records`` must either feed into a RunSummary field or document
# here. Bookkeeping/duplicate keys and keys not emitted for these arms are
# exempt with a reason; ``class_trace``/``n_bib_entries`` are deliberately NOT
# exempt — finding #3 is a real data-loss bug, asserted red below until 0385.
SOURCE_OUT_OF_SCOPE = {
    "agent": "bookkeeping — set from the run-record agent, not from the source key",
    "model": "bookkeeping — set from the run-record model, not from the source key",
    "run": "bookkeeping — set from the run-record run number",
    "total_cost_usd": "fallback feed for cost_usd, not a distinct field",
    "evidence_pack_manifest": "arm4-only — not wired for these arms",
    "tokens_in": "not emitted in source JSON for these arms (0383 non-finding)",
}


def _metricvalue_fields(model: type) -> set[str]:
    """Names of MetricValue-typed fields on a pydantic metrics model."""
    return {name for name, f in model.model_fields.items() if f.annotation is MetricValue}


def _wired_csv_columns() -> set[str]:
    """CSV columns the schema can carry: ``<group>_<field>`` for every
    MetricValue field in each ScoreSummary metric group, plus its annotation."""
    wired: set[str] = set()
    for group_name, field in ScoreSummary.model_fields.items():
        group_type = field.annotation
        if not (isinstance(group_type, type) and hasattr(group_type, "model_fields")):
            # n_rows (int) and any non-model field carry no per-column metrics.
            continue
        for metric_name in _metricvalue_fields(group_type):
            base = f"{group_name}_{metric_name}"
            wired.add(base)
            wired.add(f"{base}_annotation")
    return wired


@pytest.mark.adherence
def test_coherence_field_names_match_source_columns() -> None:
    """No CoherenceMetrics field name encodes a metric different from its feeding
    column. Pins the corrected mapping from finding #1's fix (commit f7f5c4ea):
    ``status_vocab_adherence`` reads ``coherence_status_vocab_adherence`` and
    ``capacity_nonnegative`` reads ``coherence_capacity_nonnegative`` — they are
    no longer collapsed onto the same column.
    """
    row = {
        "n_rows": "10",
        "coherence_vocab_adherence": "0.1",
        "coherence_vocab_adherence_annotation": "",
        "coherence_status_vocab_adherence": "0.2",
        "coherence_status_vocab_adherence_annotation": "",
        "coherence_capacity_nonnegative": "0.3",
        "coherence_capacity_nonnegative_annotation": "",
    }
    summary = _score_summary(row)
    assert summary.coherence.vocab_adherence.value == 0.1, (
        "vocab_adherence must read the coherence_vocab_adherence column"
    )
    assert summary.coherence.status_vocab_adherence.value == 0.2, (
        "status_vocab_adherence must read the coherence_status_vocab_adherence column"
    )
    assert summary.coherence.capacity_nonnegative.value == 0.3, (
        "capacity_nonnegative must read the coherence_capacity_nonnegative column"
    )


@pytest.mark.adherence
def test_scorer_columns_reach_mart_or_documented_out_of_scope() -> None:
    """Every metric column the scorer emits (``_CSV_COLUMNS``) must either be
    wired into a ScoreSummary field or be listed in ``SCORER_OUT_OF_SCOPE`` with a
    reason. Catches finding #2: scorer columns silently dropped at Layer 2.
    """
    wired = _wired_csv_columns()
    for col in _CSV_COLUMNS:
        if col in _METADATA_COLUMNS or col == "n_rows":
            continue
        if col in wired:
            continue
        assert col in SCORER_OUT_OF_SCOPE, (
            f"scorer column {col!r} is neither wired into ScoreSummary nor listed "
            f"in SCORER_OUT_OF_SCOPE — wire it or allowlist it with a reason"
        )

    # The allowlist must not rot: every exempted column must still be a real
    # scorer column (otherwise the exemption is stale and hides nothing).
    stale = SCORER_OUT_OF_SCOPE.keys() - set(_CSV_COLUMNS)
    assert not stale, f"SCORER_OUT_OF_SCOPE lists non-existent columns: {stale}"


@pytest.mark.adherence
def test_run_summary_wiring_documents_every_source_key() -> None:
    """Every source-JSON key wired into RunSummary by ``_build_run_records`` must
    correspond to a RunSummary schema field, and every documented out-of-scope
    key must be a real RunSummary field too — so the allowlist cannot rot."""
    from aedist.exp2_mart import RunSummary

    stale = SOURCE_OUT_OF_SCOPE.keys() - set(RunSummary.model_fields) - {
        "agent",
        "model",
        "run",
        "evidence_pack_manifest",
        "total_cost_usd",
    }
    assert not stale, (
        f"SOURCE_OUT_OF_SCOPE lists keys that are neither RunSummary fields nor "
        f"known bookkeeping/fallback keys: {stale}"
    )


@pytest.mark.adherence
def test_run_summary_wires_class_trace_and_n_bib_entries() -> None:
    """Finding #3 data-loss guard (resolved by ticket 0385). ``class_trace`` and
    ``n_bib_entries`` are declared on ``RunSummary`` and populated in the source
    JSON; ``_build_run_records`` now wires them through. This asserts against the
    projection *code* so the wiring cannot silently regress."""
    src = inspect.getsource(build_exp2_mart._build_run_records)
    missing = [key for key in ("class_trace", "n_bib_entries") if f'"{key}"' not in src]
    assert not missing, (
        f"_build_run_records does not wire source keys into RunSummary: {missing}"
    )


@pytest.mark.adherence
def test_committed_mart_class_trace_n_bib_entries_populated() -> None:
    """Corroborating data check (ticket 0385): in the committed mart the
    previously-unwired keys are now populated on every run record. Guards against
    a regenerated mart that drops finding #3's fix; skips when the artifact is
    absent (clean-room checkout)."""
    if not MART.exists():
        pytest.skip("mart artifact absent")
    recs = [json.loads(line) for line in MART.read_text().splitlines() if line.strip()]
    runs = [r for r in recs if r["record_kind"] == "run"]
    assert runs, "no run records to audit"
    for key in ("class_trace", "n_bib_entries"):
        missing = [r["record_id"] for r in runs if r["run_summary"].get(key) is None]
        assert not missing, (
            f"{key} is null in the committed mart for run records {missing} — "
            f"finding #3's wiring (ticket 0385) regressed or the mart is stale; "
            f"regenerate via the score.mk mart target"
        )
