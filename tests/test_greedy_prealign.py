"""Tests for _greedy_prealign warm-start logic in the LP matching module."""

import pandas as pd
import pytest

from aedist.matching.lp import _compute_costs, _greedy_prealign, reconcile


def _make_df(rows):
    """Build a small DataFrame with the required columns."""
    return pd.DataFrame(rows, columns=["name", "name_clean", "capacity_clean"])


# ---------------------------------------------------------------------------
# 1. Feasibility: every i matched or unmatched, every j matched or unmatched,
#    no double assignments
# ---------------------------------------------------------------------------

class TestFeasibility:
    """The greedy solution must be a valid assignment."""

    def test_each_i_covered_exactly_once(self):
        df1 = _make_df([
            ("A", "a", 100),
            ("B", "b", 200),
            ("C", "c", 300),
        ])
        df2 = _make_df([
            ("A", "a", 100),
            ("D", "d", 999),
        ])
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=10000)

        for i in df1.index:
            matched = sum(
                sol.get(("x", i, j), 0.0) for j in df2.index
            )
            unmatched = sol.get(("u", i), 0.0)
            assert matched + unmatched == 1.0, f"Row i={i} not covered exactly once"

    def test_each_j_covered_exactly_once(self):
        df1 = _make_df([
            ("A", "a", 100),
            ("B", "b", 200),
            ("C", "c", 300),
        ])
        df2 = _make_df([
            ("A", "a", 100),
            ("D", "d", 999),
        ])
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=10000)

        for j in df2.index:
            matched = sum(
                sol.get(("x", i, j), 0.0) for i in df1.index
            )
            unmatched = sol.get(("v", j), 0.0)
            assert matched + unmatched == 1.0, f"Col j={j} not covered exactly once"

    def test_no_double_assignment(self):
        """No i appears in two x entries, no j appears in two x entries."""
        df1 = _make_df([
            ("A", "a", 100),
            ("B", "b", 200),
        ])
        df2 = _make_df([
            ("A", "a", 100),
            ("B", "b", 200),
        ])
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=10000)

        # Collect assigned pairs (keys are ("x", i, j) or ("u", i) or ("v", j))
        pairs = [key[1:] for key in sol if key[0] == "x" and sol[key] == 1.0]
        assigned_i = [p[0] for p in pairs]
        assigned_j = [p[1] for p in pairs]
        assert len(assigned_i) == len(set(assigned_i)), "Duplicate i assignment"
        assert len(assigned_j) == len(set(assigned_j)), "Duplicate j assignment"


# ---------------------------------------------------------------------------
# 2. Pairs with cost >= dummy_cost are left unmatched
# ---------------------------------------------------------------------------

class TestDummyCostThreshold:

    def test_expensive_pairs_left_unmatched(self):
        """When all pair costs exceed dummy_cost, nothing is matched."""
        df1 = _make_df([("X", "x", 0)])
        df2 = _make_df([("Y", "y", 999)])
        # mismatch_penalty=1000, capacity_weight large enough to push cost high
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        # Set a very low dummy_cost so that every real pair is too expensive
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=5)

        assert sol.get(("x", 0, 0), 0.0) == 0.0
        assert sol[("u", 0)] == 1.0
        assert sol[("v", 0)] == 1.0

    def test_cheap_pair_matched_expensive_pair_not(self):
        """Only the pair below dummy_cost is matched."""
        df1 = _make_df([
            ("A", "a", 100),
            ("Z", "z", 0),
        ])
        df2 = _make_df([
            ("A", "a", 100),
            ("W", "w", 9999),
        ])
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=500)

        # A-A should be matched (cost = 0 + small capacity term)
        assert sol.get(("x", 0, 0), 0.0) == 1.0
        # Z-W should NOT be matched (cost = 1000 + capacity term >> 500)
        assert sol.get(("x", 1, 1), 0.0) == 0.0
        assert sol[("u", 1)] == 1.0
        assert sol[("v", 1)] == 1.0


# ---------------------------------------------------------------------------
# 3. Simple 2x2 cost matrix where the optimal is obvious
# ---------------------------------------------------------------------------

