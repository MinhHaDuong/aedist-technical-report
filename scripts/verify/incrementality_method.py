"""Growth-curve probe: incremental vs global F1 as a function of N fragments.

Measures how entity-level F1 grows as fragments are added one by one, comparing
incremental (JSON) fusion against global (JSON) fusion for the same N fragments.

Budget note: single-pass design → 18 incremental LLM calls + 18 global calls = 36
total API calls (matching the stated budget).  A naive "call run_incremental for
each N" would cost 1+2+…+18=171 calls; the single-pass avoids that by scoring
the master after each fuse step, reusing intermediate state.

Usage::

    uv run python scripts/verify/incrementality_method.py
    uv run python scripts/verify/incrementality_method.py --fragments 5
    uv run python scripts/verify/incrementality_method.py --output-dir /tmp/probe
"""

import argparse
import csv
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from aedist.evaluate import load_plants_csv
from aedist.harness import make_client
from aedist.prototype_v1_fusion import (
    DEFAULT_SEQUENCE,
    _llm_extract,
    _llm_global,
    dicts_to_plants,
    fuse_fragment,
    master_to_plants,
    score_against_reference,
)

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CORPUS = _PROJECT_ROOT / "data" / "rag_corpus"
_DEFAULT_REF = _PROJECT_ROOT / "data" / "reference" / "vietnam_thermal_v1.csv"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "derived" / "fusion_proto"
_DEFAULT_MODEL = "openai/gpt-4o-mini"


# ---------------------------------------------------------------------------
# Growth curve computation
# ---------------------------------------------------------------------------


def compute_incremental_growth(
    sequence,
    corpus_dir: Path,
    client,
    model: str,
    ref_plants: list,
) -> list[dict]:
    """Single-pass incremental fusion: score master after each fragment.

    Processes fragments in order, scoring after each fuse step.
    Cost: len(sequence) LLM calls (one extract per fragment).
    """
    master: list = []
    rows = []
    for i, spec in enumerate(sequence, start=1):
        fragment_path = corpus_dir / spec.filename
        if not fragment_path.exists():
            log.warning("Fragment not found: %s", spec.filename)
            continue
        text = fragment_path.read_text(encoding="utf-8")
        log.info("[incremental N=%d] Extracting from %s ...", i, spec.source_id)
        plants_dicts = _llm_extract(text, client, model)
        fuse_fragment(master, plants_dicts, spec)
        plants = master_to_plants(master)
        scores = score_against_reference(plants, ref_plants)
        log.info(
            "  N=%d  plants=%d  F1=%.3f  coverage=%.3f  precision=%.3f",
            i,
            scores["system_count"],
            scores["f1"],
            scores["coverage"],
            scores["precision"],
        )
        rows.append(
            {
                "N": i,
                "mode": "incremental",
                "entity_f1": scores["f1"],
                "coverage": scores["coverage"],
                "precision": scores["precision"],
                "system_count": scores["system_count"],
            }
        )
    return rows


