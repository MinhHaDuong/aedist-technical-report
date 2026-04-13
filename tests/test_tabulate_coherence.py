"""Tests for tabulate_coherence (ticket 0078)."""

from pathlib import Path

from aedist.tabulate_coherence import (
    format_coherence_latex,
    load_extractions,
    summarize_coherence,
)

# ── Helpers ────────────────────────────────────────────────────────────


def _write_csv_file(path: Path, rows: list[dict]) -> None:
    """Write a minimal CSV that load_plants_csv can parse."""
    import csv

    fieldnames = ["name", "fuel", "capacity_mwe", "province", "status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _clean_plants() -> list[dict]:
    """Row dicts for a fully-coherent extraction (known fuel, province, etc.)."""
    return [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": "440",
            "province": "Hải Dương",
            "status": "operational",
        },
        {
            "name": "Mong Duong 1",
            "fuel": "coal",
            "capacity_mwe": "1080",
            "province": "Quảng Ninh",
            "status": "operational",
        },
    ]


def _plants_with_issues() -> list[dict]:
    """Rows containing coherence problems: unknown fuel, duplicate."""
    return [
        {
            "name": "Mystery",
            "fuel": "unknown",
            "capacity_mwe": "100",
            "province": "Ha Noi",
            "status": "operational",
        },
        {
            "name": "Duplicate",
            "fuel": "coal",
            "capacity_mwe": "200",
            "province": "Ha Noi",
            "status": "operational",
        },
        {
            "name": "Duplicate",
            "fuel": "coal",
            "capacity_mwe": "200",
            "province": "Ha Noi",
            "status": "operational",
        },
    ]


# ── Filter logic ───────────────────────────────────────────────────────


def test_filter_skips_reconciliation(tmp_path: Path):
    """reconciliation_* files must not appear in extractions."""
    _write_csv_file(tmp_path / "model-a-run1.csv", _clean_plants())
    _write_csv_file(tmp_path / "reconciliation_model-a-run1.csv", _clean_plants())
    exts = load_extractions([tmp_path])
    assert "model-a" in exts
    # Only one run loaded (the raw one, not reconciliation)
    assert len(exts["model-a"]) == 1


def test_filter_skips_consolidated_and_union(tmp_path: Path):
    """Files ending in -consolidated.csv or -union.csv are skipped."""
    _write_csv_file(tmp_path / "model-b-run1.csv", _clean_plants())
    _write_csv_file(tmp_path / "model-b-consolidated.csv", _clean_plants())
    _write_csv_file(tmp_path / "model-b-union.csv", _clean_plants())
    exts = load_extractions([tmp_path])
    assert "model-b" in exts
    assert len(exts["model-b"]) == 1


# ── Clean data ─────────────────────────────────────────────────────────


def test_clean_data_coherence_rate_one(tmp_path: Path):
    """Fully-clean rows should produce coherence_rate == 1.0."""
    _write_csv_file(tmp_path / "clean-model-run1.csv", _clean_plants())
    exts = load_extractions([tmp_path])
    rows = summarize_coherence(exts)
    assert len(rows) == 1
    assert rows[0]["coherence_rate"] == 1.0
    assert rows[0]["n_row_issues"] == 0
    assert rows[0]["n_cross_row_issues"] == 0


# ── Data with issues ──────────────────────────────────────────────────


def test_issues_counted_correctly(tmp_path: Path):
    """Rows with problems must lower coherence_rate and count issues."""
    _write_csv_file(tmp_path / "bad-model-run1.csv", _plants_with_issues())
    exts = load_extractions([tmp_path])
    rows = summarize_coherence(exts)
    assert len(rows) == 1
    r = rows[0]
    assert r["n_row_issues"] > 0 or r["n_cross_row_issues"] > 0
    assert r["coherence_rate"] < 1.0


# ── LaTeX structure ───────────────────────────────────────────────────


def test_latex_structure():
    """LaTeX output must have table environment and expected columns."""
    sample = [
        {
            "model": "test-model",
            "n_rows": 10,
            "n_row_issues": 1,
            "n_cross_row_issues": 0,
            "coherence_rate": 0.9,
        },
    ]
    latex = format_coherence_latex(sample)
    assert "\\begin{table}" in latex
    assert "\\end{table}" in latex
    assert "\\toprule" in latex
    assert "\\bottomrule" in latex
    assert "90.0\\%" in latex
    assert "Test-Model" in latex


# ── CLI end-to-end ────────────────────────────────────────────────────


def test_cli_end_to_end(tmp_path: Path):
    """CLI writes both LaTeX and CSV outputs."""
    from aedist.tabulate_coherence import main

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_csv_file(data_dir / "m1-run1.csv", _clean_plants())
    _write_csv_file(data_dir / "m1-run2.csv", _clean_plants())

    tex_path = tmp_path / "out.tex"
    csv_path = tmp_path / "out.csv"

    main(
        [
            "--input",
            str(data_dir),
            "--output",
            str(tex_path),
            "--csv-output",
            str(csv_path),
        ]
    )

    assert tex_path.exists()
    assert csv_path.exists()
    content = tex_path.read_text()
    assert "\\begin{table}" in content
    csv_content = csv_path.read_text()
    assert "coherence_rate" in csv_content
