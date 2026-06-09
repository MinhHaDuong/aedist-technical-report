"""Record the three E542 PL9.2 potential sites as aliases on the master (ticket 0458).

Master-side companion to the 0497 removal. Ticket 0497 dropped Kim Sơn, Rạng Đông
and Phú Thọ as *counted* rows (they are draft potential sites, not projects —
PROVENANCE.md "Traceability without counting"). The boundary rule still wants the
names retained as **aliases** against the existing PDP7 northern *"NĐ Miền Bắc"*
cancelled slots, so the PL9.2 cross-reference stays findable without re-counting a
candidate as a project.

This script writes each removed-site name into the empty ``Project alias`` column
(column 7, 0-indexed) of the corresponding ``NĐ Miền Bắc 1/2/3`` row and appends a
``Change log`` entry. The three slots are interchangeable cancelled placeholders
(Region ``Bắc Bộ``, no capacity), so the slot↔site assignment is by listed order:

    NĐ Miền Bắc 1 ← Kim Sơn      NĐ Miền Bắc 2 ← Rạng Đông      NĐ Miền Bắc 3 ← Phú Thọ

Aliases live in a column the reference pipeline does NOT extract (``extract_ods.py``
projects name/complex/plant/unit/province/asset_type/capacity/status/level only),
so the regenerated 177-plant reference is byte-identical — verified by
``verify_master_convergence.py``.

Usage:
    python data/reference/add_aliases_0458.py \\
        --src  data/reference/raw/pipeline+0497-2026-06-09.ods \\
        --dest data/reference/raw/pipeline+0458-2026-06-09.ods
"""
import argparse
from pathlib import Path

from odf.opendocument import load
from odf.table import Table, TableCell, TableRow
from odf.text import P

# Plant name (column 5) of each NĐ Miền Bắc slot -> the PL9.2 site recorded as its alias.
_ALIAS_BY_SLOT = {
    "NĐ Miền Bắc 1": "Kim Sơn",
    "NĐ Miền Bắc 2": "Rạng Đông",
    "NĐ Miền Bắc 3": "Phú Thọ",
}
_PROJECT_ALIAS_COL = 7  # 0-indexed column of "Project alias" in the Power plants sheet
_PLANT_COL = 5

_CHANGELOG_ROWS = [
    ("2026-06-09", "Reverse-sync (ticket 0458): replay extensions (0445), Kiên Lương (0472), Yên Hưng (0395)."),
    ("2026-06-09", "Record E542 PL9.2 potential sites Kim Sơn / Rạng Đông / Phú Thọ as aliases on NĐ Miền Bắc 1/2/3 (not counted rows)."),
]


def _cell_text(cell: TableCell) -> str:
    return "".join(str(p) for p in cell.getElementsByType(P))


def _table(doc, name: str) -> Table:
    for t in doc.spreadsheet.getElementsByType(Table):
        if t.getAttribute("name") == name:
            return t
    raise KeyError(f"sheet {name!r} not found")


def _set_alias(row: TableRow, target_col: int, text: str) -> None:
    """Write ``text`` into ``target_col`` of ``row``, splitting a repeated empty cell.

    Cells carry ``number-columns-repeated``; the Project alias column sits inside a
    repeated empty run. We replace that run with [empty-before][string-cell][empty-after],
    preserving the total column span.
    """
    col = 0
    for cell in list(row.getElementsByType(TableCell)):
        rep = int(cell.getAttribute("numbercolumnsrepeated") or 1)
        if col <= target_col < col + rep:
            if _cell_text(cell):
                raise ValueError(f"target column {target_col} is not empty: {_cell_text(cell)!r}")
            before = target_col - col
            after = (col + rep - 1) - target_col
            parent = cell.parentNode
            replacements = []
            if before > 0:
                bc = TableCell()
                if before > 1:
                    bc.setAttribute("numbercolumnsrepeated", str(before))
                replacements.append(bc)
            target = TableCell(valuetype="string")
            target.addElement(P(text=text))
            replacements.append(target)
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


def add_aliases(src: Path, dest: Path) -> None:
    doc = load(str(src))
    power = _table(doc, "Power plants")

    remaining = dict(_ALIAS_BY_SLOT)
    for row in power.getElementsByType(TableRow):
        cells = row.getElementsByType(TableCell)
        # Plant cell text (column 5) identifies the slot; walk repeats to read col 5.
        col, plant = 0, ""
        for c in cells:
            rep = int(c.getAttribute("numbercolumnsrepeated") or 1)
            if col <= _PLANT_COL < col + rep:
                plant = _cell_text(c)
                break
            col += rep
        if plant in remaining:
            _set_alias(row, _PROJECT_ALIAS_COL, remaining.pop(plant))
    if remaining:
        raise RuntimeError(f"slots not found in master: {sorted(remaining)}")

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
    parser.add_argument("--dest", type=Path, required=True, help="Destination ODS (with aliases).")
    args = parser.parse_args(argv)
    add_aliases(args.src, args.dest)
    print(f"Wrote {args.dest} (aliases on {len(_ALIAS_BY_SLOT)} NĐ Miền Bắc slots).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
