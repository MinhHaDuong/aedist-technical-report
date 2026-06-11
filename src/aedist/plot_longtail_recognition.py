"""Long-tail recognition figure (tickets 0514, 0537).

The reference register documents every plant by construction (Gold), but the
*public* documentation thins out into a long tail: GEM, Wikipedia, and
OpenStreetMap cover the operational head well and the speculative tail poorly.
This figure makes the long-tail claim empirical — X is the reference plants
sorted by visibility (descending), Y is four recognition layers, and one glance
shows the documented head and the under-documented tail.

Layers (rows, top to bottom):
  * Gold       — the reference register; all plants by construction.
  * GEM        — Global Energy Monitor coverage (reviewed match, per concordance).
  * Wikipedia  — Wikipedia coverage (reviewed match, per concordance).
  * OSM        — OpenStreetMap coverage (power=plant extract, thermal fuels);
                 a presence check for physically existing infrastructure —
                 name-only fuzzy matching, no LP reconciliation, no capacity
                 term, because OSM maps what stands on the ground.

Two-step pipeline (figures-are-artifacts rule):
  1. ``derive_layer_rows`` runs the LP reconciliation once (shared with the
     concordance script) and emits a committed per-plant layer CSV.
  2. ``render_longtail`` reads THAT CSV and draws the PDF; caption / coverage
     counts are re-derived from the CSV via :func:`coverage_counts` — never
     hardcoded (derive-prose-from-artifacts rule).

Usage::

    uv run python -m aedist.plot_longtail_recognition \\
        --reference data/reference/vietnam_thermal_plants_v2_classified.csv \\
        --csv data/reference/tab_longtail_layers.csv \\
        --output report/inputs/generated/fig_longtail_recognition.pdf \\
        --output-macros report/inputs/generated/macros_longtail.tex
"""

import argparse
import csv
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .config import (  # noqa: E402
    GEM_THERMAL_REFERENCE_CSV,
    LONGTAIL_LAYERS_CSV,
    OSM_VN_POWER_PLANTS_CSV,
    VN_THERMAL_PLANTS_RELEASE_CSV,
)
from .evaluate import load_plants_csv  # noqa: E402
from .util import (  # noqa: E402
    COLOR_MATCHED,
    COLOR_NEUTRAL,
    COLOR_REFERENCE,
)

log = logging.getLogger(__name__)

# CSV columns of the per-plant layer table (single source of truth for the
# generated artifact's schema; the adherence test pins this set).
LAYER_COLUMNS = [
    "plant_id",
    "plant_name",
    "status",
    "in_gold",
    "in_gem",
    "in_wiki",
    "in_osm",
]

# Display order of the recognition layers, top (most complete) to bottom.
_LAYER_ROWS = ["Gold", "GEM", "Wikipedia", "OSM"]

# OSM `source` (fuel) values that count as thermal plants for the OSM layer.
_OSM_THERMAL_FUELS = {"coal", "gas", "gas;oil", "oil", "waste"}

# ASCII-folded partial_ratio threshold for the OSM name presence check —
# mirrors tabulate_source_concordance._RECOVER (same fold, same metric).
_OSM_MATCH = 88


def build_row(
    plant_id: int,
    plant_name: str,
    status: str,
    *,
    in_gem: bool,
    in_wiki: bool,
    in_osm: bool,
) -> dict:
    """Build one per-plant layer-membership row.

    Every reference plant is Gold by construction, so ``in_gold`` is always 1.
    """
    return {
        "plant_id": int(plant_id),
        "plant_name": plant_name,
        "status": status,
        "in_gold": 1,
        "in_gem": 1 if in_gem else 0,
        "in_wiki": 1 if in_wiki else 0,
        "in_osm": 1 if in_osm else 0,
    }


def visibility_key(row: dict) -> tuple:
    """Sort key for visibility (higher = more visible / better documented).

    Ordered by the number of public-source layers (GEM + Wikipedia + OSM),
    then descending plant_id as a stable tie-break so the committed CSV is
    byte-reproducible. Gold is excluded from the key because every plant has
    it (it would not discriminate).
    """
    source_layers = int(row["in_gem"]) + int(row["in_wiki"]) + int(row["in_osm"])
    return (source_layers, -int(row["plant_id"]))


