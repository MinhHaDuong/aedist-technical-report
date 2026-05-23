"""Unit tests for the Exp 2 interactive / agentic smoke (ticket 0185).

Pure unit tests — no network, no API key, no subprocess.
"""

import io
import json
from pathlib import Path

import pytest

from experiments.sota.exp2_interactive_smoke import (
    BASELINE_PATH,
    METAPROMPT_PATH,
    QUALITY_BAR_END,
    QUALITY_BAR_PATH,
    QUALITY_BAR_START,
    assemble_meta_prompt,
    extract_narrative_from_mistral_raw,
    extract_phase_a_design,
    extract_quality_bar,
    strip_meta_framing,
    wait_for_space,
)


def test_strip_meta_framing_drops_prefix_and_separator():
    """The framing line + `---` separator is stripped; content survives intact."""
    text = "This is the prompt sent to the agents, verbatim.\n\n---\n\n# ROLE\n\nBody content.\n"
    stripped = strip_meta_framing(text)
    assert stripped.startswith("# ROLE"), f"unexpected leading content: {stripped[:40]!r}"
    assert "This is the prompt sent" not in stripped
    assert "Body content." in stripped


def test_strip_meta_framing_idempotent_on_unframed_input():
    """Files without a framing separator are returned unchanged."""
    text = "# ROLE\n\nBody.\n"
    assert strip_meta_framing(text) == text


def test_assemble_meta_prompt_strips_framing():
    """assemble_meta_prompt() must NOT include the framing line in the dispatched bytes."""
    prompt = assemble_meta_prompt()
    assert not prompt.startswith("This is the prompt"), (
        "framing line leaked into dispatched meta-prompt"
    )
    assert "# ROLE" in prompt or "# GOAL" in prompt, "meta-prompt content missing"


def test_metaprompt_file_exists():
    """The canonical Doc 02 meta-prompt file is on disk."""
    assert METAPROMPT_PATH.exists(), f"meta-prompt missing: {METAPROMPT_PATH}"


def test_baseline_and_quality_bar_files_exist():
    """Legacy source files (referenced by Doc 02 content) are still on disk."""
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


def test_assemble_meta_prompt_is_doc_02_content_post_framing():
    """The assembled meta-prompt is Doc 02's content after the framing strip.

    Single source of truth: edits to Doc 02 propagate to the dispatched
    bytes (modulo the meta-framing line stripped by strip_meta_framing).
    """
    assembled = assemble_meta_prompt()
    on_disk = METAPROMPT_PATH.read_text(encoding="utf-8")
    assert assembled == strip_meta_framing(on_disk), (
        "assemble_meta_prompt() must return Doc 02 minus the framing line — "
        "any in-code template would create a second source of truth"
    )


def test_assemble_meta_prompt_contains_quality_bar_and_envelope():
    """Sanity anchors that Doc 02 carries the four §2 axes + JSON envelope spec."""
    prompt = assemble_meta_prompt()
    for axis in ("Accuracy", "Coherence", "Provenance", "Temporality"):
        assert axis in prompt, f"axis {axis!r} missing from meta-prompt"
    assert "designed_prompt" in prompt  # JSON envelope spec
    assert "Output ONLY" in prompt  # explicit no-prose instruction


def test_assemble_meta_prompt_announces_system_prompt_field():
    """Ticket 0213: the Phase A envelope must include `system_prompt` as a
    required string key — the dict-vs-string ambiguity cost us a turn during
    0185, so the FORMAT section in Doc 02 names the key explicitly.
    """
    prompt = assemble_meta_prompt()
    assert "system_prompt" in prompt, "envelope spec must announce system_prompt key"


def test_extract_phase_a_design_parses_clean_json():
    payload = json.dumps(
        {
            "designed_prompt": "X",
            "system_prompt": "sys",
            "settings": {"thinking": True, "max_tokens": 8000, "rationale_for_settings": "y"},
            "rationale": "targets accuracy and provenance",
        }
    )
    obj = extract_phase_a_design(payload)
    assert obj["designed_prompt"] == "X"
    assert obj["system_prompt"] == "sys"
    assert obj["settings"]["thinking"] is True


