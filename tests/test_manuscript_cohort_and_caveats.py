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

Ticket 0557 (CI test polarity rule, see .claude/rules/writing.md): assertions
here are mechanical (re-derived from artifacts), content-fidelity (verbatim
quotes of fixed external documents), or *negative/conditional* guards on
forbidden phrasings. Positive authorial-wording pins are banned — the standing
editorial decisions they encoded live in docs/editorial-brief.md, checked at
review time by /review-pr-prose.
"""

import csv
import json
import re
import tomllib
from pathlib import Path

import pytest
from manuscript_source import body, body_raw, figure_caption, normalized, section

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
    """The analysis-cohort count matches an independent re-derivation, and the
    run-set bookkeeping (16 models dispatched) is NOT in the body.

    Ticket 0613 swept the run-set / dispatch-count bookkeeping (16 models
    dispatched, two dropped) out of the §5 body into the Exp-1 annex; the body
    now states only the \\NumCensusModels analysis cohort. Per the CI polarity
    rule (ticket 0557) this guard is mechanical: the analysis count is
    re-derived from the scoring CSV (\\NumCensusModels expands to it via the
    macro table, so the literal appears in the normalized body), and the
    run-set count is asserted *absent* from the body — a negative guard, not a
    positive prose pin.
    """
    if not (TOML.exists() and XEVAL_CSV.exists()):
        pytest.skip("cohort artifacts not present")
    n_run, n_analysis = _derive_cohort_counts()
    assert (n_run, n_analysis) == (16, 14), (
        f"expected cohorts 16/14, derived {n_run}/{n_analysis}"
    )
    body_text = body().split("\\appendix", 1)[0]
    # Analysis cohort (\NumCensusModels) is named in the body — macro-expanded.
    assert f"cohort of {n_analysis} models" in body_text, (
        f"§5 cohort summary must state the {n_analysis}-model analysis cohort "
        "(via \\NumCensusModels)"
    )
    # Run-set / dispatch bookkeeping moved to the annex (ticket 0613).
    assert f"{n_run} models" not in body_text, (
        f"run-set bookkeeping ('{n_run} models') must not appear in the body — "
        "swept to the Exp-1 annex (ticket 0613)"
    )


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
    177-plant register must not be misstated as operating-only (ticket 0557:
    the positive 'lifecycle' wording pin moved to docs/editorial-brief.md,
    entry lifecycle-scope)."""
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
    assert "operating plants" not in abstract and "operating-only" not in abstract, (
        "author brief: the 177-plant register must not read as operating-only "
        "— it spans the whole project lifecycle (see docs/editorial-brief.md)"
    )
    assert len(abstract.split()) < 300, (
        "author brief: the abstract must stay markedly shorter than the "
        "356-word round-1 version"
    )


def test_spearman_rho_regression_absent_from_manuscript():
    """Ticket 0598: the Spearman ρ regression presentation is dropped from the
    whole manuscript — body AND annex. The screening conclusion (a
    reference-free reliability grade triages the weak models without ground
    truth) is now carried by Figure~\\ref{fig:reliability}, not by a
    coefficient. This is a pure negative guard (CI polarity rule, ticket
    0557): forbid the jargon and the regression literals; pin no positive
    replacement wording.

    Supersedes the former conditional caveat guard (the now-retired
    rho-caveat-conclusion / rho-caveat-discussion brief entries): there is no
    ρ claim left to qualify, so the conditional can never fire — a negative
    guard is the correct retirement, keeping the literal from creeping back."""
    text = body_raw()
    assert "Spearman" not in text, (
        "the Spearman ρ regression must not appear in main.tex (ticket 0598 "
        "dropped it; the screening conclusion is carried by fig:reliability)"
    )
    assert "ρ = 0.92" not in text and "ρ=0.92" not in text, (
        "the ρ = 0.92 screen-correlation literal must not appear in main.tex "
        "(ticket 0598)"
    )
    assert "\\ScreenPooledSpearman" not in text, (
        "the \\ScreenPooledSpearman macro call must not appear in main.tex "
        "(ticket 0598 dropped the ρ regression presentation)"
    )


def _sentences_containing(text: str, phrase: str) -> list[str]:
    """Sentences of the normalized text that contain `phrase` (sentence =
    split at .!? followed by whitespace; decimals like 0.92 survive intact)."""
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if phrase in s]


