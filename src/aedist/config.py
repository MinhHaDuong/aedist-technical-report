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

# Vietnam thermal units release (v2) — unit-grain CSV produced by extract_ods.py.
# Carries three-column address (complex/plant/unit) and pre-assigned `level`.
# Primary source for derive_reference_level() (ticket 0401).
VN_THERMAL_UNITS_RELEASE_CSV = (
    _REPO_ROOT / "data" / "reference" / "vietnam_thermal_units_v2.csv"
)

# Vietnam thermal master snapshot (pipeline.ods) — the pinned ODS capture
# from the author's "Market report on Gas to Power" master spreadsheet.
# Datestamped immutable; extraction reads this to produce v2 releases.
#
# Reverse-sync COMPLETE (ticket 0458, 2026-06-09): the four formerly un-replayed
# local edit-sets are now in the master, so the pinned snapshot and the master are
# back in lockstep (a fresh import.sh would reproduce this snapshot). The edits:
#   1. the author's 8-cell standalone-extensions edit (4 rows, ticket 0445);
#   2. the 4-row Kiên Lương complex insertion (ticket 0472, add_kien_luong.py);
#   3. the 4-row potential-coal-sites addition (ticket 0395, add_plants_0395.py),
#      THREE of which were then removed as out-of-scope potential sites;
#   4. the 3-row potential-site removal (ticket 0497, remove_plants_0497.py):
#      Kim Sơn, Rạng Đông, Phú Thọ dropped (E542 PL9.2 candidate locations, not
#      projects), noted on NĐ Miền Bắc 1/2/3 with an explicit no-specific-
#      correspondence annotation (note_potential_sites_0458.py — NOT aliased);
#      Yên Hưng retained (PDP7 planned project). Net: 177 plants (180 − 3).
# The notes live in the non-extracted Note column, so the regenerated
# reference stays byte-identical at 177 (verify_master_convergence.py).
VN_THERMAL_MASTER_SNAPSHOT_ODS = (
    _REPO_ROOT / "data" / "reference" / "raw" / "pipeline+0458-2026-06-09.ods"
)
