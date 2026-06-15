"""Adherence guards for ticket 0611: Figure 2 (capability-timeline).

Negative/structural guards only (writing.md polarity rule):

- the Figure 2 caption references ``sec:annex-rollout`` via ``\\ref`` and
  carries no hand-typed "Annex E" (the rollout annex letter shifts when
  other annexes are inserted; the house rule bans literal annex letters);
- the emitter no longer draws the right-margin gray annotation for
  dateless cells (the figure is widened by dropping it).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = REPO_ROOT / "slides" / "manuscript" / "main.tex"
EMITTER = REPO_ROOT / "src" / "aedist" / "plot_capability_timeline.py"


def _fig2_caption() -> str:
    """Return the raw caption block of the capability-timeline figure."""
    text = MANUSCRIPT.read_text(encoding="utf-8")
    # The figure is identified by its label; grab the \caption{...} that
    # carries \label{fig:capability-timeline}.
    m = re.search(
        r"\\caption\{(?P<body>.*?)\}\\label\{fig:capability-timeline\}",
        text,
        re.DOTALL,
    )
    assert m, "fig:capability-timeline caption block not found"
    return m.group("body")


def test_caption_refs_annex_rollout_label() -> None:
    caption = _fig2_caption()
    assert "\\ref{sec:annex-rollout}" in caption, (
        "Figure 2 caption must reference the rollout annex via "
        "\\ref{sec:annex-rollout}"
    )


def test_caption_has_no_hardcoded_annex_letter() -> None:
    caption = _fig2_caption()
    assert not re.search(r"Annex\s+[A-Z]\b", caption), (
        "Figure 2 caption must not hand-type an annex letter (e.g. "
        "'Annex E'); use \\ref{sec:annex-rollout}"
    )


def test_emitter_drops_right_margin_gray_annotation() -> None:
    src = EMITTER.read_text(encoding="utf-8")
    assert 'color="gray"' not in src, (
        "right-margin gray annotation must be removed to widen the figure"
    )
    assert "right_x" not in src, (
        "right-margin annotation x-anchor (right_x) must be gone"
    )
