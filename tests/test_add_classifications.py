"""Tests for data/reference/add_classifications.py — fuel -> IRES/ISIC columns.

The script adds four classification columns (ires_code, ires_label, isic_code,
pypsa_carrier) keyed on a CSV's fuel column. Ticket 0416 rewrote it from an
in-place mutator to an argparse input -> output transform so it slots into the
acquire.mk reference pipe without mutating its input.

ires_code is a zero-prefixed string ("0121"); the script must read and write
all-text so the 0121 -> 121 coercion (the defect that motivated the v2 pipe)
can never recur.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from data.reference.add_classifications import FUEL_MAP, add_columns


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_add_columns_maps_fuels(tmp_path):
    """A coal/gas/gas-oil CSV gets correct IRES + carrier columns."""
    src = tmp_path / "in.csv"
    dst = tmp_path / "out.csv"
    _write_csv(
        src,
        "name,fuel",
        ["Plant A,coal", "Plant B,gas", "Plant C,gas/oil"],
    )
    add_columns(src, dst, fuel_col="fuel")

    out = dst.read_text(encoding="utf-8").splitlines()
    assert out[0] == "name,fuel,ires_code,ires_label,isic_code,pypsa_carrier"
    assert out[1] == "Plant A,coal,0121,Hard coal,D3510,coal"
    assert "0311,Natural gas,D3510,CCGT" in out[2]


def test_input_not_mutated(tmp_path):
    """The input file is untouched — output goes to a distinct path."""
    src = tmp_path / "in.csv"
    dst = tmp_path / "out.csv"
    original = "name,fuel\nPlant A,coal\n"
    src.write_text(original, encoding="utf-8")
    add_columns(src, dst, fuel_col="fuel")
    assert src.read_text(encoding="utf-8") == original


def test_ires_code_zero_prefix_survives(tmp_path):
    """ires_code is written as the string '0121', never coerced to 121."""
    src = tmp_path / "in.csv"
    dst = tmp_path / "out.csv"
    _write_csv(src, "name,fuel", ["Plant A,coal"])
    add_columns(src, dst, fuel_col="fuel")
    body = dst.read_text(encoding="utf-8").splitlines()[1]
    assert ",0121," in body


def test_unmapped_fuel_leaves_blank_classification(tmp_path):
    """An unmapped fuel yields empty IRES fields (warned, not crashed)."""
    src = tmp_path / "in.csv"
    dst = tmp_path / "out.csv"
    _write_csv(src, "name,fuel", ["Plant A,uranium"])
    add_columns(src, dst, fuel_col="fuel")
    body = dst.read_text(encoding="utf-8").splitlines()[1]
    # name, fuel, then four columns: ires_code/label blank, isic set, carrier blank
    assert body == "Plant A,uranium,,,D3510,"


def test_fuel_map_covers_v2_fuels():
    """The fuel map covers every label aggregate_units emits (coal/gas/gas/oil)."""
    for fuel in ("coal", "gas", "gas/oil"):
        assert fuel in FUEL_MAP


@pytest.mark.integration
def test_cli_input_output(tmp_path):
    """The argparse CLI reads --input and writes --output."""
    src = tmp_path / "in.csv"
    dst = tmp_path / "out.csv"
    _write_csv(src, "name,fuel", ["Plant A,coal"])
    script = Path(__file__).resolve().parent.parent / "data" / "reference" / "add_classifications.py"
    r = subprocess.run(
        [sys.executable, str(script), "--input", str(src), "--output", str(dst), "--fuel-col", "fuel"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert dst.exists()
    assert "0121" in dst.read_text(encoding="utf-8")
