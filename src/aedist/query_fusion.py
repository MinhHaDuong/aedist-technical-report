"""Fusion pipeline entry point — wraps prototype_v1_fusion for the worker/sweep arch.

Fusion is different from the model-loop methods (RAG, decomposed, etc.):
- It takes a *single* model as a string (not a models.yaml file).
- It does not iterate over a model registry; each sweep run is one cell comparison.
- Outputs go to ``derived/fusion_proto/`` (not ``outputs/``).
- Results are not in measurements.jsonl format; they are saved as JSON in the
  output directory by the prototype's own serialisation helpers.

Accordingly, ``run_fusion`` skips the ``load_models`` + per-model loop and calls
the prototype pipeline functions directly.

CLI usage (standalone sweep run)::

    uv run query-fusion --sweep fusion_dev

Worker dispatch: ``worker.py`` calls ``_execute_fusion(job)`` which delegates here.
"""

import argparse
import json
import logging
import time
from pathlib import Path

from .config import DEFAULT_REFERENCE
from .evaluate import load_plants_csv
from .harness import load_experiments, make_client
from .prototype_v1_fusion import (
    _EXTRACT_PROMPT,
    _FUSE_PROMPT,
    _GLOBAL_MD_PROMPT,
    _GLOBAL_PROMPT,
    DEFAULT_SEQUENCE,
    _save_plants_csv,
    dicts_to_plants,
    master_to_plants,
    run_global,
    run_global_md,
    run_incremental,
    run_incremental_direct,
    save_master_csv,
    save_provenance,
    score_against_reference,
)

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CORPUS = _PROJECT_ROOT / "data" / "rag_corpus"

# Keys in experiments.toml [sweeps.fusion*] that query_fusion.py reads.
_FUSION_SWEEP_KEYS = frozenset(
    {
        "model",
        "seed",
        "provider",
        "corpus",
        "reference",
        "output",
        "fusion_mode",
        "format",
        "fragments",
    }
)


