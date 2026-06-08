"""Tests for tabulate_decomposition: Exp3 per-model F1 comparison table.

Guards:
- test_decomposition_table_matches_mart: re-derives one cell from live mart and
  checks the generated file contains that value (not a hard-coded literal).
- test_decomposition_no_v1_values: stale v1 strings ("98,8", "94,8") absent.
"""

import statistics

import pytest
from conftest import patch_measurements_loader, write_measurements

# ---------------------------------------------------------------------------
# Synthetic metrics fixtures
# ---------------------------------------------------------------------------

def _make_run(prefix: str, model: str, run: int, f1: float) -> dict:
    """Helper to construct a minimal metrics entry."""
    return {
        "label": f"{prefix}/{model}-run{run}",
        "method": "rag",
        "prompt_version": prefix,
        "f1": f1,
        "coverage": f1 * 0.9,
        "precision": 0.95,
        "n_reference": 173,
        "n_matched": int(f1 * 173 * 0.9),
    }


SAMPLE_METRICS = [
    # --- mistral-small-2603 ---
    _make_run("rag_extract", "mistral-small-2603", 1, 0.510),
    _make_run("rag_extract", "mistral-small-2603", 2, 0.515),
    _make_run("rag_extract", "mistral-small-2603", 3, 0.520),
    _make_run("rag_per_fuel", "mistral-small-2603", 1, 0.530),
    _make_run("rag_per_fuel", "mistral-small-2603", 2, 0.545),
    _make_run("rag_per_fuel", "mistral-small-2603", 3, 0.607),
    # --- gpt-5.4 ---
    _make_run("rag_extract", "gpt-5.4", 1, 0.700),
    _make_run("rag_extract", "gpt-5.4", 2, 0.713),
    _make_run("rag_extract", "gpt-5.4", 3, 0.713),
    _make_run("rag_per_fuel", "gpt-5.4", 1, 0.640),
    _make_run("rag_per_fuel", "gpt-5.4", 2, 0.655),
    _make_run("rag_per_fuel", "gpt-5.4", 3, 0.659),
    # --- mistral-large-2512 ---
    _make_run("rag_extract", "mistral-large-2512", 1, 0.600),
    _make_run("rag_extract", "mistral-large-2512", 2, 0.612),
    _make_run("rag_extract", "mistral-large-2512", 3, 0.649),
    _make_run("rag_per_fuel", "mistral-large-2512", 1, 0.760),
    _make_run("rag_per_fuel", "mistral-large-2512", 2, 0.762),
    _make_run("rag_per_fuel", "mistral-large-2512", 3, 0.763),
    # --- deepseek-v3.2: 3 single + 4 decomposed ---
    _make_run("rag_extract", "deepseek-v3.2", 1, 0.510),
    _make_run("rag_extract", "deepseek-v3.2", 2, 0.518),
    _make_run("rag_extract", "deepseek-v3.2", 3, 0.643),
    _make_run("rag_per_fuel", "deepseek-v3.2", 1, 0.640),
    _make_run("rag_per_fuel", "deepseek-v3.2", 2, 0.680),
    _make_run("rag_per_fuel", "deepseek-v3.2", 3, 0.720),
    _make_run("rag_per_fuel", "deepseek-v3.2", 4, 0.765),
    # rag_per_fuel_v2 rows for deepseek — must be EXCLUDED from the table
    _make_run("rag_per_fuel_v2", "deepseek-v3.2", 1, 0.999),
    # --- gemini-2.5-flash-lite ---
    _make_run("rag_extract", "gemini-2.5-flash-lite", 1, 0.460),
    _make_run("rag_extract", "gemini-2.5-flash-lite", 2, 0.465),
    _make_run("rag_extract", "gemini-2.5-flash-lite", 3, 0.496),
    _make_run("rag_per_fuel", "gemini-2.5-flash-lite", 1, 0.530),
    _make_run("rag_per_fuel", "gemini-2.5-flash-lite", 2, 0.540),
    _make_run("rag_per_fuel", "gemini-2.5-flash-lite", 3, 0.646),
]


# ---------------------------------------------------------------------------
# Unit tests for compute_decomposition_table()
# ---------------------------------------------------------------------------


def test_compute_table_returns_five_rows():
    from aedist.tabulate_decomposition import TABLE_MODELS, compute_decomposition_table

    table = compute_decomposition_table(SAMPLE_METRICS)
    # Only models that appear in both single and decomposed
    model_slugs = [r["slug"] for r in table]
    assert "mistral-small-2603" in model_slugs
    assert len(table) == len(TABLE_MODELS)


def test_compute_table_excludes_rag_per_fuel_v2():
    """rag_per_fuel_v2 rows must not contaminate the decomposed column."""
    from aedist.tabulate_decomposition import compute_decomposition_table

    table = compute_decomposition_table(SAMPLE_METRICS)
    deepseek_row = next(r for r in table if r["slug"] == "deepseek-v3.2")
    # If rag_per_fuel_v2 were included, best_decomposed would be 0.999
    assert deepseek_row["best_decomposed"] < 0.99


def test_compute_table_mistral_small_median_single():
    from aedist.tabulate_decomposition import compute_decomposition_table

    table = compute_decomposition_table(SAMPLE_METRICS)
    row = next(r for r in table if r["slug"] == "mistral-small-2603")
    expected_median = statistics.median([0.510, 0.515, 0.520])
    assert row["median_single"] == pytest.approx(expected_median)