def sort_by_visibility(rows: list[dict]) -> list[dict]:
    """Reference plants sorted by visibility, descending (head first)."""
    return sorted(rows, key=visibility_key, reverse=True)


def coverage_counts(rows: list[dict]) -> dict:
    """Per-layer coverage counts, re-derived from the layer rows.

    This is the single place caption numbers come from — the renderer and any
    macros call it; nothing hardcodes a layer total (derive-prose rule).
    """
    n = len(rows)
    return {
        "n_reference": n,
        "gold": sum(int(r["in_gold"]) for r in rows),
        "gem": sum(int(r["in_gem"]) for r in rows),
        "wiki": sum(int(r["in_wiki"]) for r in rows),
        "osm": sum(int(r["in_osm"]) for r in rows),
    }


# --- derivation (slow: LP reconciliation, runs once) ------------------------


def load_osm_thermal_names(osm_path: Path) -> list[str]:
    """Thermal plant names from the OSM power=plant extract.

    Filters on the ``source`` (fuel) column so hydro/solar/wind rows do not
    count toward the thermal recognition layer.
    """
    with Path(osm_path).open(encoding="utf-8") as fh:
        return [
            r["name"].strip()
            for r in csv.DictReader(fh)
            if r.get("name", "").strip()
            and r.get("source", "").strip() in _OSM_THERMAL_FUELS
        ]


def derive_layer_rows(
    reference_path: Path,
    gem_path: Path,
    osm_path: Path,
) -> list[dict]:
    """Reconcile GEM / Wikipedia / OSM against the reference once.

    Reuses the concordance script's fold/reconcile machinery (imported, not
    reimplemented) so GEM/Wikipedia coverage matches the committed concordance
    table exactly. The OSM layer is a deliberate name-only presence check
    (fold + partial_ratio >= _OSM_MATCH): OSM maps existing infrastructure, so
    no LP reconciliation and no capacity term apply.
    """
    from rapidfuzz import fuzz

    from .tabulate_source_concordance import (
        _fold,
        _names_to_plants,
        _reviewed_coverage,
        _wikipedia_names,
    )

    reference = load_plants_csv(reference_path)
    gem_plants = load_plants_csv(gem_path)
    gem_names = [
        r["Name"].strip()
        for r in csv.DictReader(Path(gem_path).open(encoding="utf-8"))
        if r.get("Name")
    ]
    wiki_names = _wikipedia_names()

    _, gem_cov = _reviewed_coverage(reference, gem_plants, gem_names)
    _, wiki_cov = _reviewed_coverage(
        reference, _names_to_plants(wiki_names), wiki_names
    )

    folded_osm = [f for f in (_fold(n) for n in load_osm_thermal_names(osm_path)) if f]

    rows: list[dict] = []
    for pid, plant in enumerate(reference):
        fr = _fold(plant.name)
        in_osm = bool(fr) and any(
            fuzz.partial_ratio(fr, fo) >= _OSM_MATCH for fo in folded_osm
        )
        rows.append(
            build_row(
                pid,
                plant.name,
                plant.status.value if plant.status else "",
                in_gem=plant.name in gem_cov,
                in_wiki=plant.name in wiki_cov,
                in_osm=in_osm,
            )
        )
    return rows


