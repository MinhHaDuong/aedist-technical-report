"""Insert Kiên Lương complex rows into the pipeline ODS.

Source: GEM wiki (Kien_Luong_power_station) — checked 2026-06-08.
  Phase 1: 2×600 MW coal, certificate revoked April 2017.
  Phase 2: 1200 MW coal (unit split not attested).
  Phase 3: 2000 MW coal (unit split not attested).
  Location: Bình An, Kiên Lương, Kiên Giang.

Usage:
    python data/reference/add_kien_luong.py \
        --src  data/reference/raw/pipeline+extensions-as-plants-2026-06-05.ods \
        --dest data/reference/raw/pipeline+KG-2026-06-08.ods
"""
import argparse
import io
import shutil
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Rows to insert — ordered list of (col_index, value) pairs per row.
# Only non-empty cells are listed; all others become empty table:table-cell.
# Column indices follow the "Power plants" sheet header (0-based).
#   0  Record status    1  Asset type         2  Project stage
#   3  Updated on       4  Complex            5  Plant
#   6  Unit             8  Commune / Xã       9  District / Huyện
#  10  Province / Tỉnh 13  Capacity (MW)     52  Source
# ---------------------------------------------------------------------------
_ROWS = [
    # Kiên Lương 1, Unit 1 — 600 MW coal, cancelled
    {
        1: ("s", "Coal power plant"),
        2: ("s", "9 cancelled"),
        3: ("s", "2026-06"),
        4: ("s", "Kiên Lương"),
        5: ("s", "Kiên Lương 1"),
        6: ("s", "Unit 1"),
        8: ("s", "Bình An"),
        9: ("s", "Kiên Lương"),
        10: ("s", "Kiên Giang"),
        13: ("f", "600"),
        52: ("s", "GEM wiki Kien_Luong_power_station"),
    },
    # Kiên Lương 1, Unit 2 — 600 MW coal, cancelled
    {
        1: ("s", "Coal power plant"),
        2: ("s", "9 cancelled"),
        3: ("s", "2026-06"),
        4: ("s", "Kiên Lương"),
        5: ("s", "Kiên Lương 1"),
        6: ("s", "Unit 2"),
        8: ("s", "Bình An"),
        9: ("s", "Kiên Lương"),
        10: ("s", "Kiên Giang"),
        13: ("f", "600"),
        52: ("s", "GEM wiki Kien_Luong_power_station"),
    },
    # Kiên Lương 2 — 1200 MW coal, cancelled (unit split not attested)
    {
        1: ("s", "Coal power plant"),
        2: ("s", "9 cancelled"),
        3: ("s", "2026-06"),
        4: ("s", "Kiên Lương"),
        5: ("s", "Kiên Lương 2"),
        8: ("s", "Bình An"),
        9: ("s", "Kiên Lương"),
        10: ("s", "Kiên Giang"),
        13: ("f", "1200"),
        52: ("s", "GEM wiki Kien_Luong_power_station"),
    },
    # Kiên Lương 3 — 2000 MW coal, cancelled (unit split not attested)
    {
        1: ("s", "Coal power plant"),
        2: ("s", "9 cancelled"),
        3: ("s", "2026-06"),
        4: ("s", "Kiên Lương"),
        5: ("s", "Kiên Lương 3"),
        8: ("s", "Bình An"),
        9: ("s", "Kiên Lương"),
        10: ("s", "Kiên Giang"),
        13: ("f", "2000"),
        52: ("s", "GEM wiki Kien_Luong_power_station"),
    },
]

# Total real columns in the sheet (columns 0–56 = 57 cols).
_TOTAL_COLS = 57
# Trailing empty cells to pad each row to full width.
_TRAILING = 1026 - _TOTAL_COLS  # ODS internal sheet width


def _cell(col_type: str, value: str) -> str:
    """Return an ODS XML table-cell element string."""
    if col_type == "s":
        return (
            f'<table:table-cell office:value-type="string" calcext:value-type="string">'
            f"<text:p>{value}</text:p></table:table-cell>"
        )
    # float
    return (
        f'<table:table-cell table:style-name="ce507" '
        f'office:value-type="float" office:value="{value}" calcext:value-type="float">'
        f"<text:p>{value}</text:p></table:table-cell>"
    )


def _build_row(cells: dict) -> str:
    """Build a complete ODS table-row XML string from a cells dict."""
    parts = ['<table:table-row table:style-name="ro10">']
    col = 0
    for idx in range(_TOTAL_COLS):
        if idx in cells:
            parts.append(_cell(*cells[idx]))
        else:
            parts.append("<table:table-cell/>")
        col += 1
    # trailing empty cells to fill the sheet width
    parts.append(
        f'<table:table-cell table:number-columns-repeated="{_TRAILING}"/>'
    )
    parts.append("</table:table-row>")
    return "".join(parts)


# Marker: the trailing-empty-rows block that follows the last data row.
_TRAILING_MARKER = '<table:table-row table:style-name="ro1" table:number-rows-repeated="18">'


def patch_ods(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    with zipfile.ZipFile(src, "r") as zin:
        xml = zin.read("content.xml").decode("utf-8")

    # Locate insertion point (before trailing empty rows of Power plants sheet).
    # The marker appears once in the Power plants table.
    idx = xml.index(_TRAILING_MARKER)
    new_rows_xml = "".join(_build_row(r) for r in _ROWS)
    patched = xml[:idx] + new_rows_xml + xml[idx:]

    # Rewrite the zip, replacing only content.xml.
    buf = io.BytesIO()
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(buf, "w") as zout:
        for item in zin.infolist():
            if item.filename == "content.xml":
                zout.writestr(item, patched.encode("utf-8"))
            else:
                zout.writestr(item, zin.read(item.filename))

    dest.write_bytes(buf.getvalue())
    print(f"Written: {dest}  ({dest.stat().st_size:,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    args = parser.parse_args()

    if args.dest.exists():
        raise SystemExit(f"Destination already exists: {args.dest}  (remove it first)")

    patch_ods(args.src, args.dest)
    print("Done. Verify with: uv run python data/reference/extract_ods.py --input", args.dest)


if __name__ == "__main__":
    main()
