"""Reconciliation pipeline: Pydantic schema ↔ LP matching ↔ metrics.

This module bridges the canonical Plant schema with the existing LP-based
matching algorithm.  Unlike the legacy reconcile.py, matching is **global**
(no grouping by province×fuel) — see ADR-3.

For manual review, the output includes province and fuel columns so results
can be sorted/filtered by province+fuel after the fact.
"""

import importlib.resources
from pathlib import Path

import pandas as pd

from .cleaner import PowerPlantDataframeCleaner
from .matching.lp import reconcile as reconcile_lp
from .schema import MatchType, Plant, ReconciliationEntry


# ---------------------------------------------------------------------------
# Config path resolution
# ---------------------------------------------------------------------------

_CLEANER_CONFIG = Path(__file__).parent / "cleaner" / "config.json"


# ---------------------------------------------------------------------------
# Pydantic → DataFrame
# ---------------------------------------------------------------------------

def plants_to_dataframe(plants: list[Plant]) -> pd.DataFrame:
    """Convert a list of Plant to a DataFrame suitable for lp.reconcile().

    The LP matcher expects columns: name, name_clean, capacity_clean.
    We also preserve province, fuel, status for attribute-level metrics.
    """
    rows = []
    for p in plants:
        rows.append({
            "name": p.name,
            "province": p.province or "",
            "fuel": p.fuel.value if p.fuel else "",
            "capacity": str(p.capacity_mwe) if p.capacity_mwe is not None else "",
            "status": p.status.value if p.status else "",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["name", "province", "fuel", "capacity", "status"])

    # Use the existing cleaner for normalization
    cleaner = PowerPlantDataframeCleaner(config_path=str(_CLEANER_CONFIG))
    cleaned = cleaner.clean_dataframe(df)
    return cleaned


# ---------------------------------------------------------------------------
# DataFrame results → ReconciliationEntry
# ---------------------------------------------------------------------------

def _extract_entries(
    result_df: pd.DataFrame,
    ref_df: pd.DataFrame,
    sys_df: pd.DataFrame,
) -> list[ReconciliationEntry]:
    """Convert LP reconciliation DataFrame to list of ReconciliationEntry."""
    entries = []
    for _, row in result_df.iterrows():
        status = row.get("status", "")

        # Determine match type
        if status == "Matched":
            mt = MatchType.EXACT
        elif status == "Matched (Fuzzy)":
            mt = MatchType.FUZZY
        elif status == "Only in file1":
            mt = MatchType.REFERENCE_ONLY
        elif status == "Only in file2":
            mt = MatchType.SYSTEM_ONLY
        else:
            # "Matched (Fuzzy) (Diff)", "Mismatched", etc.
            mt = MatchType.FUZZY_CAPACITY_DIFF if "Fuzzy" in str(status) else MatchType.EXACT_CAPACITY_DIFF

        ref_name = _safe(row, "name_file1")
        sys_name = _safe(row, "name_file2")
        ref_cap = _safe_float(row, "capacity_file1")
        sys_cap = _safe_float(row, "capacity_file2")

        # Capacity diff
        cap_diff_pct = None
        if ref_cap is not None and sys_cap is not None and ref_cap > 0:
            cap_diff_pct = round(abs(sys_cap - ref_cap) / ref_cap * 100, 1)
        elif ref_cap is not None and sys_cap is not None and ref_cap == 0:
            cap_diff_pct = None

        # Look up province/fuel/status from original DataFrames
        ref_prov, ref_fuel, ref_status = _lookup_attrs(ref_df, row, "file1")
        sys_prov, sys_fuel, sys_status = _lookup_attrs(sys_df, row, "file2")

        # Attribute matches (only for matched pairs)
        fuel_match = None
        status_match = None
        province_match = None
        if mt not in (MatchType.REFERENCE_ONLY, MatchType.SYSTEM_ONLY):
            if ref_fuel and sys_fuel:
                fuel_match = ref_fuel == sys_fuel
            if ref_status and sys_status:
                status_match = ref_status == sys_status
            if ref_prov and sys_prov:
                province_match = ref_prov == sys_prov

        entries.append(ReconciliationEntry(
            reference_name=ref_name,
            system_name=sys_name,
            reference_province=ref_prov,
            system_province=sys_prov,
            reference_fuel=ref_fuel,
            system_fuel=sys_fuel,
            reference_capacity_mwe=ref_cap,
            system_capacity_mwe=sys_cap,
            capacity_diff_pct=cap_diff_pct,
            match_type=mt,
            fuel_match=fuel_match,
            status_match=status_match,
            province_match=province_match,
        ))
    return entries


def _safe(row: pd.Series, key: str) -> str | None:
    val = row.get(key)
    if pd.isna(val):
        return None
    return str(val) if val is not None else None


def _safe_float(row: pd.Series, key: str) -> float | None:
    val = row.get(key)
    if val is None or pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _lookup_attrs(
    df: pd.DataFrame, row: pd.Series, suffix: str
) -> tuple[str | None, str | None, str | None]:
    """Look up province_clean, fuel_clean, status_clean from original df by name_clean."""
    name_key = f"name_clean_{suffix}"
    name_clean = row.get(name_key)
    if name_clean is None or pd.isna(name_clean):
        return None, None, None
    matches = df[df["name_clean"] == name_clean]
    if matches.empty:
        return None, None, None
    first = matches.iloc[0]
    return (
        str(first.get("province_clean", "")) or None,
        str(first.get("fuel_clean", "")) or None,
        str(first.get("status_clean", "")) or None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reconcile(
    reference: list[Plant],
    system: list[Plant],
    **kwargs,
) -> list[ReconciliationEntry]:
    """Reconcile system output against reference using global LP matching.

    This is the main entry point for the benchmark.  See ADR-2 (LP matching)
    and ADR-3 (global matching, no province×fuel grouping).

    Keyword arguments are forwarded to matching.lp.reconcile():
        mismatch_penalty, similarity_threshold, capacity_tolerance,
        dummy_cost, capacity_weight.

    Returns a list of ReconciliationEntry (one per reference or system plant).
    """
    ref_df = plants_to_dataframe(reference)
    sys_df = plants_to_dataframe(system)

    result_df = reconcile_lp(ref_df, sys_df, **kwargs)

    return _extract_entries(result_df, ref_df, sys_df)
