"""Tests for aedist.self_consistency: vote logic, normalization, CSV, grouping, records."""

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from aedist.metrics import BenchmarkMetrics
from aedist.schema import (
    FuelType,
    Method,
    MethodParams,
    Plant,
    PlantStatus,
    ResultSummary,
    RunRecord,
)
from aedist.self_consistency import (
    _build_name_maps,
    _canonical_name,
    _extract_to_csv,
    _group_runs,
    _metrics_to_result_summary,
    _normalize_name,
    _print_comparison_table,
    _results_to_records,
    evaluate_single_runs,
    majority_vote,
    plants_to_csv_text,
    run_analysis,
    union_vote,
    write_measurements,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plant(name: str, fuel=FuelType.COAL, status=PlantStatus.OPERATIONAL,
           cod=None, province=None, capacity_mwe=None) -> Plant:
    return Plant(
        name=name,
        fuel=fuel,
        status=status,
        cod=cod,
        province=province,
        capacity_mwe=capacity_mwe,
    )


def _make_metrics(**overrides) -> BenchmarkMetrics:
    defaults = dict(
        coverage=0.8,
        precision=0.9,
        f1=0.8471,
        n_reference=100,
        n_system=90,
        n_matched=80,
        n_exact=60,
        n_fuzzy=20,
        n_missed=20,
        n_hallucinated=10,
        fuel_accuracy=0.75,
        status_accuracy=0.82,
        province_accuracy=0.91,
        capacity_match_rate=0.85,
        errors={"hallucinated_plant": 10, "missed_plant": 20},
        justification_rate=0.5,
    )
    defaults.update(overrides)
    return BenchmarkMetrics(**defaults)


def _make_run_record(model="test-model", prompt_version="rag", **overrides) -> RunRecord:
    return RunRecord(
        method=Method.RAG,
        method_params=MethodParams(model=model, prompt_version=prompt_version),
        result_summary=ResultSummary(
            status="ok",
            n_plants=overrides.get("n_plants", 80),
            tp=overrides.get("tp", 70),
            fp=overrides.get("fp", 10),
            fn=overrides.get("fn", 30),
            f1=overrides.get("f1", 0.7778),
        ),
        result_file=overrides.get("result_file"),
    )


# ---------------------------------------------------------------------------
# _normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_basic_lowering(self):
        assert _normalize_name("Mong Duong") == "mong duong"

    def test_already_lowercase(self):
        assert _normalize_name("vinh tan") == "vinh tan"

    def test_mixed_case(self):
        assert _normalize_name("VINH TAN") == "vinh tan"

    def test_leading_trailing_whitespace(self):
        assert _normalize_name("  Mong Duong  ") == "mong duong"

    def test_collapse_multiple_spaces(self):
        assert _normalize_name("Mong   Duong   1") == "mong duong 1"

    def test_tabs_collapsed(self):
        assert _normalize_name("Mong\tDuong") == "mong duong"

    def test_unicode_nfc_normalization(self):
        # NFC normalization: decomposed e-acute -> composed e-acute
        name_nfd = "caf\u0065\u0301"  # e + combining acute
        result = _normalize_name(name_nfd)
        assert result == "caf\u00e9"

    def test_empty_string(self):
        assert _normalize_name("") == ""

    def test_single_word(self):
        assert _normalize_name("Duyen") == "duyen"

    def test_preserves_digits(self):
        assert _normalize_name("Plant 2A") == "plant 2a"


# ---------------------------------------------------------------------------
# _canonical_name
# ---------------------------------------------------------------------------


class TestCanonicalName:
    def test_delegates_to_normalize(self):
        p = _plant("  Mong  Duong  ")
        assert _canonical_name(p) == "mong duong"


# ---------------------------------------------------------------------------
# _build_name_maps
# ---------------------------------------------------------------------------


class TestBuildNameMaps:
    def test_single_run(self):
        plants = [_plant("Mong Duong"), _plant("Vinh Tan")]
        result = _build_name_maps([plants])
        assert len(result) == 1
        assert set(result[0].keys()) == {"mong duong", "vinh tan"}

    def test_duplicate_name_keeps_first(self):
        p1 = _plant("Mong Duong", capacity_mwe=100.0)
        p2 = _plant("Mong Duong", capacity_mwe=200.0)
        result = _build_name_maps([[p1, p2]])
        assert result[0]["mong duong"].capacity_mwe == 100.0

    def test_multiple_runs(self):
        run1 = [_plant("A"), _plant("B")]
        run2 = [_plant("B"), _plant("C")]
        result = _build_name_maps([run1, run2])
        assert len(result) == 2
        assert "a" in result[0] and "b" in result[0]
        assert "b" in result[1] and "c" in result[1]

    def test_empty_run(self):
        result = _build_name_maps([[]])
        assert result == [{}]


# ---------------------------------------------------------------------------
# majority_vote
# ---------------------------------------------------------------------------


class TestMajorityVote:
    def test_plant_in_two_of_three_included(self):
        run1 = [_plant("Alpha"), _plant("Beta")]
        run2 = [_plant("Alpha"), _plant("Gamma")]
        run3 = [_plant("Alpha"), _plant("Beta")]
        result = majority_vote([run1, run2, run3])
        names = {p.name for p in result}
        assert "Alpha" in names
        assert "Beta" in names

    def test_plant_in_one_of_three_excluded(self):
        run1 = [_plant("Alpha"), _plant("Beta")]
        run2 = [_plant("Alpha"), _plant("Gamma")]
        run3 = [_plant("Alpha"), _plant("Beta")]
        result = majority_vote([run1, run2, run3])
        names = {p.name for p in result}
        assert "Gamma" not in names

    def test_plant_in_all_three_included(self):
        run1 = [_plant("Alpha")]
        run2 = [_plant("Alpha")]
        run3 = [_plant("Alpha")]
        result = majority_vote([run1, run2, run3])
        assert len(result) == 1
        assert result[0].name == "Alpha"

    def test_empty_runs(self):
        result = majority_vote([[], [], []])
        assert result == []

    def test_all_empty_input(self):
        result = majority_vote([])
        assert result == []

    def test_two_runs_requires_both(self):
        """With 2 runs, majority = 2 (both), so a plant in only 1 is excluded."""
        run1 = [_plant("Alpha"), _plant("Beta")]
        run2 = [_plant("Alpha")]
        result = majority_vote([run1, run2])
        names = {p.name for p in result}
        assert "Alpha" in names
        assert "Beta" not in names

    def test_attributes_from_longest_run(self):
        """Plant attributes come from the run with the most plants."""
        run1 = [_plant("Alpha", capacity_mwe=100.0)]  # 1 plant
        run2 = [_plant("Alpha", capacity_mwe=200.0), _plant("Beta", capacity_mwe=50.0)]  # 2 plants
        run3 = [_plant("Alpha", capacity_mwe=300.0), _plant("Beta", capacity_mwe=60.0),
                _plant("Gamma", capacity_mwe=70.0)]  # 3 plants
        result = majority_vote([run1, run2, run3])
        alpha = [p for p in result if _normalize_name(p.name) == "alpha"][0]
        # Should take from run3 (longest)
        assert alpha.capacity_mwe == 300.0

    def test_case_insensitive_matching(self):
        run1 = [_plant("mong duong")]
        run2 = [_plant("Mong Duong")]
        run3 = [_plant("MONG DUONG")]
        result = majority_vote([run1, run2, run3])
        assert len(result) == 1

    def test_result_sorted_by_key(self):
        run1 = [_plant("Zebra"), _plant("Alpha")]
        run2 = [_plant("Zebra"), _plant("Alpha")]
        run3 = [_plant("Zebra"), _plant("Alpha")]
        result = majority_vote([run1, run2, run3])
        names = [_normalize_name(p.name) for p in result]
        assert names == sorted(names)

    def test_four_runs_requires_three(self):
        """With 4 runs, majority threshold = 4//2+1 = 3."""
        run1 = [_plant("Alpha"), _plant("Beta")]
        run2 = [_plant("Alpha"), _plant("Beta")]
        run3 = [_plant("Alpha")]
        run4 = [_plant("Alpha")]
        result = majority_vote([run1, run2, run3, run4])
        names = {_normalize_name(p.name) for p in result}
        # Alpha appears in 4/4 → included
        assert "alpha" in names
        # Beta appears in 2/4, below threshold of 3 → excluded
        assert "beta" not in names


# ---------------------------------------------------------------------------
# union_vote
# ---------------------------------------------------------------------------


class TestUnionVote:
    def test_all_plants_included(self):
        run1 = [_plant("Alpha")]
        run2 = [_plant("Beta")]
        run3 = [_plant("Gamma")]
        result = union_vote([run1, run2, run3])
        names = {_normalize_name(p.name) for p in result}
        assert names == {"alpha", "beta", "gamma"}

    def test_dedup_by_name(self):
        run1 = [_plant("Alpha")]
        run2 = [_plant("Alpha")]
        result = union_vote([run1, run2])
        assert len(result) == 1

    def test_empty_runs(self):
        result = union_vote([[], [], []])
        assert result == []

    def test_empty_input(self):
        result = union_vote([])
        assert result == []

    def test_attributes_from_longest_run(self):
        run1 = [_plant("Alpha", capacity_mwe=100.0)]
        run2 = [_plant("Alpha", capacity_mwe=200.0), _plant("Beta")]
        result = union_vote([run1, run2])
        alpha = [p for p in result if _normalize_name(p.name) == "alpha"][0]
        assert alpha.capacity_mwe == 200.0

    def test_union_superset_of_majority(self):
        run1 = [_plant("Alpha"), _plant("Beta")]
        run2 = [_plant("Alpha"), _plant("Gamma")]
        run3 = [_plant("Alpha"), _plant("Beta")]
        majority = set(_normalize_name(p.name) for p in majority_vote([run1, run2, run3]))
        union = set(_normalize_name(p.name) for p in union_vote([run1, run2, run3]))
        assert majority.issubset(union)


# ---------------------------------------------------------------------------
# plants_to_csv_text
# ---------------------------------------------------------------------------


class TestPlantsToCsvText:
    def test_header_row(self):
        text = plants_to_csv_text([])
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        assert header == ["name", "fuel", "status", "cod", "province", "capacity_mwe"]

    def test_single_plant_all_fields(self):
        p = _plant("Vinh Tan", fuel=FuelType.COAL, status=PlantStatus.OPERATIONAL,
                    cod="2018", province="Binh Thuan", capacity_mwe=600.0)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)  # skip header
        row = next(reader)
        assert row[0] == "Vinh Tan"
        assert row[1] == "coal"
        assert row[2] == "operational"
        assert row[3] == "2018"
        assert row[4] == "Binh Thuan"
        assert row[5] == "600.0"

    def test_unknown_fuel_renders_empty(self):
        p = _plant("X", fuel=FuelType.UNKNOWN)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[1] == ""

    def test_unknown_status_renders_empty(self):
        p = _plant("X", status=PlantStatus.UNKNOWN)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[2] == ""

    def test_none_fields_render_empty(self):
        p = _plant("X", cod=None, province=None, capacity_mwe=None)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[3] == ""  # cod
        assert row[4] == ""  # province
        assert row[5] == ""  # capacity_mwe

    def test_multiple_plants(self):
        plants = [_plant("A"), _plant("B"), _plant("C")]
        text = plants_to_csv_text(plants)
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 4  # header + 3 plants

    def test_gas_fuel_renders_correctly(self):
        p = _plant("Y", fuel=FuelType.GAS)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[1] == "gas"

    def test_imported_lng_fuel(self):
        p = _plant("Z", fuel=FuelType.IMPORTED_LNG)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[1] == "imported lng"

    def test_retired_status(self):
        p = _plant("W", status=PlantStatus.RETIRED)
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[2] == "retired"

    def test_name_with_comma(self):
        """CSV writer properly quotes names containing commas."""
        p = _plant("Mong Duong 1, Unit 2")
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[0] == "Mong Duong 1, Unit 2"

    def test_name_with_quotes(self):
        """CSV writer properly escapes names containing double quotes."""
        p = _plant('Vinh Tan "Phase 2"')
        text = plants_to_csv_text([p])
        reader = csv.reader(io.StringIO(text))
        next(reader)
        row = next(reader)
        assert row[0] == 'Vinh Tan "Phase 2"'


