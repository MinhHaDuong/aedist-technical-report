"""Tests for the measurements adapter: round-trip invariant and output equivalence.

The core contract: for any list[dict] in all_metrics format, converting to
RunRecords and back via the adapter must reproduce the original dicts exactly
(for the fields the reporting scripts consume).
"""

import json
from pathlib import Path

import pytest

from aedist.measurements_adapter import (
    load_metrics_from_measurements,
    metrics_to_records,
    records_to_metrics,
)
from aedist.schema import RunRecord

# ---------------------------------------------------------------------------
# Fixtures — reuse the same sample data as existing test modules
# ---------------------------------------------------------------------------

# Fixtures use internally consistent counts: coverage = round(tp/(tp+fn), 4),
# precision = round(tp/(tp+fp), 4), matching compute_metrics() output.
CENSUS_METRICS = [
    {
        "label": "sweep1_census/gpt-5.4-run1",
        "coverage": 0.4908,  # 80/163
        "precision": 1.0,  # 80/80
        "f1": 0.658,
        "n_reference": 163,
        "n_system": 80,
        "n_matched": 80,
        "n_exact": 70,
        "n_fuzzy": 10,
        "n_missed": 83,
        "n_hallucinated": 0,
        "fuel_accuracy": 0.642,
        "status_accuracy": 0.716,
        "province_accuracy": 0.818,
    },
    {
        "label": "sweep1_census/gpt-5.4-run2",
        "coverage": 0.5031,  # 82/163
        "precision": 0.9762,  # 82/84
        "f1": 0.66,
        "n_reference": 163,
        "n_system": 84,
        "n_matched": 82,
        "n_exact": 72,
        "n_fuzzy": 10,
        "n_missed": 81,
        "n_hallucinated": 2,
        "fuel_accuracy": 0.65,
        "status_accuracy": 0.72,
        "province_accuracy": 0.82,
    },
    {
        "label": "sweep1_census/padme-qwen3.5-122b-run1",
        "coverage": 0.3006,  # 49/163
        "precision": 0.8033,  # 49/61
        "f1": 0.436,
        "n_reference": 163,
        "n_system": 61,
        "n_matched": 49,
        "n_exact": 40,
        "n_fuzzy": 9,
        "n_missed": 114,
        "n_hallucinated": 12,
        "fuel_accuracy": 0.5,
        "status_accuracy": 0.6,
        "province_accuracy": 0.7,
    },
]

# Minimal metrics (only fields used by plot_census / tabulate_macros)
MINIMAL_METRICS = [
    {"label": "sweep1_census/gpt-5.4-run1", "f1": 0.70},
    {"label": "sweep1_census/gpt-5.4-run2", "f1": 0.68},
    {"label": "sweep1_census/gpt-5.4-run3", "f1": 0.72},
]

# Fields that reporting scripts actually consume
_CONSUMED_FIELDS = (
    "label",
    "f1",
    "coverage",
    "precision",
    "n_matched",
    "n_reference",
    "n_system",
    "n_missed",
    "n_hallucinated",
    "fuel_accuracy",
    "status_accuracy",
    "province_accuracy",
)


# ---------------------------------------------------------------------------
# Layer A: Round-trip invariant
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """metrics → RunRecords → adapter → metrics must be identity."""

    def test_full_metrics_roundtrip(self):
        records = metrics_to_records(CENSUS_METRICS)
        recovered = records_to_metrics(records)
        assert len(recovered) == len(CENSUS_METRICS)
        for orig, rec in zip(CENSUS_METRICS, recovered):
            for field in _CONSUMED_FIELDS:
                assert orig.get(field) == rec.get(field), (
                    f"Field {field!r} mismatch: {orig.get(field)} != {rec.get(field)} "
                    f"for {orig['label']}"
                )

    def test_minimal_metrics_roundtrip(self):
        """Round-trip works even with sparse dicts (only label + f1)."""
        records = metrics_to_records(MINIMAL_METRICS)
        recovered = records_to_metrics(records)
        for orig, rec in zip(MINIMAL_METRICS, recovered):
            assert orig["label"] == rec["label"]
            assert orig["f1"] == rec["f1"]

    def test_method_inference(self):
        """Method is inferred from prompt_version in label."""
        metrics = [
            {"label": "sweep1_census/model-run1", "f1": 0.5},
            {"label": "sweep2_multiturn/model-run1", "f1": 0.6},
            {"label": "sweep2_rag/model-run1", "f1": 0.7},
            {"label": "sweep2_web/model-run1", "f1": 0.4},
        ]
        records = metrics_to_records(metrics)
        assert records[0].method == "single"
        assert records[1].method == "multiturn"
        assert records[2].method == "rag"
        assert records[3].method == "web"

    def test_label_preserved(self):
        """Label reconstruction from prompt_version + result_file stem."""
        records = metrics_to_records(CENSUS_METRICS)
        recovered = records_to_metrics(records)
        for orig, rec in zip(CENSUS_METRICS, recovered):
            assert orig["label"] == rec["label"]

    def test_cost_roundtrip(self):
        """cost_usd and wall_seconds survive the round-trip."""
        metrics = [
            {
                "label": "sweep1_census/model-run1",
                "f1": 0.5,
                "n_matched": 10,
                "n_missed": 5,
                "n_hallucinated": 2,
                "cost_usd": 0.015,
                "wall_seconds": 24.5,
            }
        ]
        records = metrics_to_records(metrics)
        recovered = records_to_metrics(records)
        assert recovered[0]["cost_usd"] == 0.015
        assert recovered[0]["wall_seconds"] == 24.5


