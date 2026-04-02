"""Tests for aedist.verify — verification pipeline."""

import csv
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_input_json(tmp_path: Path, csv_content: str) -> Path:
    """Create a query output JSON with embedded CSV response."""
    p = tmp_path / "test-model-run1.json"
    p.write_text(json.dumps({
        "model": "test/model",
        "run": 1,
        "date": "2026-04-01",
        "response": csv_content,
    }))
    return p


def _make_gem_csv(tmp_path: Path) -> Path:
    """Create a minimal GEM reference CSV."""
    p = tmp_path / "gem_thermal.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Province", "Fuel", "Capacity", "Status", "Aggregated Units"])
        w.writerow(["Pha Lai", "Hai Duong", "Coal", "1040.0", "operating", "Unit 1, Unit 2"])
        w.writerow(["Ba Ria", "Ba Ria - Vung Tau", "gas", "1200.0", "cancelled", "2"])
        w.writerow(["Nhon Trach 1", "Dong Nai", "gas", "450.0", "operating", "1"])
    return p


def test_tool_mode_verifies_known_plants(tmp_path):
    """--mode tool correctly identifies plants found in GEM database."""
    input_json = _make_input_json(tmp_path, (
        "name,fuel,status,cod,province,capacity_mwe\n"
        "Pha Lai,coal,operating,1985,Hai Duong,1040\n"
        "Fake Plant,coal,planned,2030,Nowhere,500\n"
        "Ba Ria,gas,cancelled,,Ba Ria - Vung Tau,1200\n"
    ))
    gem_path = _make_gem_csv(tmp_path)
    output_dir = tmp_path / "verified"

    with patch.object(sys, "argv", [
        "verify",
        "--input", str(input_json),
        "--mode", "tool",
        "--reference", str(gem_path),
        "--output", str(output_dir),
    ]):
        from aedist.verify import main
        main()

    # Check summary JSON
    summary_files = list(output_dir.glob("*_summary.json"))
    assert len(summary_files) == 1
    summary = json.loads(summary_files[0].read_text())
    assert "verified_rate" in summary
    assert "fabricated_rate" in summary
    assert "uncertain_rate" in summary

    # Pha Lai and Ba Ria should be verified, Fake Plant should not
    assert summary["verified_rate"] > 0
    assert summary["fabricated_rate"] > 0

    # Check annotated CSV
    csv_files = list(output_dir.glob("*.csv"))
    assert len(csv_files) == 1
    with open(csv_files[0]) as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 3

    # Find the Pha Lai row
    pha_lai = [r for r in reader if "Pha Lai" in r.get("name", "")]
    assert len(pha_lai) == 1
    assert pha_lai[0]["verified"] == "True"

    # Find the Fake Plant row
    fake = [r for r in reader if "Fake" in r.get("name", "")]
    assert len(fake) == 1
    assert fake[0]["verified"] == "False"


def test_tool_mode_empty_csv(tmp_path):
    """--mode tool handles input with no CSV gracefully."""
    input_json = _make_input_json(tmp_path, "No CSV here, just text.")
    gem_path = _make_gem_csv(tmp_path)
    output_dir = tmp_path / "verified"

    with patch.object(sys, "argv", [
        "verify",
        "--input", str(input_json),
        "--mode", "tool",
        "--reference", str(gem_path),
        "--output", str(output_dir),
    ]):
        from aedist.verify import main
        # Should not crash, just warn
        main()


def test_self_mode_calls_api(tmp_path):
    """--mode self sends CSV back to same model for verification."""
    input_json = _make_input_json(tmp_path, (
        "name,fuel,status,cod,province,capacity_mwe\n"
        "Pha Lai,coal,operating,1985,Hai Duong,1040\n"
    ))
    output_dir = tmp_path / "verified"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        "Verification results:\n"
        "Pha Lai: VERIFIED - This is a real coal plant in Hai Duong."
    )
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 100

    with patch("aedist.harness.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_cls.return_value = mock_client

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
            with patch.object(sys, "argv", [
                "verify",
                "--input", str(input_json),
                "--mode", "self",
                "--output", str(output_dir),
            ]):
                from aedist.verify import main
                main()

    mock_client.chat.completions.create.assert_called_once()
    # Verify the model used matches the input JSON's model
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs.get("model") == "test/model" or call_kwargs[1].get("model") == "test/model"
