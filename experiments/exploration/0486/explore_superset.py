"""0486 prototype: is the reference a strict superset of GEM? Count GEM plants
NOT in the reference (GEM-only), with ASCII-fold review so naming variants don't
inflate it.

Run from repo root:  uv run python experiments/exploration/0486/explore_superset.py
Reproduces the 0486 ticket numbers: GEM 153 rows / 119 distinct; 11 true GEM-only.
"""

import csv
import re
import unicodedata

from rapidfuzz import fuzz

from aedist.config import GEM_THERMAL_REFERENCE_CSV, VN_THERMAL_PLANTS_RELEASE_CSV
from aedist.evaluate import load_plants_csv
from aedist.reconcile import reconcile
from aedist.schema import MatchType

MATCHED = {MatchType.EXACT, MatchType.EXACT_CAPACITY_DIFF, MatchType.FUZZY, MatchType.FUZZY_CAPACITY_DIFF}
RECOVER = 88


def fold(s):
    s = (s or "").replace("Đ", "D").replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\b(nd|tbkhh|tbk|nhiet dien|ccgt|gt)\b", "", s.lower())
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


ref_plants = load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV)
gem_plants = load_plants_csv(GEM_THERMAL_REFERENCE_CSV)
gem_rows = list(csv.DictReader(open(GEM_THERMAL_REFERENCE_CSV, encoding="utf-8")))
folded_ref = [fold(p.name) for p in ref_plants]

print(f"GEM rows: {len(gem_rows)}   |   reference rows: {len(ref_plants)}")
print(f"GEM distinct names: {len({r['Name'].strip() for r in gem_rows})}")
print(f"GEM status values: {sorted({r.get('Status', '').strip() for r in gem_rows})}\n")

# reconcile(ref, gem): SYSTEM_ONLY = GEM-only (in GEM, not matched to reference)
entries = reconcile(ref_plants, gem_plants)
gem_only_raw = [getattr(e, "system_name", None) for e in entries if e.match_type == MatchType.SYSTEM_ONLY]
gem_only_raw = [n for n in gem_only_raw if n]

true_gem_only, recovered = [], []
for gn in gem_only_raw:
    fg = fold(gn)
    best = max((fuzz.partial_ratio(fg, fr) for fr in folded_ref), default=0)
    (recovered if best >= RECOVER else true_gem_only).append((gn, best))

print(f"GEM-only (raw matcher):     {len(gem_only_raw)} GEM plants not matched to reference")
print(f"  - ascii-fold recovered:   {len(recovered)} (were naming variants)")
print(f"  = TRUE GEM-only:          {len(true_gem_only)}\n")

if not true_gem_only:
    print(">>> STRICT SUPERSET: every GEM plant is in the reference (reference superset of GEM).")
else:
    print(f">>> NOT a strict superset - {len(true_gem_only)} GEM plant(s) absent from the reference:")
    gem_by_name = {r["Name"].strip(): r for r in gem_rows}
    for gn, best in sorted(true_gem_only, key=lambda t: t[1]):
        r = gem_by_name.get(gn, {})
        print(f"    {gn:34} {r.get('Fuel', '?'):6} {r.get('Capacity', '?'):>7} MW  {r.get('Status', '?'):14} (fold {best:.0f})")
