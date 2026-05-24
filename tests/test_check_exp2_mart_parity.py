"""Tests for the Exp2 mart parity checker."""

import csv

from aedist.check_exp2_mart_parity import check_parity


def _write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_check_parity_passes_for_matching_views(tmp_path):
    old_dir = tmp_path / "old"
    mart_dir = tmp_path / "mart"

    _write_csv(
        old_dir / "tab_exp2_arms_runs.csv",
        ["arm", "agent", "model", "run", "classification", "narrative_chars", "inventory_rows", "cost_usd", "wall_s", "turns"],
        [
            {
                "arm": "naive",
                "agent": "anthropic",
                "model": "claude-opus-4-6",
                "run": "1",
                "classification": "report",
                "narrative_chars": "10",
                "inventory_rows": "1",
                "cost_usd": "0.10",
                "wall_s": "1.0",
                "turns": "1",
            }
        ],
    )
    _write_csv(
        mart_dir / "tab_exp2_arms_runs_view.csv",
        ["arm", "agent", "model", "run", "classification", "narrative_chars", "inventory_rows", "cost_usd", "wall_s", "turns"],
        [
            {
                "arm": "naive",
                "agent": "anthropic",
                "model": "claude-opus-4-6",
                "run": "1",
                "classification": "report",
                "narrative_chars": "10",
                "inventory_rows": "1",
                "cost_usd": "0.1005",
                "wall_s": "1.0",
                "turns": "1",
            }
        ],
    )

    bib_fields = [
        "agent",
        "arm",
        "run",
        "n_rows",
        "src1_empty",
        "src1_notfound",
        "src1_present",
        "src1_valid",
        "src1_primary",
        "src2_empty",
        "src2_notfound",
        "src2_present",
        "src2_valid",
        "src2_primary",
        "notes_empty",
        "notes_notfound",
        "notes_present",
        "bib_entries",
        "bib_valid",
        "bib_primary",
        "citation_style",
    ]
    bib_row = {
        "agent": "anthropic",
        "arm": "naive",
        "run": "1",
        "n_rows": "1",
        "src1_empty": "0",
        "src1_notfound": "0",
        "src1_present": "1",
        "src1_valid": "1",
        "src1_primary": "1",
        "src2_empty": "0",
        "src2_notfound": "0",
        "src2_present": "1",
        "src2_valid": "1",
        "src2_primary": "0",
        "notes_empty": "0",
        "notes_notfound": "0",
        "notes_present": "1",
        "bib_entries": "2",
        "bib_valid": "",
        "bib_primary": "1",
        "citation_style": "inline-ref",
    }
    _write_csv(old_dir / "tab_exp2_bib_quality.csv", bib_fields, [bib_row])
    _write_csv(mart_dir / "tab_exp2_bib_quality_view.csv", bib_fields, [bib_row])

    turn_fields = ["agent", "arm", "run", "turn", "rows", "cls"]
    _write_csv(
        old_dir / "exp2_turn_trajectory.csv",
        turn_fields,
        [{"agent": "anthropic", "arm": "optimised", "run": "1", "turn": "1", "rows": "1", "cls": "report"}],
    )
    _write_csv(
        mart_dir / "exp2_turn_trajectory_view.csv",
        turn_fields,
        [{"agent": "anthropic", "arm": "optimised", "run": "1", "turn": "1", "rows": "1", "cls": "report"}],
    )

    score_fields = [
        "arm",
        "model",
        "run",
        "prompt_version",
        "n_rows",
        "accuracy_coverage",
        "accuracy_coverage_annotation",
        "accuracy_precision",
        "accuracy_precision_annotation",
        "accuracy_f1",
        "accuracy_f1_annotation",
        "accuracy_fuel",
        "accuracy_fuel_annotation",
        "accuracy_status",
        "accuracy_status_annotation",
        "accuracy_province",
        "accuracy_province_annotation",
        "coherence_vocab_adherence",
        "coherence_vocab_adherence_annotation",
        "coherence_status_vocab_adherence",
        "coherence_status_vocab_adherence_annotation",
        "provenance_source_presence",
        "provenance_source_presence_annotation",
        "provenance_high_conf_dual_source",
        "provenance_high_conf_dual_source_annotation",
        "temporality_asof_presence",
        "temporality_asof_presence_annotation",
        "temporality_plausible_range",
        "temporality_plausible_range_annotation",
        "field_completeness_core",
        "field_completeness_core_annotation",
        "field_completeness_capacity",
        "field_completeness_capacity_annotation",
    ]
    score_row = {
        "arm": "naive",
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
        "coherence_status_vocab_adherence": "1.0000",
        "coherence_status_vocab_adherence_annotation": "",
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
    _write_csv(old_dir / "sota_cross_eval.csv", score_fields, [score_row])
    score_row_mart = dict(score_row)
    score_row_mart["accuracy_coverage"] = "0.5005"
    _write_csv(mart_dir / "sota_cross_eval_view.csv", score_fields, [score_row_mart])

    results = check_parity(old_dir, mart_dir)

    assert all(result.ok for result in results)
