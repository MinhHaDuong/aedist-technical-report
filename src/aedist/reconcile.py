"""Reconciliation pipeline: Pydantic schema ↔ LP matching ↔ metrics.

This module bridges the canonical Plant schema with the existing LP-based
matching algorithm.  Unlike the legacy reconcile.py, matching is **global**
(no grouping by province×fuel) — see ADR-3.

For manual review, the output includes province and fuel columns so results
can be sorted/filtered by province+fuel after the fact.
"""

import re
from pathlib import Path

import pandas as pd

from .cleaner import PowerPlantDataframeCleaner
from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .matching.lp import reconcile as reconcile_lp
from .schema import MatchType, Plant, ReconciliationEntry

# ---------------------------------------------------------------------------
# Config path resolution
# ---------------------------------------------------------------------------

_CLEANER_CONFIG = Path(__file__).parent / "cleaner" / "config.json"

# Strips any trailing digit block (used for base computation only).
_UNIT_SUFFIX = re.compile(r"\s+\d+$")
# Only "1" is strippable: "Plant 1" → "Plant". "Plant 2" implies a "Plant 1" exists.
_FIRST_UNIT_SUFFIX = re.compile(r"\s+1$")


def _build_single_unit_names(reference_path: Path | None = None) -> frozenset[str]:
    """Names of plants that are the sole unit under their base name (from the fixed reference).

    Rule: name must end in " 1" AND no sibling unit exists in the reference.
    "An Khanh 1" qualifies; "Na Duong 1" does not (Na Duong 2 exists).

    The reference defaults to ``config.VN_THERMAL_PLANTS_RELEASE_CSV`` but may be overridden
    (e.g. when switching the pipeline to a regenerated reference table).
    """
    ref = reference_path or VN_THERMAL_PLANTS_RELEASE_CSV
    if not ref.exists():
        return frozenset()
    cleaner = PowerPlantDataframeCleaner(config_path=str(_CLEANER_CONFIG))
    raw_names = pd.read_csv(ref)["name"].dropna()
    cleaned = raw_names.apply(cleaner.clean_name)
    bases = cleaned.apply(lambda s: _UNIT_SUFFIX.sub("", s))
    base_counts = bases.value_counts()
    return frozenset(
        name
        for name, base in zip(cleaned, bases, strict=True)
        if _FIRST_UNIT_SUFFIX.search(name) and base_counts[base] == 1
    )


# Fixed at import time: the reference is the golden table, so this set is constant.
_SINGLE_UNIT_NAMES: frozenset[str] = _build_single_unit_names()


# ---------------------------------------------------------------------------
# Pydantic → DataFrame
# ---------------------------------------------------------------------------


def plants_to_dataframe(plants: list[Plant]) -> pd.DataFrame:
    """Convert a list of Plant to a DataFrame suitable for lp.reconcile().

    The LP matcher expects columns: name, name_clean, capacity_clean.
    We also preserve province, fuel, status for attribute-level metrics.
    """
    rows = [
        {
            "name": p.name,
            "province": p.province or "",
            "fuel": p.fuel.value if p.fuel else "",
            "capacity": str(p.capacity_mwe) if p.capacity_mwe is not None else "",
            "status": p.status.value if p.status else "",
            "source_ref": p.source_ref or "",
        }
        for p in plants
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        # Return a zero-row DataFrame with all raw + cleaned columns so
        # downstream consumers (LP matcher, metrics) see the schema they
        # expect.  Bypass the cleaner — its validate_dataframe raises on
        # empty input, and there is nothing to clean anyway.
        return pd.DataFrame(
            columns=[
                "name",
                "province",
                "fuel",
                "capacity",
                "status",
                "source_ref",
                "name_clean",
                "province_clean",
                "fuel_clean",
                "capacity_clean",
                "status_clean",
            ]
        )

    # Use the existing cleaner for normalization
    cleaner = PowerPlantDataframeCleaner(config_path=str(_CLEANER_CONFIG))
    cleaned = cleaner.clean_dataframe(df)
    return _strip_unique_unit_suffixes(cleaned)


def _strip_unique_unit_suffixes(df: pd.DataFrame) -> pd.DataFrame:
    """Strip trailing unit numbers from name_clean for known single-unit plants.

    Uses _SINGLE_UNIT_NAMES derived from the fixed golden reference, so the
    stripping rule is identical regardless of what the model output contains.
    Multi-unit plants (Na Duong 1/2, Nghi Son 1/2/3) are never stripped.
    """
    if df.empty or "name_clean" not in df.columns or not _SINGLE_UNIT_NAMES:
        return df
    mask = df["name_clean"].isin(_SINGLE_UNIT_NAMES)
    if not mask.any():
        return df
    df = df.copy()
    df.loc[mask, "name_clean"] = df.loc[mask, "name_clean"].apply(
        lambda s: _UNIT_SUFFIX.sub("", s)
    )
    return df


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
        elif status == "Mismatched":
            # LP forced a below-threshold pair (mismatch_penalty < dummy_cost makes it cheaper
            # to match than to leave both unmatched). Treat as both a missed reference plant
            # and a hallucinated system plant — emit two separate entries.
            ref_prov, ref_fuel, _ref_st, ref_src = _lookup_attrs(ref_df, row, "file1")
            sys_prov, sys_fuel, _sys_st, sys_src = _lookup_attrs(sys_df, row, "file2")
            entries.append(
                ReconciliationEntry(
                    reference_name=_safe(row, "name_file1"),
                    reference_province=ref_prov,
                    reference_fuel=ref_fuel,
                    reference_capacity_mwe=_safe_float(row, "capacity_file1"),
                    match_type=MatchType.REFERENCE_ONLY,
                    reference_source_ref=ref_src,
                )
            )
            entries.append(
                ReconciliationEntry(
                    system_name=_safe(row, "name_file2"),
                    system_province=sys_prov,
                    system_fuel=sys_fuel,
                    system_capacity_mwe=_safe_float(row, "capacity_file2"),
                    match_type=MatchType.SYSTEM_ONLY,
                    system_source_ref=sys_src,
                )
            )
            continue
        else:
            # "Matched (Fuzzy) (Diff)", "Matched (Diff)"
            mt = (
                MatchType.FUZZY_CAPACITY_DIFF
                if "Fuzzy" in str(status)
                else MatchType.EXACT_CAPACITY_DIFF
            )

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

        # Look up province/fuel/status/source_ref from original DataFrames
        ref_prov, ref_fuel, ref_status, ref_src = _lookup_attrs(ref_df, row, "file1")
        sys_prov, sys_fuel, sys_status, sys_src = _lookup_attrs(sys_df, row, "file2")

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

        # Propagate similarity score from LP result row
        sim_score = _safe_float(row, "similarity_score")

        entries.append(
            ReconciliationEntry(
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
                reference_source_ref=ref_src,
                system_source_ref=sys_src,
                similarity_score=sim_score,
            )
        )
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
) -> tuple[str | None, str | None, str | None, str | None]:
    """Look up province_clean, fuel_clean, status_clean, source_ref from original df by name_clean."""
    name_key = f"name_clean_{suffix}"
    name_clean = row.get(name_key)
    if name_clean is None or pd.isna(name_clean):
        return None, None, None, None
    matches = df[df["name_clean"] == name_clean]
    if matches.empty:
        return None, None, None, None
    first = matches.iloc[0]
    return (
        str(first.get("province_clean", "")) or None,
        str(first.get("fuel_clean", "")) or None,
        str(first.get("status_clean", "")) or None,
        str(first.get("source_ref", "")) or None,
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
