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
    _estimate_inventory_rows,
    assemble_meta_prompt,
    extract_narrative_from_mistral_raw,
    extract_phase_a_design,
    extract_quality_bar,
    main,
    wait_for_space,
)


def test_assemble_meta_prompt_starts_with_role():
    """assemble_meta_prompt() must begin directly with content, no framing line."""
    prompt = assemble_meta_prompt()
    assert prompt.startswith("# ROLE"), f"unexpected leading content: {prompt[:40]!r}"


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


def test_assemble_meta_prompt_is_doc_02_verbatim():
    """assemble_meta_prompt() must return Doc 02 verbatim — no in-code template."""
    assembled = assemble_meta_prompt()
    on_disk = METAPROMPT_PATH.read_text(encoding="utf-8")
    assert assembled == on_disk, (
        "assemble_meta_prompt() must return Doc 02 verbatim — "
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


def test_assemble_meta_prompt_without_manifest_has_no_available_evidence_heading():
    prompt = assemble_meta_prompt()
    assert "# Evidence pack" not in prompt


def test_assemble_meta_prompt_with_manifest_injects_yaml_before_planning_headroom():
    prompt = assemble_meta_prompt(manifest_path=MANIFEST_PATH)
    assert "# Evidence pack" in prompt
    assert "1. evn_ar_2010_2011_capacities" in prompt
    assert "## Chunk 1" not in prompt
    assert prompt.find("# Evidence pack") < prompt.find("## Planning headroom")


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


def test_extract_phase_a_design_handles_literal_newlines_inside_json_strings():
    """Mistral may emit raw newlines inside quoted values of an otherwise valid envelope."""
    raw = (
        "```json\n{\n"
        '  "system_prompt": "System line 1\nSystem line 2",\n\n'
        '  "designed_prompt": "Heading\n\nBullet one\nBullet two",\n\n'
        '  "settings": {"thinking": true, "max_tokens": 4000},\n\n'
        '  "rationale": "Because provenance matters."\n'
        "}\n```"
    )

    obj = extract_phase_a_design(raw)

    assert obj["system_prompt"] == "System line 1\nSystem line 2"
    assert obj["designed_prompt"] == "Heading\n\nBullet one\nBullet two"


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


def test_main_dry_run_multiple_agents_writes_meta_and_summary(tmp_path):
    """Ticket 0237: --agents loops and writes per-agent artefacts in dry-run mode."""
    rc = main(
        [
            "--agents",
            "mistral",
            "openai",
            "--dry-run",
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0

    assert (tmp_path / "mistral_run01" / "mistral_meta_prompt.txt").exists()
    assert (tmp_path / "openai_run01" / "openai_meta_prompt.txt").exists()
    summaries = list(tmp_path.glob("summary_*.md"))
    assert summaries, "no summary_*.md written"
    summary = summaries[0].read_text(encoding="utf-8")
    assert "mistral" in summary
    assert "openai" in summary


def test_reuse_phase_a_skips_api_and_copies_design(tmp_path):
    """--reuse-phase-a-from loads Phase A artefacts without calling any API."""
    # Build a minimal Phase A fixture: probes/mistral_run01/ with the required files.
    phase_a_dir = tmp_path / "probes" / "mistral_run01"
    phase_a_dir.mkdir(parents=True)
    design = {
        "system_prompt": "You are an analyst.",
        "designed_prompt": "List capacity by fuel type.",
        "settings": {"thinking": False, "max_tokens": 2000},
        "rationale": "Short test.",
    }
    (phase_a_dir / "mistral_phase_a_design.json").write_text(json.dumps(design), encoding="utf-8")
    (phase_a_dir / "mistral_phase_a.json").write_text("{}", encoding="utf-8")

    out_dir = tmp_path / "out"
    rc = main(
        [
            "--agents",
            "mistral",
            "--stop-after-phase-a",
            "--no-confirm",
            "--reuse-phase-a-from",
            str(tmp_path / "probes"),
            "--output-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    # Design file must be copied into the run dir.
    assert (out_dir / "mistral_run01" / "mistral_phase_a_design.json").exists()


def test_module_imports_only_wired_adapters():
    """The smoke imports the four wired adapters and nothing else.

    Mistral (0214), OpenAI (0234), Anthropic (0235), Qwen (0236) — the
    full optimized-arm cohort for Exp 2 protocol v3.
    """
    src = Path(__file__).parent.parent / "experiments" / "sota" / "exp2_interactive_smoke.py"
    text = src.read_text()
    assert "adapter_mistral" in text
    assert "adapter_openai_responses" in text  # 0234
    assert "query_anthropic" in text  # 0235
    assert "adapter_qwen_dashscope" in text  # 0236


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
    monkeypatch.setitem(mod.CALL_FNS, "mistral", fake_run)
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
    monkeypatch.setitem(mod.CALL_FNS, "mistral", fake_run)
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


def test_conversation_json_persisted_after_run(monkeypatch, tmp_path):
    """run_phase_b_multiturn must write {agent}_conversation.json with the full exchange.

    Covers the showstopper gap for stateful APIs (Mistral, OpenAI): unlike
    Anthropic/Qwen which resend the full history every call, stateful providers
    only carry agent_id/conversation_id in their continuation — the conversation
    is server-side only.  The client-side conversation_history ensures the
    complete dialogue is persisted locally regardless of provider.
    """
    import experiments.sota.exp2_interactive_smoke as mod

    fake_run = _fake_run_factory(cost_per_call=0.10)
    fake_classify = _fake_classifier_factory(["no_report", "report", "no_report"])
    monkeypatch.setitem(mod.CALL_FNS, "mistral", fake_run)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
        system_prompt="you are an analyst",
    )

    conv_path = tmp_path / "mistral_conversation.json"
    assert conv_path.exists(), "mistral_conversation.json must be written"
    conv = json.loads(conv_path.read_text())
    messages = conv["messages"]
    # System prompt is first.
    assert messages[0] == {"role": "system", "content": "you are an analyst"}
    # Alternating user / assistant pairs follow.
    roles = [m["role"] for m in messages[1:]]
    assert roles == ["user", "assistant"] * ((len(messages) - 1) // 2), (
        f"expected alternating user/assistant, got {roles}"
    )
    # Turn-1 user message is the designed prompt.
    assert messages[1]["content"] == "the designed prompt"
    # Every assistant message is non-empty.
    for m in messages:
        if m["role"] == "assistant":
            assert m["content"], "assistant message must be non-empty"


def test_conversation_json_written_without_system_prompt(monkeypatch, tmp_path):
    """conversation.json is correct when no system_prompt is passed."""
    import experiments.sota.exp2_interactive_smoke as mod

    fake_run = _fake_run_factory(cost_per_call=0.10)
    fake_classify = _fake_classifier_factory(["report", "no_report"])
    monkeypatch.setitem(mod.CALL_FNS, "mistral", fake_run)
    monkeypatch.setattr(mod.dialogue_classifier, "classify_report", fake_classify)

    run_phase_b_multiturn(
        "user prompt only",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="mistral",
    )

    conv = json.loads((tmp_path / "mistral_conversation.json").read_text())
    messages = conv["messages"]
    # No system prompt — first message is the user turn.
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "user prompt only"


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
    monkeypatch.setitem(mod.CALL_FNS, "mistral", fake_run)
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
    monkeypatch.setitem(mod.CALL_FNS, "mistral", fake_run)
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
# Ticket 0234: OpenAI Responses API adapter for multi-turn Phase B
# ---------------------------------------------------------------------------


def _make_fake_openai_resp(*, resp_id: str = "resp_test_001", narrative: str = "stub"):
    """Minimal stand-in for ``openai.responses.create()`` return value.

    Built to exercise :func:`adapter_openai_responses.parse_response`,
    which is the same parser :func:`run_openai_call` uses.
    """
    from types import SimpleNamespace

    class _Resp(SimpleNamespace):
        def model_dump_json(self, indent: int | None = None) -> str:
            return json.dumps({"id": resp_id, "narrative": narrative}, indent=indent)

    return _Resp(
        id=resp_id,
        model="gpt-5.5",
        status="completed",
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text=narrative)],
            ),
        ],
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            output_tokens_details=SimpleNamespace(reasoning_tokens=200),
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        ),
    )


