"""Tests for tabulate_status_difficulty (ticket 0434).

The status difficulty table reports, per reference-list status group: how many
plants carry that status (and its share of the list), and the mean recognition
rate over all (run x plant) cells for plants of that status. It derives its data
independently from the shared exp1_recognition library (common cause with the
matrix figure 0373), never by consuming the figure's output.
"""

from pathlib import Path

import pytest

from aedist.exp1_recognition import STATUS_LABELS_EN, RecognitionCell
from aedist.tabulate_status_difficulty import (
    build_status_table,
    format_status_latex,
    format_status_latex_en,
)


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
    """Statuses are ordered by the shared STATUS_ORDER — lifecycle order
    (author-ratified 2026-06-06, ticket 0446): proposed before operational."""
    rows = build_status_table(_fixture_cells())
    assert list(rows.keys()) == ["proposed", "operational"]


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


def _fixture_cells_exp2() -> list[RecognitionCell]:
    """Synthetic Exp2 arm-3 fixture: same plants, higher detection (docs help).

    Operational: A 2/2, B 2/2 -> 4/4 = 1.0. Proposed: C 1/2, D 0/2 -> 1/4 = 0.25.
    """
    cells: list[RecognitionCell] = []
    cells.append(_cell(0, "operational", 1, True))
    cells.append(_cell(0, "operational", 2, True))
    cells.append(_cell(1, "operational", 1, True))
    cells.append(_cell(1, "operational", 2, True))
    cells.append(_cell(2, "proposed", 1, True))
    cells.append(_cell(2, "proposed", 2, False))
    cells.append(_cell(3, "proposed", 1, False))
    cells.append(_cell(3, "proposed", 2, False))
    return cells


def test_latex_emits_share_and_total():
    """The LaTeX table includes per-status share and a total row summing to 100%."""
    rows = build_status_table(_fixture_cells())
    rows2 = build_status_table(_fixture_cells_exp2())
    tex = format_status_latex(rows, rows2)
    assert "\\begin{table}" in tex
    assert "\\toprule" in tex and "\\bottomrule" in tex
    # 4 plants total; operational share = 2/4 = 50.0%.
    assert "50.0\\%" in tex
    # Total row reflects the 4-plant list.
    assert "Total" in tex or "Ensemble" in tex
    # Five-column shape: two detection columns.
    assert "lrrrr" in tex


def test_latex_en_body_matches_fr_numbers():
    """The English manuscript body carries the same numbers as the French table."""
    rows = build_status_table(_fixture_cells())
    rows2 = build_status_table(_fixture_cells_exp2())
    tex_en = format_status_latex_en(rows, rows2)
    assert "\\begin{tabular}" in tex_en and "\\begin{table}" not in tex_en, (
        "EN body must be tabular-only; caption/float stay in main.tex (0486 pattern)"
    )
    # Two detection columns: Exp1 then Exp2 arm-3.
    assert "Proposed & 2 & 50.0\\% & 0.0\\% & 25.0\\% \\\\" in tex_en
    assert "Operational & 2 & 50.0\\% & 75.0\\% & 100.0\\% \\\\" in tex_en
    assert "\\textbf{All} & \\textbf{4} & \\textbf{100.0\\%}" in tex_en


def test_exp2_column_renders_dash_when_status_absent():
    """A status present in Exp1 but absent from the Exp2 arm-3 view renders —."""
    rows = build_status_table(_fixture_cells())
    rows2 = {"operational": (2, 1.0)}  # proposed missing from Exp2
    tex_en = format_status_latex_en(rows, rows2)
    assert "Proposed & 2 & 50.0\\% & 0.0\\% & — \\\\" in tex_en


# --- Ticket 0547: manuscript adherence — generated include, row-grain guard ---

REPO_ROOT = Path(__file__).resolve().parent.parent
EN_BODY = REPO_ROOT / "report" / "inputs" / "generated" / "tab_status_difficulty_en.tex"
FR_TABLE = REPO_ROOT / "report" / "inputs" / "generated" / "tab_status_difficulty.tex"
MACROS = REPO_ROOT / "report" / "inputs" / "generated" / "macros_status_difficulty.tex"
MAIN_TEX = REPO_ROOT / "slides" / "manuscript" / "main.tex"

_EN_TO_FR = {
    "Proposed": "En projet",
    "Planned": "Planifiée",
    "Under construction": "En construction",
    "Operational": "Opérationnelle",
    "Retired": "Retirée",
    "Cancelled": "Annulée",
}


def _en_rows() -> list[list[str]]:
    if not EN_BODY.exists():
        pytest.skip(f"{EN_BODY} not generated — run: make -f experiments/render.mk report-tables")
    rows = []
    for line in EN_BODY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.endswith("\\\\") and "&" in line:
            rows.append([c.strip() for c in line[:-2].split("&")])
    return rows


@pytest.mark.adherence
def test_status_table_is_generated_include():
    """main.tex \\inputs the generated EN status table, not a hand-typed body."""
    raw = MAIN_TEX.read_text(encoding="utf-8")
    assert "\\input{../../report/inputs/generated/tab_status_difficulty_en.tex}" in raw, (
        "main.tex must \\input the generated status-difficulty table"
    )


