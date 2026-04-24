"""Generate base-vs-census LaTeX comparison table.

Compares the minimal 40-word ``census`` prompt against the structured 300-word
``p1_base`` prompt on the models that were run under both arms.  Reports
per-model precision/recall/F1, $\\Delta$F1 = F1$_\\text{base}$ - F1$_\\text{census}$,
mean input-token delta, and a 95 % bootstrap CI on the macro-average $\\Delta$F1.

Aggregation: per-run precision/recall/F1 are computed first, then averaged
across runs (arithmetic mean of per-run metrics, not F1 of mean-P / mean-R).
Applied consistently to both arms.

Inputs
------
Census arm  : ``measurements.jsonl`` rows where ``method == "direct"`` and
              ``method_params.prompt_version == "census"``.
Base arm    : ``experiments/outputs/ablation/direct/p1_base/*.record.json``.

The intersection of models present in both arms is used.  If fewer than two
models intersect, the script exits non-zero with a clear message.

Ticket: 0057 (base vs census analysis).
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path

from .measurements import load
from .schema import RunRecord
from .stats import bootstrap_ci
from .tabulate_utils import format_model_name

log = logging.getLogger(__name__)

_DEFAULT_P1_BASE_DIR = Path("experiments/outputs/ablation/direct/p1_base")
_DEFAULT_OUTPUT = Path("report/inputs/generated/tab_base_vs_census.tex")
_BOOTSTRAP_SEED = 20260411


# ---------------------------------------------------------------------------
# Per-run metrics
# ---------------------------------------------------------------------------


def _prf1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Return (precision, recall, F1) with safe zero handling."""
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def _record_metrics(record: RunRecord) -> tuple[float, float, float, int]:
    """(precision, recall, f1, tokens_in) for a single RunRecord."""
    s = record.result_summary
    tp = s.tp or 0
    fp = s.fp or 0
    fn = s.fn or 0
    p, r, f1 = _prf1(tp, fp, fn)
    tokens_in = record.resource_use.tokens_in or 0
    return p, r, f1, tokens_in


def _load_census_by_model() -> dict[str, list[RunRecord]]:
    records = load(method="direct")
    grouped: dict[str, list[RunRecord]] = {}
    for r in records:
        if r.method_params.prompt_version != "census":
            continue
        grouped.setdefault(r.method_params.model, []).append(r)
    return grouped


def _load_base_by_model(p1_base_dir: Path) -> dict[str, list[RunRecord]]:
    grouped: dict[str, list[RunRecord]] = {}
    if not p1_base_dir.exists():
        return grouped
    for path in sorted(p1_base_dir.glob("*.record.json")):
        data = json.loads(path.read_text())
        record = RunRecord.model_validate(data)
        grouped.setdefault(record.method_params.model, []).append(record)
    return grouped


def _avg_metrics(records: list[RunRecord]) -> dict[str, float]:
    metrics = [_record_metrics(r) for r in records]
    p_vals = [m[0] for m in metrics]
    r_vals = [m[1] for m in metrics]
    f1_vals = [m[2] for m in metrics]
    tok_vals = [m[3] for m in metrics]
    return {
        "precision": statistics.fmean(p_vals),
        "recall": statistics.fmean(r_vals),
        "f1": statistics.fmean(f1_vals),
        "tokens_in_mean": statistics.fmean(tok_vals),
        "n_runs": len(records),
    }


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_table(p1_base_dir: Path | None = None) -> dict:
    """Compute per-model metrics and macro-average $\\Delta$F1 with CI.

    The returned dict has keys ``rows`` (per-model list, sorted by slug),
    ``delta_f1_mean``, ``delta_f1_ci_low``, ``delta_f1_ci_high``, and
    ``model_count``.
    """
    p1_base_dir = p1_base_dir or _DEFAULT_P1_BASE_DIR
    census = _load_census_by_model()
    base = _load_base_by_model(Path(p1_base_dir))

    shared = sorted(set(census.keys()) & set(base.keys()))
    rows = []
    for model in shared:
        c = _avg_metrics(census[model])
        b = _avg_metrics(base[model])
        rows.append(
            {
                "model": model,
                "slug": model.split("/")[-1],
                "p_census": c["precision"],
                "r_census": c["recall"],
                "f1_census": c["f1"],
                "p_base": b["precision"],
                "r_base": b["recall"],
                "f1_base": b["f1"],
                "delta_f1": b["f1"] - c["f1"],
                "delta_tokens_in": b["tokens_in_mean"] - c["tokens_in_mean"],
                "n_census_runs": c["n_runs"],
                "n_base_runs": b["n_runs"],
            }
        )

    deltas = [row["delta_f1"] for row in rows]
    mean, lo, hi = bootstrap_ci(deltas, seed=_BOOTSTRAP_SEED) if deltas else (0.0, 0.0, 0.0)

    return {
        "rows": rows,
        "delta_f1_mean": mean,
        "delta_f1_ci_low": lo,
        "delta_f1_ci_high": hi,
        "model_count": len(rows),
    }


