"""Drift guard for the reference-inventory-size constant (ticket 0413).

The "full inventory" count is used as a figure reference line (cost_quality,
exp2 arms split/comparison) and as the coverage-ratio denominator (exp2 mart
views, coverage_certainty, tabulate_macros). It must equal the number of plants
in the adopted reference release, never a hardcoded literal that silently drifts
when the release changes (v1 = 163 → v2 = 170 was exactly such a latent bug).

``reference_plant_count()`` derives it from the reference CSV; these tests pin
that derivation and assert every module-level mirror agrees with it.
"""

import re
from pathlib import Path

import pytest

from aedist.config import VN_THERMAL_PLANTS_RELEASE_CSV
from aedist.evaluate import load_plants_csv, reference_plant_count

_GEN = Path(__file__).resolve().parent.parent / "report" / "inputs" / "generated"


def _read_numrefplants(path: Path) -> int | None:
    """Parse \\newcommand{\\NumRefPlants}{N} from a generated macros file."""
    m = re.search(r"\\newcommand\{\\NumRefPlants\}\{(\d+)\}", path.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def test_reference_plant_count_matches_release():
    """The derived count equals the adopted reference CSV row count (v2.4 = 177 plants)."""
    n = len(load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV))
    assert reference_plant_count() == n
    assert n == 177, f"adopted reference has {n} plants, expected 177 (v2.4 = v2.3 − 3 E542 PL9.2 potential sites: Kim Sơn, Rạng Đông, Phú Thọ removed; Yên Hưng kept)"


def test_potential_sites_absent():
    """The three E542 PL9.2 potential sites are removed; Yên Hưng (PDP7 project) stays (ticket 0497)."""
    names = {p.name for p in load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV)}
    assert {"Kim Sơn", "Rạng Đông", "Phú Thọ"}.isdisjoint(names)
    assert "Yên Hưng" in names  # the PDP7 project stays
    assert reference_plant_count() == 177


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


@pytest.mark.adherence
def test_slides_and_manuscript_numrefplants_agree():
    """Single-source-of-truth guard (ticket 0609): macros_slides.tex \\NumRefPlants
    must equal macros_manuscript.tex \\NumRefPlants and both must equal
    reference_plant_count() (derived from the reference CSV).

    Catches the class of drift where a generated artifact is not regenerated
    after the reference data changes — exactly the 173→177 slip 0609 fixed.
    """
    n = reference_plant_count()

    slides_path = _GEN / "macros_slides.tex"
    manuscript_path = _GEN / "macros_manuscript.tex"

    if not slides_path.exists():
        pytest.skip(f"{slides_path} not generated")
    if not manuscript_path.exists():
        pytest.skip(f"{manuscript_path} not generated")

    slides_n = _read_numrefplants(slides_path)
    manuscript_n = _read_numrefplants(manuscript_path)

    assert slides_n is not None, r"\NumRefPlants missing from macros_slides.tex"
    assert manuscript_n is not None, r"\NumRefPlants missing from macros_manuscript.tex"
    assert slides_n == n, (
        f"macros_slides.tex \\NumRefPlants={slides_n} != reference_plant_count()={n} "
        f"— regenerate via: uv run python -m aedist.tabulate_macros --census "
        f"--output report/inputs/generated/macros_slides.tex"
    )
    assert manuscript_n == n, (
        f"macros_manuscript.tex \\NumRefPlants={manuscript_n} != reference_plant_count()={n} "
        f"— regenerate via: make -f experiments/render.mk report-tables"
    )
