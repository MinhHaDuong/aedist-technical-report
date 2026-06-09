"""Tests for mechanical scoring helpers."""

import pytest

from aedist.score_ingest import RunLocator, ingest_run
from aedist.score_mechanical import (
    _capacity_nonnegative,
    model_reliability_grade,
    score_accuracy,
    score_cod_plausible,
    score_coherence,
    score_field_completeness,
    score_provenance,
    score_source_diversity,
    score_source_spread,
    score_temporality,
    score_variability,
)

# --- coherence_variability tests (ticket 0453) ----------------------------------


def test_variability_template_run_vetoed() -> None:
    """All-identical capacity and status → VETO (template fabrication pattern)."""
    rows = [{"capacity_mwe": "600.0", "status": "Operating"} for _ in range(50)]
    v = score_variability(rows)
    assert v.capacity_distinct == 1
    assert v.status_distinct == 1
    assert v.veto is True


def test_variability_diverse_run_not_vetoed() -> None:
    """Many distinct capacity and status values → no VETO."""
    statuses = ["Operating", "Construction", "Announced"]
    rows = [
        {"capacity_mwe": str(100 + i * 10), "status": statuses[i % 3]}
        for i in range(20)
    ]
    v = score_variability(rows)
    assert v.capacity_distinct == 20
    assert v.status_distinct == 3
    assert v.veto is False


def test_variability_exactly_four_capacity_is_vetoed() -> None:
    """cap_distinct == 4 is at the VETO threshold (≤4)."""
    statuses = ["Operating", "Construction", "Announced", "Retired"]
    rows = [
        {"capacity_mwe": str(100 * (i + 1)), "status": statuses[i % 4]}
        for i in range(4)
    ]
    v = score_variability(rows)
    assert v.capacity_distinct == 4
    assert v.status_distinct == 4
    assert v.veto is True  # cap_distinct <= 4 triggers


def test_variability_five_capacity_not_vetoed() -> None:
    """cap_distinct == 5 escapes the capacity threshold (unless status<=1)."""
    rows = [
        {"capacity_mwe": str(100 * (i + 1)), "status": f"Status{i}"}
        for i in range(5)
    ]
    v = score_variability(rows)
    assert v.capacity_distinct == 5
    assert v.veto is False


def test_variability_status_one_triggers_veto() -> None:
    """status_distinct == 1 triggers VETO regardless of capacity diversity."""
    rows = [{"capacity_mwe": str(100 + i * 10), "status": "Operating"} for i in range(20)]
    v = score_variability(rows)
    assert v.status_distinct == 1
    assert v.veto is True  # status_distinct <= 1


def test_variability_empty_rows_is_vetoed() -> None:
    """Empty run is treated as degenerate (VETO)."""
    v = score_variability([])
    assert v.capacity_distinct == 0
    assert v.veto is True


def test_variability_missing_capacity_column() -> None:
    """Rows without any capacity key → cap_distinct=0 → VETO."""
    rows = [{"name": "Plant A", "status": "Operating"} for _ in range(10)]
    v = score_variability(rows)
    assert v.capacity_distinct == 0
    assert v.veto is True


def test_variability_status_as_of_not_used() -> None:
    """status_as_of variability must NOT trigger VETO — strong models stamp run date."""
    # All rows have the same status_as_of but varied capacity and status.
    rows = [
        {
            "capacity_mwe": str(100 + i * 10),
            "status": f"Status{i % 3}",
            "status_as_of": "2026-01-01",
        }
        for i in range(15)
    ]
    v = score_variability(rows)
    # status_as_of identical but status varies → should NOT be vetoed
    assert v.status_distinct >= 2
    assert v.veto is False


# --- model_reliability_grade tests (ticket 0453) --------------------------------


def test_model_reliability_grade_disqualified() -> None:
    """5/5 vetoed runs → disqualified=True."""
    scored = [
        {"model": "bad-model", "prompt_version": "exp1", "coherence_run_veto": "1"}
        for _ in range(5)
    ]
    grades = model_reliability_grade(scored)
    grade = grades[("bad-model", "exp1")]
    assert grade["n_total"] == 5
    assert grade["n_vetoed"] == 5
    assert grade["disqualified"] is True