def test_run_openai_call_turn1_no_continuation(monkeypatch, tmp_path):
    """Turn 1: instructions=system_prompt; tools includes web_search; no previous_response_id."""
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_create(**payload):
        captured.update(payload)
        return _make_fake_openai_resp()

    fake_client = type("C", (), {})()
    fake_client.responses = type("R", (), {"create": staticmethod(fake_create)})()
    monkeypatch.setattr("openai.OpenAI", lambda **kw: fake_client)  # noqa: ARG005
    monkeypatch.setattr(
        "aedist.adapter_openai_responses._load_openai_key", lambda: "sk-test-fixture"
    )

    record = mod.run_openai_call(
        "the prompt",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw.json",
        max_tokens=1000,
        continuation=None,
        extra_metadata=None,
        system_prompt="you are an analyst",
    )

    assert captured["input"] == "the prompt"
    assert captured["instructions"] == "you are an analyst"
    assert {"type": "web_search"} in captured["tools"]
    assert "previous_response_id" not in captured
    # Cost cap accounting (Doc 02 CONTEXT > Budget): tokens_out (50) + thinking (200) = 250.
    assert record.resource_use.tokens_out == 50
    assert record.resource_use.thinking_tokens == 200
    assert record.agent_mode == "phase_b_run"
    # Raw artefact written for downstream classifier read paths.
    assert (tmp_path / "raw.json").exists()
    # Justification carries the narrative for the record-first classifier path.
    assert (record.justification or {}).get("output_text") == "stub"