def test_extract_phase_a_design_strips_markdown_fence():
    """Model sometimes wraps JSON in ```json ... ``` despite instructions."""
    raw = '```json\n{"designed_prompt":"X","system_prompt":"S","settings":{},"rationale":"z"}\n```'
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "X"
    assert obj["system_prompt"] == "S"


def test_extract_phase_a_design_tolerates_prose_preamble():
    raw = (
        "Sure! Here is my design:\n"
        '{"designed_prompt":"X","system_prompt":"S","settings":{},"rationale":"y"}'
    )
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "X"


def test_extract_phase_a_design_tolerates_prose_postamble():
    raw = (
        '{"designed_prompt":"X","system_prompt":"S","settings":{},"rationale":"y"}\n\nLet me know!'
    )
    obj = extract_phase_a_design(raw)
    assert obj["designed_prompt"] == "X"


def test_extract_phase_a_design_raises_on_invalid_json():
    with pytest.raises(ValueError, match="no JSON object|not valid JSON"):
        extract_phase_a_design("totally not json")


def test_extract_phase_a_design_raises_on_missing_keys():
    with pytest.raises(ValueError, match="missing required key"):
        extract_phase_a_design('{"designed_prompt":"X"}')


def test_extract_phase_a_design_requires_system_prompt_key():
    """Ticket 0213: system_prompt is a required key in the Phase A envelope."""
    payload = json.dumps(
        {
            "designed_prompt": "X",
            # system_prompt deliberately absent
            "settings": {"thinking": True, "max_tokens": 8000},
            "rationale": "no system prompt provided",
        }
    )
    with pytest.raises(ValueError, match="missing required key 'system_prompt'"):
        extract_phase_a_design(payload)


def test_extract_phase_a_design_rejects_system_prompt_as_dict():
    """Ticket 0213: system_prompt must be a plain string, not a dict.

    The dict-vs-string burn earlier in 0185 motivated explicit type
    enforcement here — the harness threads this value verbatim into the
    Mistral agent description field, which is a string.
    """
    payload = json.dumps(
        {
            "designed_prompt": "X",
            "system_prompt": {"role": "system", "content": "S"},
            "settings": {"thinking": True, "max_tokens": 8000},
            "rationale": "structured",
        }
    )
    with pytest.raises(ValueError, match="'system_prompt' must be a string"):
        extract_phase_a_design(payload)


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
    raw = (
        '{"designed_prompt": """multi\nline\nprompt""", '
        '"system_prompt": "S", "settings": {}, "rationale": "y"}'
    )
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


def test_module_imports_no_production_adapters():
    """The smoke calls provider APIs inline; it must not import production adapters.

    Updated from the "mistral-only" constraint (ticket 0234): all three
    providers added in the 0234-0236 wave call the SDK directly (like
    review_openai in exp2_protocol_review.py) rather than routing through
    the per-provider adapter_*.py modules. This keeps the experiment shim
    isolated from adapter contract changes.
    """
    src = Path(__file__).parent.parent / "experiments" / "sota" / "exp2_interactive_smoke.py"
    text = src.read_text()
    assert "adapter_mistral" in text
    # Production adapters must not be imported from the smoke shim.
    for forbidden in ("adapter_openai_responses", "adapter_qwen_dashscope", "query_anthropic"):
        assert forbidden not in text, f"unexpected production adapter import: {forbidden}"


# ---------------------------------------------------------------------------
# Phase B dialogue state machine (ticket 0214 — supersedes ticket 0207)
# ---------------------------------------------------------------------------

from experiments.sota import dialogue_classifier  # noqa: E402
from experiments.sota.exp2_interactive_smoke import (  # noqa: E402
    BUDGET_TRIGGER_FRAC,
    ENCOURAGE_REPLY,
    TERMINAL_REPLY,
    VERIFY_REPLY,
    format_status_line,
    run_phase_b_multiturn,
)


def _fake_classifier_factory(classes):
    """Return a stub ``classify_report`` that yields the given classes in order."""
    iterator = iter(classes)
    calls: list[str] = []

    def fake(narrative):
        calls.append(narrative)
        try:
            cls = next(iterator)
        except StopIteration:
            cls = "no_report"  # safe default if test underspecified
        return dialogue_classifier.ClassificationResult(
            class_=cls,
            classifier_cost_usd=0.0001,
            classifier_model="mock-classifier",
            wall_s=0.01,
        )

    fake.calls = calls  # type: ignore[attr-defined]
    return fake


