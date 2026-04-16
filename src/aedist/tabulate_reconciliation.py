"""Three-way reference reconciliation: expert vs GEM vs system.

Ticket 0082 — inter-annotator agreement analysis.

1. Reconciles expert reference against GEM reference using the LP matcher.
2. Computes agreement metrics (plant overlap, attribute agreement, Cohen's kappa).
3. Re-evaluates all system outputs against the GEM reference.
4. Computes Spearman rho between model rankings under both references.
5. Emits a LaTeX table summarizing reference agreement and ranking robustness.

Usage:
    python -m aedist.tabulate_reconciliation --output report/inputs/generated/tab_reconciliation.tex
"""

import argparse
import logging
import statistics
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats

from .evaluate import load_plants_csv
from .measurements import SYNTHETIC_SUFFIXES, load, load_metrics
from .metrics import compute_metrics
from .reconcile import reconcile
from .schema import MatchType, RunRecord
from .tabulate_utils import strip_label

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_EXPERT_REF = _REPO_ROOT / "data" / "reference" / "vietnam_thermal_v1.csv"
_GEM_REF = _REPO_ROOT / "data" / "reference" / "gem_thermal.csv"

_MATCHED_TYPES = {
    MatchType.EXACT,
    MatchType.EXACT_CAPACITY_DIFF,
    MatchType.FUZZY,
    MatchType.FUZZY_CAPACITY_DIFF,
}


# ---------------------------------------------------------------------------
# 1. Expert vs GEM reconciliation
# ---------------------------------------------------------------------------


def reconcile_references(
    expert_path: Path = _EXPERT_REF,
    gem_path: Path = _GEM_REF,
) -> dict:
    """Reconcile expert and GEM references, return agreement summary."""
    expert = load_plants_csv(expert_path)
    gem = load_plants_csv(gem_path)

    entries = reconcile(expert, gem)

    matched = [e for e in entries if e.match_type in _MATCHED_TYPES]
    expert_only = [e for e in entries if e.match_type == MatchType.REFERENCE_ONLY]
    gem_only = [e for e in entries if e.match_type == MatchType.SYSTEM_ONLY]

    # Attribute agreement among matched pairs
    fuel_checks = [e.fuel_match for e in matched if e.fuel_match is not None]
    status_checks = [e.status_match for e in matched if e.status_match is not None]
    cap_checks = [e for e in matched if e.match_type in {MatchType.EXACT, MatchType.FUZZY}]

    fuel_agree = sum(fuel_checks) / len(fuel_checks) if fuel_checks else 0.0
    status_agree = sum(status_checks) / len(status_checks) if status_checks else 0.0
    cap_agree = len(cap_checks) / len(matched) if matched else 0.0

    # Cohen's kappa for fuel (binary: agree vs disagree isn't right;
    # we compute it over the fuel categories for matched plants)
    fuel_kappa = _cohens_kappa_fuel(matched)

    return {
        "n_expert": len(expert),
        "n_gem": len(gem),
        "n_matched": len(matched),
        "n_expert_only": len(expert_only),
        "n_gem_only": len(gem_only),
        "fuel_agreement": fuel_agree,
        "status_agreement": status_agree,
        "capacity_agreement": cap_agree,
        "fuel_kappa": fuel_kappa,
        "entries": entries,
    }


def _cohens_kappa_fuel(matched: list) -> float | None:
    """Compute Cohen's kappa for fuel type among matched plant pairs."""
    pairs = [
        (e.reference_fuel, e.system_fuel) for e in matched if e.reference_fuel and e.system_fuel
    ]
    if len(pairs) < 2:
        return None

    # Build category set
    categories = sorted({f for pair in pairs for f in pair})
    cat_idx = {c: i for i, c in enumerate(categories)}
    n = len(categories)

    # Confusion matrix
    matrix = np.zeros((n, n), dtype=int)
    for ref_fuel, sys_fuel in pairs:
        matrix[cat_idx[ref_fuel], cat_idx[sys_fuel]] += 1

    total = matrix.sum()
    if total == 0:
        return None

    p_o = np.trace(matrix) / total  # observed agreement
    row_sums = matrix.sum(axis=1)
    col_sums = matrix.sum(axis=0)
    p_e = (row_sums * col_sums).sum() / (total * total)  # expected agreement

    if p_e == 1.0:
        return 1.0
    return float((p_o - p_e) / (1.0 - p_e))


