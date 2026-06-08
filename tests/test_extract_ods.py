"""Tests for data/reference/extract_ods.py — the ODS -> CSV extraction step.

The validators are the heart of this module: they refuse a bad input file
rather than silently producing a corrupt reference list. Since ticket 0439
the master carries a three-column address (Complex | Plant | Unit); the
designation is derived (Plant + Unit concatenated) and duplicate detection
runs on it *modulo diacritics* — two designations that differ only by
diacritical marks are the SAME entry and must trigger a hard stop. The
integration test anchors acceptance to the real tracked ODS, which is clean
post-0439.

All extraction is dtype=str (no coercion ever): the zero-prefix preservation
principle that bit ires_code (0121 -> 121) applies to every column here.
"""

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from data.reference.extract_ods import (
    STATUS_VOCABULARY,
    V1_STATUS_BY_STAGE,
    derive_level,
    derive_name,
    derive_v1_status,
    read_ods,
    select_columns,
    validate_address_shape,
    validate_capacity_numeric,
    validate_input,
    validate_no_duplicate_names,
    validate_status_vocabulary,
)


def _df(rows: list[tuple[str, str, str]], **extra: list) -> pd.DataFrame:
    """A frame of (Complex, Plant, Unit) address rows; '' becomes a real cell."""
    data = {
        "Complex": [r[0] for r in rows],
        "Plant": [r[1] for r in rows],
        "Unit": [r[2] for r in rows],
    }
    data.update(extra)
    return pd.DataFrame(data)


# --- derive_name / derive_level -----------------------------------------------


def test_derive_name_concatenates_plant_and_unit():
    """A unit row's designation is Plant + Unit — exactly the attested string."""
    df = _df([("", "An Khánh 1", "Unit 1")])
    assert derive_name(df.iloc[0]) == "An Khánh 1 Unit 1"


def test_derive_name_plant_grain_is_bare_plant():
    """Unit empty -> the row IS the plant; designation is the Plant cell."""
    df = _df([("", "Bà Rịa GT", "")])
    assert derive_name(df.iloc[0]) == "Bà Rịa GT"


def test_derive_name_complex_grain_is_bare_complex():
    """Complex alone -> complex-grain row; designation is the Complex cell."""
    df = _df([("LNG Mỹ Giang", "", "")])
    assert derive_name(df.iloc[0]) == "LNG Mỹ Giang"


def test_derive_level_finest_nonempty_wins():
    """Level is the finest non-empty address column (ticket 0401 derivation)."""
    df = _df(
        [
            ("LNG X", "Plant P", "Unit 1"),
            ("", "Plant P", ""),
            ("LNG X", "", ""),
        ]
    )
    assert [derive_level(r) for _, r in df.iterrows()] == ["unit", "plant", "complex"]


# --- validate_address_shape ----------------------------------------------------


def test_unit_without_plant_raises():
    """A Unit with no Plant is an unfinished split — hard stop naming the row."""
    df = _df([("", "", "An Khánh 1 Unit 1")])
    with pytest.raises(ValueError, match="without a Plant"):
        validate_address_shape(df)


def test_empty_address_raises():
    """A row with all three address columns empty is unreferencable."""
    df = _df([("", "", "")])
    with pytest.raises(ValueError, match="no address"):
        validate_address_shape(df)


def test_valid_shapes_pass():
    """Unit rows, plant-grain rows, and complex-grain rows are all accepted."""
    df = _df(
        [
            ("", "Plant A", "Unit 1"),
            ("", "Plant B", ""),
            ("LNG C", "", ""),
            ("LNG D", "Plant E", "Unit 2"),
        ]
    )
    validate_address_shape(df)  # must not raise


# --- validate_no_duplicate_names ------------------------------------------------


def test_duplicate_designation_raises():
    """An exact duplicate designation must raise ValueError naming the offender."""
    df = _df(
        [
            ("", "Quảng Trị 1", "Unit 2"),
            ("", "Plant B", ""),
            ("", "Quảng Trị 1", "Unit 2"),
        ]
    )
    with pytest.raises(ValueError, match="Quảng Trị 1 Unit 2"):
        validate_no_duplicate_names(df)


def test_no_duplicate_passes():
    """A clean DataFrame is accepted silently (no over-eager rejection)."""
    validate_no_duplicate_names(_df([("", "Plant A", ""), ("", "Plant B", ""), ("", "Plant C", "")]))


def test_diacritic_variants_are_duplicates():
    """Designations that differ ONLY by diacritics fold to the same key -> duplicate.

    'Duyen Hai 2 Unit 1' and 'Duyên Hải 2 Unit 1' are the same unit recorded
    twice. The validator must catch this even though the raw strings differ.
    A validator that only does exact-string matching would pass the other
    tests but fail this one — this is the discriminator.
    """
    df = _df([("", "Duyen Hai 2", "Unit 1"), ("", "Duyên Hải 2", "Unit 1")])
    with pytest.raises(ValueError):
        validate_no_duplicate_names(df)


