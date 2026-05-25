"""Tests for aedist.plot_exp2_arms_comparison."""

import csv

from aedist.plot_exp2_arms_comparison import _load_csv, make_figure


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
