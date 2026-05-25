"""Tests for aedist.plot_quality_spider_exp1."""

from pathlib import Path

from aedist.plot_quality_spider_exp1 import _load_rows, make_figure


def test_make_figure_writes_pdf(tmp_path):
    input_csv = Path("experiments/derived/exp1_cross_eval.csv")
    rows = _load_rows(input_csv)
    assert len(rows) > 0

    out = tmp_path / "fig_spider_exp1_families.pdf"
    make_figure(rows, out)

    assert out.exists()
    assert out.stat().st_size > 1000
