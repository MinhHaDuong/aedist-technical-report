"""Tests for aedist.plot_exp2_arms_split — arm canonicalisation, row loading, FP colour."""

import csv

from aedist.plot_exp2_arms_split import _canonical_arm, _mean, load_exp2_rows


def test_canonical_arm_maps_named_arms() -> None:
    assert _canonical_arm("naive") == "arm1"
    assert _canonical_arm("optimised") == "arm2"
    assert _canonical_arm("arm3") == "arm3"  # passthrough


def test_mean_empty_is_zero() -> None:
    assert _mean([]) == 0.0
    assert _mean([2.0, 4.0]) == 3.0


def test_load_exp2_rows_types_and_blank_handling(tmp_path) -> None:
    path = tmp_path / "rows.csv"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "run",
                "inventory_rows",
                "n_matched",
                "cost_usd",
                "arm",
                "classification",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "run": "1",
                "inventory_rows": "114",
                "n_matched": "100",
                "cost_usd": "0.42",
                "arm": "naive",
                "classification": "report",
            }
        )
        writer.writerow(
            {
                "run": "2",
                "inventory_rows": "",
                "n_matched": "",
                "cost_usd": "",
                "arm": "optimised",
                "classification": "no_report",
            }
        )

    rows = load_exp2_rows(path)
    assert rows[0]["run"] == 1
    assert rows[0]["inventory_rows"] == 114
    assert rows[0]["n_matched"] == 100
    assert rows[0]["cost_usd"] == 0.42
    assert rows[0]["arm"] == "arm1"
    assert rows[0]["is_report"] is True

    # Blank numerics coerced; missing n_matched -> None; cost defaults to 0.0.
    assert rows[1]["inventory_rows"] == 0
    assert rows[1]["n_matched"] is None
    assert rows[1]["cost_usd"] == 0.0
    assert rows[1]["arm"] == "arm2"
    assert rows[1]["is_report"] is False


def test_all_false_positive_bars_are_red(tmp_path) -> None:
    """0349: every FP (negative) bar — E1 baseline AND Exp2 arms — must use the
    same red (COLOR_ALERT), matching the title's 'red = false positives'."""
    from matplotlib.colors import to_hex

    from aedist.plot_exp2_arms_split import make_coverage_figure
    from aedist.util import COLOR_ALERT

    exp2_rows = [
        {
            "run": 1,
            "agent": "anthropic",
            "arm": "arm1",
            "inventory_rows": 114,
            "n_matched": 100,  # halluc = 14 -> one negative bar
            "cost_usd": 0.4,
            "classification": "report",
            "is_report": True,
        }
    ]
    exp1_summary = {
        "claude-opus-4.6": {
            "median_tp": 80,
            "min_tp": 79,
            "max_tp": 82,
            "median_fp": 16,  # -> one negative E1 bar
            "min_fp": 9,
            "max_fp": 17,
            "mean_cost": 0.42,
            "min_cost": 0.40,
            "max_cost": 0.45,
        }
    }

    fig = make_coverage_figure(exp2_rows, exp1_summary, tmp_path / "cov.pdf")
    ax = fig.axes[0]
    negative_bars = [p for p in ax.patches if p.get_height() < 0]
    assert len(negative_bars) == 2, f"expected E1 + arm1 FP bars, got {len(negative_bars)}"
    colors = {to_hex(p.get_facecolor()[:3]) for p in negative_bars}
    assert colors == {to_hex(COLOR_ALERT)}, (
        f"FP bars must all be red (COLOR_ALERT={COLOR_ALERT}); got {colors}"
    )