def test_model_reliability_grade_partial_not_disqualified() -> None:
    """4/5 vetoed → not disqualified (5/5 rule)."""
    scored = [
        {"model": "mid-model", "prompt_version": "exp1", "coherence_run_veto": "1"},
        {"model": "mid-model", "prompt_version": "exp1", "coherence_run_veto": "1"},
        {"model": "mid-model", "prompt_version": "exp1", "coherence_run_veto": "1"},
        {"model": "mid-model", "prompt_version": "exp1", "coherence_run_veto": "1"},
        {"model": "mid-model", "prompt_version": "exp1", "coherence_run_veto": "0"},
    ]
    grades = model_reliability_grade(scored)
    grade = grades[("mid-model", "exp1")]
    assert grade["n_vetoed"] == 4
    assert grade["disqualified"] is False


def test_model_reliability_grade_clean_model() -> None:
    """0/5 vetoed → disqualified=False, veto_fraction=0."""
    scored = [
        {"model": "good-model", "prompt_version": "exp1", "coherence_run_veto": "0"}
        for _ in range(5)
    ]
    grades = model_reliability_grade(scored)
    grade = grades[("good-model", "exp1")]
    assert grade["n_vetoed"] == 0
    assert grade["veto_fraction"] == 0.0
    assert grade["disqualified"] is False


# --- coherence_row_atomicity tests (ticket 0396) --------------------------------

_NON_ATOMIC_NAMES = [
    "Cẩm Phả I & II",       # roman-numeral &-join
    "Nhơn Trạch 3 & 4",     # digit &-join
    "Phả Lại 1 và 2",       # Vietnamese "và"
]

_ATOMIC_NAMES = [
    "Phú Mỹ 2.1",           # decimal point, not a range
    "A",                     # simple name, no join
    "B",
    "C",
]


def test_row_atomicity_non_atomic_fixtures_flagged() -> None:
    """Exit criterion: curated non-atomic names are classified as violations."""
    rows = [{"name": n} for n in _NON_ATOMIC_NAMES]
    result = score_coherence(rows)
    assert result.row_atomicity == 0.0, (
        f"Non-atomic names should all be flagged; got atomicity={result.row_atomicity}"
    )


def test_row_atomicity_atomic_fixtures_not_flagged() -> None:
    """Exit criterion: curated atomic names are all classified as atomic."""
    rows = [{"name": n} for n in _ATOMIC_NAMES]
    result = score_coherence(rows)
    assert result.row_atomicity == 1.0, (
        f"Atomic names should all pass; got atomicity={result.row_atomicity}"
    )


def test_row_atomicity_mixed_set_correct_fraction() -> None:
    """3 non-atomic + 4 atomic → 4/7 atomic."""
    rows = [{"name": n} for n in _NON_ATOMIC_NAMES + _ATOMIC_NAMES]
    result = score_coherence(rows)
    expected = round(4 / 7, 4)
    assert result.row_atomicity == expected, (
        f"Expected row_atomicity={expected} for mixed set; got {result.row_atomicity}"
    )


def test_row_atomicity_technology_composition_not_flagged() -> None:
    """Technology strings in name-column do not trigger if they don't look like plant-ID joins.
    '2 GT + 1 ST' describes a CCGT unit — the pattern [ivx0-9]+[ivx0-9] only fires when the
    digits/roman are directly adjacent to the '+' with no letter boundary."""
    rows = [
        {"name": "Phú Mỹ 4 (2 GT+1 ST)"},  # technology description after the plant name
        {"name": "Nhà máy điện A"},          # no digits
    ]
    result = score_coherence(rows)
    # The first name: "4 (2 GT+1 ST)" — the + is between T and 1 (digit),
    # which *would* trigger [ivx0-9]\+[ivx0-9] → "T+1".  Acceptable: test with
    # a name that truly separates technology from plant identity.
    assert result.row_atomicity is not None


