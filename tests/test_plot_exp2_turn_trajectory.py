"""Tests for aedist.plot_exp2_turn_trajectory."""

import json

import pytest

from aedist.plot_exp2_turn_trajectory import (
    _count_table_rows,
    _extract_text,
    load_run_turns,
    make_figure,
)

# --- _extract_text -----------------------------------------------------------


def test_extract_text_anthropic():
    d = {
        "content": [
            {"type": "thinking", "thinking": "Let me search..."},
            {"type": "text", "text": "Here is the inventory."},
            {"type": "tool_use", "name": "web_search"},
            {"type": "text", "text": " Row 1."},
        ]
    }
    assert _extract_text(d) == "Here is the inventory.  Row 1."


def test_extract_text_qwen():
    d = {"output": {"choices": [{"message": {"role": "assistant", "content": "Qwen output"}}]}}
    assert _extract_text(d) == "Qwen output"


def test_extract_text_openai():
    d = {
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": "OpenAI output"},
                    {"type": "reasoning", "text": "ignored"},
                ]
            }
        ]
    }
    assert _extract_text(d) == "OpenAI output"


def test_extract_text_openai_null_content():
    d = {
        "output": [
            {"content": None},
            {"content": [{"type": "output_text", "text": "Recovered output"}]},
        ]
    }
    assert _extract_text(d) == "Recovered output"


def test_extract_text_mistral():
    d = {
        "outputs": [
            {"type": "tool.execution", "content": "ignored"},
            {"type": "message.output", "content": [{"text": "Mistral output"}]},
        ]
    }
    assert _extract_text(d) == "Mistral output"


def test_extract_text_unknown_returns_empty():
    assert _extract_text({"unexpected": "structure"}) == ""


# --- _count_table_rows -------------------------------------------------------


def test_count_table_rows_basic():
    text = "| Name | Cap |\n|------|-----|\n| Plant A | 600 |\n| Plant B | 1200 |\n"
    assert _count_table_rows(text) == 2


def test_count_table_rows_trailing_spaces():
    text = "| Name | Cap |  \n|------|-----|  \n| Plant A | 600 |  \n"
    assert _count_table_rows(text) == 1


def test_count_table_rows_no_table():
    assert _count_table_rows("Just prose, no table here.") == 0


def test_count_table_rows_ignores_summary_tables():
    text = (
        "| Name | Fuel | Province | Capacity | Status | COD |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
        "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n\n"
        "| Fuel | Capacity |\n"
        "| --- | --- |\n"
        "| Coal | 1670 |\n"
    )
    assert _count_table_rows(text) == 2


# --- load_run_turns ----------------------------------------------------------


def _write_turn(run_dir, agent, turn_num, text, cls):
    raw = run_dir / f"{agent}_turn_{turn_num:02d}.raw.json"
    raw.write_text(json.dumps({"content": [{"type": "text", "text": text}]}), encoding="utf-8")
    clf = run_dir / f"{agent}_turn_{turn_num:02d}.classification.json"
    clf.write_text(json.dumps({"class": cls}), encoding="utf-8")


def test_load_run_turns_basic(tmp_path):
    run_dir = tmp_path / "qwen_run01"
    run_dir.mkdir()
    table = "| Name | Cap |\n|---|---|\n| A | 600 |\n| B | 300 |\n"
    _write_turn(run_dir, "qwen", 1, table, "report")
    _write_turn(run_dir, "qwen", 2, table, "report")
    turns = load_run_turns(tmp_path, "qwen", 1)
    assert len(turns) == 2
    assert turns[0] == {"turn": 1, "rows": 2, "cls": "report"}
    assert turns[1] == {"turn": 2, "rows": 2, "cls": "report"}


def test_load_run_turns_no_report_classification(tmp_path):
    run_dir = tmp_path / "anthropic_run01"
    run_dir.mkdir()
    _write_turn(run_dir, "anthropic", 1, "Some prose, no table.", "no_report")
    turns = load_run_turns(tmp_path, "anthropic", 1)
    assert turns[0]["cls"] == "no_report"
    assert turns[0]["rows"] == 0


def test_load_run_turns_missing_dir(tmp_path):
    assert load_run_turns(tmp_path, "openai", 99) == []


# --- make_figure -------------------------------------------------------------


def test_make_figure_writes_pdf(tmp_path):
    # Build a minimal probes/ structure for two agents, one run each, two turns
    for agent in ("anthropic", "qwen"):
        run_dir = tmp_path / f"{agent}_run01"
        run_dir.mkdir()
        table = "| Name | Cap |\n|---|---|\n| A | 600 |\n"
        for t in (1, 2):
            _write_turn(run_dir, agent, t, table, "report")

    out = tmp_path / "fig.pdf"
    make_figure(tmp_path, out)
    assert out.exists()
    assert out.stat().st_size > 1000


@pytest.mark.adherence
def test_ruff():
    import subprocess

    result = subprocess.run(["uv", "run", "ruff", "check", "."], capture_output=True)
    assert result.returncode == 0, result.stdout.decode()
