"""Snapshot↔reference lockstep guard (ticket 0458).

The committed ``vietnam_thermal_plants_v2_classified.csv`` (177 plants, v2.4) is a
*generated* artifact: the reference pipeline (extract → aggregate → classify)
applied to the master snapshot pinned in ``config.VN_THERMAL_MASTER_SNAPSHOT_ODS``.
This guard re-runs that pipeline via ``verify_master_convergence.py`` and asserts
the regenerated CSV is byte-identical to the committed one — i.e. the released
reference has not drifted from its snapshot source (hand-edit, partial re-pin, or
a master re-import that skipped one of the un-replayed edit-sets would break it).

This is also the gate ticket 0458 hands to the master-machine operator: once the
three edit-sets are replayed and a fresh ``import.sh`` snapshot is produced,
running the verifier against it must pass before re-pinning ``config``.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "data" / "reference" / "verify_master_convergence.py"


def test_pinned_snapshot_regenerates_reference_byte_identically():
    """The pinned master snapshot regenerates the committed classified CSV exactly."""
    from aedist.config import VN_THERMAL_MASTER_SNAPSHOT_ODS

    snapshot = Path(VN_THERMAL_MASTER_SNAPSHOT_ODS)
    if not snapshot.exists():
        pytest.skip(
            f"pinned snapshot {snapshot} absent — "
            "reference-pipeline source not available in this checkout"
        )
    result = subprocess.run(
        [sys.executable, str(VERIFIER)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "pinned snapshot no longer regenerates the committed reference "
        f"byte-identically:\n{result.stdout}\n{result.stderr}"
    )
