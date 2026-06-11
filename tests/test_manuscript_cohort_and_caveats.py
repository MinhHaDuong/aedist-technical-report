"""Ticket 0511 — §2-review scientific-integrity fixes guarded against artifacts.

Each assertion re-derives a number from its committed source artifact by an
independent parse, then asserts the literal (or required string) is present in
the manuscript. The cohort counts 16/14 each come from a *different* source:

- 16 = the run set ``modelset_exp1_journal`` in ``experiments/experiments.toml``.
- 14 = the analysis cohort = distinct models in ``exp1_cross_eval.csv``
  (the scoring CSV the per-model figures read).

(The third count, 12 = the spider-figure cohort, left the manuscript with the
spider figure in ticket 0507; the spider survives in the slides only.)

The ρ=0.92 caveat must appear in BOTH the abstract and the conclusion regions.
The cost-savings claim and the cost-F1 non-monotonicity novelty claim must be
gone. The status-vocabulary mismatch sentence must cite the grouped ~38% from
the committed status-difficulty table.
"""

import csv
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"
TOML = REPO_ROOT / "experiments" / "experiments.toml"
XEVAL_CSV = REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv"
DIFF_TEX = REPO_ROOT / "report" / "inputs" / "generated" / "tab_status_difficulty.tex"
PROVENANCE_MD = REPO_ROOT / "data" / "reference" / "PROVENANCE.md"

def _md() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def _derive_cohort_counts() -> tuple[int, int]:
    """Re-derive (run set, analysis cohort) model counts from artifacts."""
    with TOML.open("rb") as f:
        toml = tomllib.load(f)
    n_run = len(toml["sets"]["modelset_exp1_journal"]["model_ids"])

    rows = list(csv.DictReader(XEVAL_CSV.open(encoding="utf-8")))
    analysis_models = sorted({r["model"] for r in rows if r["model"].strip()})
    n_analysis = len(analysis_models)
    return n_run, n_analysis


def test_cohort_counts_match_artifacts():
    """The cohort paragraph's 16/14 match an independent re-derivation."""
    if not (TOML.exists() and XEVAL_CSV.exists()):
        pytest.skip("cohort artifacts not present")
    n_run, n_analysis = _derive_cohort_counts()
    assert (n_run, n_analysis) == (16, 14), (
        f"expected cohorts 16/14, derived {n_run}/{n_analysis}"
    )
    md = _md()
    # The cohort paragraph must name both counts.
    assert f"{n_run} models" in md, "cohort paragraph must state the 16-model run set"
    assert f"{n_analysis}-model" in md, "cohort paragraph must state the 14-model analysis cohort"


def test_zero_good_run_models_match_artifact():
    """The [@fig:reliability] caption names the zero-good-run models; re-derive
    that set from the scoring CSV via the gate so the caption cannot drift
    silently on a data update (ticket 0507 review finding)."""
    if not XEVAL_CSV.exists():
        pytest.skip("cross-eval artifact not present")
    from aedist.plot_exp1_reliability import load_rows, reliability_by_model

    rel = reliability_by_model(XEVAL_CSV)
    zero = sorted(m for m, n in rel.items() if n == 0)
    md = _md()
    caption = next(line for line in md.splitlines() if "{#fig:reliability}" in line)
    assert f"the {len(zero)} models with zero good runs" in caption or (
        len(zero) == 3 and "the three models with zero good runs" in caption
    ), f"caption must state the zero-good-run count ({len(zero)})"
    for model in zero:
        assert model in caption, f"zero-good-run model {model} missing from caption"
    # load_rows is exercised transitively; keep the import honest.
    assert load_rows(XEVAL_CSV)


def test_rho_caveat_in_abstract_and_conclusion():
    """The ρ=0.92 caveat appears in both the abstract and the conclusion."""
    md = _md()
    # Ticket 0518: the "Annex F" reference is now the symbolic [-@sec:annex-screen].
    # Ticket 0532: the abstract carries the hardened form — across-model/in-sample
    # confound named, within-model stratified τ inlined with its 10/14 directional count.
    abstract_caveat = (
        "pooled across models and in-sample; stratifying by model leaves a modest "
        "Kendall $\\tau$ = +0.215, positive in 10 of 14 models ([-@sec:annex-screen])"
    )
    conclusion_caveat = "within-model signal positive but modest, [-@sec:annex-screen]"
    # Abstract region: everything before the Introduction section.
    abstract = md.split("## Introduction {#sec:intro}")[0]
    conclusion_heading = "## Conclusion {#sec:conclusion}"
    conclusion = md.split(conclusion_heading)[1].split("\\appendix")[0]
    assert abstract_caveat in abstract, "ρ=0.92 caveat missing from abstract"
    assert conclusion_caveat in conclusion, "ρ=0.92 caveat missing from conclusion"


