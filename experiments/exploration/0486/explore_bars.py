"""0486 prototype: source-coverage 'bars' — GEM and Wikipedia (coal+gas) coverage
of the reference, aggregate and built-fleet. Answers: does the GEM count differ
from the Wikipedia count (→ show/no-show the Exp2 GEM bar)?

Run from the repo root:  uv run python experiments/exploration/0486/explore_bars.py
Reproduces the 0486 ticket numbers (Wikipedia 90 raw, GEM 120 raw aggregate).
"""

import csv
import re
import tempfile
from pathlib import Path

from aedist.config import GEM_THERMAL_REFERENCE_CSV, VN_THERMAL_PLANTS_RELEASE_CSV
from aedist.evaluate import load_plants_csv
from aedist.reconcile import reconcile
from aedist.schema import MatchType

MATCHED = {MatchType.EXACT, MatchType.EXACT_CAPACITY_DIFF, MatchType.FUZZY, MatchType.FUZZY_CAPACITY_DIFF}
RAW = Path("data/reference/raw")
BUILT = {"operating", "construction", "permitted"}


def status_label(raw):
    return re.sub(r"^\d+\s+", "", (raw or "").strip()) or "?"


def parse_wikitable(text):
    """Yield the first-column (name) of each data row of the first wikitable."""
    if "{|" not in text:
        return []
    table = text.split("{|", 1)[1].split("|}", 1)[0]
    names = []
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


def gas_section(text):
    out, g = [], False
    for line in text.splitlines():
        if line.startswith("==Gas turbines=="):
            g = True
        elif re.match(r"^==[^=]", line) and "Gas turbines" not in line:
            g = False
        if g:
            out.append(line)
    return "\n".join(out)


ref_plants = load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV)
ref_status = {}
with open(VN_THERMAL_PLANTS_RELEASE_CSV, newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        ref_status[r["name"].strip()] = status_label(r.get("status", ""))
print(f"reference: {len(ref_plants)} plants  ({sum(1 for s in ref_status.values() if s in BUILT)} built-fleet)")

coal = parse_wikitable((RAW / "wikipedia_coal_vietnam-2026-06-09.wikitext").read_text(encoding="utf-8"))
gas = parse_wikitable(gas_section((RAW / "wikipedia_power_vietnam-2026-06-09.wikitext").read_text(encoding="utf-8")))
wiki_names = sorted(set(coal) | set(gas))
print(f"Wikipedia thermal names: {len(coal)} coal + {len(gas)} gas = {len(wiki_names)} unique")


def to_plants(names):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "capacity_mwe", "fuel", "status"])
        for nm in names:
            w.writerow([nm, "0", "", ""])
        p = Path(f.name)
    pl = load_plants_csv(p)
    p.unlink(missing_ok=True)
    return pl


def coverage(source_plants, label):
    entries = reconcile(ref_plants, source_plants)
    agg = built = 0
    for e in entries:
        rn = getattr(e, "reference_name", None)
        if not rn or e.match_type not in MATCHED:
            continue
        agg += 1
        if ref_status.get(rn) in BUILT:
            built += 1
    n_ref = len(ref_plants)
    n_built = sum(1 for s in ref_status.values() if s in BUILT)
    print(f"\n{label} bar:")
    print(f"  aggregate (all statuses): {agg}/{n_ref}  ({agg / n_ref:.0%})")
    print(f"  built-fleet only:         {built}/{n_built}  ({built / n_built:.0%})")
    return agg, built


wiki_agg, wiki_built = coverage(to_plants(wiki_names), "WIKIPEDIA (coal+gas)")
gem_agg, gem_built = coverage(load_plants_csv(GEM_THERMAL_REFERENCE_CSV), "GEM")

print("\n=== DOES GEM DIFFER FROM WIKIPEDIA? ===")
print(f"  aggregate:  Wikipedia {wiki_agg}  vs  GEM {gem_agg}   (Δ={abs(wiki_agg - gem_agg)})")
print(f"  built-fleet: Wikipedia {wiki_built}  vs  GEM {gem_built}   (Δ={abs(wiki_built - gem_built)})")