# ---------------------------------------------------------------------------
# 2. System evaluation against GEM reference
# ---------------------------------------------------------------------------


def _is_quantitative(record: RunRecord) -> bool:
    """Check if a record has quantitative results (not refusal/error/empty).

    Excludes f1==0 runs (typically empty extractions) since they carry no
    ranking signal and would inflate the common-model set with noise.
    """
    s = record.result_summary
    return s.status == "ok" and s.f1 is not None and s.f1 > 0


def _is_synthetic(record: RunRecord) -> bool:
    """Check if a record is a synthetic aggregation."""
    stem = Path(record.result_file).stem if record.result_file else ""
    return any(stem.endswith(suffix) for suffix in SYNTHETIC_SUFFIXES)


def evaluate_against_gem(gem_path: Path = _GEM_REF) -> dict[str, list[float]]:
    """Re-evaluate all system outputs against the GEM reference.

    Returns a dict mapping model slug -> list of F1 scores against GEM.
    """
    gem_plants = load_plants_csv(gem_path)
    records = load()

    gem_f1: dict[str, list[float]] = {}
    for record in records:
        if not _is_quantitative(record) or _is_synthetic(record):
            continue
        if not record.result_file:
            continue

        csv_path = _REPO_ROOT / record.result_file
        if csv_path.suffix != ".csv":
            csv_path = csv_path.with_suffix(".csv")
        if not csv_path.exists():
            continue

        system_plants = load_plants_csv(csv_path)
        if not system_plants:
            continue

        entries = reconcile(gem_plants, system_plants)
        metrics = compute_metrics(entries)

        prompt_version = record.method_params.prompt_version or ""
        stem = Path(record.result_file).stem if record.result_file else record.run_id
        label = f"{prompt_version}/{stem}" if prompt_version else stem
        slug = strip_label(label)

        gem_f1.setdefault(slug, []).append(metrics.f1)

    return gem_f1


