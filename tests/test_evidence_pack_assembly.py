from pathlib import Path

from aedist.harness import EVIDENCE_PACK_HEADER_FIELDS, assemble_evidence_pack

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "experiments" / "evidence_packs" / "all18tables.yaml"


def test_assemble_evidence_pack_is_deterministic_and_manifest_ordered() -> None:
    """The same manifest yields byte-identical output and preserves manifest source order."""
    assembled_a = assemble_evidence_pack(MANIFEST_PATH)
    assembled_b = assemble_evidence_pack(MANIFEST_PATH)
    assert assembled_a == assembled_b

    # First three source IDs in manifest order must appear in that same order.
    first = assembled_a.find("source_id: evn_ar_2010_2011_capacities")
    second = assembled_a.find("source_id: evn_ar_2017_capacities")
    third = assembled_a.find("source_id: evn_ar_2018_capacities")
    assert -1 not in (first, second, third)
    assert first < second < third


def test_assemble_evidence_pack_has_stable_headers_and_expected_source_blocks() -> None:
    """Every source block has stable headers and includes expected source_id blocks."""
    assembled = assemble_evidence_pack(MANIFEST_PATH)

    # Manifest has 18 source blocks.
    assert assembled.count("## Source Block") == 18

    for field in EVIDENCE_PACK_HEADER_FIELDS:
        assert assembled.count(f"{field}:") >= 18

    # Spot-check expected source_id blocks from beginning, middle, and end.
    assert "source_id: evn_ar_2010_2011_capacities" in assembled
    assert "source_id: pdp8_annex2_table3" in assembled
    assert "source_id: study_e542_pl9_5a" in assembled
