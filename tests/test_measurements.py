"""Tests for aedist.measurements: records_to_metrics round-trip and output equivalence.

The core contract: RunRecord → records_to_metrics → dict must produce the
fields that reporting scripts consume, with correct derived values.
"""

from aedist.measurements import records_to_metrics
from aedist.schema import (
    Method,
    MethodParams,
    ResourceUse,
    ResultSummary,
    RunRecord,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CENSUS_METRICS = [
    {
        "label": "census/gpt-5.4-run1",
        "coverage": 0.4908,
        "precision": 1.0,
        "f1": 0.658,
        "n_reference": 163,
        "n_system": 80,
        "n_matched": 80,
        "n_missed": 83,
        "n_hallucinated": 0,
        "fuel_accuracy": 0.642,
        "status_accuracy": 0.716,
        "province_accuracy": 0.818,
    },
    {
        "label": "census/gpt-5.4-run2",
        "coverage": 0.5031,
        "precision": 0.9762,
        "f1": 0.66,
        "n_reference": 163,
        "n_system": 84,
        "n_matched": 82,
        "n_missed": 81,
        "n_hallucinated": 2,
        "fuel_accuracy": 0.65,
        "status_accuracy": 0.72,
        "province_accuracy": 0.82,
    },
]

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


def _make_record(label: str, tp: int, fp: int, fn: int, f1: float, **kwargs) -> RunRecord:
    """Build a RunRecord from counts."""
    prompt_version, stem = label.rsplit("/", 1) if "/" in label else ("", label)
    return RunRecord(
        method=Method.SINGLE,
        method_params=MethodParams(
            model=stem.replace("-run1", "").replace("-run2", ""),
            prompt_version=prompt_version or None,
        ),
        resource_use=ResourceUse(
            cost_usd=kwargs.get("cost_usd"),
            wall_s=kwargs.get("wall_seconds"),
        ),
        result_file=f"{label}.csv",
        result_summary=ResultSummary(
            tp=tp,
            fp=fp,
            fn=fn,
            f1=f1,
            n_plants=tp + fp,
            fuel_accuracy=kwargs.get("fuel_accuracy"),
            status_accuracy=kwargs.get("status_accuracy"),
            province_accuracy=kwargs.get("province_accuracy"),
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecordsToMetrics:
    def test_derived_fields(self):
        record = _make_record("census/gpt-5.4-run1", tp=80, fp=0, fn=83, f1=0.658)
        metrics = records_to_metrics([record])
        assert len(metrics) == 1
        m = metrics[0]
        assert m["label"] == "census/gpt-5.4-run1"
        assert m["n_matched"] == 80
        assert m["n_missed"] == 83
        assert m["n_hallucinated"] == 0
        assert m["n_reference"] == 163  # tp + fn
        assert m["n_system"] == 80  # tp + fp
        assert m["coverage"] == round(80 / 163, 4)
        assert m["precision"] == 1.0

    def test_cost_and_latency_included(self):
        record = _make_record(
            "census/model-run1",
            tp=10,
            fp=2,
            fn=5,
            f1=0.5,
            cost_usd=0.015,
            wall_seconds=24.5,
        )
        metrics = records_to_metrics([record])
        assert metrics[0]["cost_usd"] == 0.015
        assert metrics[0]["wall_seconds"] == 24.5

    def test_missing_cost_excluded(self):
        record = _make_record("census/model-run1", tp=10, fp=2, fn=5, f1=0.5)
        metrics = records_to_metrics([record])
        assert "cost_usd" not in metrics[0]
        assert "wall_seconds" not in metrics[0]

    def test_zero_plants(self):
        record = _make_record("census/empty-run1", tp=0, fp=0, fn=0, f1=0.0)
        metrics = records_to_metrics([record])
        assert metrics[0]["coverage"] == 0.0
        assert metrics[0]["precision"] == 0.0


class TestOutputEquivalence:
    """Pure reporting functions produce identical output from RunRecords."""

    def _records_from_metrics(self, metrics_list):
        """Build RunRecords matching the fixture data."""
        return [
            _make_record(
                m["label"],
                tp=m["n_matched"],
                fp=m["n_hallucinated"],
                fn=m["n_missed"],
                f1=m["f1"],
                fuel_accuracy=m.get("fuel_accuracy"),
                status_accuracy=m.get("status_accuracy"),
                province_accuracy=m.get("province_accuracy"),
            )
            for m in metrics_list
        ]

    def test_census_table_equivalence(self):
        from aedist.tabulate_census import generate_census_table

        direct = generate_census_table(CENSUS_METRICS)
        via_records = generate_census_table(
            records_to_metrics(self._records_from_metrics(CENSUS_METRICS))
        )
        assert direct == via_records

    def test_macros_equivalence(self):
        from aedist.tabulate_macros import generate_macros, load_and_summarize

        direct = generate_macros(load_and_summarize(CENSUS_METRICS))
        via_records = generate_macros(
            load_and_summarize(records_to_metrics(self._records_from_metrics(CENSUS_METRICS)))
        )
        assert direct == via_records


class TestInferMethod:
    """_infer_method maps subdirectory names to Method enum values."""

    def test_census(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("census") == "single"

    def test_multiturn(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("multiturn") == "multiturn"

    def test_rag(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("rag") == "rag"

    def test_rag_consistency_is_rag(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("rag_consistency") == "rag"

    def test_web(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("web") == "web"

    def test_decomposed(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("decomposed") == "decomposed"

    def test_sourced(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("sourced") == "sourced"

    def test_frontier(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("frontier") == "frontier"

    def test_frontier_scenarios(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("frontier_scenarios") == "frontier"

    def test_verification(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("verification") == "verification"

    def test_unknown_defaults_to_single(self):
        from aedist.evaluate import _infer_method

        assert _infer_method("some_new_sweep") == "single"


class TestNoExtractedInMeasurements:
    """Regression test: _extracted prompt_version must never appear in measurements.jsonl."""

    def test_no_extracted_in_measurements(self):
        """The _extracted prompt_version must never appear in measurements.jsonl.

        These CSVs are intermediate artifacts of self_consistency.py, not
        independent measurements. Their presence indicates the Makefile assembly
        is picking up derived/rag_consistency/_extracted/*.record.json files.
        """
        from aedist.measurements import load

        records = list(load())
        assert len(records) > 0, "measurements.jsonl is empty — test is vacuous"
        for r in records:
            assert r.method_params.prompt_version != "_extracted", (
                f"Found _extracted record in measurements.jsonl: "
                f"{r.method_params.model} {r.result_file}"
            )


class TestJsonlRoundTrip:
    def test_file_roundtrip(self, tmp_path):
        records = [
            _make_record("census/gpt-5.4-run1", tp=80, fp=0, fn=83, f1=0.658),
        ]
        jsonl_path = tmp_path / "measurements.jsonl"
        RunRecord.save_jsonl(records, jsonl_path)

        loaded = RunRecord.load_jsonl(jsonl_path)
        metrics = records_to_metrics(loaded)
        assert len(metrics) == 1
        assert metrics[0]["label"] == "census/gpt-5.4-run1"
        assert metrics[0]["f1"] == 0.658