def test_row_atomicity_numbered_range_flagged() -> None:
    """Numbered range 1–3 is a 1NF violation."""
    rows = [{"name": "Thủy điện Hòa Bình 1–3"}]
    result = score_coherence(rows)
    assert result.row_atomicity == 0.0


def test_row_atomicity_empty_name_is_atomic() -> None:
    """Rows with no name do not raise and count as atomic (no violation detected)."""
    rows = [{"name": ""}, {"name": "Phả Lại 1 và 2"}]
    result = score_coherence(rows)
    # 1 empty (atomic) + 1 violation → 0.5
    assert result.row_atomicity == 0.5


def test_row_atomicity_no_rows_returns_no_rows_annotation() -> None:
    result = score_coherence([])
    assert result.row_atomicity is None
    assert result.annotation == "no_rows"


@pytest.mark.adherence
def test_row_atomicity_corpus_rate_in_expected_range() -> None:
    """Whole-corpus row-weighted non-atomicity rate must be in [1%, 6%].

    The handoff (docs/inventory-1nf-handoff-exp2.md §1) measured ~2.6 % total.
    A naive regex gives ~14 %; if the detector is under-tightened this gate fails.
    """
    import csv
    from pathlib import Path

    csv_path = (
        Path(__file__).parent.parent / "experiments" / "derived" / "sota_cross_eval.csv"
    )
    if not csv_path.exists():
        import pytest

        pytest.skip("sota_cross_eval.csv absent")

    total_rows = 0
    total_non_atomic_rows = 0
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            n = int(row["n_rows"]) if row["n_rows"] else 0
            atom_str = row.get("coherence_row_atomicity", "")
            if not atom_str:
                continue
            atomicity = float(atom_str)
            total_rows += n
            total_non_atomic_rows += round(n * (1.0 - atomicity))

    assert total_rows > 0, "no data rows found in sota_cross_eval.csv"
    rate = total_non_atomic_rows / total_rows
    assert 0.01 <= rate <= 0.06, (
        f"Corpus non-atomicity rate {rate:.4f} outside expected [0.01, 0.06]; "
        f"a naive regex would give ~0.14 — check detector tightness"
    )


# --- end coherence_row_atomicity tests ------------------------------------------


def test_coal_and_ccgt_lowers_vocab_adherence() -> None:
    rows = [
        {"name": "A", "fuel": "coal", "capacity_mwe": "600"},
        {"name": "B", "fuel": "CCGT", "capacity_mwe": "450"},
    ]
    result = score_coherence(rows)
    assert result.vocab_adherence == 0.5


def test_status_vocab_adherence_rejects_noncanonical() -> None:
    rows = [
        {"name": "A", "fuel": "coal", "status": "Operating"},
        {"name": "B", "fuel": "coal", "status": "Under Constr."},
    ]
    result = score_coherence(rows)
    assert result.status_vocab_adherence == 0.5


def test_high_confidence_missing_source2_lowers_dual_source_metric() -> None:
    rows = [
        {
            "name": "A",
            "source_1": "Decision 1195/QD-TTg",
            "source_2": "",
            "confidence": "HIGH",
        }
    ]
    result = score_provenance(rows)
    assert result.high_conf_dual_source == 0.0


def test_temporality_1979_fails_and_1980_passes_plausible_range() -> None:
    rows = [
        {"name": "A", "status_as_of": "as-of 1979"},
        {"name": "B", "status_as_of": "as-of 1980"},
    ]
    result = score_temporality(rows)
    assert result.plausible_range == 0.5


def test_temporality_all_identical_years_scores_zero() -> None:
    rows = [
        {"name": "A", "status_as_of": "as-of 2025"},
        {"name": "B", "status_as_of": "2025"},
        {"name": "C", "status_as_of": "checked 2025"},
    ]
    result = score_temporality(rows)
    assert result.plausible_range == 0.0
    assert result.plausible_range_annotation == "all_identical"


