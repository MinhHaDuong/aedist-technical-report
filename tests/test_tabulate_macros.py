"""Tests for aedist.tabulate_macros — LaTeX macro generation from metrics JSON."""

import sys

from conftest import patch_measurements_loader, write_measurements

from aedist.tabulate_macros import generate_macros, load_and_summarize, load_headline_result

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.70, "coverage": 0.8, "precision": 0.62},
    {"label": "census/gpt-5.4-run2", "f1": 0.60, "coverage": 0.78, "precision": 0.60},
    {"label": "census/gpt-5.4-run3", "f1": 0.72, "coverage": 0.82, "precision": 0.64},
    {"label": "census/claude-4-run1", "f1": 0.65, "coverage": 0.75, "precision": 0.58},
    {"label": "census/claude-4-run2", "f1": 0.63, "coverage": 0.73, "precision": 0.56},
    {"label": "census/claude-4-run3", "f1": 0.67, "coverage": 0.77, "precision": 0.60},
    {
        "label": "census/padme-qwen3.5-27b-run1",
        "f1": 0.50,
        "coverage": 0.60,
        "precision": 0.43,
    },
    {
        "label": "census/padme-qwen3.5-27b-run2",
        "f1": 0.52,
        "coverage": 0.62,
        "precision": 0.45,
    },
    {
        "label": "census/padme-qwen3.5-27b-run3",
        "f1": 0.48,
        "coverage": 0.58,
        "precision": 0.41,
    },
    {
        "label": "census/padme-mistral-small3.2-run1",
        "f1": 0.40,
        "coverage": 0.50,
        "precision": 0.33,
    },
    {
        "label": "census/padme-mistral-small3.2-run2",
        "f1": 0.42,
        "coverage": 0.52,
        "precision": 0.35,
    },
    {
        "label": "census/padme-mistral-small3.2-run3",
        "f1": 0.38,
        "coverage": 0.48,
        "precision": 0.31,
    },
]

# Synthetic rag_per_fuel (formerly decomposed) runs for headline macro tests —
# mirrors the actual rag/rag_per_fuel/deepseek-v3.2 measurements (4 runs, exact values).
# Post-0120: prompt_version=rag_per_fuel replaces the old decomposed directory label.
HEADLINE_METRICS = [
    {
        "label": "rag_per_fuel/deepseek-v3.2-run1",
        "f1": 0.8859,
        "coverage": 0.9,
        "precision": 0.99,
    },
    {
        "label": "rag_per_fuel/deepseek-v3.2-run2",
        "f1": 0.8561,
        "coverage": 0.88,
        "precision": 0.99,
    },
    {
        "label": "rag_per_fuel/deepseek-v3.2-run3",
        "f1": 0.9879,
        "coverage": 1.0,
        "precision": 0.99,
    },
    {
        "label": "rag_per_fuel/deepseek-v3.2-run4",
        "f1": 0.8601,
        "coverage": 0.88,
        "precision": 0.99,
    },
    # rag_per_fuel_v2 entries must NOT be included when method="rag_per_fuel"
    {
        "label": "rag_per_fuel_v2/deepseek-v3.2-run1",
        "f1": 0.9879,
        "coverage": 1.0,
        "precision": 0.99,
    },
    {
        "label": "rag_per_fuel_v2/deepseek-v3.2-run2",
        "f1": 0.8315,
        "coverage": 0.85,
        "precision": 0.99,
    },
]


def test_load_and_summarize():
    """Model slugs are extracted and median F1 computed per model."""
    summary = load_and_summarize(SAMPLE_METRICS)
    assert len(summary) == 4
    # gpt-5.4 median of [0.60, 0.70, 0.72] = 0.70 (mean would be ~0.673)
    assert summary["gpt-5.4"]["median_f1"] == 0.70
    # claude-4 median of [0.63, 0.65, 0.67] = 0.65
    assert summary["claude-4"]["median_f1"] == 0.65
    assert summary["padme-qwen3.5-27b"]["is_local"] is True
    assert summary["gpt-5.4"]["is_local"] is False


def test_generate_macros():
    """Output contains expected LaTeX newcommands."""
    summary = load_and_summarize(SAMPLE_METRICS)
    tex = generate_macros(summary)
    assert r"\newcommand{\NumModelsTested}" in tex
    assert r"\newcommand{\BestModelName}" in tex
    assert r"\newcommand{\BestModelFOne}" in tex
    assert r"\newcommand{\BestLocalName}" in tex
    assert r"\newcommand{\BestLocalFOne}" in tex
    # Best overall is gpt-5.4 with median F1 = 0.70
    assert "70.0" in tex
    # Best local is padme-qwen3.5-27b with median F1 = 0.50
    assert "50.0" in tex
    # 4 unique models
    assert "{4}" in tex


def test_slug_strips_run_and_dir():
    """Labels with directory prefix and -runN suffix produce clean slugs."""
    metrics = [
        {"label": "census/my-model-run1", "f1": 0.5},
        {"label": "census/my-model-run2", "f1": 0.6},
    ]
    summary = load_and_summarize(metrics)
    assert "my-model" in summary
    assert len(summary) == 1


