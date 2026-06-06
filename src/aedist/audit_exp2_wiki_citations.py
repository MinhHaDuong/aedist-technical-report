"""Audit Exp2 run files for banned Wikipedia/Wikidata domain citations.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Protocol_05 §3.4 bans Wikipedia, Wikidata, DBpedia, and mirrors as sources.
This script scans Source 1/Source 2 table cells and bibliography sections of all
40 registered runs, counting citations whose URL domain matches the banned set.
Notes cells are deliberately excluded — they contain compliance annotations
(e.g. "Lead: Wikipedia (inadmissible)") that are the opposite of violations.

Usage:
    python -m aedist.audit_exp2_wiki_citations \\
        --naive-dir experiments/derived/arm1_flat \\
        --optimised-dir experiments/derived/arm2_flat \\
        --output report/inputs/generated/tab_exp2_wiki_compliance.csv \\
        --output-macros report/inputs/generated/macros_wiki_compliance.tex
"""

import argparse
import csv
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from aedist.extract_exp2_bib import (
    _RUN_RE,
    _find_bib_section,
    _find_source_columns,
    _parse_table_rows,
)

log = logging.getLogger(__name__)

BANNED_DOMAINS: frozenset[str] = frozenset({
    "wikipedia.org",
    "wikidata.org",
    "dbpedia.org",
    "wikiwand.com",
})

_URL_RE = re.compile(r"https?://[^\s)\]>]+")

_CSV_FIELDS = [
    "agent",
    "arm",
    "run",
    "n_cells_s1s2",
    "n_banned_s1s2",
    "n_bib_entries",
    "n_banned_bib",
]


def is_banned_domain(url: str) -> bool:
    """Return True if *url* resolves to a banned domain (suffix match).

    Handles full URLs (https://en.wikipedia.org/...), scheme-less hostnames
    (en.wikipedia.org), and bare words (returns False).
    """
    text = url.strip()
    if not text:
        return False
    # Normalise: add scheme if missing so urlparse locates the host
    if "://" not in text:
        text = "//" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if not host or "." not in host:
        return False
    for domain in BANNED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return True
    return False


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP(S) URLs from a free-text string."""
    return _URL_RE.findall(text)


def _count_banned_in_text(text: str) -> int:
    """Count distinct banned-domain URL occurrences in *text*."""
    urls = _extract_urls(text)
    return sum(1 for u in urls if is_banned_domain(u))


def audit_run(path: Path) -> dict:
    """Audit a single run file for banned-domain citations.

    Returns a dict with n_cells_s1s2, n_banned_s1s2, n_bib_entries, n_banned_bib.
    """
    if not path.exists() or path.stat().st_size == 0:
        return {"n_cells_s1s2": 0, "n_banned_s1s2": 0, "n_bib_entries": 0, "n_banned_bib": 0}

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")

    header_cells, data_rows = _parse_table_rows(lines)
    col_idx = _find_source_columns(header_cells) if header_cells else {}

    # Count banned URLs in Source 1 and Source 2 cells only (NOT Notes)
    n_cells_s1s2 = 0
    n_banned_s1s2 = 0
    for row in data_rows:
        for col_key in ("src1", "src2"):
            idx = col_idx.get(col_key)
            if idx is not None and idx < len(row):
                n_cells_s1s2 += 1
                n_banned_s1s2 += _count_banned_in_text(row[idx])

    # Count banned URLs in bibliography section
    bib_text = _find_bib_section(text)
    bib_urls = _extract_urls(bib_text)
    n_bib_entries = len(bib_urls)
    n_banned_bib = sum(1 for u in bib_urls if is_banned_domain(u))

    return {
        "n_cells_s1s2": n_cells_s1s2,
        "n_banned_s1s2": n_banned_s1s2,
        "n_bib_entries": n_bib_entries,
        "n_banned_bib": n_banned_bib,
    }


def audit_all(naive_dir: Path, optimised_dir: Path) -> list[dict]:
    """Audit all run files in both arms, returning one row per run."""
    rows: list[dict] = []
    for arm_dir, arm_label in [
        (naive_dir, "naive"),
        (optimised_dir, "optimised"),
    ]:
        for md_path in sorted(arm_dir.glob("*.md")):
            m = _RUN_RE.match(md_path.name)
            if not m:
                continue
            agent, run_str = m.group(1), m.group(2)
            run_num = int(run_str)

            log.info("Auditing %s/%s (arm=%s)", agent, md_path.name, arm_label)
            metrics = audit_run(md_path)

            rows.append({"agent": agent, "arm": arm_label, "run": run_num, **metrics})

    rows.sort(key=lambda r: (r["arm"], r["agent"], r["run"]))
    return rows


def write_macros(rows: list[dict], path: Path) -> None:
    """Emit LaTeX macros summarising the audit."""
    total_runs = len(rows)
    optimised_rows = [r for r in rows if r["arm"] == "optimised"]
    naive_rows = [r for r in rows if r["arm"] == "naive"]

    # Runs with ANY banned citation (s1s2 or bib)
    n_banned_optimised = sum(
        1 for r in optimised_rows if r["n_banned_s1s2"] + r["n_banned_bib"] > 0
    )
    n_banned_naive = sum(
        1 for r in naive_rows if r["n_banned_s1s2"] + r["n_banned_bib"] > 0
    )

    # Total banned citation instances across all runs
    total_banned = sum(r["n_banned_s1s2"] + r["n_banned_bib"] for r in rows)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "% Auto-generated by audit_exp2_wiki_citations.py — do not edit.\n"
        f"\\newcommand{{\\ExpTwoWikiRunsScanned}}{{{total_runs}}}\n"
        f"\\newcommand{{\\ExpTwoWikiBannedOptimised}}{{{n_banned_optimised}}}\n"
        f"\\newcommand{{\\ExpTwoWikiBannedNaive}}{{{n_banned_naive}}}\n"
        f"\\newcommand{{\\ExpTwoWikiBannedTotal}}{{{total_banned}}}\n",
        encoding="utf-8",
    )
    log.info("Wrote macros to %s", path)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Audit Exp2 runs for banned Wikipedia/Wikidata domain citations"
    )
    parser.add_argument(
        "--naive-dir",
        default="experiments/derived/arm1_flat",
        help="Directory of naive-arm run files (default: experiments/derived/arm1_flat)",
    )
    parser.add_argument(
        "--optimised-dir",
        default="experiments/derived/arm2_flat",
        help="Directory of optimised-arm run files (default: experiments/derived/arm2_flat)",
    )
    parser.add_argument(
        "--output",
        default="report/inputs/generated/tab_exp2_wiki_compliance.csv",
        help="Path to write the per-run compliance CSV",
    )
    parser.add_argument(
        "--output-macros",
        default="report/inputs/generated/macros_wiki_compliance.tex",
        help="Path to write the LaTeX macros file",
    )
    args = parser.parse_args(argv)

    rows = audit_all(Path(args.naive_dir), Path(args.optimised_dir))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), out)

    write_macros(rows, Path(args.output_macros))


if __name__ == "__main__":
    main()