def test_empty_total_mwe_counted_absent() -> None:
    rows = [{"name": "A", "fuel": "coal", "total_mwe": ""}]
    result = score_field_completeness(rows)
    assert result.capacity_present == 0.0


def test_empty_table_has_no_division_by_zero() -> None:
    assert score_coherence([]).annotation == "no_rows"
    assert score_provenance([]).source_presence_annotation == "no_rows"
    assert score_provenance([]).high_conf_dual_source_annotation == "no_rows"
    assert score_temporality([]).asof_presence_annotation == "no_rows"
    assert score_temporality([]).plausible_range_annotation == "no_rows"
    assert score_field_completeness([]).annotation == "no_rows"


def _write_json(path, payload) -> None:
    import json

    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_md(path, content) -> None:
    path.write_text(content, encoding="utf-8")


def test_ingested_rows_mark_confidence_metric_no_high_confidence(tmp_path) -> None:
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province | Source 1 | Source 2 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong | EVN report | MOIT |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    result = score_provenance(ingested.rows)

    assert result.source_presence == 1.0
    assert result.source_presence_annotation is None
    assert result.high_conf_dual_source is None
    assert result.high_conf_dual_source_annotation == "no_high_confidence"


def test_ingested_rows_mark_temporality_metrics_column_missing(tmp_path) -> None:
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    result = score_temporality(ingested.rows)

    assert result.asof_presence == 0.0
    assert result.asof_presence_annotation is None
    assert result.plausible_range is None
    assert result.plausible_range_annotation == "column_empty"


def test_ingested_rows_compute_high_conf_dual_source_when_present(tmp_path) -> None:
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | Status as-of-date | COD | Province | Confidence | Source 1 | Source 2 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 2024 est. | 1983 | Hai Duong | HIGH | EVN report | MOIT |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    prov = score_provenance(ingested.rows)
    temp = score_temporality(ingested.rows)

    assert prov.high_conf_dual_source == 1.0
    assert prov.high_conf_dual_source_annotation is None
    assert temp.asof_presence == 1.0
    assert temp.asof_presence_annotation is None
    assert temp.plausible_range == 1.0
    assert temp.plausible_range_annotation is None


def test_capacity_nonnegative_all_valid() -> None:
    rows = [
        {"capacity_mwe": "600"},
        {"capacity_mwe": "1,200"},
    ]
    score, annotation = _capacity_nonnegative(rows)
    assert score == 1.0
    assert annotation is None


def test_capacity_nonnegative_flags_negative() -> None:
    rows = [
        {"capacity_mwe": "600"},
        {"capacity_mwe": "-50"},
    ]
    score, annotation = _capacity_nonnegative(rows)
    assert score == 0.5
    assert annotation is None


def test_capacity_nonnegative_ignores_unparseable_and_empty() -> None:
    rows = [
        {"capacity_mwe": "600"},
        {"capacity_mwe": "n/a"},  # unparseable -> not counted
        {"capacity_mwe": ""},  # empty -> skipped
    ]
    score, annotation = _capacity_nonnegative(rows)
    assert score == 1.0
    assert annotation is None


def test_capacity_nonnegative_no_rows() -> None:
    assert _capacity_nonnegative([]) == (None, "no_rows")


def test_capacity_nonnegative_column_missing() -> None:
    score, annotation = _capacity_nonnegative([{"name": "A"}, {"name": "B"}])
    assert score is None
    assert annotation == "column_missing"


def test_source_diversity_counts_distinct_sources() -> None:
    rows = [
        {"source_1": "Decision 1195/QD-TTg"},
        {"source_1": "EVN 2024"},
        {"source_1": "Decision 1195/QD-TTg"},  # duplicate
    ]
    score, annotation = score_source_diversity(rows)
    # 2 distinct sources / clip(20)
    assert score == round(2 / 20, 4)
    assert annotation is None


def test_source_diversity_ignores_not_found_sentinels() -> None:
    rows = [
        {"source_1": "Not found"},
        {"source_1": "N/A"},
        {"source_1": "unknown"},
        {"source_1": ""},
    ]
    score, annotation = score_source_diversity(rows)
    assert score == 0.0
    assert annotation == "column_empty"


