"""Standing class test: every exp1_batch2 CSV consumer ignores colocated non-run outputs.

Ticket 0496 — guards the greedy-glob anti-pattern class (0492/0495).
Seeded with genuine + reconciliation_* + filtered_* decoys; asserts decoys ignored.
"""

import pytest

_SAMPLE_CSV = (
    "name,fuel,status,status_as_of,cod,province,capacity_mwe,"
    "confidence,source_1,source_2,note\n"
    "Plant A,coal,operating,2024-01-01,2020,Hanoi,600,"
    "HIGH,http://a,http://b,ok\n"
)

_SAMPLE_REF = (
    "name,fuel,status,province,cod,capacity_mwe\n"
    "Plant A,coal,operating,Hanoi,2020,600\n"
)

GENUINE_NAMES = ["model-a-run1.csv", "model-b-run1.csv"]
DECOY_NAMES = [
    "reconciliation_model-a-run1.csv",
    "filtered_model-b-run1.csv",
]


def _seed_dir(tmp_path):
    """Create a tmp dir with genuine + decoy CSVs, return (input_dir, ref_path)."""
    input_dir = tmp_path / "runs"
    input_dir.mkdir()
    for name in GENUINE_NAMES + DECOY_NAMES:
        (input_dir / name).write_text(_SAMPLE_CSV, encoding="utf-8")
    ref = tmp_path / "reference.csv"
    ref.write_text(_SAMPLE_REF, encoding="utf-8")
    return input_dir, ref


@pytest.mark.adherence
class TestNoColocatedOutputLeak:
    """Each registered consumer must ignore reconciliation_*/filtered_* decoys."""

    def test_score_exp1(self, tmp_path):
        import csv

        from aedist.score_exp1 import main

        input_dir, ref = _seed_dir(tmp_path)
        out = tmp_path / "out.csv"
        main([
            "--input-dir", str(input_dir),
            "--output", str(out),
            "--reference", str(ref),
        ])
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        models = {r["model"] for r in rows}
        assert len(rows) == len(GENUINE_NAMES), (
            f"Expected {len(GENUINE_NAMES)} rows, got {len(rows)} — decoys leaked"
        )
        for m in models:
            assert not m.startswith("reconciliation_")
            assert not m.startswith("filtered_")

    def test_screen_validation_within_model(self, tmp_path):
        from aedist.screen_validation_within_model import _load_raw_runs

        input_dir, _ = _seed_dir(tmp_path)
        runs = _load_raw_runs(input_dir, f1_map={})
        models = {r["model"] for r in runs}
        assert len(runs) == len(GENUINE_NAMES), (
            f"Expected {len(GENUINE_NAMES)} runs, got {len(runs)} — decoys leaked"
        )
        for m in models:
            assert not m.startswith("reconciliation_")
            assert not m.startswith("filtered_")

    def test_tabulate_coherence(self, tmp_path):
        from aedist.tabulate_coherence import load_extractions

        input_dir, _ = _seed_dir(tmp_path)
        groups = load_extractions([input_dir])
        assert len(groups) == len(GENUINE_NAMES), (
            f"Expected {len(GENUINE_NAMES)} models, got {len(groups)} — decoys leaked"
        )
        for model_slug in groups:
            assert not model_slug.startswith("reconciliation_")
            assert not model_slug.startswith("filtered_")
