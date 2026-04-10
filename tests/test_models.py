"""Tests for models.yaml schema, coverage, and experiments.toml consistency."""

from pathlib import Path

import pytest

from aedist.schema import Method

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
        assert model["router"] in VALID_ROUTERS, f"{model_id}: invalid router {model['router']}"
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
        assert model["router_model"] == model["id"], f"{model['id']}: router_model mismatch"


def test_coverage(models):
    """Registry covers required diversity: countries, size classes, and minimum count."""
    countries = {m["country"] for m in models}
    size_classes = {m["size_class"] for m in models}

    assert len(models) >= 45, f"Expected >= 45 models, got {len(models)}"
    # Spot-check that every model has required pricing fields
    for m in models:
        assert m.get("price_per_mtok_in") is not None, f"{m['id']}: missing price_per_mtok_in"
        assert m.get("price_per_mtok_out") is not None, f"{m['id']}: missing price_per_mtok_out"
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


# ---------------------------------------------------------------------------
# Sweep configuration validation
# ---------------------------------------------------------------------------

VALID_MODES = set(Method)
SWEEP_REQUIRED_FIELDS = {"mode", "models", "repeat", "budget_usd", "output"}
# Each sweep needs either "prompt" (file path) or "prompt_modules" (list of module names).
# verification is special — no mode/prompt/models at top level
SWEEP4_REQUIRED_FIELDS = {"repeat", "budget_usd", "output", "verification_modes", "base_configs"}


def test_sweeps_section_exists(experiments):
    """experiments.toml has a [sweeps] section with at least one entry."""
    assert "sweeps" in experiments, "experiments.toml missing [sweeps] section"
    assert len(experiments["sweeps"]) >= 1


def test_sweep_count(experiments):
    """All sweeps are present."""
    required = {
        "census",
        "census_local",
        "multiturn",
        "web",
        "rag",
        "decomposed",
        "verification",
        "sourced",
        "frontier",
        "frontier_scenarios",
        "frontier_skill",
    }
    ablation = {
        "ablation_p1_base",
        "ablation_p1_composite",
        "ablation_base",
        "ablation_persona",
        "ablation_overview",
        "ablation_narratives",
        "ablation_bibliography",
        "ablation_statistics",
        "ablation_sourcing",
        "ablation_composite",
        "ablation_frontier",
        "ablation_census",
        "ablation_no_persona",
        "ablation_no_overview",
        "ablation_no_narratives",
        "ablation_no_bibliography",
        "ablation_no_statistics",
        "ablation_no_sourcing",
    }
    expected = required | ablation
    assert set(experiments["sweeps"].keys()) == expected


def test_standard_sweep_fields(experiments):
    """Each standard sweep has required fields with valid types."""
    for name, sweep in experiments["sweeps"].items():
        if name == "verification":
            continue
        missing = SWEEP_REQUIRED_FIELDS - set(sweep.keys())
        assert not missing, f"sweeps.{name} missing fields: {missing}"
        has_prompt = "prompt" in sweep or "prompt_modules" in sweep
        assert has_prompt, f"sweeps.{name} needs 'prompt' or 'prompt_modules'"
        assert sweep["mode"] in VALID_MODES, f"sweeps.{name}: invalid mode '{sweep['mode']}'"
        assert isinstance(sweep["repeat"], int) and sweep["repeat"] >= 1, (
            f"sweeps.{name}: repeat must be int >= 1"
        )
        assert isinstance(sweep["budget_usd"], (int, float)), (
            f"sweeps.{name}: budget_usd must be numeric"
        )


def test_verification_structure(experiments):
    """verification has its special structure (base_configs, modes)."""
    s4 = experiments["sweeps"]["verification"]
    missing = SWEEP4_REQUIRED_FIELDS - set(s4.keys())
    assert not missing, f"verification missing fields: {missing}"
    assert isinstance(s4["base_configs"], list) and len(s4["base_configs"]) >= 1
    for i, bc in enumerate(s4["base_configs"]):
        assert "method" in bc, f"base_configs[{i}] missing 'method'"
        assert "model" in bc, f"base_configs[{i}] missing 'model'"
        assert "result_file" in bc, f"base_configs[{i}] missing 'result_file'"
    assert isinstance(s4["verification_modes"], list) and len(s4["verification_modes"]) >= 1


