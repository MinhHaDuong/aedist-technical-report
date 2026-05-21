"""Tests for aedist.plot_pareto — Pareto CSV from metrics JSON."""

import csv
import re
import subprocess
import sys

import pytest
from conftest import patch_measurements_loader, write_measurements

from aedist.plot_pareto import _is_p1_base_row, build_pareto_rows, write_pdf
from aedist.util import family_color, model_family_color

# Sample with three architectural families (Claude/Mistral/Qwen) and varying
# tp + F1 per rep so min/max whiskers are testable. Labels mirror the
# p1_base prompt_version so the slug stripper recovers clean model names;
# the result_file used by the Experiment 1 filter is controlled by the
# test fixtures that need it.
SAMPLE_METRICS = [
    {"label": "p1_base/claude-opus-4.6-run1", "n_matched": 80, "f1": 0.55, "cost_usd": 0.10},
    {"label": "p1_base/claude-opus-4.6-run2", "n_matched": 82, "f1": 0.50, "cost_usd": 0.10},
    {"label": "p1_base/claude-opus-4.6-run3", "n_matched": 85, "f1": 0.60, "cost_usd": 0.10},
    {"label": "p1_base/mistral-large-2512-run1", "n_matched": 50, "f1": 0.40, "cost_usd": 0.05},
    {"label": "p1_base/mistral-large-2512-run2", "n_matched": 52, "f1": 0.42, "cost_usd": 0.05},
    {"label": "p1_base/mistral-large-2512-run3", "n_matched": 55, "f1": 0.45, "cost_usd": 0.05},
    {"label": "p1_base/qwen3.6-plus-run1", "n_matched": 30, "f1": 0.30, "cost_usd": 0.02},
    {"label": "p1_base/qwen3.6-plus-run2", "n_matched": 33, "f1": 0.35, "cost_usd": 0.02},
    {"label": "p1_base/qwen3.6-plus-run3", "n_matched": 35, "f1": 0.32, "cost_usd": 0.02},
]

_EXPECTED_KEYS = {
    "model",
    "family",
    "median_tp",
    "min_tp",
    "max_tp",
    "tp_values",
    "median_f1",
    "min_f1",
    "max_f1",
    "cost_usd",
}

_CSV_EXPECTED_KEYS = _EXPECTED_KEYS - {"tp_values"}  # tp_values is in-memory only


def test_build_pareto_rows():
    """Rows expose TP and F1 stats per model, plus family + cost."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    assert len(rows) == 3
    assert all(set(r.keys()) == _EXPECTED_KEYS for r in rows)
    by_model = {r["model"]: r for r in rows}
    # Median, min, max of [80, 82, 85]
    assert by_model["claude-opus-4.6"]["median_tp"] == 82
    assert by_model["claude-opus-4.6"]["min_tp"] == 80
    assert by_model["claude-opus-4.6"]["max_tp"] == 85
    assert by_model["claude-opus-4.6"]["family"] == "claude"
    assert by_model["mistral-large-2512"]["median_tp"] == 52
    assert by_model["mistral-large-2512"]["family"] == "mistral"
    assert by_model["qwen3.6-plus"]["median_tp"] == 33
    assert by_model["qwen3.6-plus"]["family"] == "qwen"


def test_build_pareto_rows_sorted_by_median_tp():
    """Rows are sorted by median TP descending."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    medians = [r["median_tp"] for r in rows]
    assert medians == sorted(medians, reverse=True)


def test_cost_mean_across_reps():
    """Per-model cost is the mean across rep costs (all reps share cost here)."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    assert by_model["claude-opus-4.6"]["cost_usd"] == 0.10
    assert by_model["mistral-large-2512"]["cost_usd"] == 0.05


def test_is_p1_base_row():
    """Filter accepts direct/p1_base rows but rejects pilot and other sweeps."""
    assert _is_p1_base_row("experiments/outputs/ablation/direct/p1_base/claude-opus-4.6-run1.csv")
    assert not _is_p1_base_row(
        "experiments/outputs/ablation/direct/p1_base.pilot/claude-opus-4.6-run1.csv"
    )
    assert not _is_p1_base_row(
        "experiments/outputs/ablation/livesearch/p1_base/claude-opus-4.6-run1.csv"
    )
    assert not _is_p1_base_row("experiments/outputs/ablation/rag/p1_base/claude-opus-4.6-run1.csv")


def test_pareto_family_colours():
    """The three language families resolve to three distinct palette colours."""
    en = family_color("claude-opus-4.6")
    fr = family_color("mistral-large-2512")
    zh = family_color("qwen3.6-plus")
    assert en != fr
    assert fr != zh
    assert en != zh
    # All match the EN/FR/ZH direct hexes from palette.toml.
    assert en == family_color("EN")
    assert fr == family_color("FR")
    assert zh == family_color("ZH")


def test_pareto_model_family_colours():
    """The five architectural families resolve to five distinct palette colours."""
    claude = model_family_color("claude-opus-4.6")
    gpt = model_family_color("gpt-5.5")
    mistral = model_family_color("mistral-large-2512")
    qwen = model_family_color("qwen3-max-thinking")
    deepseek = model_family_color("deepseek-v4-pro")
    assert len({claude, gpt, mistral, qwen, deepseek}) == 5
    # Within-family models share the colour even across size tiers.
    assert claude == model_family_color("claude-haiku-4.5")
    assert qwen == model_family_color("qwen3.6-plus")


def test_pareto_per_rep_points(tmp_path):
    """Build returns the full per-rep TP list so write_pdf can plot every rep."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    # Each sample model has 3 reps; tp_values must surface all of them.
    assert by_model["claude-opus-4.6"]["tp_values"] == [80, 82, 85]
    assert by_model["mistral-large-2512"]["tp_values"] == [50, 52, 55]
    assert by_model["qwen3.6-plus"]["tp_values"] == [30, 33, 35]
    # write_pdf still renders without raising.
    figure_path = tmp_path / "fig_pareto.pdf"
    write_pdf(rows, figure_path)
    assert figure_path.exists() and figure_path.stat().st_size > 0


