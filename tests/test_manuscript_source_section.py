"""Ticket 0561 — unit tests for the label-keyed section extractor.

``manuscript_source.section(label)`` locates a section by the ``\\label{}``
on its ``\\section``/``\\section*`` heading and slices to the NEXT sectioning
command of any kind (``\\section``, ``\\section*``, ``\\appendix``) or the end
of the body. The label-stability contract (ticket 0560) makes the label the
only structural identifier tests may key on: retitles, reorders, annex-letter
changes, and unlabelled neighbours must not break extraction.

These are pure unit tests on a synthetic document: ``body()`` is
monkeypatched, so they exercise the slicing logic without reading main.tex.
"""

import manuscript_source
import pytest
from manuscript_source import section

# A synthetic normalized body: labelled sections, an unlabelled starred
# section (like the real "Related Work — Methods"), and an \appendix
# boundary followed by annex sections.
SYNTHETIC = (
    "\\section{Introduction}\\label{sec:intro} intro prose. "
    "\\section{Results}\\label{sec:results} results prose with 0.92. "
    "\\section*{Related Work — Methods} methods prose. "
    "\\section{Conclusion}\\label{sec:conclusion} concluding prose. "
    "\\appendix "
    "\\section{Spec}\\label{sec:annex-spec} annex spec prose. "
    "\\section{Extras}\\label{sec:annex-extras} final annex prose."
)


@pytest.fixture
def synthetic_body(monkeypatch):
    monkeypatch.setattr(manuscript_source, "body", lambda: SYNTHETIC)


def test_label_found_returns_heading_to_next_section(synthetic_body):
    text = section("sec:intro")
    assert text.startswith("\\section{Introduction}\\label{sec:intro}")
    assert "intro prose." in text
    assert "results prose" not in text


def test_slice_ends_at_unlabelled_starred_section(synthetic_body):
    """An unlabelled \\section* terminator works for free: the slice ends at
    the next sectioning command of ANY kind, labelled or not."""
    text = section("sec:results")
    assert "results prose with 0.92." in text
    assert "Related Work" not in text
    assert "methods prose" not in text


def test_slice_ends_at_appendix(synthetic_body):
    text = section("sec:conclusion")
    assert "concluding prose." in text
    assert "\\appendix" not in text
    assert "annex spec" not in text


def test_last_section_slices_to_end_of_body(synthetic_body):
    text = section("sec:annex-extras")
    assert text.startswith("\\section{Extras}\\label{sec:annex-extras}")
    assert text.endswith("final annex prose.")


def test_label_absent_raises_clear_error(synthetic_body):
    with pytest.raises(AssertionError, match="sec:nonexistent"):
        section("sec:nonexistent")


def test_label_absent_error_lists_available_labels(synthetic_body):
    with pytest.raises(AssertionError, match="sec:results"):
        section("sec:nonexistent")


def test_figure_label_is_not_a_section(monkeypatch):
    """A \\label that is not attached to a sectioning heading must not match."""
    monkeypatch.setattr(
        manuscript_source,
        "body",
        lambda: (
            "\\section{Only}\\label{sec:only} prose "
            "\\caption{A figure}\\label{fig:thing} more prose."
        ),
    )
    with pytest.raises(AssertionError, match="fig:thing"):
        section("fig:thing")


def test_robust_to_retitle_and_reorder(monkeypatch):
    """The red-step scenario from ticket 0561: retitle a section and swap the
    order of two annexes — labels kept — and extraction still lands on the
    same content. Title- or adjacency-anchored slicing would break here."""
    perturbed = (
        "\\section{Introduction}\\label{sec:intro} intro prose. "
        # Retitled (was "Results"), label kept.
        "\\section{Findings, renamed}\\label{sec:results} results prose with 0.92. "
        "\\section*{Related Work — Methods} methods prose. "
        "\\section{Conclusion}\\label{sec:conclusion} concluding prose. "
        "\\appendix "
        # Annexes swapped: extras now comes first, spec is last.
        "\\section{Extras}\\label{sec:annex-extras} final annex prose. "
        "\\section{Spec}\\label{sec:annex-spec} annex spec prose."
    )
    monkeypatch.setattr(manuscript_source, "body", lambda: perturbed)
    assert "results prose with 0.92." in section("sec:results")
    assert "methods prose" not in section("sec:results")
    extras = section("sec:annex-extras")
    assert "final annex prose." in extras
    assert "annex spec" not in extras
    spec = section("sec:annex-spec")
    assert "annex spec prose." in spec
    assert spec.endswith("annex spec prose.")


def test_real_manuscript_sections_extract(tmp_path):
    """Smoke test on the real main.tex: every body/annex label the adherence
    tests key on is extractable and non-empty."""
    for label in (
        "sec:intro",
        "sec:exp2",
        "sec:fusion",
        "sec:discussion",
        "sec:conclusion",
        "sec:annex-exp2",
    ):
        text = section(label)
        assert f"\\label{{{label}}}" in text
        assert len(text) > 200, f"section {label} suspiciously short"
