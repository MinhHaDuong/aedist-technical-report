"""Tests for tabulate_base_vs_census: per-model census/base F1 and bootstrap CI."""

import json
from pathlib import Path

import pytest

from tests.conftest import patch_measurements_loader, write_measurements


def _write_p1_base_record(
    out_dir: Path,
    model: str,
    run: int,
    tp: int,
    fp: int,
    fn: int,
    tokens_in: int,
) -> None:
    """Synthesize a p1_base *.record.json file matching the real schema."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{model.split('/')[-1]}-run{run}"
    n_plants = tp + fp
    precision = tp / n_plants if n_plants else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    record = {
        "run_id": f"test{model[:4]}{run}",
        "timestamp": "2026-04-11T00:00:00Z",
        "method": "single",
        "method_params": {
            "model": model,
            "prompt_version": "p1_base",
        },
        "resource_use": {
            "wall_s": 10.0,
            "cost_usd": 0.001,
            "tokens_in": tokens_in,
            "tokens_out": 1000,
        },
        "result_file": f"experiments/outputs/ablation/parametric/p1_base/{stem}.csv",
        "result_summary": {
            "status": "ok",
            "n_plants": n_plants,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "f1": round(f1, 4),
        },
    }
    (out_dir / f"{stem}.record.json").write_text(json.dumps(record))


def _prf1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


@pytest.fixture
def synthetic_fixture(tmp_path, monkeypatch):
    """2 models x (2 census runs + 2 p1_base runs) with known tp/fp/fn."""
    meas = tmp_path / "measurements.jsonl"
    # Census: 2 runs per model. Lower F1 than base (for H1 direction).
    census_rows = [
        {"label": "census/alpha-run1", "n_matched": 40, "n_hallucinated": 10, "n_missed": 50},
        {"label": "census/alpha-run2", "n_matched": 42, "n_hallucinated": 8, "n_missed": 48},
        {"label": "census/beta-run1", "n_matched": 30, "n_hallucinated": 20, "n_missed": 60},
        {"label": "census/beta-run2", "n_matched": 32, "n_hallucinated": 18, "n_missed": 58},
    ]
    write_measurements(meas, census_rows)
    patch_measurements_loader(monkeypatch, meas)

    # p1_base records: 2 runs per model, better F1 than census.
    p1_dir = tmp_path / "p1_base"
    _write_p1_base_record(p1_dir, "alpha", 1, tp=60, fp=5, fn=30, tokens_in=500)
    _write_p1_base_record(p1_dir, "alpha", 2, tp=58, fp=7, fn=32, tokens_in=510)
    _write_p1_base_record(p1_dir, "beta", 1, tp=50, fp=15, fn=40, tokens_in=520)
    _write_p1_base_record(p1_dir, "beta", 2, tp=52, fp=13, fn=38, tokens_in=530)

    return {"meas": meas, "p1_dir": p1_dir}


def test_analytic_per_model_metrics(synthetic_fixture):
    from aedist.tabulate_base_vs_census import compute_table

    table = compute_table(p1_base_dir=synthetic_fixture["p1_dir"])
    by_model = {row["slug"]: row for row in table["rows"]}
    assert set(by_model.keys()) == {"alpha", "beta"}

    # Alpha census run values
    p1c, r1c, f1_1c = _prf1(40, 10, 50)
    p2c, r2c, f2_2c = _prf1(42, 8, 48)
    alpha_f1_census = (f1_1c + f2_2c) / 2
    # Alpha base
    p1b, r1b, f1_1b = _prf1(60, 5, 30)
    p2b, r2b, f2_2b = _prf1(58, 7, 32)
    alpha_f1_base = (f1_1b + f2_2b) / 2

    row = by_model["alpha"]
    assert row["f1_census"] == pytest.approx(alpha_f1_census, abs=1e-4)
    assert row["f1_base"] == pytest.approx(alpha_f1_base, abs=1e-4)
    assert row["delta_f1"] == pytest.approx(alpha_f1_base - alpha_f1_census, abs=1e-4)
    assert row["p_census"] == pytest.approx((p1c + p2c) / 2, abs=1e-4)
    assert row["r_base"] == pytest.approx((r1b + r2b) / 2, abs=1e-4)


def test_macro_bootstrap_ci_contains_mean(synthetic_fixture):
    from aedist.tabulate_base_vs_census import compute_table

    table = compute_table(p1_base_dir=synthetic_fixture["p1_dir"])
    mean = table["delta_f1_mean"]
    lo = table["delta_f1_ci_low"]
    hi = table["delta_f1_ci_high"]
    assert lo <= mean <= hi


def test_cli_writes_tex(synthetic_fixture, tmp_path):
    from aedist.tabulate_base_vs_census import main

    out = tmp_path / "tab_base_vs_census.tex"
    main(
        [
            "--output",
            str(out),
            "--p1-base-dir",
            str(synthetic_fixture["p1_dir"]),
        ]
    )
    text = out.read_text()
    assert "tabular" in text
    assert "alpha" in text.lower() or "Alpha" in text
    assert "n=2" in text or "underpower" in text.lower() or "n{=}2" in text


def test_exit_on_too_few_models(tmp_path, monkeypatch):
    from aedist.tabulate_base_vs_census import main

    meas = tmp_path / "measurements.jsonl"
    write_measurements(
        meas,
        [{"label": "census/alpha-run1", "n_matched": 10, "n_hallucinated": 1, "n_missed": 5}],
    )
    patch_measurements_loader(monkeypatch, meas)

    p1_dir = tmp_path / "p1_base"
    _write_p1_base_record(p1_dir, "alpha", 1, tp=20, fp=2, fn=10, tokens_in=500)

    out = tmp_path / "tab.tex"
    with pytest.raises(SystemExit):
        main(["--output", str(out), "--p1-base-dir", str(p1_dir)])