def write_layer_csv(rows: list[dict], output: Path) -> None:
    """Write the per-plant layer table (plant-id order, stable)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: int(r["plant_id"]))
    with output.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LAYER_COLUMNS)
        w.writeheader()
        w.writerows(ordered)
    log.info("Wrote long-tail layer table to %s (%d plants)", output, len(ordered))


def load_layer_table(path: Path) -> list[dict]:
    """Read the per-plant layer table back as typed rows."""
    with Path(path).open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for col in ("plant_id", "in_gold", "in_gem", "in_wiki", "in_osm"):
            r[col] = int(r[col])
    return rows


# --- rendering (reads the CSV) ----------------------------------------------


def _layer_cmap() -> LinearSegmentedColormap:
    """Neutral (miss) -> matched (documented) ramp from the shared palette."""
    return LinearSegmentedColormap.from_list(
        "longtail_layers", ["white", COLOR_MATCHED]
    )


def render_longtail(rows: list[dict], output: Path, output_macros: Path | None = None) -> None:
    """Draw the long-tail recognition figure from the layer rows."""
    import numpy as np

    ordered = sort_by_visibility(rows)
    counts = coverage_counts(ordered)
    n = counts["n_reference"]

    # Build a per-layer presence matrix: rows = layers, cols = plants.
    # All four layers are boolean (0/1).
    grid = np.zeros((len(_LAYER_ROWS), n))
    for j, r in enumerate(ordered):
        grid[0, j] = int(r["in_gold"])
        grid[1, j] = int(r["in_gem"])
        grid[2, j] = int(r["in_wiki"])
        grid[3, j] = int(r["in_osm"])

    fig, ax = plt.subplots(figsize=(11, 2.6))
    cmap = _layer_cmap()
    ax.imshow(
        grid,
        aspect="auto",
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
    )
    ax.set_yticks(range(len(_LAYER_ROWS)))
    ax.set_yticklabels(_LAYER_ROWS, fontsize=9)
    ax.set_xticks([])
    ax.set_xlabel(
        f"{n} reference plants, sorted by visibility (documented head left, "
        "under-documented tail right)",
        fontsize=9,
    )
    # Faint separators between layer rows.
    for y in range(1, len(_LAYER_ROWS)):
        ax.axhline(y - 0.5, color=COLOR_NEUTRAL, linewidth=0.4)
    for spine in ax.spines.values():
        spine.set_color(COLOR_REFERENCE)
        spine.set_linewidth(0.6)

    ax.set_title(
        f"Recognition long tail: Gold {counts['gold']}/{n}, "
        f"GEM {counts['gem']}/{n}, Wikipedia {counts['wiki']}/{n}, "
        f"OSM {counts['osm']}/{n}",
        fontsize=9,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    log.info(
        "Wrote long-tail figure to %s (Gold %d / GEM %d / Wiki %d / OSM %d of %d)",
        output,
        counts["gold"],
        counts["gem"],
        counts["wiki"],
        counts["osm"],
        n,
    )

    if output_macros is not None:
        write_macros(counts, output_macros)


def write_macros(counts: dict, output: Path) -> None:
    """Emit LaTeX macros for the caption counts (Wave-2 prose consumes these)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "% Auto-generated by aedist.plot_longtail_recognition — do not edit.\n"
        f"\\newcommand{{\\LongtailReference}}{{{counts['n_reference']}}}\n"
        f"\\newcommand{{\\LongtailGem}}{{{counts['gem']}}}\n"
        f"\\newcommand{{\\LongtailWiki}}{{{counts['wiki']}}}\n"
        f"\\newcommand{{\\LongtailOsm}}{{{counts['osm']}}}\n",
        encoding="utf-8",
    )
    log.info("Wrote long-tail macros to %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate the long-tail recognition figure and layer CSV."
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=VN_THERMAL_PLANTS_RELEASE_CSV,
        help="Reference register CSV (the Gold layer / plant set).",
    )
    parser.add_argument(
        "--gem",
        type=Path,
        default=GEM_THERMAL_REFERENCE_CSV,
        help="GEM thermal reference CSV.",
    )
    parser.add_argument(
        "--osm",
        type=Path,
        default=OSM_VN_POWER_PLANTS_CSV,
        help="OSM power=plant extract CSV (OSM recognition layer).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=LONGTAIL_LAYERS_CSV,
        help="Output per-plant layer-membership CSV (committed artifact).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/fig_longtail_recognition.pdf"),
        help="Output figure PDF.",
    )
    parser.add_argument(
        "--output-macros",
        type=Path,
        default=None,
        help="Optional LaTeX macros file with the caption counts.",
    )
    parser.add_argument(
        "--from-csv",
        action="store_true",
        help="Skip the LP derivation and render from an existing --csv.",
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Run the LP derivation and write --csv only; render no figure.",
    )
    args = parser.parse_args(argv)

    if args.from_csv:
        rows = load_layer_table(args.csv)
    else:
        rows = derive_layer_rows(args.reference, args.gem, args.osm)
        write_layer_csv(rows, args.csv)
        if args.csv_only:
            return

    render_longtail(rows, args.output, args.output_macros)


if __name__ == "__main__":
    main()
