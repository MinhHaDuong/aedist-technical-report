"""Incremental vs. global fusion prototype (v1).

Demonstrates master + fragment → master' with per-cell provenance (incremental),
and compares against single-shot global LLM synthesis (global).

Usage::

    # Run incremental on first 4 fragments, print diffs:
    python -m aedist.prototype_v1_fusion --mode incremental --fragments 4

    # Run global fusion on same 4 fragments:
    python -m aedist.prototype_v1_fusion --mode global --fragments 4

    # Compare both on F1 against reference:
    python -m aedist.prototype_v1_fusion --mode compare --fragments 4

    # Custom fragment order (order-sensitivity probe):
    python -m aedist.prototype_v1_fusion --mode compare \\
        --sequence PDP8_annex2_table1.md PDP7_annex1.md EVN_Annual_Report_2018_CapacitiesTable.md

Options:
    --model    LLM for extraction (default: openai/gpt-4o-mini via OpenRouter)
    --output   Directory for master.csv and master_provenance.json
    --corpus   Path to rag_corpus directory
    --reference Path to reference CSV
"""

import argparse
import csv
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from .evaluate import load_plants_csv
from .harness import make_client, query_single_turn
from .metrics import compute_metrics
from .reconcile import reconcile
from .schema import FuelType, Plant, PlantStatus
from .util import strip_diacritics

log = logging.getLogger(__name__)

_DEFAULT_CORPUS = Path(__file__).parent.parent.parent / "data" / "rag_corpus"
_DEFAULT_REF = (
    Path(__file__).parent.parent.parent / "data" / "reference" / "vietnam_thermal_v1.csv"
)
_DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "derived" / "fusion_proto"

ENTITY_THRESHOLD = 72  # rapidfuzz score to consider a name match

# ---------------------------------------------------------------------------
# Fragment registry — chronological, authority-tiered
# Higher tier = wins on conflict (PDP gov doc > EVN/study)
# Within same tier, later year wins
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FragmentSpec:
    filename: str
    source_id: str
    tier: int  # 3=government planning doc, 2=utility/study report
    year: int


DEFAULT_SEQUENCE: list[FragmentSpec] = [
    FragmentSpec("PDP7_annex1.md", "PDP7-2011", 3, 2011),
    FragmentSpec("PDP7_annex2.md", "PDP7-2011", 3, 2011),
    FragmentSpec("PDP7A_annex1_table1.md", "PDP7A-2016", 3, 2016),
    FragmentSpec("PDP7A_annex1_table2.md", "PDP7A-2016", 3, 2016),
    FragmentSpec("PDP7A_annex1_table3.md", "PDP7A-2016", 3, 2016),
    FragmentSpec("PDP8_annex2_table1.md", "PDP8-2023", 3, 2023),
    FragmentSpec("PDP8_annex2_table2.md", "PDP8-2023", 3, 2023),
    FragmentSpec("PDP8_annex2_table3.md", "PDP8-2023", 3, 2023),
    FragmentSpec("PDP8_annex2_table4.md", "PDP8-2023", 3, 2023),
    FragmentSpec("PDP8_annex2_table5.md", "PDP8-2023", 3, 2023),
    FragmentSpec("Report_32_annex1.md", "Rpt32-2020", 2, 2020),
    FragmentSpec("Report_58_annex.md", "Rpt58-2021", 2, 2021),
    FragmentSpec("Study_E542_table_9.1.md", "E542-2019", 2, 2019),
    FragmentSpec("Study_E542_table_9.2.md", "E542-2019", 2, 2019),
    FragmentSpec("Study_E542_table_9.5A.md", "E542-2019", 2, 2019),
    FragmentSpec("EVN_Annual_Report_2010_2011_CapacitiesTable.md", "EVN-2011", 2, 2011),
    FragmentSpec("EVN_Annual_Report_2017_CapacitiesTable.md", "EVN-2017", 2, 2017),
    FragmentSpec("EVN_Annual_Report_2018_CapacitiesTable.md", "EVN-2018", 2, 2018),
]

