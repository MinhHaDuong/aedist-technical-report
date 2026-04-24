"""Generate LaTeX table for source grounding verification results.

Reads the 3 sourced extraction runs and 3 non-sourced baseline runs,
computes source grounding metrics, and writes a LaTeX table.

Usage:
    python -m aedist.tabulate_source_grounding
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from .verify import extract_csv_rows
from .verify_source_grounding import verify_source_grounding

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CORPUS_DIR = _PROJECT_ROOT / "data" / "rag_corpus"
_SOURCED_DIR = _PROJECT_ROOT / "experiments" / "outputs" / "rag_cited"
_DECOMPOSED_DIR = _PROJECT_ROOT / "experiments" / "outputs" / "rag_per_fuel"
_OUTPUT_PATH = _PROJECT_ROOT / "report" / "inputs" / "generated" / "tab_source_grounding.tex"


def _load_sourced_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_json_response_rows(path: Path) -> list[dict]:
    record = json.loads(path.read_text())
    response = record.get("response", "")
    return extract_csv_rows(response)


def _fmt_pct(value: float) -> str:
    return f"{100 * value:.1f}\\%"


def generate_table() -> str:
    """Generate the LaTeX source for the source grounding table."""
    lines = []
    lines.append(r"\begin{table}[ht]")
    lines.append(r"\centering")
    lines.append(
        r"\caption{Source grounding verification: RAG cité vs.\ baseline (RAG par combustible).}"
    )
    lines.append(r"\label{tab:source-grounding}")
    lines.append(r"\begin{tabular}{l r r r r r r r r r}")
    lines.append(r"\toprule")
    lines.append(
        r"Method & Run & Plants & Source & Grounding & Traceability "
        r"& \multicolumn{4}{c}{2$\times$2 counts} \\"
    )
    lines.append(
        r" & & & rate & rate & rate "
        r"& T/R & T/$\neg$R & $\neg$T/R & $\neg$T/$\neg$R \\"
    )
    lines.append(r"\midrule")

    # Sourced runs
    for run in [1, 2, 3]:
        csv_path = _SOURCED_DIR / f"claude-opus-4.6-run{run}.csv"
        rows = _load_sourced_csv(csv_path)
        _, s = verify_source_grounding(rows, _CORPUS_DIR)
        c = s["counts_2x2"]
        label = "RAG cité" if run == 1 else ""
        lines.append(
            f"  {label} & {run} & {s['total_plants']} "
            f"& {_fmt_pct(s['source_rate'])} & {_fmt_pct(s['grounding_rate'])} "
            f"& {_fmt_pct(s['traceability_rate'])} "
            f"& {c['tt']} & {c['tf']} & {c['ft']} & {c['ff']} \\\\"
        )

    lines.append(r"\midrule")

    # Baseline: decomposed deepseek-v3.2
    for run in [1, 2, 3]:
        json_path = _DECOMPOSED_DIR / f"deepseek-v3.2-run{run}.json"
        rows = _load_json_response_rows(json_path)
        _, s = verify_source_grounding(rows, _CORPUS_DIR)
        c = s["counts_2x2"]
        label = "RAG par combustible" if run == 1 else ""
        lines.append(
            f"  {label} & {run} & {s['total_plants']} "
            f"& {_fmt_pct(s['source_rate'])} & {_fmt_pct(s['grounding_rate'])} "
            f"& {_fmt_pct(s['traceability_rate'])} "
            f"& {c['tt']} & {c['tf']} & {c['ft']} & {c['ff']} \\\\"
        )

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(
        r"\par\smallskip\footnotesize "
        r"Source rate = fraction with any citation; "
        r"Grounding rate = citation fuzzy-matches a corpus filename; "
        r"Traceability = grounded \emph{and} plant name found in matched file. "
        r"T = traceable, R = in reference dataset."
    )
    lines.append(r"\end{table}")

    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    tex = generate_table()
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(tex, encoding="utf-8")
    log.info("Wrote %s", _OUTPUT_PATH)


if __name__ == "__main__":
    main()
