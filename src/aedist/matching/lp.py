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

import math
import re

import pandas as pd
from pulp import (
    PULP_CBC_CMD,
    LpMinimize,
    LpProblem,
    LpStatusOptimal,
    LpVariable,
    lpSum,
)
from rapidfuzz import fuzz

from aedist.matching.result_row import build_result_row

# ---------------------------------------------------------------------------
# Default MILP parameters for record reconciliation
# ---------------------------------------------------------------------------

# Penalty for pairings where fuzzy similarity is below threshold
DEFAULT_MISMATCH_PENALTY: float = 1000
# Minimum fuzzy similarity score (0-100) to consider a potential match
DEFAULT_SIMILARITY_THRESHOLD: int = 90
# Capacity difference tolerance for fuzzy matches
DEFAULT_CAPACITY_TOLERANCE: float = 0
# Penalty for leaving a record unmatched (should exceed mismatch_penalty)
DEFAULT_DUMMY_COST: float = 10000
# Weight for capacity difference term in cost calculation
DEFAULT_CAPACITY_WEIGHT: float = 0.001


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
            results.append(build_result_row(None, row, "Only in file2"))
        return pd.DataFrame(results)
    if df2.empty:
        for _, row in df1.iterrows():
            results.append(build_result_row(row, None, "Only in file1"))
        return pd.DataFrame(results)
    return None


def _extract_digit_tokens(name: str) -> frozenset[str]:
    """Return the set of standalone digit tokens in a name_clean string."""
    return frozenset(tok for tok in name.split() if tok.isdigit())


def _strip_digit_tokens(name: str) -> str:
    """Return the name with standalone digit tokens removed."""
    return " ".join(tok for tok in name.split() if not tok.isdigit())


# Stripped-name near-identity cutoff for the digit-asymmetric veto branch.
# Fixed (not the pair similarity_threshold): tool-mode matching at threshold 70
# must not widen the veto to word-level different bases ("an khanh" vs "an khe").
STRIPPED_NAME_VETO_THRESHOLD: int = 90


def ambiguous_phase_bases(names: list[str]) -> frozenset[str]:
    """Stripped base names carrying >= 2 distinct digit-token variants.

    "ca na 2" and "ca na 3" make base "ca na" ambiguous: a bare base-name
    emission cannot be attributed to either sibling. A base with a single
    digit variant ("lng quang ninh 1" alone) is unambiguous and stays
    matchable to its bare base name.
    """
    variants: dict[str, set[frozenset[str]]] = {}
    for name in names:
        d = _extract_digit_tokens(name)
        if d:
            variants.setdefault(_strip_digit_tokens(name), set()).add(d)
    return frozenset(base for base, ds in variants.items() if len(ds) >= 2)


def digit_veto(
    name1: str, name2: str, ambiguous_bases: frozenset[str] = frozenset()
) -> bool:
    """True when the unit-number veto blocks this pair of name_clean strings.

    Two branches (ticket 0544 symmetric case, ticket 0551 asymmetric case):
      - Both names carry digit tokens and the sets differ ("vung ang 1" vs
        "vung ang 2"): cross-unit pairs must not match.
      - Exactly one side carries digit tokens, the digit-stripped names are
        near-identical, and the stripped base is ambiguous (>= 2 phase
        siblings in the corpus — see ambiguous_phase_bases): a base name
        must not be arbitrarily absorbed by one of several siblings
        ("ca na" vs "ca na 2" when "ca na 3" also exists). With a single
        sibling the base name plausibly denotes that plant and may match.
        Digit-free pairs ("long son" vs "long son chemical") are not vetoed.
    """
    digits1 = _extract_digit_tokens(name1)
    digits2 = _extract_digit_tokens(name2)
    if digits1 and digits2:
        return digits1 != digits2
    if digits1 or digits2:
        stripped1 = _strip_digit_tokens(name1)
        stripped2 = _strip_digit_tokens(name2)
        base = stripped1 if digits1 else stripped2
        return (
            base in ambiguous_bases
            and fuzz.ratio(stripped1, stripped2) >= STRIPPED_NAME_VETO_THRESHOLD
        )
    return False


# Matches "BASE N & M", "BASE N&M", or "BASE N va M" where N and M are digits.
# Capture groups: (1) base prefix, (2) first digit, (3) second digit.
_COMBINED_UNITS_RE = re.compile(
    r"^(.*\S)\s*(\d+)\s*(?:&|va)\s*(\d+)\s*$",
    re.IGNORECASE,
)


