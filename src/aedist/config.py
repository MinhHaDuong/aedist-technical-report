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

# GEM (Global Energy Monitor) thermal reference CSV — used by reconciliation
# and source-URL audit scripts.  Single source of truth; do not hardcode the
# filename outside this module (ticket 0428 ratchet).
GEM_THERMAL_REFERENCE_CSV = (
    _REPO_ROOT / "data" / "reference" / "gem_thermal.csv"
)

# Vietnam thermal master snapshot (pipeline.ods) — the pinned ODS capture
# from the author's "Market report on Gas to Power" master spreadsheet.
# Datestamped immutable; extraction reads this to produce v2 releases.
#
# 0445/0472/0395 EXCEPTION: the pinned snapshot carries three un-replayed local
# edits that are not yet in the master (which lives on another machine):
#   1. the author's 8-cell standalone-extensions edit (4 rows, ticket 0445;
#      replay pending, ticket 0458);
#   2. the 4-row Kiên Lương complex insertion (ticket 0472, add_kien_luong.py);
#   3. the 4-row potential-coal-sites addition (ticket 0395, add_plants_0395.py).
# Do NOT re-pin to a fresh master import until ALL THREE edits are replayed,
# or the adoption silently reverts 180 → 170 (PROVENANCE.md § v2.3).
VN_THERMAL_MASTER_SNAPSHOT_ODS = (
    _REPO_ROOT / "data" / "reference" / "raw" / "pipeline+0395-2026-06-09.ods"
)
