"""Tests for the interactive Exp1 recognition matrix (ticket 0450).

Covers:
- ``collect_details=True`` path in ``load_exp1_recognition``: match_details and
  fp_candidates are populated correctly.
- ``_build_data`` produces well-formed JSON payload (all required keys present,
  vectors have correct length, match detail is present for TP cells, absent for
  FN cells).
- ``write_html`` generates a non-empty standalone HTML file containing the JS
  DATA blob.
- Level-absent degradation: ``ref_level`` is always "—" (0401/0402 not yet in
  Plant schema).
"""

import csv
import json
from pathlib import Path

import pytest

from aedist.exp1_recognition import (
    FPCandidate,
    MatchDetail,
    load_exp1_recognition,
)

# ---------------------------------------------------------------------------
# Helpers (duplicated from test_plot_exp1_matrix — isolated by design)
# ---------------------------------------------------------------------------

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
    """Single-model fixture: modelA, 2 runs with FP and partial recognition."""
    ref = tmp_path / "reference.csv"
    _write_reference(ref)

    out = tmp_path / "records"
    out.mkdir()
    # Run 1: Alpha + Bravo recognized; Ghost Plant is FP.
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
    # Run 2: Alpha only; same FP.
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


# ---------------------------------------------------------------------------
# Tests for collect_details=True path in load_exp1_recognition
# ---------------------------------------------------------------------------


def test_collect_details_populates_match_details(fixture_dir):
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)

    # match_details: one entry per (model, run, plant_id) = 2 runs x 4 plants = 8
    assert len(data.match_details) == 8
    assert all(isinstance(v, MatchDetail) for v in data.match_details.values())


def test_collect_details_tp_cell_has_system_name(fixture_dir):
    """A TP cell (recognized=True) should have system_name populated."""
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)

    # Find Alpha Power's plant_id (it's index 0 in the reference)
    alpha_id = next(
        c.plant_id for c in data.cells if c.plant_name == "Alpha Power" and c.run == 1
    )
    detail = data.match_details[("modelA", 1, alpha_id)]

    assert detail.system_name is not None
    assert "Alpha" in detail.system_name


def test_collect_details_fn_cell_has_no_system_name(fixture_dir):
    """A FN cell (recognized=False) should have system_name=None."""
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)

    # Charlie Power is missed by both runs
    charlie_id = next(
        c.plant_id for c in data.cells if c.plant_name == "Charlie Power" and c.run == 1
    )
    detail = data.match_details[("modelA", 1, charlie_id)]

    assert detail.system_name is None
    assert detail.match_type is None


def test_collect_details_ref_level_is_dash(fixture_dir):
    """ref_level must always be '—' until 0401/0402 lands in Plant schema."""
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)

    for detail in data.match_details.values():
        assert detail.ref_level == "—"


def test_collect_details_fp_candidates_populated(fixture_dir):
    """FP emissions should have a nearest-reference candidate."""
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)

    # Ghost Plant is a FP in both runs
    cand_run1 = data.fp_candidates.get(("modelA", 1, "Ghost Plant"))
    assert cand_run1 is not None
    assert isinstance(cand_run1, FPCandidate)
    assert cand_run1.fp_name == "Ghost Plant"
    assert cand_run1.best_ref_name is not None
    assert 0 <= cand_run1.best_similarity <= 100


def test_collect_details_false_does_not_populate(fixture_dir):
    """Default collect_details=False must leave match_details and fp_candidates empty."""
    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref)  # collect_details=False by default

    assert len(data.match_details) == 0
    assert len(data.fp_candidates) == 0


def test_existing_consumers_unaffected(fixture_dir):
    """cells and fp_presence are identical with and without collect_details."""
    glob, ref = fixture_dir
    data_plain = load_exp1_recognition(glob, ref)
    data_detail = load_exp1_recognition(glob, ref, collect_details=True)

    # Same cell count and recognition values
    assert len(data_plain.cells) == len(data_detail.cells)
    plain_by_key = {(c.model, c.run, c.plant_id): c.recognized for c in data_plain.cells}
    detail_by_key = {(c.model, c.run, c.plant_id): c.recognized for c in data_detail.cells}
    assert plain_by_key == detail_by_key

    # Same FP sets
    assert data_plain.fp_presence == data_detail.fp_presence


