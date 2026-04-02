"""Generate census results LaTeX table from all_metrics.json.

Usage:
    python -m aedist.tabulate_census \\
        --input results/summary/all_metrics.json \\
        --output report/inputs/generated/tab_census.tex

Reads per-run metrics, groups by model (stripping -runN suffix),
computes medians, and emits a longtable sorted by F1 descending.
Local (Padme) models are marked with (L).
"""

import argparse
import json
import logging
import re
import statistics
from pathlib import Path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Label parsing
# ---------------------------------------------------------------------------

_RUN_SUFFIX = re.compile(r"-run\d+$")


def strip_label(label: str) -> str:
    """Extract model slug from a metrics label.

    'sweep1_census/gpt-5.4-run1' -> 'gpt-5.4'
    'sweep1_census/padme-qwen3.5-122b-run3' -> 'padme-qwen3.5-122b'
    """
    # Strip directory prefix
    slug = label.rsplit("/", 1)[-1]
    # Strip -runN suffix
    slug = _RUN_SUFFIX.sub("", slug)
    return slug


def format_model_name(slug: str) -> str:
    """Turn a slug into a display name for the LaTeX table.

    Local models (padme-*) get '(L)' suffix with the padme- prefix removed.
    All slugs are title-cased with hyphens preserved.
    """
    if slug.startswith("padme-"):
        base = slug.removeprefix("padme-")
        return _titlecase_slug(base) + " (L)"
    return _titlecase_slug(slug)


# Known capitalisations for model name segments
_KNOWN_CAPS: dict[str, str] = {
    "gpt": "GPT",
    "glm": "GLM",
    "mimo": "MiMo",
    "deepseek": "DeepSeek",
}


def _titlecase_slug(slug: str) -> str:
    """Title-case each hyphen-separated segment of a slug.

    Uses a lookup for known brand capitalisations (GPT, GLM, DeepSeek...),
    falls back to capitalising the first letter.
    """
    parts = slug.split("-")
    result = []
    for part in parts:
        known = _KNOWN_CAPS.get(part.lower())
        if known:
            result.append(known)
        elif part and part[0].isalpha():
            result.append(part[0].upper() + part[1:])
        else:
            result.append(part)
    return "-".join(result)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def group_and_summarize(metrics: list[dict]) -> list[dict]:
    """Group metrics by model slug and compute medians.

    Returns a list of dicts sorted by median F1 descending:
        slug, local, f1, precision, coverage, n_matched, n_reference
    """
    groups: dict[str, list[dict]] = {}
    for entry in metrics:
        slug = strip_label(entry["label"])
        groups.setdefault(slug, []).append(entry)

    rows = []
    for slug, entries in groups.items():
        rows.append({
            "slug": slug,
            "local": slug.startswith("padme-"),
            "f1": statistics.median(e["f1"] for e in entries),
            "precision": statistics.median(e["precision"] for e in entries),
            "coverage": statistics.median(e["coverage"] for e in entries),
            "n_matched": int(statistics.median(e["n_matched"] for e in entries)),
            "n_reference": entries[0]["n_reference"],
        })

    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


def generate_census_table(metrics: list[dict]) -> str:
    """Generate a LaTeX longtable from per-run metrics."""
    rows = group_and_summarize(metrics)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrr@{}}",
        "\\caption{Model census: single-shot F1 scores"
        " (median of 3 runs)}\\label{tab:census}\\\\",
        "\\toprule",
        "Model & F1 & Precision & Recall & Matched \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        f1 = f'{row["f1"] * 100:.1f}\\%'
        prec = f'{row["precision"] * 100:.1f}\\%'
        recall = f'{row["coverage"] * 100:.1f}\\%'
        matched = f'{row["n_matched"]}/{row["n_reference"]}'
        lines.append(f"{name} & {f1} & {prec} & {recall} & {matched} \\\\")

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate census results LaTeX table",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to all_metrics.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write tab_census.tex",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    with open(input_path) as f:
        metrics = json.load(f)

    latex = generate_census_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s (%d models)", output_path, len(latex.splitlines()) - 9)


if __name__ == "__main__":
    main()
