"""Tests for aedist.query_verification — verification runner."""

from pathlib import Path

import pytest

from aedist.query_verification import _DETERMINISTIC_MODES, _output_stem


def test_load_config(experiments):
    """Config loads from TOML with expected fields."""
    config = experiments["sweeps"]["verification"]
    # Proof-of-concept: single best config (DeepSeek V3.2 decomposed)
    assert len(config["base_configs"]) == 1
    assert "unverified" in config["verification_modes"]
    assert "web" in config["verification_modes"]
    assert config["repeat"] == 3
    assert config["cross_verifier"] == "anthropic/claude-sonnet-4.6"


def test_output_stem():
    """Output filenames follow {model_short}-{mode}-run{n} pattern."""
    assert _output_stem("openai/gpt-5.4", "self", 2) == "gpt-5.4-self-run2"
    assert _output_stem("claude-opus-4.6", "tool", 1) == "claude-opus-4.6-tool-run1"
    assert (
        _output_stem("google/gemini-2.5-flash-lite", "web", 3) == "gemini-2.5-flash-lite-web-run3"
    )


def test_deterministic_modes():
    """Unverified, tool, and web are deterministic (run once)."""
    assert "unverified" in _DETERMINISTIC_MODES
    assert "tool" in _DETERMINISTIC_MODES
    assert "web" in _DETERMINISTIC_MODES
    assert "self" not in _DETERMINISTIC_MODES
    assert "cross" not in _DETERMINISTIC_MODES


def test_condition_count(experiments):
    """1 config x (3 deterministic x 1 + 2 stochastic x 3) = 9 conditions."""
    config = experiments["sweeps"]["verification"]
    repeat = config.get("repeat", 3)

    count = 0
    for _base in config["base_configs"]:
        for mode in config["verification_modes"]:
            runs = 1 if mode in _DETERMINISTIC_MODES else repeat
            count += runs

    assert count == 9


def test_unverified_baseline(tmp_path):
    """Unverified mode scores existing citations without API calls."""
    from aedist.verify import verify_unverified

    rows = [
        {"name": "Pha Lai", "fuel": "coal", "source_ref": "Decision 1509/QD-BCT Annex II"},
        {"name": "Ba Ria", "fuel": "gas", "source_ref": ""},
    ]
    annotated, summary = verify_unverified(rows)

    assert len(annotated) == 2
    assert summary["mode"] == "unverified"

    # Pha Lai has a primary-pattern citation → score >= 3
    assert int(annotated[0]["evidence_score"]) >= 3

    # Ba Ria has no source → score 1
    assert annotated[1]["evidence_score"] == "1"


# ---------------------------------------------------------------------------
# load_config — YAML file loading
# ---------------------------------------------------------------------------


def test_load_config_yaml(tmp_path):
    """load_config reads a YAML file and returns its contents as a dict."""
    from aedist.query_verification import load_config

    cfg = {
        "base_configs": [{"model": "m1", "method": "single", "result_file": "f.json"}],
        "verification_modes": ["unverified", "tool"],
        "repeat": 5,
    }
    yaml_path = tmp_path / "cfg.yaml"
    import yaml

    yaml_path.write_text(yaml.dump(cfg))

    loaded = load_config(yaml_path)
    assert loaded["repeat"] == 5
    assert loaded["verification_modes"] == ["unverified", "tool"]
    assert len(loaded["base_configs"]) == 1


def test_load_config_empty_yaml(tmp_path):
    """load_config returns None for an empty YAML file."""
    from aedist.query_verification import load_config

    yaml_path = tmp_path / "empty.yaml"
    yaml_path.write_text("")
    assert load_config(yaml_path) is None


# ---------------------------------------------------------------------------
# _estimate_llm_cost — pure arithmetic
# ---------------------------------------------------------------------------


