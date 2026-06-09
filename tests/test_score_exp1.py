from pathlib import Path

import pytest

from aedist.score_exp1 import _CSV_COLUMNS, _parse_model_run, main, score_file


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


_SAMPLE_ROW = (
    "name,fuel,status,status_as_of,cod,province,capacity_mwe,"
    "confidence,source_1,source_2,note\n"
    "Plant A,coal,operating,2024-01-01,2020,Hanoi,600,"
    "HIGH,http://a,http://b,ok\n"
)

_SAMPLE_REF = (
    "name,fuel,status,province,cod,capacity_mwe\n"
    "Plant A,coal,operating,Hanoi,2020,600\n"
)


def test_main_skips_colocated_outputs(tmp_path: Path) -> None:
    """score_exp1 main() ignores reconciliation_* and filtered_* CSVs."""
    ref = tmp_path / "reference.csv"
    ref.write_text(_SAMPLE_REF, encoding="utf-8")

    input_dir = tmp_path / "runs"
    input_dir.mkdir()
    (input_dir / "model-a-run1.csv").write_text(_SAMPLE_ROW, encoding="utf-8")
    (input_dir / "model-b-run1.csv").write_text(_SAMPLE_ROW, encoding="utf-8")
    (input_dir / "reconciliation_model-a-run1.csv").write_text(_SAMPLE_ROW, encoding="utf-8")
    (input_dir / "filtered_model-b-run1.csv").write_text(_SAMPLE_ROW, encoding="utf-8")

    out = tmp_path / "out.csv"
    main([
        "--input-dir", str(input_dir),
        "--output", str(out),
        "--reference", str(ref),
    ])

    import csv

    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    models = {r["model"] for r in rows}
    assert models == {"model-a", "model-b"}


def test_parse_model_run_still_rejects_malformed() -> None:
    """Skip prefixes don't swallow genuinely malformed filenames."""
    with pytest.raises(ValueError):
        _parse_model_run(Path("no-run-number.csv"))
