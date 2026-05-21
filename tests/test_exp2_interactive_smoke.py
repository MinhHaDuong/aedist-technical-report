"""Unit tests for the Exp 2 interactive / agentic smoke (ticket 0185).

Pure unit tests — no network, no API key, no subprocess.
"""

import io
import json
from pathlib import Path

import pytest

from experiments.sota.exp2_interactive_smoke import (
    BASELINE_PATH,
    QUALITY_BAR_END,
    QUALITY_BAR_PATH,
    QUALITY_BAR_START,
    assemble_meta_prompt,
    extract_narrative_from_mistral_raw,
    extract_phase_a_design,
    extract_quality_bar,
    wait_for_space,
)


def test_baseline_and_quality_bar_files_exist():
    """Both source files are present at the expected paths."""
    assert BASELINE_PATH.exists(), f"baseline missing: {BASELINE_PATH}"
    assert QUALITY_BAR_PATH.exists(), f"manuscript missing: {QUALITY_BAR_PATH}"


def test_extract_quality_bar_slices_section_2():
    """The §2 quality-bar slice contains all four named dimensions."""
    text = QUALITY_BAR_PATH.read_text(encoding="utf-8")
    section = extract_quality_bar(text)
    assert QUALITY_BAR_START in section
    assert QUALITY_BAR_END not in section
    for axis in ("Accuracy", "Coherence", "Provenance", "Temporality"):
        assert axis in section, f"axis {axis!r} missing from extracted §2"


def test_extract_quality_bar_raises_on_missing_markers():
    with pytest.raises(ValueError, match="Could not locate"):
        extract_quality_bar("no markers here")


def test_assemble_meta_prompt_contains_baseline_and_quality_bar():
    """Anchors from baseline (line 3) and §2 (all four axes) appear in the meta-prompt."""
    prompt = assemble_meta_prompt(BASELINE_PATH, QUALITY_BAR_PATH)
    assert "senior energy analyst" in prompt  # baseline anchor
    assert "Accuracy" in prompt and "Temporality" in prompt  # §2 axes
    assert "designed_prompt" in prompt  # JSON envelope spec
    assert "Output ONLY" in prompt  # explicit no-prose instruction


def test_extract_phase_a_design_parses_clean_json():
    payload = json.dumps(
        {
            "designed_prompt": "X",
            "settings": {"thinking": True, "max_tokens": 8000, "rationale_for_settings": "y"},
            "rationale": "targets accuracy and provenance",
        }
    )
    obj = extract_phase_a_design(payload)
    assert obj["designed_prompt"] == "X"
    assert obj["settings"]["thinking"] is True


def test_extract_phase_a_design_strips_markdown_fence():
    """Model sometimes wraps JSON in ```json ... ``` despite instructions."""
    raw = '```json\n{"designed_prompt":"X","settings":{},"rationale":"z"}\n```'
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "X"


def test_extract_phase_a_design_tolerates_prose_preamble():
    raw = 'Sure! Here is my design:\n{"designed_prompt":"X","settings":{},"rationale":"y"}'
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "X"


def test_extract_phase_a_design_tolerates_prose_postamble():
    raw = '{"designed_prompt":"X","settings":{},"rationale":"y"}\n\nLet me know!'
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "X"


def test_extract_phase_a_design_raises_on_invalid_json():
    with pytest.raises(ValueError, match="no JSON object|not valid JSON"):
        extract_phase_a_design("totally not json")


def test_extract_phase_a_design_raises_on_missing_keys():
    with pytest.raises(ValueError, match="missing required key"):
        extract_phase_a_design('{"designed_prompt":"X"}')


def test_extract_narrative_from_mistral_raw_concatenates_text_chunks():
    raw = {
        "outputs": [
            {"type": "tool.execution", "name": "web_search"},
            {
                "type": "message.output",
                "content": [
                    {"type": "text", "text": "Hello "},
                    {"type": "tool_reference", "url": "https://example"},
                    {"type": "text", "text": "world."},
                ],
            },
        ]
    }
    assert extract_narrative_from_mistral_raw(raw) == "Hello world."


def test_extract_narrative_from_mistral_raw_handles_string_content():
    """Mistral sometimes returns content as a flat string (observed 2026-05-21)."""
    raw = {"outputs": [{"type": "message.output", "content": "Hello world."}]}
    assert extract_narrative_from_mistral_raw(raw) == "Hello world."


def test_extract_phase_a_design_handles_python_triple_quotes():
    """SOTA models occasionally use Python ``\"\"\"`` inside JSON; we normalise."""
    raw = '{"designed_prompt": """multi\nline\nprompt""", "settings": {}, "rationale": "y"}'
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "multi\nline\nprompt"


def test_wait_for_space_no_confirm_returns_silently():
    """In --no-confirm mode the gate must not touch stdin."""
    wait_for_space("anything", no_confirm=True)  # should not raise / hang


def test_wait_for_space_aborts_on_q(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("q\n"))
    with pytest.raises(SystemExit) as exc:
        wait_for_space("test gate", no_confirm=False)
    assert exc.value.code == 0


