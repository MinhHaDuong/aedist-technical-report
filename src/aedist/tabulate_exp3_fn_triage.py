"""Produce and summarise the Exp3 false-negative (FN) triage artefacts.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Two modes of operation:

1. ``--mode worksheet``  (default, no make rule needed)
   Generates the *human-review worksheet* CSV:
   ``experiments/derived/exp3_fn_triage.csv``
   One row per FN plant from the best-performing arm/model/run (arm3, gpt-5.5,
   run 4 — highest recall at 40 FNs).  Mechanical evidence columns are filled
   automatically; ``bucket`` and ``rationale`` columns are left empty for the
   human reviewer.

   Mechanical evidence columns:
     n_runs_missed   how often the plant was missed across the 5 runs of
                     arm3/gpt-5.5 (0-5; higher = harder FN)
     in_gem          whether the plant name fuzzy-matches a GEM entry (>=85
                     similarity); "comparator" evidence
     mentioned_in_narrative   whether any literal substring of the reference name
                     (>= 6 chars) appears in the best-run narrative markdown;
                     "list limit" evidence
     ref_fuel        fuel from the expert reference
     ref_status      status from the expert reference (ordinal code + label)
     ref_capacity_mwe  capacity (MWe) from expert reference
     ref_province    province from expert reference

   Allowed bucket values (the four categories from ticket 0374):
     comparateur   comparator/matcher failed to recognise a name the model used
     liste         model cited something real but not in our reference
     définition    scope/definitional edge case
     résidu        genuine recall failure — nothing to fix on our side

2. ``--mode summary``
   Reads a *completed* worksheet CSV (bucket column filled in) and writes
   ``experiments/derived/tab_exp3_fn_triage_summary.csv`` plus the LaTeX
   table ``report/inputs/generated/tab_exp3_fn_triage.tex``.

Usage:
    # Generate worksheet (run once; fill in bucket + rationale by hand):
    uv run python -m aedist.tabulate_exp3_fn_triage --mode worksheet \\
        --arm3-dir experiments/derived/arm3_flat \\
        --output experiments/derived/exp3_fn_triage.csv

    # Summarise a filled worksheet:
    uv run python -m aedist.tabulate_exp3_fn_triage --mode summary \\
        --input experiments/derived/exp3_fn_triage.csv \\
        --output-csv experiments/derived/tab_exp3_fn_triage_summary.csv \\
        --output-tex report/inputs/generated/tab_exp3_fn_triage.tex
"""

import argparse
import csv
import logging
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from .config import GEM_THERMAL_REFERENCE_CSV, VN_THERMAL_PLANTS_RELEASE_CSV
from .evaluate import load_plants_csv, plants_from_dicts
from .reconcile import reconcile
from .schema import MatchType
from .score_ingest import RunLocator, ingest_run

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent

_DEFAULT_ARM3_DIR = _REPO_ROOT / "experiments" / "derived" / "arm3_flat"
_DEFAULT_INPUT = _REPO_ROOT / "experiments" / "derived" / "exp3_fn_triage.csv"
_DEFAULT_OUTPUT_WORKSHEET = _REPO_ROOT / "experiments" / "derived" / "exp3_fn_triage.csv"
_DEFAULT_OUTPUT_SUMMARY_CSV = (
    _REPO_ROOT / "experiments" / "derived" / "tab_exp3_fn_triage_summary.csv"
)
_DEFAULT_OUTPUT_TEX = (
    _REPO_ROOT / "report" / "inputs" / "generated" / "tab_exp3_fn_triage.tex"
)

# The arm/model/run with the highest recall among all Exp3 arm3 runs.
# arm3 = RAG single-turn (sota_exp3_arm3_batch1), best model = gpt-5.5,
# best run = run 4 (151 plants output, 40 FNs on 176-plant reference v2.1).
_BEST_ARM = "arm3"
_BEST_MODEL = "gpt-5.5"
_BEST_RUN = 4
_N_RUNS = 5  # total runs for arm3/gpt-5.5 used to compute n_runs_missed

# Minimum fuzzy similarity to consider a GEM match "in_gem".
_GEM_SIMILARITY_THRESHOLD = 85

# Minimum substring length to count as a narrative mention.
_MIN_MENTION_LEN = 6

# Four allowed bucket values (ticket 0374).
ALLOWED_BUCKETS = {"comparateur", "liste", "définition", "résidu"}

_WORKSHEET_FIELDS = [
    "reference_name",
    "ref_fuel",
    "ref_status",
    "ref_capacity_mwe",
    "ref_province",
    "n_runs_missed",
    "in_gem",
    "mentioned_in_narrative",
    "bucket",
    "rationale",
]