def expand_combined_units(df: pd.DataFrame) -> pd.DataFrame:
    """Split combined-unit rows like 'nhon trach 3 & 4' into two single-unit rows.

    A model sometimes lists two reference units as one combined row, e.g.
    "Nhơn Trạch 3 & 4" or "Cà Mau 1 và 2".  After name cleaning these appear
    as ``name_clean`` values matching "BASE N & M" or "BASE N va M".  The
    unit-number veto in ``_compute_costs`` then prevents either unit number from
    matching the corresponding reference row, producing a false SYSTEM_ONLY.

    This function pre-expands each such row into two rows—one for each unit—so
    the LP receives the correct one-to-one candidates.  Only the model side
    (df2 / sys_df) should be expanded; the reference is not touched.

    Capacity: each split row inherits the full combined capacity.  The LP cost
    function uses ``capacity_weight=0.001``, so a combined-capacity split row
    matches its single-unit reference counterpart even with a capacity
    discrepancy; no downstream coverage metric sums matched capacity at this
    stage.

    Rows that do not match the combined pattern are returned unchanged.
    """
    if df.empty:
        return df

    expanded_rows: list[dict] = []
    for _, row in df.iterrows():
        name_clean = str(row.get("name_clean", ""))
        m = _COMBINED_UNITS_RE.match(name_clean)
        if m:
            base, n1, n2 = m.group(1).rstrip(), m.group(2), m.group(3)
            for n in (n1, n2):
                new_row = row.to_dict()
                new_row["name_clean"] = f"{base} {n}"
                expanded_rows.append(new_row)
        else:
            expanded_rows.append(row.to_dict())

    return pd.DataFrame(expanded_rows).reset_index(drop=True)


