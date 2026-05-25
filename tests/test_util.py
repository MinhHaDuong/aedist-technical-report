"""Tests for aedist.util — shared utilities."""

import pytest

from aedist.util import (
    glyph_for_method,
    glyph_legend_handles,
    glyph_scatter_kwargs,
    parse_number,
    strip_diacritics,
)


@pytest.mark.parametrize(
    "s, integer_expected, expected",
    [
        # === Default (integer_expected=False) ===
        # Anglo thousands
        ("1,200", False, 1200.0),
        ("1,200,000", False, 1200000.0),
        ("1,200.5", False, 1200.5),
        # European (unambiguous: both . and , present)
        ("1.200,5", False, 1200.5),
        # French space
        ("1 200", False, 1200.0),
        ("\u00a01\u00a0200", False, 1200.0),  # NBSP
        # Plain
        ("600", False, 600.0),
        ("600.0", False, 600.0),
        ("0", False, 0.0),
        (".5", False, 0.5),
        # European decimal (comma, not thousands)
        ("1,5", False, 1.5),
        ("0,75", False, 0.75),
        # Ambiguous lone dot — default treats as decimal
        ("1.200", False, 1.2),
        # Negative
        ("-100", False, -100.0),
        ("-1,200.5", False, -1200.5),
        # Leading/trailing whitespace
        ("  600  ", False, 600.0),
        # Edge / invalid
        ("", False, None),
        ("  ", False, None),
        ("abc", False, None),
        ("N/A", False, None),
        ("1_000", False, 1000.0),  # Python float() accepts underscores
        # === integer_expected=True ===
        # Ambiguous lone dot with 3-digit groups → thousands
        ("1.200", True, 1200.0),
        ("1.200.000", True, 1200000.0),
        # Lone dot NOT 3-digit group → still decimal
        ("1.20", True, 1.2),
        ("1.2", True, 1.2),
        # Everything else same as default
        ("1,200", True, 1200.0),
        ("600", True, 600.0),
        ("1.200,5", True, 1200.5),
    ],
    ids=[
        "anglo-1200",
        "anglo-1200000",
        "anglo-1200.5",
        "euro-1200.5",
        "french-space",
        "french-nbsp",
        "plain-600",
        "plain-600.0",
        "plain-0",
        "plain-.5",
        "euro-decimal-1.5",
        "euro-decimal-0.75",
        "ambiguous-dot-default",
        "negative",
        "negative-anglo",
        "whitespace",
        "empty",
        "spaces-only",
        "letters",
        "na",
        "python-underscores",
        "int-dot-thousands",
        "int-dot-millions",
        "int-dot-not-3digits",
        "int-dot-1digit",
        "int-anglo",
        "int-plain",
        "int-euro-both",
    ],
)
def test_parse_number(s: str, integer_expected: bool, expected: float | None) -> None:
    result = parse_number(s, integer_expected=integer_expected)
    if expected is None:
        assert result is None, f"Expected None for {s!r}, got {result}"
    else:
        assert result == pytest.approx(expected), f"Expected {expected} for {s!r}, got {result}"


# ---------------------------------------------------------------------------
# strip_diacritics
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "s, expected",
    [
        # ASCII passthrough
        ("Power Plant", "Power Plant"),
        ("hello", "hello"),
        ("", ""),
        # Accented Latin
        ("Plántà", "Planta"),
        ("café", "cafe"),
        ("naïve", "naive"),
        ("über", "uber"),
        ("résumé", "resume"),
        # Vietnamese vowels
        ("Công suất", "Cong suat"),
        ("Năng lượng", "Nang luong"),
        ("Tỉnh", "Tinh"),
        ("Trạng thái", "Trang thai"),
        # Vietnamese Đ/đ (distinct letter, not a composition)
        ("Điện", "Dien"),
        ("điện", "dien"),
        ("Đồng Nai", "Dong Nai"),
        # Mixed
        ("Hà Tĩnh", "Ha Tinh"),
        ("Quảng Ninh", "Quang Ninh"),
        ("Sơn La", "Son La"),
        # Numbers and punctuation preserved
        ("600 MWe", "600 MWe"),
        ("(2026-04-08)", "(2026-04-08)"),
        # Other scripts — non-Latin characters are kept (no transliteration)
        ("日本語", "日本語"),
    ],
    ids=[
        "ascii-phrase",
        "ascii-word",
        "empty",
        "latin-accent",
        "cafe",
        "naive-diaeresis",
        "uber-umlaut",
        "resume-acute",
        "vn-cong-suat",
        "vn-nang-luong",
        "vn-tinh",
        "vn-trang-thai",
        "vn-dien-upper",
        "vn-dien-lower",
        "vn-dong-nai",
        "vn-ha-tinh",
        "vn-quang-ninh",
        "vn-son-la",
        "numbers-preserved",
        "punctuation-preserved",
        "non-latin-kept",
    ],
)
def test_strip_diacritics(s: str, expected: str) -> None:
    assert strip_diacritics(s) == expected


@pytest.mark.parametrize(
    "method, marker, size, open_face",
    [
        ("parametric", "o", 18, False),
        ("arm1", "o", 25, True),
        ("arm2", "D", 20, False),
        ("arm3", "D", 25, True),
        ("arm4", "D", 20, False),
        ("naive", "o", 25, True),
        ("optimised", "D", 20, False),
    ],
)
def test_glyph_for_method(method: str, marker: str, size: int, open_face: bool) -> None:
    glyph = glyph_for_method(method)
    assert glyph["marker"] == marker
    assert glyph["s"] == size
    if open_face:
        assert glyph["facecolors"] == "none"
    else:
        assert glyph["facecolors"] != "none"


def test_glyph_for_method_unknown() -> None:
    with pytest.raises(ValueError):
        glyph_for_method("unknown")


def test_glyph_legend_handles_roundtrip() -> None:
    handles = glyph_legend_handles(["parametric", "arm1", "arm4"])
    assert len(handles) == 3
    labels = [h.get_label() for h in handles]
    assert labels == ["parametric", "arm1", "arm4"]


def test_glyph_scatter_kwargs_resolve_auto_colours() -> None:
    kw = glyph_scatter_kwargs("arm2", "#112233")
    assert kw["facecolors"] == "#112233"
    assert kw["edgecolors"] == "#112233"

    kw_open = glyph_scatter_kwargs("arm1", "#445566")
    assert kw_open["facecolors"] == "none"
    assert kw_open["edgecolors"] == "#445566"
