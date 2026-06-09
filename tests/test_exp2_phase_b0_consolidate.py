"""Tests for experiments.sota.exp2_phase_b0_consolidate."""

import json
import re
from pathlib import Path

from experiments.sota.exp2_phase_b0_consolidate import _count_table_rows, consolidate_batch


def test_count_table_rows_ignores_summary_tables():
    text = (
        "| Name | Fuel | Province | Capacity | Status | COD |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
        "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n"
        "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n\n"
        "| Fuel | Capacity |\n"
        "| --- | --- |\n"
        "| Coal | 2910 |\n"
        "| Gas | 0 |\n"
    )
    assert _count_table_rows(text) == 3


def _make_agent_run_dir(base: Path, agent: str, run: int) -> Path:
    """Create a minimal {agent}_run{N:02d}/ structure under base."""
    run_tag = f"run{run:02d}"
    agent_dir = base / f"{agent}_{run_tag}"
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Minimal phase_a record so _process_agent can read model/cost
    phase_a = {
        "resource_use": {"cost_usd": 0.01},
        "method_params": {"model": f"test-model-{agent}"},
    }
    (agent_dir / f"{agent}_phase_a.json").write_text(
        json.dumps(phase_a), encoding="utf-8"
    )

    # One turn: cost + record files
    cost = {
        "classification": "report",
        "spent_usd": 0.02,
        "classifier_cost_usd": 0.001,
    }
    (agent_dir / f"{agent}_turn_01.cost.json").write_text(
        json.dumps(cost), encoding="utf-8"
    )
    record = {
        "resource_use": {"wall_s": 1.5},
        "method_params": {"model": f"test-model-{agent}"},
        "justification": {
            "output_text": (
                "| Plant | Fuel | Status |\n"
                "|-------|------|--------|\n"
                f"| {agent.title()} Plant | Coal | Operating |\n"
            )
        },
    }
    (agent_dir / f"{agent}_turn_01.record.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    return agent_dir


def test_consolidate_batch_walks_run_subdirs(tmp_path):
    """consolidate_batch discovers run{N}/ subdirs and processes each run.

    Verifies the run{N}/ layout walk: given a batch directory with run01/ and
    run02/ containing per-agent subdirectories, consolidate_batch must produce
    {agent}_run{N}.md files and a summary.json aggregating both runs.
    """
    batch_dir = tmp_path / "sota_exp3_arm2_batch1"
    agents = ["openai", "mistral"]

    for run_number in (1, 2):
        run_dir = batch_dir / f"run{run_number:02d}"
        run_dir.mkdir(parents=True)
        for agent in agents:
            _make_agent_run_dir(run_dir, agent, run_number)

    consolidate_batch(batch_dir)

    # Each run dir should have per-agent .md and .json artifacts
    for run_number in (1, 2):
        run_dir = batch_dir / f"run{run_number:02d}"
        run_tag = f"run{run_number:02d}"
        for agent in agents:
            md_path = run_dir / f"{agent}_{run_tag}.md"
            json_path = run_dir / f"{agent}_{run_tag}.json"
            assert md_path.exists(), f"Missing {md_path}"
            assert json_path.exists(), f"Missing {json_path}"
            rec = json.loads(json_path.read_text(encoding="utf-8"))
            assert rec["run"] == run_number
            assert rec["agent"] == agent

    # summary.json must aggregate all runs
    for run_number in (1, 2):
        run_dir = batch_dir / f"run{run_number:02d}"
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        run_agents = {r["agent"] for r in summary}
        assert set(agents).issubset(run_agents), (
            f"run{run_number:02d}/summary.json missing agents: "
            f"{set(agents) - run_agents}"
        )

    # Non-run directories must be ignored (no crash)
    assert not re.match(r"run\d+", "probes")  # sanity-check the RE
    probes_dir = batch_dir / "probes"
    if probes_dir.exists():
        assert (batch_dir / "run01" / "summary.json").exists()
