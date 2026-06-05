"""Tests for aedist.plot_exp2_arms_comparison."""

import csv
import json

from aedist.plot_exp2_arms_comparison import _load_csv, _load_pack_arm_rows, make_figure


def _write_csv(path, rows):
    fields = [
        "arm",
        "agent",
        "model",
        "run",
        "classification",
        "narrative_chars",
        "inventory_rows",
        "cost_usd",
        "wall_s",
        "turns",
    ]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _minimal_rows():
    base = [
        {
            "arm": arm,
            "agent": agent,
            "model": "m",
            "run": str(i + 1),
            "classification": "report",
            "narrative_chars": "15000",
            "inventory_rows": "50",
            "cost_usd": "0.50",
            "wall_s": "120.0",
            "turns": "1",
        }
        for arm in ("naive", "optimised", "arm3", "arm4")
        for agent in ("anthropic", "mistral", "openai", "qwen")
        for i in range(5)
    ]
    base[0]["classification"] = "no_report"
    base[0]["inventory_rows"] = "None"
    return base


def test_load_csv_parses_no_report(tmp_path):
    csv_path = tmp_path / "runs.csv"
    _write_csv(csv_path, _minimal_rows())
    rows = _load_csv(csv_path)
    assert len(rows) == 80
    assert {r["arm"] for r in rows} == {"arm1", "arm2", "arm3", "arm4"}
    no_report = [r for r in rows if not r["is_report"]]
    assert len(no_report) == 1
    assert no_report[0]["inventory_rows"] == 0


def test_make_figure_writes_pdf(tmp_path):
    csv_path = tmp_path / "runs.csv"
    _write_csv(csv_path, _minimal_rows())
    rows = _load_csv(csv_path)
    out = tmp_path / "fig.pdf"
    make_figure(rows, out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_load_pack_arm_rows_total_cost_usd(tmp_path):
    payload = {
        "agent": "anthropic",
        "model": "claude-opus-4-6",
        "run": 1,
        "classification": "report",
        "total_cost_usd": 0.93252,
        "n_rows": 12,
    }
    (tmp_path / "anthropic_run01.json").write_text(json.dumps(payload))
    rows = _load_pack_arm_rows(tmp_path, "arm4")
    assert len(rows) == 1
    assert rows[0]["cost_usd"] > 0


def test_all_false_positive_bars_are_red(tmp_path) -> None:
    """0403: every FP (negative) bar must use red (COLOR_ALERT), matching the
    'red = false positives' convention unified in PR #678 (ticket 0349)."""
    from matplotlib.colors import to_hex

    from aedist.util import COLOR_ALERT

    # Synthetic rows with one FP bar per arm (scored arms only).
    csv_path = tmp_path / "rows.csv"
    rows_data = [
        {
            "arm": "arm1",
            "agent": "anthropic",
            "model": "claude-opus-4-6",
            "run": "1",
            "classification": "report",
            "narrative_chars": "15000",
            "inventory_rows": "114",
            "cost_usd": "0.4",
            "wall_s": "120.0",
            "turns": "1",
        },
        {
            "arm": "arm2",
            "agent": "mistral",
            "model": "mistral-large-2512",
            "run": "1",
            "classification": "report",
            "narrative_chars": "15000",
            "inventory_rows": "120",
            "cost_usd": "0.5",
            "wall_s": "120.0",
            "turns": "5",
        },
    ]
    _write_csv(csv_path, rows_data)

    # Load and inject n_matched manually (scored arms have this field).
    rows = _load_csv(csv_path)
    rows[0]["n_matched"] = 100  # 14 FP
    rows[1]["n_matched"] = 110  # 10 FP

    fig = make_figure(rows, tmp_path / "fig.pdf")
    ax = fig.axes[0]  # coverage panel
    negative_bars = [p for p in ax.patches if p.get_height() < 0]
    assert len(negative_bars) == 2, f"expected 2 FP bars (arm1+arm2), got {len(negative_bars)}"
    colors = {to_hex(p.get_facecolor()[:3]) for p in negative_bars}
    assert colors == {to_hex(COLOR_ALERT)}, (
        f"FP bars must all be red (COLOR_ALERT={COLOR_ALERT}); got {colors}"
    )
