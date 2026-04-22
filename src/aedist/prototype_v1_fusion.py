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
from .extract import extract_fenced_blocks, fallback_extract_inline_csv, parse_and_canonicalize
from .harness import load_experiments, make_client, query_model
from .metrics import compute_metrics
from .reconcile import reconcile
from .schema import FuelType, Plant, PlantStatus
from .util import strip_diacritics

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CORPUS = _PROJECT_ROOT / "data" / "rag_corpus"
_DEFAULT_REF = _PROJECT_ROOT / "data" / "reference" / "vietnam_thermal_v1.csv"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "derived" / "fusion_proto"
_PROMPT_DIR = _PROJECT_ROOT / "experiments" / "prompts"


def _read_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


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
# Prompts — loaded from experiments/prompts/ at import time
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = _read_prompt("fusion_extract_system.txt")
_EXTRACT_PROMPT = _read_prompt("fusion_extract_user.txt")
_GLOBAL_SYSTEM = _read_prompt("fusion_global_json_system.txt")
_GLOBAL_PROMPT = _read_prompt("fusion_global_json_user.txt")
_FUSE_SYSTEM = _read_prompt("fusion_incremental_md_system.txt")
_FUSE_PROMPT = _read_prompt("fusion_incremental_md_user.txt")
_GLOBAL_MD_PROMPT = _read_prompt("fusion_global_md_user.txt")

# ---------------------------------------------------------------------------
# LLM call helpers
# ---------------------------------------------------------------------------


def _llm_extract(
    text: str, client, model: str, extract_prompt: str = _EXTRACT_PROMPT, **api_kw
) -> list[dict]:
    messages = [
        {"role": "system", "content": _EXTRACT_SYSTEM},
        {"role": "user", "content": extract_prompt.format(text=text[:10000])},
    ]
    result = query_model(client, model, messages, max_tokens=3000, temperature=0, **api_kw)
    raw = result["content"] or ""
    return _parse_json_array(raw)


def _llm_global(
    texts: list[str],
    source_ids: list[str],
    client,
    model: str,
    global_prompt: str = _GLOBAL_PROMPT,
    **api_kw,
) -> list[dict]:
    sources = "\n\n".join(
        f"=== {sid} ===\n{t[:4000]}" for sid, t in zip(source_ids, texts, strict=False)
    )
    messages = [
        {"role": "system", "content": _GLOBAL_SYSTEM},
        {"role": "user", "content": global_prompt.format(n=len(texts), sources=sources)},
    ]
    result = query_model(client, model, messages, max_tokens=16000, temperature=0, **api_kw)
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
    **api_kw,
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
        plants = _llm_extract(text, client, model, extract_prompt, **api_kw)
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
    **api_kw,
) -> list[dict]:
    texts, source_ids = [], []
    for spec in sequence:
        fragment_path = corpus_dir / spec.filename
        if not fragment_path.exists():
            continue
        texts.append(fragment_path.read_text(encoding="utf-8"))
        source_ids.append(spec.source_id)
    log.info("Global fusion: %d fragments → single LLM call", len(texts))
    plants = _llm_global(texts, source_ids, client, model, global_prompt, **api_kw)
    log.info("  → %d plants synthesized", len(plants))
    return plants


# ---------------------------------------------------------------------------
# Markdown-direct modes (no JSON extraction step)
# ---------------------------------------------------------------------------


def _parse_csv_from_response(raw: str) -> list[Plant]:
    import os
    import tempfile

    blocks = extract_fenced_blocks(raw)
    csv_text = blocks[0] if blocks else (fallback_extract_inline_csv(raw) or "")
    if not csv_text.strip():
        log.warning("No CSV found in LLM response")
        return []
    try:
        canonical = parse_and_canonicalize(csv_text)
    except ValueError as e:
        log.warning("CSV canonicalization failed: %s", e)
        canonical = csv_text
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8", delete=False) as f:
        f.write(canonical)
        tmp = f.name
    try:
        return load_plants_csv(Path(tmp))
    finally:
        os.unlink(tmp)


