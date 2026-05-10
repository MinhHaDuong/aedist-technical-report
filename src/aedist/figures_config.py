"""Load ordered model sets for figure generation from figures.toml."""

import tomllib
from pathlib import Path

from .harness import load_models

_EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "experiments"


def _load_config(figures_path: Path) -> dict:
    with open(figures_path, "rb") as f:
        return tomllib.load(f)


def load_modelset(
    name: str,
    *,
    figures_path: Path | None = None,
    registry_path: Path | None = None,
) -> list[dict]:
    """Return registry dicts for a named modelset, in config order.

    Raises KeyError if a model name in the config is missing from the registry.
    Raises KeyError if the modelset name does not exist in figures.toml.
    """
    figures_path = figures_path or _EXPERIMENTS_DIR / "figures.toml"
    registry_path = registry_path or _EXPERIMENTS_DIR / "models.yaml"

    config = _load_config(figures_path)
    modelsets = config.get("modelsets", {})
    if name not in modelsets:
        raise KeyError(f"Unknown modelset {name!r}; available: {sorted(modelsets)}")

    ordered_names = modelsets[name]["models"]

    registry = load_models(str(registry_path))
    by_name = {m["name"]: m for m in registry}

    result = []
    for model_name in ordered_names:
        if model_name not in by_name:
            raise KeyError(f"Model {model_name!r} in modelset {name!r} not found in registry")
        result.append(by_name[model_name])
    return result


def available_modelsets(*, figures_path: Path | None = None) -> list[str]:
    """Return sorted list of modelset names defined in figures.toml."""
    figures_path = figures_path or _EXPERIMENTS_DIR / "figures.toml"
    return sorted(_load_config(figures_path).get("modelsets", {}))
