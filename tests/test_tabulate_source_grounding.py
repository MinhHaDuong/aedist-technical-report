"""Tests for aedist.tabulate_source_grounding loaders and formatting."""

import json

from aedist.tabulate_source_grounding import (
    _fmt_pct,
    _load_json_response_rows,
    _load_sourced_csv,
)


def test_fmt_pct_scales_and_formats() -> None:
    assert _fmt_pct(0.0) == "0.0\\%"
    assert _fmt_pct(1.0) == "100.0\\%"
    assert _fmt_pct(0.123) == "12.3\\%"


def test_load_sourced_csv_reads_rows(tmp_path) -> None:
    path = tmp_path / "run.csv"
    path.write_text(
        "name,fuel,source_1\nPha Lai,coal,EVN 2024\nVung Ang,coal,MOIT\n",
        encoding="utf-8",
    )
    rows = _load_sourced_csv(path)
    assert len(rows) == 2
    assert rows[0]["name"] == "Pha Lai"
    assert rows[1]["source_1"] == "MOIT"


def test_load_json_response_rows_extracts_fenced_csv(tmp_path) -> None:
    response = "Here is the table:\n```\nname,fuel\nPha Lai,coal\nVung Ang,coal\n```\n"
    path = tmp_path / "resp.json"
    path.write_text(json.dumps({"response": response}), encoding="utf-8")
    rows = _load_json_response_rows(path)
    assert len(rows) == 2
    assert any("Pha Lai" in str(v) for v in rows[0].values())


def test_load_json_response_rows_empty_response(tmp_path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"response": ""}), encoding="utf-8")
    assert _load_json_response_rows(path) == []