def test_run_openai_call_turn2_uses_previous_response_id(monkeypatch, tmp_path):
    """Turn 2+: previous_response_id is forwarded; instructions NOT re-sent."""
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_create(**payload):
        captured.update(payload)
        return _make_fake_openai_resp(resp_id="resp_test_turn2")

    fake_client = type("C", (), {})()
    fake_client.responses = type("R", (), {"create": staticmethod(fake_create)})()
    monkeypatch.setattr("openai.OpenAI", lambda **kw: fake_client)  # noqa: ARG005
    monkeypatch.setattr(
        "aedist.adapter_openai_responses._load_openai_key", lambda: "sk-test-fixture"
    )

    mod.run_openai_call(
        "follow-up prompt",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw_turn2.json",
        max_tokens=1000,
        continuation={"response_id": "resp_test_turn1"},
        extra_metadata=None,
        system_prompt="you are an analyst",  # passed but should be ignored on followup
    )

    assert captured["previous_response_id"] == "resp_test_turn1"
    assert "instructions" not in captured, (
        "follow-up turn must not re-send instructions — server-side state inherits"
    )


def test_state_machine_openai_dispatch_chains_response_id(monkeypatch, tmp_path):
    """Dispatcher routes --agent openai through run_openai_call and chains response_id.

    Turn-1 has empty continuation. Turn-2's call must receive
    ``continuation={"response_id": <turn1_resp_id>}`` — proving the
    CONTINUATION_EXTRACTORS table replaces the Mistral-specific
    agent_id / conversation_id extraction without code branching in
    the dispatcher body.
    """
    from experiments.sota import exp2_interactive_smoke as mod

    call_log: list[dict] = []

    def fake_run_openai(
        prompt,
        *,
        cap_usd,  # noqa: ARG001  # signature parity; cap enforced inside the real call
        agent_mode,
        raw_output_path,
        max_tokens,  # noqa: ARG001
        continuation=None,
        extra_metadata=None,
        system_prompt=None,
    ):
        from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

        call_log.append(
            {
                "prompt": prompt,
                "continuation": continuation,
                "extra_metadata": extra_metadata,
                "system_prompt": system_prompt,
            }
        )
        raw_output_path.write_text(json.dumps({"id": f"resp_t{len(call_log)}"}))
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model="gpt-5.5",
                max_tokens=100,
                extra={"response_id": f"resp_t{len(call_log)}"},
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
            justification={"output_text": "stub narrative"},
        )

    monkeypatch.setitem(mod.CALL_FNS, "openai", fake_run_openai)
    monkeypatch.setattr(
        mod.dialogue_classifier,
        "classify_report",
        _fake_classifier_factory(["report", "no_report"]),
    )

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="openai",
        system_prompt="designed system text",
    )

    assert result["turns"] == 2, f"expected 2 turns, got {result['turns']}"
    # Turn 1: continuation is the initial empty dict — no response_id yet.
    assert not call_log[0]["continuation"] or "response_id" not in call_log[0]["continuation"]
    # System prompt installed on turn 1.
    assert call_log[0]["system_prompt"] == "designed system text"
    # Turn 2: continuation carries the turn-1 response_id.
    assert call_log[1]["continuation"] == {"response_id": "resp_t1"}
    # OpenAI is in SYSTEM_PROMPT_PASSTHROUGH = False group → system masked on follow-up.
    assert call_log[1]["system_prompt"] is None
    # Per-turn artefacts present for both turns.
    for turn in (1, 2):
        for suffix in (".user.txt", ".raw.json", ".record.json", ".classification.json"):
            assert (tmp_path / f"openai_turn_{turn:02d}{suffix}").exists(), (
                f"missing artefact openai_turn_{turn:02d}{suffix}"
            )


