"""Shared utilities for the aedist package."""

import tomllib
import unicodedata
from pathlib import Path

# ── Plot palette (loaded from palette.toml) ──────────────────────────────────

with open(Path(__file__).parent / "palette.toml", "rb") as _f:
    _palette = tomllib.load(_f)

COLOR_MATCHED = _palette["semantic"]["matched"]
COLOR_HALLUC = _palette["semantic"]["halluc"]
COLOR_REFUSAL = _palette["semantic"]["refusal"]
COLOR_ALERT = _palette["semantic"]["alert"]
COLOR_REFERENCE = _palette["semantic"]["reference"]
FAMILY_COLORS = _palette["families"]


def normalize_model(raw: str) -> str:
    """Strip provider prefix from a model slug: 'openrouter/deepseek-v3' → 'deepseek-v3'."""
    return (raw or "").split("/")[-1]


def strip_diacritics(s: str) -> str:
    """Remove diacritics, keeping base letters.

    Uses NFKD decomposition to split combined characters, then drops
    combining marks.  Also handles Vietnamese Đ/đ (a distinct letter,
    not a diacritic composition).

    Examples: ``"Công suất"`` → ``"Cong suat"``, ``"Điện"`` → ``"Dien"``.
    """
    s = s.replace("\u0110", "D").replace("\u0111", "d")  # Vietnamese Đ/đ
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def parse_number(s: str, *, integer_expected: bool = False) -> float | None:
    """Parse a numeric string with cultural thousands separators.

    Handles Anglo (``1,200.5``), European (``1.200,5``), French space
    (``1 200``), and plain (``600``) formats.  Returns *None* when *s*
    cannot be interpreted as a number.

    Parameters
    ----------
    s:
        Raw string that may contain a formatted number.
    integer_expected:
        Disambiguation hint.  When *True*, a lone dot followed by exactly
        three digits is treated as a thousands separator rather than a
        decimal point (e.g. ``"1.200"`` → 1200 instead of 1.2).
    """
    raw = s.strip().replace("\u00a0", " ").replace(" ", "")
    if not raw:
        return None

    if "," in raw and "." in raw:
        # Both present — the last one is the decimal separator.
        if raw.rfind(",") > raw.rfind("."):
            # European: 1.200,5
            raw = raw.replace(".", "").replace(",", ".")
        else:
            # Anglo: 1,200.5
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]):
            # Thousands separator: 1,200 or 1,200,000
            raw = raw.replace(",", "")
        else:
            # European decimal: 1,5
            raw = raw.replace(",", ".")
    elif "." in raw and integer_expected:
        # Ambiguous: "1.200" could be 1200 or 1.2.
        # With integer_expected, treat .NNN groups as thousands separators.
        parts = raw.split(".")
        if all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")

    try:
        return float(raw)
    except ValueError:
        return None
