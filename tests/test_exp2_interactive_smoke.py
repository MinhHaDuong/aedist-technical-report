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
