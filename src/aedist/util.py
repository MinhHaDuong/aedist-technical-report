"""Shared utilities for the aedist package."""

import tomllib
import unicodedata
from functools import cache
from pathlib import Path

_GLYPH_METHOD_ALIASES = {
    "naive": "arm1",
    "optimised": "arm2",
}

_GLYPH_BY_METHOD: dict[str, dict[str, object]] = {
    "parametric": {
        "marker": "o",
        "s": 18,
        "facecolors": "auto",
        "edgecolors": "auto",
        "linewidths": 0.8,
    },
    "arm1": {
        "marker": "o",
        "s": 25,
        "facecolors": "none",
        "edgecolors": "auto",
        "linewidths": 1.0,
    },
    "arm2": {
        "marker": "D",
        "s": 20,
        "facecolors": "auto",
        "edgecolors": "auto",
        "linewidths": 0.8,
    },
    "arm3": {
        "marker": "D",
        "s": 25,
        "facecolors": "none",
        "edgecolors": "auto",
        "linewidths": 1.0,
    },
    "arm4": {
        "marker": "D",
        "s": 20,
        "facecolors": "auto",
        "edgecolors": "neutral",
        "linewidths": 1.2,
    },
}

# ── Plot palette (loaded from palette.toml) ──────────────────────────────────

with open(Path(__file__).parent / "palette.toml", "rb") as _f:
    _palette = tomllib.load(_f)

COLOR_MATCHED = _palette["semantic"]["matched"]
COLOR_HALLUC = _palette["semantic"]["halluc"]
COLOR_REFUSAL = _palette["semantic"]["refusal"]
COLOR_ALERT = _palette["semantic"]["alert"]
COLOR_REFERENCE = _palette["semantic"]["reference"]
COLOR_LOCAL = _palette["semantic"]["local_model"]
COLOR_NEUTRAL = _palette["semantic"]["neutral"]
COLOR_ARM_NAIVE = _palette["semantic"]["arm_naive"]
COLOR_ARM_OPTIMISED = _palette["semantic"]["arm_optimised"]
COLOR_IDENTIFIED = _palette["quality"]["identified"]
FAMILY_COLORS = _palette["families"]

# ── Beamer slide figure sizes ────────────────────────────────────────────────
#
# Full-slide figures are included with
# ``\includegraphics[width=\paperwidth,height=\paperheight,keepaspectratio]``.
# When the source figure is wider than 16:9 (ratio > 1.78), ``height=\paperheight``
# wins and the figure renders wider than the slide, so its right edge is clipped
# (the systemic "décalage droite" bug). Keep every full-slide figure at ratio
# ≤ 1.78 by sizing from one of these constants instead of a hardcoded tuple.
SLIDE_FIGSIZE_FULL = (10.0, 5.625)  # exact 16:9 full slide
SLIDE_FIGSIZE_WIDE = (11.2, 6.3)  # 16:9, larger canvas for dense two-panel figures

# Figures placed beside text in a column (width=\textwidth, ~0.55-0.6 of slide).
# A squarer ratio is fine here — the column, not the slide, bounds the width.
SLIDE_FIGSIZE_HALF = (5.5, 4.0)

# Multipanel polar (spider) grids — taller than wide, never décalage-prone.
SLIDE_FIGSIZE_POLAR_2x2 = (10.0, 8.0)

# Single large polar (spider) — one panel filling the slide, taller than wide.
SLIDE_FIGSIZE_POLAR_SINGLE = (8.2, 6.6)

_LANGUAGE_FAMILIES = _palette["language_families"]
_LANG_DIRECT = {
    code: _LANGUAGE_FAMILIES[code]
    for code in _LANGUAGE_FAMILIES
    if isinstance(_LANGUAGE_FAMILIES[code], str)
}
_LANG_PROVIDER_MAP: dict[str, str] = _LANGUAGE_FAMILIES["provider_map"]
_LANG_SLUG_PREFIX_MAP: dict[str, str] = _LANGUAGE_FAMILIES["slug_prefix_map"]
_LANG_FALLBACK = _LANG_DIRECT["fallback"]

_valid_codes = set(_LANG_DIRECT) - {"fallback"}
assert set(_LANG_PROVIDER_MAP.values()) <= _valid_codes, (
    f"palette.toml provider_map maps to unknown family codes: "
    f"{set(_LANG_PROVIDER_MAP.values()) - _valid_codes}"
)
assert set(_LANG_SLUG_PREFIX_MAP.values()) <= _valid_codes, (
    f"palette.toml slug_prefix_map maps to unknown family codes: "
    f"{set(_LANG_SLUG_PREFIX_MAP.values()) - _valid_codes}"
)

