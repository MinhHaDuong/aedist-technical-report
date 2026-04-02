# matching_triphasic.py
#
# Minh Ha-Duong, CNRS (2025)
# CC-BY-SA

"""Module for reconciling power plant data using fuzzy and exact matching."""

from typing import Any
import pandas as pd
from rapidfuzz import fuzz, process


def build_reconciled_row(
    row1: pd.Series | None, row2: pd.Series | None, status: str
) -> dict[str, Any]:
    """
    Build a reconciliation dictionary (row) from given rows and a match status.

    Args:
        row1 (pd.Series | None): A row from file1 (or None).
        row2 (pd.Series | None): A row from file2 (or None).
        status (str): The reconciliation status (e.g., "Matched", "Only in file1").

    Returns:
        dict[str, Any]: Dictionary with keys:
            - name_file1, name_clean_file1, capacity_file1
            - name_file2, name_clean_file2, capacity_file2
            - capacity_difference (if applicable)
            - status
    """
    if row1 is not None:
        name_file1 = row1.get("name")
        name_clean_file1 = row1.get("name_clean")
        capacity_file1 = row1.get("capacity_clean")
    else:
        name_file1, name_clean_file1, capacity_file1 = None, None, None

    if row2 is not None:
        name_file2 = row2.get("name")
        name_clean_file2 = row2.get("name_clean")
        capacity_file2 = row2.get("capacity_clean")
    else:
        name_file2, name_clean_file2, capacity_file2 = None, None, None

    if row1 is not None and row2 is not None:
        try:
            capacity_difference = capacity_file1 - capacity_file2
        except Exception:
            capacity_difference = None
    else:
        capacity_difference = None

    return {
        "name_file1": name_file1,
        "name_clean_file1": name_clean_file1,
        "name_file2": name_file2,
        "name_clean_file2": name_clean_file2,
        "capacity_file1": capacity_file1,
        "capacity_file2": capacity_file2,
        "capacity_difference": capacity_difference,
        "status": status,
    }


def find_exact_match(
    row1: pd.Series, unmatched_group2: pd.DataFrame
) -> tuple[pd.Series | None, int | None]:
    """
    Find an exact match for `row1` within `unmatched_group2` by comparing both
    "name_clean" and "capacity_clean".

    Args:
        row1 (pd.Series): A row from group1 (file1).
        unmatched_group2 (pd.DataFrame): DataFrame with unmatched rows from file2.

    Returns:
        tuple[pd.Series | None, int | None]:
            - matched_row (pd.Series): The matching row from unmatched_group2.
            - matched_index (int): The index of the matched row.
            Returns (None, None) if no exact match is found.
    """
    # Assert required columns exist on row1 and unmatched_group2.
    assert (
        "name_clean" in row1 and "capacity_clean" in row1
    ), "row1 is missing required columns 'name_clean' and/or 'capacity_clean'."
    assert (
        "name_clean" in unmatched_group2.columns
        and "capacity_clean" in unmatched_group2.columns
    ), "unmatched_group2 is missing required columns 'name_clean' and/or 'capacity_clean'."

    exact_matches = unmatched_group2[
        (unmatched_group2["name_clean"] == row1["name_clean"])
        & (unmatched_group2["capacity_clean"] == row1["capacity_clean"])
    ]

    if not exact_matches.empty:
        matched_index = exact_matches.index[0]
        matched_row = unmatched_group2.loc[matched_index]
        return matched_row, matched_index

    return None, None


