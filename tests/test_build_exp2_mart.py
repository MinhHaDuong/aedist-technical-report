"""Tests for the Exp2 mart builder."""

import json
from pathlib import Path

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
        "coherence_status_vocab_adherence": "0.7500",
        "coherence_status_vocab_adherence_annotation": "",
        "coherence_capacity_nonnegative": "0.5000",
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
        (probe_dir / "anthropic_turn_01.raw.json").write_text(
            "{not: valid json}", encoding="utf-8"
        )
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
    run_record = next(
        record for record in records if record.record_kind == "run" and record.arm == "naive"
    )
    probe_record = next(
        record for record in records if record.record_kind == "probe" and record.arm == "naive"
    )
    score_record = next(
        record for record in records if record.record_kind == "score" and record.arm == "naive"
    )
    assert run_record.run_summary.n_rows == 1
    assert probe_record.probe_summary.turn == 1
    assert score_record.score_summary.accuracy.coverage.value == 0.5


def test_build_exp2_mart_wires_class_trace_and_n_bib_entries(tmp_path):
    """Finding #3 (ticket 0385): a run whose source JSON carries ``class_trace``
    and ``n_bib_entries`` produces a RunSummary with both populated, not None."""
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
                "class_trace": ["report"],
                "n_bib_entries": 7,
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

    run_records = [record for record in records if record.record_kind == "run"]
    assert run_records, "expected at least one run record"
    for run_record in run_records:
        assert run_record.run_summary.class_trace == ["report"]
        assert run_record.run_summary.n_bib_entries == 7


def test_build_exp2_mart_resolves_repo_relative_paths_from_repo_root(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    cwd = tmp_path / "elsewhere"
    naive_dir = repo_root / "experiments" / "outputs" / "sota_exp2_naive_arm"
    optimised_dir = repo_root / "experiments" / "outputs" / "sota_exp2_brerun1"
    naive_dir.mkdir(parents=True)
    optimised_dir.mkdir(parents=True)
    cwd.mkdir()

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

    (repo_root / "experiments" / "derived").mkdir(parents=True)
    _write_cross_eval_csv(
        repo_root / "experiments" / "derived" / "sota_cross_eval.csv",
        [
            _score_row("naive", "claude-opus-4-6", 1),
            _score_row("optimised", "claude-opus-4-6", 1),
        ],
    )

    monkeypatch.chdir(cwd)
    records = build_exp2_mart(
        naive_dir=Path("experiments/outputs/sota_exp2_naive_arm"),
        optimised_dir=Path("experiments/outputs/sota_exp2_brerun1"),
        cross_eval_csv=Path("experiments/derived/sota_cross_eval.csv"),
        repo_root=repo_root,
    )

    assert len(records) == 4
    assert any(record.record_kind == "score" for record in records)


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
        _write_json(
            probe_dir / "anthropic_turn_01.raw.json",
            {"content": [{"type": "text", "text": "| A | 1 |\n"}]},
        )

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
        if record.record_kind == "run"
        and record.arm == "naive"
        and record.model == "mistral-large-2512"
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


def test_build_exp2_mart_includes_arm3_and_arm4(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    arm3_dir = tmp_path / "arm3"
    arm4_dir = tmp_path / "arm4"
    for d in (naive_dir, optimised_dir, arm3_dir, arm4_dir):
        d.mkdir()

    table = (
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| A | Coal | 1 | Operating | 1983 | HN |\n"
    )
    for arm_dir in (naive_dir, optimised_dir, arm3_dir, arm4_dir):
        _write_json(
            arm_dir / "anthropic_run01.json",
            {
                "model": "claude-opus-4-6",
                "run": 1,
                "classification": "report",
                "narrative_chars": 4,
            },
        )
        _write_md(arm_dir / "anthropic_run01.md", table)

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [
            _score_row("naive", "claude-opus-4-6", 1),
            _score_row("optimised", "claude-opus-4-6", 1),
            _score_row("arm3", "claude-opus-4-6", 1),
            _score_row("arm4", "claude-opus-4-6", 1),
        ],
    )

    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        arm3_dir=arm3_dir,
        arm4_dir=arm4_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    arms_with_run = {r.arm for r in records if r.record_kind == "run"}
    arms_with_score = {r.arm for r in records if r.record_kind == "score"}
    assert arms_with_run == {"naive", "optimised", "arm3", "arm4"}
    assert arms_with_score == {"naive", "optimised", "arm3", "arm4"}

    # Single-turn arms (naive, arm3) default turns=1; multi-turn arms leave it unset.
    arm3_run = next(r for r in records if r.record_kind == "run" and r.arm == "arm3")
    arm4_run = next(r for r in records if r.record_kind == "run" and r.arm == "arm4")
    assert arm3_run.run_summary.turns == 1
    assert arm4_run.run_summary.turns is None


def test_build_exp2_mart_falls_back_to_agent_for_null_model(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    arm4_dir = tmp_path / "arm4"
    for d in (naive_dir, optimised_dir, arm4_dir):
        d.mkdir()

    # model: null is a real extraction artifact in arm4 mistral/qwen run01.
    _write_json(
        arm4_dir / "mistral_run01.json", {"model": None, "run": 1, "classification": "report"}
    )
    _write_md(
        arm4_dir / "mistral_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| A | Coal | 1 | Operating | 1983 | HN |\n",
    )

    _write_cross_eval_csv(tmp_path / "sota_cross_eval.csv", [_score_row("naive", "x", 99)])

    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        arm4_dir=arm4_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    arm4_run = next(r for r in records if r.record_kind == "run" and r.arm == "arm4")
    # No model in metadata → record falls back to the agent name, stays valid,
    # and carries no paired score record.
    assert arm4_run.model == "mistral"
    assert not any(r.record_kind == "score" and r.arm == "arm4" for r in records)


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
