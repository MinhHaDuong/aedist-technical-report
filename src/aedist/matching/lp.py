from __future__ import annotations

#
# Minh Ha-Duong, CNRS (2025)
# CC-BY-SA

"""
Module matching_lp.py

This module reconciles power plant records by solving a Mixed-Integer Linear Programming (MILP)
assignment problem. The reconciliation uses fuzzy matching on plant names along with capacity closeness
to determine the optimal pairing of records between two DataFrames.

The MILP formulation is as follows:

Let:
  - X₍ᵢⱼ₎ be a binary variable that is 1 if record i from df1 is matched with record j from df2, 0 otherwise.
  - uᵢ be a binary variable that is 1 if record i from df1 is left unmatched.
  - vⱼ be a binary variable that is 1 if record j from df2 is left unmatched.

The goal is to minimize the total cost:
    
  Minimize: ∑₍ᵢ,j₎ [cost(i, j) · X₍ᵢⱼ₎] + dummy_cost · (∑ᵢ uᵢ + ∑ⱼ vⱼ)
  
Subject to the assignment constraints:
  For each record i in df1:
    ∑ⱼ X₍ᵢⱼ₎ + uᵢ = 1

  For each record j in df2:
    ∑ᵢ X₍ᵢⱼ₎ + vⱼ = 1

The cost for pairing record i and record j is computed as:

  cost(i, j) = base_cost(i, j) + capacity_weight · |capacity_df1 - capacity_df2|

Where the base_cost is defined as:
  - 0 if the cleaned names match exactly;
  - 1 if the fuzzy matching score (using fuzz.partial_ratio) meets the similarity_threshold;
  - mismatch_penalty otherwise.

Adjustable parameters:
  - mismatch_penalty: Penalty when the fuzzy similarity does not meet the threshold.
  - similarity_threshold: Minimum score for fuzzy matching.
  - capacity_tolerance: Tolerance for capacity differences in fuzzy matches.
  - dummy_cost: Penalty cost for leaving a record unmatched.
  - capacity_weight: Weight factor for the capacity difference term.
"""

import pandas as pd
from pulp import (
    LpProblem,
    LpVariable,
    lpSum,
    LpMinimize,
    PULP_CBC_CMD,
    LpStatusOptimal,
)
from rapidfuzz import fuzz


def _safe_get(row: pd.Series | None, key: str) -> object | None:
    """
    Safely retrieve the value for a key from a pandas Series.

    Args:
        row (pd.Series | None): A row from a DataFrame or None.
        key (str): The key (column name) to retrieve.

    Returns:
        The value corresponding to the given key if row exists; otherwise, None.
    """
    if row is None:
        return None
    return row[key]


def _build_result_row(
    df1_row: pd.Series | None,
    df2_row: pd.Series | None,
    capacity_diff: float | None,
    status: str,
) -> dict[str, object | None]:
    """
    Construct and return a result dictionary summarizing a match or an unmatched record.

    Args:
        df1_row (pd.Series | None): Row from df1, or None if unmatched.
        df2_row (pd.Series | None): Row from df2, or None if unmatched.
        capacity_diff (float | None): Difference in capacity (df1 minus df2) if available.
        status (str): Description of the matching status.

    Returns:
        dict[str, object | None]: A dictionary with details on the match and associated metadata.
        
    Note:
        The keys in the returned dictionary still use the "file1"/"file2" naming to maintain test compatibility.
    """
    return {
        "name_file1": _safe_get(df1_row, "name"),
        "name_clean_file1": _safe_get(df1_row, "name_clean"),
        "capacity_file1": _safe_get(df1_row, "capacity_clean"),
        "name_file2": _safe_get(df2_row, "name"),
        "name_clean_file2": _safe_get(df2_row, "name_clean"),
        "capacity_file2": _safe_get(df2_row, "capacity_clean"),
        "capacity_difference": capacity_diff,
        "status": status,
    }


