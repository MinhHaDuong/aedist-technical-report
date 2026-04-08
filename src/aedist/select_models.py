"""Select top models from census metrics with diversity constraints.

Reads evaluation metrics (measurements.jsonl), groups by model slug,
ranks by median F1, and selects top N ensuring diversity across
geography, provider type, and price tier.

Usage:
    uv run python -m aedist.select_models \
        --measurements measurements.jsonl \
        --registry experiments/models.yaml \
        --padme experiments/models_padme.yaml \
        --output experiments/models_selected.yaml \
        --n 8
"""

import argparse
import logging
import re
import statistics
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Slug extraction
# ---------------------------------------------------------------------------


def extract_slug(label: str) -> str:
    """Extract model slug from a metrics label.

    Labels look like 'census/gpt-5.4-run1'.
    Strip the directory prefix and the '-runN' suffix to get 'gpt-5.4'.
    """
    # Strip directory prefix (everything up to and including last '/')
    if "/" in label:
        label = label.rsplit("/", 1)[1]
    # Strip -runN suffix
    slug = re.sub(r"-run\d+$", "", label)
    return slug


# ---------------------------------------------------------------------------
# Grouping and ranking
# ---------------------------------------------------------------------------


def group_median_f1(metrics: list[dict]) -> dict[str, float]:
    """Group metrics by model slug and compute median F1 per model.

    Returns dict mapping slug -> median F1, sorted descending.
    """
    groups: dict[str, list[float]] = {}
    for entry in metrics:
        slug = extract_slug(entry["label"])
        groups.setdefault(slug, []).append(entry["f1"])

    medians = {slug: statistics.median(f1s) for slug, f1s in groups.items()}
    return dict(sorted(medians.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def load_registry(models: list[dict], *, is_padme: bool = False) -> dict[str, dict]:
    """Build slug -> model entry mapping from a registry list.

    For cloud models: slug = id.split('/')[-1].replace(':', '-')
    For Padme models: slug = 'padme-' + id.replace(':', '-')
    """
    result: dict[str, dict] = {}
    for model in models:
        model_id = model["id"]
        if is_padme:
            slug = "padme-" + model_id.replace(":", "-")
        else:
            slug = model_id.split("/")[-1].replace(":", "-")
        result[slug] = {**model, "_slug": slug}
    return result


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def select_models(
    rankings: dict[str, float],
    cloud_registry: dict[str, dict],
    local_registry: dict[str, dict],
    n: int = 1,
    *,
    require_countries: list[str] | None = None,
    n_cheap: int = 0,
) -> list[dict]:
    """Select models with optional diversity constraints.

    When *require_countries* is empty (default), falls back to the original
    behaviour: top N cloud + top N local by median F1.

    With diversity constraints:
      1. **Frontier tier** — one model per required country, best F1 among
         that country's ``size_class: frontier`` cloud models.
      2. **Cheap tier** — *n_cheap* cheapest cloud models whose F1 exceeds
         the best local model's F1 (the "local floor"), excluding models
         already picked in the frontier tier.
    """
    # --- legacy path (no diversity flags) ---------------------------------
    if not require_countries:

        def _pick_top_n(registry: dict[str, dict], label: str) -> list[dict]:
            candidates = []
            for slug in rankings:
                if slug in registry:
                    entry = registry[slug].copy()
                    entry["_median_f1"] = rankings[slug]
                    candidates.append(entry)
            picked = candidates[:n]
            for m in picked:
                log.info(
                    "  %s: %s (median F1=%.1f%%)",
                    label,
                    m.get("name", m["_slug"]),
                    m["_median_f1"] * 100,
                )
            return picked

        log.info("Selecting top %d cloud + %d local:", n, n)
        cloud = _pick_top_n(cloud_registry, "cloud")
        local = _pick_top_n(local_registry, "local")

        selected = cloud + local
        selected.sort(key=lambda x: x["_median_f1"], reverse=True)
        for model in selected:
            model.pop("_median_f1", None)
            model.pop("_slug", None)
        return selected

    # --- diversity-aware path ---------------------------------------------

    # Annotate cloud candidates with rankings
    scored: list[dict] = []
    for slug in rankings:
        if slug in cloud_registry:
            entry = cloud_registry[slug].copy()
            entry["_median_f1"] = rankings[slug]
            scored.append(entry)

    # 1. Frontier tier: best F1 per required country (frontier only)
    picked_ids: set[str] = set()
    frontier_picks: list[dict] = []
    for country in require_countries:
        candidates = [
            m
            for m in scored
            if m.get("country") == country
            and m.get("size_class") == "frontier"
            and m["id"] not in picked_ids
        ]
        candidates.sort(key=lambda m: m["_median_f1"], reverse=True)
        if candidates:
            pick = candidates[0]
            frontier_picks.append(pick)
            picked_ids.add(pick["id"])
            log.info(
                "  frontier %s: %s (F1=%.1f%%)",
                country,
                pick.get("name", pick["id"]),
                pick["_median_f1"] * 100,
            )
        else:
            log.warning("  frontier %s: no candidate found", country)

    # 2. Cheap tier: cheapest cloud models beating the local floor
    local_f1s = [rankings[slug] for slug in rankings if slug in local_registry]
    local_floor = max(local_f1s) if local_f1s else 0.0
    log.info("  local floor: F1=%.1f%%", local_floor * 100)

    cheap_candidates = [
        m for m in scored if m["id"] not in picked_ids and m["_median_f1"] > local_floor
    ]
    cheap_candidates.sort(key=lambda m: m.get("price_per_mtok_in", 999))
    cheap_picks = cheap_candidates[:n_cheap]
    for m in cheap_picks:
        log.info(
            "  cheap: %s ($%.2f/Mtok, F1=%.1f%%)",
            m.get("name", m["id"]),
            m.get("price_per_mtok_in", 0),
            m["_median_f1"] * 100,
        )

    # Combine and clean
    selected = frontier_picks + cheap_picks
    selected.sort(key=lambda x: x["_median_f1"], reverse=True)
    for model in selected:
        model.pop("_median_f1", None)
        model.pop("_slug", None)
    return selected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        prog="aedist.select_models",
        description="Select top models from census evaluation metrics",
    )
    parser.add_argument(
        "--registry",
        required=True,
        type=Path,
        help="Path to models.yaml (cloud registry)",
    )
    parser.add_argument(
        "--padme",
        required=False,
        type=Path,
        default=None,
        help="Path to models_padme.yaml (deprecated — local models detected by router field)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output path for selected models YAML",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Select N cloud + N local models (default: 1, i.e. 2 total)",
    )
    parser.add_argument(
        "--require-country",
        action="append",
        dest="require_countries",
        metavar="CC",
        help="Reserve one frontier slot for this country (repeatable)",
    )
    parser.add_argument(
        "--n-cheap",
        type=int,
        default=0,
        help="Number of cheap models beating local floor (default: 0)",
    )

    args = parser.parse_args()

    # Load metrics
    from .measurements import load_metrics

    metrics = load_metrics()
    log.info("Loaded %d metric entries", len(metrics))

    # Load registries
    with open(args.registry) as f:
        all_models = yaml.safe_load(f)

    if args.padme:
        # Legacy: separate padme file
        log.warning("--padme is deprecated; local models are detected by router field")
        with open(args.padme) as f:
            padme_models = yaml.safe_load(f)
        cloud_models = all_models
    else:
        # New: single registry, split by router field
        cloud_models = [m for m in all_models if m.get("router") != "ollama"]
        padme_models = [m for m in all_models if m.get("router") == "ollama"]

    cloud_reg = load_registry(cloud_models, is_padme=False)
    padme_reg = load_registry(padme_models, is_padme=True)
    log.info("Registry: %d cloud + %d local", len(cloud_reg), len(padme_reg))

    # Rank
    rankings = group_median_f1(metrics)
    log.info("Rankings (median F1):")
    all_known = {**cloud_reg, **padme_reg}
    for slug, f1 in rankings.items():
        marker = " *" if slug in all_known else " ?"
        log.info("  %s  %.1f%%%s", slug.ljust(35), f1 * 100, marker)

    # Select
    selected = select_models(
        rankings,
        cloud_reg,
        padme_reg,
        n=args.n,
        require_countries=args.require_countries,
        n_cheap=args.n_cheap,
    )

    # Write output
    # Strip internal fields and write clean YAML
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        yaml.dump(selected, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    log.info("Wrote %d models to %s", len(selected), args.output)
    for model in selected:
        log.info("  %s (%s, %s)", model["name"], model["provider"], model["country"])


if __name__ == "__main__":
    main()