def test_dispatch_tables_share_provider_set():
    """CALL_FNS and CONTINUATION_EXTRACTORS must cover the same providers.

    Catches drift where someone adds a new provider to one table but
    forgets the other — a partial wiring would crash at runtime with
    a KeyError. Cheap structural invariant.
    """
    from experiments.sota import exp2_interactive_smoke as mod

    assert set(mod.CALL_FNS) == set(mod.CONTINUATION_EXTRACTORS), (
        f"CALL_FNS={set(mod.CALL_FNS)} but "
        f"CONTINUATION_EXTRACTORS={set(mod.CONTINUATION_EXTRACTORS)} — "
        "every wired provider needs both"
    )
    # SYSTEM_PROMPT_PASSTHROUGH may be a subset (missing entry = default False),
    # but every key in it must be a known provider.
    assert set(mod.SYSTEM_PROMPT_PASSTHROUGH).issubset(set(mod.CALL_FNS))


# ---------------------------------------------------------------------------
# Ticket 0235: Anthropic Messages API adapter for multi-turn Phase B
# ---------------------------------------------------------------------------


def _make_fake_anthropic_resp(*, narrative: str = "stub"):
    """Minimal stand-in for ``anthropic.messages.create()`` return value."""
    from types import SimpleNamespace

    return SimpleNamespace(
        id="msg_test_001",
        model="claude-opus-4-6",
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="text", text=narrative, citations=[]),
        ],
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            server_tool_use=SimpleNamespace(web_search_requests=2),
        ),
    )


def test_run_anthropic_call_turn1_sends_system_and_messages(monkeypatch, tmp_path):
    """Turn 1: system installed, messages = [{user, prompt}], no replayed history."""
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_create(**payload):
        captured.update(payload)
        return _make_fake_anthropic_resp()

    fake_client = type("C", (), {})()
    fake_client.messages = type("M", (), {"create": staticmethod(fake_create)})()
    monkeypatch.setattr("anthropic.Anthropic", lambda **kw: fake_client)  # noqa: ARG005
    monkeypatch.setattr("aedist.query_anthropic._load_key", lambda _: "sk-ant-test")

    record = mod.run_anthropic_call(
        "the prompt",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw.json",
        max_tokens=1000,
        continuation=None,
        extra_metadata=None,
        system_prompt="you are an analyst",
    )

    assert captured["system"] == "you are an analyst"
    assert captured["messages"] == [{"role": "user", "content": "the prompt"}]
    # Single web_search tool installed at turn 1 (max_uses=3 default).
    assert any(t.get("name") == "web_search" for t in captured["tools"])
    assert record.agent_mode == "phase_b_run"
    # Narrative stashed for the record-first classifier path.
    assert (record.justification or {}).get("output_text") == "stub"


def test_run_anthropic_call_turn2_replays_full_history(monkeypatch, tmp_path):
    """Turn 2+: messages list contains prior turns AND system is re-sent identically.

    Anthropic is stateless on the wire: every call must replay the full
    conversation history including each previous assistant reply, AND the
    ``system`` parameter must be passed as identical bytes every turn.
    """
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_create(**payload):
        captured.update(payload)
        return _make_fake_anthropic_resp(narrative="turn-2 reply")

    fake_client = type("C", (), {})()
    fake_client.messages = type("M", (), {"create": staticmethod(fake_create)})()
    monkeypatch.setattr("anthropic.Anthropic", lambda **kw: fake_client)  # noqa: ARG005
    monkeypatch.setattr("aedist.query_anthropic._load_key", lambda _: "sk-ant-test")

    prior_history = [
        {"role": "user", "content": "first user message"},
        {"role": "assistant", "content": "first assistant reply"},
    ]

    mod.run_anthropic_call(
        "second user message",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw_turn2.json",
        max_tokens=1000,
        continuation={"messages": prior_history},
        extra_metadata=None,
        system_prompt="you are an analyst",
    )

    # Full history replayed: prior 2 + new user = 3 messages.
    assert captured["messages"] == [
        {"role": "user", "content": "first user message"},
        {"role": "assistant", "content": "first assistant reply"},
        {"role": "user", "content": "second user message"},
    ]
    # System bytes identical to turn 1 (required by Anthropic).
    assert captured["system"] == "you are an analyst"


