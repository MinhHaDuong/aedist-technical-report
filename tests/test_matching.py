import importlib

import pandas as pd
import pytest


# Parameterize the fixture over both implementations to run after this change.
@pytest.fixture(params=["lp", "phased"])
def reconcile(request):
    module = importlib.import_module(f"aedist.matching.{request.param}")
    return module.reconcile


def test_exact_match(reconcile):
    """Test when group1 and group2 contain exactly matching rows."""
    group1 = pd.DataFrame([{"name": "Plant A", "name_clean": "plant a", "capacity_clean": 50}])
    group2 = pd.DataFrame([{"name": "Plant A", "name_clean": "plant a", "capacity_clean": 50}])

    result = reconcile(group1, group2)

    # Expect a single match with exactly equal capacities.
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched"
    assert row["capacity_file1"] == 50
    assert row["capacity_file2"] == 50
    assert row["capacity_difference"] == 0


def test_only_in_file1(reconcile):
    """Test when group2 is empty, so all group1 capacity is unmatched."""
    group1 = pd.DataFrame([{"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}])
    group2 = pd.DataFrame(columns=["name", "name_clean", "capacity_clean"])

    result = reconcile(group1, group2)

    # Expect a single row flagged as "Only in file1".
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Only in file1"
    assert row["capacity_file1"] == 100
    assert row["name_file2"] is None


def test_only_in_file2(reconcile):
    """Test when group1 is empty, so all group2 capacity is unmatched."""
    group1 = pd.DataFrame(columns=["name", "name_clean", "capacity_clean"])
    group2 = pd.DataFrame([{"name": "Plant B", "name_clean": "plant b", "capacity_clean": 80}])

    result = reconcile(group1, group2)

    # Expect a single row flagged as "Only in file2".
    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Only in file2"
    assert row["capacity_file2"] == 80
    assert row["name_file1"] is None


def test_fuzzy_match_name(reconcile):
    """
    Test fuzzy matching with names that differ slightly but have capacities
    within the allowed tolerance.
    """
    group1 = pd.DataFrame([{"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}])
    group2 = pd.DataFrame(
        [
            {
                "name": "Plant A Incorporated",
                "name_clean": "plant a incorporated",
                "capacity_clean": 100,
            }
        ]
    )

    result = reconcile(group1, group2)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched (Fuzzy)"


def test_fuzzy_match_within_tolerance(reconcile):
    """
    Test fuzzy matching with names that differ slightly but have capacities
    within the allowed tolerance.
    """
    group1 = pd.DataFrame([{"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}])
    group2 = pd.DataFrame(
        [
            {
                "name": "Plant A Incorporated",
                "name_clean": "plant a incorporated",
                "capacity_clean": 145,
            }
        ]
    )

    result = reconcile(group1, group2, capacity_tolerance=50)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched (Fuzzy)"
    assert row["capacity_file1"] == 100
    assert row["capacity_file2"] == 145


def test_fuzzy_match_outside_tolerance(reconcile):
    """
    Test fuzzy matching with names that differ slightly but have capacities
    outside of the allowed tolerance.
    """
    group1 = pd.DataFrame([{"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100}])
    group2 = pd.DataFrame(
        [
            {
                "name": "Plant A Incorporated",
                "name_clean": "plant a incorporated",
                "capacity_clean": 145,
            }
        ]
    )

    result = reconcile(group1, group2, capacity_tolerance=0)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["status"] == "Matched (Fuzzy) (Diff)"
    assert row["capacity_file1"] == 100
    assert row["capacity_file2"] == 145


def test_main_example(reconcile):
    """
    Test the demo example originally run in the main() block.
    We expect two matches:
      - "Plant A" from file1 should be matched to "Plant A Incorporated" in file2 with a capacity difference of -5 and status "Matched (Fuzzy)".
      - "Plant B" should be exactly matched.
    """
    data1 = [
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100},
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
    ]
    data2 = [
        {
            "name": "Plant A Incorporated",
            "name_clean": "plant a incorporated",
            "capacity_clean": 105,
        },
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
    ]
    file1_df = pd.DataFrame(data1)
    file2_df = pd.DataFrame(data2)
    result = reconcile(
        file1_df,
        file2_df,
        similarity_threshold=90,
        capacity_tolerance=10,
        mismatch_penalty=1000,
    )

    # There should be exactly two rows of matches.
    assert len(result) == 2

    # Identify the matched pairs based on file1's name.
    row_a = result[result["name_file1"] == "Plant A"].iloc[0]
    row_b = result[result["name_file1"] == "Plant B"].iloc[0]

    # For Plant A: capacity difference = 100 - 105 = -5 (fuzzy match within tolerance)
    assert row_a["capacity_difference"] == -5
    assert row_a["status"] == "Matched (Fuzzy)"

    # For Plant B: capacity difference = 200 - 200 = 0 (exact match)
    assert row_b["capacity_difference"] == 0
    assert row_b["status"] == "Matched"


def test_greedy_prealign_exact_names():
    """Greedy pre-alignment should pair plants with identical names."""
    from aedist.matching.lp import _greedy_prealign

    df1 = pd.DataFrame(
        [
            {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100},
            {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
        ]
    )
    df2 = pd.DataFrame(
        [
            {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
            {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100},
        ]
    )

    pairs = _greedy_prealign(df1, df2)
    pair_set = set(pairs)

    # Plant A (i=0) should match Plant A (j=1), Plant B (i=1) should match Plant B (j=0)
    assert (0, 1) in pair_set
    assert (1, 0) in pair_set
    assert len(pairs) == 2


def test_greedy_prealign_no_match():
    """Completely different names should not be paired below threshold."""
    from aedist.matching.lp import _greedy_prealign

    df1 = pd.DataFrame(
        [
            {"name": "Alpha", "name_clean": "alpha", "capacity_clean": 100},
        ]
    )
    df2 = pd.DataFrame(
        [
            {"name": "Zeta", "name_clean": "zeta", "capacity_clean": 999},
        ]
    )

    pairs = _greedy_prealign(df1, df2)
    assert len(pairs) == 0


def test_warm_start_identical_to_cold():
    """Warm start must produce the same matching as a cold solve."""
    from pulp import PULP_CBC_CMD, LpStatusOptimal

    from aedist.matching.lp import (
        _apply_warm_start,
        _compute_costs,
        _extract_results,
        _greedy_prealign,
        _setup_lp,
    )

    data1 = [
        {"name": "Plant A", "name_clean": "plant a", "capacity_clean": 100},
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
        {"name": "Plant C", "name_clean": "plant c", "capacity_clean": 300},
        {"name": "Orphan Ref", "name_clean": "orphan ref", "capacity_clean": 50},
    ]
    data2 = [
        {"name": "Plant A Inc", "name_clean": "plant a inc", "capacity_clean": 105},
        {"name": "Plant B", "name_clean": "plant b", "capacity_clean": 200},
        {"name": "Plant C Corp", "name_clean": "plant c corp", "capacity_clean": 310},
        {"name": "Orphan Sys", "name_clean": "orphan sys", "capacity_clean": 999},
    ]
    df1 = pd.DataFrame(data1)
    df2 = pd.DataFrame(data2)
    params = {"similarity_threshold": 90, "mismatch_penalty": 1000, "capacity_weight": 0.001}

    costs = _compute_costs(df1, df2, **params)
    config = {"similarity_threshold": 90, "capacity_tolerance": 0}

    # Cold solve
    prob_cold, x_cold, u_cold, v_cold = _setup_lp(df1, df2, costs, 10000)
    prob_cold.solve(PULP_CBC_CMD(msg=False))
    assert prob_cold.status == LpStatusOptimal
    cold_results = _extract_results(
        {"df1": df1, "df2": df2, "x_vars": x_cold, "u_vars": u_cold, "v_vars": v_cold},
        config,
    )

    # Warm solve
    prob_warm, x_warm, u_warm, v_warm = _setup_lp(df1, df2, costs, 10000)
    pairs = _greedy_prealign(df1, df2)
    _apply_warm_start(pairs, df1, df2, x_warm, u_warm, v_warm)
    prob_warm.solve(PULP_CBC_CMD(msg=False, warmStart=True))
    assert prob_warm.status == LpStatusOptimal
    warm_results = _extract_results(
        {"df1": df1, "df2": df2, "x_vars": x_warm, "u_vars": u_warm, "v_vars": v_warm},
        config,
    )

    # Same number of results
    assert len(cold_results) == len(warm_results)

    # Same statuses (sort by name_file1 for deterministic comparison)
    def sort_key(r):
        return (str(r.get("name_file1", "")), str(r.get("name_file2", "")))

    cold_sorted = sorted(cold_results, key=sort_key)
    warm_sorted = sorted(warm_results, key=sort_key)

    for c, w in zip(cold_sorted, warm_sorted):
        assert c["status"] == w["status"]
        assert c["name_file1"] == w["name_file1"]
        assert c["name_file2"] == w["name_file2"]


if __name__ == "__main__":
    pytest.main()
