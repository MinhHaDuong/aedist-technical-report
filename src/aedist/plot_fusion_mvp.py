"""Naive presence fusion MVP: UNION vs ≥2-MODELS rules — §5 discovery gain figure.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Implements two naive presence fusion rules pooling plant detections across
runs and models:
  R1 UNION:      plant included if detected by ≥1 valid run (any model)
  R2 ≥2-MODELS:  plant included if detected by ≥2 distinct models

Both TP (reference identity) and FP (system-only names) are tracked so
precision is meaningful (see ADR-7 and advisor note 2026-06-08).

Regimes evaluated:
  E1   — Exp1 memory-only, SOTA-4 models × 5 runs = 20 valid runs
           (same 4 SOTA models as E2-1D: claude-opus-4.6, gpt-5.5,
           mistral-large-2512, qwen3.7-max)
  E2-1D — Exp2 arm3 (single-turn WITH documents), 4 models × 5 runs = 20 valid runs

Outputs:
  --output-csv    fusion_mvp.csv   — P/R/F1 for each (regime, rule) combination
  --output-macros macros_fusion_mvp.tex — LaTeX macro literals for §5 prose
  --output-figure fig_fusion_mvp.pdf   — bar chart comparing rules × regimes

Usage:
    python -m aedist.plot_fusion_mvp \\
        --records-glob "experiments/outputs/exp1_batch2/*.record.json" \\
        --arm3-dir experiments/derived/arm3_flat \\
        --reference data/reference/vietnam_thermal_plants_v2_classified.csv \\
        --output-csv report/inputs/generated/fusion_mvp.csv \\
        --output-macros report/inputs/generated/macros_fusion_mvp.tex \\
        --output-figure report/inputs/generated/fig_fusion_mvp.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .evaluate import load_plants_csv, plants_from_dicts, reference_plant_count
from .exp1_recognition import load_exp1_recognition
from .metrics import _MATCHED_TYPES
from .reconcile import reconcile
from .schema import MatchType
from .score_ingest import RunLocator, ingest_run
from .util import COLOR_ARM_NAIVE as _COLOR_BEST
from .util import COLOR_MATCHED as _COLOR_UNION
from .util import COLOR_REFERENCE as _COLOR_R2

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SOTA-4 model filter for E1 (must match normalized names from record.json)
# normalize_model() strips provider prefix: 'anthropic/claude-opus-4.6' → 'claude-opus-4.6'
# ---------------------------------------------------------------------------
SOTA_4_MODELS: frozenset[str] = frozenset(
    {
        "claude-opus-4.6",
        "gpt-5.5",
        "mistral-large-2512",
        "qwen3.7-max",
    }
)

# Colors for the three fusion rules, routed through palette.toml via util.
_RULE_COLORS = {
    "best_single": _COLOR_BEST,
    "union": _COLOR_UNION,
    "r2_models": _COLOR_R2,
}

# ---------------------------------------------------------------------------
# Arm3 agent → model name mapping (from arm3_flat JSON metadata)
# ---------------------------------------------------------------------------
_ARM3_AGENTS = ["anthropic", "mistral", "openai", "qwen"]

_ARM3_AGENT_MODEL = {
    "anthropic": "claude-opus-4-6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3.7-max-2026-05-20",
}
_ARM3_RUNS = 5


# ---------------------------------------------------------------------------
# Core data type: per-run detection sets
# ---------------------------------------------------------------------------


@dataclass
class RunDetections:
    """TP and FP detection sets for a single run."""

    model: str
    run: int
    tp_plants: set[str]  # reference_name values for matched entries
    fp_plants: set[str]  # system_name values for SYSTEM_ONLY entries


# ---------------------------------------------------------------------------
# Fused result dataclass (returned by merge rules)
# ---------------------------------------------------------------------------


@dataclass
class FusedSet:
    """Fused detection result with precision/recall/F1 already computed."""

    tp_plants: set[str]
    fp_plants: set[str]
    n_reference: int

    @property
    def recall(self) -> float:
        return len(self.tp_plants) / self.n_reference if self.n_reference else 0.0

    @property
    def precision(self) -> float:
        n_system = len(self.tp_plants) + len(self.fp_plants)
        return len(self.tp_plants) / n_system if n_system else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)


# ---------------------------------------------------------------------------
# Merge rule implementations (pure functions, no I/O)
# ---------------------------------------------------------------------------


def union_fuse(runs: list[dict]) -> "FusedSet":
    """R1 UNION: plant included if detected by ≥1 run (any model).

    Args:
        runs: list of dicts with keys ``model``, ``tp_plants`` (set[str]),
            ``fp_plants`` (set[str]).  ``n_reference`` is NOT required here;
            the caller wraps in :class:`FusedSet`.

    Returns:
        FusedSet with n_reference=0; caller must set n_reference before use.
        (Kept as internal helper; public callers use
        :func:`_fuse_regime` which constructs the FusedSet.)
    """
    tp: set[str] = set()
    fp: set[str] = set()
    for run in runs:
        tp |= run["tp_plants"]
        fp |= run["fp_plants"]
    return FusedSet(tp_plants=tp, fp_plants=fp, n_reference=0)


def at_least_2_models_fuse(runs: list[dict]) -> "FusedSet":
    """R2 ≥2-MODELS: plant included if detected by ≥2 distinct models.

    Two runs from the *same* model count as one.

    Args:
        runs: list of dicts with keys ``model``, ``tp_plants``, ``fp_plants``.

    Returns:
        FusedSet with n_reference=0 (caller sets it).
    """
    # Map plant → set of distinct models that detected it
    tp_models: dict[str, set[str]] = defaultdict(set)
    fp_models: dict[str, set[str]] = defaultdict(set)
    for run in runs:
        model = run["model"]
        for plant in run["tp_plants"]:
            tp_models[plant].add(model)
        for plant in run["fp_plants"]:
            fp_models[plant].add(model)

    tp = {plant for plant, models in tp_models.items() if len(models) >= 2}
    fp = {plant for plant, models in fp_models.items() if len(models) >= 2}
    return FusedSet(tp_plants=tp, fp_plants=fp, n_reference=0)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_e1_runs(records_glob: str, reference_path: Path) -> list[dict]:
    """Load per-run detection sets for E1 (Exp1 memory-only).

    Uses :func:`aedist.exp1_recognition.load_exp1_recognition` to reconcile
    each run once.  Only runs with at least one parsed result row are included
    (valid-run filter).

    Returns:
        List of run dicts compatible with :func:`union_fuse` /
        :func:`at_least_2_models_fuse`.
    """
    data = load_exp1_recognition(records_glob, reference_path)

    # Build tp_plants per (model, run) from recognition cells
    tp_by_run: dict[tuple[str, int], set[str]] = defaultdict(set)
    for cell in data.cells:
        if cell.recognized:
            tp_by_run[(cell.model, cell.run)].add(cell.plant_name)

    runs = []
    for (model, run), fps in data.fp_presence.items():
        if model not in SOTA_4_MODELS:
            log.debug("E1: skipping model %r (not in SOTA_4_MODELS)", model)
            continue
        runs.append(
            {
                "model": model,
                "run": run,
                "tp_plants": tp_by_run.get((model, run), set()),
                "fp_plants": fps,
            }
        )

    n_models = len({r["model"] for r in runs})
    log.info("E1: loaded %d valid runs from %d SOTA-4 models", len(runs), n_models)
    return runs


def _load_arm3_runs(arm3_dir: Path, reference_path: Path) -> list[dict]:
    """Load per-run detection sets for E2-1D (Exp2 arm3, single-turn with docs).

    Reconciles each arm3 run on-the-fly using :func:`score_ingest.ingest_run`
    + :func:`reconcile`.

    Only runs with at least one ingested row are included (valid-run filter).

    Returns:
        List of run dicts compatible with :func:`union_fuse` /
        :func:`at_least_2_models_fuse`.
    """
    reference = load_plants_csv(reference_path)
    runs = []

    for agent in _ARM3_AGENTS:
        model = _ARM3_AGENT_MODEL[agent]
        for run_n in range(1, _ARM3_RUNS + 1):
            locator = RunLocator(arm="arm3", model=model, run=run_n)
            try:
                ingested = ingest_run(locator, arm3_dir=arm3_dir)
            except Exception as exc:
                log.warning("arm3 run %s/%d: skipping (%s)", model, run_n, exc)
                continue

            if not ingested.rows:
                log.warning("arm3 run %s/%d: no rows ingested, skipping", model, run_n)
                continue

            system = plants_from_dicts(ingested.rows)
            entries = reconcile(reference, system)

            tp: set[str] = set()
            fp: set[str] = set()
            for entry in entries:
                if entry.match_type in _MATCHED_TYPES and entry.reference_name:
                    tp.add(entry.reference_name)
                elif entry.match_type == MatchType.SYSTEM_ONLY and entry.system_name:
                    fp.add(entry.system_name)

            runs.append(
                {
                    "model": model,
                    "run": run_n,
                    "tp_plants": tp,
                    "fp_plants": fp,
                }
            )
            log.debug(
                "arm3 %s/run%02d: tp=%d fp=%d",
                model,
                run_n,
                len(tp),
                len(fp),
            )

    log.info("E2-1D: loaded %d valid arm3 runs", len(runs))
    return runs


# ---------------------------------------------------------------------------
# Baseline: best single-model mean F1 (same reconciliation basis)
# ---------------------------------------------------------------------------


def _best_single_model_f1(runs: list[dict], n_reference: int) -> float:
    """Best per-model mean F1 across the run collection.

    Args:
        runs: list of run dicts (model, run, tp_plants, fp_plants).
        n_reference: reference inventory size (from reference_plant_count()).

    Returns:
        Highest per-model mean F1 over all models in the collection.
    """
    f1_by_model: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        tp = len(run["tp_plants"])
        fp = len(run["fp_plants"])
        n_system = tp + fp
        recall = tp / n_reference if n_reference else 0.0
        precision = tp / n_system if n_system else 0.0
        if precision + recall > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = 0.0
        f1_by_model[run["model"]].append(f1)

    if not f1_by_model:
        return 0.0
    return max(
        sum(f1s) / len(f1s) for f1s in f1_by_model.values()
    )


# ---------------------------------------------------------------------------
# Regime analysis
# ---------------------------------------------------------------------------


@dataclass
class RegimeResult:
    """Fusion results for one regime (E1 or E2-1D)."""

    regime: str  # e.g. "E1" or "E2-1D"
    n_runs: int
    n_models: int
    n_reference: int
    best_single_f1: float
    best_single_recall: float
    best_single_precision: float
    # best_single TP/FP are per-run means over the best model's runs (fractional)
    best_single_tp: float
    best_single_fp: float
    union_recall: float
    union_precision: float
    union_f1: float
    union_tp: int  # absolute count from set cardinality
    union_fp: int
    r2_recall: float
    r2_precision: float
    r2_f1: float
    r2_tp: int  # absolute count from set cardinality
    r2_fp: int


def analyze_regime(regime: str, runs: list[dict], reference_path: Path | None = None) -> RegimeResult:
    """Compute fusion metrics for a regime.

    Args:
        regime: Regime name (e.g. "E1" or "E2-1D").
        runs: List of run dicts (model, run, tp_plants, fp_plants).
        reference_path: Path to the reference CSV; defaults to
            VN_THERMAL_PLANTS_RELEASE_CSV when None.  Passed through so
            recall/F1 denominators are consistent with the reference used
            for TP/FP reconciliation.
    """
    n_ref = reference_plant_count(reference_path) if reference_path else reference_plant_count()
    n_models = len({r["model"] for r in runs})

    # Fused sets
    union_result = union_fuse(runs)
    union_result.n_reference = n_ref
    r2_result = at_least_2_models_fuse(runs)
    r2_result.n_reference = n_ref

    # Best single-model
    best_f1 = _best_single_model_f1(runs, n_ref)

    # Compute best single recall/precision/TP/FP at the model level (mean across runs)
    f1_by_model: dict[str, list[float]] = defaultdict(list)
    recall_by_model: dict[str, list[float]] = defaultdict(list)
    prec_by_model: dict[str, list[float]] = defaultdict(list)
    tp_by_model: dict[str, list[float]] = defaultdict(list)
    fp_by_model: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        tp = len(run["tp_plants"])
        fp = len(run["fp_plants"])
        n_sys = tp + fp
        r = tp / n_ref if n_ref else 0.0
        p = tp / n_sys if n_sys else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        f1_by_model[run["model"]].append(f1)
        recall_by_model[run["model"]].append(r)
        prec_by_model[run["model"]].append(p)
        tp_by_model[run["model"]].append(float(tp))
        fp_by_model[run["model"]].append(float(fp))

    best_model = max(f1_by_model, key=lambda m: sum(f1_by_model[m]) / len(f1_by_model[m]))
    best_recall = sum(recall_by_model[best_model]) / len(recall_by_model[best_model])
    best_prec = sum(prec_by_model[best_model]) / len(prec_by_model[best_model])
    # Per-run mean TP/FP for best model (fractional — documented in RegimeResult)
    best_tp = sum(tp_by_model[best_model]) / len(tp_by_model[best_model])
    best_fp = sum(fp_by_model[best_model]) / len(fp_by_model[best_model])

    return RegimeResult(
        regime=regime,
        n_runs=len(runs),
        n_models=n_models,
        n_reference=n_ref,
        best_single_f1=best_f1,
        best_single_recall=best_recall,
        best_single_precision=best_prec,
        best_single_tp=best_tp,
        best_single_fp=best_fp,
        union_recall=union_result.recall,
        union_precision=union_result.precision,
        union_f1=union_result.f1,
        union_tp=len(union_result.tp_plants),
        union_fp=len(union_result.fp_plants),
        r2_recall=r2_result.recall,
        r2_precision=r2_result.precision,
        r2_f1=r2_result.f1,
        r2_tp=len(r2_result.tp_plants),
        r2_fp=len(r2_result.fp_plants),
    )


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


_CSV_FIELDS = [
    "regime",
    "n_runs",
    "n_models",
    "n_reference",
    "rule",
    "recall",
    "precision",
    "f1",
    "tp",
    "fp",
]


def write_csv(results: list[RegimeResult], output: Path) -> None:
    """Write one row per (regime, rule) to a CSV.

    TP/FP for best_single are per-run means (may be fractional).
    TP/FP for union and r2_models are integer set cardinalities.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for res in results:
            for rule, r, p, f1, tp, fp in [
                (
                    "best_single",
                    res.best_single_recall,
                    res.best_single_precision,
                    res.best_single_f1,
                    res.best_single_tp,
                    res.best_single_fp,
                ),
                (
                    "union",
                    res.union_recall,
                    res.union_precision,
                    res.union_f1,
                    res.union_tp,
                    res.union_fp,
                ),
                (
                    "r2_models",
                    res.r2_recall,
                    res.r2_precision,
                    res.r2_f1,
                    res.r2_tp,
                    res.r2_fp,
                ),
            ]:
                writer.writerow(
                    {
                        "regime": res.regime,
                        "n_runs": res.n_runs,
                        "n_models": res.n_models,
                        "n_reference": res.n_reference,
                        "rule": rule,
                        "recall": round(r, 4),
                        "precision": round(p, 4),
                        "f1": round(f1, 4),
                        "tp": round(tp, 1) if isinstance(tp, float) else tp,
                        "fp": round(fp, 1) if isinstance(fp, float) else fp,
                    }
                )
    log.info("Wrote CSV: %s", output)


