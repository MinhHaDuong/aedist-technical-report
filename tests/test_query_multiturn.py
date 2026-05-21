"""Tests for aedist.query_multiturn — multi-turn conversational queries."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_mock_response(
    content="name,fuel\nPlant A,coal", prompt_tokens=100, completion_tokens=200
):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.choices[0].finish_reason = "stop"
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    resp.usage.model_dump.return_value = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
    return resp


def _setup_files(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create minimal test files, return (prompt, followups, models, output)."""
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("List power plants.")

    followups = tmp_path / "followups.txt"
    followups.write_text("Any missing?\nCheck LNG plants too.\n")

    models = tmp_path / "models.yaml"
    models.write_text(
        "- id: test/tiny-model\n"
        "  name: Tiny\n"
        "  price_per_mtok_in: 1.0\n"
        "  price_per_mtok_out: 2.0\n"
        "  context_window: 8000\n"
        "  country: US\n"
        "  architecture: dense\n"
        "  size_class: edge\n"
    )

    output = tmp_path / "out"
    return prompt, followups, models, output


@patch("aedist.harness.OpenAI")
def test_multiturn_produces_correct_turn_structure(mock_openai_cls, tmp_path):
    """Output JSON has turns array with alternating user/assistant messages."""
    mock_client = MagicMock()
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _make_mock_response(f"Response {call_count}")

    mock_client.chat.completions.create.side_effect = side_effect
    mock_openai_cls.return_value = mock_client

    prompt, followups, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(
            sys,
            "argv",
            [
                "query_multiturn",
                "--prompt",
                str(prompt),
                "--followups",
                str(followups),
                "--models",
                str(models),
                "--output",
                str(output),
            ],
        ):
            from aedist.query_multiturn import main

            main()

    json_files = list(output.rglob("*.json"))
    assert len(json_files) == 1

    record = json.loads(json_files[0].read_text())
    turns = record["turns"]

    # Initial prompt + response (turn 0), then 2 followups + responses (turns 1, 2)
    # = 6 messages total: user, assistant, user, assistant, user, assistant
    assert len(turns) == 6
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"
    assert turns[2]["role"] == "user"
    assert turns[3]["role"] == "assistant"
    assert turns[4]["role"] == "user"
    assert turns[5]["role"] == "assistant"

    # Turn numbers
    assert turns[0]["turn"] == 0
    assert turns[1]["turn"] == 0
    assert turns[2]["turn"] == 1
    assert turns[3]["turn"] == 1

    # Assistant turns have timing
    assert "wall_seconds" in turns[1]
    assert "cost_usd" in turns[1]

    # Totals
    assert "total_cost_usd" in record
    assert "total_wall_seconds" in record
    assert "model_metadata" in record


@patch("aedist.harness.OpenAI")
def test_multiturn_followups_parsed_from_file(mock_openai_cls, tmp_path):
    """Followup prompts are correctly parsed from file (one per line)."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, followups, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(
            sys,
            "argv",
            [
                "query_multiturn",
                "--prompt",
                str(prompt),
                "--followups",
                str(followups),
                "--models",
                str(models),
                "--output",
                str(output),
            ],
        ):
            from aedist.query_multiturn import main

            main()

    # 3 API calls: initial + 2 followups
    assert mock_client.chat.completions.create.call_count == 3


@patch("aedist.harness.OpenAI")
def test_multiturn_budget_guard(mock_openai_cls, tmp_path):
    """Budget guard works across turns within a conversation."""
    mock_client = MagicMock()
    # Each call: 100 prompt + 200 completion tokens
    # cost = (100*1.0 + 200*2.0)/1e6 = 0.0005
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, followups, models, output = _setup_files(tmp_path)

    # Budget 0.0008 allows 1 call but not 2
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(
            sys,
            "argv",
            [
                "query_multiturn",
                "--prompt",
                str(prompt),
                "--followups",
                str(followups),
                "--models",
                str(models),
                "--output",
                str(output),
                "--repeat",
                "3",
                "--budget-usd",
                "0.0008",
            ],
        ):
            from aedist.query_multiturn import main

            main()

    json_files = list(output.rglob("*.json"))
    # Should produce fewer than 3 files
    assert len(json_files) < 3


@patch("aedist.harness.OpenAI")
def test_multiturn_repeat(mock_openai_cls, tmp_path):
    """--repeat 2 produces 2 files per model."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, followups, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(
            sys,
            "argv",
            [
                "query_multiturn",
                "--prompt",
                str(prompt),
                "--followups",
                str(followups),
                "--models",
                str(models),
                "--output",
                str(output),
                "--repeat",
                "2",
            ],
        ):
            from aedist.query_multiturn import main

            main()

    json_files = list(output.rglob("*.json"))
    assert len(json_files) == 2


