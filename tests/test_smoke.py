"""Adherence tests for src/aedist/smoke.py.

The smoke utility is a one-off model probe; full network tests would
spend money, so this module covers CLI structure, default config matching
the locked Experiment 1 sweep, and the record-saving contract that
preserves full response bodies.
"""

import inspect

from aedist import smoke


def test_main_has_argparse():
    """Per project rule: every __main__ entry point gets argparse."""
    src = inspect.getsource(smoke.main)
    assert "argparse" in src
    assert "ArgumentParser" in src or "add_argument" in src


def test_default_seed_matches_locked_sweep():
    """Smoke defaults must mirror sweep_ablation_p1_direct_base so a
    smoke and a production rep are comparable.

    See experiments/experiments.toml [sweeps.sweep_ablation_p1_direct_base].
    """
    src = inspect.getsource(smoke.main)
    assert "default=42" in src, "seed default should match sweep seed=42"
    assert "default=32768" in src, "max_tokens default should match sweep max_tokens=32768"
    assert "default=0.0" in src, "temperature default should match sweep temperature=0.0"


def test_default_system_instruction_is_no_websearch():
    """The locked Experiment 1 baseline declares no-web-search; smoke
    must use the same instruction unless the caller overrides."""
    assert "web search" in smoke.DEFAULT_SYSTEM_INSTRUCTION.lower()
    assert "parametric" in smoke.DEFAULT_SYSTEM_INSTRUCTION.lower()


def test_record_saves_full_response_not_tail():
    """Regression: the original /tmp/smoke_36flash.py only captured
    response_tail_200, losing $0.024 of billed payload. smoke_one must
    save the FULL response under a 'response' key.
    """
    src = inspect.getsource(smoke.smoke_one)
    assert '"response": result["content"]' in src, "smoke_one must save full response, not a tail"
    # And explicitly NOT save only a tail
    assert "response_tail" not in src, (
        "smoke records must persist the full response body, "
        "not just response_tail_200 — that loses billed payload"
    )


def test_smoke_marker_in_record():
    """Smoke records carry an explicit smoke=True marker so a downstream
    rebuild-measurements run can filter them out and not treat them as
    production reps."""
    src = inspect.getsource(smoke.smoke_one)
    assert '"smoke": True' in src
