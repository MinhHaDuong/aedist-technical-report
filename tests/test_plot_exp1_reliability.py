"""Tests for the reliability-vs-accuracy screen figure (ticket 0506).

Unit tests pin the gate semantics (good run = no zero on any of the 12
reference-free dimensions; missing score = skip, not a doubt).  Adherence
tests re-derive the floor membership, the empty accurate-but-unreliable
quadrant, and one sensitivity-sweep cell from the committed artifacts —
never from ticket predictions (writing rule: numbers come from artifacts).
"""

import csv
from pathlib import Path

import pytest

from aedist.plot_exp1_reliability import (
    DIMENSIONS_ALL,
    DIMENSIONS_COHERENCE,
    GATE_TAU,
    discriminating_dimensions,
    is_good_run,
    load_rows,
    mean_f1_good_by_model,
    reliability_by_model,
    sensitivity_sweep,
    spearman,
)

CROSS_EVAL_CSV = Path("experiments/derived/exp1_cross_eval.csv")
SENSITIVITY_CSV = Path("experiments/derived/exp1_reliability_sensitivity.csv")


def _row(**overrides: str) -> dict[str, str]:
    """A synthetic run row that clears every reference-free dimension."""
    base = {dim: "1.0" for dim in DIMENSIONS_ALL}
    base["coherence_run_veto"] = "0"  # inverted polarity: 0 = passed the screen
    base.update(overrides)
    return base


# ── Gate semantics ───────────────────────────────────────────────────────────


def test_gate_constants() -> None:
    assert len(DIMENSIONS_ALL) == 12
    assert len(DIMENSIONS_COHERENCE) == 3
    assert set(DIMENSIONS_COHERENCE) <= set(DIMENSIONS_ALL)
    assert GATE_TAU == 0.0


def test_good_run_all_clear() -> None:
    assert is_good_run(_row())


def test_one_zero_taints_the_whole_run() -> None:
    """One doubt taints the run — the gate is a minimum, not an average."""
    for dim in DIMENSIONS_ALL:
        bad = "1" if dim == "coherence_run_veto" else "0.0"
        assert not is_good_run(_row(**{dim: bad})), dim


def test_missing_score_is_skipped_not_a_doubt() -> None:
    """Missing score = skip (only high_conf_dual_source is ever missing)."""
    assert is_good_run(_row(provenance_high_conf_dual_source=""))


@pytest.mark.adherence
def test_only_high_conf_dual_source_is_ever_missing() -> None:
    """The skip rule is sanctioned for exactly one column (ticket 0506).
    If any other dimension develops empty cells, good-run counts would
    silently inflate — fail loudly instead."""
    rows = load_rows(CROSS_EVAL_CSV)
    others = [d for d in DIMENSIONS_ALL if d != "provenance_high_conf_dual_source"]
    for row in rows:
        for dim in others:
            assert (row.get(dim) or "").strip(), (
                f"{dim} unexpectedly missing for {row.get('model')} run {row.get('run')}"
            )


def test_nonzero_low_score_passes_at_tau_zero() -> None:
    assert is_good_run(_row(coherence_vocab_adherence="0.05"))


def test_tau_raises_the_bar() -> None:
    row = _row(coherence_vocab_adherence="0.05")
    assert is_good_run(row, tau=0.0)
    assert not is_good_run(row, tau=0.1)


def test_coherence_only_gate_ignores_other_dimensions() -> None:
    row = _row(provenance_source_diversity="0.0")
    assert not is_good_run(row)
    assert is_good_run(row, dims=DIMENSIONS_COHERENCE)


# ── Aggregations on the real CSV ─────────────────────────────────────────────


@pytest.mark.adherence
def test_reliability_is_integer_count_0_to_5() -> None:
    rel = reliability_by_model(CROSS_EVAL_CSV)
    assert len(rel) == 14
    assert all(isinstance(n, int) and 0 <= n <= 5 for n in rel.values())


@pytest.mark.adherence
def test_mean_f1_covers_every_model() -> None:
    f1 = mean_f1_good_by_model(CROSS_EVAL_CSV)
    assert set(f1) == set(reliability_by_model(CROSS_EVAL_CSV))
    assert all(0.0 <= v <= 1.0 for v in f1.values())