def _fake_run_factory(cost_per_call: float = 0.10):
    """Return a stub ``run_mistral_call`` that costs a fixed amount per call."""
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
        system_prompt=None,
    ):
        from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

        call_log.append(
            {
                "prompt": prompt,
                "prompt_starts_with_status": prompt.startswith("Status:"),
                "continuation": continuation,
                "extra_metadata": extra_metadata,
                "system_prompt": system_prompt,
            }
        )
        # Write a minimal raw artefact the classifier-narrative extractor can read.
        raw_output_path.write_text(
            json.dumps({"outputs": [{"type": "message.output", "content": "stub narrative"}]})
        )
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model="mistral-large-2512",
                max_tokens=100,
                extra={"conversation_id": "conv_X", "agent_id": "ag_X"},
            ),
            resource_use=ResourceUse(
                cost_usd=cost_per_call, wall_s=1.0, tokens_in=10, tokens_out=20
            ),
            result_summary=ResultSummary(status="ok"),
            agent_family="mistral-direct",
            agent_mode=agent_mode,
        )

    fake_run.calls = call_log  # type: ignore[attr-defined]
    return fake_run


def test_format_status_line_exact_string():
    s = format_status_line(45000, 50000, 2.50, 3.00, 12.3, verify_state="pending")
    assert s == (
        "Status: remaining 45.0K of 50K tokens, $2.50 of $3.00. "
        "Wall-clock elapsed 12.3s. Verify pending."
    )


def test_format_status_line_verify_states():
    for state in ("pending", "on this turn", "used"):
        s = format_status_line(45000, 50000, 2.50, 3.00, 0.0, verify_state=state)
        assert f"Verify {state}." in s


def test_meta_prompt_announces_dual_axis_budget():
    """Doc 02 announces both the 50K-token cap and the $3 dollar guard."""
    prompt = assemble_meta_prompt()
    assert "50,000 tokens" in prompt, "token cap must be announced"
    assert "$3.00" in prompt, "dollar guard must be announced"
    assert f"{int(BUDGET_TRIGGER_FRAC * 100)}%" in prompt, "20% threshold must be named"


def test_three_reply_slot_constants_distinct():
    """The three slot strings must be unambiguous: no slot accidentally equal."""
    assert ENCOURAGE_REPLY != VERIFY_REPLY
    assert ENCOURAGE_REPLY != TERMINAL_REPLY
    assert VERIFY_REPLY != TERMINAL_REPLY
    # VERIFY_REPLY must mention the four §2 axes that the verify pass prioritises.
    for marker in ("provenance", "coverage", "temporality", "consistency"):
        assert marker in VERIFY_REPLY.lower(), f"VERIFY_REPLY missing {marker!r}"


def test_state_machine_report_then_verify_then_stop(monkeypatch, tmp_path):
    """Turn-1 = report → turn-2 sends VERIFY → accept turn-2 response and stop.

    Verify is used at most once per smoke run; after the agent's response
    to the verify reply, the loop terminates without cycling back to
    encouragement.
    """
    import experiments.sota.exp2_interactive_smoke as mod

    fake_run = _fake_run_factory(cost_per_call=0.10)
    fake_classify = _fake_classifier_factory(["report", "no_report"])
    monkeypatch.setattr(mod, "run_mistral_call", fake_run)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
        system_prompt="designed system text",
    )

    assert result["turns"] == 2, f"expected 2 turns, got {result['turns']}"
    assert result["terminal_sent"] is False
    # Turn 2's user-side message must contain the VERIFY_REPLY text.
    assert VERIFY_REPLY in fake_run.calls[1]["prompt"]  # type: ignore[attr-defined]
    # Turn 1 was the designed prompt (no status prefix).
    assert fake_run.calls[0]["prompt_starts_with_status"] is False  # type: ignore[attr-defined]
    # Turn 2 is status-prefixed.
    assert fake_run.calls[1]["prompt_starts_with_status"] is True  # type: ignore[attr-defined]
    # Ticket 0213: system_prompt is forwarded only on the multi-turn-start
    # turn (turn 1); follow-up turns must pass None because the agent is
    # already created with its description fixed.
    assert fake_run.calls[0]["system_prompt"] == "designed system text"  # type: ignore[attr-defined]
    for entry in fake_run.calls[1:]:  # type: ignore[attr-defined]
        assert entry["system_prompt"] is None, (
            "follow-up turns must not pass system_prompt (agent already created)"
        )
    # Per-turn artefacts including the new .classification.json.
    for turn in (1, 2):
        for suffix in (
            ".user.txt",
            ".raw.json",
            ".record.json",
            ".cost.json",
            ".classification.json",
        ):
            assert (tmp_path / f"mistral_turn_{turn:02d}{suffix}").exists(), (
                f"missing artefact mistral_turn_{turn:02d}{suffix}"
            )
    # Classifier cost is harness overhead — reported separately, NOT
    # deducted from the SOTA agent's spend.
    assert "total_classifier_cost_usd" in result
    assert result["total_classifier_cost_usd"] > 0
    # Agent spend = 2 calls × $0.10 = $0.20, independent of classifier cost.
    assert result["total_spent_usd"] == pytest.approx(0.20, abs=1e-6)


