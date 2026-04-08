"""Integration test: full pipeline on real data (Claude census output vs HDM reference)."""

from pathlib import Path

import pytest

from aedist.metrics import compute_metrics, format_metrics
from aedist.reconcile import reconcile
from aedist.evaluate import load_plants_csv
from aedist.schema import MatchType

DATA_DIR = Path(__file__).parent.parent / "data" / "reference"
OUTPUTS_DIR = Path(__file__).parent.parent / "experiments" / "outputs"

_REF_PATH = DATA_DIR / "vietnam_thermal_v1.csv"
_CENSUS_PATH = OUTPUTS_DIR / "census" / "claude-sonnet-4.6-run1.csv"

_SKIP_REF = pytest.mark.skipif(not _REF_PATH.exists(), reason=f"Missing {_REF_PATH}")
_SKIP_CENSUS = pytest.mark.skipif(not _CENSUS_PATH.exists(), reason=f"Missing {_CENSUS_PATH}")


@pytest.fixture
def reference():
    return load_plants_csv(_REF_PATH)


@pytest.fixture
def claude_census():
    return load_plants_csv(_CENSUS_PATH)


class TestLoadData:
    @_SKIP_REF
    def test_reference_count(self, reference):
        assert len(reference) == 163

    @_SKIP_CENSUS
    def test_claude_census_count(self, claude_census):
        assert len(claude_census) == 53  # 54 lines - 1 header


@_SKIP_REF
@_SKIP_CENSUS
class TestReconciliation:
    def test_reconcile_produces_entries(self, reference, claude_census):
        entries = reconcile(reference, claude_census)
        assert len(entries) > 0
        # Every reference plant must appear (matched or missed)
        ref_entries = [e for e in entries if e.match_type != MatchType.SYSTEM_ONLY]
        [e for e in entries if e.match_type != MatchType.REFERENCE_ONLY]
        assert len(ref_entries) >= len(reference)

    def test_metrics_are_plausible(self, reference, claude_census):
        entries = reconcile(reference, claude_census)
        m = compute_metrics(entries)
        # Census run with 53 plants vs 163 reference: moderate coverage
        assert 0.1 < m.coverage < 0.7
        # Precision should be reasonable (Claude doesn't hallucinate much)
        assert m.precision > 0.3
        # Sanity: n_reference = 163
        assert m.n_reference == 163
        print("\n" + format_metrics(m))


@_SKIP_REF
@_SKIP_CENSUS
class TestMetricsAttributes:
    def test_error_taxonomy_keys(self, reference, claude_census):
        entries = reconcile(reference, claude_census)
        m = compute_metrics(entries)
        expected_keys = {
            "hallucinated_plant", "missed_plant", "wrong_fuel",
            "wrong_status", "wrong_province", "capacity_mismatch",
        }
        assert set(m.errors.keys()) == expected_keys
