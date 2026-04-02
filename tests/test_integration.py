"""Integration test: full pipeline on real data (Claude concise output vs HDM reference)."""

from pathlib import Path

import pytest

from aedist.metrics import compute_metrics, format_metrics
from aedist.reconcile import reconcile
from aedist.runner import load_plants_csv
from aedist.schema import MatchType

DATA_DIR = Path(__file__).parent.parent / "data" / "reference"
OUTPUTS_DIR = Path(__file__).parent.parent / "experiments" / "outputs"

_REF_PATH = DATA_DIR / "vietnam_thermal_v1.csv"
_CONCISE_PATH = OUTPUTS_DIR / "llm_direct" / "claude_sonnet_concise.csv"

_SKIP_REF = pytest.mark.skipif(not _REF_PATH.exists(), reason=f"Missing {_REF_PATH}")
_SKIP_CONCISE = pytest.mark.skipif(not _CONCISE_PATH.exists(), reason=f"Missing {_CONCISE_PATH}")


@pytest.fixture
def reference():
    return load_plants_csv(_REF_PATH)


@pytest.fixture
def claude_concise():
    return load_plants_csv(_CONCISE_PATH)


class TestLoadData:
    @_SKIP_REF
    def test_reference_count(self, reference):
        assert len(reference) == 163

    @_SKIP_CONCISE
    def test_claude_concise_count(self, claude_concise):
        assert len(claude_concise) == 30  # 31 lines - 1 header


@_SKIP_REF
@_SKIP_CONCISE
class TestReconciliation:
    def test_reconcile_produces_entries(self, reference, claude_concise):
        entries = reconcile(reference, claude_concise)
        assert len(entries) > 0
        # Every reference plant must appear (matched or missed)
        ref_entries = [e for e in entries if e.match_type != MatchType.SYSTEM_ONLY]
        [e for e in entries if e.match_type != MatchType.REFERENCE_ONLY]
        assert len(ref_entries) >= len(reference)

    def test_metrics_are_plausible(self, reference, claude_concise):
        entries = reconcile(reference, claude_concise)
        m = compute_metrics(entries)
        # Claude concise with 30 plants vs 163 reference: coverage should be low
        assert 0.05 < m.coverage < 0.5
        # Precision should be reasonable (Claude doesn't hallucinate much)
        assert m.precision > 0.3
        # Sanity: n_reference = 163
        assert m.n_reference == 163
        print("\n" + format_metrics(m))


@_SKIP_REF
@_SKIP_CONCISE
class TestMetricsAttributes:
    def test_error_taxonomy_keys(self, reference, claude_concise):
        entries = reconcile(reference, claude_concise)
        m = compute_metrics(entries)
        expected_keys = {
            "hallucinated_plant", "missed_plant", "wrong_fuel",
            "wrong_status", "wrong_province", "capacity_mismatch",
        }
        assert set(m.errors.keys()) == expected_keys