def test_state_machine_three_no_reports_then_terminal(monkeypatch, tmp_path):
    """3-strike rule: after the 3rd no_report observation TERMINAL fires.

    Trace under MAX_ENCOURAGEMENTS=3 with the count-first, then-check
    convention:

    - Turn 1: designed prompt → no_report (count 0→1) → ENCOURAGE pending
    - Turn 2: ENCOURAGE → no_report (1→2) → ENCOURAGE pending
    - Turn 3: ENCOURAGE → no_report (2→3) → TERMINAL pending, terminal_sent=True
    - Turn 4: TERMINAL sent → response accepted → loop stops

    Total = 4 turns. Two ENCOURAGE replies and one TERMINAL reply
    actually appeared on the wire.
    """
    import experiments.sota.exp2_interactive_smoke as mod

    fake_run = _fake_run_factory(cost_per_call=0.10)
    # Four classifications consumed (one per turn) — all no_report.
    fake_classify = _fake_classifier_factory(["no_report"] * 4)
    monkeypatch.setattr(mod, "run_mistral_call", fake_run)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
    )

    assert result["turns"] == 4, f"expected 4 turns, got {result['turns']}"
    assert result["terminal_sent"] is True
    # Turn 2 and 3 user-side: ENCOURAGE. Turn 4: TERMINAL.
    assert ENCOURAGE_REPLY in fake_run.calls[1]["prompt"]  # turn 2  # type: ignore[attr-defined]
    assert ENCOURAGE_REPLY in fake_run.calls[2]["prompt"]  # turn 3  # type: ignore[attr-defined]
    assert TERMINAL_REPLY in fake_run.calls[3]["prompt"]  # turn 4  # type: ignore[attr-defined]
    # Turn 4's cost artefact records the terminal slot.
    cost4 = json.loads((tmp_path / "mistral_turn_04.cost.json").read_text())
    assert cost4["user_slot"] == "terminal"
    assert cost4["classification"] == "no_report"
    # Five artefact files per turn.
    for turn in range(1, 5):
        for suffix in (
            ".user.txt",
            ".raw.json",
            ".record.json",
            ".cost.json",
            ".classification.json",
        ):
            assert (tmp_path / f"mistral_turn_{turn:02d}{suffix}").exists()