FIELDS = ("fuel", "capacity_mwe", "status", "province", "cod")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SourcedField:
    value: Any
    source_id: str
    tier: int
    year: int


@dataclass
class MasterRecord:
    name: str
    fuel: SourcedField | None = None
    capacity_mwe: SourcedField | None = None
    status: SourcedField | None = None
    province: SourcedField | None = None
    cod: SourcedField | None = None

    def update_field(self, fname: str, value: Any, spec: FragmentSpec) -> bool:
        """Apply a sourced value; return True if the field changed.

        Authority rule: higher tier wins. Within same tier, later year wins.
        A null incoming value never overwrites an existing value.
        """
        if value is None:
            return False
        current: SourcedField | None = getattr(self, fname)
        incoming = SourcedField(value, spec.source_id, spec.tier, spec.year)
        if current is None:
            setattr(self, fname, incoming)
            return True
        if spec.tier > current.tier or (spec.tier == current.tier and spec.year >= current.year):
            if current.value != value:
                setattr(self, fname, incoming)
                return True
        return False

    def to_plant(self) -> Plant:
        fuel = None
        if self.fuel and self.fuel.value:
            try:
                fuel = FuelType(self.fuel.value.lower())
            except ValueError:
                fuel = None
        status = None
        if self.status and self.status.value:
            sv = self.status.value.lower().replace(" ", "_")
            try:
                status = PlantStatus(sv)
            except ValueError:
                status = None
        cap = self.capacity_mwe.value if self.capacity_mwe else None
        try:
            cap = float(cap) if cap is not None else None
        except (TypeError, ValueError):
            cap = None
        return Plant(
            name=self.name,
            fuel=fuel,
            status=status,
            capacity_mwe=cap,
            province=self.province.value if self.province else None,
        )


@dataclass
class FusionDiff:
    source_id: str
    added: int = 0
    field_updates: int = 0
    unchanged: int = 0


# ---------------------------------------------------------------------------
# LLM extraction prompts
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = (
    "You extract thermal power plant records from Vietnamese government documents. "
    "Return ONLY a valid JSON array, no prose, no markdown fences."
)

_EXTRACT_PROMPT = """\
Extract all thermal power plants (coal, gas, lng, oil) from this document.
Skip hydro, solar, wind, biomass, nuclear.

Return a JSON array. Each object must have these keys (use null if unknown):
  "name"        - plant name (keep Vietnamese diacritics)
  "fuel"        - one of: coal, gas, lng, oil  (null if unclear)
  "capacity_mwe" - number in MWe  (null if unclear)
  "status"      - one of: operational, planned, cancelled, proposed, under_construction  (null if unclear)
  "province"    - Vietnamese province name  (null if unclear)
  "cod"         - year as 4-digit string e.g. "2025"  (null if unclear)

Document:
{text}

JSON array:"""

_GLOBAL_SYSTEM = (
    "You synthesize thermal power plant inventories from multiple Vietnamese government sources. "
    "Return ONLY a valid JSON array, no prose, no markdown fences."
)

_GLOBAL_PROMPT = """\
Synthesize the following {n} source documents into a single deduplicated JSON array \
of thermal power plants in Vietnam (coal, gas, lng, oil only). \
For each plant, use the most authoritative and recent value available. \
Do NOT include provenance — just the best-known values.

Each object: "name", "fuel", "capacity_mwe", "status", "province", "cod" \
(same schema as above; null if unknown).

{sources}

JSON array:"""


# ---------------------------------------------------------------------------
# LLM call helpers
# ---------------------------------------------------------------------------


def _llm_extract(
    text: str, client, model: str, extract_prompt: str = _EXTRACT_PROMPT
) -> list[dict]:
    messages = [
        {"role": "system", "content": _EXTRACT_SYSTEM},
        {"role": "user", "content": extract_prompt.format(text=text[:10000])},
    ]
    result = query_single_turn(client, model, messages, max_tokens=3000, temperature=0)
    raw = result["content"] or ""
    return _parse_json_array(raw)


