import subprocess
import sys

import pytest


@pytest.mark.integration
def test_script_runs_without_error(tmp_path):
    out = tmp_path / "fig.pdf"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aedist.plot_exp2_coverage_certainty",
            "--input",
            "report/inputs/generated/tab_exp2_bib_quality.csv",
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
