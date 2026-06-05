"""Path constants for the AEDIST pipeline.

Single source of truth for default file locations. Deliberately not a
config *system* (no TOML, env loading, or classes) — just the few path
constants that multiple modules would otherwise duplicate. YAGNI.
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent

# Vietnam thermal plants release (v2) — the ground-truth CSV that scoring
# entry points use by default. Adopted in ticket 0413: the pipe-regenerated v2
# (extract_ods → aggregate_units → add_classifications from the pinned master
# snapshot) replaces the hand-assembled v1. Override per invocation with the
# `--reference` CLI flag or the `reference_path` parameter.
VN_THERMAL_PLANTS_RELEASE_CSV = (
    _REPO_ROOT / "data" / "reference" / "vietnam_thermal_plants_v2_classified.csv"
)

# Vietnam thermal master snapshot (pipeline.ods) — the pinned ODS capture
# from the author's "Market report on Gas to Power" master spreadsheet.
# Datestamped immutable; extraction reads this to produce v2 releases.
VN_THERMAL_MASTER_SNAPSHOT_ODS = _REPO_ROOT / "data" / "reference" / "raw" / "pipeline-2026-06-05.ods"
