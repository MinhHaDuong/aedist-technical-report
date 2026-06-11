"""Ticket 0486 — source concordance: reference vs GEM and Wikipedia.

Productionises the throwaway prototypes in ``experiments/exploration/0486/``.
Both source lists are matched against the reference with the project LP matcher,
then an ASCII-fold pass recovers Vietnamese-diacritic naming variants the raw
matcher floors (e.g. "Cà Mau I" vs "Ca Mau 1"). Coverage is therefore reported
as *light-reviewed* — the fold recovery slightly over-counts via grain mismatch
(one source row ↔ several reference phases), so the figures are upper-ish; full
per-plant HITL is post-arXiv (ticket 0498).

Bidirectional by construction: neither source is a superset. The reference adds
the PDP8 LNG pipeline (reference-only); GEM retains a cancelled/announced tail
(GEM-only). Denominator is ``reference_plant_count()`` — never hardcoded.

Outputs:
  - data/reference/tab_source_concordance.csv      (per-status, bidirectional)
  - report/inputs/generated/macros_source_concordance.tex  (headline aggregates)
  - report/inputs/generated/tab_source_concordance.tex     (annex table body,
    \\input by slides/manuscript/main.tex — no hand-typed numbers in prose)
"""

import argparse
import csv
import logging
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from aedist.config import (
    GEM_THERMAL_REFERENCE_CSV,
    SOURCE_CONCORDANCE_CSV,
    VN_THERMAL_PLANTS_RELEASE_CSV,
)
from aedist.evaluate import load_plants_csv, reference_plant_count
from aedist.exp1_recognition import STATUS_LABELS_EN, STATUS_ORDER
from aedist.reconcile import reconcile
from aedist.schema import MatchType

log = logging.getLogger(__name__)

_MATCHED = {
    MatchType.EXACT,
    MatchType.EXACT_CAPACITY_DIFF,
    MatchType.FUZZY,
    MatchType.FUZZY_CAPACITY_DIFF,
}
_RAW_DIR = Path("data/reference/raw")
_WIKI_COAL = _RAW_DIR / "wikipedia_coal_vietnam-2026-06-09.wikitext"
_WIKI_POWER = _RAW_DIR / "wikipedia_power_vietnam-2026-06-09.wikitext"
# ASCII-folded partial_ratio threshold above which a residual is a naming variant.
_RECOVER = 88


def _fold(s: str | None) -> str:
    """Vietnamese diacritics → ASCII, drop plant-type noise words, normalise."""
    s = (s or "").replace("Đ", "D").replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\b(nd|tbkhh|tbk|nhiet dien|ccgt|gt)\b", "", s.lower())
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def _parse_wikitable(text: str) -> list[str]:
    """First-column (plant name) of each data row of the first wikitable."""
    if "{|" not in text:
        return []
    table = text.split("{|", 1)[1].split("|}", 1)[0]
    names: list[str] = []
    for row in table.split("\n|-"):
        cells = [c.strip() for c in re.split(r"\n\|", row) if c.strip()]
        cells = [c for c in cells if not c.startswith("!") and "class=" not in c and "width=" not in c]
        if not cells:
            continue
        nm = re.sub(r"\[\[|\]\]|'''|<ref.*?</ref>|<ref.*?/>", "", cells[0]).split("|")[0].strip()
        nm = re.sub(r"\s+(gas|coal)?\s*power (plant|station).*$", "", nm, flags=re.I).strip()
        if nm and len(nm) > 2 and "Station" not in nm and "Power plant" not in nm:
            names.append(nm)
    return names


def _gas_section(text: str) -> str:
    """The ``==Gas turbines==`` section of the general Wikipedia power page."""
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("==Gas turbines=="):
            in_section = True
        elif re.match(r"^==[^=]", line) and "Gas turbines" not in line:
            in_section = False
        if in_section:
            out.append(line)
    return "\n".join(out)


