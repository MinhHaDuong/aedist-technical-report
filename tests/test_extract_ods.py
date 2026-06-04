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
    read_ods,
    select_columns,
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


# --- select_columns: success path (projection, rename, Level passthrough) ----


def _full_raw_frame(with_level: bool = False) -> pd.DataFrame:
    """A raw frame carrying every source column select_columns expects."""
    data = {
        "Project name": ["Plant A"],
        "Province / Tỉnh": ["Hà Nội"],
        "Asset type": ["Power plant"],
        "Capacity (MW)": ["650"],
        "Project stage": ["Operating"],
    }
    if with_level:
        data["Level"] = ["plant"]
    return pd.DataFrame(data)


def test_select_columns_renames_to_snake_case():
    """Source columns are projected and renamed; unmapped columns are dropped."""
    out = select_columns(_full_raw_frame())
    assert list(out.columns) == ["name", "province", "asset_type", "capacity_mwe", "status"]
    assert out["name"].iloc[0] == "Plant A"
    assert out["capacity_mwe"].iloc[0] == "650"


def test_select_columns_level_passthrough_when_present():
    """A Level column passes through, renamed to `level` (exit criterion)."""
    out = select_columns(_full_raw_frame(with_level=True))
    assert "level" in out.columns
    assert out["level"].iloc[0] == "plant"


def test_select_columns_omits_level_when_absent():
    """No `level` column when the source has no Level (graceful no-op)."""
    out = select_columns(_full_raw_frame(with_level=False))
    assert "level" not in out.columns


def test_select_columns_missing_source_column_raises():
    """A missing expected source column is an actionable error, not silent NaN."""
    df = pd.DataFrame({"Project name": ["Plant A"]})
    with pytest.raises(ValueError, match="absent"):
        select_columns(df)


# --- zero-prefix / dtype=str preservation (unit, synthetic) ------------------


def _write_ods(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a minimal ODS whose "Power plants" sheet matches the real layout.

    Mirrors the master: row 0 = title, rows 1-3 = metadata, row 4 = headers,
    then data — so read_ods's header=4 lands on the real column names.
    """
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    table = Table(name="Power plants")

    def _row(cells: list[str]) -> TableRow:
        tr = TableRow()
        for value in cells:
            tc = TableCell(valuetype="string")
            tc.addElement(P(text=value))
            tr.addElement(tc)
        return tr

    headers = list(rows[0].keys())
    table.addElement(_row(["Pipeline master"]))  # row 0: title
    for _ in range(3):  # rows 1-3: metadata padding
        table.addElement(_row([""]))
    table.addElement(_row(headers))  # row 4: column names
    for record in rows:
        table.addElement(_row([record[h] for h in headers]))
    doc.spreadsheet.addElement(table)
    doc.save(str(path))


def test_read_ods_keeps_zero_prefix_as_string(tmp_path):
    """read_ods round-trips a zero-prefixed value as a string via the real read.

    Anchors the dtype=str exit criterion to extract_ods's own read path, not a
    hand-built DataFrame: '0121' read from an ODS cell must stay '0121', never
    become '121' or the int 121. Capacity is likewise kept as a string.
    """
    ods = tmp_path / "tiny.ods"
    _write_ods(
        ods,
        [
            {"Project name": "Plant A", "ires_code": "0121", "Capacity (MW)": "650"},
            {"Project name": "Plant B", "ires_code": "0007", "Capacity (MW)": "60"},
        ],
    )
    df = read_ods(ods)
    assert df["ires_code"].tolist() == ["0121", "0007"]
    assert df["Capacity (MW)"].iloc[0] == "650"
    assert isinstance(df["Capacity (MW)"].iloc[0], str)


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
