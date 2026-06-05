"""Tests for the Exp1 recognition matrix (ticket 0373).

Covers the shared derivation library (`aedist.exp1_recognition`) on a synthetic
fixture and a smoke test that the plot script writes a non-empty PDF. The
library function — not a file side-output — is the unit under test, per the
ticket's common-cause-consistency design.
"""

import csv
import json
from pathlib import Path

import pytest

from aedist.exp1_recognition import (
    RecognitionCell,
    load_exp1_recognition,
    top_false_positives,
)

# Synthetic reference: 4 plants across two status groups, distinct capacities so
# the LP name+capacity matcher resolves them unambiguously.
_REFERENCE_ROWS = [
    {"name": "Alpha Power", "status": "operating", "capacity_mwe": "1200"},
    {"name": "Bravo Power", "status": "operating", "capacity_mwe": "800"},
    {"name": "Charlie Power", "status": "planned", "capacity_mwe": "600"},
    {"name": "Delta Power", "status": "planned", "capacity_mwe": "400"},
]


def _write_reference(path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "status", "capacity_mwe"])
        w.writeheader()
        w.writerows(_REFERENCE_ROWS)


def _write_run(out_dir: Path, model: str, run: int, system_rows: list[dict]) -> None:
    """Write a {model}-run{N}.record.json + its result CSV into out_dir."""
    result_file = out_dir / f"{model}-run{run}.csv"
    with open(result_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "status", "capacity_mwe"])
        w.writeheader()
        w.writerows(system_rows)
    record = {
        "method_params": {"model": model, "extra": {"size_class": "small"}},
        "result_file": str(result_file),
    }
    (out_dir / f"{model}-run{run}.record.json").write_text(json.dumps(record))


@pytest.fixture
def fixture_dir(tmp_path: Path) -> tuple[str, Path]:
    """Build a synthetic records dir + reference; return (glob, reference_path)."""
    ref = tmp_path / "reference.csv"
    _write_reference(ref)

    out = tmp_path / "records"
    out.mkdir()
    # Run 1: recognizes Alpha + Bravo (half hit, half miss); 1 false positive.
    _write_run(
        out,
        "modelA",
        1,
        [
            {"name": "Alpha Power", "status": "operating", "capacity_mwe": "1200"},
            {"name": "Bravo Power", "status": "operating", "capacity_mwe": "800"},
            {"name": "Ghost Plant", "status": "operating", "capacity_mwe": "999"},
        ],
    )
    # Run 2: recognizes Alpha only; same false positive (so it counts twice).
    _write_run(
        out,
        "modelA",
        2,
        [
            {"name": "Alpha Power", "status": "operating", "capacity_mwe": "1200"},
            {"name": "Ghost Plant", "status": "operating", "capacity_mwe": "999"},
        ],
    )
    return (str(out / "*.record.json"), ref)


def test_recognition_cells_cover_every_run_and_plant(fixture_dir):
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref)
    # 2 runs x 4 reference plants = 8 cells.
    assert len(data.cells) == 8
    assert all(isinstance(c, RecognitionCell) for c in data.cells)
    runs = {(c.model, c.run) for c in data.cells}
    assert runs == {("modelA", 1), ("modelA", 2)}


def test_recognition_matches_input_hits(fixture_dir):
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref)
    recognized = {
        (c.model, c.run, c.plant_name): c.recognized for c in data.cells
    }
    # Run 1 recognized Alpha + Bravo, missed Charlie + Delta.
    assert recognized[("modelA", 1, "Alpha Power")] is True
    assert recognized[("modelA", 1, "Bravo Power")] is True
    assert recognized[("modelA", 1, "Charlie Power")] is False
    assert recognized[("modelA", 1, "Delta Power")] is False
    # Run 2 recognized Alpha only.
    assert recognized[("modelA", 2, "Alpha Power")] is True
    assert recognized[("modelA", 2, "Bravo Power")] is False


def test_cells_carry_status_and_capacity(fixture_dir):
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref)
    alpha = next(c for c in data.cells if c.plant_name == "Alpha Power")
    assert alpha.capacity_mw == 1200.0
    assert alpha.size_class == "small"


def test_same_name_plants_get_distinct_columns(tmp_path):
    """Two reference plants sharing a name but differing in capacity must keep
    distinct plant_id columns and distinct recognition (the 161-vs-163 bug)."""
    ref = tmp_path / "reference.csv"
    with open(ref, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "status", "capacity_mwe"])
        w.writeheader()
        w.writerows(
            [
                {"name": "Twin Power", "status": "operating", "capacity_mwe": "300"},
                {"name": "Twin Power", "status": "proposed", "capacity_mwe": "150"},
            ]
        )
    out = tmp_path / "records"
    out.mkdir()
    # Run recognizes the 300 MW Twin Power only.
    _write_run(
        out,
        "modelA",
        1,
        [{"name": "Twin Power", "status": "operating", "capacity_mwe": "300"}],
    )
    data = load_exp1_recognition(str(out / "*.record.json"), ref)
    twins = [c for c in data.cells if c.plant_name == "Twin Power"]
    assert len(twins) == 2  # two distinct columns, not merged into one
    assert {c.plant_id for c in twins} == {0, 1}
    by_cap = {c.capacity_mw: c.recognized for c in twins}
    assert by_cap[300.0] is True
    assert by_cap[150.0] is False


def test_false_positive_presence_and_ranking(fixture_dir):
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref)
    # Both runs emitted the same FP -> count 2, top of the ranking.
    assert "Ghost Plant" in data.fp_presence[("modelA", 1)]
    assert "Ghost Plant" in data.fp_presence[("modelA", 2)]
    top = top_false_positives(data.fp_presence, top_n=40)
    assert top[0] == ("Ghost Plant", 2)


def test_top_fp_seed_is_stable(fixture_dir):
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref)
    a = top_false_positives(data.fp_presence, top_n=40, seed=42)
    b = top_false_positives(data.fp_presence, top_n=40, seed=42)
    assert a == b


def test_top_fp_invariant_to_input_set_order():
    """Tied counts must rank identically regardless of set-iteration order.

    Set iteration / dict insertion order can vary across processes under hash
    randomization. Sorting by name before the seeded shuffle removes that
    dependence, so the committed figure stays byte-stable across rebuilds.
    """
    # Four FPs all at count 1 (all tied); two runs, different emission orders.
    fp_a = {("m", 1): {"Zeta", "Alpha"}, ("m", 2): {"Mu", "Beta"}}
    fp_b = {("m", 2): {"Beta", "Mu"}, ("m", 1): {"Alpha", "Zeta"}}
    assert top_false_positives(fp_a, top_n=40) == top_false_positives(fp_b, top_n=40)


@pytest.mark.slow
def test_plot_writes_nonempty_pdf(fixture_dir, tmp_path):
    from aedist.plot_exp1_matrix import write_pdf

    glob, ref = fixture_dir
    out = tmp_path / "fig.pdf"
    write_pdf(records_glob=glob, reference_path=ref, output=out)
    assert out.exists()
    assert out.stat().st_size > 0