@pytest.mark.adherence
def test_status_en_body_rederives_from_fr_artifact_and_macros():
    """Row-grain guard: every EN row re-derives from the FR artifact's numbers,
    and the Proposed/All rows match the committed macros (same generator pass)."""
    rows = [r for r in _en_rows() if r[0] not in ("Status",)]
    fr = FR_TABLE.read_text(encoding="utf-8")
    macros = MACROS.read_text(encoding="utf-8")

    data_rows = [r for r in rows if not r[0].startswith("\\textbf")]
    assert len(data_rows) == len(_EN_TO_FR), "unexpected EN row count"
    for label, n, share, rate1, rate2 in data_rows:
        fr_row = f"{_EN_TO_FR[label]} & {n} & {share} & {rate1} & {rate2} \\\\"
        assert fr_row in fr, f"EN row {label!r} not re-derivable from {FR_TABLE.name}"

    proposed = next(r for r in data_rows if r[0] == "Proposed")
    proposed_share = proposed[2].removesuffix("\\%")
    assert f"\\newcommand{{\\StatusProposedCount}}{{{proposed[1]}}}" in macros
    assert f"\\newcommand{{\\StatusProposedSharePct}}{{{proposed_share}}}" in macros

    all_row = next(r for r in rows if r[0] == "\\textbf{All}")
    overall = all_row[3].replace("\\textbf{", "").replace("}", "").removesuffix("\\%")
    assert f"\\newcommand{{\\StatusOverallRatePct}}{{{overall}}}" in macros


# --- Ticket 0597: finding 16 — EN rate-column header matches the new framing ---

# The §7.1 prose + caption reword the metric as "the average probability of a
# plant being found by an Experiment 1 model run" (tbl:status-difficulty). The
# generated EN column header must follow the same framing, not the legacy
# "Recognition rate" label. Re-derived independently from the committed artifact.


@pytest.mark.adherence
def test_status_en_header_matches_detection_framing():
    """Finding 16: the EN rate columns read as detection probabilities, not the
    legacy 'Recognition rate' label that contradicts the caption's framing.

    Ticket 0628: two detection columns now — Experiment 1 (all models) and
    Experiment 2 arm 3 (single-shot with documents, 1D)."""
    header = next(r for r in _en_rows() if r and r[0] == "Status")
    assert header[-2] == "Avg. detection prob. (Exp 1)", (
        "EN Exp-1 detection column must be labelled '(Exp 1)' (ticket 0628)"
    )
    assert header[-1] == "Avg. detection prob. (Exp 2, 1D)", (
        "EN Exp-2 arm-3 detection column must be labelled '(Exp 2, 1D)' (ticket 0628)"
    )
    raw = EN_BODY.read_text(encoding="utf-8")
    assert "Recognition rate" not in raw, (
        "legacy 'Recognition rate' header must not survive in the EN artifact"
    )


# --- Ticket 0628: arm-3 detection column re-derived from the mart artifact ---

MART_JSONL = REPO_ROOT / "experiments" / "derived" / "exp2_mart.jsonl"
EXPERT_REF = REPO_ROOT / "data" / "reference" / "vietnam_thermal_plants_v2_classified.csv"


@pytest.mark.slow
def test_exp2_arm3_column_rederives_from_mart():
    """The committed EN table's Exp-2 column re-derives independently from the
    arm-3 mart records (derive-from-artifact, ticket 0628). Marked slow: it
    reconciles every arm-3 run against the reference."""
    from aedist.exp2_recognition import load_exp2_recognition

    if not (MART_JSONL.exists() and EXPERT_REF.exists() and EN_BODY.exists()):
        pytest.skip("mart / reference / generated table not available")

    data = load_exp2_recognition(MART_JSONL, EXPERT_REF, REPO_ROOT, arm="arm3")
    rows2 = build_status_table(data.cells)
    expected = {
        STATUS_LABELS_EN.get(s, s.capitalize()): f"{rate * 100:.1f}\\%"
        for s, (_n, rate) in rows2.items()
    }

    data_rows = [r for r in _en_rows() if r and r[0] not in ("Status",) and not r[0].startswith("\\textbf")]
    assert data_rows, "no EN data rows parsed"
    for row in data_rows:
        label, arm3_cell = row[0], row[-1]
        if label in expected:
            assert arm3_cell == expected[label], (
                f"EN arm-3 cell for {label!r} ({arm3_cell}) does not re-derive "
                f"from the mart ({expected[label]})"
            )
        else:
            assert arm3_cell == "—", f"{label!r} absent from arm-3 view must render —"


# --- Ticket 0628: §7.1 register-shape softening — negative guard ---


@pytest.mark.adherence
def test_section_71_softens_cannot_know():
    """§7.1 must not assert parametric memory *cannot* know the long tail — the
    softened framing is 'hard to know' (ticket 0628 author decision)."""
    raw = MAIN_TEX.read_text(encoding="utf-8")
    assert "parametric memory cannot know" not in raw, (
        "§7.1 must soften 'parametric memory cannot know them' to 'hard to know'"
    )
    assert "memory cannot know" not in raw, (
        "absolute 'memory cannot know' phrasing must not survive in §7.1"
    )