def compute_global_growth(
    sequence,
    corpus_dir: Path,
    client,
    model: str,
    ref_plants: list,
) -> list[dict]:
    """Global fusion for each prefix of length N.

    Each call is independent: concatenate first N fragments, call LLM once.
    Cost: len(sequence) LLM calls (one global call per N).
    """
    rows = []
    for i in range(1, len(sequence) + 1):
        sub_seq = sequence[:i]
        texts, source_ids = [], []
        for spec in sub_seq:
            fragment_path = corpus_dir / spec.filename
            if not fragment_path.exists():
                continue
            texts.append(fragment_path.read_text(encoding="utf-8"))
            source_ids.append(spec.source_id)
        if not texts:
            continue
        log.info("[global N=%d] Synthesizing %d fragments ...", i, len(texts))
        plants_dicts = _llm_global(texts, source_ids, client, model)
        plants = dicts_to_plants(plants_dicts)
        scores = score_against_reference(plants, ref_plants)
        log.info(
            "  N=%d  plants=%d  F1=%.3f  coverage=%.3f  precision=%.3f",
            i,
            scores["system_count"],
            scores["f1"],
            scores["coverage"],
            scores["precision"],
        )
        rows.append(
            {
                "N": i,
                "mode": "global",
                "entity_f1": scores["f1"],
                "coverage": scores["coverage"],
                "precision": scores["precision"],
                "system_count": scores["system_count"],
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def save_growth_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["N", "mode", "entity_f1", "coverage", "precision", "system_count"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    log.info("Saved growth curve CSV: %s (%d rows)", path, len(rows))


def save_growth_pdf(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    inc = [(r["N"], r["entity_f1"]) for r in rows if r["mode"] == "incremental"]
    glb = [(r["N"], r["entity_f1"]) for r in rows if r["mode"] == "global"]

    fig, ax = plt.subplots(figsize=(8, 5))
    if inc:
        xs, ys = zip(*inc, strict=False)
        ax.plot(xs, ys, marker="o", label="incremental (JSON)", linewidth=2)
    if glb:
        xs, ys = zip(*glb, strict=False)
        ax.plot(xs, ys, marker="s", linestyle="--", label="global (JSON)", linewidth=2)

    ax.set_xlabel("Number of fragments (N)")
    ax.set_ylabel("Entity F1")
    ax.set_title("F1 growth curve: incremental vs global fusion")
    ax.legend()
    ax.grid(True, alpha=0.4)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0, top=1.05)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    log.info("Saved growth curve PDF: %s", path)


def print_headlines(rows: list[dict], max_n: int) -> None:
    inc_at_max = next(
        (r for r in reversed(rows) if r["mode"] == "incremental" and r["N"] == max_n), None
    )
    glb_at_max = next(
        (r for r in reversed(rows) if r["mode"] == "global" and r["N"] == max_n), None
    )
    print(f"\n{'=' * 60}")
    print(f"  Growth curve results at N={max_n}")
    print(f"{'=' * 60}")
    if inc_at_max:
        print(
            f"  incremental F1@{max_n}: {inc_at_max['entity_f1']:.3f}"
            f"  (coverage={inc_at_max['coverage']:.3f}"
            f"  precision={inc_at_max['precision']:.3f})"
        )
    if glb_at_max:
        print(
            f"  global      F1@{max_n}: {glb_at_max['entity_f1']:.3f}"
            f"  (coverage={glb_at_max['coverage']:.3f}"
            f"  precision={glb_at_max['precision']:.3f})"
        )
    if inc_at_max and glb_at_max:
        delta = inc_at_max["entity_f1"] - glb_at_max["entity_f1"]
        sign = "+" if delta >= 0 else ""
        print(f"  delta (inc - global): {sign}{delta:.3f}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--fragments",
        type=int,
        default=None,
        metavar="N",
        help="Use only the first N fragments (default: all 18)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT,
        metavar="DIR",
        help=f"Output directory (default: {_DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help=f"LLM model via OpenRouter (default: {_DEFAULT_MODEL})",
    )
    p.add_argument(
        "--corpus",
        type=Path,
        default=_DEFAULT_CORPUS,
        metavar="DIR",
        help=f"RAG corpus directory (default: {_DEFAULT_CORPUS})",
    )
    p.add_argument(
        "--reference",
        type=Path,
        default=_DEFAULT_REF,
        metavar="FILE",
        help=f"Reference CSV file (default: {_DEFAULT_REF})",
    )
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    sequence = DEFAULT_SEQUENCE
    if args.fragments is not None:
        sequence = sequence[: args.fragments]
    max_n = len(sequence)

    print(f"\nIncrementality probe — fragments={max_n}, model={args.model}")
    print("=" * 60)

    client = make_client()
    ref_plants = load_plants_csv(args.reference)

    print(f"\n[Phase 1/2] Incremental (single-pass, {max_n} LLM calls)")
    inc_rows = compute_incremental_growth(sequence, args.corpus, client, args.model, ref_plants)

    print(f"\n[Phase 2/2] Global (per-N, {max_n} LLM calls)")
    glb_rows = compute_global_growth(sequence, args.corpus, client, args.model, ref_plants)

    all_rows = inc_rows + glb_rows

    csv_path = args.output_dir / "growth_curve.csv"
    pdf_path = args.output_dir / "growth_curve.pdf"

    save_growth_csv(all_rows, csv_path)
    save_growth_pdf(all_rows, pdf_path)

    print_headlines(all_rows, max_n)

    print(f"  CSV: {csv_path}")
    print(f"  PDF: {pdf_path}")


if __name__ == "__main__":
    main()
