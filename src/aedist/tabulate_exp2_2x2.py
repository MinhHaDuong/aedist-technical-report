"""Exp2 2x2 factorial table: F1 and cost across query-mode x documents.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

The four Exp2 arms form a 2x2 factorial:

                 | without docs      | with docs
    -------------+-------------------+-----------------
    single query | naive   (arm1)    | arm3
    multi-turn   | optimised (arm2)  | arm4

Aggregation treats the **agent** (model family) as the unit of replication, not
the individual run:

  Level 1 collapses the runs of each (agent, arm) to a mean -- F1 over the
  scored runs, cost over the runs that produced cost -- plus a coverage count.

  Level 2 builds the 2x2 cells by averaging the per-agent means, and reads the
  factor effects as within-agent contrasts averaged across agents. Each effect
  is reported with its directional consistency (k/n agents agreeing in sign),
  never a p-value: with at most four agents the minimum attainable sign/
  permutation p is 1/2^4 ~ 0.06, so significance is structurally unreachable
  and consistency is the honest evidence.

F1 effects are in points (raw scale). Cost effects are multiplicative: the
factorial runs on log(cost) so exponentiated effects read as ratios and the
priciest agent does not dominate the average.

An agent contributes to a contrast only if it has the metric in all four arms.
F1 and cost are assessed independently, so an agent missing F1 in some arm (no
scorable table) can still contribute to the cost contrast if it has cost there.
"""

import argparse
import csv
import json
import logging
import math
import statistics
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)

_ARMS = ("naive", "optimised", "arm3", "arm4")
_AGENT_ORDER = ("anthropic", "mistral", "openai", "qwen")

# Canonical flat-ledger dir name per arm (derived from sota_exp3_arm{N}_batch1).
_ARM_FLAT_DIR_NAME = {
    "naive": "arm1_flat",
    "optimised": "arm2_flat",
    "arm3": "arm3_flat",
    "arm4": "arm4_flat",
}

# (query mode, documents) for each arm.
_ARM_FACTORS: dict[str, tuple[str, str]] = {
    "naive": ("single", "no"),
    "optimised": ("multi", "no"),
    "arm3": ("single", "yes"),
    "arm4": ("multi", "yes"),
}
_ARM_LABEL = {
    "naive": "Single query",
    "optimised": "Multi-turn",
    "arm3": "Single query + docs",
    "arm4": "Multi-turn + docs",
}
_COST_KEYS = ("total_cost_usd", "cost_usd")

_DEFAULT_CROSS_EVAL = Path("experiments/derived/sota_cross_eval.csv")
_DEFAULT_FLAT_ROOT = Path("experiments/derived")
_DEFAULT_OUTPUT_CSV = Path("experiments/derived/tab_exp2_2x2.csv")
_DEFAULT_OUTPUT_TEX = Path("report/inputs/generated/tab_exp2_2x2.tex")
_DEFAULT_EXP1_CROSS_EVAL = Path("experiments/derived/exp1_cross_eval.csv")

# Same lab's flagship in the Exp1 parametric sweep — the memory-only baseline
# the §exp2 prose compares each agent against (ticket 0572). The adherence
# test (tests/test_manuscript_claims_alignment.py) re-derives the same pairs
# by an independent parse with its own copy of this mapping.
_EXP1_FLAGSHIPS = {
    "anthropic": "claude-opus-4.6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3.7-max",
}

# Letters-only macro-name parts (tectonic truncates control words at digits).
_MACRO_AGENT = {
    "anthropic": "Anthropic",
    "mistral": "Mistral",
    "openai": "OpenAI",
    "qwen": "Qwen",
}
_MACRO_ARM = {
    "naive": "Naive",
    "optimised": "Optimised",
    "arm3": "DocsSingle",
    "arm4": "DocsMulti",
}


def _geomean(values: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(v) for v in values))


def load_f1(cross_eval_csv: Path) -> dict[tuple[str, str, str], float | None]:
    """Per-(arm, model, run) F1 from the cross-eval CSV; '' -> None."""
    out: dict[tuple[str, str, str], float | None] = {}
    with cross_eval_csv.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            raw = (row.get("accuracy_f1") or "").strip()
            out[(row["arm"], row["model"], str(row["run"]))] = float(raw) if raw else None
    return out


