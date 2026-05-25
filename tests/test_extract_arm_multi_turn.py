"""Tests for extract_arm_multi_turn."""

from __future__ import annotations

import json
from pathlib import Path

from aedist.extract_arm_multi_turn import (
    extract_agent_name,
    extract_bibliography,
    extract_output_text,
    find_last_turn,
    process_batch,
)


def test_extract_agent_name() -> None:
    assert extract_agent_name("anthropic_run01") == "anthropic"
    assert extract_agent_name("mistral_run10") == "mistral"
    assert extract_agent_name("openai_run02") == "openai"


def test_find_last_turn_uses_highest_number_not_alphabetic(tmp_path: Path) -> None:
    """Alphabetic sort would place turn_10 before turn_2; numeric sort must win."""
    agent_dir = tmp_path / "testagent_run01"
    agent_dir.mkdir()

    (agent_dir / "testagent_turn_01.record.json").write_text('{"output": "t1"}')
    (agent_dir / "testagent_turn_02.record.json").write_text('{"output": "t2"}')
    (agent_dir / "testagent_turn_10.record.json").write_text('{"output": "t10"}')

    last = find_last_turn(agent_dir)
    assert last is not None
    assert last.name == "testagent_turn_10.record.json"


def test_class_trace_split_into_list(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run01"
    agent_dir = run_dir / "testagent_run01"
    agent_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "testagent",
            "status": "pass",
            "total_cost_usd": 1.0,
            "wall_s": 10.0,
            "turns": 2,
            "class_trace": "no_report,report",
            "inventory_rows": 5,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary))

    record = {"output": "hello world", "method_params": {"model": "gpt-4"}}
    (agent_dir / "testagent_turn_01.record.json").write_text(json.dumps(record))

    process_batch(input_dir, output_dir)

    meta_path = output_dir / "testagent_run01.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["class_trace"] == ["no_report", "report"]


def test_bib_extraction_with_sources_heading(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run01"
    agent_dir = run_dir / "testagent_run01"
    agent_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "testagent",
            "status": "pass",
            "total_cost_usd": 1.0,
            "wall_s": 5.0,
            "turns": 1,
            "class_trace": "report",
            "inventory_rows": 3,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary))

    text = (
        "# Report\n\nSome prose here.\n\n"
        "## Sources\n\n"
        "1. Foo et al.\n"
        "2. Bar et al.\n\n"
        "End of doc.\n"
    )
    record = {"output": text, "method_params": {"model": "gpt-4"}}
    (agent_dir / "testagent_turn_01.record.json").write_text(json.dumps(record))

    process_batch(input_dir, output_dir)

    bib_path = output_dir / "testagent_run01_bib.md"
    assert bib_path.exists()
    bib_content = bib_path.read_text()
    assert "## Sources" in bib_content
    assert "1. Foo et al." in bib_content
    assert "2. Bar et al." in bib_content

    meta = json.loads((output_dir / "testagent_run01.json").read_text())
    assert meta["n_bib_entries"] == 2


def test_skip_error_status_silently(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run01"
    run_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "goodagent",
            "status": "pass",
            "total_cost_usd": 1.0,
            "wall_s": 10.0,
            "turns": 1,
            "class_trace": "report",
            "inventory_rows": 5,
        },
        {
            "agent": "badagent",
            "status": "error",
            "total_cost_usd": 0.0,
            "wall_s": 0.0,
            "turns": 0,
            "class_trace": "",
            "inventory_rows": 0,
        },
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary))

    good_dir = run_dir / "goodagent_run01"
    good_dir.mkdir()
    (good_dir / "goodagent_turn_01.record.json").write_text(
        json.dumps({"output": "ok", "method_params": {"model": "gpt-4"}})
    )

    bad_dir = run_dir / "badagent_run01"
    bad_dir.mkdir()
    (bad_dir / "badagent_turn_01.record.json").write_text(
        json.dumps({"output": "fail", "method_params": {"model": "gpt-4"}})
    )

    process_batch(input_dir, output_dir)

    assert (output_dir / "goodagent_run01.json").exists()
    assert (output_dir / "goodagent_run01.md").exists()
    assert not (output_dir / "badagent_run01.json").exists()
    assert not (output_dir / "badagent_run01.md").exists()


def test_model_extracted_from_record(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run01"
    agent_dir = run_dir / "testagent_run01"
    agent_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "testagent",
            "status": "pass",
            "total_cost_usd": 1.0,
            "wall_s": 1.0,
            "turns": 1,
            "class_trace": "report",
            "inventory_rows": 1,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary))

    record = {
        "justification": {"output_text": "report text"},
        "method_params": {"model": "claude-opus-4-6"},
    }
    (agent_dir / "testagent_turn_01.record.json").write_text(json.dumps(record))

    process_batch(input_dir, output_dir)

    meta = json.loads((output_dir / "testagent_run01.json").read_text())
    assert meta["model"] == "claude-opus-4-6"
    assert (output_dir / "testagent_run01.md").read_text() == "report text"


def test_extract_output_text_fallbacks() -> None:
    assert extract_output_text({"output": "out"}) == "out"
    assert extract_output_text({"text": "txt"}) == "txt"
    assert extract_output_text({"content": "cnt"}) == "cnt"
    assert extract_output_text({"response": "resp"}) == "resp"
    assert extract_output_text({"justification": {"output_text": "jtxt"}}) == "jtxt"
    assert extract_output_text({"other": "x"}) == ""


def test_extract_bibliography_no_heading() -> None:
    text, n = extract_bibliography("just some text")
    assert text is None
    assert n == 0


def test_process_batch_counts_inventory_rows_from_raw_payload(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run01"
    agent_dir = run_dir / "testagent_run01"
    agent_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "testagent",
            "status": "pass",
            "total_cost_usd": 1.0,
            "wall_s": 1.0,
            "turns": 2,
            "class_trace": "report,report",
            "inventory_rows": 0,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    raw_payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": (
                            "| Name | Fuel | Capacity | Status | COD | Province |\n"
                            "| --- | --- | --- | --- | --- | --- |\n"
                            "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n"
                            "| Uong Bi | Coal | 330 | Operating | 2011 | Quang Ninh |\n"
                        ),
                    }
                ],
            }
        ]
    }
    (agent_dir / "testagent_turn_02.raw.json").write_text(
        json.dumps(raw_payload), encoding="utf-8"
    )

    process_batch(input_dir, output_dir)

    meta = json.loads((output_dir / "testagent_run01.json").read_text(encoding="utf-8"))
    assert meta["n_rows"] == 2