def test_pareto_xscale_flag(tmp_path, monkeypatch):
    """--xscale log and --xscale linear both run and reflect in the figure."""
    input_path = tmp_path / "measurements.jsonl"
    # Stamp the result_file via post-processing so the p1_base filter accepts these rows.
    _write_p1_base_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    for scale in ("linear", "log"):
        figure_path = tmp_path / f"fig_pareto_{scale}.pdf"
        from aedist.plot_pareto import main

        sys.argv = [
            "plot_pareto",
            "--output",
            str(tmp_path / f"pareto_{scale}.csv"),
            "--figure",
            str(figure_path),
            "--xscale",
            scale,
        ]
        main()
        assert figure_path.exists()
        assert figure_path.stat().st_size > 0


def test_main_writes_csv(tmp_path, monkeypatch):
    """CLI writes well-formed CSV with the TP + F1 schema."""
    input_path = tmp_path / "measurements.jsonl"
    _write_p1_base_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "pareto.csv"

    from aedist.plot_pareto import main

    sys.argv = [
        "plot_pareto",
        "--output",
        str(output_path),
    ]
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) == 3
    assert set(reader.fieldnames) == _CSV_EXPECTED_KEYS


def test_main_writes_figure(tmp_path, monkeypatch):
    """CLI --figure writes a PDF."""
    input_path = tmp_path / "measurements.jsonl"
    _write_p1_base_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    figure_path = tmp_path / "fig_pareto.pdf"

    from aedist.plot_pareto import main

    sys.argv = [
        "plot_pareto",
        "--output",
        str(tmp_path / "pareto.csv"),
        "--figure",
        str(figure_path),
    ]
    main()
    assert figure_path.exists()
    assert figure_path.stat().st_size > 0


# --- adherence-style checks on the manuscript caption ----------------------

REPO_ROOT_MD = (
    __import__("pathlib").Path(__file__).resolve().parent.parent
    / "slides"
    / "manuscript"
    / "main.md"
)


@pytest.mark.adherence
def test_caption_has_no_stale_pilot_numbers():
    """Figure 2 caption must not carry stale pilot numbers (ticket 0196)."""
    text = REPO_ROOT_MD.read_text()
    forbidden = [
        "DeepSeek V3.2 decomposed+RAG",
        "89.8%",
        "$0.06",
        "\\$0.06",
    ]
    found = [needle for needle in forbidden if needle in text]
    assert not found, (
        f"Stale pilot numbers still present in {REPO_ROOT_MD.name}: {found}. "
        "Rewrite the Figure 2 caption (ticket 0196)."
    )


# --- helpers --------------------------------------------------------------


def _write_p1_base_measurements(path, metrics):
    """write_measurements + rewrite result_file paths to pass the p1_base filter.

    The default conftest helper stamps result_file = f"{label}.csv" which the
    Experiment 1 filter rejects; we rewrite each row's result_file to
    ``.../direct/p1_base/<original-stem>.csv`` so it satisfies the filter
    while preserving the per-rep slug that records_to_metrics needs.
    """
    write_measurements(path, metrics)
    # Patch each line's result_file in place so it satisfies the filter.
    out_lines = []
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        m = re.search(r'"result_file":"([^"]*)"', raw)
        if not m:
            out_lines.append(raw)
            continue
        original_stem = m.group(1).rsplit("/", 1)[-1].removesuffix(".csv")
        new_path = f"experiments/outputs/ablation/direct/p1_base/{original_stem}.csv"
        new = raw[: m.start()] + f'"result_file":"{new_path}"' + raw[m.end() :]
        out_lines.append(new)
    path.write_text("\n".join(out_lines) + "\n")


@pytest.mark.integration
def test_help_lists_xscale_flag():
    """--help advertises the --xscale flag."""
    result = subprocess.run(
        ["uv", "run", "python", "-m", "aedist.plot_pareto", "--help"],
        capture_output=True,
        text=True,
    )
    assert "--xscale" in result.stdout
