"""Tests for models.yaml schema, coverage, and experiments.toml consistency."""

from pathlib import Path

import pytest

from aedist.schema import Method

EXPERIMENTS_DIR = Path(__file__).parent.parent / "experiments"
MODELS_PATH = EXPERIMENTS_DIR / "models.yaml"
EXPERIMENTS_PATH = EXPERIMENTS_DIR / "experiments.toml"

# Native fields in models.yaml (v2 schema — ticket 0156)
REQUIRED_FIELDS_V2 = {
    "name",
    "display_name",
    "route",
    "model_id",
    "provider",
    "country",
    "architecture",
    "context_window",
    "price_per_mtok_in",
    "price_per_mtok_out",
    "size_class",
    "license",
}
# SDK-based routes require base_url; CLI routes must not have it.
ROUTES_REQUIRE_BASE_URL = {"openrouter", "ollama", "openllm"}
ROUTES_NO_BASE_URL = {"claude-code-cli", "codex"}

VALID_COUNTRIES = {"US", "CN", "FR", "Other"}
VALID_ARCHITECTURES = {"dense", "moe"}
VALID_SIZE_CLASSES = {"frontier", "large", "medium", "small", "edge"}
VALID_LICENSES = {"commercial", "open-apache", "open-MIT", "open-llama", "open", "open-other"}
VALID_ROUTES = ROUTES_REQUIRE_BASE_URL | ROUTES_NO_BASE_URL


BANNED_FIELDS_V1 = {"id", "router", "router_model"}


def test_schema_validation(models):
    """Each model entry has all required fields with valid values (v2 schema)."""
    for model in models:
        model_name = model.get("name", "<missing>")
        present = set(model.keys())
        missing = REQUIRED_FIELDS_V2 - present
        assert not missing, f"{model_name} missing fields: {missing}"
        leftover = BANNED_FIELDS_V1 & present
        assert not leftover, f"{model_name} still has v1 fields: {leftover}"

        assert model["country"] in VALID_COUNTRIES, (
            f"{model_name}: invalid country {model['country']}"
        )
        assert model["architecture"] in VALID_ARCHITECTURES, (
            f"{model_name}: invalid architecture {model['architecture']}"
        )
        assert model["size_class"] in VALID_SIZE_CLASSES, (
            f"{model_name}: invalid size_class {model['size_class']}"
        )
        assert model["license"] in VALID_LICENSES, (
            f"{model_name}: invalid license {model['license']}"
        )
        assert model["route"] in VALID_ROUTES, f"{model_name}: invalid route {model['route']}"
        route = model["route"]
        if route in ROUTES_REQUIRE_BASE_URL:
            assert "base_url" in model, f"{model_name}: route={route} requires base_url"
        if route in ROUTES_NO_BASE_URL:
            assert "base_url" not in model, f"{model_name}: route={route} must not have base_url"
        assert isinstance(model["context_window"], int), (
            f"{model_name}: context_window must be int"
        )
        assert isinstance(model["price_per_mtok_in"], (int, float)), (
            f"{model_name}: price_per_mtok_in must be numeric"
        )
        assert isinstance(model["price_per_mtok_out"], (int, float)), (
            f"{model_name}: price_per_mtok_out must be numeric"
        )


def test_coverage(models):
    """Registry covers required diversity: countries, size classes, and minimum count."""
    countries = {m["country"] for m in models}
    size_classes = {m["size_class"] for m in models}

    assert len(models) >= 45, f"Expected >= 45 models, got {len(models)}"
    # Spot-check that every model has required pricing fields
    for m in models:
        assert m.get("price_per_mtok_in") is not None, f"{m['name']}: missing price_per_mtok_in"
        assert m.get("price_per_mtok_out") is not None, f"{m['name']}: missing price_per_mtok_out"
    assert "US" in countries
    assert "CN" in countries
    assert {"frontier", "large", "medium", "small", "edge"} <= size_classes, (
        f"Missing size classes: {size_classes}"
    )


def test_unique_names(models):
    """All model instance names must be unique."""
    names = [m["name"] for m in models]
    assert len(names) == len(set(names)), (
        f"Duplicate names found: {[x for x in names if names.count(x) > 1]}"
    )


def test_experiments_model_ids_exist(models, experiments):
    """Every model_id in experiments.toml exists in the registry."""
    registry_names = {m["name"] for m in models}
    for set_name, spec in experiments["sets"].items():
        for mid in spec["model_ids"]:
            assert mid in registry_names, (
                f"experiments.toml sets.{set_name}: '{mid}' not in registry"
            )


def test_experiments_sets_nonempty(experiments):
    """Every model set in experiments.toml has at least one model (unless intentionally empty)."""
    # modelset_ablation_core is intentionally empty until Phase 1 identifies cross-regime models
    allowed_empty = {"modelset_ablation_core"}
    for set_name, spec in experiments["sets"].items():
        if set_name in allowed_empty:
            continue
        assert len(spec["model_ids"]) > 0, f"sets.{set_name} is empty"


