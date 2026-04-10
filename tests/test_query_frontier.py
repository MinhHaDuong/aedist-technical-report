"""Tests for aedist.query_frontier — reasoning flag, sweep derivation, budget, dry-run."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_mock_response(prompt_tokens=100, completion_tokens=200):
    """Create a mock OpenAI ChatCompletion response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = "Plant A uses coal."
    resp.choices[0].finish_reason = "stop"
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


def _minimal_models_yaml(tmp_path: Path, *, reasoning: bool = False) -> Path:
    p = tmp_path / "models.yaml"
    lines = (
        "- id: test/tiny-model\n"
        "  name: Tiny\n"
        "  price_per_mtok_in: 1.0\n"
        "  price_per_mtok_out: 2.0\n"
        "  context_window: 8000\n"
        "  country: US\n"
        "  architecture: dense\n"
        "  size_class: edge\n"
    )
    if reasoning:
        lines += "  reasoning: true\n"
    p.write_text(lines)
    return p


def _prompt_file(tmp_path: Path, name: str = "prompt_frontier.txt") -> Path:
    p = tmp_path / name
    p.write_text("List power plants.")
    return p


@patch("aedist.harness.OpenAI")
def test_basic_produces_output(mock_openai_cls, tmp_path):
    """Single run produces a JSON file with expected fields."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    for field in ("model", "sweep", "usage", "wall_seconds", "cost_usd",
                  "max_tokens", "temperature", "model_metadata"):
        assert field in record, f"Missing field: {field}"
    assert record["sweep"] == "frontier"


@patch("aedist.harness.OpenAI")
def test_reasoning_model_omits_temperature(mock_openai_cls, tmp_path):
    """Models with reasoning: true must not send temperature to the API."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path, reasoning=True)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "temperature" not in call_kwargs
    assert call_kwargs["max_tokens"] == 32768


@patch("aedist.harness.OpenAI")
def test_non_reasoning_sends_temperature(mock_openai_cls, tmp_path):
    """Models without reasoning flag send temperature to the API."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path, reasoning=False)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["max_tokens"] == 32768


@patch("aedist.harness.OpenAI")
def test_budget_guard_stops(mock_openai_cls, tmp_path):
    """--budget-usd stops when budget exceeded."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    # cost = (100 * 1.0 + 200 * 2.0) / 1_000_000 = 0.0005 per call
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
            "--repeat", "5",
            "--budget-usd", "0.0008",
        ]):
            from aedist.query_frontier import main
            main()

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) < 5, f"Expected fewer than 5 files, got {len(json_files)}"
    assert len(json_files) >= 1


@patch("aedist.harness.OpenAI")
def test_dry_run_no_api_calls(mock_openai_cls, tmp_path):
    """--dry-run lists models but makes no API calls."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
            "--dry-run",
        ]):
            from aedist.query_frontier import main
            main()

    mock_client.chat.completions.create.assert_not_called()
    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 0


@patch("aedist.harness.OpenAI")
def test_prompt_modules_assembles_prompt(mock_openai_cls, tmp_path):
    """--prompt-modules assembles prompt from module files via assemble_prompt()."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    output_dir = tmp_path / "out"

    # Create modules directory with base + persona + overview
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    (modules_dir / "base.txt").write_text("Base prompt text.")
    (modules_dir / "persona.txt").write_text("You are an expert.")
    (modules_dir / "overview.txt").write_text("Provide an overview.")

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier",
            "--prompt-modules", "persona", "overview",
            "--modules-dir", str(modules_dir),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    # Verify the assembled prompt was sent to the API
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    user_content = messages[0]["content"]
    # persona is prepended before base, overview appended after base
    assert "You are an expert." in user_content
    assert "Base prompt text." in user_content
    assert "Provide an overview." in user_content
    assert user_content.index("You are an expert.") < user_content.index("Base prompt text.")
    assert user_content.index("Base prompt text.") < user_content.index("Provide an overview.")


@patch("aedist.harness.OpenAI")
def test_prompt_modules_empty_list_uses_base_only(mock_openai_cls, tmp_path):
    """--prompt-modules with no modules uses base.txt only."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    output_dir = tmp_path / "out"

    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    (modules_dir / "base.txt").write_text("Base prompt only.")

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier",
            "--prompt-modules",
            "--modules-dir", str(modules_dir),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert messages[0]["content"] == "Base prompt only."


@patch("aedist.harness.OpenAI")
def test_prompt_and_prompt_modules_mutually_exclusive(mock_openai_cls, tmp_path):
    """--prompt and --prompt-modules cannot be used together."""
    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier",
            "--prompt", str(prompt_path),
            "--prompt-modules", "persona",
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            import pytest
            with pytest.raises(SystemExit):
                from aedist.query_frontier import main
                main()


@patch("aedist.harness.OpenAI")
def test_prompt_modules_dry_run(mock_openai_cls, tmp_path):
    """--prompt-modules with --dry-run assembles prompt but makes no API calls."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    output_dir = tmp_path / "out"

    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    (modules_dir / "base.txt").write_text("Base prompt text.")
    (modules_dir / "persona.txt").write_text("You are an expert.")

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier",
            "--prompt-modules", "persona",
            "--modules-dir", str(modules_dir),
            "--models", str(models_path),
            "--output", str(output_dir),
            "--dry-run",
        ]):
            from aedist.query_frontier import main
            main()

    mock_client.chat.completions.create.assert_not_called()


@patch("aedist.harness.OpenAI")
def test_prompt_modules_sweep_name(mock_openai_cls, tmp_path):
    """When using --prompt-modules, sweep is derived from module list."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    output_dir = tmp_path / "out"

    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    (modules_dir / "base.txt").write_text("Base prompt text.")
    (modules_dir / "persona.txt").write_text("You are an expert.")

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier",
            "--prompt-modules", "persona",
            "--modules-dir", str(modules_dir),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    assert record["sweep"] == "modules_persona"


@patch("aedist.harness.OpenAI")
def test_sweep_derived_from_prompt_filename(mock_openai_cls, tmp_path):
    """Sweep field is derived from prompt filename, not hardcoded."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path, name="prompt_frontier_scenarios.txt")
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_frontier", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query_frontier import main
            main()

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    assert record["sweep"] == "frontier_scenarios"
