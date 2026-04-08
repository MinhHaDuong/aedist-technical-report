"""Shared utilities for the aedist package."""


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