class TestSimple2x2:

    def test_diagonal_assignment(self):
        """With identical names on the diagonal, greedy picks (0,0) and (1,1)."""
        df1 = _make_df([
            ("Alpha", "alpha", 50),
            ("Beta", "beta", 60),
        ])
        df2 = _make_df([
            ("Alpha", "alpha", 50),
            ("Beta", "beta", 60),
        ])
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=10000)

        assert sol.get(("x", 0, 0), 0.0) == 1.0
        assert sol.get(("x", 1, 1), 0.0) == 1.0
        assert sol[("u", 0)] == 0.0
        assert sol[("u", 1)] == 0.0
        assert sol[("v", 0)] == 0.0
        assert sol[("v", 1)] == 0.0

    def test_swapped_order(self):
        """Names appear in reversed order across DFs; greedy still pairs correctly."""
        df1 = _make_df([
            ("Alpha", "alpha", 50),
            ("Beta", "beta", 60),
        ])
        df2 = _make_df([
            ("Beta", "beta", 60),
            ("Alpha", "alpha", 50),
        ])
        costs = _compute_costs(df1, df2, 90, 1000, 0.001)
        sol = _greedy_prealign(df1, df2, costs, dummy_cost=10000)

        # Alpha(0) <-> Alpha(1), Beta(1) <-> Beta(0)
        assert sol.get(("x", 0, 1), 0.0) == 1.0
        assert sol.get(("x", 1, 0), 0.0) == 1.0


# ---------------------------------------------------------------------------
# 4. Warm-started solve produces identical results to cold solve
# ---------------------------------------------------------------------------

class TestWarmVsCold:

    @staticmethod
    def _reconcile_cold(df1, df2, **kwargs):
        """Run reconcile without warm start by passing dummy_cost so high
        that _greedy_prealign assigns nothing, effectively a cold start."""
        from aedist.matching.lp import (
            _compute_costs,
            _extract_results,
            _setup_lp,
        )
        from pulp import PULP_CBC_CMD, LpStatusOptimal

        mismatch_penalty = kwargs.get("mismatch_penalty", 1000)
        similarity_threshold = kwargs.get("similarity_threshold", 90)
        capacity_tolerance = kwargs.get("capacity_tolerance", 0)
        dummy_cost = kwargs.get("dummy_cost", 10000)
        capacity_weight = kwargs.get("capacity_weight", 0.001)

        costs = _compute_costs(df1, df2, similarity_threshold, mismatch_penalty, capacity_weight)
        prob, x_vars, u_vars, v_vars = _setup_lp(df1, df2, costs, dummy_cost)

        # Solve WITHOUT warm start
        prob.solve(PULP_CBC_CMD(msg=False, warmStart=False))
        assert prob.status == LpStatusOptimal

        context = {"df1": df1, "df2": df2, "x_vars": x_vars, "u_vars": u_vars, "v_vars": v_vars}
        config = {"similarity_threshold": similarity_threshold, "capacity_tolerance": capacity_tolerance}
        return pd.DataFrame(_extract_results(context, config))

    def _compare_results(self, df1, df2, **kwargs):
        warm = reconcile(df1, df2, **kwargs)
        cold = self._reconcile_cold(df1, df2, **kwargs)

        # Sort both by all columns for fully deterministic comparison
        sort_cols = ["status", "name_file1", "name_file2", "capacity_file1", "capacity_file2"]
        warm_sorted = warm.sort_values(sort_cols, na_position="last").reset_index(drop=True)
        cold_sorted = cold.sort_values(sort_cols, na_position="last").reset_index(drop=True)

        pd.testing.assert_frame_equal(warm_sorted, cold_sorted)

    def test_identical_result_exact_matches(self):
        df1 = _make_df([
            ("Plant A", "plant a", 100),
            ("Plant B", "plant b", 200),
        ])
        df2 = _make_df([
            ("Plant A", "plant a", 100),
            ("Plant B", "plant b", 200),
        ])
        self._compare_results(df1, df2)

    def test_identical_result_mixed(self):
        """Mix of exact, fuzzy, and unmatched records."""
        df1 = _make_df([
            ("Plant A", "plant a", 100),
            ("Plant B", "plant b", 200),
            ("Orphan X", "orphan x", 50),
        ])
        df2 = _make_df([
            ("Plant A Inc", "plant a inc", 105),
            ("Plant B", "plant b", 200),
            ("Orphan Y", "orphan y", 70),
        ])
        self._compare_results(df1, df2, capacity_tolerance=10)

    def test_identical_result_all_unmatched(self):
        """All names are completely different; both solvers should produce
        the same set of statuses (though pairing of mismatched records
        may differ when costs are tied)."""
        df1 = _make_df([
            ("Foo", "foo", 10),
            ("Bar", "bar", 20),
        ])
        df2 = _make_df([
            ("Qux", "qux", 999),
            ("Baz", "baz", 888),
        ])
        warm = reconcile(df1, df2)
        cold = self._reconcile_cold(df1, df2)

        # Both should have the same status distribution
        warm_statuses = sorted(warm["status"].tolist())
        cold_statuses = sorted(cold["status"].tolist())
        assert warm_statuses == cold_statuses

        # Both should match the same set of df1 names and df2 names
        assert sorted(warm["name_file1"].dropna().tolist()) == sorted(cold["name_file1"].dropna().tolist())
        assert sorted(warm["name_file2"].dropna().tolist()) == sorted(cold["name_file2"].dropna().tolist())
