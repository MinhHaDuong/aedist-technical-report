"""Tests for aedist.query — repeat, budget guard, dry-run, operational metrics."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_response(prompt_tokens=100, completion_tokens=200):
    """Create a mock OpenAI ChatCompletion response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = "name,fuel\nPlant A,coal"
    resp.choices[0].finish_reason = "stop"
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


def _minimal_models_yaml(tmp_path: Path) -> Path:
    """Write a minimal models.yaml with one cheap model."""
    p = tmp_path / "models.yaml"
    p.write_text(
        "- id: test/tiny-model\n"
        "  name: Tiny\n"
        "  price_per_mtok_in: 1.0\n"
        "  price_per_mtok_out: 2.0\n"
        "  context_window: 8000\n"
        "  country: US\n"
        "  architecture: dense\n"
        "  size_class: edge\n"
    )
    return p


def _prompt_file(tmp_path: Path) -> Path:
    p = tmp_path / "prompt.txt"
    p.write_text("List power plants.")
    return p


@patch("aedist.harness.OpenAI")
def test_repeat_produces_n_files(mock_openai_cls, tmp_path):
    """--repeat 3 produces 3 JSON files per model."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
            "--repeat", "3",
        ]):
            from aedist.query import main
            main()

    # Find JSON files in the date subdirectory
    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 3
    stems = sorted(f.stem for f in json_files)
    assert stems == ["tiny-model-run1", "tiny-model-run2", "tiny-model-run3"]


@patch("aedist.harness.OpenAI")
def test_output_json_has_operational_metrics(mock_openai_cls, tmp_path):
    """Output JSON includes wall_seconds, cost_usd, model_metadata, run."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
        ]):
            from aedist.query import main
            main()

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    assert "wall_seconds" in record
    assert "cost_usd" in record
    assert "model_metadata" in record
    assert "run" in record
    assert isinstance(record["wall_seconds"], float)
    assert isinstance(record["cost_usd"], float)
    assert record["run"] == 1


@patch("aedist.harness.OpenAI")
def test_budget_guard_stops(mock_openai_cls, tmp_path):
    """--budget-usd stops when budget exceeded."""
    mock_client = MagicMock()
    # Each call uses 100 prompt + 200 completion tokens
    # With price_per_mtok_in=1.0, price_per_mtok_out=2.0:
    # cost = (100 * 1.0 + 200 * 2.0) / 1_000_000 = 0.0005 per call
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    # Budget of 0.0008 should allow 1 call but stop before the 2nd
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
            "--repeat", "5",
            "--budget-usd", "0.0008",
        ]):
            from aedist.query import main
            main()

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) < 5, f"Expected fewer than 5 files, got {len(json_files)}"
    assert len(json_files) >= 1, "Should produce at least 1 file"


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
            "query", "--prompt", str(prompt_path),
            "--models", str(models_path),
            "--output", str(output_dir),
            "--dry-run",
        ]):
            from aedist.query import main
            main()

    mock_client.chat.completions.create.assert_not_called()
    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) == 0


@patch("aedist.harness.OpenAI")
def test_skip_existing_files(mock_openai_cls, tmp_path):
    """Existing files are skipped — no duplicate API calls."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    models_path = _minimal_models_yaml(tmp_path)
    prompt_path = _prompt_file(tmp_path)
    output_dir = tmp_path / "out"

    # Run twice
    for _ in range(2):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
            with patch.object(sys, "argv", [
                "query", "--prompt", str(prompt_path),
                "--models", str(models_path),
                "--output", str(output_dir),
            ]):
                from aedist.query import main
                main()

    # Only 1 API call (second run should skip)
    assert mock_client.chat.completions.create.call_count == 1