def test_duplicate_message_reports_original_surface_form():
    """The error reports the original (diacritic-bearing) designation, not the folded key."""
    df = _df([("", "Quang Tri 1", ""), ("", "Quảng Trị 1", "")])
    with pytest.raises(ValueError, match="Quảng Trị 1"):
        validate_no_duplicate_names(df)


def test_case_only_difference_is_duplicate():
    """Folding is case-insensitive: case-only variants are duplicates."""
    df = _df([("", "Vung Ang 2", ""), ("", "vung ang 2", "")])
    with pytest.raises(ValueError):
        validate_no_duplicate_names(df)


def test_plant_grain_vs_unit_row_same_plant_not_duplicate():
    """'Plant A' (plant-grain elsewhere impossible by exclusivity, but the
    validator itself only compares full designations): 'Plant A' vs
    'Plant A Unit 1' are distinct designations — no false positive."""
    df = _df([("", "Plant A", ""), ("", "Plant A", "Unit 1")])
    validate_no_duplicate_names(df)  # must not raise


def test_validate_input_runs_shape_then_duplicates():
    """validate_input composes the validators (duplicate still caught)."""
    df = _df([("", "Dup", ""), ("", "Dup", "")])
    with pytest.raises(ValueError):
        validate_input(df)


# --- validate_status_vocabulary -------------------------------------------------


def _stage_df(stages: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"Project stage": stages})


def test_all_nine_labels_accepted():
    """Every label of the closed vocabulary passes (no over-eager rejection)."""
    validate_status_vocabulary(_stage_df(list(STATUS_VOCABULARY)))  # must not raise


def test_unknown_stage_hard_stops():
    """A value outside the ladder is a data-entry error — hard stop, named."""
    df = _stage_df(["6 operating", "7 mothballed"])
    with pytest.raises(ValueError, match="7 mothballed"):
        validate_status_vocabulary(df)


def test_pre_renumber_label_hard_stops():
    """The old ladder's labels are no longer valid — no silent coercion.

    '5 operating' was the pre-2026-06-05 label for today's '6 operating'; a
    validator that normalized instead of refusing would mask a master file
    saved with the wrong vocabulary version.
    """
    with pytest.raises(ValueError, match="5 operating"):
        validate_status_vocabulary(_stage_df(["5 operating"]))


def test_empty_stage_hard_stops():
    """An empty stage cell is out-of-vocabulary too (every row carries one)."""
    with pytest.raises(ValueError, match="<empty>"):
        validate_status_vocabulary(_stage_df([""]))


def test_validate_input_includes_vocabulary():
    """validate_input composes the vocabulary check."""
    df = _df([("", "Plant A", "")], **{"Project stage": ["bogus"]})
    with pytest.raises(ValueError, match="bogus"):
        validate_input(df)


# --- validate_capacity_numeric (ticket 0442) ------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        "Err:510",
        "#VALUE!",
        "#REF!",
        "#DIV/0!",
        "#NAME?",
        "#N/A",
        "#NULL!",
        "abc",
    ],
    ids=lambda v: v.replace("#", "hash-").replace("!", "").replace("/", "-").replace(":", "-"),
)
def test_capacity_error_string_hard_stops(bad_value):
    """Spreadsheet error strings in capacity must hard-stop extraction.

    Ticket 0442: Err:510 leaked through extract_ods into the CSV; the failure
    surfaced only downstream in aggregate_units. Extraction is the primary
    catch — it must refuse with an actionable message naming both the offending
    row and the bad value.
    """
    df = _df(
        [("", "Plant A", "Unit 1")],
        **{"Capacity (MW)": [bad_value]},
    )
    with pytest.raises(ValueError, match=re.escape(bad_value)):
        validate_capacity_numeric(df)


def test_capacity_empty_is_allowed():
    """Empty capacity is legitimate (planned plants with unknown MW)."""
    df = _df(
        [("", "Plant A", "")],
        **{"Capacity (MW)": [""]},
    )
    validate_capacity_numeric(df)  # must not raise


def test_capacity_nan_is_allowed():
    """NaN capacity (raw ODS blank cell) is treated like empty — allowed."""
    df = _df(
        [("", "Plant A", "")],
        **{"Capacity (MW)": [float("nan")]},
    )
    validate_capacity_numeric(df)  # must not raise


def test_capacity_valid_number_passes():
    """A valid numeric capacity string passes validation."""
    df = _df(
        [("", "Plant A", "Unit 1"), ("", "Plant B", "")],
        **{"Capacity (MW)": ["650", "1200.5"]},
    )
    validate_capacity_numeric(df)  # must not raise