def run_fusion(
    model: str,
    corpus_dir: Path,
    output_dir: Path,
    fusion_mode: str = "compare",
    fmt: str = "md",
    fragments: int | None = None,
    seed: int | None = None,
    provider: str | None = None,
    reference: Path | None = None,
) -> dict:
    """Run fusion pipeline for one model and return a summary dict.

    Parameters
    ----------
    model:
        OpenRouter model ID, e.g. ``openai/gpt-4o-mini``.
    corpus_dir:
        Path to the rag_corpus directory (must contain .md fragment files).
    output_dir:
        Directory where per-cell CSV outputs are written.
    fusion_mode:
        ``"incremental"``, ``"global"``, or ``"compare"`` (all cells).
    fmt:
        Intermediate representation: ``"md"``, ``"json"``, or ``"both"``
        (``"both"`` requires ``fusion_mode == "compare"``).
    fragments:
        Limit to first N fragments from the default sequence.
    seed:
        RNG seed forwarded to every LLM call (best-effort).
    provider:
        Pin OpenRouter provider, e.g. ``"Alibaba"`` for DeepSeek.
    reference:
        Path to reference CSV for F1 scoring (defaults to config.DEFAULT_REFERENCE).

    Returns
    -------
    dict
        Summary with keys: ``cells``, ``model``, ``fusion_mode``, ``format``,
        ``n_fragments``, ``wall_seconds``.
    """
    if reference is None:
        reference = DEFAULT_REFERENCE

    sequence = DEFAULT_SEQUENCE
    if fragments is not None:
        sequence = sequence[:fragments]

    client = make_client()

    api_kw: dict = {}
    if seed is not None:
        api_kw["seed"] = seed
    if provider:
        api_kw["extra_body"] = {"provider": {"order": [provider], "allow_fallbacks": False}}

    ref_plants = load_plants_csv(reference) if reference.exists() else []

    output_dir.mkdir(parents=True, exist_ok=True)

    cells: dict[str, dict] = {}
    t0 = time.monotonic()

    run_global_md_cell = fmt in ("md", "both") and fusion_mode in ("global", "compare")
    run_global_json_cell = fmt in ("json", "both") and fusion_mode in ("global", "compare")
    run_inc_md_cell = fmt in ("md", "both") and fusion_mode in ("incremental", "compare")
    run_inc_json_cell = fmt in ("json", "both") and fusion_mode in ("incremental", "compare")

    if run_global_md_cell:
        log.info("[global×md]")
        plants = run_global_md(corpus_dir, sequence, client, model, _GLOBAL_MD_PROMPT, **api_kw)
        scores = score_against_reference(plants, ref_plants)
        cells["global×md"] = scores
        log.info("  plants=%d  F1=%.1f%%", scores["system_count"], scores["f1"] * 100)
        if fusion_mode == "global":
            out = output_dir / "global_md"
            out.mkdir(parents=True, exist_ok=True)
            _save_plants_csv(plants, out / "master.csv")

    if run_global_json_cell:
        log.info("[global×json]")
        plants_raw = run_global(corpus_dir, sequence, client, model, _GLOBAL_PROMPT, **api_kw)
        plants = dicts_to_plants(plants_raw)
        scores = score_against_reference(plants, ref_plants)
        cells["global×json"] = scores
        log.info("  plants=%d  F1=%.1f%%", scores["system_count"], scores["f1"] * 100)
        if fusion_mode == "global":
            from .prototype_v1_fusion import _save_global_csv

            _save_global_csv(plants_raw, output_dir / "global_json" / "master.csv")

    if run_inc_md_cell:
        log.info("[incremental×md]")
        plants, diffs = run_incremental_direct(
            corpus_dir, sequence, client, model, _FUSE_PROMPT, **api_kw
        )
        scores = score_against_reference(plants, ref_plants)
        cells["incremental×md"] = scores
        log.info("  plants=%d  F1=%.1f%%", scores["system_count"], scores["f1"] * 100)
        if fusion_mode == "incremental":
            out = output_dir / "incremental_md"
            out.mkdir(parents=True, exist_ok=True)
            _save_plants_csv(plants, out / "master.csv")

    if run_inc_json_cell:
        log.info("[incremental×json]")
        master, diffs = run_incremental(
            corpus_dir, sequence, client, model, _EXTRACT_PROMPT, **api_kw
        )
        plants = master_to_plants(master)
        scores = score_against_reference(plants, ref_plants)
        cells["incremental×json"] = scores
        log.info("  plants=%d  F1=%.1f%%", scores["system_count"], scores["f1"] * 100)
        if fusion_mode == "incremental":
            out = output_dir / "incremental_json"
            save_master_csv(master, out / "master.csv")
            save_provenance(master, out / "master_provenance.json")

    wall_seconds = time.monotonic() - t0

    # Save summary JSON
    summary = {
        "model": model,
        "fusion_mode": fusion_mode,
        "format": fmt,
        "n_fragments": len(sequence),
        "cells": cells,
        "wall_seconds": round(wall_seconds, 2),
    }
    summary_path = output_dir / "fusion_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info("Saved fusion summary: %s", summary_path)

    return summary


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for standalone fusion sweep runs."""
    p = argparse.ArgumentParser(
        description="Run fusion pipeline for one sweep configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--sweep",
        required=True,
        metavar="NAME",
        help="Load parameters from [sweeps.NAME] in experiments.toml",
    )
    p.add_argument(
        "--experiments",
        default="experiments/experiments.toml",
        metavar="FILE",
        help="Path to experiments.toml",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Override model from sweep config",
    )
    p.add_argument(
        "--fusion-mode",
        dest="fusion_mode",
        choices=["incremental", "global", "compare"],
        default=None,
        help="Override fusion_mode from sweep config",
    )
    p.add_argument(
        "--format",
        choices=["json", "md", "both"],
        default=None,
        help="Override format from sweep config",
    )
    p.add_argument("--fragments", type=int, default=None, help="Limit to first N fragments")
    p.add_argument("--output", default=None, help="Override output directory")
    p.add_argument("--verbose", action="store_true")

    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    exps = load_experiments(args.experiments)
    sweep_cfg = exps.get("sweeps", {}).get(args.sweep)
    if sweep_cfg is None:
        p.error(f"Sweep '{args.sweep}' not found in {args.experiments}")

    model = args.model or sweep_cfg.get("model", "openai/gpt-4o-mini")
    fusion_mode = args.fusion_mode or sweep_cfg.get("fusion_mode", "compare")
    fmt = args.format or sweep_cfg.get("format", "md")
    fragments = args.fragments or sweep_cfg.get("fragments")
    output_dir = Path(args.output or sweep_cfg.get("output", "derived/fusion_proto"))
    corpus_dir = Path(sweep_cfg.get("corpus", str(_DEFAULT_CORPUS)))
    reference = Path(sweep_cfg.get("reference", str(DEFAULT_REFERENCE)))
    seed = sweep_cfg.get("seed")
    provider = sweep_cfg.get("provider")

    if fmt == "both" and fusion_mode != "compare":
        p.error("--format both is only valid with --fusion-mode compare")

    log.info(
        "Fusion sweep=%s model=%s fusion_mode=%s format=%s fragments=%s",
        args.sweep,
        model,
        fusion_mode,
        fmt,
        fragments,
    )

    summary = run_fusion(
        model=model,
        corpus_dir=corpus_dir,
        output_dir=output_dir,
        fusion_mode=fusion_mode,
        fmt=fmt,
        fragments=fragments,
        seed=seed,
        provider=provider,
        reference=reference,
    )

    if len(summary["cells"]) >= 2:
        print("\nCOMPARISON")
        print("=" * 60)
        hdr = f"  {'Cell':<22} {'n':>5} {'coverage':>9} {'precision':>10} {'F1':>7}"
        print(hdr)
        for cell_name, sc in summary["cells"].items():
            print(
                f"  {cell_name:<22} {sc['system_count']:>5} "
                f"{sc['coverage']:>9.1%} {sc['precision']:>10.1%} {sc['f1']:>7.1%}"
            )
    else:
        for cell_name, sc in summary["cells"].items():
            print(
                f"{cell_name}: plants={sc['system_count']}  "
                f"F1={sc['f1']:.1%}  coverage={sc['coverage']:.1%}"
            )

    log.info("Done. Wall time: %.1fs", summary["wall_seconds"])


if __name__ == "__main__":
    main()
