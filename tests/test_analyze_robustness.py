"""Tests for aedist.analyze_robustness — joint robustness summary."""

from aedist.analyze_robustness import analyze_robustness


def test_low_residual_message():
    """When eta_sq_residual < 0.10, summary says rankings are stable."""
    decomp = {
        "eta_sq_model": 0.45,
        "eta_sq_method": 0.38,
        "eta_sq_interaction": 0.12,
        "eta_sq_residual": 0.05,
        "unstable_pairs": [],
    }
    result = analyze_robustness(decomp, threshold_sensitivity=None)
    assert "stable" in result["summary"].lower() or "<10\\%" in result["summary"]


def test_high_residual_message():
    """When eta_sq_residual >= 0.10, summary warns about noise."""
    decomp = {
        "eta_sq_model": 0.30,
        "eta_sq_method": 0.25,
        "eta_sq_interaction": 0.10,
        "eta_sq_residual": 0.35,
        "unstable_pairs": [],
    }
    result = analyze_robustness(decomp, threshold_sensitivity=None)
    assert "noise" in result["summary"].lower() or "caution" in result["summary"].lower()


def test_unstable_pairs_flagged():
    """Unstable pairs from decomposition appear in robustness summary."""
    decomp = {
        "eta_sq_model": 0.40,
        "eta_sq_method": 0.35,
        "eta_sq_interaction": 0.15,
        "eta_sq_residual": 0.10,
        "unstable_pairs": [
            {"model_a": "X", "model_b": "Y", "f1_diff": 0.02, "ci_overlap": True}
        ],
    }
    result = analyze_robustness(decomp, threshold_sensitivity=None)
    assert result["n_unstable_pairs"] == 1


def test_latex_output_is_string():
    """The summary field is a LaTeX-ready string."""
    decomp = {
        "eta_sq_model": 0.45,
        "eta_sq_method": 0.38,
        "eta_sq_interaction": 0.12,
        "eta_sq_residual": 0.05,
        "unstable_pairs": [],
    }
    result = analyze_robustness(decomp, threshold_sensitivity=None)
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 20  # non-trivial paragraph