def test_no_routers_section(experiments):
    """experiments.toml no longer has a [routers] section — base_url is per-model (ticket 0156)."""
    assert "routers" not in experiments, (
        "experiments.toml [routers] section should have been removed"
    )


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
    """Core sweeps are present (minimum-baseline check, not exact-equality)."""
    core = {
        "sweep_direct_extract",
        "sweep_direct_extract_local",
        "sweep_direct_multiturn",
        "sweep_rag_livesearch",
        "sweep_rag_extract",
        "sweep_rag_per_fuel",
        "sweep_rag_verification",
        "sweep_rag_verification_multi",
        "sweep_rag_verification_poc",
        "sweep_rag_cited",
        "sweep_direct_complete",
        "sweep_direct_scenarios",
        "sweep_fusion",
        "sweep_fusion_dev",
    }
    actual = set(experiments["sweeps"].keys())
    missing = core - actual
    assert not missing, f"Core sweeps missing from experiments.toml: {missing}"
    # Sanity: sweeps grow over time; ensure at least the core count
    assert len(actual) >= len(core), f"Expected at least {len(core)} sweeps, got {len(actual)}"


def test_standard_sweep_fields(experiments):
    """Each standard sweep has required fields with valid types."""
    fusion_sweeps = {n for n in experiments["sweeps"] if n.startswith("sweep_fusion")}
    for name, sweep in experiments["sweeps"].items():
        if name.startswith("sweep_rag_verification") or name in fusion_sweeps:
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


def test_fusion_sweep_fields(experiments):
    """Fusion sweeps have their own required schema (different from standard sweeps)."""
    fusion_required = {"fusion_mode", "format", "model", "corpus", "reference", "output"}
    valid_fusion_modes = {"incremental", "global", "compare"}
    valid_formats = {"json", "md", "both"}
    for name, sweep in experiments["sweeps"].items():
        if not name.startswith("sweep_fusion"):
            continue
        missing = fusion_required - set(sweep.keys())
        assert not missing, f"sweeps.{name} missing fusion fields: {missing}"
        assert sweep["fusion_mode"] in valid_fusion_modes, (
            f"sweeps.{name}: invalid fusion_mode '{sweep['fusion_mode']}'"
        )
        assert sweep["format"] in valid_formats, (
            f"sweeps.{name}: invalid format '{sweep['format']}'"
        )
        assert isinstance(sweep["model"], str) and sweep["model"], (
            f"sweeps.{name}: model must be a non-empty string"
        )


def test_verification_structure(experiments):
    """verification has its special structure (base_configs, modes)."""
    s4 = experiments["sweeps"]["sweep_rag_verification"]
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
    registry_names = {m["name"] for m in models}
    for name, sweep in experiments["sweeps"].items():
        set_name = sweep.get("model_set")
        if set_name is None:
            continue
        model_set = experiments["sets"][set_name]
        for mid in model_set["model_ids"]:
            assert mid in registry_names, (
                f"sweeps.{name} → sets.{set_name}: '{mid}' not in registry"
            )


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
    assert "For EVERY thermal power plant" in base
    assert "senior energy analyst" not in base
    # With persona (prepended before base)
    with_persona = assemble_prompt(modules_dir, ["persona"])
    assert with_persona.startswith("You are a senior energy analyst")
    assert "For EVERY thermal power plant" in with_persona
    # With overview (prepended before base, after persona)
    with_both = assemble_prompt(modules_dir, ["persona", "overview"])
    assert with_both.index("thermal power sector") < with_both.index("For EVERY")


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
            # Some sweep pairs intentionally share an output directory:
            # - census/census_local: cloud + local models writing to same dir
            # - ablation_p1_parametric_base/_extended: extended set mixes into base dir
            pair = {name, outputs[out]}
            allowed_pairs = [
                {"sweep_direct_extract", "sweep_direct_extract_local"},
                {"sweep_ablation_p1_direct_base", "sweep_ablation_p1_direct_base_extended"},
                {"sweep_regimes_direct_cloud", "sweep_regimes_direct_local"},
                {"sweep_regimes_multiturn_cloud", "sweep_regimes_multiturn_local"},
                {"sweep_regimes_rag_cloud", "sweep_regimes_rag_local"},
            ]
            if pair not in allowed_pairs:
                pytest.fail(f"sweeps.{name} and sweeps.{outputs[out]} share output '{out}'")
        outputs[out] = name


# ---------------------------------------------------------------------------
# _list_models.py helper
# ---------------------------------------------------------------------------


def test_list_models_helper(experiments):
    """_list_models.py produces correct short names for modelset_census_cloud."""
    import subprocess

    result = subprocess.run(
        [
            "python3",
            str(EXPERIMENTS_DIR / "_list_models.py"),
            str(MODELS_PATH),
            "--set",
            "modelset_census_cloud",
            "--experiments",
            str(EXPERIMENTS_PATH),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    shorts = set(result.stdout.strip().split())
    cloud_ids = experiments["sets"]["modelset_census_cloud"]["model_ids"]
    expected = {mid.split("/")[-1].replace(":", "-") for mid in cloud_ids}
    assert shorts == expected, f"Mismatch: extra={shorts - expected}, missing={expected - shorts}"