def test_state_machine_token_cap_overrides(monkeypatch, tmp_path):
    """Token cap below 20 % → TERMINAL on next turn regardless of class.

    Dual-axis budget: tokens-side override mirrors the dollar-side override.
    fake_run emits 20 tokens_out per call; with `cap_tokens=100`, three
    calls = 60 tokens, leaving 40 (40%). Need to push faster: use
    `cap_tokens=80` so after 2 calls (40 tokens) we're at 50%, after 3
    calls (60 tokens) we're at 25%, after 4 calls (80 tokens) we'd be at
    0% — but the 20% trigger fires when remaining ≤ 16 tokens, which
    happens at start of turn 4 (after 3 turns × 20 = 60 used → 20 left,
    which is just above the trigger; need to go one more turn).

    With `cap_tokens=75`: after 3 calls (60 tokens), remaining=15 ≤ 0.20×75=15
    → trigger fires at the top of turn 4. Total turns = 4.
    """
    import experiments.sota.exp2_interactive_smoke as mod

    fake_run = _fake_run_factory(cost_per_call=0.01)  # cheap; dollar cap won't bind
    fake_classify = _fake_classifier_factory(["no_report"] * 10)
    monkeypatch.setattr(mod, "run_mistral_call", fake_run)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=100.0,  # non-binding
        cap_tokens=75,  # binding: 4 × 20 = 80 > 75; trigger after 3 turns
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
    )

    assert result["turns"] == 4
    assert result["terminal_sent"] is True
    assert TERMINAL_REPLY in fake_run.calls[3]["prompt"]  # type: ignore[attr-defined]


def test_state_machine_budget_overrides(monkeypatch, tmp_path):
    """Budget below 20 % → TERMINAL on next turn regardless of class.

    Classifier always says no_report; each call costs $3 against a $10
    cap. Turn 1 → remaining $7. Turn 2 (encourage) → remaining $4.
    Turn 3 (encourage) → remaining $1 (≤ $2 trigger). On turn 4 the
    state machine builds TERMINAL (budget override), sends it, accepts
    one response, stops. Total turns = 4.

    Budget override matters even if encouragement_count has not yet hit
    its limit — the 20 % threshold is checked unconditionally at the
    top of the transition function.
    """
    import experiments.sota.exp2_interactive_smoke as mod

    fake_run = _fake_run_factory(cost_per_call=3.0)
    fake_classify = _fake_classifier_factory(["no_report"] * 10)
    monkeypatch.setattr(mod, "run_mistral_call", fake_run)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
    )

    assert result["turns"] == 4
    assert result["terminal_sent"] is True
    # Turn 4's user-side message must be TERMINAL (budget trigger).
    assert TERMINAL_REPLY in fake_run.calls[3]["prompt"]  # type: ignore[attr-defined]
    # Encouragement count never exhausted (we stopped at 2 encouragements
    # plus the budget-triggered terminal — not 3 encouragements then
    # terminal). Verify by checking turns 2 and 3 were encouragements.
    assert ENCOURAGE_REPLY in fake_run.calls[1]["prompt"]  # type: ignore[attr-defined]
    assert ENCOURAGE_REPLY in fake_run.calls[2]["prompt"]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# dialogue_classifier unit tests
# ---------------------------------------------------------------------------


