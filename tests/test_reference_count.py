"""Drift guard for the reference-inventory-size constant (ticket 0413).

The "full inventory" count is used as a figure reference line (cost_quality,
exp2 arms split/comparison) and as the coverage-ratio denominator (exp2 mart
views, coverage_certainty, tabulate_macros). It must equal the number of plants
in the adopted reference release, never a hardcoded literal that silently drifts
when the release changes (v1 = 163 → v2 = 170 was exactly such a latent bug).

``reference_plant_count()`` derives it from the reference CSV; these tests pin
that derivation and assert every module-level mirror agrees with it.
"""

from aedist.config import VN_THERMAL_PLANTS_RELEASE_CSV
from aedist.evaluate import load_plants_csv, reference_plant_count


def test_reference_plant_count_matches_release():
    """The derived count equals the adopted reference CSV row count (v2 = 170)."""
    n = len(load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV))
    assert reference_plant_count() == n
    assert n == 170, f"adopted reference has {n} plants, expected 170 (v2)"


def test_all_module_constants_track_the_release():
    """Every module-level inventory-size constant equals reference_plant_count()."""
    from aedist import (
        build_exp2_mart_views,
        exp1_cost_quality,
        plot_exp2_arms_comparison,
        plot_exp2_arms_split,
        plot_exp2_coverage_certainty,
    )

    n = reference_plant_count()
    assert exp1_cost_quality.N_REFERENCE_PLANTS == n
    assert plot_exp2_arms_split.N_REFERENCE_PLANTS == n
    assert plot_exp2_arms_comparison.N_REFERENCE_PLANTS == n
    assert plot_exp2_coverage_certainty._N_REFERENCE_PLANTS == n
    assert build_exp2_mart_views._N_REFERENCE_PLANTS == n