def _llm_global(
    texts: list[str],
    source_ids: list[str],
    client,
    model: str,
    global_prompt: str = _GLOBAL_PROMPT,
) -> list[dict]:
    sources = "\n\n".join(
        f"=== {sid} ===\n{t[:4000]}" for sid, t in zip(source_ids, texts, strict=False)
    )
    messages = [
        {"role": "system", "content": _GLOBAL_SYSTEM},
        {"role": "user", "content": global_prompt.format(n=len(texts), sources=sources)},
    ]
    result = query_single_turn(client, model, messages, max_tokens=16000, temperature=0)
    raw = result["content"] or ""
    return _parse_json_array(raw)


def _parse_json_array(raw: str) -> list[dict]:
    raw = raw.strip()
    # Strip markdown fences if the model wrapped the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict) and d.get("name")]
        return []
    except json.JSONDecodeError:
        log.warning("JSON parse failed, attempting bracket extraction")
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                return [d for d in data if isinstance(d, dict) and d.get("name")]
            except json.JSONDecodeError:
                pass
        log.error("Could not parse LLM JSON response")
        return []


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------


def _normalize(name: str) -> str:
    return strip_diacritics(name).lower().strip()


def resolve_entity(name: str, master: list[MasterRecord]) -> int | None:
    """Return index of best fuzzy match in master, or None if below threshold."""
    norm = _normalize(name)
    best_score, best_idx = 0, None
    for i, rec in enumerate(master):
        score = fuzz.token_sort_ratio(norm, _normalize(rec.name))
        if score > best_score:
            best_score, best_idx = score, i
    if best_score >= ENTITY_THRESHOLD:
        return best_idx
    return None


# ---------------------------------------------------------------------------
# Incremental fusion engine
# ---------------------------------------------------------------------------


def fuse_fragment(
    master: list[MasterRecord],
    plants: list[dict],
    spec: FragmentSpec,
) -> FusionDiff:
    diff = FusionDiff(source_id=spec.source_id)
    for p in plants:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        idx = resolve_entity(name, master)
        if idx is None:
            # New entity
            rec = MasterRecord(name=name)
            for f in FIELDS:
                v = p.get(f)
                if v is not None:
                    setattr(rec, f, SourcedField(v, spec.source_id, spec.tier, spec.year))
            master.append(rec)
            diff.added += 1
        else:
            # Existing entity — try to update each field
            updated_any = False
            for f in FIELDS:
                if master[idx].update_field(f, p.get(f), spec):
                    diff.field_updates += 1
                    updated_any = True
            if not updated_any:
                diff.unchanged += 1
    return diff


def run_incremental(
    corpus_dir: Path,
    sequence: list[FragmentSpec],
    client,
    model: str,
    extract_prompt: str = _EXTRACT_PROMPT,
) -> tuple[list[MasterRecord], list[FusionDiff]]:
    master: list[MasterRecord] = []
    diffs: list[FusionDiff] = []
    for spec in sequence:
        fragment_path = corpus_dir / spec.filename
        if not fragment_path.exists():
            log.warning("Fragment not found: %s", spec.filename)
            continue
        text = fragment_path.read_text(encoding="utf-8")
        log.info("Extracting from %s ...", spec.source_id)
        plants = _llm_extract(text, client, model, extract_prompt)
        log.info("  → %d plants extracted", len(plants))
        diff = fuse_fragment(master, plants, spec)
        diffs.append(diff)
        print(
            f"  {spec.source_id:<14}  +{diff.added:>3} new  "
            f"{diff.field_updates:>3} field-updates  "
            f"{diff.unchanged:>3} unchanged  "
            f"[total: {len(master)}]"
        )
    return master, diffs


# ---------------------------------------------------------------------------
# Global fusion
# ---------------------------------------------------------------------------


def run_global(
    corpus_dir: Path,
    sequence: list[FragmentSpec],
    client,
    model: str,
    global_prompt: str = _GLOBAL_PROMPT,
) -> list[dict]:
    texts, source_ids = [], []
    for spec in sequence:
        fragment_path = corpus_dir / spec.filename
        if not fragment_path.exists():
            continue
        texts.append(fragment_path.read_text(encoding="utf-8"))
        source_ids.append(spec.source_id)
    log.info("Global fusion: %d fragments → single LLM call", len(texts))
    plants = _llm_global(texts, source_ids, client, model, global_prompt)
    log.info("  → %d plants synthesized", len(plants))
    return plants


