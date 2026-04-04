"""Generate multi-turn relances LaTeX table from all_metrics.json.

Usage:
    python -m aedist.tabulate_relances \\
        --input results/summary/all_metrics.json \\
        --output report/inputs/generated/tab_relances.tex

Reads per-run metrics from sweep2_multiturn, groups by model (stripping
-runN suffix), computes medians, and emits a longtable showing how plant
count progresses across turns for each model.
"""

import argparse
import json
import logging
import re
import statistics
from pathlib import Path

log = logging.getLogger(__name__)

_RUN_SUFFIX = re.compile(r"-run\d+$")
_MULTITURN_PREFIX = "sweep2_multiturn/"


def strip_label(label: str) -> str:
    """Extract model slug from a metrics label.

    'sweep2_multiturn/gpt-5.4-run1' -> 'gpt-5.4'
    """
    slug = label.rsplit("/", 1)[-1]
    slug = _RUN_SUFFIX.sub("", slug)
    return slug


def is_multiturn(entry: dict) -> bool:
    """True if metrics entry comes from a multiturn sweep."""
    return entry.get("label", "").startswith(_MULTITURN_PREFIX)


# Known capitalisations for model name segments
_KNOWN_CAPS: dict[str, str] = {
    "gpt": "GPT",
    "glm": "GLM",
    "mimo": "MiMo",
    "deepseek": "DeepSeek",
}


def _titlecase_slug(slug: str) -> str:
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


def format_model_name(slug: str) -> str:
    if slug.startswith("padme-"):
        base = slug.removeprefix("padme-")
        return _titlecase_slug(base) + " (L)"
    return _titlecase_slug(slug)


def group_and_summarize(metrics: list[dict]) -> list[dict]:
    """Group multiturn metrics by model slug and compute medians.

    Returns a list of dicts sorted by median F1 descending:
        slug, f1, precision, coverage, n_matched, n_reference
    """
    mt_entries = [e for e in metrics if is_multiturn(e)]
    if not mt_entries:
        return []

    groups: dict[str, list[dict]] = {}
    for entry in mt_entries:
        slug = strip_label(entry["label"])
        groups.setdefault(slug, []).append(entry)

    rows = []
    for slug, entries in groups.items():
        rows.append({
            "slug": slug,
            "f1": statistics.median(e["f1"] for e in entries),
            "precision": statistics.median(e["precision"] for e in entries),
            "coverage": statistics.median(e["coverage"] for e in entries),
            "n_matched": int(statistics.median(e["n_matched"] for e in entries)),
            "n_reference": entries[0]["n_reference"],
        })

    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


def generate_relances_table(metrics: list[dict]) -> str:
    """Generate a LaTeX longtable for multi-turn relances results."""
    rows = group_and_summarize(metrics)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrr@{}}",
        "\\caption{Multi-turn relances: F1 scores"
        " (median of 3 runs)}\\label{tab:relances}\\\\",
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


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate multi-turn relances LaTeX table",
    )
    parser.add_argument("--input", required=True, help="Path to all_metrics.json")
    parser.add_argument("--output", required=True, help="Path to write tab_relances.tex")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    with open(input_path) as f:
        metrics = json.load(f)

    latex = generate_relances_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s (%d models)", output_path, len(group_and_summarize(metrics)))


if __name__ == "__main__":
    main()