def compute_ranking_robustness(
    expert_metrics: list[dict],
    gem_f1: dict[str, list[float]],
) -> dict:
    """Compute Spearman rho between model rankings under expert vs GEM reference.

    Only includes models present in both evaluations with >= 1 run.
    """
    # Expert rankings: group by slug, median F1
    expert_by_slug: dict[str, list[float]] = {}
    for entry in expert_metrics:
        if entry["f1"] is None or entry["f1"] == 0:
            continue
        slug = strip_label(entry["label"])
        # Skip synthetic suffixes
        if any(slug.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        expert_by_slug.setdefault(slug, []).append(entry["f1"])

    expert_medians = {s: statistics.median(vs) for s, vs in expert_by_slug.items()}
    gem_medians = {s: statistics.median(vs) for s, vs in gem_f1.items()}

    common = sorted(set(expert_medians) & set(gem_medians))
    if len(common) < 3:
        return {"n_common": len(common), "spearman_rho": None, "spearman_p": None}

    expert_ranks = [expert_medians[s] for s in common]
    gem_ranks = [gem_medians[s] for s in common]

    rho, p_value = scipy_stats.spearmanr(expert_ranks, gem_ranks)

    return {
        "n_common": len(common),
        "spearman_rho": float(rho),
        "spearman_p": float(p_value),
    }


# ---------------------------------------------------------------------------
# 3. LaTeX table generation
# ---------------------------------------------------------------------------


def generate_latex(ref_agreement: dict, ranking: dict) -> str:
    """Generate LaTeX table for reference reconciliation results."""
    lines = [
        "% Auto-generated by tabulate_reconciliation.py — do not edit",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Inter-annotator agreement: expert reference vs.\\ GEM"
        " (Global Energy Monitor)}\\label{tab:reconciliation}",
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Metric & Value \\\\",
        "\\midrule",
        f"Expert plants & {ref_agreement['n_expert']} \\\\",
        f"GEM plants & {ref_agreement['n_gem']} \\\\",
        f"Matched plants & {ref_agreement['n_matched']} \\\\",
        f"Expert-only & {ref_agreement['n_expert_only']} \\\\",
        f"GEM-only & {ref_agreement['n_gem_only']} \\\\",
        "\\midrule",
        f"Fuel agreement & {ref_agreement['fuel_agreement'] * 100:.1f}\\% \\\\",
        f"Status agreement & {ref_agreement['status_agreement'] * 100:.1f}\\% \\\\",
        f"Capacity agreement$^{{a}}$ & {ref_agreement['capacity_agreement'] * 100:.1f}\\% \\\\",
    ]

    if ref_agreement["fuel_kappa"] is not None:
        lines.append(f"Fuel Cohen's $\\kappa$ & {ref_agreement['fuel_kappa']:.3f} \\\\")

    lines.append("\\midrule")

    if ranking["spearman_rho"] is not None:
        rho = ranking["spearman_rho"]
        p = ranking["spearman_p"]
        sig = ""
        if p < 0.001:
            sig = "$^{***}$"
        elif p < 0.01:
            sig = "$^{**}$"
        elif p < 0.05:
            sig = "$^{*}$"
        lines.append(f"Model ranking Spearman $\\rho$ & {rho:.3f}{sig} \\\\")
        lines.append(f"Models compared & {ranking['n_common']} \\\\")
    else:
        lines.append(f"Models compared & {ranking['n_common']} (insufficient) \\\\")

    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "",
            "\\smallskip{\\footnotesize $^{a}$Fraction of matched plants with"
            " identical capacity (within LP matcher tolerance).}",
            "\\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Three-way reference reconciliation (expert vs GEM vs system)",
    )
    parser.add_argument("--output", required=True, help="Path to write tab_reconciliation.tex")
    parser.add_argument(
        "--expert-ref",
        type=Path,
        default=_EXPERT_REF,
        help="Path to expert reference CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--gem-ref",
        type=Path,
        default=_GEM_REF,
        help="Path to GEM reference CSV (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)

    # Step 1: Expert vs GEM
    log.info("Reconciling expert vs GEM references...")
    ref_agreement = reconcile_references(args.expert_ref, args.gem_ref)
    log.info(
        "Matched: %d, Expert-only: %d, GEM-only: %d",
        ref_agreement["n_matched"],
        ref_agreement["n_expert_only"],
        ref_agreement["n_gem_only"],
    )
    log.info(
        "Fuel agreement: %.1f%%, Status agreement: %.1f%%, Capacity agreement: %.1f%%",
        ref_agreement["fuel_agreement"] * 100,
        ref_agreement["status_agreement"] * 100,
        ref_agreement["capacity_agreement"] * 100,
    )
    if ref_agreement["fuel_kappa"] is not None:
        log.info("Fuel Cohen's kappa: %.3f", ref_agreement["fuel_kappa"])

    # Step 2: Re-evaluate system outputs against GEM
    log.info("Re-evaluating system outputs against GEM reference...")
    gem_f1 = evaluate_against_gem(args.gem_ref)
    log.info("Evaluated %d model slugs against GEM", len(gem_f1))

    # Step 3: Ranking robustness
    expert_metrics = load_metrics()
    ranking = compute_ranking_robustness(expert_metrics, gem_f1)
    if ranking["spearman_rho"] is not None:
        log.info(
            "Spearman rho: %.3f (p=%.4f) across %d models",
            ranking["spearman_rho"],
            ranking["spearman_p"],
            ranking["n_common"],
        )
    else:
        log.info("Insufficient common models for ranking comparison (%d)", ranking["n_common"])

    # Step 4: Generate LaTeX
    latex = generate_latex(ref_agreement, ranking)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