# ---------------------------------------------------------------------------
# Metrics against reference
# ---------------------------------------------------------------------------


def master_to_plants(master: list[MasterRecord]) -> list[Plant]:
    return [rec.to_plant() for rec in master]


def dicts_to_plants(dicts: list[dict]) -> list[Plant]:
    plants = []
    for p in dicts:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        fuel = FuelType.UNKNOWN
        if p.get("fuel"):
            try:
                fuel = FuelType(p["fuel"].lower())
            except ValueError:
                pass
        status = PlantStatus.UNKNOWN
        if p.get("status"):
            sv = p["status"].lower().replace(" ", "_")
            try:
                status = PlantStatus(sv)
            except ValueError:
                pass
        cap = None
        try:
            cap = float(p["capacity_mwe"]) if p.get("capacity_mwe") is not None else None
        except (TypeError, ValueError):
            pass
        plants.append(
            Plant(
                name=name, fuel=fuel, status=status, capacity_mwe=cap, province=p.get("province")
            )
        )
    return plants


def score_against_reference(plants: list[Plant], ref_path: Path) -> dict:
    reference = load_plants_csv(ref_path)
    entries = reconcile(reference, plants)
    m = compute_metrics(entries)
    return {
        "coverage": round(m.coverage, 3),
        "precision": round(m.precision, 3),
        "f1": round(m.f1, 3),
        "system_count": len(plants),
        "ref_count": len(reference),
    }


# ---------------------------------------------------------------------------
# Output serialization
# ---------------------------------------------------------------------------


def save_master_csv(master: list[MasterRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "name",
                "fuel",
                "capacity_mwe",
                "status",
                "province",
                "cod",
                "fuel_source",
                "capacity_mwe_source",
                "status_source",
                "province_source",
                "cod_source",
            ]
        )
        for rec in master:
            w.writerow(
                [
                    rec.name,
                    rec.fuel.value if rec.fuel else "",
                    rec.capacity_mwe.value if rec.capacity_mwe else "",
                    rec.status.value if rec.status else "",
                    rec.province.value if rec.province else "",
                    rec.cod.value if rec.cod else "",
                    rec.fuel.source_id if rec.fuel else "",
                    rec.capacity_mwe.source_id if rec.capacity_mwe else "",
                    rec.status.source_id if rec.status else "",
                    rec.province.source_id if rec.province else "",
                    rec.cod.source_id if rec.cod else "",
                ]
            )
    log.info("Saved master CSV: %s (%d plants)", path, len(master))