def load_run_records(cross_eval_csv: Path, flat_root: Path) -> list[dict]:
    """One record per run: arm, agent, model, run, cost, f1 (None if unscored)."""
    f1_lookup = load_f1(cross_eval_csv)
    records: list[dict] = []
    for arm in _ARMS:
        arm_dir = flat_root / _ARM_FLAT_DIR_NAME[arm]
        for json_path in sorted(arm_dir.glob("*_run*.json")):
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            agent = meta.get("agent")
            model = meta.get("model")
            run = meta.get("run")
            if agent is None or model is None or run is None:
                continue
            cost = next((meta[k] for k in _COST_KEYS if meta.get(k) is not None), None)
            records.append(
                {
                    "arm": arm,
                    "agent": agent,
                    "model": model,
                    "run": str(run),
                    "cost": float(cost) if cost is not None else None,
                    "f1": f1_lookup.get((arm, model, str(run))),
                }
            )
    return records


def collapse_runs(records: list[dict]) -> dict[tuple[str, str], dict]:
    """Collapse runs to per-(agent, arm) means + coverage (Level 1)."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in records:
        groups[(rec["agent"], rec["arm"])].append(rec)
    collapsed: dict[tuple[str, str], dict] = {}
    for key, recs in groups.items():
        f1s = [r["f1"] for r in recs if r["f1"] is not None]
        costs = [r["cost"] for r in recs if r["cost"] is not None]
        collapsed[key] = {
            "f1_mean": statistics.fmean(f1s) if f1s else None,
            "n_f1": len(f1s),
            "n_total": len(recs),
            "cost_mean": statistics.fmean(costs) if costs else None,
        }
    return collapsed


def _agent_arm_values(collapsed: dict, metric: str) -> dict[str, dict[str, float]]:
    vals: dict[str, dict[str, float]] = defaultdict(dict)
    for (agent, arm), cell in collapsed.items():
        if cell[metric] is not None:
            vals[agent][arm] = cell[metric]
    return vals


def factor_effects(collapsed: dict, metric: str, *, log_scale: bool) -> dict:
    """Within-agent factorial contrasts averaged across complete-coverage agents.

    Returns one entry per effect (docs, mode, interaction) with: the mean
    effect (points for F1, a multiplicative ratio for log-scale cost), the
    per-agent deltas, and directional consistency k/n.
    """
    vals = _agent_arm_values(collapsed, metric)
    complete = {a: v for a, v in vals.items() if all(arm in v for arm in _ARMS)}

    def fwd(x: float) -> float:
        return math.log(x) if log_scale else x

    contrasts = {
        "docs": lambda v: (
            (fwd(v["arm3"]) + fwd(v["arm4"])) / 2 - (fwd(v["naive"]) + fwd(v["optimised"])) / 2
        ),
        "mode": lambda v: (
            (fwd(v["optimised"]) + fwd(v["arm4"])) / 2 - (fwd(v["naive"]) + fwd(v["arm3"])) / 2
        ),
        "interaction": lambda v: (
            (fwd(v["arm4"]) - fwd(v["arm3"])) - (fwd(v["optimised"]) - fwd(v["naive"]))
        ),
    }

    out: dict[str, dict] = {}
    for name, fn in contrasts.items():
        per_agent = {a: fn(v) for a, v in complete.items()}
        deltas = list(per_agent.values())
        mean = statistics.fmean(deltas) if deltas else None
        out[name] = {
            "mean": mean,
            "effect": (math.exp(mean) if log_scale else mean) if mean is not None else None,
            "per_agent": per_agent,
            "k_positive": sum(1 for d in deltas if d > 0),
            "n": len(deltas),
            "agents": sorted(complete),
        }
    return out


def cell_table(collapsed: dict) -> dict[str, dict]:
    """The four 2x2 cells: F1 mean+-sd over agents, coverage, cost ratio vs naive."""
    f1vals = _agent_arm_values(collapsed, "f1_mean")
    costvals = _agent_arm_values(collapsed, "cost_mean")
    cells: dict[str, dict] = {}
    for arm in _ARMS:
        agent_f1 = [v[arm] for v in f1vals.values() if arm in v]
        cov_num = sum(collapsed[(a, arm)]["n_f1"] for a in _AGENT_ORDER if (a, arm) in collapsed)
        cov_den = sum(
            collapsed[(a, arm)]["n_total"] for a in _AGENT_ORDER if (a, arm) in collapsed
        )
        ratios = [
            v[arm] / v["naive"] for v in costvals.values() if arm in v and v.get("naive", 0) > 0
        ]
        abs_costs = [v[arm] for v in costvals.values() if arm in v]
        cells[arm] = {
            "f1_mean": statistics.fmean(agent_f1) if agent_f1 else None,
            "f1_sd": statistics.pstdev(agent_f1) if len(agent_f1) > 1 else 0.0,
            "n_agents_f1": len(agent_f1),
            "coverage": (cov_num, cov_den),
            "cost_ratio": _geomean(ratios) if ratios else None,
            "cost_abs": statistics.fmean(abs_costs) if abs_costs else None,
        }
    return cells


def _fmt_f1(cell: dict) -> str:
    if cell["f1_mean"] is None:
        return "--"
    return f"{cell['f1_mean']:.3f} $\\pm$ {cell['f1_sd']:.3f}"


def _fmt_cost(cell: dict) -> str:
    if cell["cost_ratio"] is None:
        return "--"
    return f"{cell['cost_ratio']:.2f}$\\times$ (\\${cell['cost_abs']:.2f})"


# Structural labels per language. Numbers stay locale-neutral (decimal point).
_TEX_LABELS = {
    "en": {
        "without": "Without docs",
        "with": "With docs",
        "single": "Single query",
        "multi": "Multi-turn",
        "effects": "Factor effects (within-agent, mean; k/n agents same sign)",
        "f1_col": "F1 (points)",
        "cost_col": "Cost (ratio)",
        "docs": "Documents",
        "mode": "Query mode (multi$-$single)",
        "interaction": "Interaction",
    },
    "fr": {
        "without": "Sans documents",
        "with": "Avec documents",
        "single": "Requête unique",
        "multi": "Multi-tours",
        "effects": "Effets (intra-modèle, moyenne ; $k/n$ agents même signe)",
        "f1_col": "F1 (points)",
        "cost_col": "Coût (ratio)",
        "docs": "Documents",
        "mode": "Multi-tours $-$ unique",
        "interaction": "Interaction",
    },
}


def render_tex(cells: dict, f1_eff: dict, cost_eff: dict, *, lang: str = "en") -> str:
    """A 2x2 LaTeX table: F1 (top) and cost ratio (bottom) per cell, with
    marginal factor effects and a consistency note. `lang` selects label set."""
    label = _TEX_LABELS[lang]

    def eff_line(key: str, fe: dict, ce: dict) -> str:
        f1s = f"{fe['effect']:+.3f} ({fe['k_positive']}/{fe['n']})"
        cs = f"{ce['effect']:.2f}$\\times$ ({ce['k_positive']}/{ce['n']})"
        return f"{label[key]} & {f1s} & {cs} \\\\"

    lines = [
        "% Generated by aedist.tabulate_exp2_2x2 -- do not edit by hand.",
        "\\begin{tabular}{lcc}",
        "\\toprule",
        f" & {label['without']} & {label['with']} \\\\",
        "\\midrule",
        f"{label['single']} & {_fmt_f1(cells['naive'])} & {_fmt_f1(cells['arm3'])} \\\\",
        f" & {_fmt_cost(cells['naive'])} & {_fmt_cost(cells['arm3'])} \\\\",
        f"{label['multi']} & {_fmt_f1(cells['optimised'])} & {_fmt_f1(cells['arm4'])} \\\\",
        f" & {_fmt_cost(cells['optimised'])} & {_fmt_cost(cells['arm4'])} \\\\",
        "\\midrule",
        f"\\multicolumn{{3}}{{l}}{{\\emph{{{label['effects']}}}}} \\\\",
        f" & {label['f1_col']} & {label['cost_col']} \\\\",
        eff_line("docs", f1_eff["docs"], cost_eff["docs"]),
        eff_line("mode", f1_eff["mode"], cost_eff["mode"]),
        eff_line("interaction", f1_eff["interaction"], cost_eff["interaction"]),
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def write_csv(collapsed: dict, output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["agent", "arm", "mode", "docs", "f1_mean", "n_f1", "n_total", "cost_mean"]
        )
        for agent in _AGENT_ORDER:
            for arm in _ARMS:
                cell = collapsed.get((agent, arm))
                if cell is None:
                    continue
                mode, docs = _ARM_FACTORS[arm]
                writer.writerow(
                    [
                        agent,
                        arm,
                        mode,
                        docs,
                        "" if cell["f1_mean"] is None else f"{cell['f1_mean']:.4f}",
                        cell["n_f1"],
                        cell["n_total"],
                        "" if cell["cost_mean"] is None else f"{cell['cost_mean']:.4f}",
                    ]
                )


# Manuscript labels for the per-(agent, arm) rows table (Table tbl:exp2-2x2).
_AGENT_DISPLAY = {
    "anthropic": "Anthropic",
    "mistral": "Mistral",
    "openai": "OpenAI",
    "qwen": "Qwen",
}
_MODE_DISPLAY = {"single": "naive (single-shot)", "multi": "optimised (multi-turn)"}


def render_agents_tex(collapsed: dict) -> str:
    """Per-(agent, arm) rows table body for the manuscript (ticket 0547).

    One row per agent x arm with the level-1 means (F1 over scored runs, cost
    over costed runs), 2-decimal precision — the same projection the hand-typed
    manuscript longtable carried. Caption and label stay in main.tex; only
    numbers live here (0486 pattern).
    """

    def fmt(value: float | None) -> str:
        return "--" if value is None else f"{value:.2f}"

    lines = [
        "% Generated by aedist.tabulate_exp2_2x2 -- do not edit by hand.",
        "\\begin{tabular}{@{}lllll@{}}",
        "\\toprule",
        "Agent & Query mode & Documents & F1 (mean) & Cost (mean, USD) \\\\",
        "\\midrule",
    ]
    for agent in _AGENT_ORDER:
        for arm in _ARMS:
            cell = collapsed.get((agent, arm))
            if cell is None:
                continue
            mode, docs = _ARM_FACTORS[arm]
            lines.append(
                f"{_AGENT_DISPLAY.get(agent, agent.capitalize())} & {_MODE_DISPLAY[mode]} & "
                f"{docs} & {fmt(cell['f1_mean'])} & {fmt(cell['cost_mean'])} \\\\"
            )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def load_exp1_flagship_means(exp1_cross_eval_csv: Path) -> dict[str, float]:
    """Per-agent mean parametric F1 of the same lab's Exp1 flagship.

    The memory-only baseline of the §exp2 memory-vs-web comparison
    (ticket 0572). Agents whose flagship has no scored parametric run are
    simply absent from the result.
    """
    model_to_agent = {m: a for a, m in _EXP1_FLAGSHIPS.items()}
    scores: dict[str, list[float]] = defaultdict(list)
    with exp1_cross_eval_csv.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            agent = model_to_agent.get(row["model"])
            raw = (row.get("accuracy_f1") or "").strip()
            if agent is not None and row["arm"] == "parametric" and raw:
                scores[agent].append(float(raw))
    return {agent: statistics.fmean(vals) for agent, vals in scores.items()}


# Median row-count and cost macros for the §exp2 coverage paragraph
# (ticket 0575). Naming mirrors the F1 macros (letters-only parts, tectonic
# truncates control words at digits): \ExpTwoRows<Agent><Arm>,
# \ExpTwoRowsMin/Max<Agent><Arm>, \ExpTwoCost<Agent><Arm>. The prose only
# quotes a subset; we emit them all so any future sentence is already sourced.
def load_run_rows_and_cost(flat_root: Path) -> dict[tuple[str, str], dict]:
    """Per-(agent, arm) report-run inventory-row counts and costs from flat dirs.

    The §exp2 coverage paragraph quotes *medians* of the table-row count and
    of the per-run cost, computed over the runs the figure classifies as
    reports (``classification == "report"``) — the same projection
    ``plot_exp2_arms_comparison`` draws. Row counts come from the committed
    ``*.md`` sibling via ``count_best_table_rows`` (the flat JSON has no
    ``inventory_rows`` field); cost comes from the JSON. Both inputs are
    tracked sources, so the macro values are recomputable from git.
    """
    from .extract import count_best_table_rows

    groups: dict[tuple[str, str], dict[str, list]] = defaultdict(
        lambda: {"rows": [], "costs": []}
    )
    for arm in _ARMS:
        arm_dir = flat_root / _ARM_FLAT_DIR_NAME[arm]
        for json_path in sorted(arm_dir.glob("*_run*.json")):
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            agent = meta.get("agent")
            if agent not in _AGENT_ORDER:
                continue
            if str(meta.get("classification") or "report") != "report":
                continue
            rows_val = next(
                (meta[k] for k in ("inventory_rows", "n_rows") if isinstance(meta.get(k), int)),
                None,
            )
            if rows_val is None:
                md_path = json_path.with_suffix(".md")
                rows_val = (
                    count_best_table_rows(md_path.read_text(encoding="utf-8"))
                    if md_path.exists()
                    else 0
                )
            cost = next((meta[k] for k in _COST_KEYS if meta.get(k) is not None), None)
            grp = groups[(agent, arm)]
            grp["rows"].append(int(rows_val))
            if cost is not None:
                grp["costs"].append(float(cost))

    out: dict[tuple[str, str], dict] = {}
    for key, grp in groups.items():
        rows = grp["rows"]
        costs = grp["costs"]
        out[key] = {
            "rows_median": statistics.median(rows) if rows else None,
            "rows_min": min(rows) if rows else None,
            "rows_max": max(rows) if rows else None,
            "cost_median": statistics.median(costs) if costs else None,
        }
    return out


def _rows_cost_macro_lines(stats: dict[tuple[str, str], dict]) -> list[str]:
    """`\\newcommand` lines for the row-count and cost median macros."""
    lines: list[str] = []
    for agent in _AGENT_ORDER:
        for arm in _ARMS:
            cell = stats.get((agent, arm))
            if cell is None:
                continue
            a, m = _MACRO_AGENT[agent], _MACRO_ARM[arm]
            if cell["rows_median"] is not None:
                # Medians of integer counts are whole or .5; the prose quotes
                # whole-number medians, so emit with no decimal when integral.
                med = cell["rows_median"]
                med_str = f"{med:.0f}" if float(med).is_integer() else f"{med:g}"
                lines.append(f"\\newcommand{{\\ExpTwoRows{a}{m}}}{{{med_str}}}")
                lines.append(f"\\newcommand{{\\ExpTwoRowsMin{a}{m}}}{{{cell['rows_min']}}}")
                lines.append(f"\\newcommand{{\\ExpTwoRowsMax{a}{m}}}{{{cell['rows_max']}}}")
            if cell["cost_median"] is not None:
                lines.append(
                    f"\\newcommand{{\\ExpTwoCost{a}{m}}}{{{cell['cost_median']:.2f}}}"
                )
    return lines


def write_macros(
    collapsed: dict,
    exp1_means: dict[str, float],
    output: Path,
    rows_cost_stats: dict[tuple[str, str], dict] | None = None,
) -> None:
    """Flat F1 macros for the §exp2 prose (tickets 0531/0572).

    One 2-dp macro per (agent, arm) mean — ``\\ExpTwoFOneQwenDocsSingle`` —
    plus the Exp1 memory baselines (``\\ExpTwoFOneQwenMemory``) and the
    derived values the prose quotes:

    - ``\\ExpTwoFOneSpreadNoDocs`` / ``\\ExpTwoFOneSpreadDocs``: max − min of
      the *rounded* per-agent means in the naive / docs-single arm, so the
      spread is exactly recomputable from the displayed pair values;
    - ``\\ExpTwoFOneDocsConvergence``: mean of the docs-single per-agent
      means excluding the top agent — the level the rest of the cohort
      converges to when handed the curated documents.
    """

    def arm_means(arm: str) -> dict[str, float]:
        return {
            agent: cell["f1_mean"]
            for (agent, a), cell in collapsed.items()
            if a == arm and cell["f1_mean"] is not None
        }

    lines = ["% Auto-generated by aedist.tabulate_exp2_2x2 — do not edit."]
    for agent in _AGENT_ORDER:
        if agent in exp1_means:
            lines.append(
                f"\\newcommand{{\\ExpTwoFOne{_MACRO_AGENT[agent]}Memory}}"
                f"{{{exp1_means[agent]:.2f}}}"
            )
        for arm in _ARMS:
            cell = collapsed.get((agent, arm))
            if cell is None or cell["f1_mean"] is None:
                continue
            lines.append(
                f"\\newcommand{{\\ExpTwoFOne{_MACRO_AGENT[agent]}{_MACRO_ARM[arm]}}}"
                f"{{{cell['f1_mean']:.2f}}}"
            )

    for name, arm in (("SpreadNoDocs", "naive"), ("SpreadDocs", "arm3")):
        rounded = [round(v, 2) for v in arm_means(arm).values()]
        if len(rounded) > 1:
            lines.append(
                f"\\newcommand{{\\ExpTwoFOne{name}}}{{{max(rounded) - min(rounded):.2f}}}"
            )
    docs = arm_means("arm3")
    if len(docs) > 1:
        rest = sorted(docs.values())[:-1]
        lines.append(
            f"\\newcommand{{\\ExpTwoFOneDocsConvergence}}{{{statistics.fmean(rest):.2f}}}"
        )

    if rows_cost_stats is not None:
        lines.extend(_rows_cost_macro_lines(rows_cost_stats))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote %s", output)


def _log_tables(cells: dict, f1_eff: dict, cost_eff: dict) -> None:
    log.info("=== 2x2 cells (F1 mean+-sd over agents; coverage scored/total) ===")
    log.info("%-20s %-22s %-22s", "", "without docs", "with docs")
    for mode_label, no_arm, yes_arm in (
        ("Single query", "naive", "arm3"),
        ("Multi-turn", "optimised", "arm4"),
    ):

        def cellstr(arm: str) -> str:
            c = cells[arm]
            f1 = "--" if c["f1_mean"] is None else f"{c['f1_mean']:.3f}±{c['f1_sd']:.3f}"
            cov = f"{c['coverage'][0]}/{c['coverage'][1]}"
            cost = "--" if c["cost_ratio"] is None else f"{c['cost_ratio']:.2f}x"
            return f"F1 {f1} cov {cov} cost {cost}"

        log.info("%-20s %-22s %-22s", mode_label, cellstr(no_arm), cellstr(yes_arm))

    log.info("=== factor effects (mean; k/n agents same sign) ===")
    for name in ("docs", "mode", "interaction"):
        fe, ce = f1_eff[name], cost_eff[name]
        f1s = (
            "--"
            if fe["effect"] is None
            else f"{fe['effect']:+.3f} pts ({fe['k_positive']}/{fe['n']})"
        )
        cs = (
            "--" if ce["effect"] is None else f"{ce['effect']:.2f}x ({ce['k_positive']}/{ce['n']})"
        )
        log.info("  %-12s F1 %-22s cost %s", name, f1s, cs)
        log.info("      F1 per-agent: %s", {a: round(d, 3) for a, d in fe["per_agent"].items()})


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Build the Exp2 2x2 factorial F1/cost table")
    parser.add_argument("--cross-eval-csv", type=Path, default=_DEFAULT_CROSS_EVAL)
    parser.add_argument("--flat-root", type=Path, default=_DEFAULT_FLAT_ROOT)
    parser.add_argument("--output-csv", type=Path, default=_DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-tex", type=Path, default=_DEFAULT_OUTPUT_TEX)
    parser.add_argument(
        "--output-agents-tex",
        type=Path,
        default=None,
        help="Optional per-(agent, arm) rows table body for the manuscript (ticket 0547)",
    )
    parser.add_argument(
        "--output-macros",
        type=Path,
        default=None,
        help="Optional flat F1 macros fragment for the manuscript prose (ticket 0572)",
    )
    parser.add_argument(
        "--exp1-cross-eval",
        type=Path,
        default=_DEFAULT_EXP1_CROSS_EVAL,
        help="Exp1 cross-eval CSV providing the memory-baseline flagship means "
        "(read only when --output-macros is given)",
    )
    parser.add_argument("--lang", choices=["en", "fr"], default="en", help="LaTeX label language")
    args = parser.parse_args(argv)

    records = load_run_records(args.cross_eval_csv, args.flat_root)
    collapsed = collapse_runs(records)
    cells = cell_table(collapsed)
    f1_eff = factor_effects(collapsed, "f1_mean", log_scale=False)
    cost_eff = factor_effects(collapsed, "cost_mean", log_scale=True)

    write_csv(collapsed, args.output_csv)
    args.output_tex.parent.mkdir(parents=True, exist_ok=True)
    args.output_tex.write_text(
        render_tex(cells, f1_eff, cost_eff, lang=args.lang), encoding="utf-8"
    )
    if args.output_agents_tex is not None:
        args.output_agents_tex.parent.mkdir(parents=True, exist_ok=True)
        args.output_agents_tex.write_text(render_agents_tex(collapsed), encoding="utf-8")
        log.info("Wrote %s", args.output_agents_tex)
    if args.output_macros is not None:
        write_macros(
            collapsed,
            load_exp1_flagship_means(args.exp1_cross_eval),
            args.output_macros,
            rows_cost_stats=load_run_rows_and_cost(args.flat_root),
        )

    _log_tables(cells, f1_eff, cost_eff)
    log.info("Wrote %s and %s", args.output_csv, args.output_tex)


if __name__ == "__main__":
    main()
