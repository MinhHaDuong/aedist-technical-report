"""Tests for aedist.prototype_v1_fusion.

Unit tests only — no LLM calls. All external calls are mocked.
"""

from unittest.mock import MagicMock

import pytest

from aedist.prototype_v1_fusion import (
    _EXTRACT_PROMPT,
    _FUSE_PROMPT,
    _GLOBAL_MD_PROMPT,
    _GLOBAL_PROMPT,
    DEFAULT_SEQUENCE,
    FragmentSpec,
    MasterRecord,
    SourcedField,
    _parse_csv_from_response,
    dicts_to_plants,
    master_to_plants,
    run_global_md,
    run_incremental,
    run_incremental_direct,
    score_against_reference,
)
from aedist.schema import FuelType, Plant, PlantStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(filename, source_id, tier, year):
    return FragmentSpec(filename=filename, source_id=source_id, tier=tier, year=year)


def _mock_client(response_text, finish_reason="stop"):
    choice = MagicMock()
    choice.message.content = response_text
    choice.finish_reason = finish_reason
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 100
    resp.usage.completion_tokens = 50
    client = MagicMock()
    client.chat.completions.create.return_value = resp
    return client


# ---------------------------------------------------------------------------
# Prompt files loaded — spot-check placeholders
# ---------------------------------------------------------------------------


def test_extract_prompt_has_text_placeholder():
    assert "{text}" in _EXTRACT_PROMPT


def test_global_prompt_has_placeholders():
    assert "{n}" in _GLOBAL_PROMPT
    assert "{sources}" in _GLOBAL_PROMPT


def test_fuse_prompt_has_all_placeholders():
    for key in ("n_master", "master_csv", "source_id", "tier", "year", "fragment_text"):
        assert "{" + key + "}" in _FUSE_PROMPT, f"Missing placeholder: {{{key}}}"


def test_global_md_prompt_specifies_columns():
    """Prompt must mention the expected CSV columns."""
    for col in ("name", "fuel", "capacity_mwe", "status", "province", "cod"):
        assert col in _GLOBAL_MD_PROMPT, f"Column '{col}' missing from global_md prompt"


# ---------------------------------------------------------------------------
# MasterRecord authority rule
# ---------------------------------------------------------------------------


def _sf(value, tier, year, source="src"):
    return SourcedField(value=value, source_id=source, tier=tier, year=year)


def test_update_field_higher_tier_wins():
    rec = MasterRecord(name="Plant A", fuel=_sf("coal", tier=2, year=2020))
    rec.update_field("fuel", "gas", _make_spec("f.md", "PDP8", tier=3, year=2023))
    assert rec.fuel.value == "gas"
    assert rec.fuel.tier == 3


def test_update_field_lower_tier_loses():
    rec = MasterRecord(name="Plant A", fuel=_sf("coal", tier=3, year=2020))
    rec.update_field("fuel", "gas", _make_spec("f.md", "EVN", tier=2, year=2022))
    assert rec.fuel.value == "coal"


def test_update_field_same_tier_later_year_wins():
    rec = MasterRecord(name="Plant A", fuel=_sf("coal", tier=2, year=2018))
    rec.update_field("fuel", "gas", _make_spec("f.md", "EVN2", tier=2, year=2020))
    assert rec.fuel.value == "gas"


def test_update_field_null_incoming_never_overwrites():
    rec = MasterRecord(name="Plant A", fuel=_sf("coal", tier=2, year=2018))
    rec.update_field("fuel", None, _make_spec("f.md", "PDP8", tier=3, year=2023))
    assert rec.fuel.value == "coal"


# ---------------------------------------------------------------------------
# _parse_csv_from_response
# ---------------------------------------------------------------------------


def test_parse_csv_from_response_fenced_block(tmp_path):
    raw = (
        "Here is the result:\n"
        "```csv\n"
        "name,fuel,capacity_mwe,status,province,cod\n"
        "Pha Lai,coal,400,operational,Hai Duong,1983\n"
        "Ba Ria,gas,150,,Ba Ria,\n"
        "```\n"
    )
    plants = _parse_csv_from_response(raw)
    assert len(plants) == 2
    assert plants[0].name == "Pha Lai"
    assert plants[0].fuel == FuelType.COAL
    assert plants[0].capacity_mwe == 400.0
    assert plants[1].name == "Ba Ria"
    assert plants[1].fuel == FuelType.GAS