def test_main_writes_file(tmp_path, monkeypatch):
    """CLI writes macros.tex from measurements."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "macros.tex"

    from aedist.tabulate_macros import main

    sys.argv = [
        "tabulate_macros",
        "--output",
        str(output_path),
    ]
    main()
    content = output_path.read_text()
    assert r"\newcommand" in content


def test_main_census_headline_macros_nonzero(tmp_path, monkeypatch):
    """CLI with --census still emits non-zero \\Headline* macros from measurements.

    Post-ticket-0436 the census summary is derived from measurements.jsonl
    directly (via aedist.exp1_census), not round-tripped through a CSV
    side-output; the headline macros still load the raw run data.
    """
    # Write measurements JSONL with headline-eligible rows
    meas_path = tmp_path / "measurements.jsonl"
    write_measurements(meas_path, HEADLINE_METRICS)
    patch_measurements_loader(monkeypatch, meas_path)

    output_path = tmp_path / "macros_slides.tex"

    from aedist.tabulate_macros import main

    sys.argv = [
        "tabulate_macros",
        "--census",
        "--output",
        str(output_path),
    ]
    main()
    content = output_path.read_text()
    # HeadlineMeanFOne must not be 0.0 — should be ~89.8 from the 4 rag_per_fuel runs
    assert r"\newcommand{\HeadlineMeanFOne}{0.0}" not in content
    assert r"\newcommand{\HeadlineNRuns}{0}" not in content
    assert r"\newcommand{\HeadlineMeanFOne}{89.8}" in content


# ---------------------------------------------------------------------------
# Headline-pinned macro tests (Option A)
# ---------------------------------------------------------------------------


def test_load_headline_result_selects_correct_rows():
    """Only 'rag_per_fuel/' rows for deepseek-v3.2 are matched; rag_per_fuel_v2 excluded."""
    result = load_headline_result(HEADLINE_METRICS)
    assert result["n_runs"] == 4
    assert set(result["f1_values"]) == {0.8859, 0.8561, 0.9879, 0.8601}


def test_load_headline_result_ci_bounds():
    """Bootstrap CI is non-degenerate and mean is inside [lo, hi]."""
    result = load_headline_result(HEADLINE_METRICS)
    assert result["ci_lo"] < result["mean"] <= result["ci_hi"]
    assert result["ci_hi"] - result["ci_lo"] > 0


def test_load_headline_result_empty_on_no_match():
    """Returns zero-filled dict when no rows match."""
    result = load_headline_result(HEADLINE_METRICS, model_slug="nonexistent-model")
    assert result["n_runs"] == 0
    assert result["mean"] == 0.0


def test_generate_macros_headline_keys():
    """generate_macros emits all four \\Headline* commands."""
    summary = load_and_summarize(SAMPLE_METRICS)
    tex = generate_macros(summary, headline_metrics=HEADLINE_METRICS)
    assert r"\newcommand{\HeadlineModelName}" in tex
    assert r"\newcommand{\HeadlineMeanFOne}" in tex
    assert r"\newcommand{\HeadlineCILo}" in tex
    assert r"\newcommand{\HeadlineCIHi}" in tex
    assert r"\newcommand{\HeadlineNRuns}" in tex


def test_generate_macros_headline_model_name():
    """\\HeadlineModelName uses brand-aware capitalization."""
    summary = load_and_summarize(SAMPLE_METRICS)
    tex = generate_macros(summary, headline_metrics=HEADLINE_METRICS)
    assert r"\newcommand{\HeadlineModelName}{DeepSeek V3.2}" in tex


def test_generate_macros_headline_values():
    """\\HeadlineMeanFOne, \\HeadlineCILo, \\HeadlineCIHi match expected numbers."""
    summary = load_and_summarize(SAMPLE_METRICS)
    tex = generate_macros(summary, headline_metrics=HEADLINE_METRICS)
    # Mean of [0.8859, 0.8561, 0.9879, 0.8601] = 0.8975 -> 89.8%
    assert r"\newcommand{\HeadlineMeanFOne}{89.8}" in tex
    # Bootstrap CI (seed=42): lo=85.8%, hi=95.6%
    assert r"\newcommand{\HeadlineCILo}{85.8}" in tex
    assert r"\newcommand{\HeadlineCIHi}{95.6}" in tex
    assert r"\newcommand{\HeadlineNRuns}{4}" in tex


# quarantine: test_decomposed_deepseek_has_ci — passes once headline macros computed
def test_decomposed_deepseek_has_ci():
    """Bootstrap CI must be computable from the headline condition (actual measurements).

    This test validates that load_headline_result produces values matching the
    numbers reported in slides.tex. It is marked quarantine because it reads
    the live measurements.jsonl, which must be present.
    """
    from aedist.measurements import load_metrics

    metrics = load_metrics()
    result = load_headline_result(metrics)
    assert result["n_runs"] >= 3
    assert result["ci_lo"] < result["mean"] <= result["ci_hi"]
    assert result["ci_hi"] - result["ci_lo"] > 0
    # Values must match what is reported in slides.tex (v2.1 reference, 173 plants)
    assert abs(result["mean"] - 0.686) < 0.005, f"Mean {result['mean']:.3f} != 68.6%"
    assert abs(result["ci_lo"] - 0.607) < 0.01, f"CI lower {result['ci_lo']:.3f} != 60.7%"
    assert abs(result["ci_hi"] - 0.748) < 0.01, f"CI upper {result['ci_hi']:.3f} != 74.8%"
