"""Tests for figures.toml modelset configuration."""

from pathlib import Path

import pytest

from aedist.figures_config import available_modelsets, load_modelset

EXPERIMENTS_DIR = Path(__file__).parent.parent / "experiments"
FIGURES_PATH = EXPERIMENTS_DIR / "figures.toml"
REGISTRY_PATH = EXPERIMENTS_DIR / "models.yaml"


def test_figures_toml_exists():
    """figures.toml exists in experiments/."""
    assert FIGURES_PATH.exists()


def test_available_modelsets():
    """At least frontier, ablation, regimes_scatter are defined."""
    names = available_modelsets(figures_path=FIGURES_PATH)
    assert "frontier" in names
    assert "ablation" in names
    assert "regimes_scatter" in names


@pytest.mark.parametrize("name", available_modelsets(figures_path=FIGURES_PATH))
def test_modelset_loads(name):
    """Each modelset loads without error (all names resolve in registry)."""
    models = load_modelset(name, figures_path=FIGURES_PATH, registry_path=REGISTRY_PATH)
    assert len(models) >= 1


@pytest.mark.parametrize("name", available_modelsets(figures_path=FIGURES_PATH))
def test_modelset_order_matches_config(name):
    """Returned model order matches the order in figures.toml."""
    import tomllib

    with open(FIGURES_PATH, "rb") as f:
        config = tomllib.load(f)
    expected_names = config["modelsets"][name]["models"]

    models = load_modelset(name, figures_path=FIGURES_PATH, registry_path=REGISTRY_PATH)
    actual_names = [m["name"] for m in models]
    assert actual_names == expected_names


@pytest.mark.parametrize("name", available_modelsets(figures_path=FIGURES_PATH))
def test_modelset_has_display_names(name):
    """Every model in a modelset has a display_name from the registry."""
    models = load_modelset(name, figures_path=FIGURES_PATH, registry_path=REGISTRY_PATH)
    for m in models:
        assert "display_name" in m, f"{m['name']} missing display_name"
        assert m["display_name"], f"{m['name']} has empty display_name"


def test_unknown_modelset_raises():
    """Requesting a non-existent modelset raises KeyError."""
    with pytest.raises(KeyError, match="Unknown modelset"):
        load_modelset("nonexistent", figures_path=FIGURES_PATH, registry_path=REGISTRY_PATH)
