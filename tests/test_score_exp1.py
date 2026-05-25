from pathlib import Path

import pytest

from aedist.score_exp1 import _CSV_COLUMNS, _parse_model_run, score_file


def test_parse_model_run() -> None:
    model, run = _parse_model_run(Path("qwen3-max-thinking-run05.csv"))
    assert model == "qwen3-max-thinking"
    assert run == 5


def test_parse_model_run_invalid_name() -> None:
    with pytest.raises(ValueError):
        _parse_model_run(Path("bad_name.csv"))


def test_score_file_emits_expected_columns(tmp_path: Path) -> None:
    source = tmp_path / "toy-model-run1.csv"
    source.write_text(
        "name,fuel,status,status_as_of,cod,province,capacity_mwe,confidence,source_1,source_2,note\n"
        "Plant A,coal,operating,2024-01-01,2020,Hanoi,600,HIGH,http://a,http://b,ok\n",
        encoding="utf-8",
    )
    reference = tmp_path / "reference.csv"
    reference.write_text(
        "name,fuel,status,province,cod,capacity_mwe\n"
        "Plant A,coal,operating,Hanoi,2020,600\n",
        encoding="utf-8",
    )

    row = score_file(source, reference, prompt_version="exp1")

    assert list(row.keys()) == _CSV_COLUMNS
    assert row["arm"] == "parametric"
    assert row["model"] == "toy-model"
    assert row["run"] == "1"
    assert row["prompt_version"] == "exp1"
