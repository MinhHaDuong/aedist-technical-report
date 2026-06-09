"""Remove the three E542 PL9.2 potential sites from the pipeline ODS (ticket 0497).

Inverse of ``add_plants_0395.py`` for the boundary correction recorded in
``data/reference/PROVENANCE.md`` ("Scope boundary: a project is not a potential
site"). Ticket 0395 added four rows via XML surgery; three of them — Kim Sơn,
Rạng Đông, Phú Thọ — are *potential coal sites* from a draft siting study
(Study E542 Table PL9.2, "tổng hợp các vị trí tiềm năng"), not projects, and
violate the scope boundary. Yên Hưng (PDP7 Annex 1+2, a specific planned
project) is **retained**. Reference goes 180 → 177.

Replayability: this script does NOT modify ``add_plants_0395.py``; it operates on
the post-0395 snapshot (``raw/pipeline+0395-2026-06-09.ods``, passed explicitly
via ``--src``) and produces a NEW dated snapshot
(``raw/pipeline+0497-2026-06-09.ods``), which this ticket repins as
``config.VN_THERMAL_MASTER_SNAPSHOT_ODS``. The 0395 → 0497 edit chain stays
intact and replayable.

Byte-exact removal: the three rows to drop were inserted by ``add_plants_0395``
using ``_build_row`` over ``_ROWS``. We import those and regenerate the exact
row XML strings, then ``str.replace(row, "", 1)`` each. Yên Hưng sits *between*
Rạng Đông and Phú Thọ in ``_ROWS``, so the three are not a contiguous block;
per-row string replacement excises each independently and leaves Yên Hưng in
place. The match is guaranteed byte-identical because the same builder produced
the bytes now in content.xml.

Usage:
    python data/reference/remove_plants_0497.py \\
        --src  data/reference/raw/pipeline+0395-2026-06-09.ods \\
        --dest data/reference/raw/pipeline+0497-2026-06-09.ods
"""
import argparse
import io
import shutil
import zipfile
from pathlib import Path

from add_plants_0395 import _ROWS, _build_row

# Plant names (column 5) of the rows to REMOVE. Yên Hưng is deliberately absent.
_REMOVE_NAMES = {"Kim Sơn", "Rạng Đông", "Phú Thọ"}


def _rows_to_remove() -> list[str]:
    """Regenerate the exact ODS row XML for each potential site to drop."""
    out = []
    for cells in _ROWS:
        name = cells.get(5, (None, None))[1]
        if name in _REMOVE_NAMES:
            out.append(_build_row(cells))
    return out


def unpatch_ods(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    with zipfile.ZipFile(src, "r") as zin:
        xml = zin.read("content.xml").decode("utf-8")

    to_remove = _rows_to_remove()
    if len(to_remove) != len(_REMOVE_NAMES):
        raise SystemExit(
            f"Expected {len(_REMOVE_NAMES)} rows to remove, found {len(to_remove)}"
        )

    patched = xml
    for row in to_remove:
        if row not in patched:
            raise SystemExit(
                "Row XML not found in content.xml — the snapshot is not the "
                "post-0395 ODS, or add_plants_0395 row format drifted."
            )
        patched = patched.replace(row, "", 1)

    # Rewrite the zip, replacing only content.xml (byte-stable elsewhere).
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

    unpatch_ods(args.src, args.dest)
    print(
        "Done. Verify with: uv run python data/reference/extract_ods.py --input",
        args.dest,
    )


if __name__ == "__main__":
    main()
