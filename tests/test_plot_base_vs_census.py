"""Tests for plot_base_vs_census robustness on sparse inputs."""

from pathlib import Path


def test_make_figure_handles_empty_rows(tmp_path):
    from aedist.plot_base_vs_census import _make_figure

    output = tmp_path / "fig_empty.pdf"
    _make_figure({"rows": []}, output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_main_does_not_exit_on_empty_intersection(tmp_path, monkeypatch):
    from aedist import plot_base_vs_census

    output = tmp_path / "fig.pdf"

    def fake_compute_table(*, p1_base_dir: Path | None = None) -> dict:
        return {
            "rows": [],
            "delta_f1_mean": 0.0,
            "delta_f1_ci_low": 0.0,
            "delta_f1_ci_high": 0.0,
            "model_count": 0,
        }

    monkeypatch.setattr(plot_base_vs_census, "compute_table", fake_compute_table)

    plot_base_vs_census.main(["--output", str(output)])

    assert output.exists()
    assert output.stat().st_size > 0
