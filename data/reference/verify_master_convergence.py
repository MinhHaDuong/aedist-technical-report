"""Verify a candidate master snapshot converges to the post-0497 reference (ticket 0458).

The master ``pipeline.ods`` lives on the author's other machine; the analysis
repo pins a re-imported snapshot in ``config.VN_THERMAL_MASTER_SNAPSHOT_ODS``.
Three edit-sets applied on the analysis side are NOT yet replayed on the master
(0445 standalone-extensions, 0472 Kiên Lương, 0395-with-boundary: Yên Hưng only —
Kim Sơn / Rạng Đông / Phú Thọ recorded as aliases, not rows). Until they are,
a fresh ``import.sh`` snapshot regenerates a DIFFERENT reference and re-pinning
``config`` to it silently reverts the adoption (177 → 170).

This script is the convergence gate for that handover. It runs the reference
pipeline (``extract_ods`` → ``aggregate_units`` → ``add_classifications``) on a
candidate snapshot into a temp dir and byte-compares the regenerated classified
CSV against the committed post-0497 artifact. On mismatch it prints a
plant-name-level diff (rows only the candidate has, rows only the reference has)
to localise which edit-set is missing or wrong, then exits non-zero.

Usage:
    # Self-test: the currently pinned snapshot must regenerate the committed CSV.
    python data/reference/verify_master_convergence.py

    # Gate a fresh master re-import BEFORE re-pinning config to it:
    python data/reference/verify_master_convergence.py \\
        --snapshot data/reference/raw/pipeline+0458-YYYY-MM-DD.ods

Exit status: 0 = byte-identical convergence (safe to re-pin); 1 = divergence.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent

# Committed target the master must converge to (post-0497, 177 plants).
_DEFAULT_REFERENCE = _HERE / "vietnam_thermal_plants_v2_classified.csv"


def _pinned_snapshot() -> Path:
    """The snapshot currently pinned in config (used when --snapshot is omitted)."""
    from aedist.config import VN_THERMAL_MASTER_SNAPSHOT_ODS

    return Path(VN_THERMAL_MASTER_SNAPSHOT_ODS)


def regenerate_classified(snapshot: Path, workdir: Path) -> Path:
    """Run extract → aggregate → classify on ``snapshot``; return the classified CSV.

    Each stage is invoked as its own subprocess (same interpreter, so it inherits
    the project venv), mirroring the ``reference-pipeline`` recipe in acquire.mk.
    Any stage's hard-fail guard (dirty ODS, duplicate plant key, …) surfaces here.
    """
    units = workdir / "units.csv"
    plants = workdir / "plants.csv"
    classified = workdir / "classified.csv"

    stages = [
        (_HERE / "extract_ods.py", ["--input", str(snapshot), "--output", str(units)]),
        (_HERE / "aggregate_units.py", ["--input", str(units), "--output", str(plants)]),
        (
            _HERE / "add_classifications.py",
            ["--input", str(plants), "--output", str(classified), "--fuel-col", "fuel"],
        ),
    ]
    for script, args in stages:
        subprocess.run([sys.executable, str(script), *args], check=True)
    return classified


def _plant_names(csv_path: Path) -> set[str]:
    """First column ('name') of a classified CSV, excluding the header."""
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    return {line.split(",", 1)[0] for line in lines[1:] if line}


def verify(snapshot: Path, reference: Path) -> bool:
    """True iff ``snapshot`` regenerates a byte-identical copy of ``reference``."""
    with tempfile.TemporaryDirectory() as tmp:
        regenerated = regenerate_classified(snapshot, Path(tmp))
        regenerated_bytes = regenerated.read_bytes()
        reference_bytes = reference.read_bytes()

        if regenerated_bytes == reference_bytes:
            n = len(_plant_names(reference))
            print(f"OK: {snapshot.name} regenerates {reference.name} byte-identically ({n} plants).")
            return True

        got = _plant_names(regenerated)
        want = _plant_names(reference)
        only_candidate = sorted(got - want)
        only_reference = sorted(want - got)
        print(f"DIVERGENCE: {snapshot.name} does not regenerate {reference.name}.")
        print(f"  candidate plants: {len(got)}    reference plants: {len(want)}")
        if only_candidate:
            print("  only in candidate (extra rows — un-applied removal / spurious add):")
            for name in only_candidate:
                print(f"    + {name}")
        if only_reference:
            print("  only in reference (missing rows — un-replayed edit-set):")
            for name in only_reference:
                print(f"    - {name}")
        if not only_candidate and not only_reference:
            print("  plant SETS match but bytes differ — column/ordering/whitespace drift.")
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="Candidate master ODS snapshot (default: config.VN_THERMAL_MASTER_SNAPSHOT_ODS).",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=_DEFAULT_REFERENCE,
        help="Committed classified CSV the snapshot must converge to.",
    )
    args = parser.parse_args(argv)
    snapshot = args.snapshot if args.snapshot is not None else _pinned_snapshot()
    return 0 if verify(snapshot, args.reference) else 1


if __name__ == "__main__":
    raise SystemExit(main())
