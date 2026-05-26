"""Tests for aedist.plot_cost_quality — cost × quality CSV from metrics JSON."""

import csv
import re
import subprocess
import sys

import pytest
from conftest import patch_measurements_loader, write_measurements

from aedist.plot_cost_quality import _is_p1_base_row, build_cost_quality_rows, write_pdf
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
    "reps",
    "median_tp",
    "min_tp",
    "max_tp",
    "tp_values",
    "fp_values",
    "base_tp_values",
    "topup_tp_values",
    "median_fp",
    "min_fp",
    "max_fp",
    "median_cost",
    "min_cost",
    "max_cost",
    "mean_cost",
    "median_f1",
    "min_f1",
    "max_f1",
    "cost_usd",
}

# In-memory only — list/dict-valued fields are dropped by the CSV writer.
_CSV_EXPECTED_KEYS = _EXPECTED_KEYS - {
    "reps",
    "tp_values",
    "fp_values",
    "base_tp_values",
    "topup_tp_values",
}


def test_build_cost_quality_rows():
    """Rows expose TP and F1 stats per model, plus family + cost."""
    rows = build_cost_quality_rows(SAMPLE_METRICS)
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


def test_build_cost_quality_rows_sorted_by_median_tp():
    """Rows are sorted by median TP descending."""
    rows = build_cost_quality_rows(SAMPLE_METRICS)
    medians = [r["median_tp"] for r in rows]
    assert medians == sorted(medians, reverse=True)


def test_cost_mean_across_reps():
    """Per-model cost is the mean across rep costs (all reps share cost here)."""
    rows = build_cost_quality_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    assert by_model["claude-opus-4.6"]["cost_usd"] == 0.10
    assert by_model["mistral-large-2512"]["cost_usd"] == 0.05


def test_is_p1_base_row():
    """Filter accepts exp1_batch2, rejects everything else."""
    assert _is_p1_base_row("experiments/outputs/exp1_batch2/claude-opus-4.6-run1.csv")
    assert _is_p1_base_row("experiments/outputs/exp1_batch2/mistral-large-2512-run3.json")
    # Rejected — old p1_base directories no longer included:
    assert not _is_p1_base_row(
        "experiments/outputs/ablation/direct/p1_base/claude-opus-4.6-run1.csv"
    )
    assert not _is_p1_base_row(
        "experiments/outputs/ablation/direct/p1_base.pilot/claude-opus-4.6-run1.csv"
    )
    assert not _is_p1_base_row(
        "experiments/outputs/ablation/livesearch/p1_base/claude-opus-4.6-run1.csv"
    )


def test_cost_quality_family_colours():
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


def test_cost_quality_model_family_colours():
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


def test_cost_quality_per_rep_points(tmp_path):
    """Build returns the full per-rep TP list so write_pdf can plot every rep."""
    rows = build_cost_quality_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    # Each sample model has 3 reps; tp_values must surface all of them.
    assert by_model["claude-opus-4.6"]["tp_values"] == [80, 82, 85]
    assert by_model["mistral-large-2512"]["tp_values"] == [50, 52, 55]
    assert by_model["qwen3.6-plus"]["tp_values"] == [30, 33, 35]
    # write_pdf still renders without raising.
    figure_path = tmp_path / "fig_cost_quality.pdf"
    write_pdf(rows, figure_path)
    assert figure_path.exists() and figure_path.stat().st_size > 0