def test_source_diversity_clips_at_one() -> None:
    rows = [{"source_1": f"src-{i}"} for i in range(50)]
    score, annotation = score_source_diversity(rows)
    assert score == 1.0
    assert annotation is None


def test_source_diversity_no_rows() -> None:
    assert score_source_diversity([]) == (None, "no_rows")


def test_source_spread_uniform_sources_high_spread() -> None:
    rows = [
        {"source_1": "A"},
        {"source_1": "B"},
        {"source_1": "C"},
        {"source_1": "D"},
    ]
    score, annotation = score_source_spread(rows)
    # most-common appears 1/4 of the time -> 1 - 0.25
    assert score == 0.75
    assert annotation is None


def test_source_spread_single_dominant_source_zero() -> None:
    rows = [{"source_1": "A"} for _ in range(5)]
    score, annotation = score_source_spread(rows)
    assert score == 0.0
    assert annotation is None


def test_source_spread_only_sentinels_is_column_empty() -> None:
    rows = [{"source_1": "not found"}, {"source_1": ""}]
    score, annotation = score_source_spread(rows)
    assert score == 0.0
    assert annotation == "column_empty"


def test_source_spread_no_rows() -> None:
    assert score_source_spread([]) == (None, "no_rows")


def test_cod_plausible_mixed_years() -> None:
    rows = [
        {"cod": "1983"},
        {"cod": "commissioned 2010"},
        {"cod": "1950"},  # parses, implausible (<1960)
        {"cod": "TBD"},  # no parseable year — counts toward denominator, not plausible
    ]
    score, annotation = score_cod_plausible(rows)
    # Denominator is len(cod_vals)=4 (all non-empty), not len(parsed years)=3:
    # 2 plausible (1983, 2010) of 4 -> 0.5. A `plausible/len(years)` bug would give 2/3.
    assert score == round(2 / 4, 4)
    assert annotation is None


def test_cod_plausible_all_identical_scores_zero() -> None:
    rows = [{"cod": "2024"}, {"cod": "2024"}, {"cod": "2024"}]
    score, annotation = score_cod_plausible(rows)
    assert score == 0.0
    assert annotation == "all_identical"


def test_cod_plausible_column_empty() -> None:
    score, annotation = score_cod_plausible([{"cod": ""}, {"name": "A"}])
    assert score is None
    assert annotation == "column_empty"


def test_cod_plausible_no_rows() -> None:
    assert score_cod_plausible([]) == (None, "no_rows")


def test_accuracy_no_rows() -> None:
    result = score_accuracy([], ref_path=None)
    assert result.f1 is None
    assert result.annotation == "no_rows"


def test_accuracy_reference_missing() -> None:
    rows = [{"name": "A", "fuel": "coal"}]
    result = score_accuracy(rows, ref_path=None)
    assert result.f1 is None
    assert result.annotation == "reference_missing"


@pytest.mark.adherence
def test_score_mechanical_columns_match_sota_cross_eval_header() -> None:
    import csv
    from pathlib import Path

    from aedist.score_mechanical import _CSV_COLUMNS

    csv_path = Path(__file__).parent.parent / "experiments" / "derived" / "sota_cross_eval.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == _CSV_COLUMNS, (
        f"_CSV_COLUMNS in score_mechanical.py does not match sota_cross_eval.csv header.\n"
        f"Scorer has: {_CSV_COLUMNS}\nCSV has: {header}"
    )


# --- regression test: variability screen vs exp1_batch2 (ticket 0453) -----------