# ---------------------------------------------------------------------------
# _group_runs
# ---------------------------------------------------------------------------


class TestGroupRuns:
    def test_groups_by_model_name(self, tmp_path):
        for name in ["gpt-4o-run1.json", "gpt-4o-run2.json", "gpt-4o-run3.json"]:
            (tmp_path / name).write_text("{}")
        groups = _group_runs(tmp_path)
        assert "gpt-4o" in groups
        assert len(groups["gpt-4o"]) == 3

    def test_multiple_models(self, tmp_path):
        for name in ["gpt-4o-run1.json", "gpt-4o-run2.json",
                      "claude-sonnet-run1.json", "claude-sonnet-run2.json"]:
            (tmp_path / name).write_text("{}")
        groups = _group_runs(tmp_path)
        assert len(groups) == 2
        assert "gpt-4o" in groups
        assert "claude-sonnet" in groups

    def test_sorted_by_run_number(self, tmp_path):
        for name in ["model-run3.json", "model-run1.json", "model-run2.json"]:
            (tmp_path / name).write_text("{}")
        groups = _group_runs(tmp_path)
        paths = groups["model"]
        assert [p.name for p in paths] == ["model-run1.json", "model-run2.json", "model-run3.json"]

    def test_ignores_non_matching_files(self, tmp_path):
        (tmp_path / "model-run1.json").write_text("{}")
        (tmp_path / "summary.json").write_text("{}")
        (tmp_path / "notes.txt").write_text("")
        groups = _group_runs(tmp_path)
        assert len(groups) == 1
        assert "model" in groups

    def test_empty_directory(self, tmp_path):
        groups = _group_runs(tmp_path)
        assert groups == {}

    def test_model_name_with_hyphens_and_numbers(self, tmp_path):
        """Model names with hyphens and numbers."""
        (tmp_path / "openai-gpt-4o-mini-run1.json").write_text("{}")
        (tmp_path / "openai-gpt-4o-mini-run2.json").write_text("{}")
        groups = _group_runs(tmp_path)
        assert "openai-gpt-4o-mini" in groups
        assert len(groups["openai-gpt-4o-mini"]) == 2