def test_estimate_llm_cost_basic():
    """Cost formula: (prompt * 3.0 + completion * 15.0) / 1_000_000."""
    from aedist.query_verification import _estimate_llm_cost

    summary = {"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0}}
    assert _estimate_llm_cost(summary) == pytest.approx(3.0)

    summary2 = {"usage": {"prompt_tokens": 0, "completion_tokens": 1_000_000}}
    assert _estimate_llm_cost(summary2) == pytest.approx(15.0)


def test_estimate_llm_cost_combined():
    """Both token types contribute to cost."""
    from aedist.query_verification import _estimate_llm_cost

    summary = {"usage": {"prompt_tokens": 500_000, "completion_tokens": 100_000}}
    expected = (500_000 * 3.0 + 100_000 * 15.0) / 1_000_000
    assert _estimate_llm_cost(summary) == pytest.approx(expected)


def test_estimate_llm_cost_missing_usage():
    """Missing usage dict returns zero cost."""
    from aedist.query_verification import _estimate_llm_cost

    assert _estimate_llm_cost({}) == 0.0
    assert _estimate_llm_cost({"usage": {}}) == 0.0


def test_estimate_llm_cost_none_tokens():
    """None token counts are treated as zero."""
    from aedist.query_verification import _estimate_llm_cost

    summary = {"usage": {"prompt_tokens": None, "completion_tokens": None}}
    assert _estimate_llm_cost(summary) == 0.0


# ---------------------------------------------------------------------------
# _evaluate_plants — metrics from Plant objects and a reference CSV
# ---------------------------------------------------------------------------


def _make_reference_csv(tmp_path):
    """Create a minimal reference CSV and return its path."""
    import csv

    ref_path = tmp_path / "reference.csv"
    with open(ref_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "province", "fuel", "capacity_mwe", "status"])
        w.writerow(["Pha Lai", "Hai Duong", "coal", "600", "operational"])
        w.writerow(["Ca Mau I", "Ca Mau", "gas", "771", "operational"])
        w.writerow(["Vinh Tan 2", "Binh Thuan", "coal", "1244", "operational"])
    return ref_path


def test_evaluate_plants_empty_list(tmp_path):
    """Empty system plant list returns zeroed metrics."""
    from aedist.query_verification import _evaluate_plants

    ref_path = _make_reference_csv(tmp_path)
    cache = {}
    result = _evaluate_plants([], ref_path, cache)

    assert result["n_plants"] == 0
    assert result["tp"] == 0
    assert result["fp"] == 0
    assert result["fn"] == 0
    assert result["f1"] == 0.0
    assert result["precision"] == 0.0
    assert result["coverage"] == 0.0


def test_evaluate_plants_with_matches(tmp_path):
    """System plants matching reference yield nonzero metrics."""
    from aedist.query_verification import _evaluate_plants
    from aedist.schema import Plant

    ref_path = _make_reference_csv(tmp_path)
    cache = {}

    system_plants = [
        Plant(name="Pha Lai", fuel="coal", province="Hai Duong", capacity_mwe=600.0),
        Plant(name="Ca Mau I", fuel="gas", province="Ca Mau", capacity_mwe=771.0),
    ]
    result = _evaluate_plants(system_plants, ref_path, cache)

    assert result["n_plants"] == 2
    assert result["tp"] >= 1  # at least one match expected
    assert isinstance(result["f1"], float)
    assert result["f1"] > 0
    # Cache should now contain the reference
    assert str(ref_path) in cache


def test_evaluate_plants_cache_reuse(tmp_path):
    """Second call reuses the ref_plants_cache instead of re-loading."""
    from aedist.query_verification import _evaluate_plants
    from aedist.schema import Plant

    ref_path = _make_reference_csv(tmp_path)
    cache = {}

    plants = [Plant(name="Pha Lai", fuel="coal", capacity_mwe=600.0)]
    _evaluate_plants(plants, ref_path, cache)
    assert str(ref_path) in cache

    # Mutate cache entry to prove second call reads from cache
    cached_list = cache[str(ref_path)]

    result2 = _evaluate_plants(plants, ref_path, cache)
    assert result2["n_plants"] == 1
    # Cache wasn't reloaded (same object identity)
    assert cache[str(ref_path)] is cached_list


def test_evaluate_plants_no_reference_match(tmp_path):
    """System plant not in reference yields metrics with n_plants=1."""
    from aedist.query_verification import _evaluate_plants
    from aedist.schema import Plant

    ref_path = _make_reference_csv(tmp_path)
    cache = {}

    system_plants = [
        Plant(name="Nonexistent Power Plant XYZ", fuel="coal", capacity_mwe=100.0),
    ]
    result = _evaluate_plants(system_plants, ref_path, cache)

    assert result["n_plants"] == 1
    # Only 1 system plant vs 3 reference → most reference plants are missed
    assert result["fn"] >= 2
    assert result["f1"] < 1.0


# ---------------------------------------------------------------------------
# _write_filtered_csv — filtering by evidence_score
# ---------------------------------------------------------------------------