_SUMMARY_FIELDS = ["bucket", "n_plants", "pct_of_total"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_gem_names(gem_csv: Path) -> list[str]:
    """Return the list of plant names from the GEM reference CSV."""
    if not gem_csv.exists():
        log.warning("GEM CSV not found at %s — in_gem will be False", gem_csv)
        return []
    with gem_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [r.get("Name") or r.get("name") or "" for r in reader]


def _in_gem(plant_name: str, gem_names: list[str]) -> bool:
    """True if any GEM entry fuzzy-matches plant_name above threshold."""
    if not gem_names:
        return False
    name_lower = plant_name.lower()
    for name in gem_names:
        if fuzz.token_sort_ratio(name_lower, name.lower()) >= _GEM_SIMILARITY_THRESHOLD:
            return True
    return False


def _mentioned_in_narrative(plant_name: str, narrative_text: str) -> bool:
    """True if any >=6-char word from plant_name appears verbatim in the narrative."""
    name_lower = plant_name.lower()
    text_lower = narrative_text.lower()
    # Try full name first (most common)
    if name_lower in text_lower:
        return True
    # Try each word that is long enough to be distinctive
    for word in name_lower.split():
        if len(word) >= _MIN_MENTION_LEN and word in text_lower:
            return True
    return False


def _load_ref_lookup(ref_csv: Path) -> dict[str, dict]:
    """Return {name: row_dict} from the expert reference CSV."""
    lookup: dict[str, dict] = {}
    with ref_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lookup[row["name"]] = row
    return lookup


# ---------------------------------------------------------------------------
# Worksheet generation
# ---------------------------------------------------------------------------


def generate_worksheet(
    arm3_dir: Path = _DEFAULT_ARM3_DIR,
    output: Path = _DEFAULT_OUTPUT_WORKSHEET,
    ref_csv: Path = VN_THERMAL_PLANTS_RELEASE_CSV,
    gem_csv: Path | None = None,
) -> list[dict]:
    """Produce the FN triage worksheet CSV.

    Returns the list of row dicts (for testing).
    """
    if gem_csv is None:
        gem_csv = GEM_THERMAL_REFERENCE_CSV

    ref_plants = load_plants_csv(ref_csv)
    ref_lookup = _load_ref_lookup(ref_csv)
    gem_names = _load_gem_names(gem_csv)

    log.info("Reference: %d plants", len(ref_plants))

    # Count how often each reference plant is missed across all 5 runs.
    missed_count: Counter = Counter()
    for run_id in range(1, _N_RUNS + 1):
        locator = RunLocator(arm=_BEST_ARM, model=_BEST_MODEL, run=run_id)
        ingested = ingest_run(locator, arm3_dir=arm3_dir)
        system_plants = plants_from_dicts(ingested.rows)
        entries = reconcile(ref_plants, system_plants)
        missed_names = [e.reference_name for e in entries if e.match_type == MatchType.REFERENCE_ONLY]
        missed_count.update(missed_names)

    # Load the best run's narrative for mention checks.
    best_locator = RunLocator(arm=_BEST_ARM, model=_BEST_MODEL, run=_BEST_RUN)
    best_ingested = ingest_run(best_locator, arm3_dir=arm3_dir)
    narrative_text = best_ingested.markdown_path.read_text(encoding="utf-8", errors="replace")

    # Reconcile the best run to get the exact FN list for that run.
    system_plants = plants_from_dicts(best_ingested.rows)
    entries = reconcile(ref_plants, system_plants)
    fn_entries = [e for e in entries if e.match_type == MatchType.REFERENCE_ONLY]

    log.info(
        "Best run (%s/%s/run%d): %d system plants, %d FNs",
        _BEST_ARM,
        _BEST_MODEL,
        _BEST_RUN,
        len(system_plants),
        len(fn_entries),
    )

    rows: list[dict] = []
    for entry in sorted(fn_entries, key=lambda e: -(missed_count.get(e.reference_name or "", 0))):
        ref_name = entry.reference_name or ""
        ref_row = ref_lookup.get(ref_name, {})
        row = {
            "reference_name": ref_name,
            "ref_fuel": ref_row.get("fuel", ""),
            "ref_status": ref_row.get("status", ""),
            "ref_capacity_mwe": ref_row.get("capacity_mwe", ""),
            "ref_province": ref_row.get("province", ""),
            "n_runs_missed": missed_count.get(ref_name, 0),
            "in_gem": "yes" if _in_gem(ref_name, gem_names) else "no",
            "mentioned_in_narrative": "yes" if _mentioned_in_narrative(ref_name, narrative_text) else "no",
            "bucket": "",
            "rationale": "",
        }
        rows.append(row)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_WORKSHEET_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote worksheet: %s (%d rows)", output, len(rows))
    return rows


# ---------------------------------------------------------------------------
# Summary generation from completed worksheet
# ---------------------------------------------------------------------------


def generate_summary(
    input_csv: Path = _DEFAULT_INPUT,
    output_csv: Path = _DEFAULT_OUTPUT_SUMMARY_CSV,
    output_tex: Path = _DEFAULT_OUTPUT_TEX,
) -> list[dict]:
    """Summarise a completed triage worksheet into counts per bucket.

    Returns the list of summary row dicts (for testing).
    Raises ValueError if any non-empty bucket value is not in ALLOWED_BUCKETS.
    """
    with input_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    bucket_counts: Counter = Counter()
    n_empty = 0
    for row in rows:
        b = row.get("bucket", "").strip()
        if not b:
            n_empty += 1
            continue
        if b not in ALLOWED_BUCKETS:
            raise ValueError(
                f"Unknown bucket value {b!r} for plant {row.get('reference_name')!r}. "
                f"Allowed: {sorted(ALLOWED_BUCKETS)}"
            )
        bucket_counts[b] += 1

    if n_empty:
        log.warning("%d rows have no bucket — excluded from summary", n_empty)

    total = sum(bucket_counts.values())
    ordered_buckets = ["comparateur", "liste", "définition", "résidu"]
    summary_rows = []
    for bucket in ordered_buckets:
        n = bucket_counts.get(bucket, 0)
        pct = round(100.0 * n / total, 1) if total > 0 else 0.0
        summary_rows.append({"bucket": bucket, "n_plants": n, "pct_of_total": pct})

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)

    log.info("Wrote summary CSV: %s", output_csv)

    latex = _generate_latex(summary_rows, total)
    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex, encoding="utf-8")
    log.info("Wrote LaTeX table: %s", output_tex)

    return summary_rows