def test_sweep_model_sets_exist(experiments):
    """Every model_set referenced by a sweep exists in [sets]."""
    defined_sets = set(experiments.get("sets", {}).keys())
    for name, sweep in experiments["sweeps"].items():
        if "model_set" in sweep:
            assert sweep["model_set"] in defined_sets, (
                f"sweeps.{name}: model_set '{sweep['model_set']}' not in [sets]"
            )


def test_sweep_model_set_ids_in_registry(models, experiments):
    """model_ids in sets referenced by sweeps all exist in the registry."""
    registry_ids = {m["id"] for m in models}
    for name, sweep in experiments["sweeps"].items():
        set_name = sweep.get("model_set")
        if set_name is None:
            continue
        model_set = experiments["sets"][set_name]
        for mid in model_set["model_ids"]:
            assert mid in registry_ids, f"sweeps.{name} → sets.{set_name}: '{mid}' not in registry"


def test_sweep_prompts_exist(experiments):
    """Prompt files referenced by sweeps exist on disk."""
    for name, sweep in experiments["sweeps"].items():
        if "prompt" not in sweep:
            continue
        prompt_path = EXPERIMENTS_DIR / sweep["prompt"]
        assert prompt_path.exists(), f"sweeps.{name}: prompt file missing: {prompt_path}"


def test_sweep_prompt_modules_exist(experiments):
    """Module files referenced by prompt_modules exist on disk."""
    modules_dir = EXPERIMENTS_DIR / "prompts" / "modules"
    assert (modules_dir / "base.txt").exists(), "modules/base.txt missing"
    for name, sweep in experiments["sweeps"].items():
        for mod in sweep.get("prompt_modules", []):
            mod_path = modules_dir / f"{mod}.txt"
            assert mod_path.exists(), f"sweeps.{name}: module file missing: {mod_path}"


def test_assemble_prompt():
    """assemble_prompt composes base + modules correctly."""
    from aedist.harness import assemble_prompt

    modules_dir = EXPERIMENTS_DIR / "prompts" / "modules"
    # Base only
    base = assemble_prompt(modules_dir, [])
    assert "Produce a comprehensive CSV table" in base
    assert "senior energy analyst" not in base
    # With persona (prepended)
    with_persona = assemble_prompt(modules_dir, ["persona"])
    assert with_persona.startswith("You are a senior energy analyst")
    assert "Produce a comprehensive CSV table" in with_persona
    # With overview (appended)
    with_overview = assemble_prompt(modules_dir, ["overview"])
    assert with_overview.index("sector overview") > with_overview.index("CSV table")


def test_assemble_prompt_unknown_module_raises():
    """assemble_prompt raises ValueError on unknown module names."""
    from aedist.harness import assemble_prompt

    modules_dir = EXPERIMENTS_DIR / "prompts" / "modules"
    with pytest.raises(ValueError, match="Unknown prompt modules"):
        assemble_prompt(modules_dir, ["personaa"])  # typo


def test_sweep_output_dirs_unique(experiments):
    """Each sweep writes to a distinct output directory (no overwrites)."""
    outputs = {}
    for name, sweep in experiments["sweeps"].items():
        out = sweep.get("output")
        if out is None:
            continue
        if out in outputs:
            # census and census_local share output dir by design
            pair = {name, outputs[out]}
            if pair != {"census", "census_local"}:
                pytest.fail(f"sweeps.{name} and sweeps.{outputs[out]} share output '{out}'")
        outputs[out] = name


# ---------------------------------------------------------------------------
# _list_models.py helper
# ---------------------------------------------------------------------------


def test_list_models_helper(experiments):
    """_list_models.py produces correct short names for census_cloud."""
    import subprocess

    result = subprocess.run(
        [
            "python3",
            str(EXPERIMENTS_DIR / "_list_models.py"),
            str(MODELS_PATH),
            "--set",
            "census_cloud",
            "--experiments",
            str(EXPERIMENTS_PATH),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    shorts = set(result.stdout.strip().split())
    cloud_ids = experiments["sets"]["census_cloud"]["model_ids"]
    expected = {mid.split("/")[-1].replace(":", "-") for mid in cloud_ids}
    assert shorts == expected, f"Mismatch: extra={shorts - expected}, missing={expected - shorts}"
