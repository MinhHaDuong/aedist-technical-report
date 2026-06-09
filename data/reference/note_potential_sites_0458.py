"""Note the three E542 PL9.2 potential sites on the master, without aliasing (ticket 0458).

Master-side companion to the 0497 removal. Kim Sơn, Rạng Đông and Phú Thọ are draft
*potential sites* from Study E542 Table PL9.2 ("tổng hợp các vị trí tiềm năng" /
summary of potential coal-power locations), not projects — so they are not counted
reference rows (PROVENANCE.md "Traceability without counting").

They are NOT recorded as aliases: there is **no specific correspondence** between a
PL9.2 candidate location and any one of the existing PDP7 northern "NĐ Miền Bắc 1/2/3"
cancelled slots (interchangeable placeholders, Region "Bắc Bộ", no capacity). Writing a
name into the Project alias column would falsely assert such a 1:1 match. Instead this
script appends a free-text **Note** on each slot stating the non-correspondence and
citing E542 PL9.2, keeping the cross-reference findable without implying identity.

The Note column is NOT extracted by ``extract_ods.py`` (it projects
name/complex/plant/unit/province/asset_type/capacity/status/level only), so the
regenerated 177-plant reference is byte-identical — verified by
``verify_master_convergence.py``.

Usage:
    python data/reference/note_potential_sites_0458.py \\
        --src  data/reference/raw/pipeline+0497-2026-06-09.ods \\
        --dest data/reference/raw/pipeline+0458-2026-06-09.ods
"""
import argparse
from pathlib import Path

from odf.opendocument import load
from odf.table import Table, TableCell, TableRow
from odf.text import P

# NĐ Miền Bắc cancelled slots that receive the non-correspondence note.
_SLOTS = ("NĐ Miền Bắc 1", "NĐ Miền Bắc 2", "NĐ Miền Bắc 3")
_PLANT_COL = 5   # 0-indexed "Plant" column
_NOTE_COL = 54   # 0-indexed "Note " column (where the existing slot annotation lives)

_NOTE_TEXT = (
    "No specific correspondence to the E542 Table PL9.2 potential coal sites "
    "(Kim Sơn, Rạng Đông, Phú Thọ): candidate locations, not matched 1:1 to these slots."
)

_CHANGELOG_ROWS = [
    ("2026-06-09", "Reverse-sync (ticket 0458): replay extensions (0445), Kiên Lương (0472), Yên Hưng (0395)."),
    ("2026-06-09", "Note E542 PL9.2 potential sites (Kim Sơn / Rạng Đông / Phú Thọ) on NĐ Miền Bắc 1/2/3 — no specific correspondence, not counted rows."),
]


def _cell_text(cell: TableCell) -> str:
    return "".join(str(p) for p in cell.getElementsByType(P))


def _table(doc, name: str) -> Table:
    for t in doc.spreadsheet.getElementsByType(Table):
        if t.getAttribute("name") == name:
            return t
    raise KeyError(f"sheet {name!r} not found")


def _column_text(row: TableRow, target_col: int) -> str:
    col = 0
    for cell in row.getElementsByType(TableCell):
        rep = int(cell.getAttribute("numbercolumnsrepeated") or 1)
        if col <= target_col < col + rep:
            return _cell_text(cell)
        col += rep
    return ""


def _add_note(row: TableRow, target_col: int, text: str) -> None:
    """Append ``text`` as a new line in ``target_col``.

    If the target cell already carries a note (e.g. NĐ Miền Bắc 1), add a second
    ``text:p`` paragraph. If it is an empty repeated run, split it into
    [empty-before][note-cell][empty-after], preserving the column span.
    """
    col = 0
    for cell in list(row.getElementsByType(TableCell)):
        rep = int(cell.getAttribute("numbercolumnsrepeated") or 1)
        if col <= target_col < col + rep:
            if _cell_text(cell):
                cell.addElement(P(text=text))  # append a new paragraph, keep existing note
                return
            before = target_col - col
            after = (col + rep - 1) - target_col
            parent = cell.parentNode
            replacements = []
            if before > 0:
                bc = TableCell()
                if before > 1:
                    bc.setAttribute("numbercolumnsrepeated", str(before))
                replacements.append(bc)
            note = TableCell(valuetype="string")
            note.addElement(P(text=text))
            replacements.append(note)
            if after > 0:
                ac = TableCell()
                if after > 1:
                    ac.setAttribute("numbercolumnsrepeated", str(after))
                replacements.append(ac)
            for rc in replacements:
                parent.insertBefore(rc, cell)
            parent.removeChild(cell)
            return
        col += rep
    raise RuntimeError(f"column {target_col} not reached in row")


def add_notes(src: Path, dest: Path) -> None:
    doc = load(str(src))
    power = _table(doc, "Power plants")

    seen = set()
    for row in power.getElementsByType(TableRow):
        plant = _column_text(row, _PLANT_COL)
        if plant in _SLOTS and plant not in seen:
            _add_note(row, _NOTE_COL, _NOTE_TEXT)
            seen.add(plant)
    missing = set(_SLOTS) - seen
    if missing:
        raise RuntimeError(f"slots not found in master: {sorted(missing)}")

    changelog = _table(doc, "Change log")
    for date, desc in _CHANGELOG_ROWS:
        tr = TableRow()
        for value in (date, desc):
            tc = TableCell(valuetype="string")
            tc.addElement(P(text=value))
            tr.addElement(tc)
        changelog.addElement(tr)

    doc.save(str(dest))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, required=True, help="Source ODS (post-0497 snapshot).")
    parser.add_argument("--dest", type=Path, required=True, help="Destination ODS (with notes).")
    args = parser.parse_args(argv)
    add_notes(args.src, args.dest)
    print(f"Wrote {args.dest} (non-correspondence note on {len(_SLOTS)} NĐ Miền Bắc slots).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