def test_classify_report_returns_one_word_on_clean_response(monkeypatch):
    """Clean 'report' single-word response parses correctly with cost."""

    def fake_post(prompt, api_key):
        return {
            "choices": [{"message": {"content": "report"}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 1},
        }

    monkeypatch.setattr(dialogue_classifier, "_load_api_key", lambda: "test-key")
    monkeypatch.setattr(dialogue_classifier, "_post_classifier", fake_post)

    result = dialogue_classifier.classify_report("here is a table of plants...")
    assert result.class_ == "report"
    assert result.classifier_cost_usd > 0
    assert result.classifier_model == dialogue_classifier.CLASSIFIER_MODEL


def test_classify_report_falls_back_to_no_report_on_garbage(monkeypatch):
    """Unexpected one-word response → safe default to 'no_report'."""

    def fake_post(prompt, api_key):
        return {
            "choices": [{"message": {"content": "I'm sorry, I cannot decide."}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 8},
        }

    monkeypatch.setattr(dialogue_classifier, "_load_api_key", lambda: "test-key")
    monkeypatch.setattr(dialogue_classifier, "_post_classifier", fake_post)

    result = dialogue_classifier.classify_report("ambiguous narrative")
    assert result.class_ == "no_report"


def test_classify_report_falls_back_on_http_error(monkeypatch):
    """Transport error → 'no_report' with zero cost; never raises."""
    import httpx

    def fake_post(prompt, api_key):
        raise httpx.RequestError("connection refused")

    monkeypatch.setattr(dialogue_classifier, "_load_api_key", lambda: "test-key")
    monkeypatch.setattr(dialogue_classifier, "_post_classifier", fake_post)

    result = dialogue_classifier.classify_report("anything")
    assert result.class_ == "no_report"
    assert result.classifier_cost_usd == 0.0


def test_classify_report_falls_back_when_no_api_key(monkeypatch):
    """Missing key → 'no_report' with zero cost; logs but does not raise."""
    monkeypatch.setattr(dialogue_classifier, "_load_api_key", lambda: None)
    result = dialogue_classifier.classify_report("anything")
    assert result.class_ == "no_report"
    assert result.classifier_cost_usd == 0.0


def test_classification_result_to_artefact_dict_uses_class_key():
    """Serialised artefact uses the JSON-friendly 'class' key, not 'class_'."""
    result = dialogue_classifier.ClassificationResult(
        class_="report",
        classifier_cost_usd=0.000123,
        classifier_model="mock",
        wall_s=0.5,
    )
    d = dialogue_classifier.result_to_artefact_dict(result)
    assert d == {
        "class": "report",
        "classifier_cost_usd": 0.000123,
        "classifier_model": "mock",
        "wall_s": 0.5,
    }


# ---------------------------------------------------------------------------
# OpenAI Responses API multi-turn adapter (ticket 0234)
# ---------------------------------------------------------------------------


from experiments.sota.exp2_interactive_smoke import run_openai_call  # noqa: E402


def _make_openai_mock_resp(
    response_id: str = "resp_abc123",
    output_tokens: int = 200,
    reasoning_tokens: int = 50,
    input_tokens: int = 1000,
) -> object:
    """Build a minimal mock response object shaped like the Responses API output."""
    import types

    output_tokens_details = types.SimpleNamespace(reasoning_tokens=reasoning_tokens)
    usage = types.SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        output_tokens_details=output_tokens_details,
    )
    content_block = types.SimpleNamespace(type="output_text", text="Here is the inventory.")
    message_item = types.SimpleNamespace(type="message", content=[content_block])

    resp = types.SimpleNamespace(
        id=response_id,
        model="gpt-5.5",
        status="completed",
        output=[message_item],
        usage=usage,
    )
    resp.model_dump_json = lambda **_kwargs: json.dumps({"id": response_id, "model": "gpt-5.5"})
    return resp


def test_run_openai_call_turn1_no_continuation(monkeypatch, tmp_path):
    """Turn 1 (continuation=None): instructions set, web_search present, previous_response_id absent.

    Also verifies:
    - returned record has tokens_out and thinking_tokens populated correctly
    - record.method_params.extra carries {"previous_response_id": resp.id}
    """
    import types

    mock_resp = _make_openai_mock_resp(
        response_id="resp_turn1",
        output_tokens=200,
        reasoning_tokens=50,
        input_tokens=1000,
    )

    captured_kwargs: list[dict] = []

    class _FakeResponses:
        def create(self, **kwargs):
            captured_kwargs.append(kwargs)
            return mock_resp

    class _FakeClient:
        responses = _FakeResponses()

    fake_openai_module = types.ModuleType("openai")
    fake_openai_module.OpenAI = lambda **_: _FakeClient()  # type: ignore[attr-defined]

    monkeypatch.setitem(
        __import__(
            "sys"
        ).modules,  # patch sys.modules so the lazy import inside the function sees it
        "openai",
        fake_openai_module,
    )
    monkeypatch.setattr(
        "experiments.sota.exp2_interactive_smoke._load_openai_key",
        lambda: "test-key",
    )

    raw_path = tmp_path / "turn1.raw.json"
    record = run_openai_call(
        "Build a power plant inventory.",
        cap_usd=5.0,
        agent_mode="phase_b_run",
        raw_output_path=raw_path,
        max_tokens=8000,
        continuation=None,
        extra_metadata=None,
        system_prompt="You are a research assistant.",
    )

    assert len(captured_kwargs) == 1
    kw = captured_kwargs[0]

    # Turn 1 must carry instructions (system prompt installed on the session).
    assert kw.get("instructions") == "You are a research assistant.", (
        "instructions kwarg must carry system_prompt on turn 1"
    )

    # web_search tool must be requested.
    assert {"type": "web_search"} in kw.get("tools", []), "web_search tool must be in the request"

    # previous_response_id must NOT appear on turn 1.
    assert "previous_response_id" not in kw, (
        "previous_response_id must not be present on turn 1 (no continuation)"
    )

    # Token fields must be populated for dual-axis cap arithmetic.
    assert record.resource_use.tokens_out == 200
    assert record.resource_use.thinking_tokens == 50

    # Continuation token for turn 2 lives in extra.
    assert record.method_params.extra is not None
    assert record.method_params.extra.get("previous_response_id") == "resp_turn1"

    # Raw artefact must be written.
    assert raw_path.exists()


def test_run_openai_call_turn2_forwards_previous_response_id(monkeypatch, tmp_path):
    """Turn 2 (continuation carries previous_response_id): id forwarded, instructions absent."""
    import types

    mock_resp = _make_openai_mock_resp(response_id="resp_turn2")
    captured_kwargs: list[dict] = []

    class _FakeResponses:
        def create(self, **kwargs):
            captured_kwargs.append(kwargs)
            return mock_resp

    class _FakeClient:
        responses = _FakeResponses()

    fake_openai_module = types.ModuleType("openai")
    fake_openai_module.OpenAI = lambda **_: _FakeClient()  # type: ignore[attr-defined]

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        fake_openai_module,
    )
    monkeypatch.setattr(
        "experiments.sota.exp2_interactive_smoke._load_openai_key",
        lambda: "test-key",
    )

    raw_path = tmp_path / "turn2.raw.json"
    record = run_openai_call(
        "Proceed as instructed.",
        cap_usd=5.0,
        agent_mode="phase_b_run",
        raw_output_path=raw_path,
        max_tokens=8000,
        continuation={"previous_response_id": "resp_turn1"},
        extra_metadata=None,
        system_prompt=None,  # follow-up turns must pass None
    )

    assert len(captured_kwargs) == 1
    kw = captured_kwargs[0]

    # previous_response_id must be forwarded on turn 2.
    assert kw.get("previous_response_id") == "resp_turn1", (
        "previous_response_id must be forwarded from continuation on turn 2"
    )

    # instructions must NOT be sent again on follow-up turns.
    assert "instructions" not in kw, "instructions must not be re-sent on follow-up turns"

    # Continuation for the next turn must carry the new response id.
    assert record.method_params.extra is not None
    assert record.method_params.extra.get("previous_response_id") == "resp_turn2"


