"""Tests for scripts/verify/incrementality_method.py.

Unit tests only — no real LLM calls.  All external calls are mocked.
"""

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPTS_VERIFY = Path(__file__).parent.parent / "scripts" / "verify"


def _make_mock_client(response_text: str, finish_reason: str = "stop") -> MagicMock:
    """Return an OpenAI-compatible mock client that always returns response_text."""
    choice = MagicMock()
    choice.message.content = response_text
    choice.finish_reason = finish_reason
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 100
    resp.usage.completion_tokens = 50
    resp.usage.model_dump.return_value = {"prompt_tokens": 100, "completion_tokens": 50}
    client = MagicMock()
    client.chat.completions.create.return_value = resp
    return client


# A minimal JSON array response that _llm_extract and _llm_global can parse.
_PLANT_JSON = json.dumps(
    [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": 400,
            "status": "operational",
            "province": "Hai Duong",
            "cod": "1983",
        }
    ]
)


def _mock_ref_plants() -> list:
    """Two reference plants so coverage/precision are well-defined."""
    from aedist.schema import FuelType, Plant, PlantStatus

    return [
        Plant(
            name="Pha Lai", fuel=FuelType.COAL, status=PlantStatus.OPERATIONAL, capacity_mwe=400
        ),
        Plant(
            name="Ba Ria",
            fuel=FuelType.GAS,
            status=PlantStatus.OPERATIONAL,
            capacity_mwe=150,
        ),
    ]


# ---------------------------------------------------------------------------
# Import the script module
# ---------------------------------------------------------------------------


def _import_script():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "incrementality_method",
        _SCRIPTS_VERIFY / "incrementality_method.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Pre-import once (avoids repeated disk reads in tests).
try:
    _script = _import_script()
except Exception:
    _script = None  # will cause tests to fail with a clear import error


# ---------------------------------------------------------------------------
# Test: growth_curve.csv has expected shape
# ---------------------------------------------------------------------------


def test_growth_curve_produces_csv(tmp_path):
    """N=2 fragments, both modes: growth_curve.csv has 4 rows and all F1 values are non-null."""
    if _script is None:
        pytest.fail("Could not import incrementality_method script")

    client = _make_mock_client(_PLANT_JSON)
    ref_plants = _mock_ref_plants()

    from aedist.prototype_v1_fusion import DEFAULT_SEQUENCE

    sequence = DEFAULT_SEQUENCE[:2]

    # Use a real corpus dir — the script reads files from it.
    # We build a temporary mini-corpus with two stub fragment files.
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    for spec in sequence:
        (corpus_dir / spec.filename).write_text(
            "| Name | Fuel | Capacity | Status | Province | COD |\n"
            "|------|------|----------|--------|----------|-----|\n"
            "| Pha Lai | Coal | 400 | Operational | Hai Duong | 1983 |\n",
            encoding="utf-8",
        )

    inc_rows = _script.compute_incremental_growth(
        sequence, corpus_dir, client, "openai/gpt-4o-mini", ref_plants
    )
    glb_rows = _script.compute_global_growth(
        sequence, corpus_dir, client, "openai/gpt-4o-mini", ref_plants
    )
    all_rows = inc_rows + glb_rows

    # Save CSV and verify shape
    csv_path = tmp_path / "growth_curve.csv"
    _script.save_growth_csv(all_rows, csv_path)

    assert csv_path.exists(), "growth_curve.csv was not created"

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 4, f"Expected 4 rows (2 inc + 2 global), got {len(rows)}"

    for row in rows:
        val = row["entity_f1"]
        assert val not in (None, "", "None"), f"entity_f1 is null/empty in row: {row}"
        assert 0.0 <= float(val) <= 1.0, f"entity_f1 out of range: {val}"

    modes = {row["mode"] for row in rows}
    assert modes == {"incremental", "global"}


# ---------------------------------------------------------------------------
# Test: single fragment produces a non-empty master
# ---------------------------------------------------------------------------


def test_single_fragment_produces_nonempty_master(tmp_path):
    """N=1 incremental run produces at least one plant row."""
    if _script is None:
        pytest.fail("Could not import incrementality_method script")

    client = _make_mock_client(_PLANT_JSON)
    ref_plants = _mock_ref_plants()

    from aedist.prototype_v1_fusion import DEFAULT_SEQUENCE

    sequence = DEFAULT_SEQUENCE[:1]

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    spec = sequence[0]
    (corpus_dir / spec.filename).write_text(
        "| Name | Fuel | Capacity | Status | Province | COD |\n"
        "| Pha Lai | Coal | 400 | Operational | Hai Duong | 1983 |\n",
        encoding="utf-8",
    )

    rows = _script.compute_incremental_growth(
        sequence, corpus_dir, client, "openai/gpt-4o-mini", ref_plants
    )

    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    assert rows[0]["N"] == 1
    assert rows[0]["mode"] == "incremental"
    assert rows[0]["system_count"] >= 1, "Expected at least one plant in master after N=1"


# ---------------------------------------------------------------------------
# Test: PDF is created when rows are present
# ---------------------------------------------------------------------------


def test_save_growth_pdf_creates_file(tmp_path):
    """save_growth_pdf writes a .pdf file to the output directory."""
    if _script is None:
        pytest.fail("Could not import incrementality_method script")

    rows = [
        {"N": 1, "mode": "incremental", "entity_f1": 0.5},
        {"N": 1, "mode": "global", "entity_f1": 0.4},
        {"N": 2, "mode": "incremental", "entity_f1": 0.6},
        {"N": 2, "mode": "global", "entity_f1": 0.55},
    ]
    pdf_path = tmp_path / "growth_curve.pdf"
    _script.save_growth_pdf(rows, pdf_path)
    assert pdf_path.exists(), "growth_curve.pdf was not created"
    assert pdf_path.stat().st_size > 0, "growth_curve.pdf is empty"
