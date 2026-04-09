#
# Minh Ha-Duong, CNRS (2025)
# CC-BY-SA

"""Build a reconciliation result dict from matched/unmatched plant pairs."""

from typing import Any

import pandas as pd


def build_result_row(
    row1: pd.Series | None,
    row2: pd.Series | None,
    status: str,
    *,
    similarity_score: float | None = None,
) -> dict[str, Any]:
    """Build a reconciliation result dict from a pair of matched/unmatched rows.

    Args:
        row1: Row from file 1 (or None if unmatched).
        row2: Row from file 2 (or None if unmatched).
        status: Match status string (e.g. "Matched", "Only in file1").
        similarity_score: Fuzzy similarity score (0-100), 100 for exact,
            None for unmatched entries.

    Returns:
        Dictionary with keys: name_file1, name_clean_file1, capacity_file1,
        name_file2, name_clean_file2, capacity_file2, capacity_difference,
        status, similarity_score.
    """

    def _get(row: pd.Series | None, key: str) -> Any:
        if row is None:
            return None
        return row.get(key)

    cap1 = _get(row1, "capacity_clean")
    cap2 = _get(row2, "capacity_clean")

    if cap1 is not None and cap2 is not None:
        try:
            capacity_difference = cap1 - cap2
        except Exception:
            capacity_difference = None
    else:
        capacity_difference = None

    return {
        "name_file1": _get(row1, "name"),
        "name_clean_file1": _get(row1, "name_clean"),
        "capacity_file1": cap1,
        "name_file2": _get(row2, "name"),
        "name_clean_file2": _get(row2, "name_clean"),
        "capacity_file2": cap2,
        "capacity_difference": capacity_difference,
        "status": status,
        "similarity_score": similarity_score,
    }