def test_state_machine_openai_dispatch(monkeypatch, tmp_path):
    """CALL_FNS table routes 'openai' to run_openai_call without NotImplementedError."""
    import experiments.sota.exp2_interactive_smoke as mod

    captured_calls: list[dict] = []

    def fake_openai_call(
        prompt,
        *,
        cap_usd,
        agent_mode,
        raw_output_path,
        max_tokens,
        continuation=None,
        extra_metadata=None,
        system_prompt=None,
    ):
        from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

        captured_calls.append(
            {
                "prompt": prompt,
                "continuation": continuation,
                "system_prompt": system_prompt,
            }
        )
        raw_output_path.write_text(
            json.dumps({"outputs": [{"type": "message.output", "content": "stub"}]})
        )
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model="gpt-5.5",
                max_tokens=100,
                extra={"previous_response_id": f"resp_{len(captured_calls)}"},
            ),
            resource_use=ResourceUse(
                cost_usd=0.10,
                wall_s=1.0,
                tokens_in=10,
                tokens_out=20,
                thinking_tokens=5,
            ),
            result_summary=ResultSummary(status="ok"),
            agent_family="openai-direct",
            agent_mode=agent_mode,
        )

    fake_classify = _fake_classifier_factory(["report", "no_report"])
    monkeypatch.setattr(mod, "run_openai_call", fake_openai_call)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    result = mod.run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="openai",
        system_prompt="system text",
    )

    # Should complete without NotImplementedError.
    assert result["turns"] == 2
    assert result["terminal_sent"] is False
    # Turn 1 receives system_prompt; turn 2 (follow-up) must not.
    assert captured_calls[0]["system_prompt"] == "system text"
    assert captured_calls[1]["system_prompt"] is None
    # Turn 2 continuation must forward the response id from turn 1's record.
    assert captured_calls[1]["continuation"] == {"previous_response_id": "resp_1"}
