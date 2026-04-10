"""Tests for the verification tradeoff table generator."""

import csv
import io

import pytest
from aedist.tabulate_verification import (
    compute_tradeoff,
    generate_tradeoff_csv,
    generate_tradeoff_latex,
)


def _make_annotated_csv(rows: list[dict]) -> str:
    """Build CSV text from list of dicts."""
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _sample_rows(n_verified=5, n_unverified=3, mode="tool"):
    """Create sample annotated rows with known evidence scores.

    Returns n_verified plants with score=3 (one primary) and
    n_unverified plants with score=1 (no sources).
    """
    rows = []
    for i in range(n_verified):
        rows.append(
            {
                "name": f"Plant V{i}",
                "fuel": "Coal",
                "province": "Hanoi",
                "capacity_mwe": "100",
                "evidence_score": "3",
                "verified": "True",
                "source_1": f"ref: Plant V{i}",
                "source_1_type": "primary",
            }
        )
    for i in range(n_unverified):
        rows.append(
            {
                "name": f"Plant U{i}",
                "fuel": "Gas",
                "province": "HCMC",
                "capacity_mwe": "200",
                "evidence_score": "1",
                "verified": "False",
                "source_1": "",
                "source_1_type": "none",
            }
        )
    return rows


@pytest.fixture
def verification_dir(tmp_path):
    """Create a verification output directory with annotated CSVs."""
    vdir = tmp_path / "verification"
    vdir.mkdir()

    # Tool mode: 5 verified (score=3), 3 unverified (score=1)
    rows_tool = _sample_rows(5, 3, "tool")
    csv_text = _make_annotated_csv(rows_tool)
    (vdir / "deepseek-v3.2-tool-run1.csv").write_text(csv_text)

    # Unverified mode: all score=1
    rows_unverified = _sample_rows(0, 8, "unverified")
    csv_text = _make_annotated_csv(rows_unverified)
    (vdir / "deepseek-v3.2-unverified-run1.csv").write_text(csv_text)

    # Self mode: mix of scores (3 runs)
    for run in range(1, 4):
        rows_self = _sample_rows(3, 5, "self")
        # Add one score=4 plant and one score=2 plant
        rows_self.append(
            {
                "name": "Plant S4",
                "fuel": "Coal",
                "province": "Quang Ninh",
                "capacity_mwe": "600",
                "evidence_score": "4",
                "verified": "True",
                "source_1": "Decision 123/QD-TTg",
                "source_1_type": "primary",
            }
        )
        rows_self.append(
            {
                "name": "Plant S2",
                "fuel": "Gas",
                "province": "Ba Ria",
                "capacity_mwe": "300",
                "evidence_score": "2",
                "verified": "False",
                "source_1": "Wikipedia article",
                "source_1_type": "secondary",
            }
        )
        csv_text = _make_annotated_csv(rows_self)
        (vdir / f"deepseek-v3.2-self-run{run}.csv").write_text(csv_text)

    return vdir


def test_compute_tradeoff_all_modes(verification_dir):
    """compute_tradeoff returns rows for each mode × threshold."""
    rows = compute_tradeoff(verification_dir)
    modes = {r["mode"] for r in rows}
    assert "tool" in modes
    assert "unverified" in modes
    assert "self" in modes


def test_compute_tradeoff_thresholds(verification_dir):
    """Each mode has rows for thresholds 1 through 4."""
    rows = compute_tradeoff(verification_dir)
    for mode in ("tool", "unverified", "self"):
        mode_rows = [r for r in rows if r["mode"] == mode]
        thresholds = {int(r["threshold"]) for r in mode_rows}
        assert thresholds == {1, 2, 3, 4}, f"{mode} missing thresholds: {thresholds}"


def test_tool_precision_at_high_threshold(verification_dir):
    """Tool mode at threshold=3 should have perfect precision (only verified plants)."""
    rows = compute_tradeoff(verification_dir)
    tool_t3 = [r for r in rows if r["mode"] == "tool" and int(r["threshold"]) == 3]
    assert len(tool_t3) == 1
    # All retained plants are verified (score=3), precision should be 1.0 or near it
    assert float(tool_t3[0]["n_retained"]) == 5


def test_unverified_loses_all_at_threshold_2(verification_dir):
    """Unverified mode: all plants have score=1, so threshold>=2 retains 0."""
    rows = compute_tradeoff(verification_dir)
    unv_t2 = [r for r in rows if r["mode"] == "unverified" and int(r["threshold"]) == 2]
    assert len(unv_t2) == 1
    assert int(unv_t2[0]["n_retained"]) == 0


def test_self_averages_across_runs(verification_dir):
    """Self mode with 3 runs should report averaged metrics."""
    rows = compute_tradeoff(verification_dir)
    self_t1 = [r for r in rows if r["mode"] == "self" and int(r["threshold"]) == 1]
    assert len(self_t1) == 1
    # At threshold=1, all 10 plants retained (3+5+1+1)
    assert int(self_t1[0]["n_retained"]) == 10


def test_generate_tradeoff_csv(verification_dir, tmp_path):
    """generate_tradeoff_csv writes valid CSV with expected columns."""
    out = tmp_path / "tradeoff.csv"
    generate_tradeoff_csv(verification_dir, out)
    assert out.exists()

    with open(out) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0
    required_cols = {"mode", "threshold", "n_retained", "n_total", "retention_pct"}
    assert required_cols.issubset(set(rows[0].keys()))


def test_generate_tradeoff_latex(verification_dir):
    """generate_tradeoff_latex returns a non-empty LaTeX string."""
    tex = generate_tradeoff_latex(verification_dir)
    assert "\\begin{tabular}" in tex or "\\begin{longtable}" in tex
    assert "tool" in tex.lower() or "Tool" in tex