def test_state_machine_anthropic_dispatch_chains_messages(monkeypatch, tmp_path):
    """Dispatcher routes --agent anthropic and appends turn-1 reply into turn-2 messages.

    Two-turn trace under ``[report, no_report]``: turn-1 is the designed
    prompt; the classifier returns "report" → VERIFY fires on turn-2.
    On turn-2 the dispatcher must pass ``continuation["messages"]`` that
    contains the turn-1 user message AND the turn-1 assistant reply.
    System prompt MUST be re-sent on turn-2 (SYSTEM_PROMPT_PASSTHROUGH).
    """
    from experiments.sota import exp2_interactive_smoke as mod

    call_log: list[dict] = []

    def fake_run_anthropic(
        prompt,
        *,
        cap_usd,  # noqa: ARG001
        agent_mode,
        raw_output_path,
        max_tokens,  # noqa: ARG001
        continuation=None,
        extra_metadata=None,
        system_prompt=None,
    ):
        from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

        call_log.append(
            {
                "prompt": prompt,
                "continuation": continuation,
                "extra_metadata": extra_metadata,
                "system_prompt": system_prompt,
            }
        )
        # Build the next-turn messages list: prior history (if any) + this turn.
        history = list((continuation or {}).get("messages", []))
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": f"reply-{len(call_log)}"})
        raw_output_path.write_text(json.dumps({"id": f"msg_t{len(call_log)}"}))
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model="claude-opus-4-6",
                max_tokens=100,
                extra={"run_number": 1, "messages": history},
            ),
            resource_use=ResourceUse(
                cost_usd=0.10,
                wall_s=1.0,
                tokens_in=10,
                tokens_out=20,
                thinking_tokens=None,
            ),
            result_summary=ResultSummary(status="ok"),
            agent_family="anthropic-direct",
            agent_mode=agent_mode,
            justification={"output_text": f"reply-{len(call_log)}"},
        )

    monkeypatch.setitem(mod.CALL_FNS, "anthropic", fake_run_anthropic)
    monkeypatch.setattr(
        mod.dialogue_classifier,
        "classify_report",
        _fake_classifier_factory(["report", "no_report"]),
    )

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="anthropic",
        system_prompt="designed system text",
    )

    assert result["turns"] == 2, f"expected 2 turns, got {result['turns']}"
    # Turn 1: empty continuation, system installed.
    assert not call_log[0]["continuation"] or "messages" not in call_log[0]["continuation"]
    assert call_log[0]["system_prompt"] == "designed system text"
    # Turn 2: messages list contains turn-1 user + turn-1 assistant.
    msgs = (call_log[1]["continuation"] or {}).get("messages", [])
    assert msgs[0] == {"role": "user", "content": "the designed prompt"}
    assert msgs[1] == {"role": "assistant", "content": "reply-1"}
    # SYSTEM_PROMPT_PASSTHROUGH=True for Anthropic — system re-sent on turn 2.
    assert call_log[1]["system_prompt"] == "designed system text"


# ---------------------------------------------------------------------------
# Ticket 0236: Qwen DashScope adapter for multi-turn Phase B
# ---------------------------------------------------------------------------


def _make_fake_qwen_resp(*, narrative: str = "stub-qwen"):
    """Minimal stand-in for ``dashscope.Generation.call()`` return value.

    Mirrors the dict-shape DashScope returns: nested ``output.choices[0].message``
    plus a top-level ``usage`` dict. Built to exercise
    ``adapter_qwen_dashscope.parse_response``.
    """
    return {
        "output": {
            "choices": [
                {
                    "message": {
                        "content": narrative,
                        "reasoning_content": None,
                    },
                    "finish_reason": "stop",
                },
            ],
            "search_info": {"search_results": []},
        },
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "output_tokens_details": {"reasoning_tokens": 0},
            "plugins": {"search": {"count": 0}},
        },
        "request_id": "req_test_001",
        "status_code": 200,
    }


def test_run_qwen_call_turn1_injects_system(monkeypatch, tmp_path):
    """Turn 1 Qwen call: messages = [system, user]; enable_search=True; thinking on."""
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_call(**payload):
        captured.update(payload)
        return _make_fake_qwen_resp()

    monkeypatch.setattr("dashscope.Generation.call", fake_call)
    monkeypatch.setattr("aedist.adapter_qwen_dashscope._resolve_api_key", lambda: "sk-qwen-test")

    record = mod.run_qwen_call(
        "the prompt",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw.json",
        max_tokens=1000,
        continuation=None,
        extra_metadata=None,
        system_prompt="you are an analyst",
    )

    assert captured["messages"] == [
        {"role": "system", "content": "you are an analyst"},
        {"role": "user", "content": "the prompt"},
    ]
    assert captured["enable_search"] is True
    assert captured["enable_thinking"] is True
    # Continuation messages (post-parse override) include system + user + assistant.
    extra_msgs = (record.method_params.extra or {}).get("messages", [])
    assert extra_msgs[0] == {"role": "system", "content": "you are an analyst"}
    assert extra_msgs[1] == {"role": "user", "content": "the prompt"}
    assert extra_msgs[2] == {"role": "assistant", "content": "stub-qwen"}
    # Narrative reachable via the record-first classifier path.
    assert (record.justification or {}).get("output_text") == "stub-qwen"


