"""Standing class test: every exp1_batch2 CSV consumer ignores colocated non-run outputs.

Tickets 0496/0499 — guards the greedy-glob anti-pattern class (0492/0495).
Batch2 consumers are seeded with reconciliation_*/filtered_* PREFIX decoys; the
two source-aware consumers (score_provenance, audit_lp_mismatched) are also
seeded with the real *_filtered.csv SUFFIX decoy that retains source_1.
Registered consumers: score_exp1, screen_validation_within_model, tabulate_coherence,
score_provenance, scripts.audit_lp_mismatched, and the 0492 test path.
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

    def test_score_provenance(self, tmp_path):
        """score_provenance.score_directory ignores the *_filtered.csv suffix
        decoy that RETAINS source_1 — the content filter alone would score it as
        a spurious run alongside its base run (query_verification emits both)."""
        from aedist.score_provenance import score_directory

        input_dir = tmp_path / "runs"
        input_dir.mkdir()
        # genuine + reconciliation_ prefix + the real _filtered.csv suffix decoy,
        # all carrying source_1 so the content filter cannot distinguish them.
        for name in [
            "model-a-run1.csv",
            "model-b-run1.csv",
            "reconciliation_model-a-run1.csv",
            "model-a-run1_filtered.csv",
        ]:
            (input_dir / name).write_text(_SAMPLE_CSV, encoding="utf-8")

        result = score_directory(input_dir)
        runs = result["runs"]
        assert len(runs) == 2, f"Expected 2 genuine runs, got {len(runs)} — decoys leaked"
        for stem in runs:
            assert not stem.startswith("reconciliation_")
            assert not stem.endswith("_filtered")

    def test_audit_lp_mismatched(self, tmp_path):
        """scripts.audit_lp_mismatched.sweep ignores reconciliation_ prefix and
        _filtered.csv suffix decoys."""
        from scripts.audit_lp_mismatched import sweep

        # A run whose single plant force-matches the reference under a low
        # similarity → a Mismatched pair, so genuine runs produce output.
        run_csv = (
            "name,fuel,status,status_as_of,cod,province,capacity_mwe,"
            "confidence,source_1,source_2,note\n"
            "Zzz Unrelated Plant,coal,operating,2024-01-01,2020,Hanoi,600,"
            "HIGH,http://a,http://b,ok\n"
        )
        input_dir = tmp_path / "runs"
        input_dir.mkdir()
        for name in [
            "model-a-run1.csv",
            "model-b-run1.csv",
            "reconciliation_model-a-run1.csv",
            "model-a-run1_filtered.csv",
        ]:
            (input_dir / name).write_text(run_csv, encoding="utf-8")
        ref = tmp_path / "reference.csv"
        ref.write_text(_SAMPLE_REF, encoding="utf-8")

        rows = sweep(ref, input_dir)
        # Assert on (model, run) pairs, not just models: the _filtered.csv decoy
        # parses to model="model-a", run="run1_filtered" — a leak that a
        # model-only check would miss because it reuses a genuine model name.
        pairs = {(r["model"], r["run"]) for r in rows}
        # Genuine runs must have been processed (sanity: not vacuously green).
        assert pairs == {("model-a", "run1"), ("model-b", "run1")}, (
            f"Expected only genuine (model, run) pairs, got {pairs}"
        )

    def test_variability_screen_regression_guard(self):
        """The 0492 test glob also skips colocated outputs (source inspection)."""
        from pathlib import Path

        src = Path(__file__).parent / "test_score_mechanical.py"
        text = src.read_text(encoding="utf-8")
        assert '"reconciliation_"' in text or "'reconciliation_'" in text, (
            "test_score_mechanical.py lost its reconciliation_ skip guard"
        )
        assert '"filtered_"' in text or "'filtered_'" in text, (
            "test_score_mechanical.py lost its filtered_ skip guard"
        )
