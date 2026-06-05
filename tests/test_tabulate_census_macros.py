"""Tests for aedist.tabulate_census_macros (ticket 0436).

The census macros (\\NumCensusModels, \\Census*) used to be harvested as a
side-output of plot_method_convergence, invoked purely to dump them while
discarding a sentinel PDF. This module emits them directly from the shared
derivation. These tests pin the CLI wiring and the deliberate decision that the
record set is selected by --prompt-version only (the old --methods flag never
narrowed the macro counts, so it is not replayed).
"""

import sys

from conftest import patch_measurements_loader, write_measurements

# Two census-prompt models, two reps each. prompt_version=census → method
# resolves to "direct" (in the convergence _METHOD_ORDER), so these rows reach
# load_convergence_data and the macro counts.
CENSUS_METRICS = [
    {"label": "census/gpt-5.4-run1", "n_matched": 80, "n_hallucinated": 10, "n_missed": 73, "f1": 0.70},
    {"label": "census/gpt-5.4-run2", "n_matched": 90, "n_hallucinated": 5, "n_missed": 63, "f1": 0.72},
    {"label": "census/claude-4-run1", "n_matched": 100, "n_hallucinated": 2, "n_missed": 53, "f1": 0.80},
    {"label": "census/claude-4-run2", "n_matched": 120, "n_hallucinated": 0, "n_missed": 43, "f1": 0.85},
]


def test_main_writes_census_macros(tmp_path, monkeypatch):
    """CLI emits the \\NumCensusModels / \\Census* macros from measurements."""
    meas_path = tmp_path / "measurements.jsonl"
    write_measurements(meas_path, CENSUS_METRICS)
    patch_measurements_loader(monkeypatch, meas_path)
    output_path = tmp_path / "macros_census.tex"

    from aedist.tabulate_census_macros import main

    sys.argv = [
        "tabulate_census_macros",
        "--prompt-version",
        "census",
        "--output",
        str(output_path),
    ]
    main()

    content = output_path.read_text()
    # The four census reps are counted (the conftest stamps a per-rep model
    # stem, so each rep is its own "model" here — the wiring, not real-data
    # dedup, is what this pins).
    assert r"\newcommand{\NumCensusModels}{4}" in content
    # TP range across reps: min 80 (gpt run1), max 120 (claude run2).
    assert r"\newcommand{\CensusTPMin}{80}" in content
    assert r"\newcommand{\CensusTPMax}{120}" in content
    # FP range: min 0, max 10.
    assert r"\newcommand{\CensusFPMin}{0}" in content
    assert r"\newcommand{\CensusFPMax}{10}" in content
    # prompt_version-scoped run count is emitted (the 4 census reps).
    assert r"\newcommand{\CensusNumRuns}{4}" in content


def test_prompt_version_scopes_the_record_set(tmp_path, monkeypatch):
    """Records outside the requested prompt_version are excluded from the macros.

    Adding a p1_base direct row (same method, different prompt_version) must
    leave the census TP/FP ranges and scoped run count untouched.
    """
    mixed = CENSUS_METRICS + [
        # A non-census direct row with an out-of-range TP — must NOT widen the
        # census TP range or the scoped run count.
        {"label": "p1_base/mistral-large-run1", "n_matched": 5, "n_hallucinated": 99, "n_missed": 100, "f1": 0.4},
    ]
    meas_path = tmp_path / "measurements.jsonl"
    write_measurements(meas_path, mixed)
    patch_measurements_loader(monkeypatch, meas_path)
    output_path = tmp_path / "macros_census.tex"

    from aedist.tabulate_census_macros import main

    sys.argv = [
        "tabulate_census_macros",
        "--prompt-version",
        "census",
        "--output",
        str(output_path),
    ]
    main()

    content = output_path.read_text()
    # The out-of-census row (TP=5, FP=99) is excluded by the prompt_version
    # filter, so the census ranges and run count are unchanged.
    assert r"\newcommand{\CensusTPMin}{80}" in content
    assert r"\newcommand{\CensusFPMax}{10}" in content
    assert r"\newcommand{\CensusNumRuns}{4}" in content
