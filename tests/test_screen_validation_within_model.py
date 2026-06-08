"""Tests for aedist.screen_validation_within_model — within-model screen validation."""

import csv
from pathlib import Path

import pytest

from aedist.screen_validation_within_model import (
    _stratified_kendall_tau,
    within_model_accuracy_gap,
)


def _make_run(model: str, run: int, cap_distinct: int, status_distinct: int, f1: float | None):
    vetoed = cap_distinct <= 4 or status_distinct <= 1
    return {
        "model": model,
        "run": run,
        "cap_distinct": cap_distinct,
        "status_distinct": status_distinct,
        "vetoed": vetoed,
        "f1": f1,
    }


def test_within_model_stratification_removes_across_model_signal():
    """Two models, each with vetoed (low-F1) and surviving (high-F1) runs.

    A naive across-model correlation would be inflated by the model gap;
    the within-model statistic must isolate the run-grain effect.
    """
    # Model A: consistently good model — two strong runs, one degenerate run
    # Model B: consistently weak model — two weak runs, one slightly better run
    rows = [
        # Model A: strong model — degenerate run has low F1, strong runs have high F1
        _make_run("model-A", 1, cap_distinct=2, status_distinct=2, f1=0.05),  # vetoed, low F1
        _make_run("model-A", 2, cap_distinct=15, status_distinct=6, f1=0.60),  # surviving, high F1
        _make_run("model-A", 3, cap_distinct=18, status_distinct=7, f1=0.65),  # surviving, high F1
        # Model B: weak model — most runs degenerate, one slightly less bad
        _make_run("model-B", 1, cap_distinct=1, status_distinct=1, f1=0.01),  # vetoed, very low F1
        _make_run("model-B", 2, cap_distinct=3, status_distinct=2, f1=0.03),  # vetoed, low F1
        _make_run("model-B", 3, cap_distinct=5, status_distinct=3, f1=0.12),  # surviving, slightly better
    ]

    stat = within_model_accuracy_gap(rows)

    assert stat.is_within_model  # strata are (model,) not pooled
    assert stat.vetoed_mean_f1 is not None
    assert stat.surviving_mean_f1 is not None
    assert stat.vetoed_mean_f1 < stat.surviving_mean_f1
    assert stat.n_mixed_models == 2  # both models have mixed runs


def test_within_model_all_vetoed_one_model():
    """A model with all runs vetoed contributes to pooled stats but not to binary gap."""
    rows = [
        _make_run("all-vetoed", 1, cap_distinct=1, status_distinct=1, f1=0.00),
        _make_run("all-vetoed", 2, cap_distinct=2, status_distinct=1, f1=0.02),
        _make_run("mixed", 1, cap_distinct=2, status_distinct=2, f1=0.05),  # vetoed
        _make_run("mixed", 2, cap_distinct=10, status_distinct=5, f1=0.45),  # surviving
    ]

    stat = within_model_accuracy_gap(rows)

    assert stat.n_mixed_models == 1  # only "mixed" contributes
    assert stat.is_within_model


def test_stratified_kendall_tau_perfectly_concordant():
    """All pairs concordant within a model → tau = +1.0."""
    model_groups = {
        "m1": [
            {"cap_distinct": 1, "f1": 0.1},
            {"cap_distinct": 5, "f1": 0.3},
            {"cap_distinct": 10, "f1": 0.6},
        ]
    }
    tau, concordant, discordant = _stratified_kendall_tau(model_groups, "cap_distinct")
    assert tau == pytest.approx(1.0)
    assert concordant == 3  # C(3,2) = 3 pairs
    assert discordant == 0


def test_stratified_kendall_tau_perfectly_discordant():
    """All pairs discordant within a model → tau = -1.0."""
    model_groups = {
        "m1": [
            {"cap_distinct": 10, "f1": 0.1},
            {"cap_distinct": 5, "f1": 0.3},
            {"cap_distinct": 1, "f1": 0.6},
        ]
    }
    tau, concordant, discordant = _stratified_kendall_tau(model_groups, "cap_distinct")
    assert tau == pytest.approx(-1.0)
    assert concordant == 0
    assert discordant == 3