def _names_to_plants(names: list[str]):
    """Wrap bare source names as zero-capacity Plants so the matcher can score them."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "capacity_mwe", "fuel", "status"])
        for nm in names:
            w.writerow([nm, "0", "", ""])
        path = Path(f.name)
    plants = load_plants_csv(path)
    path.unlink(missing_ok=True)
    return plants


def _wikipedia_names() -> list[str]:
    coal = _parse_wikitable(_WIKI_COAL.read_text(encoding="utf-8"))
    gas = _parse_wikitable(_gas_section(_WIKI_POWER.read_text(encoding="utf-8")))
    return sorted(set(coal) | set(gas))


def _reviewed_coverage(ref_plants, source_plants, source_names: list[str]) -> tuple[set[str], set[str]]:
    """Return (raw-matched, reviewed-covered) reference names for a source.

    Reviewed = raw-matched ∪ ASCII-fold-recovered residuals (naming variants).
    """
    entries = reconcile(ref_plants, source_plants)
    matched = {e.reference_name for e in entries if e.match_type in _MATCHED and e.reference_name}
    folded_src = [_fold(n) for n in source_names]
    covered = set(matched)
    for p in ref_plants:
        if p.name in matched:
            continue
        fr = _fold(p.name)
        if any(fuzz.partial_ratio(fr, fs) >= _RECOVER for fs in folded_src):
            covered.add(p.name)
    return matched, covered


def _gem_only(ref_plants, gem_plants) -> list:
    """GEM plants absent from the reference after ASCII-fold review (the GEM tail)."""
    entries = reconcile(ref_plants, gem_plants)
    raw = [e.system_name for e in entries if e.match_type == MatchType.SYSTEM_ONLY and e.system_name]
    folded_ref = [_fold(p.name) for p in ref_plants]
    gem_by_name = {p.name: p for p in gem_plants}
    out = []
    for name in raw:
        fg = _fold(name)
        if max((fuzz.partial_ratio(fg, fr) for fr in folded_ref), default=0) < _RECOVER:
            if name in gem_by_name:
                out.append(gem_by_name[name])
    return out


def build_concordance() -> tuple[list[dict], dict]:
    """Compute the per-status concordance rows and the headline aggregates."""
    ref_plants = load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV)
    gem_plants = load_plants_csv(GEM_THERMAL_REFERENCE_CSV)
    gem_names = [
        r["Name"].strip()
        for r in csv.DictReader(GEM_THERMAL_REFERENCE_CSV.open(encoding="utf-8"))
        if r.get("Name")
    ]
    wiki_names = _wikipedia_names()

    gem_raw, gem_cov = _reviewed_coverage(ref_plants, gem_plants, gem_names)
    wiki_raw, wiki_cov = _reviewed_coverage(ref_plants, _names_to_plants(wiki_names), wiki_names)
    gem_only = _gem_only(ref_plants, gem_plants)

    def bucket(p) -> str:
        return p.status.value if p.status else "unknown"

    ref_status = {p.name: bucket(p) for p in ref_plants}
    gem_only_by_status = Counter(bucket(p) for p in gem_only)

    rows: list[dict] = []
    for status in STATUS_ORDER:
        names = [n for n, s in ref_status.items() if s == status]
        n_ref = len(names)
        gem_m = sum(1 for n in names if n in gem_cov)
        wiki_m = sum(1 for n in names if n in wiki_cov)
        rows.append(
            {
                "status": STATUS_LABELS_EN[status],
                "n_reference": n_ref,
                "gem_matched": gem_m,
                "gem_reference_only": n_ref - gem_m,
                "gem_only": gem_only_by_status.get(status, 0),
                "wiki_matched": wiki_m,
                "wiki_reference_only": n_ref - wiki_m,
            }
        )

    n = reference_plant_count()
    total = {
        "status": "All",
        "n_reference": n,
        "gem_matched": sum(r["gem_matched"] for r in rows),
        "gem_reference_only": sum(r["gem_reference_only"] for r in rows),
        "gem_only": len(gem_only),
        "wiki_matched": sum(r["wiki_matched"] for r in rows),
        "wiki_reference_only": sum(r["wiki_reference_only"] for r in rows),
    }
    rows.append(total)

    aggregates = {
        "n_reference": n,
        "gem_distinct": len({p.name for p in gem_plants}),
        "gem_raw": len(gem_raw),
        "gem_reviewed": total["gem_matched"],
        "gem_reviewed_pct": round(total["gem_matched"] / n * 100),
        "wiki_raw": len(wiki_raw),
        "wiki_reviewed": total["wiki_matched"],
        "wiki_reviewed_pct": round(total["wiki_matched"] / n * 100),
        "gem_only": len(gem_only),
    }
    return rows, aggregates


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "status",
        "n_reference",
        "gem_matched",
        "gem_reference_only",
        "gem_only",
        "wiki_matched",
        "wiki_reference_only",
    ]
    with output.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote source concordance table to %s (%d status rows)", output, len(rows) - 1)


def write_macros(agg: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "% Auto-generated by aedist.tabulate_source_concordance — do not edit.",
        f"\\newcommand{{\\GemDistinct}}{{{agg['gem_distinct']}}}",
        f"\\newcommand{{\\GemReviewed}}{{{agg['gem_reviewed']}}}",
        f"\\newcommand{{\\GemReviewedPct}}{{{agg['gem_reviewed_pct']}}}",
        f"\\newcommand{{\\GemOnly}}{{{agg['gem_only']}}}",
        f"\\newcommand{{\\WikiReviewed}}{{{agg['wiki_reviewed']}}}",
        f"\\newcommand{{\\WikiReviewedPct}}{{{agg['wiki_reviewed_pct']}}}",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote concordance macros to %s", output)


def write_table(rows: list[dict], output: Path) -> None:
    """Annex table body (booktabs tabular) for \\input from main.tex.

    Same column selection as the hand-typed table it replaces; the All row is
    bold. Caption and label stay in main.tex (prose), only numbers live here.
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    def cells(r: dict) -> list[str]:
        return [
            str(r[k]) for k in ("status", "n_reference", "gem_matched", "gem_only", "wiki_matched")
        ]

    lines = [
        "% Auto-generated by aedist.tabulate_source_concordance — do not edit.",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "Status & Reference & GEM matched & GEM-only & Wikipedia matched \\\\",
        "\\midrule",
    ]
    for r in rows:
        row_cells = cells(r)
        if r["status"] == "All":
            lines.append("\\midrule")
            row_cells = [f"\\textbf{{{c}}}" for c in row_cells]
        lines.append(" & ".join(row_cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote concordance annex table body to %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate the reference vs GEM/Wikipedia source concordance")
    parser.add_argument("--csv", type=Path, default=SOURCE_CONCORDANCE_CSV)
    parser.add_argument(
        "--macros", type=Path, default=Path("report/inputs/generated/macros_source_concordance.tex")
    )
    parser.add_argument(
        "--table", type=Path, default=Path("report/inputs/generated/tab_source_concordance.tex")
    )
    args = parser.parse_args(argv)

    rows, agg = build_concordance()
    write_csv(rows, args.csv)
    write_macros(agg, args.macros)
    write_table(rows, args.table)
    log.info(
        "GEM %d raw -> %d reviewed (%d%%); Wikipedia %d raw -> %d reviewed (%d%%); GEM-only %d",
        agg["gem_raw"],
        agg["gem_reviewed"],
        agg["gem_reviewed_pct"],
        agg["wiki_raw"],
        agg["wiki_reviewed"],
        agg["wiki_reviewed_pct"],
        agg["gem_only"],
    )


if __name__ == "__main__":
    main()