def test_parse_csv_from_response_arbitrary_headers(tmp_path):
    """parse_and_canonicalize normalises 'Name', 'Fuel Type', 'Generation Capacity (MWe)'."""
    raw = (
        "```csv\n"
        "Name,Fuel Type,Generation Capacity (MWe),Construction Stage,Province,COD\n"
        "Ninh Binh,Coal,100,Operational,Ninh Binh,1974\n"
        "```\n"
    )
    plants = _parse_csv_from_response(raw)
    assert len(plants) == 1
    assert plants[0].name == "Ninh Binh"
    assert plants[0].fuel == FuelType.COAL
    assert plants[0].capacity_mwe == 100.0
    assert plants[0].status == PlantStatus.OPERATIONAL


def test_parse_csv_from_response_empty_returns_empty():
    plants = _parse_csv_from_response("No CSV here.")
    assert plants == []


# ---------------------------------------------------------------------------
# dicts_to_plants
# ---------------------------------------------------------------------------


def test_dicts_to_plants_basic():
    dicts = [
        {"name": "Pha Lai", "fuel": "coal", "capacity_mwe": "400", "status": "operational"},
        {"name": "Ba Ria", "fuel": "gas", "capacity_mwe": None, "status": None},
    ]
    plants = dicts_to_plants(dicts)
    assert len(plants) == 2
    assert plants[0].fuel == FuelType.COAL
    assert plants[0].capacity_mwe == 400.0
    assert plants[1].fuel == FuelType.GAS
    assert plants[1].capacity_mwe is None


def test_dicts_to_plants_skips_empty_name():
    dicts = [{"name": "", "fuel": "coal"}, {"name": "Pha Lai", "fuel": "coal"}]
    plants = dicts_to_plants(dicts)
    assert len(plants) == 1


def test_dicts_to_plants_unknown_fuel_fallback():
    plants = dicts_to_plants([{"name": "X", "fuel": "nuclear"}])
    assert plants[0].fuel == FuelType.UNKNOWN


# ---------------------------------------------------------------------------
# master_to_plants
# ---------------------------------------------------------------------------


def test_master_to_plants_converts_records():
    rec = MasterRecord(
        name="Pha Lai",
        fuel=_sf(FuelType.COAL, tier=3, year=2020),
        capacity_mwe=_sf(400.0, tier=3, year=2020),
        status=_sf(PlantStatus.OPERATIONAL, tier=3, year=2020),
    )
    plants = master_to_plants([rec])
    assert len(plants) == 1
    assert plants[0].name == "Pha Lai"
    assert plants[0].fuel == FuelType.COAL
    assert plants[0].capacity_mwe == 400.0


# ---------------------------------------------------------------------------
# DEFAULT_SEQUENCE sanity
# ---------------------------------------------------------------------------


def test_default_sequence_has_expected_count():
    assert len(DEFAULT_SEQUENCE) == 18


def test_default_sequence_tier_range():
    tiers = {s.tier for s in DEFAULT_SEQUENCE}
    assert tiers == {2, 3}


def test_default_sequence_no_duplicate_filenames():
    names = [s.filename for s in DEFAULT_SEQUENCE]
    assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# run_incremental — mocked LLM (JSON mode)
# ---------------------------------------------------------------------------