def _generate_latex(summary_rows: list[dict], total: int) -> str:
    """Generate a LaTeX table from summary rows."""
    bucket_labels = {
        "comparateur": "Comparateur (matcher limit)",
        "liste": "Liste (scope hole in reference)",
        "définition": "Définition (scope/threshold edge case)",
        "résidu": "Résidu (genuine recall failure)",
    }
    lines = [
        "% Auto-generated by tabulate_exp3_fn_triage.py — do not edit",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Triage des faux négatifs de l'Exp.~3 (bras arm3, GPT-5.5,"
        " run 4, $n=" + str(total) + "$~FN)}"
        "\\label{tab:exp3-fn-triage}",
        "\\begin{tabular}{lrr}",
        "\\toprule",
        "Catégorie & $n$ & \\% \\\\",
        "\\midrule",
    ]
    for row in summary_rows:
        label = bucket_labels.get(row["bucket"], row["bucket"])
        lines.append(f"{label} & {row['n_plants']} & {row['pct_of_total']}\\% \\\\")
    lines.extend(
        [
            "\\midrule",
            f"Total & {total} & 100.0\\% \\\\",
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Produce or summarise the Exp3 FN triage worksheet",
    )
    parser.add_argument(
        "--mode",
        choices=["worksheet", "summary"],
        default="worksheet",
        help="worksheet: generate blank triage CSV; summary: summarise filled CSV (default: worksheet)",
    )
    parser.add_argument(
        "--arm3-dir",
        type=Path,
        default=_DEFAULT_ARM3_DIR,
        help="Path to arm3_flat directory (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT_WORKSHEET,
        help="Output path for worksheet CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_DEFAULT_INPUT,
        help="Input path for filled worksheet CSV (summary mode; default: %(default)s)",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=_DEFAULT_OUTPUT_SUMMARY_CSV,
        help="Output path for summary CSV (summary mode; default: %(default)s)",
    )
    parser.add_argument(
        "--output-tex",
        type=Path,
        default=_DEFAULT_OUTPUT_TEX,
        help="Output path for LaTeX table (summary mode; default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if args.mode == "worksheet":
        generate_worksheet(arm3_dir=args.arm3_dir, output=args.output)
    else:
        generate_summary(
            input_csv=args.input,
            output_csv=args.output_csv,
            output_tex=args.output_tex,
        )


if __name__ == "__main__":
    main()