def test_binding_constraint_framed_as_hypothesis():
    """Tickets 0532/0541, demoted to negative/sentence-scoped form (ticket
    0557): the binding-constraint claim is never stated as a flat finding,
    anywhere.

    - Abstract: the claim must not appear at all (unchanged negative; the
      2026-06-12 rewrite dropped it — absence satisfies the no-overclaim
      intent by construction).
    - Body-wide: every sentence asserting "binding constraint is ..." must
      carry conjecture/conditional framing; every sentence relocating the
      constraint ("binding constraint lies") or claiming the constraint
      shifts must carry an epistemic hedge.

    The exact hedged phrasings ("the evidence points toward a conjecture
    about why", "If the constraint is indeed the documents", "suggests the
    binding constraint lies", "appears to shift from model capability") are
    editorial decisions recorded in docs/editorial-brief.md
    (binding-constraint-conjecture, equalisation-hedge, fusion-hedge).
    """
    abstract = _abstract_paragraph()
    text = body()
    assert "binding constraint is" not in abstract, (
        "abstract must not state the binding-constraint claim as a flat finding"
    )
    hedges = ("conjectur", "hypothes", "suggest", "appear", "If ", "if the constraint")
    for sentence in _sentences_containing(text, "binding constraint is"):
        assert any(h in sentence for h in hedges), (
            f"flat binding-constraint finding (no conjecture/conditional "
            f"framing in sentence): {sentence!r}"
        )
    for sentence in _sentences_containing(text, "binding constraint lies"):
        assert "suggest" in sentence or "appear" in sentence, (
            f"unhedged constraint-relocation claim: {sentence!r}"
        )
    for sentence in _sentences_containing(text, "binding constraint"):
        if "shift" not in sentence:
            continue
        # A hedged claim ("appears to shift") or an explicit negation
        # ("did not shift") is fine; only the flat positive claim is banned.
        assert any(h in sentence for h in ("appear", "may", "suggest", "not")), (
            f"unhedged constraint-shift claim: {sentence!r}"
        )


def test_intro_does_not_claim_per_cell_provenance_checking():
    """Author brief (reading 1): the paper measures citation presence and
    counts; it does not check/trace per-cell provenance. The Introduction
    (through Contributions) must not claim that it does."""
    intro = section("sec:intro")
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


def test_novelty_claim_demotions_hold():
    """Demoted primacy claims stay demoted; surviving claims keep loose anchors.

    Negative half (unchanged ratchet): the MoE-non-determinism, day-scale-drift
    and per-row-provenance primacy phrasings were demoted to plain observations
    (ticket 0532) and must not return.

    Positive half, demoted to loose anchors (ticket 0557): the three surviving
    novelty claims — (1) benchmark gap and (2) per-row provenance × temporality,
    both in the subsection labelled sec:fusion; (3) two-grain
    credibility/reliability scoring, in the screening subsection
    (sec:ext-screen — moved out of the Discussion by ticket 0562) — are
    guarded by section-scoped marker presence, not verbatim sentences.
    §fusion must keep at least two primacy-marker sentences (one per claim);
    the screening subsection must keep the STANAG 2511 two-grain vocabulary
    ("information credibility" / "source reliability" — fixed external
    terminology, not authorial prose). The verbatim phrasings are recorded in
    docs/editorial-brief.md (novelty-benchmark-gap, novelty-provenance-temporality,
    novelty-two-grain).
    """
    text = body()
    demoted_phrasings = [
        "MoE non-determinism specifically for multi-row structured outputs at deterministic decoding settings has not been characterised",
        "day-scale F1 drift at fixed deterministic call parameters has not been quantified",
        "per-row provenance analysis of this kind has not been published",
    ]
    for phrase in demoted_phrasings:
        assert phrase not in text, f"demoted observation still carries primacy framing: {phrase!r}"
    fusion = section("sec:fusion")
    markers = ("no published", "to our knowledge", "did we find", "has not been")
    marker_sentences = [
        s
        for s in re.split(r"(?<=[.!?])\s+", fusion)
        if any(m in s.lower() for m in markers)
    ]
    assert len(marker_sentences) >= 2, (
        "§fusion must keep both surviving primacy claims (benchmark gap; "
        f"provenance × temporality) — found {len(marker_sentences)} "
        "primacy-marker sentence(s)"
    )
    screen = section("sec:ext-screen")
    assert "information credibility" in screen and "source reliability" in screen, (
        "the screening subsection (sec:ext-screen) must keep the two-grain "
        "scoring claim (STANAG 2511 information-credibility / "
        "source-reliability vocabulary)"
    )


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


def test_status_vocab_mismatch_share_matches_artifact():
    """The manuscript cites the grouped ~38% Proposed share from the committed
    status-difficulty table (mechanical artifact check). The "controlled
    vocabulary" / "status accuracy" phrase anchors were demoted to
    docs/editorial-brief.md (status-vocab-mismatch) by ticket 0557."""
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
    assert f"{share}%" in body(), (
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


def test_annex_baseline_prompt_block_removed():
    """The archived-baseline prompt subsection was deleted from Annex A
    (reading-2 finding 9, ticket 0590): its results were never presented, so
    the coding-archeology block is gone. Negative guard — the block must not
    reappear."""
    annex = body().split("\\appendix")[1]
    assert "Archived baseline prompt" not in annex, (
        "the archived-baseline prompt block was deleted (ticket 0590); "
        "it must not reappear in Annex A"
    )


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
