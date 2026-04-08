"""Tests for aedist.query_verification — sweep 4 runner."""

from aedist.query_verification import _DETERMINISTIC_MODES, _output_stem


def test_load_config(experiments):
    """Config loads from TOML with expected fields."""
    config = experiments["sweeps"]["verification"]
    assert len(config["base_configs"]) == 3
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
    """3 configs x (3 deterministic x 1 + 2 stochastic x 3) = 27 conditions."""
    config = experiments["sweeps"]["verification"]
    repeat = config.get("repeat", 3)

    count = 0
    for _base in config["base_configs"]:
        for mode in config["verification_modes"]:
            runs = 1 if mode in _DETERMINISTIC_MODES else repeat
            count += runs

    assert count == 27


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