def save_provenance(master: list[MasterRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for rec in master:
        entry: dict = {"name": rec.name, "fields": {}}
        for f in FIELDS:
            sf: SourcedField | None = getattr(rec, f)
            if sf:
                entry["fields"][f] = {
                    "value": sf.value,
                    "source": sf.source_id,
                    "tier": sf.tier,
                    "year": sf.year,
                }
        out.append(entry)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    log.info("Saved provenance: %s", path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_sequence(args: argparse.Namespace) -> list[FragmentSpec]:
    seq = DEFAULT_SEQUENCE
    if args.sequence:
        by_name = {s.filename: s for s in DEFAULT_SEQUENCE}
        seq = [by_name[fn] for fn in args.sequence if fn in by_name]
    if args.fragments:
        seq = seq[: args.fragments]
    return seq


def _load_prompt(path_or_none: Path | None, default: str) -> str:
    if path_or_none is None:
        return default
    return path_or_none.read_text(encoding="utf-8")


def _save_global_csv(plants_raw: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "fuel", "capacity_mwe", "status", "province", "cod"])
        for p in plants_raw:
            w.writerow(
                [
                    p.get("name", ""),
                    p.get("fuel", ""),
                    p.get("capacity_mwe", ""),
                    p.get("status", ""),
                    p.get("province", ""),
                    p.get("cod", ""),
                ]
            )
    log.info("Saved global CSV: %s (%d plants)", path, len(plants_raw))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--mode", choices=["incremental", "global", "compare"], default="compare")
    p.add_argument(
        "--fragments",
        type=int,
        default=None,
        help="Use only the first N fragments from the sequence (default: all)",
    )
    p.add_argument(
        "--sequence",
        nargs="+",
        metavar="FILENAME",
        help="Explicit fragment filenames in fusion order (overrides default sequence)",
    )
    p.add_argument(
        "--model",
        default="openai/gpt-4o-mini",
        help="LLM model via OpenRouter (default: openai/gpt-4o-mini)",
    )
    p.add_argument(
        "--extract-prompt",
        type=Path,
        default=None,
        metavar="FILE",
        help="Prompt file for per-fragment extraction (default: built-in). "
        "Must contain a {text} placeholder.",
    )
    p.add_argument(
        "--global-prompt",
        type=Path,
        default=None,
        metavar="FILE",
        help="Prompt file for global synthesis (default: built-in). "
        "Must contain {n} and {sources} placeholders.",
    )
    p.add_argument("--corpus", type=Path, default=_DEFAULT_CORPUS)
    p.add_argument("--reference", type=Path, default=_DEFAULT_REF)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    sequence = _build_sequence(args)
    client = make_client()
    extract_prompt = _load_prompt(args.extract_prompt, _EXTRACT_PROMPT)
    global_prompt = _load_prompt(args.global_prompt, _GLOBAL_PROMPT)

    print(f"\nFusion prototype — mode={args.mode}, fragments={len(sequence)}, model={args.model}")
    if args.extract_prompt:
        print(f"  extract-prompt: {args.extract_prompt}")
    if args.global_prompt:
        print(f"  global-prompt:  {args.global_prompt}")
    print("=" * 70)

    if args.mode in ("incremental", "compare"):
        print("\n[Incremental fusion]")
        master, diffs = run_incremental(args.corpus, sequence, client, args.model, extract_prompt)
        inc_plants = master_to_plants(master)
        inc_scores = score_against_reference(inc_plants, args.reference)
        print(f"\n  Final master: {len(master)} plants")
        print(f"  Coverage (recall): {inc_scores['coverage']:.1%}")
        print(f"  Precision:         {inc_scores['precision']:.1%}")
        print(f"  F1:                {inc_scores['f1']:.1%}")

        if args.mode == "incremental":
            out = args.output / "incremental"
            save_master_csv(master, out / "master.csv")
            save_provenance(master, out / "master_provenance.json")

    if args.mode in ("global", "compare"):
        print("\n[Global fusion]")
        global_plants_raw = run_global(args.corpus, sequence, client, args.model, global_prompt)
        global_plants = dicts_to_plants(global_plants_raw)
        global_scores = score_against_reference(global_plants, args.reference)
        print(f"\n  Synthesized: {len(global_plants)} plants")
        print(f"  Coverage (recall): {global_scores['coverage']:.1%}")
        print(f"  Precision:         {global_scores['precision']:.1%}")
        print(f"  F1:                {global_scores['f1']:.1%}")

        if args.mode == "global":
            _save_global_csv(global_plants_raw, args.output / "global" / "master.csv")

    if args.mode == "compare":
        print("\n[Comparison]")
        print(f"  {'Metric':<20} {'Incremental':>12} {'Global':>12} {'Delta':>10}")
        print(f"  {'-' * 56}")
        for key in ("coverage", "precision", "f1"):
            inc_v = inc_scores[key]
            gl_v = global_scores[key]
            delta = inc_v - gl_v
            sign = "+" if delta >= 0 else ""
            print(f"  {key:<20} {inc_v:>11.1%} {gl_v:>11.1%} {sign}{delta:>8.1%}")
        print("\n  Provenance: incremental tracks source per cell; global has none.")

        out = args.output / "compare"
        save_master_csv(master, out / "incremental_master.csv")
        save_provenance(master, out / "incremental_provenance.json")
        _save_global_csv(global_plants_raw, out / "global_master.csv")


if __name__ == "__main__":
    main()