def write_macros(results: list[RegimeResult], output: Path) -> None:
    """Emit LaTeX macros for §5 prose (generated; guarded by adherence test)."""
    output.parent.mkdir(parents=True, exist_ok=True)

    def _pct(v: float) -> str:
        return f"{round(v * 100, 1)}"

    lines = [
        "% Fusion MVP macros — generated by aedist.plot_fusion_mvp",
        "% DO NOT EDIT — regenerate with: make -f experiments/render.mk fusion-mvp",
        "",
    ]
    for res in results:
        regime_key = res.regime.replace("-", "").lower()  # "e1" or "e21d"
        # best_single TP/FP are per-run means; displayed as integer for prose clarity
        best_tp_int = round(res.best_single_tp)
        best_fp_int = round(res.best_single_fp)
        lines += [
            f"% Regime: {res.regime}",
            rf"\newcommand{{\FusionN{regime_key.upper()}Runs}}{{{res.n_runs}}}",
            rf"\newcommand{{\FusionN{regime_key.upper()}Models}}{{{res.n_models}}}",
            rf"\newcommand{{\FusionBest{regime_key.upper()}F}}{{{_pct(res.best_single_f1)}\%}}",
            rf"\newcommand{{\FusionBest{regime_key.upper()}Recall}}{{{_pct(res.best_single_recall)}\%}}",
            rf"\newcommand{{\FusionBest{regime_key.upper()}Prec}}{{{_pct(res.best_single_precision)}\%}}",
            rf"\newcommand{{\FusionBest{regime_key.upper()}TP}}{{{best_tp_int}}}",
            rf"\newcommand{{\FusionBest{regime_key.upper()}FP}}{{{best_fp_int}}}",
            rf"\newcommand{{\FusionUnion{regime_key.upper()}F}}{{{_pct(res.union_f1)}\%}}",
            rf"\newcommand{{\FusionUnion{regime_key.upper()}Recall}}{{{_pct(res.union_recall)}\%}}",
            rf"\newcommand{{\FusionUnion{regime_key.upper()}Prec}}{{{_pct(res.union_precision)}\%}}",
            rf"\newcommand{{\FusionUnion{regime_key.upper()}TP}}{{{res.union_tp}}}",
            rf"\newcommand{{\FusionUnion{regime_key.upper()}FP}}{{{res.union_fp}}}",
            rf"\newcommand{{\FusionRTwo{regime_key.upper()}F}}{{{_pct(res.r2_f1)}\%}}",
            rf"\newcommand{{\FusionRTwo{regime_key.upper()}Recall}}{{{_pct(res.r2_recall)}\%}}",
            rf"\newcommand{{\FusionRTwo{regime_key.upper()}Prec}}{{{_pct(res.r2_precision)}\%}}",
            rf"\newcommand{{\FusionRTwo{regime_key.upper()}TP}}{{{res.r2_tp}}}",
            rf"\newcommand{{\FusionRTwo{regime_key.upper()}FP}}{{{res.r2_fp}}}",
            "",
        ]

    output.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote macros: %s", output)