def _make_mock_client():
    """Create a mock client whose create() returns incrementing responses."""
    client = MagicMock()
    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        return _make_mock_response(f"Response {call_count['n']}")

    client.chat.completions.create.side_effect = side_effect
    return client


def test_context_overflow_guard():
    """run_conversation stops when estimated tokens exceed context window."""
    from aedist.harness import BudgetTracker
    from aedist.query_multiturn import run_conversation

    client = _make_mock_client()
    # context_window=50 tokens → limit=40 (80%).
    # Prompt "a"*200 = 50 estimated tokens > 40 limit → overflow on turn 0.
    model = {"context_window": 50, "price_per_mtok_in": 0, "price_per_mtok_out": 0}
    budget = BudgetTracker(budget_usd=None)

    result = run_conversation(
        client,
        "test/model",
        "a" * 200,
        ["followup1"],
        model,
        budget,
    )
    assert result is not None
    assert result["context_overflow"] is True
    # Should not have called the API at all
    assert client.chat.completions.create.call_count == 0


def test_context_overflow_mid_conversation():
    """Context guard triggers mid-conversation after responses accumulate."""
    from aedist.harness import BudgetTracker
    from aedist.query_multiturn import run_conversation

    client = _make_mock_client()
    # context_window=100 tokens → limit=80.
    # Initial prompt "List plants." = 3 tokens, fits.
    # Response "Response 1" ~2 tokens.
    # Followup "a"*400 = 100 tokens → total ~105 > 80 → overflow.
    model = {"context_window": 100, "price_per_mtok_in": 0, "price_per_mtok_out": 0}
    budget = BudgetTracker(budget_usd=None)

    result = run_conversation(
        client,
        "test/model",
        "List plants.",
        ["a" * 400, "more?"],
        model,
        budget,
    )
    assert result is not None
    assert result["context_overflow"] is True
    # Initial call should succeed, overflow at followup
    assert client.chat.completions.create.call_count == 1
    asst_turns = [t for t in result["turns"] if t["role"] == "assistant"]
    assert len(asst_turns) == 1


def test_stateless_mode_resets_messages():
    """In stateless mode, each API call receives only 1 message (no history)."""
    from aedist.harness import BudgetTracker
    from aedist.query_multiturn import run_conversation

    client = _make_mock_client()
    model = {"context_window": 100000, "price_per_mtok_in": 0, "price_per_mtok_out": 0}
    budget = BudgetTracker(budget_usd=None)

    result = run_conversation(
        client,
        "test/model",
        "List plants.",
        ["Any missing?", "Check LNG?"],
        model,
        budget,
        stateless=True,
    )
    assert result is not None
    assert result["context_overflow"] is False

    # 3 API calls: initial + 2 followups
    assert client.chat.completions.create.call_count == 3

    # In stateless mode, each followup creates a fresh messages list.
    # However, call_args captures references that get mutated by later
    # .append(). Verify correctness via the result: each followup call
    # should NOT accumulate prior responses. The last call's messages
    # list (calls[2]) was created fresh and then had 1 response appended,
    # so it has 2 entries — but the user message should be prompt+followup,
    # not the full history.
    calls = client.chat.completions.create.call_args_list
    last_call_msgs = calls[2].kwargs["messages"]
    # Should contain only the combined prompt+followup as user, plus appended response
    assert len(last_call_msgs) == 2  # user + appended assistant
    assert "List plants." in last_call_msgs[0]["content"]
    assert "Check LNG?" in last_call_msgs[0]["content"]
    # Critically: should NOT contain earlier followup responses
    assert "Response 2" not in last_call_msgs[0]["content"]


def test_no_context_window_skips_guard():
    """Models without context_window field skip the guard entirely."""
    from aedist.harness import BudgetTracker
    from aedist.query_multiturn import run_conversation

    client = _make_mock_client()
    model = {"price_per_mtok_in": 0, "price_per_mtok_out": 0}  # no context_window
    budget = BudgetTracker(budget_usd=None)

    result = run_conversation(
        client,
        "test/model",
        "a" * 10000,
        ["followup"],
        model,
        budget,
    )
    assert result is not None
    assert result["context_overflow"] is False
    assert client.chat.completions.create.call_count == 2