# ---------------------------------------------------------------------------
# _metrics_to_result_summary
# ---------------------------------------------------------------------------


class TestMetricsToResultSummary:
    def test_correct_field_mapping(self):
        m = _make_metrics()
        rs = _metrics_to_result_summary(m)
        assert rs.status == "ok"
        assert rs.n_plants == m.n_system
        assert rs.tp == m.n_matched
        assert rs.fp == m.n_hallucinated
        assert rs.fn == m.n_missed
        assert rs.f1 == round(m.f1, 4)

    def test_accuracy_fields_rounded(self):
        m = _make_metrics(fuel_accuracy=0.75432, status_accuracy=0.82111,
                          province_accuracy=0.91999)
        rs = _metrics_to_result_summary(m)
        assert rs.fuel_accuracy == round(0.75432, 4)
        assert rs.status_accuracy == round(0.82111, 4)
        assert rs.province_accuracy == round(0.91999, 4)

    def test_none_accuracy_stays_none(self):
        m = _make_metrics(fuel_accuracy=None, status_accuracy=None, province_accuracy=None)
        rs = _metrics_to_result_summary(m)
        assert rs.fuel_accuracy is None
        assert rs.status_accuracy is None
        assert rs.province_accuracy is None

    def test_zero_accuracy_treated_as_falsy(self):
        """Known quirk: fuel_accuracy=0.0 is falsy → mapped to None.
        Source uses `if m.fuel_accuracy` instead of `is not None`."""
        m = _make_metrics(fuel_accuracy=0.0)
        rs = _metrics_to_result_summary(m)
        # 0.0 is falsy in Python, so `if m.fuel_accuracy` is False
        assert rs.fuel_accuracy is None

    def test_f1_rounded_to_four_decimals(self):
        m = _make_metrics(f1=0.123456789)
        rs = _metrics_to_result_summary(m)
        assert rs.f1 == 0.1235