@pytest.mark.adherence
def test_floor_is_the_inaccurate_models() -> None:
    """Models with <=1 good run are exactly the low-F1 models; the
    accurate-but-unreliable quadrant is empty (post-0505)."""
    rel = reliability_by_model(CROSS_EVAL_CSV)
    f1 = mean_f1_good_by_model(CROSS_EVAL_CSV)
    floor = {m for m, n in rel.items() if n <= 1}
    assert floor  # the screen separates someone
    assert all(f1[m] < 0.30 for m in floor)  # floor == inaccurate
    assert not any(rel[m] <= 1 and f1[m] > 0.45 for m in rel)  # no accurate-unreliable


@pytest.mark.adherence
def test_screen_is_bimodal() -> None:
    """No model sits in the middle columns (2-3) — the screening cut."""
    rel = reliability_by_model(CROSS_EVAL_CSV)
    assert not any(n in (2, 3) for n in rel.values())


# ── Spearman helper ──────────────────────────────────────────────────────────


def test_spearman_perfect_monotone() -> None:
    assert spearman([1, 2, 3, 4], [0.1, 0.2, 0.3, 0.4]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [0.4, 0.3, 0.2, 0.1]) == pytest.approx(-1.0)


# ── Adherence: artifacts are the source of truth ─────────────────────────────


@pytest.mark.adherence
def test_sensitivity_artifact_matches_rederivation() -> None:
    """Self-consistency check: the committed sweep artifact must match a fresh
    sweep over the source CSV (guards against artifact staleness), plus one
    pinned literal so a systematic sweep bug cannot validate its own output."""
    assert SENSITIVITY_CSV.exists(), "sensitivity sweep artifact not committed"
    with SENSITIVITY_CSV.open(newline="", encoding="utf-8") as fh:
        cells = list(csv.DictReader(fh))
    # Full grid: 4 tau values x 3 indicator sets.
    assert len(cells) == 12

    rows = load_rows(CROSS_EVAL_CSV)
    fresh = {(c["indicator_set"], c["tau"]): c for c in sensitivity_sweep(rows)}
    for cell in cells:
        key = (cell["indicator_set"], cell["tau"])
        assert key in fresh, key
        assert cell["n_dims"] == fresh[key]["n_dims"], key
        assert cell["n_disqualified"] == fresh[key]["n_disqualified"], key
        assert cell["equals_floor"] == fresh[key]["equals_floor"], key
        assert float(cell["spearman"]) == pytest.approx(
            float(fresh[key]["spearman"]), abs=1e-6
        ), key

    # The baseline cell (12 dims, tau=0) IS the main-figure floor.
    base = next(c for c in cells if c["indicator_set"] == "all_reference_free" and float(c["tau"]) == 0.0)
    # Pinned from the committed artifact (independent of sensitivity_sweep):
    # a sweep bug regenerating a wrong CSV cannot satisfy this literal.
    assert float(base["spearman"]) == pytest.approx(0.7817, abs=5e-5)
    rel = reliability_by_model(CROSS_EVAL_CSV)
    floor = {m for m, n in rel.items() if n <= 1}
    assert set(base["disqualified_models"].split(";")) == floor
    assert base["equals_floor"] == "yes"


@pytest.mark.adherence
def test_coherence_only_gate_is_insufficient() -> None:
    """The annex headline: the 3-dim coherence-only gate must NOT reproduce
    the full-gate floor at tau=0 — the reference-free conjunction does the work."""
    with SENSITIVITY_CSV.open(newline="", encoding="utf-8") as fh:
        cells = list(csv.DictReader(fh))
    coh = next(
        c for c in cells if c["indicator_set"] == "coherence_only" and float(c["tau"]) == 0.0
    )
    assert coh["equals_floor"] == "no"


@pytest.mark.adherence
def test_discriminating_dimensions_are_reference_free_subset() -> None:
    rows = load_rows(CROSS_EVAL_CSV)
    disc = discriminating_dimensions(rows)
    assert set(disc) < set(DIMENSIONS_ALL)
    assert len(disc) >= 5