def test_compute_table_mistral_small_best_decomposed():
    from aedist.tabulate_decomposition import compute_decomposition_table

    table = compute_decomposition_table(SAMPLE_METRICS)
    row = next(r for r in table if r["slug"] == "mistral-small-2603")
    assert row["best_decomposed"] == pytest.approx(0.607)


def test_compute_table_deepseek_run_count():
    from aedist.tabulate_decomposition import compute_decomposition_table

    table = compute_decomposition_table(SAMPLE_METRICS)
    row = next(r for r in table if r["slug"] == "deepseek-v3.2")
    assert row["n_decomposed"] == 4


# ---------------------------------------------------------------------------
# LaTeX rendering
# ---------------------------------------------------------------------------


def test_render_latex_structure():
    from aedist.tabulate_decomposition import compute_decomposition_table, render_latex

    table = compute_decomposition_table(SAMPLE_METRICS)
    latex = render_latex(table)
    assert "\\begin{table}" in latex
    assert "\\end{table}" in latex
    assert "\\label{tab:decomposition}" in latex
    assert "\\caption{" in latex


def test_render_latex_autogenerated_comment():
    from aedist.tabulate_decomposition import compute_decomposition_table, render_latex

    table = compute_decomposition_table(SAMPLE_METRICS)
    latex = render_latex(table)
    assert latex.startswith("% Auto-generated")


def test_render_latex_french_commas():
    """Values are formatted with French decimal commas (51,5 not 51.5)."""
    from aedist.tabulate_decomposition import compute_decomposition_table, render_latex

    table = compute_decomposition_table(SAMPLE_METRICS)
    latex = render_latex(table)
    # mistral-small-2603 median single = 51.5% → "51,5"
    assert "51,5" in latex


def test_render_latex_bold_winner():
    """The per-model decomposed winner (if better) is bolded."""
    from aedist.tabulate_decomposition import compute_decomposition_table, render_latex

    table = compute_decomposition_table(SAMPLE_METRICS)
    latex = render_latex(table)
    assert "\\textbf{" in latex


def test_render_latex_footnote():
    """Footnote explaining n and Méd. is present."""
    from aedist.tabulate_decomposition import compute_decomposition_table, render_latex

    table = compute_decomposition_table(SAMPLE_METRICS)
    latex = render_latex(table)
    assert "footnotesize" in latex or "textsuperscript" in latex


# ---------------------------------------------------------------------------
# Adherence test: re-derive DeepSeek cell from live mart
# ---------------------------------------------------------------------------


@pytest.mark.adherence
def test_decomposition_table_matches_mart(tmp_path):
    """tab_decomposition.tex contains the median decomposed F1 for deepseek-v3.2.

    Re-derives the value from measurements.jsonl (not a hard-coded literal)
    to guard against the re-typed-number trap.
    """
    import statistics

    from aedist.measurements import SYNTHETIC_SUFFIXES, load_metrics
    from aedist.tabulate_decomposition import main
    from aedist.tabulate_utils import strip_label

    metrics = load_metrics()
    deepseek_decomp = [
        m["f1"]
        for m in metrics
        if m["label"].startswith("rag_per_fuel/")
        and strip_label(m["label"]) == "deepseek-v3.2"
        and not any(m["label"].endswith(s) for s in SYNTHETIC_SUFFIXES)
    ]
    assert deepseek_decomp, "No deepseek-v3.2 rag_per_fuel rows in mart"

    median_f1 = statistics.median(deepseek_decomp)
    # Format the same way the script does: French comma, 1 decimal
    expected_str = f"{median_f1 * 100:.1f}".replace(".", ",")

    output = tmp_path / "tab_decomposition.tex"
    main(["--output", str(output)])

    content = output.read_text()
    assert expected_str in content, (
        f"DeepSeek decomposed median {expected_str} not found in generated table.\n"
        f"Generated content:\n{content}"
    )


@pytest.mark.adherence
def test_decomposition_no_v1_values(tmp_path):
    """Stale v1 values '98,8' (DeepSeek best) and '94,8' (Mistral-Large best) absent.

    These were the v1-era numbers in the hand-written table and must not
    appear in the regenerated artifact.
    """
    from aedist.tabulate_decomposition import main

    output = tmp_path / "tab_decomposition.tex"
    main(["--output", str(output)])

    content = output.read_text()
    assert "98,8" not in content, "Stale v1 DeepSeek best F1 '98,8' found in generated table"
    assert "94,8" not in content, "Stale v1 Mistral-Large best F1 '94,8' found in generated table"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_main_writes_output(tmp_path, monkeypatch):
    """main() reads measurements and writes LaTeX output."""
    from aedist.tabulate_decomposition import main

    input_file = tmp_path / "measurements.jsonl"
    write_measurements(input_file, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_file)
    output_file = tmp_path / "tab_decomposition.tex"

    main(["--output", str(output_file)])

    content = output_file.read_text()
    assert "\\begin{table}" in content
    assert "\\label{tab:decomposition}" in content
    assert "tab:decomposition" in content


def test_main_creates_parent_dirs(tmp_path, monkeypatch):
    """main() creates parent directories if they don't exist."""
    from aedist.tabulate_decomposition import main

    input_file = tmp_path / "measurements.jsonl"
    write_measurements(input_file, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_file)
    output_file = tmp_path / "sub" / "dir" / "tab_decomposition.tex"

    main(["--output", str(output_file)])

    assert output_file.exists()