# ---------------------------------------------------------------------------
# _results_to_records
# ---------------------------------------------------------------------------


class TestResultsToRecords:
    def _make_analysis_output(self):
        """Build minimal results, run_metrics_by_model, run_paths_by_model."""
        m1 = _make_metrics(f1=0.80, n_system=90, n_matched=80, n_hallucinated=10, n_missed=20)
        m2 = _make_metrics(f1=0.82, n_system=92, n_matched=82, n_hallucinated=10, n_missed=18)
        m3 = _make_metrics(f1=0.85, n_system=95, n_matched=85, n_hallucinated=10, n_missed=15)

        results = [{
            "model": "test-model",
            "n_reference": 100,
            "n_runs": 3,
            "n_valid_runs": 3,
            "run_f1_scores": [0.80, 0.82, 0.85],
            "run_n_matched": [80, 82, 85],
            "run_n_system": [90, 92, 95],
            "median_f1": 0.82,
            "median_coverage": 0.82,
            "median_precision": 0.90,
            "majority_f1": 0.87,
            "majority_coverage": 0.87,
            "majority_precision": 0.92,
            "majority_n_matched": 87,
            "majority_n_system": 95,
            "majority_n_hallucinated": 8,
            "n_majority_plants": 95,
            "union_f1": 0.89,
            "union_coverage": 0.89,
            "union_precision": 0.88,
            "union_n_matched": 89,
            "union_n_system": 101,
            "union_n_hallucinated": 12,
        }]

        run_metrics = {"test-model": [m1, m2, m3]}
        run_paths = {
            "test-model": [
                Path("/data/test-model-run1.json"),
                Path("/data/test-model-run2.json"),
                Path("/data/test-model-run3.json"),
            ]
        }
        return results, run_metrics, run_paths

    def test_creates_per_run_records(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        output_dir = Path("/output")
        records = _results_to_records(results, run_metrics, run_paths, output_dir)
        rag_records = [r for r in records if r.method_params.prompt_version == "rag"]
        assert len(rag_records) == 3

    def test_per_run_records_have_correct_model(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        records = _results_to_records(results, run_metrics, run_paths, Path("/output"))
        rag_records = [r for r in records if r.method_params.prompt_version == "rag"]
        for r in rag_records:
            assert r.method_params.model == "test-model"

    def test_per_run_records_have_result_files(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        records = _results_to_records(results, run_metrics, run_paths, Path("/output"))
        rag_records = [r for r in records if r.method_params.prompt_version == "rag"]
        assert rag_records[0].result_file == "/data/test-model-run1.json"

    def test_creates_majority_record(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        output_dir = Path("/output")
        records = _results_to_records(results, run_metrics, run_paths, output_dir)
        cons_records = [
            r for r in records
            if r.method_params.prompt_version == "rag_consistency"
            and "consolidated" in r.method_params.model
        ]
        assert len(cons_records) == 1
        assert cons_records[0].method_params.model == "test-model-consolidated"
        assert cons_records[0].result_summary.f1 == 0.87

    def test_creates_union_record(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        output_dir = Path("/output")
        records = _results_to_records(results, run_metrics, run_paths, output_dir)
        union_records = [
            r for r in records
            if r.method_params.prompt_version == "rag_consistency"
            and "union" in r.method_params.model
        ]
        assert len(union_records) == 1
        assert union_records[0].method_params.model == "test-model-union"
        assert union_records[0].result_summary.f1 == 0.89

    def test_total_record_count(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        records = _results_to_records(results, run_metrics, run_paths, Path("/output"))
        # 3 per-run + 1 majority + 1 union = 5
        assert len(records) == 5

    def test_no_majority_when_none(self):
        results = [{
            "model": "sparse-model",
            "n_reference": 100,
            "n_runs": 1,
            "n_valid_runs": 1,
            "run_f1_scores": [0.5],
            "run_n_matched": [50],
            "run_n_system": [60],
            "median_f1": 0.5,
            "median_coverage": 0.5,
            "median_precision": 0.83,
            "majority_f1": None,
            "majority_coverage": None,
            "majority_precision": None,
            "majority_n_matched": None,
            "majority_n_system": None,
            "majority_n_hallucinated": None,
            "n_majority_plants": 0,
            "union_f1": None,
            "union_coverage": None,
            "union_precision": None,
            "union_n_matched": None,
            "union_n_system": None,
            "union_n_hallucinated": None,
        }]
        m = _make_metrics(f1=0.5)
        records = _results_to_records(
            results, {"sparse-model": [m]},
            {"sparse-model": [Path("/data/sparse-model-run1.json")]},
            Path("/output"),
        )
        cons = [r for r in records if r.method_params.prompt_version == "rag_consistency"]
        assert len(cons) == 0

    def test_all_records_are_method_rag(self):
        results, run_metrics, run_paths = self._make_analysis_output()
        records = _results_to_records(results, run_metrics, run_paths, Path("/output"))
        for r in records:
            assert r.method == Method.RAG


# ---------------------------------------------------------------------------
# write_measurements
# ---------------------------------------------------------------------------


class TestWriteMeasurements:
    def test_creates_new_file(self, tmp_path):
        path = tmp_path / "measurements.jsonl"
        records = [_make_run_record()]
        write_measurements(records, path)
        assert path.exists()
        loaded = RunRecord.load_jsonl(path)
        assert len(loaded) == 1

    def test_replaces_rag_records(self, tmp_path):
        path = tmp_path / "measurements.jsonl"
        # Write initial rag records
        old_records = [
            _make_run_record(model="old-model", prompt_version="rag", f1=0.5),
        ]
        RunRecord.save_jsonl(old_records, path)

        # Now write new rag records via write_measurements
        new_records = [
            _make_run_record(model="new-model", prompt_version="rag", f1=0.9),
        ]
        write_measurements(new_records, path)

        loaded = RunRecord.load_jsonl(path)
        models = [r.method_params.model for r in loaded]
        assert "old-model" not in models
        assert "new-model" in models

    def test_replaces_rag_consistency_records(self, tmp_path):
        path = tmp_path / "measurements.jsonl"
        old_records = [
            _make_run_record(model="old-cons", prompt_version="rag_consistency"),
        ]
        RunRecord.save_jsonl(old_records, path)

        new_records = [
            _make_run_record(model="new-cons", prompt_version="rag_consistency"),
        ]
        write_measurements(new_records, path)

        loaded = RunRecord.load_jsonl(path)
        models = [r.method_params.model for r in loaded]
        assert "old-cons" not in models
        assert "new-cons" in models

    def test_preserves_non_rag_records(self, tmp_path):
        path = tmp_path / "measurements.jsonl"
        # Pre-existing single-method record
        existing = RunRecord(
            method=Method.SINGLE,
            method_params=MethodParams(model="keep-me", prompt_version="census_v1"),
            result_summary=ResultSummary(status="ok", n_plants=50, tp=40, fp=10, fn=10, f1=0.8),
        )
        RunRecord.save_jsonl([existing], path)

        new_records = [_make_run_record(model="new-rag", prompt_version="rag")]
        write_measurements(new_records, path)

        loaded = RunRecord.load_jsonl(path)
        models = [r.method_params.model for r in loaded]
        assert "keep-me" in models
        assert "new-rag" in models
        assert len(loaded) == 2

    def test_merge_replaces_rag_keeps_others(self, tmp_path):
        """Full scenario: existing file has census + rag + rag_consistency.
        After merge, census stays, old rag/rag_consistency replaced by new."""
        path = tmp_path / "measurements.jsonl"
        existing = [
            RunRecord(
                method=Method.SINGLE,
                method_params=MethodParams(model="census-model", prompt_version="census_v1"),
                result_summary=ResultSummary(status="ok", f1=0.7),
            ),
            RunRecord(
                method=Method.RAG,
                method_params=MethodParams(model="old-rag", prompt_version="rag"),
                result_summary=ResultSummary(status="ok", f1=0.6),
            ),
            RunRecord(
                method=Method.RAG,
                method_params=MethodParams(model="old-cons", prompt_version="rag_consistency"),
                result_summary=ResultSummary(status="ok", f1=0.65),
            ),
        ]
        RunRecord.save_jsonl(existing, path)

        new_records = [
            _make_run_record(model="new-rag-1", prompt_version="rag"),
            _make_run_record(model="new-rag-2", prompt_version="rag"),
            _make_run_record(model="new-cons", prompt_version="rag_consistency"),
        ]
        write_measurements(new_records, path)

        loaded = RunRecord.load_jsonl(path)
        assert len(loaded) == 4  # 1 census + 3 new
        versions = [r.method_params.prompt_version for r in loaded]
        assert versions.count("census_v1") == 1
        assert versions.count("rag") == 2
        assert versions.count("rag_consistency") == 1
        models = [r.method_params.model for r in loaded]
        assert "old-rag" not in models
        assert "old-cons" not in models

    def test_nonexistent_file(self, tmp_path):
        """When file does not exist, creates it fresh."""
        path = tmp_path / "subdir" / "measurements.jsonl"
        path.parent.mkdir(parents=True)
        records = [_make_run_record()]
        write_measurements(records, path)
        loaded = RunRecord.load_jsonl(path)
        assert len(loaded) == 1

    def test_empty_new_records_preserves_non_rag(self, tmp_path):
        """Empty new records list still strips old rag entries, keeps others."""
        path = tmp_path / "measurements.jsonl"
        existing = [
            RunRecord(
                method=Method.SINGLE,
                method_params=MethodParams(model="census-model", prompt_version="census_v1"),
                result_summary=ResultSummary(status="ok", f1=0.7),
            ),
            RunRecord(
                method=Method.RAG,
                method_params=MethodParams(model="old-rag", prompt_version="rag"),
                result_summary=ResultSummary(status="ok", f1=0.6),
            ),
        ]
        RunRecord.save_jsonl(existing, path)

        write_measurements([], path)
        loaded = RunRecord.load_jsonl(path)
        assert len(loaded) == 1
        assert loaded[0].method_params.model == "census-model"


# ---------------------------------------------------------------------------
# _extract_to_csv
# ---------------------------------------------------------------------------


@dataclass
class _FakeExtractResult:
    output_path: Path | None
    message: str


class TestExtractToCsv:
    def test_success_returns_csv_path(self, tmp_path):
        json_path = tmp_path / "model-run1.json"
        json_path.write_text("{}")
        work_dir = tmp_path / "work"
        csv_path = work_dir / "model-run1.csv"

        def fake_extract(jp, wd, overwrite):
            wd.mkdir(parents=True, exist_ok=True)
            csv_path.write_text("name,fuel\nPlantA,coal\n")
            return _FakeExtractResult(output_path=csv_path, message="ok")

        with patch("aedist.self_consistency.extract_one", side_effect=fake_extract):
            result = _extract_to_csv(json_path, work_dir)
        assert result == csv_path

    def test_failure_returns_none(self, tmp_path):
        json_path = tmp_path / "bad-run1.json"
        json_path.write_text("{}")
        work_dir = tmp_path / "work"

        def fake_extract(jp, wd, overwrite):
            return _FakeExtractResult(output_path=None, message="parse error")

        with patch("aedist.self_consistency.extract_one", side_effect=fake_extract):
            result = _extract_to_csv(json_path, work_dir)
        assert result is None

    def test_creates_work_dir(self, tmp_path):
        json_path = tmp_path / "model-run1.json"
        json_path.write_text("{}")
        work_dir = tmp_path / "deep" / "nested" / "work"
        csv_path = work_dir / "model-run1.csv"

        def fake_extract(jp, wd, overwrite):
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            csv_path.write_text("name,fuel\n")
            return _FakeExtractResult(output_path=csv_path, message="ok")

        with patch("aedist.self_consistency.extract_one", side_effect=fake_extract):
            result = _extract_to_csv(json_path, work_dir)
        assert work_dir.exists()

    def test_output_path_exists_but_missing_file_returns_none(self, tmp_path):
        """If extract_one returns a path that doesn't actually exist on disk."""
        json_path = tmp_path / "model-run1.json"
        json_path.write_text("{}")
        work_dir = tmp_path / "work"
        phantom = work_dir / "phantom.csv"

        def fake_extract(jp, wd, overwrite):
            return _FakeExtractResult(output_path=phantom, message="ok")

        with patch("aedist.self_consistency.extract_one", side_effect=fake_extract):
            result = _extract_to_csv(json_path, work_dir)
        assert result is None


# ---------------------------------------------------------------------------
# evaluate_single_runs
# ---------------------------------------------------------------------------


class TestEvaluateSingleRuns:
    def test_evaluates_each_run(self, tmp_path):
        """With mocked extraction and evaluation, returns metrics per run."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        csv1 = work_dir / "run1.csv"
        csv2 = work_dir / "run2.csv"
        csv1.write_text("name\nA\n")
        csv2.write_text("name\nB\n")

        calls = iter([csv1, csv2])
        fake_metrics = _make_metrics(f1=0.75)

        with (
            patch("aedist.self_consistency._extract_to_csv", side_effect=lambda jp, wd: next(calls)),
            patch("aedist.self_consistency.load_plants_csv", return_value=[_plant("A")]),
            patch("aedist.self_consistency.reconcile", return_value=[]),
            patch("aedist.self_consistency.compute_metrics", return_value=fake_metrics),
        ):
            metrics_list, csv_paths = evaluate_single_runs(
                [Path("run1.json"), Path("run2.json")],
                work_dir,
                [_plant("A")],
            )

        assert len(metrics_list) == 2
        assert len(csv_paths) == 2
        for m in metrics_list:
            assert m is not None
            assert m.f1 == 0.75

    def test_failed_extraction_returns_none_metrics(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        with patch("aedist.self_consistency._extract_to_csv", return_value=None):
            metrics_list, csv_paths = evaluate_single_runs(
                [Path("run1.json")],
                work_dir,
                [_plant("A")],
            )

        assert len(metrics_list) == 1
        assert metrics_list[0] is None
        assert csv_paths[0] is None

    def test_mixed_success_and_failure(self, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        csv1 = work_dir / "run1.csv"
        csv1.write_text("name\nA\n")
        fake_metrics = _make_metrics(f1=0.60)

        extract_results = iter([csv1, None])

        with (
            patch("aedist.self_consistency._extract_to_csv", side_effect=lambda jp, wd: next(extract_results)),
            patch("aedist.self_consistency.load_plants_csv", return_value=[_plant("A")]),
            patch("aedist.self_consistency.reconcile", return_value=[]),
            patch("aedist.self_consistency.compute_metrics", return_value=fake_metrics),
        ):
            metrics_list, csv_paths = evaluate_single_runs(
                [Path("run1.json"), Path("run2.json")],
                work_dir,
                [_plant("A")],
            )

        assert len(metrics_list) == 2
        assert metrics_list[0] is not None
        assert metrics_list[1] is None


# ---------------------------------------------------------------------------
# _print_comparison_table
# ---------------------------------------------------------------------------


class TestPrintComparisonTable:
    def test_prints_without_error(self, capsys):
        results = [
            {
                "model": "gpt-4o",
                "median_f1": 0.82,
                "majority_f1": 0.87,
                "union_f1": 0.89,
            },
            {
                "model": "claude-sonnet",
                "median_f1": 0.78,
                "majority_f1": 0.80,
                "union_f1": 0.85,
            },
        ]
        _print_comparison_table(results)
        captured = capsys.readouterr()
        assert "gpt-4o" in captured.out
        assert "claude-sonnet" in captured.out

    def test_handles_none_majority_and_union(self, capsys):
        results = [
            {
                "model": "sparse-model",
                "median_f1": 0.5,
                "majority_f1": None,
                "union_f1": None,
            },
        ]
        _print_comparison_table(results)
        captured = capsys.readouterr()
        assert "sparse-model" in captured.out

    def test_shows_gain_columns(self, capsys):
        results = [
            {
                "model": "model-a",
                "median_f1": 0.80,
                "majority_f1": 0.85,
                "union_f1": 0.90,
            },
        ]
        _print_comparison_table(results)
        captured = capsys.readouterr()
        # Should contain the header words
        assert "Med F1" in captured.out
        assert "Maj F1" in captured.out
        assert "Union F1" in captured.out


# ---------------------------------------------------------------------------
# run_analysis — integration test with real extraction
# ---------------------------------------------------------------------------


class TestRunAnalysis:
    def _setup_runs(self, tmp_path):
        """Create reference CSV and model JSON files with extractable CSV responses."""
        ref_path = tmp_path / "reference.csv"
        ref_path.write_text(
            "name,fuel,status,cod,province,capacity_mwe\n"
            "Pha Lai,coal,operational,1983,Hai Duong,440\n"
            "Ca Mau I,gas,operational,2007,Ca Mau,771\n"
            "Vinh Tan 2,coal,operational,2014,Binh Thuan,1244\n"
        )
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()

        csv_run1 = (
            "name,fuel,status,cod,province,capacity_mwe\n"
            "Pha Lai,coal,operational,1983,Hai Duong,440\n"
            "Ca Mau I,gas,operational,2007,Ca Mau,771\n"
        )
        csv_run2 = (
            "name,fuel,status,cod,province,capacity_mwe\n"
            "Pha Lai,coal,operational,1983,Hai Duong,440\n"
            "Vinh Tan 2,coal,operational,2014,Binh Thuan,1244\n"
        )
        csv_run3 = (
            "name,fuel,status,cod,province,capacity_mwe\n"
            "Pha Lai,coal,operational,1983,Hai Duong,440\n"
            "Ca Mau I,gas,operational,2007,Ca Mau,771\n"
            "Vinh Tan 2,coal,operational,2014,Binh Thuan,1244\n"
        )
        for i, csv_content in enumerate([csv_run1, csv_run2, csv_run3], 1):
            jp = input_dir / f"test-model-run{i}.json"
            jp.write_text(json.dumps({"response": f"```csv\n{csv_content}```"}))

        output_dir = tmp_path / "output"
        return input_dir, output_dir, ref_path

    def test_produces_results(self, tmp_path):
        input_dir, output_dir, ref_path = self._setup_runs(tmp_path)
        results, run_metrics, run_paths = run_analysis(input_dir, output_dir, ref_path)
        assert len(results) == 1
        r = results[0]
        assert r["model"] == "test-model"
        assert r["n_valid_runs"] == 3
        assert r["majority_f1"] is not None
        assert r["union_f1"] is not None

    def test_majority_f1_positive(self, tmp_path):
        input_dir, output_dir, ref_path = self._setup_runs(tmp_path)
        results, _, _ = run_analysis(input_dir, output_dir, ref_path)
        assert results[0]["majority_f1"] > 0

    def test_writes_consolidated_and_union_csv(self, tmp_path):
        input_dir, output_dir, ref_path = self._setup_runs(tmp_path)
        run_analysis(input_dir, output_dir, ref_path)
        assert (output_dir / "test-model-consolidated.csv").exists()
        assert (output_dir / "test-model-union.csv").exists()

    def test_empty_input_dir(self, tmp_path):
        input_dir = tmp_path / "empty"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        ref_path = tmp_path / "ref.csv"
        ref_path.write_text("name,fuel\nA,coal\n")
        results, _, _ = run_analysis(input_dir, output_dir, ref_path)
        assert results == []

    def test_run_metrics_sorted_by_f1(self, tmp_path):
        input_dir, output_dir, ref_path = self._setup_runs(tmp_path)
        _, run_metrics, _ = run_analysis(input_dir, output_dir, ref_path)
        metrics = run_metrics["test-model"]
        f1_scores = [m.f1 for m in metrics]
        assert f1_scores == sorted(f1_scores)

    def test_result_fields_complete(self, tmp_path):
        input_dir, output_dir, ref_path = self._setup_runs(tmp_path)
        results, _, _ = run_analysis(input_dir, output_dir, ref_path)
        r = results[0]
        expected_keys = {
            "model", "n_reference", "n_runs", "n_valid_runs",
            "run_f1_scores", "run_n_matched", "run_n_system",
            "median_f1", "median_coverage", "median_precision",
            "majority_f1", "majority_coverage", "majority_precision",
            "majority_n_matched", "majority_n_system", "majority_n_hallucinated",
            "n_majority_plants",
            "union_f1", "union_coverage", "union_precision",
            "union_n_matched", "union_n_system", "union_n_hallucinated",
        }
        assert expected_keys.issubset(set(r.keys()))
