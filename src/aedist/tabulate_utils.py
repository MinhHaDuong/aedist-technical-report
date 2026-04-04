"""Shared utilities for tabulation scripts.

Label parsing, model name formatting, and common patterns used by
tabulate_census, tabulate_relances, and tabulate_comparaison.
"""

import re

_RUN_SUFFIX = re.compile(r"-run\d+$")

# Known capitalisations for model name segments
KNOWN_CAPS: dict[str, str] = {
    "gpt": "GPT",
    "glm": "GLM",
    "mimo": "MiMo",
    "deepseek": "DeepSeek",
}


def strip_label(label: str) -> str:
    """Extract model slug from a metrics label.

    'sweep1_census/gpt-5.4-run1' -> 'gpt-5.4'
    'sweep1_census/padme-qwen3.5-122b-run3' -> 'padme-qwen3.5-122b'
    """
    slug = label.rsplit("/", 1)[-1]
    slug = _RUN_SUFFIX.sub("", slug)
    return slug


def titlecase_slug(slug: str) -> str:
    """Title-case each hyphen-separated segment of a slug.

    Uses a lookup for known brand capitalisations (GPT, GLM, DeepSeek...),
    falls back to capitalising the first letter.
    """
    parts = slug.split("-")
    result = []
    for part in parts:
        known = KNOWN_CAPS.get(part.lower())
        if known:
            result.append(known)
        elif part and part[0].isalpha():
            result.append(part[0].upper() + part[1:])
        else:
            result.append(part)
    return "-".join(result)


def format_model_name(slug: str) -> str:
    """Turn a slug into a display name for LaTeX tables.

    Local models (padme-*) get '(L)' suffix with the padme- prefix removed.
    """
    if slug.startswith("padme-"):
        base = slug.removeprefix("padme-")
        return titlecase_slug(base) + " (L)"
    return titlecase_slug(slug)


def median_metric(entries: list[dict], key: str) -> float:
    """Compute median of a metric across entries."""
    import statistics
    return statistics.median(e[key] for e in entries)