def make_figure(results: list[RegimeResult], output: Path) -> None:
    """Bar chart: P/R/F1 for (UNION, ≥2-models, best-single) × regimes."""
    import matplotlib.pyplot as plt

    regimes = [res.regime for res in results]
    n_regimes = len(regimes)
    rules = ["best_single", "union", "r2_models"]
    rule_labels = {"best_single": "Best single\nmodel", "union": "R1 Union", "r2_models": "R2 ≥2 models"}
    rule_colors = _RULE_COLORS  # palette.toml colours, defined at module level

    metrics = ["recall", "precision", "f1"]
    metric_labels = {"recall": "Recall", "precision": "Precision", "f1": "F1"}

    # Look up values per (regime, rule, metric)
    data: dict[tuple[str, str, str], float] = {}
    for res in results:
        for rule, r, p, f1 in [
            ("best_single", res.best_single_recall, res.best_single_precision, res.best_single_f1),
            ("union", res.union_recall, res.union_precision, res.union_f1),
            ("r2_models", res.r2_recall, res.r2_precision, res.r2_f1),
        ]:
            data[(res.regime, rule, "recall")] = r
            data[(res.regime, rule, "precision")] = p
            data[(res.regime, rule, "f1")] = f1

    fig, axes = plt.subplots(1, n_regimes, figsize=(6.0 * n_regimes, 4.5), sharey=True)
    if n_regimes == 1:
        axes = [axes]

    bar_width = 0.22
    x_pos = {m: i * (len(rules) * bar_width + 0.3) for i, m in enumerate(metrics)}

    for ax, res in zip(axes, results, strict=True):
        for r_idx, rule in enumerate(rules):
            xs = [x_pos[m] + r_idx * bar_width for m in metrics]
            ys = [data.get((res.regime, rule, m), 0.0) for m in metrics]
            ax.bar(
                xs,
                ys,
                bar_width,
                label=rule_labels[rule],
                color=rule_colors[rule],
                alpha=0.85,
                zorder=3,
            )
            # Annotate bars with value
            for x, y in zip(xs, ys, strict=True):
                ax.text(x, y + 0.01, f"{y:.2f}", ha="center", va="bottom", fontsize=7)

        ax.set_title(
            f"{res.regime}  ({res.n_runs} runs, {res.n_models} models)",
            fontsize=10,
            fontweight="bold",
        )
        xtick_centers = [
            x_pos[m] + (len(rules) - 1) * bar_width / 2 for m in metrics
        ]
        ax.set_xticks(xtick_centers)
        ax.set_xticklabels([metric_labels[m] for m in metrics], fontsize=9)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Score", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.axhline(0, color="black", linewidth=0.7)
        ax.legend(fontsize=8, loc="upper right")

    fig.suptitle(
        "Naive presence fusion: UNION vs ≥2-models vs best single model",
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote figure: %s", output)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Naive presence fusion MVP: UNION vs ≥2-MODELS — §5 discovery gain figure"
    )
    parser.add_argument(
        "--records-glob",
        default="experiments/outputs/exp1_batch2/*.record.json",
        help="Glob for Exp1 batch2 .record.json files",
    )
    parser.add_argument(
        "--arm3-dir",
        default="experiments/derived/arm3_flat",
        type=Path,
        help="Directory containing arm3 flat files",
    )
    parser.add_argument(
        "--reference",
        default=str(VN_THERMAL_PLANTS_RELEASE_CSV),
        type=Path,
        help="Reference CSV path",
    )
    parser.add_argument(
        "--output-csv",
        default="report/inputs/generated/fusion_mvp.csv",
        type=Path,
        help="Output CSV with P/R/F1 per (regime, rule)",
    )
    parser.add_argument(
        "--output-macros",
        default="report/inputs/generated/macros_fusion_mvp.tex",
        type=Path,
        help="Output LaTeX macros file",
    )
    parser.add_argument(
        "--output-figure",
        default="report/inputs/generated/fig_fusion_mvp.pdf",
        type=Path,
        help="Output PDF figure",
    )
    args = parser.parse_args(argv)

    log.info("Loading E1 runs from glob: %s", args.records_glob)
    e1_runs = _load_e1_runs(args.records_glob, args.reference)

    log.info("Loading E2-1D runs from %s", args.arm3_dir)
    e2_runs = _load_arm3_runs(args.arm3_dir, args.reference)

    results = [
        analyze_regime("E1", e1_runs, args.reference),
        analyze_regime("E2-1D", e2_runs, args.reference),
    ]

    for res in results:
        log.info(
            "%s: best_single F1=%.3f  union F1=%.3f (recall=%.3f prec=%.3f)  "
            "r2 F1=%.3f (recall=%.3f prec=%.3f)",
            res.regime,
            res.best_single_f1,
            res.union_f1,
            res.union_recall,
            res.union_precision,
            res.r2_f1,
            res.r2_recall,
            res.r2_precision,
        )

    write_csv(results, args.output_csv)
    write_macros(results, args.output_macros)
    make_figure(results, args.output_figure)
    log.info("Done.")


if __name__ == "__main__":
    main()
