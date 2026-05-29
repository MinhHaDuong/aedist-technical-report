"""Ground-truth audit of the Experiment 2 mart column contract.

The unit tests in ``test_exp2_mart.py`` check the contract for *internal*
consistency: every column projects from a key in ``PIPELINE_KEYS`` (a
hand-maintained mirror) and the Arrow schema matches the declared dtypes.

But ``PIPELINE_KEYS`` is just a mirror. If the extraction pipeline renames a
key and the mirror is not updated, the internal checks still pass while
``project_row``'s ``row.get(source_key)`` silently yields an all-null column.
That is the exact drift class fixed in commit ``d39021e`` (certainty vs
mean_certainty) — and it was unguarded against the real producer output.

This module audits the contract against the committed upstream data file, so
the mart columns are verified to *really feed on what they say they encode*.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pytest

from aedist.exp2_mart import MART_COLUMNS, PIPELINE_KEYS

# The committed per-run metrics the mart projects from.
MART_DATA = (
    Path(__file__).resolve().parents[1] / "experiments" / "derived" / "exp2_mart.jsonl"
)


def _load_records() -> list[dict]:
    if not MART_DATA.exists():
        pytest.skip(f"upstream mart data not present: {MART_DATA}")
    records = [
        json.loads(line)
        for line in MART_DATA.read_text().splitlines()
        if line.strip()
    ]
    if not records:
        pytest.skip(f"upstream mart data is empty: {MART_DATA}")
    return records


def _data_keys() -> set[str]:
    return {k for r in _load_records() for k in r}


# Arrow dtype -> the Python value types JSON may legitimately decode into.
# bool is excluded from int64 on purpose: JSON true/false must not pass as int.
_DTYPE_PY_TYPES = {
    pa.string(): (str,),
    pa.int64(): (int,),
    pa.float64(): (int, float),  # JSON has no float/int distinction for 1.0
}


@pytest.mark.adherence
def test_every_source_key_present_in_real_data():
    """Each column's source_key must appear in the actual upstream records.

    A source_key absent from the data is the silent all-null-column failure
    mode: it cannot be caught by the PIPELINE_KEYS mirror alone.
    """
    keys = _data_keys()
    orphans = {
        c.name: c.source_key for c in MART_COLUMNS if c.source_key not in keys
    }
    assert not orphans, (
        "mart columns project source keys absent from "
        f"{MART_DATA.name}: {orphans}"
    )


@pytest.mark.adherence
def test_pipeline_keys_mirror_matches_real_data():
    """PIPELINE_KEYS must equal the keys the real producer actually emits.

    Catches mirror staleness in both directions: keys the mirror claims that
    the data lacks, and keys the data emits that the mirror omits.
    """
    keys = _data_keys()
    claimed_but_absent = sorted(PIPELINE_KEYS - keys)
    emitted_but_unmirrored = sorted(keys - PIPELINE_KEYS)
    assert not claimed_but_absent and not emitted_but_unmirrored, (
        "PIPELINE_KEYS drifted from real producer output "
        f"({MART_DATA.name}): claimed_but_absent={claimed_but_absent}, "
        f"emitted_but_unmirrored={emitted_but_unmirrored}"
    )


@pytest.mark.adherence
def test_column_dtypes_match_real_values():
    """Declared Arrow dtype must accept the real value type for each column."""
    records = _load_records()
    mismatches: list[str] = []
    for c in MART_COLUMNS:
        allowed = _DTYPE_PY_TYPES.get(c.dtype)
        if allowed is None:
            continue  # dtype not covered by this audit
        for r in records:
            v = r.get(c.source_key)
            if v is None:
                continue
            if isinstance(v, bool) or not isinstance(v, allowed):
                mismatches.append(
                    f"{c.name}: declared {c.dtype} but data has "
                    f"{type(v).__name__}={v!r}"
                )
                break
    assert not mismatches, "; ".join(mismatches)