def test_stratified_kendall_tau_cross_model_cancellation():
    """Pairs are counted only within each model's runs, not across models.

    If model A has perfectly concordant pairs and model B perfectly discordant,
    the net tau is 0 — the across-model confound is removed.
    """
    model_groups = {
        "concordant": [
            {"cap_distinct": 1, "f1": 0.1},
            {"cap_distinct": 5, "f1": 0.5},
        ],
        "discordant": [
            {"cap_distinct": 5, "f1": 0.1},
            {"cap_distinct": 1, "f1": 0.5},
        ],
    }
    tau, concordant, discordant = _stratified_kendall_tau(model_groups, "cap_distinct")
    assert tau == pytest.approx(0.0)
    assert concordant == 1
    assert discordant == 1


def test_is_within_model_flag():
    """WithinModelAccuracyGap.is_within_model must always be True."""
    stat = within_model_accuracy_gap([])
    assert stat.is_within_model is True


@pytest.mark.adherence
def test_within_model_script_has_argparse():
    """screen_validation_within_model.py must expose --exp1-dir, --cross-eval, --output."""
    src = (
        Path(__file__).parent.parent
        / "src"
        / "aedist"
        / "screen_validation_within_model.py"
    )
    text = src.read_text(encoding="utf-8")
    for flag in ("--exp1-dir", "--cross-eval", "--output"):
        assert flag in text, f"Missing CLI flag: {flag}"


def test_run_analysis_produces_csv(tmp_path: Path):
    """run_analysis writes a CSV with the expected metric rows."""
    # Build synthetic exp1 dir: two models, 2 runs each
    exp1_dir = tmp_path / "exp1"
    exp1_dir.mkdir()

    # strong-model: both runs surviving (cap_distinct > 4)
    for run in (1, 2):
        f = exp1_dir / f"strong-model-run{run}.csv"
        rows = [{"name": f"Plant {i}", "capacity_mwe": str(100 + i * 10), "status": "Operating" if i % 2 else "Planned"}
                for i in range(20)]
        with f.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["name", "capacity_mwe", "status"])
            writer.writeheader()
            writer.writerows(rows)

    # weak-model: run1 vetoed (all same capacity), run2 also vetoed
    for run in (1, 2):
        f = exp1_dir / f"weak-model-run{run}.csv"
        rows = [{"name": f"Fake {i}", "capacity_mwe": "600.0", "status": "Operating"}
                for i in range(20)]
        with f.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["name", "capacity_mwe", "status"])
            writer.writeheader()
            writer.writerows(rows)

    # cross-eval CSV with F1 values
    cross_eval = tmp_path / "exp1_cross_eval.csv"
    with cross_eval.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["model", "run", "accuracy_f1"])
        writer.writeheader()
        writer.writerows([
            {"model": "strong-model", "run": "1", "accuracy_f1": "0.60"},
            {"model": "strong-model", "run": "2", "accuracy_f1": "0.65"},
            {"model": "weak-model", "run": "1", "accuracy_f1": "0.05"},
            {"model": "weak-model", "run": "2", "accuracy_f1": "0.03"},
        ])

    from aedist.screen_validation_within_model import run_analysis

    output = tmp_path / "out.csv"
    run_analysis(exp1_dir, cross_eval, output)

    assert output.exists()
    with output.open() as fh:
        rows_out = list(csv.DictReader(fh))
    metrics = {r["metric"] for r in rows_out}
    assert "stratified_kendall_tau_cap_distinct" in metrics
    assert "stratified_kendall_tau_status_distinct" in metrics
    assert "pooled_vetoed_mean_f1" in metrics
    assert "pooled_surviving_mean_f1" in metrics


def test_stratified_tau_ignores_runs_with_no_f1():
    """Runs with f1=None must be excluded from the tau computation."""
    model_groups = {
        "m1": [
            {"cap_distinct": 5, "f1": None},  # no F1 — should be excluded
            {"cap_distinct": 3, "f1": 0.1},
            {"cap_distinct": 10, "f1": 0.4},
        ]
    }
    tau, concordant, discordant = _stratified_kendall_tau(model_groups, "cap_distinct")
    # Only 1 pair: (3, 0.1) vs (10, 0.4) → concordant
    assert concordant == 1
    assert discordant == 0
    assert tau == pytest.approx(1.0)
