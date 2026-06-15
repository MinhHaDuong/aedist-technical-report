"""Tickets 0612, 0613, 0614 — §5 (Experiment 1) prose tightening.

Negative guards only (CI polarity rule, ticket 0557): forbid the old
phrasings; never pin the new authorial wording.

- 0612: §5 opener recast from a statement-with-clause into a statement +
  question. The old assertive clause must be absent.
- 0613: the "\\textbf{Cohorts.}" bookkeeping paragraph is replaced by a
  one-sentence cohort summary, and the experimental-history bookkeeping
  ("16 models dispatched / two dropped") is swept OUT of the body (it lives
  in the Exp-1 annex). The cohort facts are stated once — the redundant
  cohort enumeration in the Experiment-1 paragraph is gone.
- 0614: the inline scoring methodology in §5 is replaced by a reference to
  the quality-dimensions section; the restated-method signatures are absent.

`body()` is whitespace-normalized (hard wraps joined, runs collapsed to one
space), so the substrings below are written as single-line prose.
"""

import pytest
from manuscript_source import body, section

pytestmark = pytest.mark.adherence


def _body_before_appendix() -> str:
    """The §1..Conclusion body — everything before \\appendix."""
    return body().split("\\appendix", 1)[0]


def test_old_s5_opener_clause_absent() -> None:
    """0612: assertive clause recast as a question — old clause must be gone."""
    assert "but not one that meets statistical or scientific quality standards" not in body(), (
        "old §5 opener clause '..., but not one that meets statistical or "
        "scientific quality standards' must be absent — recast as a question "
        "(ticket 0612)"
    )


def test_cohorts_bookkeeping_paragraph_absent() -> None:
    """0613: the 'Cohorts.' dispatch-count paragraph is replaced."""
    assert "The sweep dispatched 16 models" not in body(), (
        "old §5 'Cohorts.' paragraph signature 'The sweep dispatched 16 "
        "models' must be absent from the body (ticket 0613)"
    )


def test_dispatch_count_not_in_body() -> None:
    """0613: experimental-history bookkeeping swept out of the body (annex only)."""
    body_text = _body_before_appendix()
    assert "dispatched 16 models" not in body_text, (
        "dispatch-count bookkeeping ('dispatched 16 models') must not appear "
        "before \\appendix — experimental history lives in the annex (ticket 0613)"
    )
    assert "16-model analysis cohort" not in body_text, (
        "'16-model analysis cohort' bookkeeping must not appear before "
        "\\appendix (ticket 0613)"
    )


def test_dispatch_history_preserved_in_annex() -> None:
    """0613: the swept detail is preserved in the annex, not lost."""
    annex = body().split("\\appendix", 1)
    assert len(annex) == 2, "manuscript has an \\appendix"
    assert "16-model" in annex[1], (
        "the original-16-model baseline detail must be preserved in the annex "
        "(ticket 0613 — swept, not deleted)"
    )


def test_cohort_enumeration_not_repeated_in_exp1_paragraph() -> None:
    """0613.C: cohort facts stated once — the duplicate enumeration is gone."""
    s5 = section("sec:exp1")
    assert "include Claude, DeepSeek, Mistral and Qwen" not in s5, (
        "the Experiment-1 paragraph's redundant cohort enumeration "
        "('include Claude, DeepSeek, Mistral and Qwen at various sizes') must "
        "be gone — the cohort is described once in the summary (ticket 0613.C)"
    )


def test_inline_scoring_methodology_absent() -> None:
    """0614: inline scoring method replaced by a section reference."""
    s5 = section("sec:exp1")
    assert "scored at the cell level for matched rows" not in s5, (
        "inline scoring detail 'scored at the cell level for matched rows' "
        "must be absent from §5 — replaced by a \\ref to the quality section, "
        "detail lives in the annex (ticket 0614)"
    )
    assert "using fuzzy string matching, yielding row-level precision" not in s5, (
        "inline scoring detail 'fuzzy string matching, yielding row-level "
        "precision, recall, and F1' must be absent from §5 (ticket 0614)"
    )


def test_s5_references_quality_section() -> None:
    """0614: §5 carries a reference to the quality-dimensions section."""
    assert "\\ref{sec:quality}" in section("sec:exp1"), (
        "§5 must reference the quality-dimensions section in place of the "
        "removed inline scoring methodology (ticket 0614)"
    )
