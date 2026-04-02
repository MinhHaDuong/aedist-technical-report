"""Tests for models.yaml schema and coverage."""

from pathlib import Path

import pytest
import yaml

MODELS_PATH = Path(__file__).parent.parent / "experiments" / "models.yaml"

REQUIRED_FIELDS = {
    "id",
    "name",
    "provider",
    "country",
    "architecture",
    "reasoning",
    "context_window",
    "price_per_mtok_in",
    "price_per_mtok_out",
    "size_class",
    "license",
}

VALID_COUNTRIES = {"US", "CN", "FR", "Other"}
VALID_ARCHITECTURES = {"dense", "moe"}
VALID_REASONING = {"instruct", "cot", "reasoner"}
VALID_SIZE_CLASSES = {"frontier", "large", "medium", "small", "edge"}
VALID_LICENSES = {"commercial", "open-apache", "open-MIT", "open-llama", "open", "open-other"}


@pytest.fixture
def models():
    with open(MODELS_PATH) as f:
        return yaml.safe_load(f)


def test_schema_validation(models):
    """Each model entry has all required fields with valid values."""
    for model in models:
        model_id = model.get("id", "<missing>")
        present = set(model.keys())
        missing = REQUIRED_FIELDS - present
        assert not missing, f"{model_id} missing fields: {missing}"

        assert model["country"] in VALID_COUNTRIES, f"{model_id}: invalid country {model['country']}"
        assert model["architecture"] in VALID_ARCHITECTURES, f"{model_id}: invalid architecture {model['architecture']}"
        assert model["reasoning"] in VALID_REASONING, f"{model_id}: invalid reasoning {model['reasoning']}"
        assert model["size_class"] in VALID_SIZE_CLASSES, f"{model_id}: invalid size_class {model['size_class']}"
        assert model["license"] in VALID_LICENSES, f"{model_id}: invalid license {model['license']}"
        assert isinstance(model["context_window"], int), f"{model_id}: context_window must be int"
        assert isinstance(model["price_per_mtok_in"], (int, float)), f"{model_id}: price_per_mtok_in must be numeric"
        assert isinstance(model["price_per_mtok_out"], (int, float)), f"{model_id}: price_per_mtok_out must be numeric"


def test_coverage(models):
    """Registry covers required diversity: countries, size classes, and minimum count."""
    countries = {m["country"] for m in models}
    size_classes = {m["size_class"] for m in models}

    assert len(models) >= 20, f"Expected >= 20 models, got {len(models)}"
    assert "US" in countries
    assert "CN" in countries
    assert {"frontier", "large", "medium", "small"} <= size_classes, f"Missing size classes: {size_classes}"


def test_unique_ids(models):
    """All model IDs must be unique."""
    ids = [m["id"] for m in models]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"