_MODEL_FAMILIES = _palette["model_families"]
_MODEL_FAMILY_DIRECT = {
    code: _MODEL_FAMILIES[code]
    for code in _MODEL_FAMILIES
    if isinstance(_MODEL_FAMILIES[code], str)
}
_MODEL_FAMILY_PREFIX_MAP: dict[str, str] = _MODEL_FAMILIES["prefix_map"]
_MODEL_FAMILY_FALLBACK = _MODEL_FAMILY_DIRECT["fallback"]

_mf_valid = set(_MODEL_FAMILY_DIRECT) - {"fallback"}
assert set(_MODEL_FAMILY_PREFIX_MAP.values()) <= _mf_valid, (
    f"palette.toml model_families.prefix_map maps to unknown family codes: "
    f"{set(_MODEL_FAMILY_PREFIX_MAP.values()) - _mf_valid}"
)


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


def model_family_color(model: str) -> str:
    """Return the colorblind-safe hex color for an architectural model family.

    "Architectural family" is the lineage of a model — Claude / GPT / Mistral /
    Qwen / DeepSeek and so on — resolved by longest-prefix match against the
    ``model_families.prefix_map`` table in ``palette.toml``. This is the colour
    axis used by the cost × quality scatter (Figure 2). Distinct from
    :func:`family_color`, which encodes the lab's *country* via the
    language-family table.

    Returns the fallback hue when no prefix matches. Empty input returns
    fallback.
    """
    if not model:
        return _MODEL_FAMILY_FALLBACK

    slug = normalize_model(model).lower()

    best_prefix = ""
    best_family: str | None = None
    for prefix, family in _MODEL_FAMILY_PREFIX_MAP.items():
        if slug.startswith(prefix.lower()) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_family = family
    if best_family and best_family in _MODEL_FAMILY_DIRECT:
        return _MODEL_FAMILY_DIRECT[best_family]

    return _MODEL_FAMILY_FALLBACK


def model_family(model: str) -> str:
    """Return the architectural-family code for *model* (e.g. ``"claude"``).

    Companion to :func:`model_family_color` for legend construction.
    Returns ``"fallback"`` when no prefix matches.
    """
    if not model:
        return "fallback"
    slug = normalize_model(model).lower()
    best_prefix = ""
    best_family: str | None = None
    for prefix, family in _MODEL_FAMILY_PREFIX_MAP.items():
        if slug.startswith(prefix.lower()) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_family = family
    return best_family if best_family else "fallback"


def normalize_model(raw: str) -> str:
    """Strip provider prefix from a model slug: 'openrouter/deepseek-v3' → 'deepseek-v3'."""
    return (raw or "").split("/")[-1]


def glyph_for_method(method: str) -> dict[str, object]:
    """Return canonical scatter kwargs for a method glyph.

    Methods: ``parametric``, ``arm1``, ``arm2``, ``arm3``, ``arm4``.
    For backwards compatibility, ``naive`` maps to ``arm1`` and
    ``optimised`` maps to ``arm2``.

    The returned dict is intended for ``matplotlib.axes.Axes.scatter`` and
    includes marker shape, size, and face/edge color semantics.
    """
    canonical = _GLYPH_METHOD_ALIASES.get(method, method)
    if canonical not in _GLYPH_BY_METHOD:
        msg = f"unknown method glyph: {method!r}"
        raise ValueError(msg)
    glyph = dict(_GLYPH_BY_METHOD[canonical])
    if glyph.get("edgecolors") == "neutral":
        glyph["edgecolors"] = COLOR_NEUTRAL
    return glyph


def glyph_scatter_kwargs(method: str, color: str) -> dict[str, object]:
    """Return scatter kwargs for *method* with placeholder colors resolved."""
    glyph = glyph_for_method(method)
    face = glyph.pop("facecolors", "auto")
    edge = glyph.pop("edgecolors", "auto")
    glyph["facecolors"] = color if face == "auto" else face
    glyph["edgecolors"] = color if edge == "auto" else edge
    return glyph


def glyph_legend_handles(
    methods: list[str],
    color: str = COLOR_NEUTRAL,
    label_overrides: dict[str, str] | None = None,
):
    """Create legend handles with canonical method glyphs.

    The handle labels are the method names as passed in.
    """
    from matplotlib.lines import Line2D

    handles = []
    if label_overrides is None:
        label_overrides = {}
    for method in methods:
        glyph = glyph_for_method(method)
        face = glyph.get("facecolors", "auto")
        edge = glyph.get("edgecolors", "auto")
        markerface = color if face == "auto" else face
        markeredge = color if edge == "auto" else edge
        handles.append(
            Line2D(
                [0],
                [0],
                linestyle="",
                marker=str(glyph["marker"]),
                markersize=max(4.0, float(glyph["s"]) ** 0.5),
                markerfacecolor=markerface,
                markeredgecolor=markeredge,
                markeredgewidth=float(glyph.get("linewidths", 0.8)),
                label=label_overrides.get(method, method),
            )
        )
    return handles


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