def test_run_qwen_call_merges_metadata_into_existing_system(monkeypatch, tmp_path):
    """When system_prompt AND extra_metadata are both set, exactly one system message.

    Regression: an earlier implementation prepended a SECOND
    ``{"role": "system"}`` entry when extra_metadata was set, producing
    payload [metadata-system, real-system, user]. DashScope honours at
    most one leading system message and would silently drop one of them.

    Correct behaviour: append the [metadata] line to the existing
    system message content, keeping a single system entry at index 0.
    """
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_call(**payload):
        captured.update(payload)
        return _make_fake_qwen_resp()

    monkeypatch.setattr("dashscope.Generation.call", fake_call)
    monkeypatch.setattr("aedist.adapter_qwen_dashscope._resolve_api_key", lambda: "sk-qwen-test")

    mod.run_qwen_call(
        "the prompt",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw.json",
        max_tokens=1000,
        continuation=None,
        extra_metadata={"remaining_usd": "2.50", "cap_usd": "3.00"},
        system_prompt="you are an analyst",
    )

    # Exactly one system message at index 0.
    system_messages = [m for m in captured["messages"] if m.get("role") == "system"]
    assert len(system_messages) == 1, (
        f"expected exactly 1 system message, got {len(system_messages)}: "
        f"{[m for m in captured['messages']]}"
    )
    assert captured["messages"][0]["role"] == "system"
    # Both the agent's system_prompt AND the [metadata] line must be present.
    sys_content = captured["messages"][0]["content"]
    assert "you are an analyst" in sys_content
    assert "[metadata]" in sys_content
    assert "remaining_usd=2.50" in sys_content


def test_run_qwen_call_turn2_replays_full_history(monkeypatch, tmp_path):
    """Turn 2+: messages list replays prior history (including system) + new user."""
    from experiments.sota import exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_call(**payload):
        captured.update(payload)
        return _make_fake_qwen_resp(narrative="turn-2 reply")

    monkeypatch.setattr("dashscope.Generation.call", fake_call)
    monkeypatch.setattr("aedist.adapter_qwen_dashscope._resolve_api_key", lambda: "sk-qwen-test")

    prior_history = [
        {"role": "system", "content": "you are an analyst"},
        {"role": "user", "content": "first user message"},
        {"role": "assistant", "content": "first assistant reply"},
    ]

    mod.run_qwen_call(
        "second user message",
        cap_usd=3.0,
        agent_mode="phase_b_run",
        raw_output_path=tmp_path / "raw_turn2.json",
        max_tokens=1000,
        continuation={"messages": prior_history},
        extra_metadata=None,
        system_prompt="you are an analyst",  # ignored because continuation carries it
    )

    # Full history (incl. system) + new user message sent on the wire.
    assert captured["messages"] == [
        {"role": "system", "content": "you are an analyst"},
        {"role": "user", "content": "first user message"},
        {"role": "assistant", "content": "first assistant reply"},
        {"role": "user", "content": "second user message"},
    ]


