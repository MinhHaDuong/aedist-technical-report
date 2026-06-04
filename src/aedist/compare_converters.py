"""Compare PDF converter backends on table extraction quality.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Reads pre-generated markdown outputs from each backend and produces
a side-by-side quality report: tables detected, rows, Vietnamese
diacritics, file size.  When ``--meta`` points to a YAML sidecar the
script merges observational data (timing, diacritics labels, display
names) with computed metrics and emits the LaTeX table used in the
report.

Usage:
    python -m aedist.compare_converters --input experiments/data/converter_test
    python -m aedist.compare_converters --input experiments/data/converter_test \
        --meta experiments/data/converter_test/benchmark_meta.yaml \
        --output report/inputs/generated/tab_converter_benchmark.tex
"""

import argparse
import logging
import re
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

# Display order: best table coverage first, then by table count descending.
_DISPLAY_ORDER = [
    "marker",
    "mistral-ocr-direct",
    "mineru",
    "grobid",
    "mistral-ocr",
    "cloudflare-ai",
]


def count_tables(md: str) -> int:
    """Count markdown tables by counting separator lines (|---|)."""
    return sum(1 for line in md.splitlines() if re.match(r"\s*\|[-:| ]+\|\s*$", line))


def count_table_rows(md: str) -> int:
    """Count lines that look like markdown table rows (| ... |)."""
    return sum(1 for line in md.splitlines() if re.match(r"\s*\|.+\|\s*$", line))


def count_html_tables(md: str) -> int:
    """Count HTML <table> blocks."""
    return md.count("<table>")


def count_html_table_rows(md: str) -> int:
    """Count HTML <tr> tags (may appear multiple times per line)."""
    return len(re.findall(r"<tr[ >]", md))


def vietnamese_sample_check(md: str) -> dict[str, bool]:
    """Check for presence of common Vietnamese diacriticked words."""
    checks = {
        "Quyết định": "Quyết định" in md or "Quyết Định" in md,
        "điện lực": "điện lực" in md or "điện" in md,
        "công suất": "công suất" in md,
        "nhà máy": "nhà máy" in md,
        "tỉnh": "tỉnh" in md,
    }
    return checks


def analyze_backend(md_path: Path) -> dict:
    """Analyze a single backend's markdown output."""
    md = md_path.read_text(encoding="utf-8")
    lines = md.splitlines()
    viet = vietnamese_sample_check(md)

    md_tables = count_tables(md)
    html_tables = count_html_tables(md)
    md_rows = count_table_rows(md)
    html_rows = count_html_table_rows(md)

    return {
        "file": md_path.name,
        "size_kb": md_path.stat().st_size / 1024,
        "lines": len(lines),
        "md_tables": md_tables,
        "md_table_rows": md_rows,
        "html_tables": html_tables,
        "html_table_rows": html_rows,
        "total_tables": md_tables + html_tables,
        "total_rows": md_rows + html_rows,
        "vietnamese_score": sum(viet.values()),
        "vietnamese_max": len(viet),
        "vietnamese_detail": viet,
    }


def format_summary(results: dict[str, dict], document: str) -> str:
    """Format comparison as a text table."""
    header = f"Converter Benchmark: {document}\n{'=' * 60}\n"
    rows = []
    rows.append(
        f"{'Backend':<20} {'Tables':>7} {'Rows':>6} {'Size KB':>8} {'Viet':>5}"
    )
    rows.append("-" * 60)
    for backend in _ordered_keys(results):
        r = results[backend]
        rows.append(
            f"{backend:<20} {r['total_tables']:>7} "
            f"{r['total_rows']:>6} "
            f"{r['size_kb']:>7.0f} "
            f"{r['vietnamese_score']}/{r['vietnamese_max']:>3}"
        )
    return header + "\n".join(rows) + "\n"


def _ordered_keys(results: dict[str, dict]) -> list[str]:
    """Return backend keys in display order, unknown backends appended."""
    known = [k for k in _DISPLAY_ORDER if k in results]
    extra = sorted(k for k in results if k not in _DISPLAY_ORDER)
    return known + extra


def _latex_int(n: int) -> str:
    """Format integer with LaTeX thin-space thousands separator."""
    s = str(n)
    if n >= 1000:
        s = f"{n:,}".replace(",", r"\,")
    return s


def format_latex(results: dict[str, dict], meta: dict[str, dict] | None = None) -> str:
    """Format comparison as a LaTeX booktabs table for the report.

    When *meta* is provided (from benchmark_meta.yaml), the table includes
    timing and qualitative diacritics columns with human-readable backend
    names.  Without meta, falls back to a simpler schema.
    """
    if meta is None:
        meta = {}

    lines = [
        r"\begin{tabular}{lrrrcl}",
        r"\toprule",
        r"Backend & Tableaux & Lignes & Taille (Ko) & Temps (s) & Diacritiques \\",
        r"\midrule",
    ]
    for backend in _ordered_keys(results):
        r = results[backend]
        m = meta.get(backend, {})
        name = m.get("display_name", backend)
        tables = _latex_int(r["total_tables"])
        rows_na = m.get("rows_na", False)
        rows = "--" if rows_na else _latex_int(r["total_rows"])
        size = _latex_int(round(r["size_kb"]))
        timing = str(m["timing_s"]) if "timing_s" in m else "--"
        diacritics = m.get("diacritics", f"{r['vietnamese_score']}/{r['vietnamese_max']}")
        lines.append(f"{name} & {tables} & {rows} & {size} & {timing} & {diacritics} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare PDF converter backends on table extraction"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Directory with per-backend subdirectories (e.g., grobid/, marker/)",
    )
    parser.add_argument(
        "--document",
        default="Decision-1509",
        help="Document stem to compare (default: Decision-1509)",
    )
    parser.add_argument(
        "--meta",
        type=Path,
        default=None,
        help="YAML sidecar with display names, timing, diacritics labels",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .tex file for LaTeX table",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    meta = {}
    if args.meta:
        meta = yaml.safe_load(args.meta.read_text(encoding="utf-8")) or {}

    results = {}
    for backend_dir in sorted(args.input.iterdir()):
        if not backend_dir.is_dir():
            continue
        md_file = backend_dir / f"{args.document}.md"
        if not md_file.exists():
            log.warning("Skipping %s: no %s.md found", backend_dir.name, args.document)
            continue
        results[backend_dir.name] = analyze_backend(md_file)
        r = results[backend_dir.name]
        log.info(
            "Analyzed %s: %d tables, %d rows",
            backend_dir.name,
            r["total_tables"],
            r["total_rows"],
        )

    if not results:
        log.error("No backend outputs found in %s", args.input)
        return

    print(format_summary(results, args.document))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(format_latex(results, meta), encoding="utf-8")
        log.info("Wrote %s", args.output)


if __name__ == "__main__":
    main()