# ---------------------------------------------------------------------------
# Tests for _build_data payload shape
# ---------------------------------------------------------------------------


def test_build_data_keys(fixture_dir):
    """_build_data returns a dict with all required top-level keys."""
    from aedist.plot_exp1_matrix_interactive import _build_data

    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)
    payload = _build_data(data)

    required = {"runs", "ref_plants", "fp_names", "fp_run_counts", "status_bands",
                "match_details", "fp_candidates"}
    assert required <= set(payload.keys())


def test_build_data_vector_lengths(fixture_dir):
    """recognized and fp_present vectors match the column counts."""
    from aedist.plot_exp1_matrix_interactive import _build_data

    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)
    payload = _build_data(data)

    n_plants = len(payload["ref_plants"])
    n_fp = len(payload["fp_names"])
    for run_row in payload["runs"]:
        assert len(run_row["recognized"]) == n_plants
        assert len(run_row["fp_present"]) == n_fp


def test_build_data_fp_run_counts_match_names(fixture_dir):
    """fp_run_counts must be the same length as fp_names."""
    from aedist.plot_exp1_matrix_interactive import _build_data

    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)
    payload = _build_data(data)

    assert len(payload["fp_names"]) == len(payload["fp_run_counts"])


def test_build_data_tp_detail_present(fixture_dir):
    """match_details in the payload must exist for TP cells."""
    from aedist.plot_exp1_matrix_interactive import _build_data

    glob, ref = fixture_dir
    data = load_exp1_recognition(glob, ref, collect_details=True)
    payload = _build_data(data)

    # Find at least one TP cell and confirm its detail is in the payload
    found_tp_detail = False
    for run_idx, run_row in enumerate(payload["runs"]):
        for plant_j, recognized in enumerate(run_row["recognized"]):
            if recognized:
                run_key = str(run_idx)
                plant_key = str(plant_j)
                if run_key in payload["match_details"]:
                    if plant_key in payload["match_details"][run_key]:
                        found_tp_detail = True
                        break
        if found_tp_detail:
            break
    assert found_tp_detail, "No TP cell had a match_detail in the payload"


def test_build_data_empty_graceful():
    """_build_data with empty RecognitionData returns empty-but-valid dict."""
    from aedist.exp1_recognition import RecognitionData
    from aedist.plot_exp1_matrix_interactive import _build_data

    data = RecognitionData()
    payload = _build_data(data)

    assert payload["runs"] == []
    assert payload["ref_plants"] == []
    assert payload["fp_names"] == []


# ---------------------------------------------------------------------------
# Smoke test: write_html produces a non-empty standalone HTML file
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_write_html_produces_nonempty_file(fixture_dir, tmp_path):
    from aedist.plot_exp1_matrix_interactive import write_html

    glob, ref = fixture_dir
    out = tmp_path / "matrix.html"
    write_html(records_glob=glob, reference_path=ref, output=out)

    assert out.exists()
    assert out.stat().st_size > 0


@pytest.mark.slow
def test_write_html_contains_data_blob(fixture_dir, tmp_path):
    """The HTML must contain the embedded DATA JSON blob."""
    from aedist.plot_exp1_matrix_interactive import write_html

    glob, ref = fixture_dir
    out = tmp_path / "matrix.html"
    write_html(records_glob=glob, reference_path=ref, output=out)

    html = out.read_text(encoding="utf-8")
    assert "const DATA = " in html
    assert "ref_plants" in html
    assert "fp_names" in html


@pytest.mark.slow
def test_write_html_standalone_no_external_refs(fixture_dir, tmp_path):
    """The HTML must not reference external scripts or stylesheets."""
    from aedist.plot_exp1_matrix_interactive import write_html

    glob, ref = fixture_dir
    out = tmp_path / "matrix.html"
    write_html(records_glob=glob, reference_path=ref, output=out)

    html = out.read_text(encoding="utf-8")
    # No external CDN references
    assert "cdn.jsdelivr.net" not in html
    assert "cdnjs.cloudflare.com" not in html
    assert 'src="http' not in html
    assert "href=\"http" not in html
