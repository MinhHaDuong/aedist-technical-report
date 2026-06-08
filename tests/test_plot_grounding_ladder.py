"""Tests for aedist.plot_grounding_ladder — within-agent paired deltas."""

from pathlib import Path

import pytest

from aedist.plot_exp2_arms_split import _AGENT_EXP1_SLUG
from aedist.plot_grounding_ladder import (
    _AGENT_ORDER,
    _LADDER_RUNGS,
    LadderStep,
    ladder_agents,
    ladder_deltas,
    load_rung_means,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXP1_CSV = _REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv"
_EXP2_CSV = _REPO_ROOT / "experiments" / "derived" / "sota_cross_eval.csv"


def test_restricted_to_shared_four_agents():
    """Exactly the 4 agents present in both Exp1 and Exp2."""
    assert set(ladder_agents()) == set(_AGENT_EXP1_SLUG)


def test_deltas_are_within_agent_paired():
    """Each rung delta is computed within one agent, never pooled across agents."""
    # Build minimal rung_means with 2 agents, 2 rungs, 1 metric.
    rung_means = {
        "anthropic": {
            "e1": {"accuracy_f1": 0.6},
            "arm1": {"accuracy_f1": 0.7},
        },
        "openai": {
            "e1": {"accuracy_f1": 0.5},
            "arm1": {"accuracy_f1": 0.8},
        },
    }
    steps = ladder_deltas(rung_means, metrics=["accuracy_f1"])
    assert all(step.agent is not None for step in steps)
    # Each step must carry its own agent — no None, no cross-agent mixing.
    agent_set = {step.agent for step in steps}
    assert agent_set.issubset({"anthropic", "openai"})


def test_delta_values_are_within_agent():
    """Delta is to_value − from_value for the same agent."""
    rung_means = {
        "anthropic": {
            "e1": {"accuracy_f1": 0.60},
            "arm1": {"accuracy_f1": 0.65},
            "arm3": {"accuracy_f1": 0.70},
            "arm4": {"accuracy_f1": 0.68},
        },
        "mistral": {
            "e1": {"accuracy_f1": 0.40},
            "arm1": {"accuracy_f1": 0.50},
            "arm3": {"accuracy_f1": 0.55},
            "arm4": {"accuracy_f1": 0.53},
        },
    }
    steps = ladder_deltas(rung_means, metrics=["accuracy_f1"])

    for step in steps:
        assert isinstance(step, LadderStep), f"expected LadderStep, got {type(step)}"
        expected_delta = step.to_value - step.from_value
        assert abs(step.delta - expected_delta) < 1e-9, (
            f"delta mismatch for {step.agent}/{step.from_rung}→{step.to_rung}: "
            f"delta={step.delta}, to-from={expected_delta}"
        )


def test_ladder_rungs_order():
    """Ladder uses E1→1N(arm1)→1D(arm3)→5D(arm4) — arm2 (5N) excluded."""
    assert _LADDER_RUNGS == ["e1", "arm1", "arm3", "arm4"]
    assert "arm2" not in _LADDER_RUNGS


def test_agent_order_matches_exp2_arms_split():
    """_AGENT_ORDER matches the keys of _AGENT_EXP1_SLUG."""
    assert set(_AGENT_ORDER) == set(_AGENT_EXP1_SLUG)


@pytest.mark.slow
def test_load_rung_means_four_agents_four_rungs():
    """Integration: all 4 agents have data for all 4 rungs on real CSVs."""
    rung_means = load_rung_means(_EXP1_CSV, _EXP2_CSV)
    for agent in _AGENT_EXP1_SLUG:
        assert agent in rung_means, f"missing agent {agent}"
        for rung in _LADDER_RUNGS:
            assert rung in rung_means[agent], f"missing rung {rung} for agent {agent}"
            assert len(rung_means[agent][rung]) > 0, f"no metrics for {agent}/{rung}"


@pytest.mark.slow
def test_regenerates_pdf(tmp_path):
    """Integration: figure script produces a non-empty PDF from the real CSVs."""
    from aedist.plot_grounding_ladder import make_figure

    out = tmp_path / "fig_grounding_ladder.pdf"
    make_figure(_EXP1_CSV, _EXP2_CSV, out)
    assert out.exists(), "output PDF not written"
    assert out.stat().st_size > 10_000, "PDF suspiciously small"
