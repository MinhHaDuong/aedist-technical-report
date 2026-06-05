"""Tests for tabulate_status_difficulty (ticket 0434).

The status difficulty table reports, per reference-list status group: how many
plants carry that status (and its share of the list), and the mean recognition
rate over all (run x plant) cells for plants of that status. It derives its data
independently from the shared exp1_recognition library (common cause with the
matrix figure 0373), never by consuming the figure's output.
"""

from aedist.exp1_recognition import RecognitionCell
from aedist.tabulate_status_difficulty import build_status_table, format_status_latex


def _cell(plant_id: int, status: str, run: int, recognized: bool) -> RecognitionCell:
    """One (run x reference-plant) recognition cell with the fields the table reads."""
    return RecognitionCell(
        model="m",
        run=run,
        size_class=None,
        plant_id=plant_id,
        plant_name=f"plant{plant_id}",
        status=status,
        capacity_mw=100.0,
        recognized=recognized,
    )


def _fixture_cells() -> list[RecognitionCell]:
    """Synthetic fixture: 2 statuses, 2 plants each, 2 runs.

    Operational: plant A hit 2/2 runs, plant B hit 1/2 -> 3/4 cells = 0.75.
    Proposed:    plants C, D both 0/2 -> 0/4 cells = 0.0.
    """
    cells: list[RecognitionCell] = []
    # plant A (id 0, operational): recognized in both runs
    cells.append(_cell(0, "operational", 1, True))
    cells.append(_cell(0, "operational", 2, True))
    # plant B (id 1, operational): recognized in run 1 only
    cells.append(_cell(1, "operational", 1, True))
    cells.append(_cell(1, "operational", 2, False))
    # plant C (id 2, proposed): never recognized
    cells.append(_cell(2, "proposed", 1, False))
    cells.append(_cell(2, "proposed", 2, False))
    # plant D (id 3, proposed): never recognized
    cells.append(_cell(3, "proposed", 1, False))
    cells.append(_cell(3, "proposed", 2, False))
    return cells


def test_status_difficulty_rates():
    """Exact (count, rate) pairs from the synthetic fixture (first test, ticket)."""
    rows = build_status_table(_fixture_cells())
    assert rows["operational"] == (2, 0.75)
    assert rows["proposed"] == (2, 0.0)


def test_status_order_follows_shared_library():
    """Statuses are ordered by the shared STATUS_ORDER, operational before proposed."""
    rows = build_status_table(_fixture_cells())
    assert list(rows.keys()) == ["operational", "proposed"]


def test_count_is_distinct_plants_not_cells():
    """n is the number of distinct reference plants, independent of run count."""
    rows = build_status_table(_fixture_cells())
    # 2 operational plants across 2 runs = 4 cells, but n must be 2.
    assert rows["operational"][0] == 2


def test_unknown_status_sorts_last():
    """A status outside STATUS_ORDER lands after the known groups."""
    cells = _fixture_cells()
    cells.append(_cell(4, "mothballed", 1, False))
    cells.append(_cell(4, "mothballed", 2, True))
    rows = build_status_table(cells)
    assert list(rows.keys())[-1] == "mothballed"
    assert rows["mothballed"] == (1, 0.5)


def test_latex_emits_share_and_total():
    """The LaTeX table includes per-status share and a total row summing to 100%."""
    rows = build_status_table(_fixture_cells())
    tex = format_status_latex(rows)
    assert "\\begin{table}" in tex
    assert "\\toprule" in tex and "\\bottomrule" in tex
    # 4 plants total; operational share = 2/4 = 50.0%.
    assert "50.0\\%" in tex
    # Total row reflects the 4-plant list.
    assert "Total" in tex or "Ensemble" in tex
