"""Ticket 0494 — Wikipedia recall bar by raw reference status.

The author seeded Wikipedia's Vietnam coal list from the MOIT/PDP8 reference
before the experiment (which is why Protocol §3.4 bans Wikipedia as a
justification source). Wikipedia coverage of the reference is therefore the
recall bar a competent parametric model ought to clear: the answer key was
placed in the training corpus. This script measures that bar per raw reference
status, exposing its two regimes — built fleet well covered (high bar, the
quantified "disappointing"), forward-looking pipeline barely covered (the
reference's unique contribution, which no parametric source holds).

Distinct from the 0486 concordance (``tabulate_source_concordance``): GEM is an
independent external tracker (reproduction); Wikipedia is the author's own
seeded derivative (contamination-aware ceiling). Different epistemics, separate
artifacts — kept apart on purpose. The matching machinery is shared.

Output: data/reference/tab_wikipedia_recall_bar.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
from pathlib import Path

from aedist.config import VN_THERMAL_PLANTS_RELEASE_CSV, WIKIPEDIA_RECALL_BAR_CSV
from aedist.evaluate import load_plants_csv
from aedist.tabulate_source_concordance import (
    _names_to_plants,
    _reviewed_coverage,
    _wikipedia_names,
)

log = logging.getLogger(__name__)

# Raw reference statuses in lifecycle order (leading-digit prefixes stripped).
_RAW_STATUS_ORDER = [
    "exploring",
    "announced",
    "proposed",
    "added to PDP",
    "permitted",
    "construction",
    "operating",
    "retired",
    "cancelled",
]
BUILT_STATUSES = ("operating", "construction", "permitted")
PIPELINE_STATUSES = ("proposed", "announced")


def _raw_status(s: str | None) -> str:
    return re.sub(r"^\d+\s+", "", (s or "").strip()) or "unknown"


def build_recall_bar() -> list[dict]:
    """Per-raw-status Wikipedia reviewed coverage of the reference."""
    ref_plants = load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV)
    status_by_name: dict[str, str] = {}
    with VN_THERMAL_PLANTS_RELEASE_CSV.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            status_by_name[r["name"].strip()] = _raw_status(r.get("status"))

    wiki_names = _wikipedia_names()
    _, covered = _reviewed_coverage(ref_plants, _names_to_plants(wiki_names), wiki_names)

    rows: list[dict] = []
    for status in _RAW_STATUS_ORDER:
        names = [n for n, s in status_by_name.items() if s == status]
        if not names:
            continue
        n_cov = sum(1 for n in names if n in covered)
        rows.append(
            {
                "status": status,
                "n_reference": len(names),
                "covered": n_cov,
                "coverage": round(n_cov / len(names), 4),
            }
        )
    total_n = sum(r["n_reference"] for r in rows)
    total_cov = sum(r["covered"] for r in rows)
    rows.append(
        {
            "status": "All",
            "n_reference": total_n,
            "covered": total_cov,
            "coverage": round(total_cov / total_n, 4),
        }
    )
    return rows


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["status", "n_reference", "covered", "coverage"])
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote Wikipedia recall bar to %s (%d status rows)", output, len(rows) - 1)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate the per-status Wikipedia recall bar (ticket 0494)")
    parser.add_argument("--output", type=Path, default=WIKIPEDIA_RECALL_BAR_CSV)
    args = parser.parse_args(argv)

    rows = build_recall_bar()
    write_csv(rows, args.output)
    by = {r["status"]: r for r in rows}
    built = [by[s]["coverage"] for s in BUILT_STATUSES if s in by]
    pipeline = [by[s]["coverage"] for s in PIPELINE_STATUSES if s in by]
    log.info(
        "built-fleet mean %.0f%% (%s); pipeline mean %.0f%% (%s)",
        100 * sum(built) / len(built),
        ", ".join(f"{s} {by[s]['coverage']:.0%}" for s in BUILT_STATUSES if s in by),
        100 * sum(pipeline) / len(pipeline),
        ", ".join(f"{s} {by[s]['coverage']:.0%}" for s in PIPELINE_STATUSES if s in by),
    )


if __name__ == "__main__":
    main()
