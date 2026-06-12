"""Ticket 0511 — §2-review scientific-integrity fixes guarded against artifacts.

Each assertion re-derives a number from its committed source artifact by an
independent parse, then asserts the literal (or required string) is present in
the manuscript (main.tex since ticket 0524). The cohort counts 16/14 each come
from a *different* source:

- 16 = the run set ``modelset_exp1_journal`` in ``experiments/experiments.toml``.
- 14 = the analysis cohort = distinct models in ``exp1_cross_eval.csv``
  (the scoring CSV the per-model figures read).

(The third count, 12 = the spider-figure cohort, left the manuscript with the
spider figure in ticket 0507; the spider survives in the slides only.)

Ticket 0532 round 2 (author brief, reading 1): the abstract carries NO
statistics (no F1, no ρ) and no em-dash; the ρ=0.92 caveat must accompany ρ
wherever it still appears (conclusion, Discussion). The cost-savings claim and
the cost-F1 non-monotonicity novelty claim must be gone. The status-vocabulary
mismatch sentence must cite the grouped ~38% from the committed
status-difficulty table.
"""

import csv
import json
import re
import tomllib
from pathlib import Path

import pytest
from manuscript_source import body, body_raw, figure_caption, normalized

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
TOML = REPO_ROOT / "experiments" / "experiments.toml"
XEVAL_CSV = REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv"
DIFF_TEX = REPO_ROOT / "report" / "inputs" / "generated" / "tab_status_difficulty.tex"
PROVENANCE_MD = REPO_ROOT / "data" / "reference" / "PROVENANCE.md"


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
    text = body()
    # The cohort paragraph must name both counts.
    assert f"{n_run} models" in text, "cohort paragraph must state the 16-model run set"
    assert f"{n_analysis}-model" in text, "cohort paragraph must state the 14-model analysis cohort"


def test_zero_good_run_models_match_artifact():
    """The reliability-figure caption names the zero-good-run models; re-derive
    that set from the scoring CSV via the gate so the caption cannot drift
    silently on a data update (ticket 0507 review finding)."""
    if not XEVAL_CSV.exists():
        pytest.skip("cross-eval artifact not present")
    from aedist.plot_exp1_reliability import load_rows, reliability_by_model

    rel = reliability_by_model(XEVAL_CSV)
    zero = sorted(m for m, n in rel.items() if n == 0)
    caption = figure_caption("fig:reliability")
    assert f"the {len(zero)} models with zero good runs" in caption or (
        len(zero) == 3 and "the three models with zero good runs" in caption
    ), f"caption must state the zero-good-run count ({len(zero)})"
    for model in zero:
        assert model in caption, f"zero-good-run model {model} missing from caption"
    # load_rows is exercised transitively; keep the import honest.
    assert load_rows(XEVAL_CSV)


def _abstract_paragraph() -> str:
    """The abstract text itself (the article-class abstract environment,
    ticket 0542), normalized — not the whole pre-Introduction region."""
    text = body_raw()
    start = text.find("\\begin{abstract}")
    assert start != -1, "no abstract environment found in main.tex"
    start += len("\\begin{abstract}")
    end = text.find("\\end{abstract}", start)
    assert end != -1, "unterminated abstract environment in main.tex"
    return normalized(text[start:end])


def test_abstract_register_follows_author_brief():
    """Ticket 0532 round 2 (author reading-1 brief): the abstract is written
    for the general reader — no statistics (no F1 scores, no ρ/τ), no
    em-dashes, no literature-review closing, no fusion sentence — and the
    177-plant register is disambiguated as spanning the whole lifecycle."""
    abstract = _abstract_paragraph()
    assert "F1" not in abstract, "author brief: no F1 detail in the abstract"
    assert "ρ" not in abstract and "τ" not in abstract and "\\tau" not in abstract, (
        "author brief: the ρ=0.92 screening statistics leave the abstract"
    )
    assert "—" not in abstract, "author brief: no em-dashes in the abstract"
    assert "To our knowledge" not in abstract, (
        "author brief: no literature review in the abstract"
    )
    assert "Pooling" not in abstract and "pooling" not in abstract, (
        "author brief: the fusion/pooling sentence leaves the abstract"
    )
    assert "lifecycle" in abstract, (
        "author brief: 177 plants must read as the full-lifecycle register, "
        "not 177 operating plants"
    )
    assert len(abstract.split()) < 300, (
        "author brief: the abstract must stay markedly shorter than the "
        "356-word round-1 version"
    )


