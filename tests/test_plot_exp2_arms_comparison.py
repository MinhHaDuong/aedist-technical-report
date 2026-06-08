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
    make_figure(rows, out, exp1_summary={})
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

    fig = make_figure(rows, tmp_path / "fig.pdf", exp1_summary={})
    ax = fig.axes[0]  # coverage panel
    negative_bars = [p for p in ax.patches if p.get_height() < 0]
    assert len(negative_bars) == 2, f"expected 2 FP bars (arm1+arm2), got {len(negative_bars)}"
    colors = {to_hex(p.get_facecolor()[:3]) for p in negative_bars}
    assert colors == {to_hex(COLOR_ALERT)}, (
        f"FP bars must all be red (COLOR_ALERT={COLOR_ALERT}); got {colors}"
    )


def test_exp1_baseline_bars_rendered(tmp_path) -> None:
    """0463: the comparison figure must draw E1 hatched baseline bars for each
    agent, matching the visual language from plot_exp2_arms_split."""
    from matplotlib.colors import to_hex

    from aedist.plot_exp2_arms_comparison import _AGENT_EXP1_SLUG
    from aedist.util import COLOR_ALERT

    # Minimal Exp2 rows: one scored row per agent.
    csv_path = tmp_path / "rows.csv"
    rows_data = [
        {
            "arm": "arm1",
            "agent": agent,
            "model": "m",
            "run": "1",
            "classification": "report",
            "narrative_chars": "15000",
            "inventory_rows": "80",
            "cost_usd": "0.50",
            "wall_s": "120.0",
            "turns": "1",
        }
        for agent in ("anthropic", "mistral", "openai", "qwen")
    ]
    _write_csv(csv_path, rows_data)
    rows = _load_csv(csv_path)
    for r in rows:
        r["n_matched"] = 70  # 10 FP each

    # Synthetic Exp1 summary keyed by exp1 slugs — one per agent.
    exp1_summary = {
        slug: {
            "median_tp": 60,
            "min_tp": 55,
            "max_tp": 65,
            "median_fp": 8,
            "min_fp": 5,
            "max_fp": 10,
            "mean_cost": 0.30,
            "min_cost": 0.28,
            "max_cost": 0.32,
        }
        for slug in _AGENT_EXP1_SLUG.values()
    }

    fig = make_figure(rows, tmp_path / "fig.pdf", exp1_summary=exp1_summary)

    # Coverage panel: should have 4 E1 positive bars (hatched) + 4 arm1 positive
    # bars + 4 E1 FP bars (hatched, negative) + 4 arm1 FP bars (negative).
    cov_ax = fig.axes[0]
    hatched = [p for p in cov_ax.patches if p.get_hatch()]
    assert len(hatched) >= 4, (
        f"expected at least 4 hatched E1 bars in coverage panel, got {len(hatched)}"
    )
    # All negative hatched bars must be red (FP colour).
    neg_hatched = [p for p in hatched if p.get_height() < 0]
    if neg_hatched:
        colors = {to_hex(p.get_facecolor()[:3]) for p in neg_hatched}
        assert colors == {to_hex(COLOR_ALERT)}, (
            f"E1 FP bars must be red; got {colors}"
        )

    # Cost panel: should have 4 hatched E1 bars.
    cost_ax = fig.axes[1]
    cost_hatched = [p for p in cost_ax.patches if p.get_hatch()]
    assert len(cost_hatched) == 4, (
        f"expected 4 hatched E1 bars in cost panel, got {len(cost_hatched)}"
    )


import pytest  # noqa: E402 — placed after test functions to survive ruff hook


@pytest.mark.integration
def test_exp1_slugs_resolve_in_mart() -> None:
    """0463: every agent's Exp1 slug must appear in the mart-derived summary,
    otherwise the E1 bar silently disappears for that agent."""
    from aedist.plot_exp2_arms_comparison import _AGENT_EXP1_SLUG, load_exp1_summary

    summary = load_exp1_summary()
    for agent, slug in _AGENT_EXP1_SLUG.items():
        assert slug in summary, (
            f"Exp1 slug {slug!r} for agent {agent!r} not found in mart summary; "
            f"available slugs: {sorted(summary)}"
        )