def test_state_machine_qwen_dispatch_chains_messages(monkeypatch, tmp_path):
    """Dispatcher routes --agent qwen, replays full conversation, re-sends system on turn 2."""
    from experiments.sota import exp2_interactive_smoke as mod

    call_log: list[dict] = []

    def fake_run_qwen(
        prompt,
        *,
        cap_usd,  # noqa: ARG001
        agent_mode,
        raw_output_path,
        max_tokens,  # noqa: ARG001
        continuation=None,
        extra_metadata=None,
        system_prompt=None,
    ):
        from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

        call_log.append(
            {
                "prompt": prompt,
                "continuation": continuation,
                "extra_metadata": extra_metadata,
                "system_prompt": system_prompt,
            }
        )
        # Build the full history for the next-turn continuation.
        if continuation and continuation.get("messages"):
            history = list(continuation["messages"])
        else:
            history = [{"role": "system", "content": system_prompt}] if system_prompt else []
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": f"reply-{len(call_log)}"})
        raw_output_path.write_text(json.dumps({"request_id": f"req_t{len(call_log)}"}))
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model="qwen3-max",
                max_tokens=100,
                extra={"messages": history},
            ),
            resource_use=ResourceUse(cost_usd=0.10, wall_s=1.0, tokens_in=10, tokens_out=20),
            result_summary=ResultSummary(status="ok"),
            agent_family="qwen-direct",
            agent_mode=agent_mode,
            justification={"output_text": f"reply-{len(call_log)}"},
        )

    monkeypatch.setitem(mod.CALL_FNS, "qwen", fake_run_qwen)
    monkeypatch.setattr(
        mod.dialogue_classifier,
        "classify_report",
        _fake_classifier_factory(["report", "no_report"]),
    )

    result = run_phase_b_multiturn(
        "the designed prompt",
        output_dir=tmp_path,
        cap_usd=10.0,
        cap_tokens=100_000,
        initial_spent_usd=0.0,
        max_tokens=100,
        agent="qwen",
        system_prompt="designed system text",
    )

    assert result["turns"] == 2, f"expected 2 turns, got {result['turns']}"
    # Turn 1: empty continuation, system installed.
    assert not call_log[0]["continuation"] or "messages" not in call_log[0]["continuation"]
    assert call_log[0]["system_prompt"] == "designed system text"
    # Turn 2: full history (system + user1 + assistant1) replayed.
    msgs = (call_log[1]["continuation"] or {}).get("messages", [])
    assert msgs[0] == {"role": "system", "content": "designed system text"}
    assert msgs[1] == {"role": "user", "content": "the designed prompt"}
    assert msgs[2] == {"role": "assistant", "content": "reply-1"}
    # SYSTEM_PROMPT_PASSTHROUGH=True for Qwen — system re-sent on turn 2.
    assert call_log[1]["system_prompt"] == "designed system text"


# ---------------------------------------------------------------------------
# Regression guards — must pass before and after the --evidence-pack-manifest patch
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "experiments" / "evidence_packs" / "all18tables.yaml"

FAKE_DESIGN = {
    "designed_prompt": "Extract thermal plants from the documents.",
    "system_prompt": "You are an energy data analyst.",
    "settings": {"max_tokens": 4000},
}

FAKE_PHASE_B_RESULT = {
    "turns": 2,
    "total_spent_usd": 0.05,
    "records": [],
}


@pytest.fixture()
def phase_a_reuse_dir(tmp_path):
    """Minimal Phase A reuse dir for mistral_run01 — skips Phase A API call."""
    reuse = tmp_path / "phase_a_probes" / "mistral_run01"
    reuse.mkdir(parents=True)
    (reuse / "mistral_phase_a_design.json").write_text(json.dumps(FAKE_DESIGN), encoding="utf-8")
    for fname in ("mistral_phase_a.json", "mistral_phase_a.raw.json"):
        (reuse / fname).write_bytes(b"{}")
    return tmp_path / "phase_a_probes"


@pytest.fixture()
def patched_phase_b(monkeypatch):
    """Capture the prompt passed to run_phase_b_multiturn; suppress downstream reads."""
    import experiments.sota.exp2_interactive_smoke as mod

    captured: dict = {}

    def fake_phase_b(prompt, **kwargs):
        captured["prompt"] = prompt
        return FAKE_PHASE_B_RESULT

    monkeypatch.setattr(mod, "run_phase_b_multiturn", fake_phase_b)
    monkeypatch.setattr(mod, "_read_turn_field", lambda *_a, **_k: ["report"])
    monkeypatch.setattr(mod, "_estimate_inventory_rows", lambda *_a, **_k: 5)
    return captured


def test_main_dry_run_exits_zero(tmp_path):
    from experiments.sota.exp2_interactive_smoke import main

    ret = main(["--agents", "mistral", "--dry-run", "--no-confirm", "--output-dir", str(tmp_path)])
    assert ret == 0


def test_estimate_inventory_rows_ignores_summary_tables(monkeypatch, tmp_path):
    import experiments.sota.exp2_interactive_smoke as mod

    monkeypatch.setattr(mod, "_read_turn_field", lambda *_a, **_k: ["report"])
    monkeypatch.setattr(
        mod, "_turn_artefact_paths", lambda *_a, **_k: {"raw": tmp_path / "missing"}
    )
    monkeypatch.setattr(
        mod,
        "_narrative_from_record_or_raw",
        lambda *_a, **_k: (
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
            "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n"
            "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n\n"
            "| Fuel | Capacity |\n"
            "| --- | --- |\n"
            "| Coal | 2910 |\n"
            "| Gas | 0 |\n"
        ),
    )

    phase_b = {"records": [object()], "turns": 1}
    assert _estimate_inventory_rows("openai", phase_b, tmp_path) == 3