def test_rho_caveat_wherever_rho_appears():
    """Ticket 0532 round 2: ρ=0.92 left the abstract; wherever it still
    appears in the narrative (conclusion, Discussion), the pooled /
    across-model / in-sample qualification must accompany it."""
    text = body()
    conclusion = text.split("\\section{Conclusion}\\label{sec:conclusion}")[1].split("\\appendix")[0]
    assert "ρ = 0.92, pooled across models and in-sample" in conclusion, (
        "conclusion ρ=0.92 must carry the pooled/in-sample caveat"
    )
    assert "within-model signal positive but modest, \\ref{sec:annex-screen}" in conclusion, (
        "conclusion ρ=0.92 must point to the within-model validation annex"
    )
    discussion = text.split("\\section{Discussion}\\label{sec:discussion}")[1].split(
        "\\section*{Related Work — Methods}"
    )[0]
    assert "ρ = 0.92" in discussion and "existence proof rather than a validated detector" in discussion, (
        "Discussion ρ=0.92 must keep the existence-proof qualification"
    )
    assert "tuned on the same 70 runs" in discussion, (
        "Discussion must keep the in-sample (cutoffs tuned on the same runs) caveat"
    )


def test_binding_constraint_framed_as_hypothesis():
    """Ticket 0532: abstract and conclusion frame the binding-constraint claim
    as a hypothesis, not a finding.

    Round 2 (author brief) literals: the abstract's "working hypothesis"
    framing and the exploratory/unregistered qualifier on the documents
    condition; the conclusion's "conjecture about why" opener and the
    conditional recommendation.

    Ticket 0541 (scoped divergence): the body speaks within-experiment with
    light epistemic markers — "suggests" in the equalisation paragraph,
    "appears to" in the fusion section — so a later edit cannot silently
    revert the body to a flat factual register.
    """
    abstract = _abstract_paragraph()
    text = body()
    conclusion = text.split("\\section{Conclusion}\\label{sec:conclusion}")[1].split("\\appendix")[0]
    assert "point toward a working hypothesis" in abstract, (
        "abstract must frame the binding-constraint claim as a working hypothesis"
    )
    assert "exploratory, unregistered condition" in abstract, (
        "abstract must name the equalisation evidence exploratory and unregistered"
    )
    assert "the evidence points toward a conjecture about why" in conclusion, (
        "conclusion must frame the binding-constraint claim as a conjecture"
    )
    assert "If the constraint is indeed the documents" in conclusion, (
        "conclusion recommendation must stay conditional on the hypothesis"
    )
    assert "suggests the binding constraint lies" in text, (
        "equalisation paragraph must hedge the relocation claim with 'suggests'"
    )
    assert "appears to shift from model capability" in text, (
        "fusion section must hedge the constraint-shift claim with 'appears to'"
    )


def test_intro_does_not_claim_per_cell_provenance_checking():
    """Author brief (reading 1): the paper measures citation presence and
    counts; it does not check/trace per-cell provenance. The Introduction
    (through Contributions) must not claim that it does."""
    intro = body().split("\\section{Introduction}\\label{sec:intro}")[1].split(
        "\\section{Related Work — Empirical landscape}"
    )[0]
    assert "per-cell provenance" not in intro, (
        "intro must not claim per-cell provenance checking; scope to per-row "
        "citation coverage and corroboration"
    )


