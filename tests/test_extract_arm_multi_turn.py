"""Tests for extract_arm_multi_turn."""

from __future__ import annotations

import json
from pathlib import Path

from aedist.extract_arm_multi_turn import (
    _count_inventory_rows,
    extract_agent_name,
    extract_bibliography,
    extract_output_text,
    find_last_turn,
    find_turns_descending,
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


def test_extract_output_text_mistral_content_blocks() -> None:
    """Mistral Agents return ``outputs[].content`` as a list of mixed blocks.

    The report text lives in ``type="text"`` blocks interleaved with
    ``type="tool_reference"`` blocks (citations). Extraction must concatenate
    the text blocks into a non-empty narrative carrying the markdown table.
    """
    raw = {
        "object": "conversation.response",
        "outputs": [
            {
                "type": "message.output",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Here is the inventory:\n\n"},
                    {
                        "type": "tool_reference",
                        "tool": "web_search",
                        "title": "EVN",
                        "url": "https://example.invalid",
                    },
                    {
                        "type": "text",
                        "text": (
                            "| Name | Fuel | Capacity | Status | COD | Province |\n"
                            "| --- | --- | --- | --- | --- | --- |\n"
                            "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n"
                            "| Uong Bi | Coal | 330 | Operating | 2011 | Quang Ninh |\n"
                        ),
                    },
                ],
            }
        ],
    }

    text = extract_output_text(raw)
    assert text, "mistral content-block payload must yield non-empty text"
    assert "Pha Lai" in text
    assert _count_inventory_rows(text) > 0


def test_process_batch_falls_back_to_raw_when_record_text_empty(tmp_path: Path) -> None:
    """mistral-direct writes the report only into the sibling .raw.json.

    Its .record.json carries an empty ``justification`` / ``result_summary``,
    so ``extract_output_text`` returns ``""`` on the record. ``process_batch``
    must then fall back to the matching ``.raw.json`` for the same turn.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run01"
    agent_dir = run_dir / "mistral_run01"
    agent_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "mistral",
            "status": "pass",
            "total_cost_usd": 1.0,
            "wall_s": 1.0,
            "turns": 2,
            "class_trace": "report,report",
            "inventory_rows": 0,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    # Text-less record (mistral-direct shape): justification is None and
    # result_summary has no narrative.
    record = {
        "justification": None,
        "result_summary": {"status": "ok", "f1": None},
        "method_params": {"model": "mistral-large-2512"},
    }
    (agent_dir / "mistral_turn_02.record.json").write_text(json.dumps(record), encoding="utf-8")

    # The report lives only in the sibling raw payload.
    raw_payload = {
        "object": "conversation.response",
        "outputs": [
            {
                "type": "message.output",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "| Name | Fuel | Capacity | Status | COD | Province |\n"
                            "| --- | --- | --- | --- | --- | --- |\n"
                            "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n"
                            "| Uong Bi | Coal | 330 | Operating | 2011 | Quang Ninh |\n"
                        ),
                    }
                ],
            }
        ],
    }
    (agent_dir / "mistral_turn_02.raw.json").write_text(json.dumps(raw_payload), encoding="utf-8")

    process_batch(input_dir, output_dir)

    meta = json.loads((output_dir / "mistral_run01.json").read_text(encoding="utf-8"))
    assert meta["narrative_chars"] > 0
    assert meta["n_rows"] == 2
    assert "Pha Lai" in (output_dir / "mistral_run01.md").read_text(encoding="utf-8")


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


def test_find_turns_descending_orders_most_recent_first(tmp_path: Path) -> None:
    agent_dir = tmp_path / "testagent_run01"
    agent_dir.mkdir(parents=True)
    for n in (1, 2, 10):
        (agent_dir / f"testagent_turn_{n:02d}.record.json").write_text("{}")

    turns = find_turns_descending(agent_dir)
    nums = [int(p.name.split("_turn_")[1].split(".")[0]) for p in turns]
    assert nums == [10, 2, 1]
    # find_last_turn must still return the highest-numbered turn.
    assert find_last_turn(agent_dir) == turns[0]


def test_process_batch_falls_back_to_earlier_turn_when_last_has_no_table(
    tmp_path: Path,
) -> None:
    """SOTA arm4 anthropic run04: the final turn is a short meta-message
    ("the inventory table … has been produced in full above … budget won't
    permit more") with no inventory rows, while the actual table lives in an
    earlier turn. process_batch must scan earlier turns and adopt the one that
    carries an inventory table.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    run_dir = input_dir / "run04"
    agent_dir = run_dir / "testagent_run04"
    agent_dir.mkdir(parents=True)

    summary = [
        {
            "agent": "testagent",
            "status": "pass",
            "total_cost_usd": 5.0,
            "wall_s": 800.0,
            "turns": 4,
            "class_trace": "no_report,no_report,report,no_report",
            "inventory_rows": 2,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    inventory_text = (
        "Here is the final inventory.\n\n"
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n"
        "| Uong Bi | Coal | 330 | Operating | 2011 | Quang Ninh |\n"
    )
    meta_message = (
        "The inventory table and bibliography have been produced in full "
        "above. The remaining budget will not permit further searches."
    )
    # Turn 03 carries the table; turn 04 is the budget meta-message.
    (agent_dir / "testagent_turn_03.record.json").write_text(
        json.dumps({"output": inventory_text, "method_params": {"model": "claude-x"}}),
        encoding="utf-8",
    )
    (agent_dir / "testagent_turn_04.record.json").write_text(
        json.dumps({"output": meta_message, "method_params": {"model": "claude-x"}}),
        encoding="utf-8",
    )

    process_batch(input_dir, output_dir)

    meta = json.loads((output_dir / "testagent_run04.json").read_text(encoding="utf-8"))
    assert meta["n_rows"] == 2
    md = (output_dir / "testagent_run04.md").read_text(encoding="utf-8")
    assert "Pha Lai" in md  # adopted the earlier turn's text, not the meta-message
    assert "budget will not permit" not in md


def test_process_batch_keeps_last_turn_when_it_has_a_table(tmp_path: Path) -> None:
    """The earlier-turn fallback must not fire when the last turn already
    carries an inventory table — runs that already work stay unchanged.
    """
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
            "class_trace": "report,report",
            "inventory_rows": 1,
        }
    ]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    earlier = "| Name | Fuel | Capacity | Status | COD | Province |\n| --- | --- | --- | --- | --- | --- |\n| Old Plant | Coal | 100 | Retired | 1970 | Hanoi |\n"
    last = "| Name | Fuel | Capacity | Status | COD | Province |\n| --- | --- | --- | --- | --- | --- |\n| New Plant | Gas | 500 | Operating | 2024 | Da Nang |\n"
    (agent_dir / "testagent_turn_01.record.json").write_text(
        json.dumps({"output": earlier, "method_params": {"model": "m"}}), encoding="utf-8"
    )
    (agent_dir / "testagent_turn_02.record.json").write_text(
        json.dumps({"output": last, "method_params": {"model": "m"}}), encoding="utf-8"
    )

    process_batch(input_dir, output_dir)

    md = (output_dir / "testagent_run01.md").read_text(encoding="utf-8")
    assert "New Plant" in md  # used the last turn
    assert "Old Plant" not in md
