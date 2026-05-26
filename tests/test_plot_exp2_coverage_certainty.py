import subprocess
import sys

import pytest


@pytest.mark.integration
def test_script_runs_without_error(tmp_path):
    # The figure consumes two mart views (bib-quality + arms-runs) that are
    # gitignored intermediates, so build them from the tracked mart first
    # rather than relying on a clean-room checkout having them.
    views = tmp_path / "views"
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "aedist.build_exp2_mart_views",
            "--mart-jsonl",
            "experiments/derived/exp2_mart.jsonl",
            "--output-dir",
            str(views),
        ],
        capture_output=True,
    )
    assert build.returncode == 0, build.stderr.decode()

    out = tmp_path / "fig.pdf"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aedist.plot_exp2_coverage_certainty",
            "--input",
            str(views / "tab_exp2_bib_quality_view.csv"),
            "--arms-input",
            str(views / "tab_exp2_arms_runs_view.csv"),
            "--output",
            str(out),
        ],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert out.exists() and out.stat().st_size > 1000


@pytest.mark.integration
def test_quality_spider_script_runs_without_error(tmp_path):
    out = tmp_path / "spider.pdf"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aedist.plot_quality_spider",
            "--input",
            "experiments/derived/sota_cross_eval.csv",
            "--config",
            "experiments/quality_spider_config.yaml",
            "--output",
            str(out),
        ],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert out.exists() and out.stat().st_size > 1000
