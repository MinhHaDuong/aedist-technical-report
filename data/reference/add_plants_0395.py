"""Insert plant rows into the pipeline ODS (ticket 0395).

Sources cited per plant:

Kim Sơn — Study E542 (PDP8 draft 3), Table PL9.2 «Cập nhật tiến độ các dự
    án nhiệt điện than đã có trong QHĐ VII ĐC và tổng hợp các vị trí tiềm năng
    xây dựng nhiệt điện than nhập theo vùng» (Institute of Energy / Cục ĐL and
    NLTT, 2020-11). Listed as "ND Kim Sơn", Ninh Bình, 3000 MW, potential coal
    site; no committed schedule → status "1 announced".
    RAG corpus: data/rag_corpus/Study_E542_table_9.2.md

Rạng Đông — Same source (E542 Table PL9.2). Listed as "ND Rạng Đông",
    Nam Định, 2400 MW, "Không xác định" (undetermined). Distinct from the
    existing "Rang Dong cogeneration" entry (100 MW captive cogen, different
    facility). Status "1 announced".
    RAG corpus: data/rag_corpus/Study_E542_table_9.2.md

Yên Hưng — PDP7 Annex 1 table (commissioning schedule, 2029 tranche) and
    PDP7 Annex 2 (same entry). Listed as "ND Yên Hưng #1,2", 1200 MW, coal,
    planned for 2029 commissioning. Location: Yên Hưng (now Quảng Yên),
    Quảng Ninh province. Status "1 announced" (planned in PDP7, not carried
    explicitly in PDP8 coal list; PDP8 LNG conversion context for this site
    is tracked under "LNG Quảng Ninh 3 (Quảng Yên)" which is a separate entry).
    RAG corpus: data/rag_corpus/PDP7_annex1.md, data/rag_corpus/PDP7_annex2.md

Phú Thọ — Same source (E542 Table PL9.2). Listed as "ND Phú Thọ",
    Phú Thọ province, 600 MW, potential coal site. Status "1 announced".
    RAG corpus: data/rag_corpus/Study_E542_table_9.2.md

NOT added in this script (needs-human unresolved):
  Hòa Phát Dung Quất captive power (operating BFG/coal ~240 MW):
    the RAG corpus only documents "NĐ khí dư Hòa Phát II" (300 MW, announced,
    PDP8 table 4) which is already in the reference; the operating captive-power
    phase of the Dung Quất steel complex is not attested in the available primary
    documents and requires an additional source before being added.

Usage:
    python data/reference/add_plants_0395.py \\
        --src  data/reference/raw/pipeline+KG-2026-06-08.ods \\
        --dest data/reference/raw/pipeline+0395-2026-06-09.ods
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
    # Kim Sơn — 3000 MW coal, potential site (E542/PDP8 draft 3)
    {
        1: ("s", "Coal power plant"),
        2: ("s", "1 announced"),
        3: ("s", "2026-06"),
        5: ("s", "Kim Sơn"),
        10: ("s", "Ninh Bình"),
        13: ("f", "3000"),
        52: ("s", "Study E542 PL9.2 (PDP8 draft 3, potential coal sites table)"),
    },
    # Rạng Đông — 2400 MW coal, potential site (E542/PDP8 draft 3)
    # Note: distinct from existing "Rang Dong cogeneration" (100 MW captive cogen).
    {
        1: ("s", "Coal power plant"),
        2: ("s", "1 announced"),
        3: ("s", "2026-06"),
        5: ("s", "Rạng Đông"),
        10: ("s", "Nam Định"),
        13: ("f", "2400"),
        52: ("s", "Study E542 PL9.2 (PDP8 draft 3, potential coal sites table, 'Không xác định')"),
    },
    # Yên Hưng — 1200 MW coal, PDP7 planned
    # Location: Yên Hưng district (now Quảng Yên), Quảng Ninh province.
    {
        1: ("s", "Coal power plant"),
        2: ("s", "1 announced"),
        3: ("s", "2026-06"),
        5: ("s", "Yên Hưng"),
        9: ("s", "Quảng Yên"),
        10: ("s", "Quảng Ninh"),
        13: ("f", "1200"),
        52: ("s", "PDP7 Annex 1 + Annex 2 (2x600 MW #1,2, 2029 tranche, coal)"),
    },
    # Phú Thọ — 600 MW coal, potential site (E542/PDP8 draft 3)
    {
        1: ("s", "Coal power plant"),
        2: ("s", "1 announced"),
        3: ("s", "2026-06"),
        5: ("s", "Phú Thọ"),
        10: ("s", "Phú Thọ"),
        13: ("f", "600"),
        52: ("s", "Study E542 PL9.2 (PDP8 draft 3, potential coal sites table)"),
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
    for idx in range(_TOTAL_COLS):
        if idx in cells:
            parts.append(_cell(*cells[idx]))
        else:
            parts.append("<table:table-cell/>")
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
    print(
        "Done. Verify with: uv run python data/reference/extract_ods.py --input",
        args.dest,
    )


if __name__ == "__main__":
    main()