class TestRoundTripRealData:
    """Round-trip with real all_metrics.json data."""

    @pytest.fixture
    def real_metrics(self):
        path = Path("results/summary/all_metrics.json")
        if not path.exists():
            pytest.skip("Real metrics file not available")
        with open(path) as f:
            return json.load(f)

    def test_real_data_roundtrip(self, real_metrics):
        records = metrics_to_records(real_metrics)
        recovered = records_to_metrics(records)
        assert len(recovered) == len(real_metrics)
        for orig, rec in zip(real_metrics, recovered):
            for field in _CONSUMED_FIELDS:
                assert orig.get(field) == rec.get(field), (
                    f"Field {field!r}: {orig.get(field)} != {rec.get(field)} for {orig['label']}"
                )


# ---------------------------------------------------------------------------
# Layer B: Output equivalence — pure functions produce same output
# ---------------------------------------------------------------------------


class TestOutputEquivalence:
    """Pure reporting functions produce identical output from both paths."""

    def test_census_table_equivalence(self):
        from aedist.tabulate_census import generate_census_table

        direct = generate_census_table(CENSUS_METRICS)
        records = metrics_to_records(CENSUS_METRICS)
        via_adapter = generate_census_table(records_to_metrics(records))
        assert direct == via_adapter

    def test_macros_equivalence(self):
        from aedist.tabulate_macros import generate_macros, load_and_summarize

        summary_direct = load_and_summarize(CENSUS_METRICS)
        records = metrics_to_records(CENSUS_METRICS)
        summary_adapter = load_and_summarize(records_to_metrics(records))
        assert generate_macros(summary_direct) == generate_macros(summary_adapter)

    def test_census_bars_equivalence(self):
        from aedist.plot_census import build_census_rows

        direct = build_census_rows(CENSUS_METRICS)
        records = metrics_to_records(CENSUS_METRICS)
        via_adapter = build_census_rows(records_to_metrics(records))
        assert direct == via_adapter

    def test_pareto_equivalence(self):
        from aedist.plot_pareto import build_pareto_rows

        direct = build_pareto_rows(CENSUS_METRICS)
        records = metrics_to_records(CENSUS_METRICS)
        via_adapter = build_pareto_rows(records_to_metrics(records))
        assert direct == via_adapter

    def test_comparaison_equivalence(self):
        """Comparison table needs both census and RAG entries."""
        from aedist.tabulate_comparaison import generate_comparaison_table

        mixed = CENSUS_METRICS + [
            {
                "label": "sweep2_rag/gpt-5.4-run1",
                "coverage": 0.6012,  # 98/163
                "precision": 0.98,  # 98/100
                "f1": 0.72,
                "n_reference": 163,
                "n_system": 100,
                "n_matched": 98,
                "n_missed": 65,
                "n_hallucinated": 2,
            },
        ]
        direct, n1 = generate_comparaison_table(mixed)
        records = metrics_to_records(mixed)
        via_adapter, n2 = generate_comparaison_table(records_to_metrics(records))
        assert direct == via_adapter
        assert n1 == n2


# ---------------------------------------------------------------------------
# JSONL file round-trip
# ---------------------------------------------------------------------------


class TestJsonlRoundTrip:
    """Full file-based round-trip: metrics → jsonl file → load → metrics."""

    def test_file_roundtrip(self, tmp_path):
        jsonl_path = tmp_path / "measurements.jsonl"
        records = metrics_to_records(CENSUS_METRICS)
        RunRecord.save_jsonl(records, jsonl_path)

        recovered = load_metrics_from_measurements(jsonl_path)
        assert len(recovered) == len(CENSUS_METRICS)
        for orig, rec in zip(CENSUS_METRICS, recovered):
            assert orig["label"] == rec["label"]
            assert orig["f1"] == rec["f1"]
