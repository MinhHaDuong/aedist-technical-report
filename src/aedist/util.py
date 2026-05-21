"""Shared utilities for the aedist package."""

import tomllib
import unicodedata
from functools import cache
from pathlib import Path

# ── Plot palette (loaded from palette.toml) ──────────────────────────────────

with open(Path(__file__).parent / "palette.toml", "rb") as _f:
    _palette = tomllib.load(_f)

COLOR_MATCHED = _palette["semantic"]["matched"]
COLOR_HALLUC = _palette["semantic"]["halluc"]
COLOR_REFUSAL = _palette["semantic"]["refusal"]
COLOR_ALERT = _palette["semantic"]["alert"]
COLOR_REFERENCE = _palette["semantic"]["reference"]
COLOR_LOCAL = _palette["semantic"]["local_model"]
COLOR_IDENTIFIED = _palette["quality"]["identified"]
FAMILY_COLORS = _palette["families"]

_LANGUAGE_FAMILIES = _palette["language_families"]
_LANG_DIRECT = {
    code: _LANGUAGE_FAMILIES[code]
    for code in _LANGUAGE_FAMILIES
    if isinstance(_LANGUAGE_FAMILIES[code], str)
}
_LANG_PROVIDER_MAP: dict[str, str] = _LANGUAGE_FAMILIES["provider_map"]
_LANG_SLUG_PREFIX_MAP: dict[str, str] = _LANGUAGE_FAMILIES["slug_prefix_map"]
_LANG_FALLBACK = _LANG_DIRECT["fallback"]


@cache
def _provider_for_model(slug: str) -> str | None:
    """Resolve the registry ``provider`` for a normalized model slug.

    Looks up ``experiments/models.yaml`` once and caches. Returns *None* when
    the slug is unknown (local-only models, hand-typed scaling-curve labels).
    Import is deferred to avoid a top-level cycle with ``harness``.
    """
    from .harness import load_models  # local import: harness imports util

    registry_path = Path(__file__).resolve().parent.parent.parent / "experiments" / "models.yaml"
    if not registry_path.exists():
        return None
    for entry in load_models(str(registry_path)):
        if normalize_model(entry.get("name", "")) == slug:
            return entry.get("provider")
    return None


def family_color(model_or_family: str) -> str:
    """Return the colorblind-safe hex color for a language family.

    Accepts either a family code (``"EN"``, ``"FR"``, ``"ZH"``) or a model
    slug. For slugs, resolves the family via, in order:

    1. The model registry ``provider`` field (canonical source of truth).
    2. The provider→family map in ``palette.toml``.
    3. A longest-prefix match against the slug-prefix fallback table —
       used for raw slugs that never reach the registry (local Ollama
       runs, the scaling-curve hand-typed entries).

    Returns the fallback hue when no rule matches. The returned value is a
    matplotlib-acceptable hex string (``"#RRGGBB"``).
    """
    if not model_or_family:
        return _LANG_FALLBACK

    # Direct family code (case-insensitive for two-letter codes).
    key = model_or_family.upper() if len(model_or_family) <= 4 else model_or_family
    if key in _LANG_DIRECT and key != "fallback":
        return _LANG_DIRECT[key]

    slug = normalize_model(model_or_family).lower()

    provider = _provider_for_model(normalize_model(model_or_family))
    if provider and provider in _LANG_PROVIDER_MAP:
        family = _LANG_PROVIDER_MAP[provider]
        if family in _LANG_DIRECT:
            return _LANG_DIRECT[family]

    best_prefix = ""
    best_family: str | None = None
    for prefix, family in _LANG_SLUG_PREFIX_MAP.items():
        if slug.startswith(prefix.lower()) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_family = family
    if best_family and best_family in _LANG_DIRECT:
        return _LANG_DIRECT[best_family]

    return _LANG_FALLBACK


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
