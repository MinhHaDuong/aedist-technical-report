import importlib

import pandas as pd
import pytest


@pytest.fixture(params=["lp", "phased"])
def reconcile(request):
    module = importlib.import_module(f"aedist.matching.{request.param}")
    return module.reconcile


def _make_df(rows):
    """Build a DataFrame with the columns the LP matcher expects."""
    return pd.DataFrame(rows, columns=["name", "name_clean", "capacity_clean"])


def test_fuzzy_match_result_contains_similarity_score(reconcile):
    """LP reconciliation result includes numeric similarity_score for fuzzy matches."""
    df1 = _make_df([("Vung Ang 1", "vung ang 1", 600)])
    df2 = _make_df([("Vung Ang I", "vung ang i", 600)])
    result = reconcile(df1, df2)

    assert "similarity_score" in result.columns, (
        "Result DataFrame must contain a 'similarity_score' column"
    )
    score = result.iloc[0]["similarity_score"]
    assert isinstance(score, (int, float)), (
        f"similarity_score must be numeric, got {type(score)}"
    )
    assert 0 < score <= 100, (
        f"similarity_score must be in (0, 100], got {score}"
    )


def test_exact_match_score_is_100(reconcile):
    """Exact name matches get similarity_score == 100."""
    df1 = _make_df([("Plant A", "plant a", 50)])
    df2 = _make_df([("Plant A", "plant a", 50)])
    result = reconcile(df1, df2)

    assert result.iloc[0]["similarity_score"] == 100


def test_unmatched_score_is_none(reconcile):
    """Unmatched entries (Only in file1) have similarity_score == None."""
    df1 = _make_df([("Plant A", "plant a", 100)])
    df2 = _make_df([]).reindex(columns=["name", "name_clean", "capacity_clean"])
    result = reconcile(df1, df2)

    assert pd.isna(result.iloc[0]["similarity_score"])
