"""Shared utilities for tabulation scripts.

Label parsing, model name formatting, and common patterns used by
tabulate_census, tabulate_relances, and tabulate_comparaison.
"""

import re
import statistics
from collections.abc import Callable

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

    'census/gpt-5.4-run1' -> 'gpt-5.4'
    'census/padme-qwen3.5-122b-run3' -> 'padme-qwen3.5-122b'
    """
    slug = label.rsplit("/", 1)[-1]
    slug = _RUN_SUFFIX.sub("", slug)
    slug = slug.replace("--", "-")
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


def group_and_summarize(
    metrics: list[dict],
    filter_fn: Callable[[dict], bool] | None = None,
) -> list[dict]:
    """Group metrics by model slug and compute medians.

    Args:
        metrics: List of per-run metric dicts (must have 'label', 'f1', etc.).
        filter_fn: Optional callable(entry) -> bool to pre-filter entries.

    Returns a list of dicts sorted by median F1 descending:
        slug, f1, precision, coverage, n_matched, n_reference
    """
    groups: dict[str, list[dict]] = {}
    for entry in metrics:
        if filter_fn and not filter_fn(entry):
            continue
        slug = strip_label(entry["label"])
        groups.setdefault(slug, []).append(entry)

    rows = []
    for slug, entries in groups.items():
        f1_values = [e["f1"] for e in entries]
        rows.append({
            "slug": slug,
            "f1": statistics.median(f1_values),
            "precision": statistics.median(e["precision"] for e in entries),
            "coverage": statistics.median(e["coverage"] for e in entries),
            "n_matched": int(statistics.median(e["n_matched"] for e in entries)),
            "n_reference": entries[0]["n_reference"],
            "_f1_values": f1_values,
        })

    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


def group_and_summarize_with_stats(
    metrics: list[dict],
    filter_fn: Callable[[dict], bool] | None = None,
) -> list[dict]:
    """Group metrics by model slug and compute medians plus spread.

    Delegates to :func:`group_and_summarize` and enriches each row with
    ``f1_values``, ``f1_std``, and ``n_runs`` for statistical reporting.
    """
    rows = group_and_summarize(metrics, filter_fn)
    for row in rows:
        f1_values = row.pop("_f1_values")
        row["f1_values"] = f1_values
        row["f1_std"] = statistics.stdev(f1_values) if len(f1_values) > 1 else 0.0
        row["n_runs"] = len(f1_values)
    return rows
