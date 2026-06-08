"""Unit tests for aedist.plot_fusion_mvp — naive presence fusion rules.

Tests only the pure merge functions; no I/O, no LLM calls, no real data.
Adherence tests guard the committed CSV artifact against macro drift.
"""

import csv
from pathlib import Path

import pytest

from aedist.plot_fusion_mvp import FusedSet, at_least_2_models_fuse, union_fuse

_CSV_READER = csv.DictReader  # keep import live for ruff

_CSV_PATH = Path("report/inputs/generated/fusion_mvp.csv")

# ---------------------------------------------------------------------------
# Synthetic fixture
# ---------------------------------------------------------------------------


def _run(model: str, tp_plants: set[str], fp_plants: set[str]) -> dict:
    """Return a minimal run dict for fusion tests."""
    return {"model": model, "tp_plants": tp_plants, "fp_plants": fp_plants}


def synthetic_runs() -> list[dict]:
    """Tiny multi-model, multi-run fixture.

    Model A, run1: detects P1 and P2; hallucinates H1
    Model A, run2: detects P1 (same model again — must count once for ≥2-models);
                   hallucinates H2
    Model B, run1: detects P2 and P3; hallucinates H1 (same FP as model A, run1)
    Model C, run1: detects P3 only; no hallucinations

    Expected UNION TP:      {P1, P2, P3}      (≥1 any model, same for UNION FP)
    Expected UNION FP:      {H1, H2}          (H1 from A+B, H2 from A only)
    Expected ≥2-models TP:  {P2, P3}          (P1 only by model A; P2 by A+B; P3 by B+C)
    Expected ≥2-models FP:  {H1}              (H1 by A+B; H2 only by A)
    """
    return [
        _run("model_a", {"P1", "P2"}, {"H1"}),
        _run("model_a", {"P1"}, {"H2"}),   # same model — counts once for ≥2 rule
        _run("model_b", {"P2", "P3"}, {"H1"}),
        _run("model_c", {"P3"}, set()),
    ]


# ---------------------------------------------------------------------------
# Tests for union_fuse
# ---------------------------------------------------------------------------


def test_union_fuse_tp_set():
    runs = synthetic_runs()
    result = union_fuse(runs)
    assert result.tp_plants == {"P1", "P2", "P3"}


def test_union_fuse_fp_set():
    runs = synthetic_runs()
    result = union_fuse(runs)
    assert result.fp_plants == {"H1", "H2"}


def test_union_fuse_empty_runs():
    result = union_fuse([])
    assert result.tp_plants == set()
    assert result.fp_plants == set()


def test_union_fuse_single_run():
    runs = [_run("model_a", {"P1", "P2"}, {"H1"})]
    result = union_fuse(runs)
    assert result.tp_plants == {"P1", "P2"}
    assert result.fp_plants == {"H1"}


# ---------------------------------------------------------------------------
# Tests for at_least_2_models_fuse
# ---------------------------------------------------------------------------


def test_at_least_2_models_fuse_tp_set():
    """P2 detected by model_a and model_b; P3 by model_b and model_c → both pass."""
    runs = synthetic_runs()
    result = at_least_2_models_fuse(runs)
    assert result.tp_plants == {"P2", "P3"}


def test_at_least_2_models_fuse_fp_set():
    """H1 hallucinated by model_a and model_b → passes; H2 only by model_a → dropped."""
    runs = synthetic_runs()
    result = at_least_2_models_fuse(runs)
    assert result.fp_plants == {"H1"}


def test_at_least_2_models_same_model_counts_once():
    """Two runs of the same model do NOT count as two distinct models."""
    runs = [
        _run("model_a", {"P1"}, {"H1"}),
        _run("model_a", {"P1"}, {"H1"}),  # same model, 2nd run
    ]
    result = at_least_2_models_fuse(runs)
    # P1 and H1 only seen by one distinct model → excluded
    assert result.tp_plants == set()
    assert result.fp_plants == set()


def test_at_least_2_models_fuse_empty_runs():
    result = at_least_2_models_fuse([])
    assert result.tp_plants == set()
    assert result.fp_plants == set()


def test_at_least_2_models_exactly_two():
    """Exactly two distinct models → items included."""
    runs = [
        _run("model_x", {"P1", "P2"}, {"H1"}),
        _run("model_y", {"P1"}, {"H1"}),
    ]
    result = at_least_2_models_fuse(runs)
    assert result.tp_plants == {"P1"}
    assert result.fp_plants == {"H1"}


# ---------------------------------------------------------------------------
# Tests for FusedSet dataclass
# ---------------------------------------------------------------------------


def test_fused_set_f1_perfect():
    fs = FusedSet(tp_plants={"P1", "P2"}, fp_plants=set(), n_reference=2)
    assert fs.recall == pytest.approx(1.0)
    assert fs.precision == pytest.approx(1.0)
    assert fs.f1 == pytest.approx(1.0)