def test_cost_quality_reps_carry_per_rep_cost():
    """reps surfaces each rep's individual cost so the figure can scatter in x."""
    # Vary cost per rep within a model so the test isn't degenerate.
    metrics = [
        {"label": "p1_base/claude-opus-4.6-run1", "n_matched": 80, "f1": 0.5, "cost_usd": 0.10},
        {"label": "p1_base/claude-opus-4.6-run2", "n_matched": 82, "f1": 0.5, "cost_usd": 0.12},
        {"label": "p1_base/claude-opus-4.6-run3", "n_matched": 85, "f1": 0.5, "cost_usd": 0.14},
    ]
    rows = build_cost_quality_rows(metrics)
    by_model = {r["model"]: r for r in rows}
    reps = by_model["claude-opus-4.6"]["reps"]
    assert [rep["cost"] for rep in reps] == [0.10, 0.12, 0.14]
    assert [rep["tp"] for rep in reps] == [80, 82, 85]
    assert by_model["claude-opus-4.6"]["median_cost"] == 0.12
    assert by_model["claude-opus-4.6"]["mean_cost"] == 0.12


def test_cost_quality_base_topup_partition():
    """source_by_label partitions reps into base vs topup cohorts."""
    source_by_label = {
        # Mark one of each model's reps as a topup
        "p1_base/claude-opus-4.6-run3": "topup",
        "p1_base/mistral-large-2512-run3": "topup",
        "p1_base/qwen3.6-plus-run3": "topup",
    }
    rows = build_cost_quality_rows(SAMPLE_METRICS, source_by_label=source_by_label)
    by_model = {r["model"]: r for r in rows}
    assert by_model["claude-opus-4.6"]["base_tp_values"] == [80, 82]
    assert by_model["claude-opus-4.6"]["topup_tp_values"] == [85]
    # Without a source map, everything defaults to base.
    rows_no_map = build_cost_quality_rows(SAMPLE_METRICS)
    by_model_no_map = {r["model"]: r for r in rows_no_map}
    assert by_model_no_map["claude-opus-4.6"]["base_tp_values"] == [80, 82, 85]
    assert by_model_no_map["claude-opus-4.6"]["topup_tp_values"] == []


def test_cost_quality_xscale_flag(tmp_path, monkeypatch):
    """--xscale log and --xscale linear both run and reflect in the figure."""
    input_path = tmp_path / "measurements.jsonl"
    # Stamp the result_file via post-processing so the p1_base filter accepts these rows.
    _write_p1_base_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    for scale in ("linear", "log"):
        figure_path = tmp_path / f"fig_cost_quality_{scale}.pdf"
        from aedist.plot_cost_quality import main

        sys.argv = [
            "plot_cost_quality",
            "--output",
            str(tmp_path / f"cost_quality_{scale}.csv"),
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
    output_path = tmp_path / "cost_quality.csv"

    from aedist.plot_cost_quality import main

    sys.argv = [
        "plot_cost_quality",
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
    figure_path = tmp_path / "fig_cost_quality.pdf"

    from aedist.plot_cost_quality import main

    sys.argv = [
        "plot_cost_quality",
        "--output",
        str(tmp_path / "cost_quality.csv"),
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
    """write_measurements + rewrite result_file paths to pass the exp1_batch2 filter.

    The default conftest helper stamps result_file = f"{label}.csv" which the
    Experiment 1 filter rejects; we rewrite each row's result_file to
    ``experiments/outputs/exp1_batch2/<original-stem>.csv`` so it satisfies
    the filter while preserving the per-rep slug that records_to_metrics needs.
    """
    write_measurements(path, metrics)
    out_lines = []
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        m = re.search(r'"result_file":"([^"]*)"', raw)
        if not m:
            out_lines.append(raw)
            continue
        original_stem = m.group(1).rsplit("/", 1)[-1].removesuffix(".csv")
        new_path = f"experiments/outputs/exp1_batch2/{original_stem}.csv"
        new = raw[: m.start()] + f'"result_file":"{new_path}"' + raw[m.end() :]
        out_lines.append(new)
    path.write_text("\n".join(out_lines) + "\n")


@pytest.mark.integration
def test_help_lists_xscale_flag():
    """--help advertises the --xscale flag."""
    result = subprocess.run(
        ["uv", "run", "python", "-m", "aedist.plot_cost_quality", "--help"],
        capture_output=True,
        text=True,
    )
    assert "--xscale" in result.stdout