def _handle_empty(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame | None:
    """
    Handle cases where one or both input DataFrames are empty.

    If one of the DataFrames is empty, each record in the non-empty DataFrame is marked as unmatched.
    If both are empty, an empty DataFrame is returned.

    Args:
        df1 (pd.DataFrame): First DataFrame.
        df2 (pd.DataFrame): Second DataFrame.

    Returns:
        pd.DataFrame | None: A DataFrame containing unmatched entries or None if both DataFrames contain data.
    """
    results: list[dict[str, object | None]] = []
    if df1.empty and df2.empty:
        return pd.DataFrame(results)
    if df1.empty:
        for _, row in df2.iterrows():
            results.append(_build_result_row(None, row, None, "Only in file2"))
        return pd.DataFrame(results)
    if df2.empty:
        for _, row in df1.iterrows():
            results.append(_build_result_row(row, None, None, "Only in file1"))
        return pd.DataFrame(results)
    return None


def _compute_costs(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    similarity_threshold: int,
    mismatch_penalty: float,
    capacity_weight: float,
) -> dict[tuple[int, int], float]:
    """
    Compute the matching cost for each potential pairing between records of df1 and df2.

    The cost for pairing record i (from df1) with record j (from df2) is given by:

      cost(i, j) = base_cost(i, j) + capacity_weight * |capacity_df1 - capacity_df2|

    where:
      - base_cost(i, j) is:
          0 if the cleaned names are exactly equal;
          1 if the fuzzy similarity score (using fuzz.partial_ratio) meets or exceeds similarity_threshold;
          mismatch_penalty otherwise.

    Args:
        df1 (pd.DataFrame): First DataFrame with plant records.
        df2 (pd.DataFrame): Second DataFrame with plant records.
        similarity_threshold (int): Threshold for fuzzy matching.
        mismatch_penalty (float): Penalty applied when fuzzy matching fails.
        capacity_weight (float): Weight coefficient for the capacity difference component.

    Returns:
        dict[tuple[int, int], float]: A mapping from (i, j) indices to computed matching cost.
    """
    costs: dict[tuple[int, int], float] = {}
    for i in df1.index:
        for j in df2.index:
            name1 = str(df1.loc[i, "name_clean"])
            name2 = str(df2.loc[j, "name_clean"])
            cap1 = df1.loc[i, "capacity_clean"]
            cap2 = df2.loc[j, "capacity_clean"]
            diff = abs(cap1 - cap2)
            if name1 == name2:
                base_cost = 0
            else:
                similarity = fuzz.partial_ratio(name1, name2)
                base_cost = 1 if similarity >= similarity_threshold else mismatch_penalty
            costs[(i, j)] = base_cost + capacity_weight * diff
    return costs


def _setup_lp(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    costs: dict[tuple[int, int], float],
    dummy_cost: float,
) -> tuple[
    LpProblem,
    dict[tuple[int, int], LpVariable],
    dict[int, LpVariable],
    dict[int, LpVariable],
]:
    """
    Set up the MILP assignment model and associated decision variables.

    Decision Variables:
      - x_vars[(i, j)]: 1 if record i from df1 is matched with record j from df2, 0 otherwise.
      - u_vars[i]: 1 if record i from df1 is left unmatched.
      - v_vars[j]: 1 if record j from df2 is left unmatched.

    Objective Function:
      Minimize: ∑₍ᵢ,j₎ [cost(i, j) * x_vars[(i,j)]] + dummy_cost * (∑ᵢ u_vars[i] + ∑ⱼ v_vars[j])

    Subject to:
      For each record i in df1:
        ∑ⱼ x_vars[(i, j)] + u_vars[i] = 1

      For each record j in df2:
        ∑ᵢ x_vars[(i, j)] + v_vars[j] = 1

    This formulation guarantees that each record in either DataFrame is either matched with one record in the other DataFrame
    or is marked as unmatched.

    Args:
        df1 (pd.DataFrame): DataFrame containing records from df1.
        df2 (pd.DataFrame): DataFrame containing records from df2.
        costs (dict[tuple[int, int], float]): Precomputed cost for matching each pair (i, j).
        dummy_cost (float): Cost for leaving a record unmatched.

    Returns:
        tuple: A tuple containing:
            - LpProblem: The MILP problem instance.
            - x_vars: Dictionary of binary decision variables for matches.
            - u_vars: Dictionary of binary decision variables for df1 unmatched records.
            - v_vars: Dictionary of binary decision variables for df2 unmatched records.
    """
    prob = LpProblem("Assignment_Reconciliation", LpMinimize)
    indices1: list[int] = list(df1.index)
    indices2: list[int] = list(df2.index)
    x_vars: dict[tuple[int, int], LpVariable] = {
        (i, j): LpVariable(f"x_{i}_{j}", cat="Binary")
        for i in indices1 for j in indices2
    }
    u_vars: dict[int, LpVariable] = {i: LpVariable(f"u_{i}", cat="Binary") for i in indices1}
    v_vars: dict[int, LpVariable] = {j: LpVariable(f"v_{j}", cat="Binary") for j in indices2}

    # Objective:
    #   minimize ∑₍ᵢ,j₎ [cost(i, j) * x_vars[(i, j)]] + dummy_cost * (∑ᵢ u_vars[i] + ∑ⱼ v_vars[j])
    prob += (
        lpSum(costs[(i, j)] * x_vars[(i, j)] for i in indices1 for j in indices2)
        + dummy_cost * (lpSum(u_vars[i] for i in indices1) + lpSum(v_vars[j] for j in indices2))
    )

    # Assignment constraints:
    # Each record from df1 must be either matched (across all j) or marked as unmatched.
    for i in indices1:
        prob += lpSum(x_vars[(i, j)] for j in indices2) + u_vars[i] == 1, f"df1_assign_{i}"
    # Each record from df2 must be either matched (across all i) or marked as unmatched.
    for j in indices2:
        prob += lpSum(x_vars[(i, j)] for i in indices1) + v_vars[j] == 1, f"df2_assign_{j}"
    return prob, x_vars, u_vars, v_vars


def _extract_results(
    context: dict[str, object],
    config: dict[str, int | float],
) -> list[dict[str, object]]:
    """
    Extract matching decisions from the solved MILP and build a results list.

    The function reads the decision variables to determine which pairings were chosen.
    For each pairing (i, j):
      - If the cleaned names are identical, the status is "Matched".
      - Otherwise, a fuzzy similarity check is applied:
          * If the fuzzy similarity exceeds the threshold and the capacity difference is within tolerance,
            the status is "Matched (Fuzzy)".
          * If the capacity difference exceeds the tolerance, the status becomes "Matched (Fuzzy) (Diff)".
      - Unmatched records are labeled "Only in file1" or "Only in file2" accordingly.

    Args:
        context (dict[str, object]): Dictionary containing:
            - 'df1': The first DataFrame.
            - 'df2': The second DataFrame.
            - 'x_vars': Dictionary of matching decision variables.
            - 'u_vars': Dictionary of unmatched flags for df1.
            - 'v_vars': Dictionary of unmatched flags for df2.
        config (dict[str, int | float]): Dictionary with configuration parameters:
            - 'similarity_threshold': Minimum fuzzy similarity score.
            - 'capacity_tolerance': Allowed tolerance for capacity difference.

    Returns:
        list[dict[str, object]]: A list of dictionaries, each summarizing a match or unmatched entry.
    """
    df1 = context["df1"]  # type: pd.DataFrame
    df2 = context["df2"]  # type: pd.DataFrame
    x_vars = context["x_vars"]  # type: dict[tuple[int, int], LpVariable]
    u_vars = context["u_vars"]  # type: dict[int, LpVariable]
    v_vars = context["v_vars"]  # type: dict[int, LpVariable]
    sim_thresh: int = config["similarity_threshold"]  # type: ignore
    cap_tol: float = float(config["capacity_tolerance"])
    
    results: list[dict[str, object]] = []
    indices1: list[int] = list(df1.index)
    indices2: list[int] = list(df2.index)
    matched_pairs: list[tuple[int, int]] = []
    for i in indices1:
        for j in indices2:
            # Here we expect binary values (0 or 1); if near-binary values appear, consider rounding.
            if x_vars[(i, j)].varValue == 1:
                matched_pairs.append((i, j))
    unmatched_df1: list[int] = [i for i in indices1 if u_vars[i].varValue == 1]
    unmatched_df2: list[int] = [j for j in indices2 if v_vars[j].varValue == 1]

    for i, j in matched_pairs:
        cap1: float = df1.loc[i, "capacity_clean"]
        cap2: float = df2.loc[j, "capacity_clean"]
        diff: float = cap1 - cap2
        name1 = str(df1.loc[i, "name_clean"])
        name2 = str(df2.loc[j, "name_clean"])
        if name1 == name2:
            status = "Matched"
        else:
            similarity = fuzz.partial_ratio(name1, name2)
            if similarity >= sim_thresh:
                status = "Matched (Fuzzy)" if abs(diff) <= cap_tol else "Matched (Fuzzy) (Diff)"
            else:
                status = "Mismatched"
        results.append(_build_result_row(df1.loc[i], df2.loc[j], diff, status))

    for i in unmatched_df1:
        results.append(_build_result_row(df1.loc[i], None, None, "Only in file1"))

    for j in unmatched_df2:
        results.append(_build_result_row(None, df2.loc[j], None, "Only in file2"))

    return results


def reconcile(df1: pd.DataFrame, df2: pd.DataFrame, **kwargs: object) -> pd.DataFrame:
    """
    Reconcile power plant records between two DataFrames using a MILP assignment approach.

    Each DataFrame must include the columns: 'name', 'name_clean', and 'capacity_clean'.

    Reconciliation Details:
      - Fuzzy string matching is applied on the 'name_clean' column.
      - The cost function incorporates both a base cost (derived from fuzzy name comparison)
        and a penalty proportional to the capacity difference.
      - The MILP formulation introduces binary decision variables to enforce a one-to-one matching
        or declare a record as unmatched.

    MILP Formulation:
      Decision Variables:
        x_vars[(i,j)]: 1 if record i (from df1) is matched with record j (from df2).
        u_vars[i]: 1 if record i (from df1) remains unmatched.
        v_vars[j]: 1 if record j (from df2) remains unmatched.
      
      Objective Function:
        Minimize ∑₍ᵢ,j₎ [cost(i, j) * x_vars[(i,j)]] + dummy_cost * (∑ᵢ u_vars[i] + ∑ⱼ v_vars[j])
      
      Constraints:
        For every record i in df1:
          ∑ⱼ x_vars[(i,j)] + u_vars[i] = 1
        For every record j in df2:
          ∑ᵢ x_vars[(i,j)] + v_vars[j] = 1

      Where:
        cost(i, j) = base_cost(i, j) + capacity_weight · |capacity_df1 - capacity_df2|
        and base_cost(i, j) is:
          0 if names match exactly;
          1 if fuzzy similarity (via fuzz.partial_ratio) ≥ similarity_threshold;
          mismatch_penalty otherwise.

    Keyword Arguments:
      - mismatch_penalty (float): Penalty for non-fuzzy matches (default 1000).
      - similarity_threshold (int): Minimum fuzzy similarity score for potential matches (default 90).
      - capacity_tolerance (float): Capacity difference tolerance for fuzzy matches (default 0).
      - dummy_cost (float): Penalty for leaving a record unmatched (default 10000).
      - capacity_weight (float): Weight for capacity difference in cost calculation (default 1e-3).

    Returns:
        pd.DataFrame: A DataFrame summarizing the reconciliation results, including match status,
                      capacity differences, and the relevant record details.

    Raises:
        ValueError: If either input DataFrame lacks the required columns.
        RuntimeError: If the MILP does not solve to optimality.
    """
    mismatch_penalty: float = kwargs.get("mismatch_penalty", 1000)
    similarity_threshold: int = kwargs.get("similarity_threshold", 90)
    capacity_tolerance: float = kwargs.get("capacity_tolerance", 0)
    dummy_cost: float = kwargs.get("dummy_cost", 10000)
    capacity_weight: float = kwargs.get("capacity_weight", 0.001)

    req_cols = {"name", "name_clean", "capacity_clean"}
    if not req_cols.issubset(df1.columns):
        raise ValueError("df1 must contain columns: 'name', 'name_clean', 'capacity_clean'.")
    if not req_cols.issubset(df2.columns):
        raise ValueError("df2 must contain columns: 'name', 'name_clean', 'capacity_clean'.")

    empty_result = _handle_empty(df1, df2)
    if empty_result is not None:
        return empty_result

    costs = _compute_costs(df1, df2, similarity_threshold, mismatch_penalty, capacity_weight)
    prob, x_vars, u_vars, v_vars = _setup_lp(df1, df2, costs, dummy_cost)
    prob.solve(PULP_CBC_CMD(msg=False))
    if prob.status != LpStatusOptimal:
        raise RuntimeError("Assignment MILP did not solve to optimality.")

    context: dict[str, object] = {
        "df1": df1,
        "df2": df2,
        "x_vars": x_vars,
        "u_vars": u_vars,
        "v_vars": v_vars,
    }
    config: dict[str, int | float] = {"similarity_threshold": similarity_threshold, "capacity_tolerance": capacity_tolerance}
    results = _extract_results(context, config)
    return pd.DataFrame(results)
