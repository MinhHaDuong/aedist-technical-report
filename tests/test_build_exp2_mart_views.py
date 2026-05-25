"""Tests for mart-derived Exp2 CSV views."""

import csv
import json

from aedist.build_exp2_mart import write_exp2_mart
from aedist.build_exp2_mart_views import write_exp2_mart_views


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_md(path, content):
    path.write_text(content, encoding="utf-8")


def _write_cross_eval_csv(path, rows):
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _score_row(arm):
    return {
        "arm": arm,
        "model": "claude-opus-4-6",
        "run": "1",
        "prompt_version": "exp2",
        "n_rows": "1",
        "accuracy_coverage": "0.5000",
        "accuracy_coverage_annotation": "",
        "accuracy_precision": "1.0000",
        "accuracy_precision_annotation": "",
        "accuracy_f1": "0.6667",
        "accuracy_f1_annotation": "",
        "accuracy_fuel": "1.0000",
        "accuracy_fuel_annotation": "",
        "accuracy_status": "1.0000",
        "accuracy_status_annotation": "",
        "accuracy_province": "1.0000",
        "accuracy_province_annotation": "",
        "coherence_vocab_adherence": "1.0000",
        "coherence_vocab_adherence_annotation": "",
        "coherence_capacity_nonnegative": "1.0000",
        "coherence_capacity_nonnegative_annotation": "",
        "provenance_source_presence": "1.0000",
        "provenance_source_presence_annotation": "",
        "provenance_high_conf_dual_source": "1.0000",
        "provenance_high_conf_dual_source_annotation": "",
        "temporality_asof_presence": "1.0000",
        "temporality_asof_presence_annotation": "",
        "temporality_plausible_range": "1.0000",
        "temporality_plausible_range_annotation": "",
        "field_completeness_core": "1.0000",
        "field_completeness_core_annotation": "",
        "field_completeness_capacity": "1.0000",
        "field_completeness_capacity_annotation": "",
    }


def _mart_fixture(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    for arm_dir, arm_name, turns in ((naive_dir, "naive", 1), (optimised_dir, "optimised", 2)):
        _write_json(
            arm_dir / "anthropic_run01.json",
            {
                "model": "claude-opus-4-6",
                "run": 1,
                "arm": arm_name,
                "classification": "report",
                "turns": turns,
                "narrative_chars": 4,
                "cost_usd": 0.1,
            },
        )
        _write_md(
            arm_dir / "anthropic_run01.md",
            "| Name | Fuel | Capacity | Status | COD | Province | Source 1 | Source 2 | Notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| A | Coal | 1 | Operating | 1983 | HN | EVN report | Reuters | note |\n"
            "## Bibliography\n"
            "1. **EVN report**\n"
            "2. **Reuters article**\n",
        )
        probe_dir = arm_dir / "probes" / "anthropic_run01"
        probe_dir.mkdir(parents=True)
        _write_json(
            probe_dir / "anthropic_turn_01.raw.json",
            {
                "content": [
                    {
                        "type": "text",
                        "text": "| Name | Cap |\n| --- | --- |\n| A | 1 |\n",
                    }
                ]
            },
        )
        _write_json(probe_dir / "anthropic_turn_01.classification.json", {"class": "report"})

    cross_eval_csv = tmp_path / "sota_cross_eval.csv"
    _write_cross_eval_csv(cross_eval_csv, [_score_row("naive"), _score_row("optimised")])
    mart_path = tmp_path / "exp2_mart.jsonl"
    write_exp2_mart(
        mart_path,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=cross_eval_csv,
        repo_root=tmp_path,
    )
    return mart_path


def test_write_exp2_mart_views(tmp_path):
    mart_path = _mart_fixture(tmp_path)
    output_dir = tmp_path / "generated"

    outputs = write_exp2_mart_views(mart_path, output_dir, repo_root=tmp_path)

    arms_rows = list(csv.DictReader(outputs["tab_exp2_arms_runs_view.csv"].open(encoding="utf-8")))
    bib_rows = list(
        csv.DictReader(outputs["tab_exp2_bib_quality_view.csv"].open(encoding="utf-8"))
    )
    turn_rows = list(
        csv.DictReader(outputs["exp2_turn_trajectory_view.csv"].open(encoding="utf-8"))
    )
    score_rows = list(csv.DictReader(outputs["sota_cross_eval_view.csv"].open(encoding="utf-8")))

    assert len(arms_rows) == 2
    assert arms_rows[0]["inventory_rows"] == "1"
    assert len(bib_rows) == 2
    assert bib_rows[0]["src1_present"] == "1"
    assert len(turn_rows) == 2
    assert turn_rows[0]["rows"] == "1"
    assert len(score_rows) == 2
    assert score_rows[0]["accuracy_coverage"] == "0.5000"
