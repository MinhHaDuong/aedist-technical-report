"""Tests for aedist.tabulate_exp2_bib_quality — per-(agent, arm) bib summaries."""

from aedist.tabulate_exp2_bib_quality import (
    _fmt_mean_range,
    _fmt_pct,
    _int_or_none,
    summarize_bib_quality,
)


def test_int_or_none_blank_and_literal_none() -> None:
    assert _int_or_none("") is None
    assert _int_or_none("None") is None
    assert _int_or_none("7") == 7


def test_fmt_mean_range_constant_and_spread() -> None:
    assert _fmt_mean_range([]) == "--"
    assert _fmt_mean_range([100, 100, 100]) == "100"
    assert _fmt_mean_range([90, 100, 110]) == "100 [90--110]"


def test_fmt_pct_handles_zero_denominator() -> None:
    # 50/100 and 0-denominator (counted as 0%) -> mean of 50 and 0 = 25.
    assert _fmt_pct([50, 1], [100, 0]) == "25\\%"
    assert _fmt_pct([], []) == "--"


def _row(agent: str, arm: str, run: int, n_rows: int, **kw) -> dict:
    base = {
        "agent": agent, "arm": arm, "run": run, "n_rows": n_rows,
        "src1_present": n_rows, "src2_present": 0, "src1_primary": n_rows,
        "notes_present": 0, "bib_entries": 5, "bib_primary": 5,
    }
    base.update(kw)
    return base


def test_summarize_excludes_zero_row_runs() -> None:
    rows = [
        _row("openai", "naive", 1, 100),
        _row("openai", "naive", 2, 0),  # degenerate, excluded from means
    ]
    summaries = summarize_bib_quality(rows)
    assert len(summaries) == 1
    s = summaries[0]
    assert s["n_total"] == 2
    assert s["n_valid"] == 1
    assert s["src1_present_pct"] == "100\\%"


def test_summarize_all_zero_runs_marks_dashes() -> None:
    rows = [_row("openai", "naive", 1, 0)]
    s = summarize_bib_quality(rows)[0]
    assert s["n_valid"] == 0
    assert s["n_rows"] == "--"
    assert s["bib_entries"] == "--"


def test_summarize_sorts_by_agent_then_arm() -> None:
    rows = [
        _row("qwen", "optimised", 1, 10),
        _row("anthropic", "naive", 1, 10),
        _row("anthropic", "optimised", 1, 10),
    ]
    order = [(s["agent"], s["arm"]) for s in summarize_bib_quality(rows)]
    assert order == [("anthropic", "naive"), ("anthropic", "optimised"), ("qwen", "optimised")]
