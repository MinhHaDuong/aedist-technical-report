"""Tests for models.yaml schema, coverage, and experiments.toml consistency."""

import tomllib
from pathlib import Path

import pytest
import yaml

from aedist.harness import select_models

EXPERIMENTS_DIR = Path(__file__).parent.parent / "experiments"
MODELS_PATH = EXPERIMENTS_DIR / "models.yaml"
EXPERIMENTS_PATH = EXPERIMENTS_DIR / "experiments.toml"

REQUIRED_FIELDS = {
    "id",
    "router",
    "router_model",
    "name",
    "provider",
    "country",
    "architecture",
    "context_window",
    "price_per_mtok_in",
    "price_per_mtok_out",
    "size_class",
    "license",
}

VALID_COUNTRIES = {"US", "CN", "FR", "Other"}
VALID_ARCHITECTURES = {"dense", "moe"}
VALID_SIZE_CLASSES = {"frontier", "large", "medium", "small", "edge"}
VALID_LICENSES = {"commercial", "open-apache", "open-MIT", "open-llama", "open", "open-other"}
VALID_ROUTERS = {"openrouter", "ollama"}


@pytest.fixture
def models():
    with open(MODELS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture
def experiments():
    with open(EXPERIMENTS_PATH, "rb") as f:
        return tomllib.load(f)


def test_schema_validation(models):
    """Each model entry has all required fields with valid values."""
    for model in models:
        model_id = model.get("id", "<missing>")
        present = set(model.keys())
        missing = REQUIRED_FIELDS - present
        assert not missing, f"{model_id} missing fields: {missing}"

        assert model["country"] in VALID_COUNTRIES, (
            f"{model_id}: invalid country {model['country']}"
        )
        assert model["architecture"] in VALID_ARCHITECTURES, (
            f"{model_id}: invalid architecture {model['architecture']}"
        )
        assert model["size_class"] in VALID_SIZE_CLASSES, (
            f"{model_id}: invalid size_class {model['size_class']}"
        )
        assert model["license"] in VALID_LICENSES, (
            f"{model_id}: invalid license {model['license']}"
        )
        assert model["router"] in VALID_ROUTERS, (
            f"{model_id}: invalid router {model['router']}"
        )
        assert isinstance(model["context_window"], int), f"{model_id}: context_window must be int"
        assert isinstance(model["price_per_mtok_in"], (int, float)), (
            f"{model_id}: price_per_mtok_in must be numeric"
        )
        assert isinstance(model["price_per_mtok_out"], (int, float)), (
            f"{model_id}: price_per_mtok_out must be numeric"
        )


def test_router_model_matches_id(models):
    """In Phase A, router_model == id for every entry (scaffolding for Phase B)."""
    for model in models:
        assert model["router_model"] == model["id"], (
            f"{model['id']}: router_model mismatch"
        )


def test_coverage(models):
    """Registry covers required diversity: countries, size classes, and minimum count."""
    countries = {m["country"] for m in models}
    size_classes = {m["size_class"] for m in models}

    assert len(models) >= 45, f"Expected >= 45 models, got {len(models)}"
    assert "US" in countries
    assert "CN" in countries
    assert {"frontier", "large", "medium", "small", "edge"} <= size_classes, (
        f"Missing size classes: {size_classes}"
    )


def test_unique_ids(models):
    """All model IDs must be unique."""
    ids = [m["id"] for m in models]
    assert len(ids) == len(set(ids)), (
        f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"
    )


def test_experiments_model_ids_exist(models, experiments):
    """Every model_id in experiments.toml exists in the registry."""
    registry_ids = {m["id"] for m in models}
    for set_name, spec in experiments["sets"].items():
        for mid in spec["model_ids"]:
            assert mid in registry_ids, (
                f"experiments.toml sets.{set_name}: '{mid}' not in registry"
            )


def test_experiments_sets_nonempty(experiments):
    """Every model set in experiments.toml has at least one model."""
    for set_name, spec in experiments["sets"].items():
        assert len(spec["model_ids"]) > 0, f"sets.{set_name} is empty"


def test_experiments_routers(experiments):
    """Router definitions have required fields."""
    for name, router in experiments["routers"].items():
        assert "base_url" in router, f"routers.{name} missing base_url"


# ---------------------------------------------------------------------------
# _list_models.py helper
# ---------------------------------------------------------------------------


def test_list_models_helper(experiments):
    """_list_models.py produces correct short names for census_cloud."""
    import subprocess

    result = subprocess.run(
        [
            "python3", str(EXPERIMENTS_DIR / "_list_models.py"),
            str(MODELS_PATH),
            "--set", "census_cloud",
            "--experiments", str(EXPERIMENTS_PATH),
        ],
        capture_output=True, text=True, check=True,
    )
    shorts = set(result.stdout.strip().split())
    cloud_ids = experiments["sets"]["census_cloud"]["model_ids"]
    expected = {mid.split("/")[-1].replace(":", "-") for mid in cloud_ids}
    assert shorts == expected, f"Mismatch: extra={shorts - expected}, missing={expected - shorts}"
