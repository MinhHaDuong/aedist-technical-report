"""Adherence guard: macros_slides.tex \\NumRefPlants agrees with the reference data.

Ticket 0609: macros_slides.tex carried a stale 173-plant count while
macros.tex and macros_manuscript.tex already reflected the current 177-plant
reference. This guard re-derives the count from the reference CSV (single
source of truth) and asserts slides == manuscript == reference data.
"""

import re
from pathlib import Path

import pytest

from aedist.evaluate import reference_plant_count

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN = REPO_ROOT / "report" / "inputs" / "generated"
MACROS_SLIDES = GEN / "macros_slides.tex"
MACROS_MANUSCRIPT = GEN / "macros_manuscript.tex"


def _extract_numrefplants(tex_file: Path) -> int:
    """Parse \\newcommand{\\NumRefPlants}{N} from a generated macros file."""
    text = tex_file.read_text(encoding="utf-8")
    m = re.search(r"\\newcommand\{\\NumRefPlants\}\{(\d+)\}", text)
    assert m is not None, f"\\NumRefPlants not found in {tex_file}"
    return int(m.group(1))


def test_slides_numrefplants_matches_reference_data():
    """macros_slides.tex \\NumRefPlants equals reference_plant_count() (derived from CSV)."""
    expected = reference_plant_count()
    actual = _extract_numrefplants(MACROS_SLIDES)
    assert actual == expected, (
        f"macros_slides.tex \\NumRefPlants={actual} "
        f"but reference CSV has {expected} plants — "
        "regenerate via: uv run python -m aedist.tabulate_macros --census "
        "--output report/inputs/generated/macros_slides.tex"
    )


def test_slides_numrefplants_matches_manuscript():
    """macros_slides.tex and macros_manuscript.tex carry the same \\NumRefPlants."""
    slides_n = _extract_numrefplants(MACROS_SLIDES)
    manuscript_n = _extract_numrefplants(MACROS_MANUSCRIPT)
    assert slides_n == manuscript_n, (
        f"slides \\NumRefPlants={slides_n} "
        f"≠ manuscript \\NumRefPlants={manuscript_n} — "
        "single source of truth violated; regenerate the stale file"
    )