def test_main_without_manifest_phase_b_gets_raw_designed_prompt(
    phase_a_reuse_dir, patched_phase_b, tmp_path
):
    from experiments.sota.exp2_interactive_smoke import main

    main(
        [
            "--agents",
            "mistral",
            "--reuse-phase-a-from",
            str(phase_a_reuse_dir),
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert patched_phase_b["prompt"] == FAKE_DESIGN["designed_prompt"]


# ---------------------------------------------------------------------------
# TDD tests — currently FAILING; pass after the --evidence-pack-manifest patch
# ---------------------------------------------------------------------------


def test_main_accepts_evidence_pack_manifest_flag(phase_a_reuse_dir, patched_phase_b, tmp_path):
    from experiments.sota.exp2_interactive_smoke import main

    ret = main(
        [
            "--agents",
            "mistral",
            "--reuse-phase-a-from",
            str(phase_a_reuse_dir),
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
            "--evidence-pack-manifest",
            str(MANIFEST_PATH),
        ]
    )
    assert ret == 0


def test_phase_b_prompt_contains_evidence_pack_when_manifest_set(
    phase_a_reuse_dir, patched_phase_b, tmp_path
):
    from experiments.sota.exp2_interactive_smoke import main

    main(
        [
            "--agents",
            "mistral",
            "--reuse-phase-a-from",
            str(phase_a_reuse_dir),
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
            "--evidence-pack-manifest",
            str(MANIFEST_PATH),
        ]
    )
    assert "# Evidence pack" in patched_phase_b["prompt"]
    assert "Chunk 1" in patched_phase_b["prompt"]
    assert FAKE_DESIGN["designed_prompt"] in patched_phase_b["prompt"]


def test_phase_b_prompt_not_augmented_without_manifest(
    phase_a_reuse_dir, patched_phase_b, tmp_path
):
    from experiments.sota.exp2_interactive_smoke import main

    main(
        [
            "--agents",
            "mistral",
            "--reuse-phase-a-from",
            str(phase_a_reuse_dir),
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert "# Evidence pack" not in patched_phase_b["prompt"]


def test_meta_prompt_not_augmented_with_evidence_pack(
    phase_a_reuse_dir, patched_phase_b, tmp_path
):
    """Phase A meta-prompt must include the evidence pack when manifest is set."""
    from experiments.sota.exp2_interactive_smoke import main

    main(
        [
            "--agents",
            "mistral",
            "--reuse-phase-a-from",
            str(phase_a_reuse_dir),
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
            "--evidence-pack-manifest",
            str(MANIFEST_PATH),
        ]
    )
    meta_prompt_file = tmp_path / "mistral_run01" / "mistral_meta_prompt.txt"
    assert meta_prompt_file.exists()
    meta_prompt_text = meta_prompt_file.read_text(encoding="utf-8")
    assert "# Evidence pack" in meta_prompt_text
    assert "## Chunk 1" not in meta_prompt_text
    assert "source_id:" not in meta_prompt_text


def test_meta_prompt_without_manifest_does_not_include_available_evidence_pack_heading(tmp_path):
    from experiments.sota.exp2_interactive_smoke import main

    main(
        [
            "--agents",
            "mistral",
            "--dry-run",
            "--no-confirm",
            "--output-dir",
            str(tmp_path),
        ]
    )
    meta_prompt_file = tmp_path / "mistral_run01" / "mistral_meta_prompt.txt"
    assert meta_prompt_file.exists()
    assert "# Evidence pack" not in meta_prompt_file.read_text(encoding="utf-8")


def test_min_phase_b_max_tokens_flag_present():
    """--min-phase-b-max-tokens must be wired in argparse with a default of 16000."""
    src = open("experiments/sota/exp2_interactive_smoke.py", encoding="utf-8").read()
    assert "--min-phase-b-max-tokens" in src
    assert "default=16000" in src


def test_min_phase_b_max_tokens_floor_applied():
    """Floor must be enforced with max(), not an if-guard, in _run_one_agent."""
    src = open("experiments/sota/exp2_interactive_smoke.py", encoding="utf-8").read()
    # The floor is applied via max(designed, args.min_phase_b_max_tokens)
    assert "args.min_phase_b_max_tokens" in src
    # Must use max(), not a conditional assignment
    assert "max(\n        int(design.get" in src or "= max(" in src
