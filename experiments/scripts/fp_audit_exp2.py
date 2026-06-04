"""Sweep, dedup, count and classify every Exp2 false positive (FP).

An FP is a SYSTEM_ONLY reconciliation entry: a plant the model reported that
the LP matcher could not pair with any row of the frozen reference
(``data/reference/vietnam_thermal_v1.csv``). This is the ``hallucinated_plant``
error in ``metrics.py`` — but, as this audit shows, two thirds of these are
reconciliation artefacts, not model hallucination.

Run from the repo root:

    uv run python experiments/scripts/fp_audit_exp2.py

Writes three artefacts under ``experiments/derived/``:
  * ``exp2_fp_occurrences.csv``  — one row per FP occurrence (arm/model/run + attrs)
  * ``exp2_fp_dedup.csv``        — distinct FP plants with appearance counts
  * ``exp2_fp_classified.csv``   — dedup + closest-reference scores + category

The classification buckets are:
  matcher_fail_normalization  plant IS in the reference; recovered once the
                              cleaner drops ``nhiet dien`` / ``nha may`` /
                              ``dong phat`` / ``tbk`` and unifies
                              ``mo rong`` <-> ``extension``.
  matcher_fail_lp_veto        name already matches a reference row at >=90 but
                              the global LP left it unmatched (combined ``X & Y``
                              rows, aggregate-vs-split, base-vs-extension
                              contention, unit-number veto).
  reference_hole              real Vietnamese plant absent from the 163-row
                              reference under any spelling.
  statistical_borderline      mid-similarity, few appearances; ambiguous.
  likely_hallucination        implausible capacity / no such plant.
  other                       out of thermal-fossil scope or below 30 MWe
                              (nuclear, <30 MWe captive cogen).
"""

import argparse
import csv
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz, process

from aedist.cleaner import PowerPlantDataframeCleaner
from aedist.config import DEFAULT_REFERENCE
from aedist.evaluate import load_plants_csv, plants_from_dicts
from aedist.extract import _extract_pipe_tables, parse_and_canonicalize, score_csv_like_block
from aedist.reconcile import reconcile
from aedist.schema import MatchType

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "experiments" / "derived"
ARMS = {
    "arm1": "arm1_flat",  # naive single-shot, no evidence pack
    "arm2": "arm2_flat",  # optimised multi-turn, no evidence pack
    "arm3": "arm3_flat",  # naive single-shot + evidence pack
    "arm4": "arm4_flat",  # optimised multi-turn + evidence pack
}

_CLEANER = PowerPlantDataframeCleaner(
    config_path=str(ROOT / "src" / "aedist" / "cleaner" / "config.json")
)


