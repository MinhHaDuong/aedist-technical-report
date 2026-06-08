"""Adherence: Kiên Lương complex present in the classified reference master (ticket 0472)."""

import pandas as pd
import pytest

from aedist.config import VN_THERMAL_PLANTS_RELEASE_CSV


@pytest.mark.adherence
def test_kien_luong_in_reference():
    df = pd.read_csv(VN_THERMAL_PLANTS_RELEASE_CSV, dtype=str)
    kl = df[df["name"].str.contains("Kiên Lương", na=False)]
    assert len(kl) >= 3, f"Expected ≥3 Kiên Lương plants, found {len(kl)}: {kl['name'].tolist()}"
    assert (kl["status"] == "9 cancelled").all(), "All Kiên Lương plants should be cancelled"
    assert (kl["province"] == "Kiên Giang").all()