def test_capacity_error_message_names_row():
    """The diagnostic must name the offending spreadsheet row number.

    Row numbering: df index 0 + HEADER_ROW(4) + 2 = row 6 in the spreadsheet.
    """
    df = _df(
        [("", "Plant A", "Unit 1")],
        **{"Capacity (MW)": ["Err:510"]},
    )
    with pytest.raises(ValueError, match="row 6"):
        validate_capacity_numeric(df)


def test_validate_input_includes_capacity_check():
    """validate_input composes the capacity numericness check (ticket 0442)."""
    df = _df(
        [("", "Plant A", "")],
        **{"Capacity (MW)": ["Err:510"], "Project stage": ["6 operating"]},
    )
    with pytest.raises(ValueError, match="Err:510"):
        validate_input(df)


# --- derive_v1_status (pipe-owned projection, NOT wired to extraction) ----------


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("0 exploring", "proposed"),
        ("1 announced", "proposed"),
        ("2 proposed", "proposed"),
        ("3 added to PDP", "planned"),
        ("4 permitted", "planned"),
        ("5 construction", "constructing"),
        ("6 operating", "operational"),
        ("9 cancelled", "cancelled"),
        ("10 retired", "retired"),
    ],
)
def test_derive_v1_status_all_rungs(stage, expected):
    """The exhaustive derivation table, rung by rung (Conventions sheet)."""
    assert derive_v1_status(stage) == expected


def test_derive_v1_status_unknown_raises_keyerror():
    """An invented stage raises KeyError — never a .get default.

    Silently mapping a typo would corrupt scoring downstream; the projection
    is only as trustworthy as its refusal to guess.
    """
    with pytest.raises(KeyError):
        derive_v1_status("11 dismantled")


def test_derivation_table_covers_exactly_the_vocabulary():
    """Table exhaustiveness is structural: keys == closed vocabulary."""
    assert set(V1_STATUS_BY_STAGE) == set(STATUS_VOCABULARY)


# --- select_columns: projection, rename, derivations ---------------------------


def _full_raw_frame() -> pd.DataFrame:
    """A raw frame carrying every source column select_columns expects."""
    return pd.DataFrame(
        {
            "Complex": [""],
            "Plant": ["Plant A"],
            "Unit": ["Unit 1"],
            "Province / Tỉnh": ["Hà Nội"],
            "Asset type": ["Power plant"],
            "Capacity (MW)": ["650"],
            "Project stage": ["6 operating"],
        }
    )


def test_select_columns_schema_and_derivations():
    """name leads, address columns follow, level is always derived."""
    out = select_columns(_full_raw_frame())
    assert list(out.columns) == [
        "name",
        "complex",
        "plant",
        "unit",
        "province",
        "asset_type",
        "capacity_mwe",
        "status",
        "level",
    ]
    assert out["name"].iloc[0] == "Plant A Unit 1"
    assert out["level"].iloc[0] == "unit"
    assert out["capacity_mwe"].iloc[0] == "650"


def test_select_columns_missing_source_column_raises():
    """A missing expected source column is an actionable error, not silent NaN."""
    df = pd.DataFrame({"Plant": ["Plant A"]})
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
            {"Plant": "Plant A", "ires_code": "0121", "Capacity (MW)": "650"},
            {"Plant": "Plant B", "ires_code": "0007", "Capacity (MW)": "60"},
        ],
    )
    df = read_ods(ods)
    assert df["ires_code"].tolist() == ["0121", "0007"]
    assert df["Capacity (MW)"].iloc[0] == "650"
    assert isinstance(df["Capacity (MW)"].iloc[0], str)


# --- integration: the real tracked ODS must be accepted -----------------------


@pytest.mark.integration
def test_tracked_ods_extraction_green(tmp_path):
    """The pinned snapshot passes extraction — the 0439 exit bar as a test.

    Post-0439 the master is migrated to the three-column address and its known
    duplicates are fixed; extraction must accept it and write the v2 CSV with
    the derived name/level columns. A regression here means either the
    snapshot or the pin moved without the other.
    """
    import subprocess

    from aedist.config import VN_THERMAL_MASTER_SNAPSHOT_ODS

    repo_root = Path(__file__).resolve().parent.parent
    ods = VN_THERMAL_MASTER_SNAPSHOT_ODS
    script = repo_root / "data" / "reference" / "extract_ods.py"
    out = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(ods), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert out.exists(), "extraction must write the CSV on success"
    df = pd.read_csv(out, dtype=str)
    assert {"name", "complex", "plant", "unit", "level"} <= set(df.columns)
    assert len(df) > 200
    assert not df["name"].duplicated().any()