def _llm_fuse_direct(
    master_csv: str,
    fragment_text: str,
    spec: FragmentSpec,
    client,
    model: str,
    fuse_prompt: str = _FUSE_PROMPT,
    **api_kw,
) -> str:
    """One incremental fusion step: master_csv + fragment_md → updated master_csv."""
    n_master = master_csv.count("\n") if master_csv.strip() else 0
    user = fuse_prompt.format(
        n_master=n_master,
        master_csv=master_csv or "(empty — first source)",
        source_id=spec.source_id,
        tier=spec.tier,
        year=spec.year,
        fragment_text=fragment_text[:8000],
    )
    messages = [{"role": "system", "content": _FUSE_SYSTEM}, {"role": "user", "content": user}]
    result = query_model(client, model, messages, max_tokens=8000, temperature=0, **api_kw)
    raw = result["content"] or ""
    blocks = extract_fenced_blocks(raw)
    return blocks[0] if blocks else (fallback_extract_inline_csv(raw) or master_csv)


def run_global_md(
    corpus_dir: Path,
    sequence: list[FragmentSpec],
    client,
    model: str,
    prompt: str,
    **api_kw,
) -> list[Plant]:
    """global × md: all fragments as system context, prompt as user → CSV.

    This replicates the RAG oneshot pipeline exactly.
    """
    texts = []
    for spec in sequence:
        p = corpus_dir / spec.filename
        if p.exists():
            texts.append(p.read_text(encoding="utf-8"))
    corpus_text = "\n---\n".join(texts)
    log.info("Global md: %d fragments, %d chars → single LLM call", len(texts), len(corpus_text))
    messages = [
        {"role": "system", "content": corpus_text},
        {"role": "user", "content": prompt},
    ]
    result = query_model(client, model, messages, temperature=0, **api_kw)
    raw = result["content"] or ""
    log.info("  response: %d chars, finish=%s", len(raw), result["finish_reason"])
    return _parse_csv_from_response(raw)


def run_incremental_direct(
    corpus_dir: Path,
    sequence: list[FragmentSpec],
    client,
    model: str,
    fuse_prompt: str = _FUSE_PROMPT,
    **api_kw,
) -> tuple[list[Plant], list[FusionDiff]]:
    """incremental × md: master_csv + fragment_md → master_csv', no JSON step."""

    def _data_rows(csv: str) -> int:
        n = csv.count("\n")
        return max(0, n - 1) if csv.strip() else 0

    master_csv = ""
    diffs: list[FusionDiff] = []
    for spec in sequence:
        fragment_path = corpus_dir / spec.filename
        if not fragment_path.exists():
            log.warning("Fragment not found: %s", spec.filename)
            continue
        text = fragment_path.read_text(encoding="utf-8")
        prev_data = _data_rows(master_csv)
        log.info("Fusing %s ...", spec.source_id)
        master_csv = _llm_fuse_direct(master_csv, text, spec, client, model, fuse_prompt, **api_kw)
        new_lines = master_csv.count("\n")
        diff = FusionDiff(
            source_id=spec.source_id, added=max(0, _data_rows(master_csv) - prev_data)
        )
        diffs.append(diff)
        print(f"  {spec.source_id:<14}  +{diff.added:>3} rows  [total lines: {new_lines}]")
    plants = _parse_csv_from_response("```csv\n" + master_csv + "\n```")
    return plants, diffs


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


def score_against_reference(plants: list[Plant], ref_path: Path | list[Plant]) -> dict:
    reference = ref_path if isinstance(ref_path, list) else load_plants_csv(ref_path)
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