def test_cost_savings_claim_cut():
    """The unsubstantiated cost-savings claim is removed (no committed hours figure)."""
    assert "from weeks of expert monitoring to a few euros" not in body(), (
        "cost-savings claim must be cut — no committed compilation-hours number exists"
    )


def test_cost_f1_nonmonotonicity_novelty_dropped():
    """The cost-vs-F1 non-monotonicity primacy claim is dropped entirely."""
    assert "non-monotone cost-versus-F1 relationship for structured factual extraction has not been documented" not in body(), (
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
    Round 2 (author brief): the abstract's copy of claim (1) is removed (no
    literature review in the abstract); the claim survives in §fusion.
    """
    text = body()
    demoted_phrasings = [
        "MoE non-determinism specifically for multi-row structured outputs at deterministic decoding settings has not been characterised",
        "day-scale F1 drift at fixed deterministic call parameters has not been quantified",
        "per-row provenance analysis of this kind has not been published",
    ]
    for phrase in demoted_phrasings:
        assert phrase not in text, f"demoted observation still carries primacy framing: {phrase!r}"
    # The three surviving novelty claims (verbatim anchors).
    survivors = [
        "no published benchmark or system targets open-world enumeration",  # (1) benchmark gap
        "conjunction of per-cell provenance with per-cell temporal validity",  # (2)
        "run-level screen rates \\emph{information credibility} while the model-level grade rates \\emph{source reliability}",  # (3) two-grain
    ]
    for s in survivors:
        assert s in text, f"surviving novelty claim missing: {s!r}"


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
    text = body()
    # The manuscript must cite the same verifiable 2019 dates and keep the
    # built-vs-pipeline coverage caveat (no over-claim that every plant was
    # visible to every model). It must NOT claim the group *created* the page.
    assert "19 June 2019" in text, "manuscript must state the content-injection date"
    assert "902510278" in text, "manuscript must cite the verifiable revision id"
    assert "built fleet" in text and "pipeline tail" in text, (
        "seeding paragraph must preserve the built-vs-pipeline coverage caveat"
    )


def test_status_vocab_mismatch_sentence_present():
    """The status-vocabulary mismatch sentence cites the grouped ~38% from the table."""
    if not DIFF_TEX.exists():
        pytest.skip("status difficulty table not generated")
    tex = DIFF_TEX.read_text(encoding="utf-8")
    # Re-derive the Proposed share from the committed table (En projet line).
    m = re.search(r"En projet & \d+ & (\d+\.\d+)\\%", tex)
    assert m, "could not parse Proposed share from status-difficulty table"
    share = m.group(1)  # e.g. "38.4" — the value \StatusProposedSharePct carries
    assert int(share.split(".")[0]) == 38, (
        f"expected grouped Proposed share ~38%, table says {share}"
    )
    text = body()
    assert "controlled vocabulary" in text and "status accuracy" in text, (
        "status-vocab mismatch sentence missing"
    )
    assert f"{share}%" in text, (
        f"status-vocab sentence must state the {share}% Proposed share "
        "(via \\StatusProposedSharePct)"
    )


# --- Ticket 0539: prompt transparency (Annex B verbatim Doc-07 prompt) ---

EXP1_RUN_RECORD = (
    REPO_ROOT / "experiments" / "outputs" / "exp1_batch2" / "claude-haiku-4.5-run1.json"
)
PROMPT_MD = REPO_ROOT / "experiments" / "sota" / "protocol_07_naive_prompt.md"


def test_analysis_cohort_prompt_matches_shipped_record():
    """The prompt file reproduced in the annex is identical (modulo the
    worker's trailing-newline ``.strip()``) to the prompt the exp1_batch2
    analysis cohort actually received, re-derived from an archived per-run
    record rather than trusted from a survey."""
    assert EXP1_RUN_RECORD.exists(), (
        f"{EXP1_RUN_RECORD} missing: the drift guard would be silently "
        "disabled — update this path if the record was relocated"
    )
    assert PROMPT_MD.exists(), (
        f"{PROMPT_MD} missing: the drift guard would be silently disabled"
    )
    record = json.loads(EXP1_RUN_RECORD.read_text(encoding="utf-8"))
    assert record["prompt"] == PROMPT_MD.read_text(encoding="utf-8").strip(), (
        "experiments/sota/protocol_07_naive_prompt.md has drifted from the "
        "prompt shipped to the exp1_batch2 analysis cohort"
    )


def test_body_no_longer_attributes_modules_prompt_to_cohort():
    """The pre-appendix body must not claim the analysis cohort received the
    2_goal + 5_table modules composition: that prompt belongs to the archived
    baseline sweep and is scoped as such in the annex (ticket 0539)."""
    pre_appendix = body().split("\\appendix")[0]
    assert "2_goal" not in pre_appendix, (
        "body still attributes the 2_goal + 5_table composition to the "
        "analysis cohort; it received the full Doc-07 naive prompt"
    )


BASELINE_RUN_RECORD = (
    REPO_ROOT
    / "experiments"
    / "archive"
    / "outputs"
    / "exp1"
    / "baseline"
    / "claude-haiku-4.5-run1.json"
)


def test_annex_baseline_prompt_carries_as_sent_status_vocabulary():
    """The archived-baseline prompt quoted in the annex matches the as-sent
    text, re-derived from an archived per-run record (all 133 baseline+topup
    records carry the identical prompt). The 5_table.txt module was aligned to
    GEM vocabulary only AFTER this cohort ran (cba3ffc5, 2026-05-24), so the
    annex quote must show the pre-alignment status enumeration, not the
    module file's current text (post-merge review blocker on #983)."""
    assert BASELINE_RUN_RECORD.exists(), (
        f"{BASELINE_RUN_RECORD} missing: the baseline drift guard would be "
        "silently disabled — update this path if the record was relocated"
    )
    prompt = json.loads(BASELINE_RUN_RECORD.read_text(encoding="utf-8"))["prompt"]
    # Re-derive the as-sent status enumeration from the record.
    status_line = next(
        line for line in prompt.splitlines() if line.startswith("- Status:")
    )
    statuses = [s.strip() for s in status_line.removeprefix("- Status:").split("/")]
    assert "Planned" in statuses, "as-sent baseline enum expected to contain Planned"
    annex = body().split("\\appendix")[1]
    quote = annex.split("Archived baseline prompt")[1].split("Analysis-cohort prompt")[0]
    for status in statuses:
        assert status in quote, (
            f"as-sent baseline status {status!r} missing from the annex's "
            "archived-baseline prompt quote"
        )
    # The GEM-aligned enum belongs to the analysis cohort, not this quote.
    for gem_only in ("Announced", "Pre-permit", "Permitted", "Operating", "Shelved"):
        assert gem_only not in quote, (
            f"GEM-vocabulary status {gem_only!r} leaked into the baseline "
            "prompt quote; the cohort ran before the GEM alignment"
        )
    # Two further distinctive as-sent sentences, re-derived from the record.
    for sentence in (
        "primary-sourced reference inventory",
        "Actual or expected commercial operation date",
    ):
        assert sentence in prompt, f"anchor not in record prompt: {sentence!r}"
        assert sentence in quote, f"as-sent anchor missing from annex quote: {sentence!r}"


def test_annex_carries_doc07_prompt_verbatim_anchors():
    """The Experiment 1 annex reproduces the Doc-07 analysis-cohort prompt:
    spot-check distinctive sentences that exist only in that prompt."""
    annex = body().split("\\appendix")[1]
    anchors = [
        "Begin the document directly with the inventory table",
        "aligned with Global Energy Monitor vocabulary",
        "Confident fabrication is the policed failure mode",
    ]
    for anchor in anchors:
        assert anchor in annex, f"Doc-07 prompt anchor missing from annex: {anchor!r}"