def test_fused_set_f1_zero_recall():
    fs = FusedSet(tp_plants=set(), fp_plants={"H1"}, n_reference=2)
    assert fs.recall == pytest.approx(0.0)
    assert fs.f1 == pytest.approx(0.0)


def test_fused_set_f1_zero_precision():
    """All system plants are FP → precision=0, f1=0."""
    fs = FusedSet(tp_plants=set(), fp_plants={"H1", "H2"}, n_reference=2)
    assert fs.precision == pytest.approx(0.0)
    assert fs.f1 == pytest.approx(0.0)


def test_fused_set_f1_mixed():
    """1 TP, 1 FP, 2 reference → recall=0.5, precision=0.5, f1=0.5."""
    fs = FusedSet(tp_plants={"P1"}, fp_plants={"H1"}, n_reference=2)
    assert fs.recall == pytest.approx(0.5)
    assert fs.precision == pytest.approx(0.5)
    assert fs.f1 == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Adherence: committed CSV artifact must match expected regime/rule rows
# ---------------------------------------------------------------------------


@pytest.mark.adherence
class TestFusionMvpCsvAdherence:
    """Guard the committed fusion_mvp.csv against drift.

    Re-derives values by independent CSV parse (no script import — anti-tautology).
    """

    def _load_csv(self) -> dict[tuple[str, str], dict]:
        """Load CSV as {(regime, rule): row} mapping."""
        if not _CSV_PATH.exists():
            pytest.skip("fusion_mvp.csv not yet generated")
        with _CSV_PATH.open() as fh:
            rows = list(csv.DictReader(fh))
        return {(r["regime"], r["rule"]): r for r in rows}

    def test_csv_has_expected_regimes_and_rules(self):
        data = self._load_csv()
        for regime in ("E1", "E2-1D"):
            for rule in ("best_single", "union", "r2_models"):
                assert (regime, rule) in data, f"Missing row ({regime!r}, {rule!r}) in CSV"

    def test_e1_union_recall_exceeds_best_single(self):
        """UNION must recall more than best single (by design: union ≥ any member)."""
        data = self._load_csv()
        union_recall = float(data[("E1", "union")]["recall"])
        best_recall = float(data[("E1", "best_single")]["recall"])
        assert union_recall >= best_recall, (
            f"E1 UNION recall {union_recall:.4f} < best_single recall {best_recall:.4f}"
        )

    def test_e1_union_precision_less_than_best_single(self):
        """UNION precision must be lower (pooling many models inflates FP)."""
        data = self._load_csv()
        union_prec = float(data[("E1", "union")]["precision"])
        best_prec = float(data[("E1", "best_single")]["precision"])
        assert union_prec < best_prec, (
            f"E1 UNION precision {union_prec:.4f} not < best_single {best_prec:.4f}"
        )

    def test_r2_f1_exceeds_best_single_for_e1(self):
        """R2 ≥2-models F1 should exceed best-single F1 for E1 (ticket 0473 claim)."""
        data = self._load_csv()
        r2_f1 = float(data[("E1", "r2_models")]["f1"])
        best_f1 = float(data[("E1", "best_single")]["f1"])
        assert r2_f1 > best_f1, (
            f"E1 R2 F1 {r2_f1:.4f} not > best_single F1 {best_f1:.4f}"
        )

    def test_e1_n_runs(self):
        """E1 must have 20 valid runs (4 SOTA models × 5 reps)."""
        data = self._load_csv()
        n_runs = int(data[("E1", "union")]["n_runs"])
        assert n_runs == 20, f"Expected 20 E1 runs (4 SOTA models × 5 reps), got {n_runs}"

    def test_csv_has_tp_fp_columns(self):
        """CSV must include tp and fp columns for all rows."""
        if not _CSV_PATH.exists():
            pytest.skip("fusion_mvp.csv not yet generated")
        with _CSV_PATH.open() as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            assert "tp" in row, f"Missing 'tp' column in row {row}"
            assert "fp" in row, f"Missing 'fp' column in row {row}"
            # tp and fp must be non-negative numbers
            assert float(row["tp"]) >= 0, f"Negative tp in row {row}"
            assert float(row["fp"]) >= 0, f"Negative fp in row {row}"

    def test_e2_n_runs(self):
        """E2-1D must have 20 valid runs (4 models × 5 reps)."""
        data = self._load_csv()
        n_runs = int(data[("E2-1D", "union")]["n_runs"])
        assert n_runs == 20, f"Expected 20 E2-1D runs, got {n_runs}"

    def test_f1_values_in_range(self):
        """All F1 values must be in [0, 1]."""
        data = self._load_csv()
        for key, row in data.items():
            f1 = float(row["f1"])
            assert 0.0 <= f1 <= 1.0, f"F1 out of range for {key}: {f1}"
