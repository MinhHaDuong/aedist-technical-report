"""Tests for aedist.score_ingest."""

import csv
import json

import pytest

from aedist.score_ingest import (
    IngestionError,
    IngestionErrorKind,
    RunLocator,
    _arm_dir,
    check_inventory_row_parity,
    check_inventory_row_parity_csv,
    ingest_run,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_md(path, content):
    path.write_text(content, encoding="utf-8")


def _write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_arm_dir_resolves_all_four_arms(tmp_path):
    from pathlib import Path

    naive = Path("/n")
    optimised = Path("/o")
    three = Path("/three")
    four = Path("/four")
    assert _arm_dir("naive", naive, optimised, three, four) == naive
    assert _arm_dir("optimised", naive, optimised, three, four) == optimised
    assert _arm_dir("arm3", naive, optimised, three, four) == three
    assert _arm_dir("arm4", naive, optimised, three, four) == four


def test_arm_dir_unknown_arm_raises():
    from pathlib import Path

    with pytest.raises(IngestionError) as excinfo:
        _arm_dir("arm9", Path("/n"), Path("/o"), Path("/three"), Path("/four"))
    assert excinfo.value.kind is IngestionErrorKind.UNKNOWN_ARM


def test_arm_dir_unconfigured_known_arm_raises():
    from pathlib import Path

    # arm3/arm4 default to None; calling without supplying their dirs must fail.
    with pytest.raises(IngestionError) as excinfo:
        _arm_dir("arm3", Path("/n"), Path("/o"))
    assert excinfo.value.kind is IngestionErrorKind.UNKNOWN_ARM


@pytest.mark.parametrize(
    "arm,dir_kwarg",
    [
        ("naive", "naive_dir"),
        ("optimised", "optimised_dir"),
        ("arm3", "arm3_dir"),
        ("arm4", "arm4_dir"),
    ],
)
def test_ingest_run_resolves_each_arm(tmp_path, arm, dir_kwarg):
    arm_dir = tmp_path / arm
    arm_dir.mkdir()
    _write_json(arm_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        arm_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n",
    )
    ingested = ingest_run(RunLocator(arm=arm, model="gpt-5.5", run=1), **{dir_kwarg: arm_dir})
    assert len(ingested.rows) == 1
    assert ingested.rows[0]["name"] == "Pha Lai"


def test_ingest_run_extracts_sectioned_table(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "openai_run01.json",
        {"model": "gpt-5.5", "run": 1},
    )
    _write_md(
        naive_dir / "openai_run01.md",
        "### Coal operating\n\n"
        "| Name | Fuel | Total MWe | Status | COD | Province | Notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong | Legacy |\n"
        "| Uong Bi | Coal | 630 | Operating | 2009/2013 | Quang Ninh | Expansion only |\n\n"
        "| Fuel | Capacity |\n"
        "| --- | --- |\n"
        "| Coal | 1070 |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )

    assert len(ingested.rows) == 2
    assert ingested.rows[0]["name"] == "Pha Lai"
    assert ingested.rows[0]["capacity_mwe"] == "440.0"
    assert ingested.rows[1]["name"] == "Uong Bi"
    assert ingested.rows[1]["capacity_mwe"] == "630.0"


def test_ingest_run_missing_path_returns_typed_error(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    with pytest.raises(IngestionError) as excinfo:
        ingest_run(
            RunLocator(arm="naive", model="gpt-5.5", run=99),
            naive_dir=naive_dir,
            optimised_dir=optimised_dir,
        )

    assert excinfo.value.kind is IngestionErrorKind.RUN_NOT_FOUND
    assert excinfo.value.locator.model == "gpt-5.5"
    assert "gpt-5.5" in excinfo.value.detail


def test_ingest_run_invalid_utf8_returns_typed_error(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    (naive_dir / "openai_run01.md").write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(IngestionError) as excinfo:
        ingest_run(
            RunLocator(arm="naive", model="gpt-5.5", run=1),
            naive_dir=naive_dir,
            optimised_dir=optimised_dir,
        )

    assert excinfo.value.kind is IngestionErrorKind.INVALID_ENCODING


def test_check_inventory_row_parity_for_naive_and_optimised_runs(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "openai_run01.json",
        {"model": "gpt-5.5", "run": 1},
    )
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n"
        "| Uong Bi | Coal | 630 | Operating | 2002 | Quang Ninh |\n",
    )

    _write_json(
        optimised_dir / "anthropic_run03.json",
        {"model": "claude-opus-4-6", "run": 3},
    )
    _write_md(
        optimised_dir / "anthropic_run03.md",
        "| Name | Fuel | Total MW | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Vinh Tan 1 | Coal | 1240 | Operating | 2018 | Binh Thuan |\n"
        "| Duyen Hai 1 | Coal | 1245 | Operating | 2015 | Tra Vinh |\n"
        "| Song Hau 1 | Coal | 1200 | Operating | 2022 | Hau Giang |\n",
    )

    naive_diag = check_inventory_row_parity(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        expected_rows=2,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    optimised_diag = check_inventory_row_parity(
        RunLocator(arm="optimised", model="claude-opus-4-6", run=3),
        expected_rows=3,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )

    assert naive_diag.matches is True
    assert naive_diag.observed_rows == 2
    assert "expected=2 observed=2" in naive_diag.message
    assert optimised_diag.matches is True
    assert optimised_diag.observed_rows == 3
    assert "expected=3 observed=3" in optimised_diag.message


def test_check_inventory_row_parity_csv_reads_runs_csv(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n",
    )

    _write_json(
        optimised_dir / "anthropic_run03.json",
        {"model": "claude-opus-4-6", "run": 3},
    )
    _write_md(
        optimised_dir / "anthropic_run03.md",
        "| Name | Fuel | Total MW | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Vinh Tan 1 | Coal | 1240 | Operating | 2018 | Binh Thuan |\n"
        "| Duyen Hai 1 | Coal | 1245 | Operating | 2015 | Tra Vinh |\n",
    )

    runs_csv = tmp_path / "tab_exp2_arms_runs.csv"
    _write_csv(
        runs_csv,
        ["arm", "model", "run", "inventory_rows"],
        [
            {"arm": "naive", "model": "gpt-5.5", "run": 1, "inventory_rows": 1},
            {
                "arm": "optimised",
                "model": "claude-opus-4-6",
                "run": 3,
                "inventory_rows": 2,
            },
        ],
    )

    diagnostics = check_inventory_row_parity_csv(
        runs_csv,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )

    assert len(diagnostics) == 2
    assert diagnostics[0].matches is True
    assert diagnostics[1].matches is True


def test_check_inventory_row_parity_csv_keeps_processing_on_invalid_row(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n",
    )

    runs_csv = tmp_path / "tab_exp2_arms_runs.csv"
    _write_csv(
        runs_csv,
        ["arm", "model", "run", "inventory_rows"],
        [
            {"arm": "naive", "model": "gpt-5.5", "run": "bad", "inventory_rows": 1},
            {"arm": "naive", "model": "gpt-5.5", "run": 1, "inventory_rows": 1},
        ],
    )

    diagnostics = check_inventory_row_parity_csv(
        runs_csv,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )

    assert len(diagnostics) == 2
    assert diagnostics[0].matches is False
    assert diagnostics[0].message.startswith("invalid_parity_row")
    assert diagnostics[1].matches is True