# ---------------------------------------------------------------------------
# LaTeX rendering
# ---------------------------------------------------------------------------


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}\\%"


def _fmt_delta_pct(x: float) -> str:
    sign = "+" if x >= 0 else "$-$"
    return f"{sign}{abs(x) * 100:.1f}"


def _fmt_delta_tokens(x: float) -> str:
    sign = "+" if x >= 0 else "$-$"
    return f"{sign}{abs(x):.0f}"


def render_latex(table: dict) -> str:
    """Render the compute_table() result as a LaTeX tabular."""
    rows = table["rows"]
    n = table["model_count"]

    lines = [
        "% Auto-generated by aedist.tabulate_base_vs_census — do not edit",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Prompt \\emph{base} (300~mots, structuré) \\emph{vs} prompt "
        "\\emph{census} (40~mots, minimal) — moyennes par modèle sur l'intersection "
        "des deux bras.}\\label{tab:base-vs-census}",
        "\\begin{tabular}{@{}lrrrrrrrr@{}}",
        "\\toprule",
        " & \\multicolumn{3}{c}{Census} & \\multicolumn{3}{c}{Base} & & \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}",
        "Modèle & P & R & F1 & P & R & F1 & $\\Delta$F1 (pp) & $\\Delta$tok$_\\text{in}$ \\\\",
        "\\midrule",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        lines.append(
            " & ".join(
                [
                    name,
                    _fmt_pct(row["p_census"]),
                    _fmt_pct(row["r_census"]),
                    _fmt_pct(row["f1_census"]),
                    _fmt_pct(row["p_base"]),
                    _fmt_pct(row["r_base"]),
                    _fmt_pct(row["f1_base"]),
                    _fmt_delta_pct(row["delta_f1"]),
                    _fmt_delta_tokens(row["delta_tokens_in"]),
                ]
            )
            + " \\\\"
        )

    lines.append("\\midrule")
    mean = table["delta_f1_mean"]
    lo = table["delta_f1_ci_low"]
    hi = table["delta_f1_ci_high"]
    macro_cell = f"{_fmt_delta_pct(mean)} [{_fmt_delta_pct(lo)}, {_fmt_delta_pct(hi)}]"
    lines.append(
        "\\multicolumn{7}{r}{\\textit{Macro-moyenne $\\Delta$F1 (IC 95\\,\\% bootstrap)}} & "
        + macro_cell
        + " & \\\\"
    )
    lines.append("\\bottomrule")
    lines.append(
        "\\multicolumn{9}{l}{\\footnotesize\\textit{n{=}"
        + str(n)
        + " modèles dans l'intersection des deux bras~; "
        "underpowered pour inférence générale, valeur illustrative. "
        "Tokens d'entrée = moyenne par run.}} \\\\"
    )
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate base-vs-census comparison LaTeX table")
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Path to write the .tex file (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--p1-base-dir",
        type=Path,
        default=_DEFAULT_P1_BASE_DIR,
        help="Directory containing p1_base *.record.json files",
    )
    args = parser.parse_args(argv)

    table = compute_table(p1_base_dir=args.p1_base_dir)
    n = table["model_count"]
    if n < 2:
        base_dir_exists = args.p1_base_dir.exists()
        msg = (
            f"tabulate_base_vs_census: intersection has only {n} model(s) — "
            "need at least 2 for ΔF1 comparison. "
            f"Census arm loaded from measurements.jsonl; "
            f"base arm loaded from {args.p1_base_dir} (exists={base_dir_exists})."
        )
        print(msg, file=sys.stderr)
        sys.exit(2)

    latex = render_latex(table)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(latex)
    log.info(
        "Wrote %s (%d models, ΔF1 mean=%.4f, CI=[%.4f, %.4f])",
        args.output,
        n,
        table["delta_f1_mean"],
        table["delta_f1_ci_low"],
        table["delta_f1_ci_high"],
    )


if __name__ == "__main__":
    main()
