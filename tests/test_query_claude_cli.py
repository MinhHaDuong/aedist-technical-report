"""Unit tests for the Claude Code CLI route adapter (ticket 0160).

Pure unit tests — no real subprocess, no real claude binary required.
Belong in ``make check-fast``. Integration smoke (calls the real binary)
is in ``test_query_claude_cli_smoke.py`` and is marked ``@pytest.mark.slow``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from unittest.mock import patch

import pytest

from aedist.harness import query_claude_cli

# A minimal recorded shape of `claude --print --output-format json` stdout,
# verified live against claude-sonnet-4-6 on 2026-05-21 in the 0160 raid.
SAMPLE_RESPONSE = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "duration_ms": 4662,
    "duration_api_ms": 4623,
    "result": "pong",
    "stop_reason": "end_turn",
    "session_id": "5494c3ae-5a36-4637-ae5f-4304747f220d",
    "total_cost_usd": 0.0711507,
    "usage": {
        "input_tokens": 2,
        "output_tokens": 5,
        "cache_creation_input_tokens": 17848,
        "cache_read_input_tokens": 13799,
    },
}


def _completed_process(stdout: str, stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_command_assembly_minimal():
    """User-only messages produce a command without --append-system-prompt."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        return _completed_process(json.dumps(SAMPLE_RESPONSE))

    with patch.object(subprocess, "run", side_effect=fake_run):
        query_claude_cli("claude-sonnet-4-6", [{"role": "user", "content": "ping"}])

    cmd = captured["cmd"]
    assert cmd[0] == "claude"
    assert "--print" in cmd
    assert "--bare" in cmd
    assert "--model" in cmd and "claude-sonnet-4-6" in cmd
    assert "--output-format" in cmd and "json" in cmd
    assert "--allowedTools" in cmd
    assert "--no-session-persistence" in cmd
    assert "--append-system-prompt" not in cmd
    assert captured["input"] == "ping"


def test_command_assembly_with_system_prompt():
    """System message lands on --append-system-prompt; user on stdin."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        return _completed_process(json.dumps(SAMPLE_RESPONSE))

    messages = [
        {"role": "system", "content": "no web search."},
        {"role": "user", "content": "list plants"},
    ]
    with patch.object(subprocess, "run", side_effect=fake_run):
        query_claude_cli("claude-sonnet-4-6", messages)

    cmd = captured["cmd"]
    assert "--append-system-prompt" in cmd
    idx = cmd.index("--append-system-prompt")
    assert cmd[idx + 1] == "no web search."
    assert captured["input"] == "list plants"


def test_command_assembly_with_max_budget():
    """max_budget_usd kwarg adds --max-budget-usd to the command."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed_process(json.dumps(SAMPLE_RESPONSE))

    with patch.object(subprocess, "run", side_effect=fake_run):
        query_claude_cli(
            "claude-sonnet-4-6",
            [{"role": "user", "content": "ping"}],
            max_budget_usd=0.50,
        )

    cmd = captured["cmd"]
    assert "--max-budget-usd" in cmd
    idx = cmd.index("--max-budget-usd")
    assert cmd[idx + 1] == "0.5000"


def test_response_parsing():
    """JSON stdout maps onto the standard result dict shape."""
    with patch.object(
        subprocess, "run", return_value=_completed_process(json.dumps(SAMPLE_RESPONSE))
    ):
        result = query_claude_cli("claude-sonnet-4-6", [{"role": "user", "content": "ping"}])

    assert result["content"] == "pong"
    assert result["finish_reason"] == "end_turn"
    assert result["usage"]["prompt_tokens"] == 2
    assert result["usage"]["completion_tokens"] == 5
    assert result["cost_usd"] == pytest.approx(0.0711507)
    assert result["wall_seconds"] >= 0


def test_nonzero_exit_raises():
    """Subprocess non-zero exit surfaces as RuntimeError with stderr tail."""
    with patch.object(
        subprocess,
        "run",
        return_value=_completed_process("", stderr="boom", returncode=1),
    ):
        with pytest.raises(RuntimeError, match="claude CLI exited 1"):
            query_claude_cli("claude-sonnet-4-6", [{"role": "user", "content": "ping"}])


def test_is_error_in_payload_raises():
    """A 200 OK with is_error=true in the JSON is treated as a hard failure."""
    payload = {**SAMPLE_RESPONSE, "is_error": True, "result": "model overloaded"}
    with patch.object(subprocess, "run", return_value=_completed_process(json.dumps(payload))):
        with pytest.raises(RuntimeError, match="claude CLI error: model overloaded"):
            query_claude_cli("claude-sonnet-4-6", [{"role": "user", "content": "ping"}])


def test_missing_user_message_raises():
    """Messages without a user turn fail before invoking the CLI."""
    with pytest.raises(ValueError, match="must include a user turn"):
        query_claude_cli("claude-sonnet-4-6", [{"role": "system", "content": "only system"}])


# ---------------------------------------------------------------------------
# Integration smoke — opt-in via the slow marker, skipped when CLI absent.
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_smoke_real_cli():
    """One real call against the local claude CLI.

    Skipped when the binary is absent (CI without Claude Code installed).
    Costs a few cents on the user's Anthropic subscription.
    """
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not installed")

    result = query_claude_cli(
        "claude-sonnet-4-6",
        [{"role": "user", "content": "Reply with exactly one word: pong"}],
        timeout=60.0,
    )
    assert result["content"].strip().lower().startswith("pong")
    assert result["usage"]["completion_tokens"] > 0
    assert result["cost_usd"] >= 0