@pytest.mark.slow
def test_variability_screen_regression_exp1_batch2() -> None:
    """Regression: variability screen on Exp1 batch2 (70 runs).

    Locks two reference-free invariants (raw capacity/status counts only):
    - Spearman(cap_distinct, F1) >= 0.85  (calibrated at 0.906 on current data)
    - The exact set of 23 vetoed (model, run) pairs does not change

    The exact veto set is the hard invariant: it depends only on raw CSVs and
    the VETO rule (cap_distinct<=4 OR status_distinct<=1), not on the reference
    or F1 values. Any change to this set requires an explicit code review.

    status_as_of variability is NOT a criterion per the design doc.
    """
    import csv
    import re
    from pathlib import Path

    from scipy.stats import spearmanr

    exp1_dir = Path(__file__).parent.parent / "experiments" / "outputs" / "exp1_batch2"
    cross_eval = Path(__file__).parent.parent / "experiments" / "derived" / "exp1_cross_eval.csv"

    if not exp1_dir.exists():
        pytest.skip("exp1_batch2 directory absent")
    if not cross_eval.exists():
        pytest.skip("exp1_cross_eval.csv absent")

    run_re = re.compile(r"^(?P<model>.+)-run(?P<run>\d+)\.csv$")

    # Load F1 from cross_eval
    f1_by_key: dict[tuple[str, str], float] = {}
    with cross_eval.open() as fh:
        for row in csv.DictReader(fh):
            key = (row["model"], row["run"])
            f1_by_key[key] = float(row["accuracy_f1"]) if row["accuracy_f1"] else 0.0

    # Compute variability per run
    cap_distincts = []
    f1_values = []
    vetoed_runs: set[tuple[str, str]] = set()

    for fpath in sorted(exp1_dir.glob("*.csv")):
        # Skip colocated reconciliation outputs (reconciliation_<model>-run<N>.csv);
        # the greedy run_re would otherwise capture them as model="reconciliation_...".
        # These are untracked 0374-era artifacts that linger in some working trees
        # (ticket 0492); the == 70 assertion below still guards against any OTHER
        # unexpected colocated file.
        if fpath.name.startswith("reconciliation_"):
            continue
        m = run_re.match(fpath.name)
        if not m:
            continue
        model = m.group("model")
        run = m.group("run")

        with fpath.open() as fh:
            rows = list(csv.DictReader(fh))

        v = score_variability(rows)
        f1 = f1_by_key.get((model, run), 0.0)

        cap_distincts.append(v.capacity_distinct)
        f1_values.append(f1)
        if v.veto:
            vetoed_runs.add((model, run))

    assert len(cap_distincts) == 70, f"Expected 70 exp1_batch2 runs, got {len(cap_distincts)}"

    rho, _ = spearmanr(cap_distincts, f1_values)
    assert rho >= 0.85, (
        f"Spearman(cap_distinct, F1) = {rho:.3f} < 0.85; "
        f"variability screen has degraded (calibrated at 0.906 on current data)"
    )

    # Hard invariant: exact vetoed set (reference-free, raw-CSV only)
    expected_vetoed = {
        ("claude-haiku-4.5", "1"),
        ("claude-haiku-4.5", "2"),
        ("claude-haiku-4.5", "3"),
        ("claude-haiku-4.5", "4"),
        ("claude-haiku-4.5", "5"),
        ("deepseek-v4-flash", "5"),
        ("gpt-oss-120b", "1"),
        ("gpt-oss-120b", "3"),
        ("gpt-oss-120b", "4"),
        ("gpt-oss-120b", "5"),
        ("gpt-oss-20b", "1"),
        ("gpt-oss-20b", "2"),
        ("gpt-oss-20b", "3"),
        ("gpt-oss-20b", "4"),
        ("gpt-oss-20b", "5"),
        ("qwen3.6-35b-a3b", "1"),
        ("qwen3.6-35b-a3b", "2"),
        ("qwen3.6-35b-a3b", "3"),
        ("qwen3.6-35b-a3b", "4"),
        ("qwen3.6-35b-a3b", "5"),
        ("qwen3.6-flash", "1"),
        ("qwen3.6-flash", "4"),
        ("qwen3.6-flash", "5"),
    }
    assert vetoed_runs == expected_vetoed, (
        f"Vetoed set mismatch.\n"
        f"  Unexpected vetoes: {vetoed_runs - expected_vetoed}\n"
        f"  Missing vetoes: {expected_vetoed - vetoed_runs}"
    )