def _proposed_norm(s: str) -> str:
    """Name normalisation proposed by this audit, on top of the current cleaner."""
    s = s.lower()
    s = re.sub(r"\bnha may\b", " ", s)
    s = re.sub(r"\bnhiet dien\b", " ", s)
    s = re.sub(r"\bdong phat\b", " ", s)
    s = re.sub(r"\btbk\b", " ", s)
    s = re.sub(r"\b(mo rong|mr)\b", "extension", s)
    s = re.sub(r"\s+&\s+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Domain knowledge: real plants verified ABSENT from the reference name list.
_REF_HOLE = [
    "kien luong",
    "hoa phat",
    "kim son",
    "yen hung",
    "rang dong",
    "bao dai",
    "cai lan",
    "luc nam",
]
_OTHER = ["hat nhan", "bourbon", "dam phu my"]  # nuclear / <30 MWe scope
_HALLU = ["phu yen", "than an giang"]  # implausible / non-existent


def _parse_rows(md_path: Path) -> list[dict]:
    text = md_path.read_text(encoding="utf-8")
    candidates = _extract_pipe_tables(text)
    if not candidates:
        return []
    best = max(candidates, key=score_csv_like_block)
    try:
        canonical_csv = parse_and_canonicalize(best)
    except Exception:
        return []
    return list(csv.DictReader(io.StringIO(canonical_csv)))


def sweep(reference_path: Path) -> list[dict]:
    reference = load_plants_csv(reference_path)
    occ: list[dict] = []
    for arm, sub in ARMS.items():
        for md in sorted((DERIVED / sub).glob("*_run*.md")):
            if md.stem.endswith("_bib"):
                continue
            run = int(md.stem.split("_run")[1])
            jpath = md.with_suffix(".json")
            model = json.loads(jpath.read_text())["model"] if jpath.exists() else md.stem
            rows = _parse_rows(md)
            if not rows:
                continue
            system = plants_from_dicts(rows)
            by_name = {p.name: p for p in system}
            for e in reconcile(reference, system):
                if e.match_type != MatchType.SYSTEM_ONLY:
                    continue
                p = by_name.get(e.system_name)
                occ.append(
                    {
                        "arm": arm,
                        "model": model,
                        "run": run,
                        "name": e.system_name or "",
                        "fuel": e.system_fuel or (p.fuel.value if p and p.fuel else ""),
                        "status": (p.status.value if p and p.status else ""),
                        "capacity_mwe": e.system_capacity_mwe
                        if e.system_capacity_mwe is not None
                        else "",
                        "province": e.system_province or "",
                        "clean_name": _CLEANER.clean_name(e.system_name or ""),
                    }
                )
    return occ


def classify(r: dict) -> str:
    cur, new, n = float(r["cur_score"]), float(r["new_score"]), int(r["n_appearances"])
    cn = r["clean_name"]
    for t in _OTHER:
        if t in cn:
            return "other"
    for t in _HALLU:
        if t in cn:
            return "likely_hallucination"
    for t in _REF_HOLE:
        if t in cn:
            return "reference_hole"
    if new >= 88 and cur < 90:
        return "matcher_fail_normalization"
    if cur >= 90:
        return "matcher_fail_lp_veto"
    if "&" in cn:
        return "matcher_fail_combined_units"
    if n <= 2 and 75 <= new < 88:
        return "statistical_borderline"
    if new < 75 and n >= 3:
        return "reference_hole"
    return "statistical_borderline"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="reference CSV to reconcile against (default: frozen v1)",
    )
    ap.add_argument(
        "--label", default="", help="suffix for output filenames, e.g. _v2 (avoids clobbering)"
    )
    args = ap.parse_args()

    occ = sweep(args.reference)
    DERIVED.mkdir(parents=True, exist_ok=True)

    with (DERIVED / f"exp2_fp_occurrences{args.label}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "arm",
                "model",
                "run",
                "name",
                "clean_name",
                "fuel",
                "status",
                "capacity_mwe",
                "province",
            ],
        )
        w.writeheader()
        for o in occ:
            w.writerow({k: o[k] for k in w.fieldnames})

    # Dedup by cleaned name; track appearances and spread.
    groups: dict[str, list[dict]] = defaultdict(list)
    for o in occ:
        groups[o["clean_name"]].append(o)

    # Reference keys under current and proposed normalisation, for scoring.
    ref_rows = list(csv.DictReader(open(args.reference)))
    ref_cur = {_CLEANER.clean_name(r["name"]): r["name"] for r in ref_rows}
    ref_new = {_proposed_norm(_CLEANER.clean_name(r["name"])): r["name"] for r in ref_rows}
    keys_cur, keys_new = list(ref_cur), list(ref_new)

    dedup = []
    for key, occs in groups.items():
        disp = Counter(o["name"] for o in occs).most_common(1)[0][0]
        m = process.extractOne(key, keys_cur, scorer=fuzz.partial_ratio)
        m2 = process.extractOne(_proposed_norm(key), keys_new, scorer=fuzz.partial_ratio)
        dedup.append(
            {
                "clean_name": key,
                "display_name": disp,
                "n_appearances": len(occs),
                "n_models": len({o["model"] for o in occs}),
                "n_arms": len({o["arm"] for o in occs}),
                "models": ";".join(sorted({o["model"] for o in occs})),
                "arms": ";".join(sorted({o["arm"] for o in occs})),
                "fuels": ";".join(sorted({o["fuel"] for o in occs if o["fuel"]})),
                "statuses": ";".join(sorted({o["status"] for o in occs if o["status"]})),
                "capacities": ";".join(
                    sorted({str(o["capacity_mwe"]) for o in occs if o["capacity_mwe"] != ""})
                ),
                "provinces": ";".join(sorted({o["province"] for o in occs if o["province"]})),
                "cur_score": round(m[1], 1) if m else 0.0,
                "cur_ref": ref_cur[m[0]] if m else "",
                "new_score": round(m2[1], 1) if m2 else 0.0,
                "new_ref": ref_new[m2[0]] if m2 else "",
            }
        )
    dedup.sort(key=lambda r: (-r["n_appearances"], -r["n_models"]))

    with (DERIVED / f"exp2_fp_dedup{args.label}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dedup[0].keys()))
        w.writeheader()
        w.writerows(dedup)

    for r in dedup:
        r["category"] = classify(r)
    with (DERIVED / f"exp2_fp_classified{args.label}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(dedup[0].keys()))
        w.writeheader()
        w.writerows(dedup)

    cat_d, cat_o = Counter(), Counter()
    for r in dedup:
        cat_d[r["category"]] += 1
        cat_o[r["category"]] += r["n_appearances"]
    print(f"FP occurrences: {len(occ)}   distinct plants: {len(dedup)}")
    print(f"{'category':<30}{'distinct':>9}{'occ':>7}")
    for c, _ in sorted(cat_o.items(), key=lambda x: -x[1]):
        print(f"{c:<30}{cat_d[c]:>9}{cat_o[c]:>7}")


if __name__ == "__main__":
    main()
