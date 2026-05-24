"""Tests for the Exp2 mart builder."""

import json

from aedist.build_exp2_mart import build_exp2_mart, write_exp2_mart


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


def _score_row(arm, model, run):
    return {
        "arm": arm,
        "model": model,
        "run": str(run),
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


def test_build_exp2_mart_ignores_raw_payload_files(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "anthropic_run01.json",
        {"model": "claude-opus-4-6", "run": 1, "classification": "report", "narrative_chars": 4},
    )
    _write_md(
        naive_dir / "anthropic_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| A | Coal | 1 | Operating | 1983 | HN |\n",
    )
    _write_json(
        optimised_dir / "anthropic_run01.json",
        {
            "model": "claude-opus-4-6",
            "run": 1,
            "arm": "optimised",
            "classification": "report",
            "turns": 3,
            "narrative_chars": 8,
            "total_cost_usd": 1.0,
        },
    )
    _write_md(
        optimised_dir / "anthropic_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| B | Gas | 2 | Operating | 1984 | HN |\n",
    )
    (naive_dir / "anthropic_run01.raw.json").write_text("{not: valid json}", encoding="utf-8")

    for run_dir, turn_cls in ((naive_dir, "report"), (optimised_dir, "report")):
        probe_dir = run_dir / "probes" / "anthropic_run01"
        probe_dir.mkdir(parents=True)
        (probe_dir / "anthropic_turn_01.raw.json").write_text("{not: valid json}", encoding="utf-8")
        _write_json(
            probe_dir / "anthropic_turn_01.classification.json",
            {"class": turn_cls},
        )

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [
            _score_row("naive", "claude-opus-4-6", 1),
            _score_row("optimised", "claude-opus-4-6", 1),
        ],
    )

    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    assert len(records) == 6
    run_record = next(record for record in records if record.record_kind == "run" and record.arm == "naive")
    probe_record = next(record for record in records if record.record_kind == "probe" and record.arm == "naive")
    score_record = next(record for record in records if record.record_kind == "score" and record.arm == "naive")
    assert run_record.run_summary.n_rows == 1
    assert probe_record.probe_summary.turn == 1
    assert score_record.score_summary.accuracy.coverage.value == 0.5


def test_write_exp2_mart_writes_jsonl(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    for arm_dir, arm_name in ((naive_dir, "naive"), (optimised_dir, "optimised")):
        _write_json(
            arm_dir / "anthropic_run01.json",
            {
                "model": "claude-opus-4-6",
                "run": 1,
                "arm": arm_name,
                "classification": "report",
                "turns": 1 if arm_name == "naive" else 3,
                "narrative_chars": 4,
                "cost_usd": 0.1,
            },
        )
        _write_md(
            arm_dir / "anthropic_run01.md",
            "| Name | Fuel | Capacity | Status | COD | Province |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| A | Coal | 1 | Operating | 1983 | HN |\n",
        )
        probe_dir = arm_dir / "probes" / "anthropic_run01"
        probe_dir.mkdir(parents=True)
        _write_json(probe_dir / "anthropic_turn_01.classification.json", {"class": "report"})
        _write_json(probe_dir / "anthropic_turn_01.raw.json", {"content": [{"type": "text", "text": "| A | 1 |\n"}]})

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [
            _score_row("naive", "claude-opus-4-6", 1),
            _score_row("optimised", "claude-opus-4-6", 1),
        ],
    )

    output = tmp_path / "exp2_mart.jsonl"
    records = write_exp2_mart(
        output,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(records)
    assert any('"record_kind":"score"' in line for line in lines)
    assert any('"record_kind":"probe"' in line for line in lines)


def test_build_exp2_mart_handles_no_report_empty_markdown(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "mistral_run02.json",
        {
            "model": "mistral-large-2512",
            "run": 2,
            "classification": "no_report",
            "narrative_chars": 0,
            "cost_usd": 0.1,
        },
    )
    (naive_dir / "mistral_run02.md").write_text("", encoding="utf-8")

    _write_json(
        optimised_dir / "mistral_run02.json",
        {
            "model": "mistral-large-2512",
            "run": 2,
            "arm": "optimised",
            "classification": "no_report",
            "turns": 2,
            "narrative_chars": 0,
            "total_cost_usd": 0.2,
        },
    )
    (optimised_dir / "mistral_run02.md").write_text("", encoding="utf-8")

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [
            _score_row("naive", "mistral-large-2512", 2),
            _score_row("optimised", "mistral-large-2512", 2),
        ],
    )

    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    naive_run = next(
        record
        for record in records
        if record.record_kind == "run" and record.arm == "naive" and record.model == "mistral-large-2512"
    )
    assert naive_run.run_summary.classification == "no_report"
    assert naive_run.run_summary.n_rows == 0


def test_build_exp2_mart_matches_score_row_with_model_drift(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "anthropic_run01.json",
        {
            "model": "claude-opus-4-6",
            "run": 1,
            "classification": "report",
            "narrative_chars": 4,
        },
    )
    _write_md(
        naive_dir / "anthropic_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| A | Coal | 1 | Operating | 1983 | HN |\n",
    )

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [_score_row("naive", "claude-opus-4-6-20250514", 1)],
    )

    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    score_record = next(record for record in records if record.record_kind == "score")
    assert score_record.model == "claude-opus-4-6"
    assert score_record.score_summary.n_rows == 1


def test_build_exp2_mart_allows_missing_score_rows(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "openai_run01.json",
        {
            "model": "gpt-5.5",
            "run": 1,
            "classification": "report",
            "narrative_chars": 4,
        },
    )
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| A | Coal | 1 | Operating | 1983 | HN |\n",
    )

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [_score_row("naive", "some-other-model", 99)],
    )

    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    assert any(record.record_kind == "run" for record in records)
    assert not any(record.record_kind == "score" for record in records)
