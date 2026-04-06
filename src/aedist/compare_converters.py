"""Compare PDF converter backends on table extraction quality.

Reads pre-generated markdown outputs from each backend and produces
a side-by-side quality report: tables detected, rows, Vietnamese
diacritics, file size.

Usage:
    python -m aedist.compare_converters --input experiments/data/converter_test
    python -m aedist.compare_converters --input experiments/data/converter_test --output report.tex
"""

import argparse
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)


def count_tables(md: str) -> int:
    """Count markdown tables by counting separator lines (|---|)."""
    return sum(1 for line in md.splitlines() if re.match(r"\s*\|[-:| ]+\|\s*$", line))


def count_table_rows(md: str) -> int:
    """Count lines that look like markdown table rows (| ... |)."""
    return sum(1 for line in md.splitlines() if re.match(r"\s*\|.+\|\s*$", line))


def count_html_tables(md: str) -> int:
    """Count HTML <table> blocks (GROBID style)."""
    return md.count("<table>")


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

    return {
        "file": md_path.name,
        "size_kb": md_path.stat().st_size / 1024,
        "lines": len(lines),
        "md_tables": count_tables(md),
        "md_table_rows": count_table_rows(md),
        "html_tables": count_html_tables(md),
        "vietnamese_score": sum(viet.values()),
        "vietnamese_max": len(viet),
        "vietnamese_detail": viet,
    }


def format_summary(results: dict[str, dict], document: str) -> str:
    """Format comparison as a text table."""
    header = f"Converter Benchmark: {document}\n{'=' * 60}\n"
    rows = []
    rows.append(
        f"{'Backend':<12} {'Lines':>6} {'Tables':>7} {'Rows':>6} {'HTML':>5} {'Viet':>5} {'Size KB':>8}"
    )
    rows.append("-" * 60)
    for backend, r in sorted(results.items()):
        rows.append(
            f"{backend:<12} {r['lines']:>6} {r['md_tables']:>7} "
            f"{r['md_table_rows']:>6} {r['html_tables']:>5} "
            f"{r['vietnamese_score']}/{r['vietnamese_max']:>3} "
            f"{r['size_kb']:>7.0f}"
        )
    return header + "\n".join(rows) + "\n"


def format_latex(results: dict[str, dict], document: str) -> str:
    """Format comparison as a LaTeX table."""
    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Backend & Lines & Tables & Table rows & Vietnamese & Size (KB) \\",
        r"\midrule",
    ]
    for backend, r in sorted(results.items()):
        viet = f"{r['vietnamese_score']}/{r['vietnamese_max']}"
        lines.append(
            f"{backend} & {r['lines']} & {r['md_tables']} & "
            f"{r['md_table_rows']} & {viet} & {r['size_kb']:.0f} \\\\"
        )
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
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .tex file for LaTeX table",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    results = {}
    for backend_dir in sorted(args.input.iterdir()):
        if not backend_dir.is_dir():
            continue
        md_file = backend_dir / f"{args.document}.md"
        if not md_file.exists():
            log.warning("Skipping %s: no %s.md found", backend_dir.name, args.document)
            continue
        results[backend_dir.name] = analyze_backend(md_file)
        log.info(
            "Analyzed %s: %d tables, %d rows",
            backend_dir.name,
            results[backend_dir.name]["md_tables"],
            results[backend_dir.name]["md_table_rows"],
        )

    if not results:
        log.error("No backend outputs found in %s", args.input)
        return

    print(format_summary(results, args.document))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(format_latex(results, args.document), encoding="utf-8")
        log.info("Wrote %s", args.output)


if __name__ == "__main__":
    main()