def test_run_incremental_processes_existing_fragments(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc1.md").write_text("Pha Lai plant data")

    seq = [_make_spec("doc1.md", "SRC1", tier=2, year=2020)]
    json_response = '[{"name": "Pha Lai", "fuel": "coal", "capacity_mwe": 400, "status": "operational", "province": "Hai Duong", "cod": "1983"}]'
    client = _mock_client(json_response)

    master, diffs = run_incremental(corpus, seq, client, "test/model")
    assert len(master) == 1
    assert master[0].name == "Pha Lai"
    assert len(diffs) == 1
    assert diffs[0].source_id == "SRC1"
    assert diffs[0].added == 1


def test_run_incremental_skips_missing_fragments(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()

    seq = [_make_spec("nonexistent.md", "SRC1", tier=2, year=2020)]
    client = _mock_client("[]")

    master, diffs = run_incremental(corpus, seq, client, "test/model")
    assert master == []
    assert diffs == []


def test_run_incremental_authority_across_fragments(tmp_path):
    """Later high-tier fragment overwrites earlier low-tier value."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "low.md").write_text("low tier data")
    (corpus / "high.md").write_text("high tier data")

    low_resp = '[{"name": "Pha Lai", "fuel": "coal", "capacity_mwe": 300, "status": null, "province": null, "cod": null}]'
    high_resp = '[{"name": "Pha Lai", "fuel": "gas", "capacity_mwe": 400, "status": null, "province": null, "cod": null}]'

    seq = [
        _make_spec("low.md", "LOW", tier=2, year=2018),
        _make_spec("high.md", "HIGH", tier=3, year=2023),
    ]
    call_count = 0
    responses = [low_resp, high_resp]

    def side_effect(**kwargs):
        nonlocal call_count
        choice = MagicMock()
        choice.message.content = responses[call_count]
        choice.finish_reason = "stop"
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = 10
        resp.usage.completion_tokens = 10
        call_count += 1
        return resp

    client = MagicMock()
    client.chat.completions.create.side_effect = side_effect

    master, _ = run_incremental(corpus, seq, client, "test/model")
    assert len(master) == 1
    assert master[0].fuel.value == FuelType.GAS
    assert master[0].fuel.source_id == "HIGH"


# ---------------------------------------------------------------------------
# run_global_md — mocked LLM
# ---------------------------------------------------------------------------


def test_run_global_md_sends_corpus_as_system(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc1.md").write_text("Pha Lai is a coal plant.")

    seq = [_make_spec("doc1.md", "SRC1", tier=2, year=2020)]
    csv_response = "```csv\nname,fuel,capacity_mwe,status,province,cod\nPha Lai,coal,400,operational,Hai Duong,1983\n```"
    client = _mock_client(csv_response)

    plants = run_global_md(corpus, seq, client, "test/model", "List plants as CSV.")

    call_args = client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert messages[0]["role"] == "system"
    assert "Pha Lai is a coal plant." in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert len(plants) == 1
    assert plants[0].name == "Pha Lai"


# ---------------------------------------------------------------------------
# run_incremental_direct — mocked LLM (md mode)
# ---------------------------------------------------------------------------


def test_run_incremental_direct_accumulates_csv(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc1.md").write_text("Source A")
    (corpus / "doc2.md").write_text("Source B")

    seq = [
        _make_spec("doc1.md", "A", tier=2, year=2018),
        _make_spec("doc2.md", "B", tier=3, year=2023),
    ]
    responses = [
        "```csv\nname,fuel,capacity_mwe,status,province,cod\nPha Lai,coal,400,operational,Hai Duong,1983\n```",
        "```csv\nname,fuel,capacity_mwe,status,province,cod\nPha Lai,coal,400,operational,Hai Duong,1983\nBa Ria,gas,150,operational,Ba Ria,\n```",
    ]
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        choice = MagicMock()
        choice.message.content = responses[call_count]
        choice.finish_reason = "stop"
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = 10
        resp.usage.completion_tokens = 10
        call_count += 1
        return resp

    client = MagicMock()
    client.chat.completions.create.side_effect = side_effect

    plants, diffs = run_incremental_direct(corpus, seq, client, "test/model")
    assert len(plants) == 2
    assert {p.name for p in plants} == {"Pha Lai", "Ba Ria"}
    assert len(diffs) == 2


# ---------------------------------------------------------------------------
# score_against_reference
# ---------------------------------------------------------------------------


def test_score_against_reference_perfect(tmp_path):
    ref = tmp_path / "ref.csv"
    ref.write_text("name,fuel,capacity_mwe,status,province,cod\nPha Lai,coal,400,operational,,\n")
    plants = [Plant(name="Pha Lai", fuel=FuelType.COAL, status=PlantStatus.OPERATIONAL)]
    scores = score_against_reference(plants, ref)
    assert scores["coverage"] == 1.0
    assert scores["precision"] == 1.0
    assert scores["f1"] == 1.0


def test_score_against_reference_empty_system(tmp_path):
    ref = tmp_path / "ref.csv"
    ref.write_text("name,fuel,capacity_mwe,status,province,cod\nPha Lai,coal,400,operational,,\n")
    scores = score_against_reference([], ref)
    assert scores["coverage"] == 0.0
    assert scores["f1"] == 0.0


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


def test_main_format_both_requires_compare(tmp_path):
    """--format both is only valid with --fusion-mode compare."""
    from aedist.prototype_v1_fusion import main

    with pytest.raises(SystemExit):
        main(["--fusion-mode", "incremental", "--format", "both"])
