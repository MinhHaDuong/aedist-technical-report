"""Unit tests for scripts/translate_slides.py (ticket 0389).

Guards are pure/injectable, so these need no real git or claude binary.
They belong in ``make check-fast``.
"""

from __future__ import annotations

import pytest

from scripts import translate_slides as ts

# ---------------------------------------------------------------------------
# Tier-1 work-loss guards (run BEFORE any claude call or write)
# ---------------------------------------------------------------------------


def test_aborts_when_fr_dirty(monkeypatch):
    """A dirty/untracked FR trips Tier-1 #2: never call claude, never write."""
    monkeypatch.setattr(ts, "fr_is_committed", lambda p: False)
    monkeypatch.setattr(ts, "en_at_least_as_new", lambda en, fr: True)
    called = []
    monkeypatch.setattr(ts, "run_claude", lambda *a, **k: called.append(1) or "x")
    with pytest.raises(ts.TranslationAborted):
        ts.translate(en="slides/slides-en.tex", fr="slides/slides.tex")
    assert called == []  # claude never invoked when a Tier-1 guard trips


def test_aborts_when_fr_newer_than_en(monkeypatch):
    """FR committed strictly newer than EN trips Tier-1 #1 (anteriority)."""
    monkeypatch.setattr(ts, "fr_is_committed", lambda p: True)
    monkeypatch.setattr(ts, "en_at_least_as_new", lambda en, fr: False)
    called = []
    monkeypatch.setattr(ts, "run_claude", lambda *a, **k: called.append(1) or "x")
    with pytest.raises(ts.TranslationAborted):
        ts.translate(en="slides/slides-en.tex", fr="slides/slides.tex")
    assert called == []


def test_git_error_fails_closed(monkeypatch):
    """A git error inside a guard aborts (fail-closed), never proceeds."""

    def boom(*a, **k):
        raise ts.GitError("not a repo")

    monkeypatch.setattr(ts, "fr_is_committed", boom)
    with pytest.raises(ts.TranslationAborted):
        ts.translate(en="slides/slides-en.tex", fr="slides/slides.tex")


# ---------------------------------------------------------------------------
# Tier-2 correctness guards (run AFTER claude returns, BEFORE write)
# ---------------------------------------------------------------------------


def test_rejects_structural_drift(monkeypatch, tmp_path):
    """A valid-looking deck that dropped every frame must not be written."""
    fr = tmp_path / "slides.tex"
    fr.write_text("OLD FR")
    monkeypatch.setattr(ts, "fr_is_committed", lambda p: True)
    monkeypatch.setattr(ts, "en_at_least_as_new", lambda en, fr: True)
    # claude drops every frame / leaves a valid-but-wrong deck.
    monkeypatch.setattr(
        ts,
        "run_claude",
        lambda *a, **k: r"\documentclass{beamer}\begin{document}\end{document}",
    )
    with pytest.raises(ts.TranslationAborted):
        ts.translate(en="slides/slides-en.tex", fr=str(fr))
    assert fr.read_text() == "OLD FR"  # untouched on a failed correctness check


def test_looks_like_deck_rejects_markdown_fence():
    bad = "```latex\n\\documentclass{beamer}\n\\end{document}\n```"
    with pytest.raises(ts.TranslationAborted):
        ts.check_looks_like_deck(bad)


def test_looks_like_deck_rejects_leading_prose():
    bad = "Here is the translated deck:\n\\documentclass{beamer}\n\\end{document}"
    with pytest.raises(ts.TranslationAborted):
        ts.check_looks_like_deck(bad)


def test_length_floor_rejects_truncation():
    en = "x" * 1000
    fr = "x" * 500  # 50% < 80% floor
    with pytest.raises(ts.TranslationAborted):
        ts.check_length_floor(fr, en)


def test_structural_invariants_pass_on_parallel_decks():
    """Identical scaffolding (frames + paths + labels) must validate."""
    deck = (
        r"\documentclass{beamer}\begin{document}"
        r"\begin{frame}\includegraphics{a.pdf}\label{f1}\end{frame}"
        r"\begin{frame}\input{b.tex}\end{frame}"
        r"\end{document}"
    )
    # Same structure, different prose — must not raise.
    ts.check_structural_invariants(deck, deck + "% une note")


def test_structural_invariants_reject_translated_label():
    en = r"\begin{frame}\label{intro}\end{frame}"
    fr = r"\begin{frame}\label{introduction}\end{frame}"  # \label was localized
    with pytest.raises(ts.TranslationAborted):
        ts.check_structural_invariants(en, fr)


# ---------------------------------------------------------------------------
# Deterministic include-path remap (code owns localization, not the model)
# ---------------------------------------------------------------------------


def test_remap_strips_en_suffix_on_paths():
    src = (
        r"\includegraphics[width=1cm]{../report/inputs/generated/fig_x_en.pdf}"
        r"\input{inputs/tab_exp2_2x2_en.tex}"
    )
    out = ts.remap_include_paths(src)
    assert "fig_x.pdf" in out
    assert "tab_exp2_2x2.tex" in out
    assert "_en.pdf" not in out
    assert "_en.tex" not in out


def test_remap_leaves_non_en_paths_untouched():
    src = r"\includegraphics{inputs/logo-cired.pdf}\input{macros.tex}"
    assert ts.remap_include_paths(src) == src


# ---------------------------------------------------------------------------
# CLI surface (source-inspection per the coding-python CLI-flag rule)
# ---------------------------------------------------------------------------


def test_parser_exposes_dry_run_and_compile_but_no_from_to():
    parser = ts.build_parser()
    opts = {s for action in parser._actions for s in action.option_strings}
    assert "--dry-run" in opts
    assert "--compile" in opts
    assert "--show-diff" in opts
    # A generic --from/--to would let an arg swap clobber the source of truth.
    assert "--from" not in opts
    assert "--to" not in opts
