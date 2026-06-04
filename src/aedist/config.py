"""Path constants for the AEDIST pipeline.

Single source of truth for default file locations. Deliberately not a
config *system* (no TOML, env loading, or classes) — just the few path
constants that multiple modules would otherwise duplicate. YAGNI.
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent

# Default reference list of plants (the "expert" / ground-truth CSV) that
# comparison entry points score model output against. Override per invocation
# with the `--reference` CLI flag or the `reference_path` parameter.
DEFAULT_REFERENCE = _REPO_ROOT / "data" / "reference" / "vietnam_thermal_v1.csv"