def find_fuzzy_match(
    row1: pd.Series, unmatched_group2: pd.DataFrame, similarity_threshold: int = 90
) -> tuple[pd.Series | None, int | None]:
    """
    Find the best fuzzy match for `row1` in `unmatched_group2` based on "name_clean"
    similarity. If the highest similarity score is below `similarity_threshold`,
    return (None, None).

    Args:
        row1 (pd.Series): A row from group1 (file1).
        unmatched_group2 (pd.DataFrame): DataFrame with unmatched rows from file2.
        similarity_threshold (int): The minimum acceptable similarity score (default 90).

    Returns:
        tuple[pd.Series | None, int | None]:
            - matched_row (pd.Series): The best fuzzy match from unmatched_group2.
            - matched_index (int): The index of that row.
            Returns (None, None) if no match meets the threshold.
    """
    # Assert required columns exist.
    assert "name_clean" in row1, "row1 is missing required column 'name_clean'."
    assert (
        "name_clean" in unmatched_group2.columns
    ), "unmatched_group2 is missing required column 'name_clean'."

    best_match = process.extractOne(
        row1["name_clean"],
        unmatched_group2["name_clean"],
        scorer=fuzz.partial_ratio,
    )

    if best_match:
        _, best_score, best_index = best_match  # Discard the matched name.
        if best_score >= similarity_threshold:
            matched_row = unmatched_group2.loc[best_index]
            return matched_row, best_index

    return None, None


def reconcile(group1: pd.DataFrame, group2: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """
    Reconcile rows between two DataFrames (group1 and group2) representing power plant
    records while accepting optional keyword arguments. For example:
      - similarity_threshold: minimal fuzzy-match score (default 90)
      - capacity_tolerance: an optional parameter for further matching logic

    The function performs:
      1. Exact matching on "name_clean" & "capacity_clean".
      2. Fuzzy matching on "name_clean" if no exact match is found.
      3. Assigns rows remaining unmatched in group1 as "Only in file1" and in group2 as "Only in file2".
    """
    similarity_threshold = kwargs.get("similarity_threshold", 90)
    tol = kwargs.get("capacity_tolerance", 0)
            
    # Assert that both groups have the required columns.
    required_columns = {"name", "name_clean", "capacity_clean"}
    assert required_columns.issubset(group1.columns), "group1 missing required columns."
    assert required_columns.issubset(group2.columns), "group2 missing required columns."

    # Make copies to avoid modifying the original data.
    unmatched_group1 = group1.copy()
    unmatched_group2 = group2.copy()

    reconciled_rows: list[dict[str, Any]] = []

    # ----------------------------------------------------------------------
    # Phase 1: Exact matches
    # ----------------------------------------------------------------------
    group1_drop_indexes = []
    for idx1, row1 in unmatched_group1.iterrows():
        row2, match_idx2 = find_exact_match(row1, unmatched_group2)
        if row2 is not None:
            reconciled_rows.append(build_reconciled_row(row1, row2, "Matched"))
            group1_drop_indexes.append(idx1)
            # Drop the matching row from unmatched_group2 so it won't be used again.
            unmatched_group2.drop(index=match_idx2, inplace=True)

    unmatched_group1.drop(index=group1_drop_indexes, inplace=True)
    unmatched_group1.reset_index(drop=True, inplace=True)
    unmatched_group2.reset_index(drop=True, inplace=True)

    # ----------------------------------------------------------------------
    # Phase 2: Fuzzy matches
    # ----------------------------------------------------------------------
    group1_drop_indexes = []
    for idx1, row1 in unmatched_group1.iterrows():
        row2, match_idx2 = find_fuzzy_match(
            row1, unmatched_group2, similarity_threshold
        )
        if row2 is not None:
            capacity_difference = abs(row1["capacity_clean"] - row2["capacity_clean"])
            if capacity_difference > tol:
                status = "Matched (Fuzzy) (Diff)"
            else:
                status = "Matched (Fuzzy)"
            reconciled_rows.append(build_reconciled_row(row1, row2, status))
            group1_drop_indexes.append(idx1)
            unmatched_group2.drop(index=match_idx2, inplace=True)
        else:
            reconciled_rows.append(build_reconciled_row(row1, None, "Only in file1"))

    unmatched_group1.drop(index=group1_drop_indexes, inplace=True)
    unmatched_group1.reset_index(drop=True, inplace=True)
    unmatched_group2.reset_index(drop=True, inplace=True)

    # ----------------------------------------------------------------------
    # Phase 3: Rows remaining in group2 (Only in file2)
    # ----------------------------------------------------------------------
    for _, row2 in unmatched_group2.iterrows():
        reconciled_rows.append(build_reconciled_row(None, row2, "Only in file2"))

    return pd.DataFrame(reconciled_rows)