_SWEEP_TOML_KEYS = frozenset(
    {"model", "seed", "provider", "corpus", "reference", "output", "mode", "format", "fragments"}
)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--experiments",
        default="experiments/experiments.toml",
        metavar="FILE",
        help="Path to experiments.toml (default: experiments/experiments.toml)",
    )
    p.add_argument(
        "--sweep",
        default=None,
        metavar="NAME",
        help="Load parameters from [sweeps.NAME] in experiments.toml. CLI flags override.",
    )
    p.add_argument("--mode", choices=["incremental", "global", "compare"], default="compare")
    p.add_argument(
        "--format",
        choices=["json", "md", "both"],
        default="md",
        help=(
            "Intermediate representation: 'md' = direct CSV from markdown (no JSON step); "
            "'json' = extract→synthesize JSON; 'both' = run all 4 cells (compare mode only)"
        ),
    )
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
        help="[json] Prompt for per-fragment extraction. Must contain {text} placeholder.",
    )
    p.add_argument(
        "--global-prompt",
        type=Path,
        default=None,
        metavar="FILE",
        help="[json] Prompt for global JSON synthesis. Must contain {n} and {sources}.",
    )
    p.add_argument(
        "--global-md-prompt",
        type=Path,
        default=None,
        metavar="FILE",
        help="[md] Prompt for global md mode (≈ RAG oneshot). Default: prompt_structured.txt.",
    )
    p.add_argument(
        "--fuse-prompt",
        type=Path,
        default=None,
        metavar="FILE",
        help="[md] Prompt for each incremental md fusion step. Default: built-in.",
    )
    p.add_argument("--corpus", type=Path, default=_DEFAULT_CORPUS)
    p.add_argument("--reference", type=Path, default=_DEFAULT_REF)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="RNG seed for reproducibility (passed to API; best-effort on most models)",
    )
    p.add_argument(
        "--provider",
        default=None,
        metavar="NAME",
        help="Pin OpenRouter provider, e.g. 'DeepSeek'. Eliminates cross-provider variance.",
    )
    p.add_argument("--verbose", action="store_true")

    # Two-pass: load TOML sweep defaults before final parse so CLI flags override.
    pre, _ = p.parse_known_args(argv)
    if pre.sweep:
        exps = load_experiments(pre.experiments)
        sweep_cfg = exps.get("sweeps", {}).get(pre.sweep)
        if sweep_cfg is None:
            p.error(f"Sweep '{pre.sweep}' not found in {pre.experiments}")
        p.set_defaults(**{k: v for k, v in sweep_cfg.items() if k in _SWEEP_TOML_KEYS})

    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    fmt = args.format
    if fmt == "both" and args.mode != "compare":
        p.error("--format both is only valid with --mode compare")

    sequence = _build_sequence(args)
    client = make_client()

    # Reproducibility kwargs forwarded to every LLM call
    api_kw: dict = {}
    if args.seed is not None:
        api_kw["seed"] = args.seed
    if args.provider:
        api_kw["extra_body"] = {"provider": {"order": [args.provider], "allow_fallbacks": False}}

    # JSON-mode prompts
    extract_prompt = _load_prompt(args.extract_prompt, _EXTRACT_PROMPT)
    global_json_prompt = _load_prompt(args.global_prompt, _GLOBAL_PROMPT)

    # Md-mode prompts
    global_md_prompt = _load_prompt(args.global_md_prompt, _GLOBAL_MD_PROMPT)
    fuse_prompt = _load_prompt(args.fuse_prompt, _FUSE_PROMPT)

    print(
        f"\nFusion prototype — mode={args.mode}, format={fmt}, "
        f"fragments={len(sequence)}, model={args.model}"
        + (f", seed={args.seed}" if args.seed is not None else "")
        + (f", provider={args.provider}" if args.provider else "")
    )
    print("=" * 70)

    # -----------------------------------------------------------------------
    # Collect results per cell: scores[(scope, rep)] = score_dict
    # -----------------------------------------------------------------------
    cells: dict[str, dict] = {}  # key = "global×md" etc.

    run_global_md_cell = fmt in ("md", "both") and args.mode in ("global", "compare")
    run_global_json_cell = fmt in ("json", "both") and args.mode in ("global", "compare")
    run_inc_md_cell = fmt in ("md", "both") and args.mode in ("incremental", "compare")
    run_inc_json_cell = fmt in ("json", "both") and args.mode in ("incremental", "compare")

    ref_plants = load_plants_csv(args.reference) if args.reference else []

    if run_global_md_cell:
        label = "global×md  (≈ RAG oneshot)"
        print(f"\n[{label}]")
        plants = run_global_md(
            args.corpus, sequence, client, args.model, global_md_prompt, **api_kw
        )
        scores = score_against_reference(plants, ref_plants)
        cells["global×md"] = scores
        print(
            f"  plants={scores['system_count']}  coverage={scores['coverage']:.1%}  "
            f"precision={scores['precision']:.1%}  F1={scores['f1']:.1%}"
        )
        if args.mode == "global":
            out = args.output / "global_md"
            out.mkdir(parents=True, exist_ok=True)
            _save_plants_csv(plants, out / "master.csv")

    if run_global_json_cell:
        label = "global×json"
        print(f"\n[{label}]")
        plants_raw = run_global(
            args.corpus, sequence, client, args.model, global_json_prompt, **api_kw
        )
        plants = dicts_to_plants(plants_raw)
        scores = score_against_reference(plants, ref_plants)
        cells["global×json"] = scores
        print(
            f"  plants={scores['system_count']}  coverage={scores['coverage']:.1%}  "
            f"precision={scores['precision']:.1%}  F1={scores['f1']:.1%}"
        )
        if args.mode == "global":
            _save_global_csv(plants_raw, args.output / "global_json" / "master.csv")

    if run_inc_md_cell:
        label = "incremental×md"
        print(f"\n[{label}]")
        plants, diffs = run_incremental_direct(
            args.corpus, sequence, client, args.model, fuse_prompt, **api_kw
        )
        scores = score_against_reference(plants, ref_plants)
        cells["incremental×md"] = scores
        print(
            f"  plants={scores['system_count']}  coverage={scores['coverage']:.1%}  "
            f"precision={scores['precision']:.1%}  F1={scores['f1']:.1%}"
        )
        if args.mode == "incremental":
            out = args.output / "incremental_md"
            out.mkdir(parents=True, exist_ok=True)
            _save_plants_csv(plants, out / "master.csv")

    if run_inc_json_cell:
        label = "incremental×json"
        print(f"\n[{label}]")
        master, diffs = run_incremental(
            args.corpus, sequence, client, args.model, extract_prompt, **api_kw
        )
        plants = master_to_plants(master)
        scores = score_against_reference(plants, ref_plants)
        cells["incremental×json"] = scores
        print(
            f"  plants={scores['system_count']}  coverage={scores['coverage']:.1%}  "
            f"precision={scores['precision']:.1%}  F1={scores['f1']:.1%}"
        )
        if args.mode == "incremental":
            out = args.output / "incremental_json"
            save_master_csv(master, out / "master.csv")
            save_provenance(master, out / "master_provenance.json")

    if args.mode == "compare" and len(cells) >= 2:
        print("\n" + "=" * 70)
        print("COMPARISON")
        print("=" * 70)
        hdr = f"  {'Cell':<22} {'n':>5} {'coverage':>9} {'precision':>10} {'F1':>7}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))
        for cell_name, sc in cells.items():
            print(
                f"  {cell_name:<22} {sc['system_count']:>5} "
                f"{sc['coverage']:>9.1%} {sc['precision']:>10.1%} {sc['f1']:>7.1%}"
            )
        if "global×md" in cells and "incremental×md" in cells:
            gmd = cells["global×md"]
            imd = cells["incremental×md"]
            delta_f1 = imd["f1"] - gmd["f1"]
            sign = "+" if delta_f1 >= 0 else ""
            print(f"\n  Δ F1 (incremental×md − global×md): {sign}{delta_f1:.1%}")
        if "global×md" in cells and "global×json" in cells:
            gmd = cells["global×md"]
            gjson = cells["global×json"]
            delta_f1 = gjson["f1"] - gmd["f1"]
            sign = "+" if delta_f1 >= 0 else ""
            print(f"  Δ F1 (global×json − global×md):    {sign}{delta_f1:.1%}")


def _save_plants_csv(plants: list[Plant], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "fuel", "capacity_mwe", "status", "province", "cod"])
        for pl in plants:
            w.writerow(
                [
                    pl.name,
                    pl.fuel.value if pl.fuel else "",
                    pl.capacity_mwe if pl.capacity_mwe is not None else "",
                    pl.status.value if pl.status else "",
                    pl.province or "",
                    pl.cod or "",
                ]
            )
    log.info("Saved %d plants → %s", len(plants), path)


if __name__ == "__main__":
    main()