def test_write_filtered_csv_filters_low_scores(tmp_path):
    """Only rows with evidence_score >= 3 are written."""
    from aedist.query_verification import _write_filtered_csv

    annotated = [
        {"name": "Plant A", "fuel": "coal", "evidence_score": "4"},
        {"name": "Plant B", "fuel": "gas", "evidence_score": "2"},
        {"name": "Plant C", "fuel": "coal", "evidence_score": "3"},
        {"name": "Plant D", "fuel": "oil", "evidence_score": "1"},
    ]
    out_path = tmp_path / "filtered.csv"
    _write_filtered_csv(annotated, out_path)

    import csv

    with open(out_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert names == {"Plant A", "Plant C"}


def test_write_filtered_csv_all_below_threshold(tmp_path):
    """When no rows pass the filter, the file contains only a header."""
    from aedist.query_verification import _write_filtered_csv

    annotated = [
        {"name": "Plant A", "fuel": "coal", "evidence_score": "1"},
        {"name": "Plant B", "fuel": "gas", "evidence_score": "2"},
    ]
    out_path = tmp_path / "filtered_empty.csv"
    _write_filtered_csv(annotated, out_path)

    import csv

    with open(out_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        # Header should exist but no data rows
        assert len(rows) == 0
        assert reader.fieldnames is not None


def test_write_filtered_csv_custom_min_score(tmp_path):
    """Custom min_score parameter is respected."""
    from aedist.query_verification import _write_filtered_csv

    annotated = [
        {"name": "Plant A", "evidence_score": "4"},
        {"name": "Plant B", "evidence_score": "3"},
        {"name": "Plant C", "evidence_score": "2"},
    ]
    out_path = tmp_path / "filtered_custom.csv"
    _write_filtered_csv(annotated, out_path, min_score=4)

    import csv

    with open(out_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["name"] == "Plant A"


def test_write_filtered_csv_creates_parent_dirs(tmp_path):
    """Parent directories are created when they don't exist."""
    from aedist.query_verification import _write_filtered_csv

    annotated = [
        {"name": "Plant A", "evidence_score": "1"},
    ]
    out_path = tmp_path / "sub" / "dir" / "filtered.csv"
    _write_filtered_csv(annotated, out_path)
    assert out_path.exists()


# ---------------------------------------------------------------------------
# run_condition — integration test with "unverified" mode (no API calls)
# ---------------------------------------------------------------------------


def test_run_condition_unverified_mode(tmp_path):
    """run_condition with 'unverified' mode returns a RunRecord without API calls."""
    from aedist.query_verification import run_condition
    from aedist.schema import RunRecord

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    rows = [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": "600",
            "source_ref": "Decision 1509/QD-BCT Annex II",
        },
        {"name": "Ca Mau I", "fuel": "gas", "capacity_mwe": "771", "source_ref": ""},
        {
            "name": "Vinh Tan 2",
            "fuel": "coal",
            "capacity_mwe": "1244",
            "source_ref": "EVN Annual Report 2020",
        },
    ]

    base_config = {
        "model": "openai/gpt-4o",
        "method": "single",
        "result_file": "outputs/single/gpt-4o-run1.json",
    }

    record = run_condition(
        rows=rows,
        base_config=base_config,
        mode="unverified",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
    )

    assert isinstance(record, RunRecord)
    assert record.method_params.model == "openai/gpt-4o"
    assert record.method_params.extra["verification_mode"] == "unverified"
    assert record.result_summary.status == "ok"
    assert record.result_summary.n_plants >= 0
    assert record.resource_use.cost_usd == 0.0

    # Verify output files were written
    stem = "gpt-4o-unverified-run1"
    assert (output_dir / f"{stem}.csv").exists()
    assert (output_dir / f"{stem}_filtered.csv").exists()


def test_run_condition_unverified_justification(tmp_path):
    """Justification dict contains verification metadata."""
    from aedist.query_verification import run_condition

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    rows = [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": "600",
            "source_ref": "Decision 1509/QD-BCT",
        },
    ]
    base_config = {
        "model": "test-model",
        "method": "single",
        "result_file": "test.json",
    }

    record = run_condition(
        rows=rows,
        base_config=base_config,
        mode="unverified",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
    )

    assert record.justification["verification_mode"] == "unverified"
    assert "mean_evidence_score" in record.justification
    assert "score_distribution" in record.justification
    assert "filtered_metrics" in record.justification
    assert record.justification["verification_cost_usd"] == 0.0


def test_run_condition_tool_mode(tmp_path):
    """run_condition with 'tool' mode verifies against reference (no API calls)."""
    from aedist.query_verification import run_condition
    from aedist.schema import RunRecord

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    rows = [
        {"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "600"},
        {"name": "Totally Fake Plant", "fuel": "gas", "capacity_mwe": "100"},
    ]

    base_config = {
        "model": "test/model-v1",
        "method": "rag",
        "result_file": "outputs/rag/model-v1-run1.json",
    }

    record = run_condition(
        rows=rows,
        base_config=base_config,
        mode="tool",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
    )

    assert isinstance(record, RunRecord)
    assert record.method_params.extra["verification_mode"] == "tool"
    assert record.resource_use.cost_usd == 0.0


def test_run_condition_cached_skip(tmp_path):
    """run_condition returns None when output CSV already exists (cache hit)."""
    from aedist.query_verification import run_condition

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Pre-create the CSV that run_condition would write
    stem = "gpt-4o-unverified-run1"
    (output_dir / f"{stem}.csv").write_text("name,fuel\n")

    rows = [{"name": "Pha Lai", "fuel": "coal"}]
    base_config = {
        "model": "openai/gpt-4o",
        "method": "single",
        "result_file": "test.json",
    }

    result = run_condition(
        rows=rows,
        base_config=base_config,
        mode="unverified",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
    )

    assert result is None


def test_run_condition_unknown_mode(tmp_path):
    """run_condition returns None for an unknown verification mode."""
    from aedist.query_verification import run_condition

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = run_condition(
        rows=[{"name": "X", "fuel": "coal"}],
        base_config={"model": "m", "method": "single", "result_file": "f.json"},
        mode="bogus_mode",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
    )

    assert result is None


def test_run_condition_self_mode(tmp_path):
    """run_condition with 'self' mode calls verify_self and estimates cost."""
    from unittest.mock import patch

    from aedist.query_verification import run_condition
    from aedist.schema import RunRecord

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    rows = [
        {"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "600"},
    ]
    base_config = {
        "model": "openai/gpt-4o",
        "method": "single",
        "result_file": "test.json",
    }

    fake_annotated = [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": "600",
            "evidence_score": "3",
            "verified": "True",
            "source_1": "Decision 1509",
            "source_1_type": "primary",
            "source_2": "",
            "source_2_type": "none",
        },
    ]
    fake_summary = {
        "mode": "self",
        "total_plants": 1,
        "mean_evidence_score": 3.0,
        "score_distribution": {"0": 0, "1": 0, "2": 0, "3": 1, "4": 0},
        "usage": {"prompt_tokens": 1000, "completion_tokens": 200},
    }

    with patch(
        "aedist.query_verification.verify_self", return_value=(fake_annotated, fake_summary)
    ):
        record = run_condition(
            rows=rows,
            base_config=base_config,
            mode="self",
            run=1,
            output_dir=output_dir,
            reference_path=ref_path,
            ref_plants_cache={},
        )

    assert isinstance(record, RunRecord)
    assert record.method_params.extra["verification_mode"] == "self"
    # Cost should be non-zero (1000 * 3.0 + 200 * 15.0) / 1_000_000
    assert record.resource_use.cost_usd > 0


def test_run_condition_cross_mode(tmp_path):
    """run_condition with 'cross' mode calls verify_cross with the cross_verifier."""
    from unittest.mock import patch

    from aedist.query_verification import run_condition
    from aedist.schema import RunRecord

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    rows = [
        {"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "600"},
    ]
    base_config = {
        "model": "openai/gpt-4o",
        "method": "single",
        "result_file": "test.json",
    }

    fake_annotated = [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": "600",
            "evidence_score": "3",
            "verified": "True",
            "source_1": "PDP8",
            "source_1_type": "primary",
            "source_2": "",
            "source_2_type": "none",
        },
    ]
    fake_summary = {
        "mode": "cross",
        "total_plants": 1,
        "mean_evidence_score": 3.0,
        "score_distribution": {"0": 0, "1": 0, "2": 0, "3": 1, "4": 0},
        "usage": {"prompt_tokens": 2000, "completion_tokens": 500},
    }

    with patch(
        "aedist.query_verification.verify_cross", return_value=(fake_annotated, fake_summary)
    ):
        record = run_condition(
            rows=rows,
            base_config=base_config,
            mode="cross",
            run=1,
            output_dir=output_dir,
            reference_path=ref_path,
            ref_plants_cache={},
            cross_verifier="anthropic/claude-sonnet-4.6",
        )

    assert isinstance(record, RunRecord)
    assert record.method_params.extra["verification_mode"] == "cross"
    assert record.method_params.extra["cross_verifier"] == "anthropic/claude-sonnet-4.6"
    assert record.resource_use.cost_usd > 0


def test_run_condition_web_mode(tmp_path):
    """run_condition with 'web' mode calls verify_web and computes Tavily cost."""
    from unittest.mock import patch

    from aedist.query_verification import run_condition
    from aedist.schema import RunRecord

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    rows = [
        {"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "600"},
    ]
    base_config = {
        "model": "openai/gpt-4o",
        "method": "single",
        "result_file": "test.json",
    }

    fake_annotated = [
        {
            "name": "Pha Lai",
            "fuel": "coal",
            "capacity_mwe": "600",
            "evidence_score": "3",
            "verified": "True",
            "source_1": "GEM (gem.wiki)",
            "source_1_type": "primary",
            "source_2": "",
            "source_2_type": "none",
        },
    ]
    fake_summary = {
        "mode": "web",
        "total_plants": 1,
        "mean_evidence_score": 3.0,
        "score_distribution": {"0": 0, "1": 0, "2": 0, "3": 1, "4": 0},
        "searches_performed": 5,
    }

    with patch(
        "aedist.query_verification.verify_web", return_value=(fake_annotated, fake_summary)
    ):
        record = run_condition(
            rows=rows,
            base_config=base_config,
            mode="web",
            run=1,
            output_dir=output_dir,
            reference_path=ref_path,
            ref_plants_cache={},
            tavily_key="fake-tavily-key",
        )

    assert isinstance(record, RunRecord)
    assert record.method_params.extra["verification_mode"] == "web"
    # Cost = 5 searches * 0.005 per search = 0.025
    assert record.resource_use.cost_usd == pytest.approx(0.025)


def test_run_condition_cross_no_verifier(tmp_path):
    """run_condition returns None for cross mode without a cross_verifier."""
    from aedist.query_verification import run_condition

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = run_condition(
        rows=[{"name": "X", "fuel": "coal"}],
        base_config={"model": "m", "method": "single", "result_file": "f.json"},
        mode="cross",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
        cross_verifier=None,
    )

    assert result is None


def test_run_condition_web_no_tavily_key(tmp_path):
    """run_condition returns None for web mode without TAVILY_API_KEY."""
    from aedist.query_verification import run_condition

    ref_path = _make_reference_csv(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = run_condition(
        rows=[{"name": "X", "fuel": "coal"}],
        base_config={"model": "m", "method": "single", "result_file": "f.json"},
        mode="web",
        run=1,
        output_dir=output_dir,
        reference_path=ref_path,
        ref_plants_cache={},
        tavily_key=None,
    )

    assert result is None


# ---------------------------------------------------------------------------
# main() — dry-run path with --config
# ---------------------------------------------------------------------------


def test_main_dry_run_with_config(tmp_path, monkeypatch):
    """main() --config --dry-run loads YAML and enumerates conditions."""
    import sys

    import yaml

    from aedist.query_verification import main

    cfg = {
        "base_configs": [
            {"model": "openai/gpt-4o", "method": "single", "result_file": "f.json"},
        ],
        "verification_modes": ["unverified", "self"],
        "repeat": 2,
    }
    yaml_path = tmp_path / "verify_cfg.yaml"
    yaml_path.write_text(yaml.dump(cfg))

    monkeypatch.setattr(
        sys,
        "argv",
        ["query_verification", "--config", str(yaml_path), "--dry-run"],
    )

    # Should not raise; dry-run returns early without running conditions
    main()


def test_main_dry_run_with_sweep(monkeypatch):
    """main() --sweep --dry-run loads experiments.toml and enumerates conditions."""
    import sys

    from aedist.query_verification import main

    experiments_toml = str(Path(__file__).parent.parent / "experiments" / "experiments.toml")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "query_verification",
            "--sweep",
            "verification",
            "--experiments",
            experiments_toml,
            "--dry-run",
        ],
    )

    main()


def test_main_no_config_no_sweep_errors(monkeypatch):
    """main() without --config or --sweep exits with an error."""
    import sys

    from aedist.query_verification import main

    monkeypatch.setattr(sys, "argv", ["query_verification"])

    with pytest.raises(SystemExit):
        main()