def test_cost_savings_claim_cut():
    """The unsubstantiated cost-savings claim is removed (no committed hours figure)."""
    md = _md()
    assert "from weeks of expert monitoring to a few euros" not in md, (
        "cost-savings claim must be cut — no committed compilation-hours number exists"
    )


def test_cost_f1_nonmonotonicity_novelty_dropped():
    """The cost-vs-F1 non-monotonicity primacy claim is dropped entirely."""
    md = _md()
    assert "non-monotone cost-versus-F1 relationship for structured factual extraction has not been documented" not in md, (
        "cost-F1 non-monotonicity novelty claim must be dropped (2.8)"
    )


def test_exactly_three_novelty_claims_survive():
    """Exactly three explicit primacy claims survive; demoted observations lose framing.

    Counts the manuscript-level primacy assertions of the form
    'to our knowledge ... has not been / no published / no prior'. The three
    kept are: (1) benchmark gap, (2) per-row provenance × temporality, and
    (3) two-grain credibility/reliability scoring. The MoE-non-determinism and
    day-scale-drift assertions are demoted to plain observations; the cost-F1
    claim is dropped. 'we did not find' epistemic hedges are NOT primacy claims.
    """
    md = _md()
    demoted_phrasings = [
        "MoE non-determinism specifically for multi-row structured outputs at deterministic decoding settings has not been characterised",
        "day-scale F1 drift at fixed deterministic call parameters has not been quantified",
        "per-row provenance analysis of this kind has not been published",
    ]
    for phrase in demoted_phrasings:
        assert phrase not in md, f"demoted observation still carries primacy framing: {phrase!r}"
    # The three surviving novelty claims (verbatim anchors).
    survivors = [
        "no prior benchmark targets open-world enumeration",  # (1) benchmark gap
        "conjunction of per-cell provenance with per-cell temporal validity",  # (2)
        "run-level screen rates *information credibility* while the model-level grade rates *source reliability*",  # (3) two-grain
    ]
    for s in survivors:
        assert s in md, f"surviving novelty claim missing: {s!r}"


def test_wikipedia_seeding_date_matches_provenance():
    """The §4 Wikipedia-seeding date in the manuscript matches PROVENANCE.md.

    This is a provenance fact (author disclosure recorded in PROVENANCE.md),
    not a re-derived statistic — the test enforces that the manuscript's date
    and the committed provenance record agree, so neither can drift silently.
    """
    if not PROVENANCE_MD.exists():
        pytest.skip("PROVENANCE.md not found")
    prov = PROVENANCE_MD.read_text(encoding="utf-8")
    # The load-bearing, independently-verifiable event is the 2019-06-19
    # content injection (Wikipedia revision 902510278); the coal-list split is
    # 2019-07-05.
    assert "2019-06-19" in prov, "PROVENANCE.md must record the content-injection date"
    assert "902510278" in prov, "PROVENANCE.md must cite the verifiable page-history revision"
    assert "2019-07-05" in prov, "PROVENANCE.md must record the coal-list split date"
    md = _md()
    # The manuscript must cite the same verifiable 2019 dates and keep the
    # built-vs-pipeline coverage caveat (no over-claim that every plant was
    # visible to every model). It must NOT claim the group *created* the page.
    assert "19 June 2019" in md, "manuscript must state the content-injection date"
    assert "902510278" in md, "manuscript must cite the verifiable revision id"
    assert "built fleet" in md and "pipeline tail" in md, (
        "seeding paragraph must preserve the built-vs-pipeline coverage caveat"
    )


def test_status_vocab_mismatch_sentence_present():
    """The status-vocabulary mismatch sentence cites the grouped ~38% from the table."""
    if not DIFF_TEX.exists():
        pytest.skip("status difficulty table not generated")
    tex = DIFF_TEX.read_text(encoding="utf-8")
    # Re-derive the Proposed share from the committed table (En projet line).
    import re

    m = re.search(r"En projet & \d+ & (\d+)\.\d+\\%", tex)
    assert m, "could not parse Proposed share from status-difficulty table"
    pct_int = int(m.group(1))
    assert pct_int == 38, f"expected grouped Proposed share ~38%, table says {pct_int}"
    md = _md()
    assert "controlled vocabulary" in md and "status accuracy" in md, (
        "status-vocab mismatch sentence missing"
    )
    assert "38%" in md, "status-vocab sentence must state the ~38% Proposed share"