def test_wait_for_space_continues_on_enter(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
    # Should return None without raising.
    wait_for_space("test gate", no_confirm=False)


def test_module_imports_adapter_mistral_only():
    """The smoke must not import or edit the other 3 adapters in this iteration."""
    src = Path(__file__).parent.parent / "experiments" / "sota" / "exp2_interactive_smoke.py"
    text = src.read_text()
    assert "adapter_mistral" in text
    # Only mistral dispatch is wired; others should not be imported here.
    for forbidden in ("adapter_openai_responses", "adapter_qwen_dashscope", "query_anthropic"):
        assert forbidden not in text, f"unexpected import: {forbidden}"


# ---------------------------------------------------------------------------
# Multi-turn auto-reply loop (ticket 0207 policy)
# ---------------------------------------------------------------------------

from experiments.sota.exp2_interactive_smoke import (  # noqa: E402
    BUDGET_TRIGGER_FRAC,
    PHASE_B_TOTAL_BUDGET_USD,
    STANDARD_REPLY,
    TERMINAL_REPLY,
    format_status_line,
    run_phase_b_multiturn,
    select_reply,
)


def test_format_status_line_exact_string():
    s = format_status_line(7.50, 10.00, 12.3)
    assert s == "Status: remaining budget $7.50 of $10.00; wall-clock elapsed 12.3s."


def test_select_reply_returns_standard_above_threshold():
    cap = 10.00
    # Just above 20%: still standard
    reply, terminal = select_reply(2.01, cap)
    assert reply == STANDARD_REPLY
    assert terminal is False


def test_select_reply_returns_terminal_at_threshold():
    cap = 10.00
    # Exactly 20%: terminal fires (<= is the trigger)
    reply, terminal = select_reply(2.00, cap)
    assert reply == TERMINAL_REPLY
    assert terminal is True


def test_select_reply_returns_terminal_below_threshold():
    reply, terminal = select_reply(0.50, 10.00)
    assert reply == TERMINAL_REPLY
    assert terminal is True


def test_meta_prompt_announces_dollar_budget():
    """Per ticket 0207, the meta-prompt must announce the $10 cap upfront."""
    prompt = assemble_meta_prompt(BASELINE_PATH, QUALITY_BAR_PATH)
    assert f"${PHASE_B_TOTAL_BUDGET_USD:.2f} total" in prompt
    assert f"{int(BUDGET_TRIGGER_FRAC * 100)}%" in prompt
    assert "remaining budget" in prompt.lower()


def test_phase_b_multiturn_terminates_on_budget_trigger(monkeypatch, tmp_path):
    """The loop must send the terminal reply on the turn where remaining ≤ 20%
    of cap, then accept exactly one more assistant response, then stop.
    """
    import experiments.sota.exp2_interactive_smoke as mod

    # Mock run_mistral_call so each call costs a fixed amount; no network.
    call_log: list[dict] = []

    def fake_run(
        prompt,
        *,
        cap_usd,
        agent_mode,
        raw_output_path,
        max_tokens,
        continuation=None,
        extra_metadata=None,
    ):
        from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

        call_log.append(
            {
                "prompt_starts_with_status": prompt.startswith("Status:"),
                "continuation": continuation,
                "extra_metadata": extra_metadata,
            }
        )
        # Each call costs $3 — three calls will drop a $10 budget under 20%.
        raw_output_path.write_text("{}")
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model="mistral-large-2512",
                max_tokens=100,
                extra={"conversation_id": "conv_X", "agent_id": "ag_X"},
            ),
            resource_use=ResourceUse(cost_usd=3.0, wall_s=1.0, tokens_in=10, tokens_out=20),
            result_summary=ResultSummary(status="ok"),
            agent_family="mistral-direct",
            agent_mode=agent_mode,
        )

    monkeypatch.setattr(mod, "run_mistral_call", fake_run)

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
    )

    # Sequence: turn 1 spends 3 (remaining=7), turn 2 spends 3 (remaining=4),
    # turn 3 spends 3 (remaining=1, ≤20% trigger fires on turn 4 build).
    # Actually: terminal threshold is remaining ≤ 2.00. After turn 3, remaining=1
    # → on turn 4 build select_reply returns terminal. Turn 4 sends terminal,
    # accepts one response, breaks. Total = 4 turns.
    assert result["turns"] == 4
    assert result["terminal_sent"] is True
    assert result["agent_id"] == "ag_X"
    # Turn 1 user message is the designed prompt (no status prefix).
    assert call_log[0]["prompt_starts_with_status"] is False
    # Turns 2..4 all have status prefixes.
    for entry in call_log[1:]:
        assert entry["prompt_starts_with_status"] is True
    # extra_metadata workaround for ticket 0212: present on turn 1
    # (multi-turn-start, where Mistral accepts metadata at conversation
    # creation) and suppressed on follow-up turns (Mistral 422s the
    # body-level metadata on the path-bound append endpoint).
    assert call_log[0]["extra_metadata"] is not None
    assert "remaining_budget_usd" in call_log[0]["extra_metadata"]
    for entry in call_log[1:]:
        assert entry["extra_metadata"] is None, (
            "follow-up turns must suppress extra_metadata (0212 workaround)"
        )
    # Per-turn artefacts on disk.
    for turn in range(1, 5):
        for suffix in (".user.txt", ".raw.json", ".record.json", ".cost.json"):
            assert (tmp_path / f"mistral_turn_{turn:02d}{suffix}").exists(), (
                f"missing artefact mistral_turn_{turn:02d}{suffix}"
            )
