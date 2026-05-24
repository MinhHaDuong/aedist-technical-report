"""Tests for experiments.sota.exp2_phase_b0_consolidate."""

from experiments.sota.exp2_phase_b0_consolidate import _count_table_rows


def test_count_table_rows_ignores_summary_tables():
    text = (
        "| Name | Fuel | Province | Capacity | Status | COD |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
        "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n"
        "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n\n"
        "| Fuel | Capacity |\n"
        "| --- | --- |\n"
        "| Coal | 2910 |\n"
        "| Gas | 0 |\n"
    )
    assert _count_table_rows(text) == 3
