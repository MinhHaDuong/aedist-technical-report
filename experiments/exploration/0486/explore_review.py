"""0486 prototype: light matcher review. For the reference plants the project
matcher marked absent from GEM / Wikipedia, ASCII-fold (Vietnamese diacritics →
ASCII) and re-match loosely to separate naming-variant misses (recoverable → real
coverage) from true absences. Corrects the raw matcher-floored bar counts.

Run from repo root:  uv run python experiments/exploration/0486/explore_review.py
Reproduces the 0486 ticket numbers: GEM 120→159 (88%), Wikipedia 90→131 (73%).
"""

import csv
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from aedist.config import GEM_THERMAL_REFERENCE_CSV, VN_THERMAL_PLANTS_RELEASE_CSV
from aedist.evaluate import load_plants_csv
from aedist.reconcile import reconcile
from aedist.schema import MatchType

MATCHED = {MatchType.EXACT, MatchType.EXACT_CAPACITY_DIFF, MatchType.FUZZY, MatchType.FUZZY_CAPACITY_DIFF}
RAW = Path("data/reference/raw")
RECOVER = 88  # ascii-folded partial_ratio threshold to call a residual a variant


def fold(s):
    s = (s or "").replace("Đ", "D").replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\b(nd|tbkhh|tbk|nhiet dien|ccgt|gt)\b", "", s.lower())
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def parse_wikitable(text):
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
        ref_status[r["name"].strip()] = re.sub(r"^\d+\s+", "", (r.get("status") or "").strip())


def names_to_plants(names):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "capacity_mwe", "fuel", "status"])
        for nm in names:
            w.writerow([nm, "0", "", ""])
        p = Path(f.name)
    pl = load_plants_csv(p)
    p.unlink(missing_ok=True)
    return pl


def review(source_plants, source_raw_names, label):
    entries = reconcile(ref_plants, source_plants)
    matched = {getattr(e, "reference_name", None) for e in entries if e.match_type in MATCHED}
    matched.discard(None)
    residual = [p.name for p in ref_plants if p.name not in matched]
    folded_src = [(fold(n), n) for n in source_raw_names]

    recovered, absent = [], []
    for rn in residual:
        fr = fold(rn)
        best, cand = 0, ""
        for fs, orig in folded_src:
            sc = fuzz.partial_ratio(fr, fs)
            if sc > best:
                best, cand = sc, orig
        (recovered if best >= RECOVER else absent).append((rn, cand, best))

    n = len(ref_plants)
    raw = len(matched)
    corr = raw + len(recovered)
    print(f"\n===== {label} =====")
    print(f"  raw matcher coverage:        {raw}/{n}  ({raw / n:.0%})")
    print(f"  + ascii-fold recovered:      {len(recovered)}  (naming-variant misses)")
    print(f"  = corrected coverage:        {corr}/{n}  ({corr / n:.0%})")
    print(f"  true absences:               {len(absent)}")
    print("  recovered examples (ref → source candidate @score):")
    for rn, cand, sc in recovered[:10]:
        print(f"     {rn:28} → {cand} @{sc}")
    print("  true-absence by status:")
    for st, c in Counter(ref_status.get(rn, "?") for rn, _, _ in absent).most_common():
        print(f"     {st:16} {c}")
    return raw, corr, len(absent)


gem_plants = load_plants_csv(GEM_THERMAL_REFERENCE_CSV)
gem_raw_names = [r["Name"] for r in csv.DictReader(open(GEM_THERMAL_REFERENCE_CSV, encoding="utf-8")) if r.get("Name")]
g_raw, g_corr, _ = review(gem_plants, gem_raw_names, "GEM")

coal = parse_wikitable((RAW / "wikipedia_coal_vietnam-2026-06-09.wikitext").read_text(encoding="utf-8"))
gas = parse_wikitable(gas_section((RAW / "wikipedia_power_vietnam-2026-06-09.wikitext").read_text(encoding="utf-8")))
wiki_names = sorted(set(coal) | set(gas))
w_raw, w_corr, _ = review(names_to_plants(wiki_names), wiki_names, "WIKIPEDIA (coal+gas)")

print("\n=== CORRECTED BARS (after light review) ===")
print(f"  Wikipedia: {w_raw} raw → {w_corr} corrected")
print(f"  GEM:       {g_raw} raw → {g_corr} corrected")
print(f"  GEM − Wikipedia gap: {g_raw - w_raw} raw → {g_corr - w_corr} corrected")