def _compute_costs(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    similarity_threshold: int,
    mismatch_penalty: float,
    capacity_weight: float,
    dummy_cost: float = DEFAULT_DUMMY_COST,
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

    Unit-number veto (see digit_veto): if both names carry digit tokens and the sets differ
    ("1" vs "2"), or exactly one side carries digits and the digit-stripped names are
    near-identical ("ca na" vs "ca na 2"), the cost is set to 2*dummy_cost+1, making it
    cheaper for the LP to leave both records unmatched than to accept a cross-phase
    false positive.

    Args:
        df1 (pd.DataFrame): First DataFrame with plant records.
        df2 (pd.DataFrame): Second DataFrame with plant records.
        similarity_threshold (int): Threshold for fuzzy matching.
        mismatch_penalty (float): Penalty applied when fuzzy matching fails.
        capacity_weight (float): Weight coefficient for the capacity difference component.
        dummy_cost (float): Cost for leaving a record unmatched (used to calibrate veto cost).

    Returns:
        dict[tuple[int, int], float]: A mapping from (i, j) indices to computed matching cost.
    """
    veto_cost = 2 * dummy_cost + 1
    ambiguous = ambiguous_phase_bases(
        [str(n) for n in df1["name_clean"]] + [str(n) for n in df2["name_clean"]]
    )
    costs: dict[tuple[int, int], float] = {}
    for i in df1.index:
        for j in df2.index:
            name1 = str(df1.loc[i, "name_clean"])
            name2 = str(df2.loc[j, "name_clean"])

            # Unit-number veto: different unit numbers must not match, and a
            # base name must not match one of several phase siblings (digit_veto).
            if digit_veto(name1, name2, ambiguous):
                costs[(i, j)] = veto_cost
                continue

            cap1 = df1.loc[i, "capacity_clean"]
            cap2 = df2.loc[j, "capacity_clean"]
            if cap1 is None or cap2 is None or math.isnan(cap1) or math.isnan(cap2):
                costs[(i, j)] = mismatch_penalty
                continue
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
        (i, j): LpVariable(f"x_{i}_{j}", cat="Binary") for i in indices1 for j in indices2
    }
    u_vars: dict[int, LpVariable] = {i: LpVariable(f"u_{i}", cat="Binary") for i in indices1}
    v_vars: dict[int, LpVariable] = {j: LpVariable(f"v_{j}", cat="Binary") for j in indices2}

    # Objective:
    #   minimize ∑₍ᵢ,j₎ [cost(i, j) * x_vars[(i, j)]] + dummy_cost * (∑ᵢ u_vars[i] + ∑ⱼ v_vars[j])
    prob += lpSum(
        costs[(i, j)] * x_vars[(i, j)] for i in indices1 for j in indices2
    ) + dummy_cost * (lpSum(u_vars[i] for i in indices1) + lpSum(v_vars[j] for j in indices2))

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
    sim_thresh: int = config["similarity_threshold"]  # type: ignore[assignment]
    cap_tol: float = float(config["capacity_tolerance"])

    results: list[dict[str, object]] = []
    indices1: list[int] = list(df1.index)
    indices2: list[int] = list(df2.index)
    matched_pairs: list[tuple[int, int]] = [
        (i, j) for i in indices1 for j in indices2 if x_vars[(i, j)].varValue >= 0.5
    ]
    unmatched_df1: list[int] = [i for i in indices1 if u_vars[i].varValue >= 0.5]
    unmatched_df2: list[int] = [j for j in indices2 if v_vars[j].varValue >= 0.5]

    for i, j in matched_pairs:
        cap1: float = df1.loc[i, "capacity_clean"]
        cap2: float = df2.loc[j, "capacity_clean"]
        diff: float = (cap1 - cap2) if (cap1 is not None and cap2 is not None) else 0.0
        name1 = str(df1.loc[i, "name_clean"])
        name2 = str(df2.loc[j, "name_clean"])
        if name1 == name2:
            status = "Matched"
            score: float = 100
        else:
            similarity = fuzz.partial_ratio(name1, name2)
            score = similarity
            if similarity >= sim_thresh:
                status = "Matched (Fuzzy)" if abs(diff) <= cap_tol else "Matched (Fuzzy) (Diff)"
            else:
                status = "Mismatched"
        results.append(build_result_row(df1.loc[i], df2.loc[j], status, similarity_score=score))

    results.extend(build_result_row(df1.loc[i], None, "Only in file1") for i in unmatched_df1)
    results.extend(build_result_row(None, df2.loc[j], "Only in file2") for j in unmatched_df2)

    return results


def _greedy_prealign(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    costs: dict[tuple[int, int], float],
    dummy_cost: float,
) -> dict[tuple, float]:
    """Compute a greedy pre-alignment for warm-starting CBC.

    For each pair (i, j), sorted by ascending cost, greedily assign matches
    (each i and j used at most once).  Pairs with cost >= dummy_cost are
    skipped (cheaper to leave unmatched).

    Returns a dict mapping variable keys to initial values (0 or 1):
      ("x", i, j) -> 0 or 1
      ("u", i)    -> 0 or 1
      ("v", j)    -> 0 or 1
    """
    indices1 = list(df1.index)
    indices2 = list(df2.index)

    # Sort candidate pairs by cost (cheapest first)
    pairs = sorted(costs.keys(), key=lambda k: costs[k])

    matched_i: set[int] = set()
    matched_j: set[int] = set()
    solution: dict[tuple, float] = {}

    for i, j in pairs:
        if costs[(i, j)] >= dummy_cost:
            break  # All remaining pairs are too expensive
        if i not in matched_i and j not in matched_j:
            solution[("x", i, j)] = 1.0
            matched_i.add(i)
            matched_j.add(j)

    # Set unmatched flags
    for i in indices1:
        solution[("u", i)] = 0.0 if i in matched_i else 1.0
    for j in indices2:
        solution[("v", j)] = 0.0 if j in matched_j else 1.0

    return solution


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
    mismatch_penalty: float = kwargs.get("mismatch_penalty", DEFAULT_MISMATCH_PENALTY)
    similarity_threshold: int = kwargs.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD)
    capacity_tolerance: float = kwargs.get("capacity_tolerance", DEFAULT_CAPACITY_TOLERANCE)
    dummy_cost: float = kwargs.get("dummy_cost", DEFAULT_DUMMY_COST)
    capacity_weight: float = kwargs.get("capacity_weight", DEFAULT_CAPACITY_WEIGHT)

    req_cols = {"name", "name_clean", "capacity_clean"}
    if not req_cols.issubset(df1.columns):
        raise ValueError("df1 must contain columns: 'name', 'name_clean', 'capacity_clean'.")
    if not req_cols.issubset(df2.columns):
        raise ValueError("df2 must contain columns: 'name', 'name_clean', 'capacity_clean'.")

    # Expand combined-unit system rows (e.g. "nhon trach 3 & 4" → two rows)
    # before handing off to the LP so the one-to-one assignment can match each
    # unit against its own reference row.  Only df2 (system side) is expanded;
    # the reference (df1) is never modified — see expand_combined_units docstring.
    df2 = expand_combined_units(df2)

    empty_result = _handle_empty(df1, df2)
    if empty_result is not None:
        return empty_result

    costs = _compute_costs(
        df1, df2, similarity_threshold, mismatch_penalty, capacity_weight, dummy_cost
    )
    prob, x_vars, u_vars, v_vars = _setup_lp(df1, df2, costs, dummy_cost)

    # Warm start: set initial values from greedy pre-alignment
    greedy = _greedy_prealign(df1, df2, costs, dummy_cost)
    for (i, j), var in x_vars.items():
        var.setInitialValue(greedy.get(("x", i, j), 0.0))
    for i, var in u_vars.items():
        var.setInitialValue(greedy.get(("u", i), 1.0))
    for j, var in v_vars.items():
        var.setInitialValue(greedy.get(("v", j), 1.0))

    prob.solve(PULP_CBC_CMD(msg=False, warmStart=True))
    if prob.status != LpStatusOptimal:
        raise RuntimeError("Assignment MILP did not solve to optimality.")

    context: dict[str, object] = {
        "df1": df1,
        "df2": df2,
        "x_vars": x_vars,
        "u_vars": u_vars,
        "v_vars": v_vars,
    }
    config: dict[str, int | float] = {
        "similarity_threshold": similarity_threshold,
        "capacity_tolerance": capacity_tolerance,
    }
    results = _extract_results(context, config)
    return pd.DataFrame(results)
