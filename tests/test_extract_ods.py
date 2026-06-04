"""Tests for data/reference/extract_ods.py — the ODS -> CSV extraction step.

The validators are the heart of this module: they refuse a bad input file
rather than silently producing a corrupt reference list. The exit criterion
(ticket 0420) is explicit that name duplication is checked *modulo diacritics*
— two names that differ only by diacritical marks are the SAME entry and must
trigger a hard stop. The integration test anchors this to the real tracked
ODS, which contains a genuine duplicate.

All extraction is dtype=str (no coercion ever): the zero-prefix preservation
principle that bit ires_code (0121 -> 121) applies to every column here.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

from data.reference.extract_ods import (
    validate_input,
    validate_no_duplicate_names,
    validate_unit_level_consistency,
)


def _df(names: list[str], **extra: list) -> pd.DataFrame:
    data = {"Project name": names}
    data.update(extra)
    return pd.DataFrame(data)


# --- validate_no_duplicate_names ---------------------------------------------


def test_duplicate_name_raises():
    """An exact duplicate Project name must raise ValueError naming the offender."""
    df = _df(["Quảng Trị 1 Unit 2", "Plant B", "Quảng Trị 1 Unit 2"])
    with pytest.raises(ValueError, match="Quảng Trị 1 Unit 2"):
        validate_no_duplicate_names(df)


def test_no_duplicate_passes():
    """A clean DataFrame is accepted silently (no over-eager rejection)."""
    validate_no_duplicate_names(_df(["Plant A", "Plant B", "Plant C"]))


def test_diacritic_variants_are_duplicates():
    """Names that differ ONLY by diacritics fold to the same key -> duplicate.

    This is the concrete meaning of the exit criterion's "modulo diacritiques":
    'Duyen Hai 2 Unit 1' and 'Duyên Hải 2 Unit 1' are the same unit recorded
    twice. The validator must catch this even though the raw strings differ.
    A validator that only does exact-string matching would pass the other
    tests but fail this one — this is the discriminator.
    """
    df = _df(["Duyen Hai 2 Unit 1", "Duyên Hải 2 Unit 1"])
    with pytest.raises(ValueError):
        validate_no_duplicate_names(df)


def test_duplicate_message_reports_original_surface_form():
    """The error reports the original (diacritic-bearing) name, not the folded key."""
    df = _df(["Quang Tri 1", "Quảng Trị 1"])
    with pytest.raises(ValueError, match="Quảng Trị 1"):
        validate_no_duplicate_names(df)


def test_case_only_difference_is_duplicate():
    """Folding is case-insensitive: case-only variants are duplicates."""
    df = _df(["Vung Ang 2", "vung ang 2"])
    with pytest.raises(ValueError):
        validate_no_duplicate_names(df)


# --- validate_unit_level_consistency -----------------------------------------


def test_level_absent_is_noop():
    """With no Level column the consistency rule is a graceful no-op."""
    df = _df(["Plant A Unit 1", "Plant B"])
    validate_unit_level_consistency(df)  # must not raise


def test_level_present_violation_raises():
    """A 'Unit' name with a non-unit Level fails with an actionable message."""
    df = _df(["Plant A Unit 1", "Plant B"], Level=["plant", "plant"])
    with pytest.raises(ValueError, match="Plant A Unit 1"):
        validate_unit_level_consistency(df)


def test_level_present_consistent_passes():
    """A 'Unit' name with a unit-level Level is accepted."""
    df = _df(["Plant A Unit 1", "Plant B"], Level=["unité", "plant"])
    validate_unit_level_consistency(df)  # must not raise


def test_validate_input_runs_both_checks():
    """validate_input composes the two validators (duplicate still caught)."""
    df = _df(["Dup", "Dup"])
    with pytest.raises(ValueError):
        validate_input(df)


# --- zero-prefix / dtype=str preservation (unit, synthetic) ------------------


def test_zero_prefix_preserved_as_string():
    """dtype=str round-trips a zero-prefixed code without numeric coercion.

    Documents the invariant directly: '0121' must stay '0121', never become
    '121' or 121. This is the column-agnostic guarantee extract_ods relies on.
    """
    df = pd.DataFrame({"ires_code": ["0121"]}, dtype=str)
    assert df["ires_code"].iloc[0] == "0121"


# --- integration: the real tracked ODS must be refused -----------------------


@pytest.mark.integration
def test_tracked_ods_duplicate_fires(tmp_path):
    """The tracked pipeline.ods contains 'Quảng Trị 1 Unit 2' twice.

    extract_ods.py must refuse it (non-zero exit) with an actionable message
    naming the offending plant. This refusal is correct behaviour — a
    data-quality signal — not a bug to work around. The fix belongs in the
    master file, not in this validator.
    """
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent
    ods = repo_root / "data" / "reference" / "raw" / "pipeline.ods"
    script = repo_root / "data" / "reference" / "extract_ods.py"
    out = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(ods), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (result.stdout, result.stderr)
    combined = result.stdout + result.stderr
    assert "Quảng Trị 1 Unit 2" in combined, combined
    assert not out.exists(), "no CSV must be written when validation fails"
