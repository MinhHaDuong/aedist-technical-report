"""Select top models from census metrics with diversity constraints.

Reads evaluation metrics (all_metrics.json), groups by model slug,
ranks by median F1, and selects top N ensuring diversity across
geography, provider type, and price tier.

Usage:
    uv run python -m aedist.select_top \
        --input results/summary/all_metrics.json \
        --registry experiments/models.yaml \
        --padme experiments/models_padme.yaml \
        --output experiments/models_top5.yaml \
        --n 8
"""

import argparse
import json
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

    Labels look like 'sweep1_census/gpt-5.4-run1'.
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
# Diverse selection
# ---------------------------------------------------------------------------

def _is_us(model: dict) -> bool:
    return model.get("country") == "US"


def _is_cn(model: dict) -> bool:
    return model.get("country") == "CN"


def _is_local(model: dict) -> bool:
    return "Padme" in model.get("provider", "")


def _is_cheap(model: dict) -> bool:
    return model.get("price_per_mtok_out", float("inf")) < 1.0


def select_top_diverse(
    rankings: dict[str, float],
    registry: dict[str, dict],
    n: int = 5,
) -> list[dict]:
    """Select top N models by median F1 with diversity constraints.

    Ensures at least one model from each category:
    - US provider
    - CN provider
    - Local (Padme) provider
    - Cheap (<$1/Mtok output)

    Models not found in the registry are skipped.
    """
    # Filter to models present in both rankings and registry
    candidates = []
    for slug in rankings:
        if slug in registry:
            entry = registry[slug].copy()
            entry["_median_f1"] = rankings[slug]
            candidates.append(entry)

    if not candidates:
        return []

    # Clamp n to available candidates
    n = min(n, len(candidates))

    # Greedy selection: fill diversity slots first, then top by F1
    selected_slugs: set[str] = set()
    selected: list[dict] = []

    # Diversity constraints: (predicate, label)
    constraints = [
        (_is_us, "US"),
        (_is_cn, "CN"),
        (_is_local, "local/Padme"),
        (_is_cheap, "cheap (<$1/Mtok)"),
    ]

    # For each constraint, pick the highest-F1 candidate that satisfies it
    for predicate, label in constraints:
        if len(selected) >= n:
            break
        for candidate in candidates:
            slug = candidate["_slug"]
            if slug not in selected_slugs and predicate(candidate):
                selected.append(candidate)
                selected_slugs.add(slug)
                log.info(
                    "  Diversity slot [%s]: %s (median F1=%.1f%%)",
                    label, candidate.get("name", slug),
                    candidate["_median_f1"] * 100,
                )
                break

    # Fill remaining slots with top F1 models not yet selected
    for candidate in candidates:
        if len(selected) >= n:
            break
        slug = candidate["_slug"]
        if slug not in selected_slugs:
            selected.append(candidate)
            selected_slugs.add(slug)
            log.info(
                "  Top F1 slot: %s (median F1=%.1f%%)",
                candidate.get("name", slug),
                candidate["_median_f1"] * 100,
            )

    # Sort final selection by median F1 descending
    selected.sort(key=lambda x: x["_median_f1"], reverse=True)

    # Strip internal fields before returning
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
        prog="aedist.select_top",
        description="Select top models from census evaluation metrics",
    )
    parser.add_argument(
        "--input", required=True, type=Path,
        help="Path to all_metrics.json",
    )
    parser.add_argument(
        "--registry", required=True, type=Path,
        help="Path to models.yaml (cloud registry)",
    )
    parser.add_argument(
        "--padme", required=True, type=Path,
        help="Path to models_padme.yaml (local registry)",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Output path for selected models YAML",
    )
    parser.add_argument(
        "--n", type=int, default=5,
        help="Number of models to select (default: 5)",
    )

    args = parser.parse_args()

    # Load metrics
    with open(args.input) as f:
        metrics = json.load(f)
    log.info("Loaded %d metric entries from %s", len(metrics), args.input)

    # Load registries
    with open(args.registry) as f:
        cloud_models = yaml.safe_load(f)
    with open(args.padme) as f:
        padme_models = yaml.safe_load(f)

    cloud_reg = load_registry(cloud_models, is_padme=False)
    padme_reg = load_registry(padme_models, is_padme=True)
    combined = {**cloud_reg, **padme_reg}
    log.info("Registry: %d cloud + %d local = %d models", len(cloud_reg), len(padme_reg), len(combined))

    # Rank
    rankings = group_median_f1(metrics)
    log.info("Rankings (median F1):")
    for slug, f1 in rankings.items():
        marker = " *" if slug in combined else " ?"
        log.info("  %s  %.1f%%%s", slug.ljust(35), f1 * 100, marker)

    # Select
    log.info("Selecting top %d with diversity constraints:", args.n)
    selected = select_top_diverse(rankings, combined, n=args.n)

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
