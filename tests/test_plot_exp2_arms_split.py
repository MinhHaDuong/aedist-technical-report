"""Tests for aedist.plot_exp2_arms_split — arm canonicalisation and row loading."""

import csv

from aedist.plot_exp2_arms_split import _canonical_arm, _mean, load_exp2_rows


def test_canonical_arm_maps_named_arms() -> None:
    assert _canonical_arm("naive") == "arm1"
    assert _canonical_arm("optimised") == "arm2"
    assert _canonical_arm("arm3") == "arm3"  # passthrough


def test_mean_empty_is_zero() -> None:
    assert _mean([]) == 0.0
    assert _mean([2.0, 4.0]) == 3.0


def test_load_exp2_rows_types_and_blank_handling(tmp_path) -> None:
    path = tmp_path / "rows.csv"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "run", "inventory_rows", "n_matched", "cost_usd",
                "arm", "classification",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "run": "1", "inventory_rows": "114", "n_matched": "100",
            "cost_usd": "0.42", "arm": "naive", "classification": "report",
        })
        writer.writerow({
            "run": "2", "inventory_rows": "", "n_matched": "",
            "cost_usd": "", "arm": "optimised", "classification": "no_report",
        })

    rows = load_exp2_rows(path)
    assert rows[0]["run"] == 1
    assert rows[0]["inventory_rows"] == 114
    assert rows[0]["n_matched"] == 100
    assert rows[0]["cost_usd"] == 0.42
    assert rows[0]["arm"] == "arm1"
    assert rows[0]["is_report"] is True

    # Blank numerics coerced; missing n_matched -> None; cost defaults to 0.0.
    assert rows[1]["inventory_rows"] == 0
    assert rows[1]["n_matched"] is None
    assert rows[1]["cost_usd"] == 0.0
    assert rows[1]["arm"] == "arm2"
    assert rows[1]["is_report"] is False
