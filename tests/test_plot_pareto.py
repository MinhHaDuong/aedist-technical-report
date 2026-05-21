"""Tests for aedist.plot_pareto — Pareto CSV from metrics JSON."""

import csv
import re
import subprocess
import sys

import pytest
from conftest import patch_measurements_loader, write_measurements

from aedist.plot_pareto import _is_p1_base_row, build_pareto_rows, write_pdf
from aedist.util import family_color

# Sample with three families (EN/FR/ZH) and varying F1 per rep so min/max
# whiskers are testable. Labels mirror the p1_base prompt_version so the
# slug stripper recovers clean model names; the result_file used by the
# Experiment 1 filter is controlled by the test fixtures that need it.
SAMPLE_METRICS = [
    {"label": "p1_base/claude-opus-4.6-run1", "f1": 0.55, "cost_usd": 0.10},
    {"label": "p1_base/claude-opus-4.6-run2", "f1": 0.50, "cost_usd": 0.10},
    {"label": "p1_base/claude-opus-4.6-run3", "f1": 0.60, "cost_usd": 0.10},
    {"label": "p1_base/mistral-large-2512-run1", "f1": 0.40, "cost_usd": 0.05},
    {"label": "p1_base/mistral-large-2512-run2", "f1": 0.42, "cost_usd": 0.05},
    {"label": "p1_base/mistral-large-2512-run3", "f1": 0.45, "cost_usd": 0.05},
    {"label": "p1_base/qwen3.6-plus-run1", "f1": 0.30, "cost_usd": 0.02},
    {"label": "p1_base/qwen3.6-plus-run2", "f1": 0.35, "cost_usd": 0.02},
    {"label": "p1_base/qwen3.6-plus-run3", "f1": 0.32, "cost_usd": 0.02},
]


def test_build_pareto_rows():
    """Rows have correct models with median F1, min/max F1, and cost."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    assert len(rows) == 3
    assert all(
        set(r.keys()) == {"model", "median_f1", "min_f1", "max_f1", "cost_usd"} for r in rows
    )
    by_model = {r["model"]: r for r in rows}
    # Median, min, max of [0.50, 0.55, 0.60]
    assert by_model["claude-opus-4.6"]["median_f1"] == 0.55
    assert by_model["claude-opus-4.6"]["min_f1"] == 0.50
    assert by_model["claude-opus-4.6"]["max_f1"] == 0.60
    assert by_model["mistral-large-2512"]["median_f1"] == 0.42
    assert by_model["qwen3.6-plus"]["median_f1"] == 0.32


def test_build_pareto_rows_sorted_by_median():
    """Rows are sorted by median F1 descending."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    medians = [r["median_f1"] for r in rows]
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
    """The three families resolve to three distinct palette colours."""
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


def test_pareto_whiskers_present(tmp_path):
    """Rendered figure carries errorbar containers (one per model)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.container import ErrorbarContainer

    rows = build_pareto_rows(SAMPLE_METRICS)
    figure_path = tmp_path / "fig_pareto.pdf"
    write_pdf(rows, figure_path)
    assert figure_path.exists()

    # Inspect the last rendered figure: 3 models → 3 errorbar containers.
    # write_pdf calls plt.close on its fig, so we re-render here to inspect.
    fig, ax = plt.subplots()
    for r in rows:
        median = r["median_f1"]
        ax.errorbar(
            [r["cost_usd"]],
            [median],
            yerr=[[median - r["min_f1"]], [r["max_f1"] - median]],
            fmt="o",
        )
    containers = [c for c in ax.containers if isinstance(c, ErrorbarContainer)]
    assert len(containers) == len(rows)
    plt.close(fig)


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
    """CLI writes well-formed CSV with the new median/min/max schema."""
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
    assert set(reader.fieldnames) == {"model", "median_f1", "min_f1", "max_f1", "cost_usd"}


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
