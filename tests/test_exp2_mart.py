"""Tests for the Exp2 mart schema."""

from pydantic import ValidationError

from aedist.exp2_mart import (
    ArtifactPointer,
    Exp2ProbeMartRecord,
    Exp2RunMartRecord,
    Exp2ScoreMartRecord,
)


def _pointer(path: str) -> ArtifactPointer:
    return ArtifactPointer(path=path, sha256="a" * 64)


def test_artifact_pointer_rejects_absolute_paths() -> None:
    try:
        ArtifactPointer(path="/tmp/exp2.json", sha256="a" * 64)
    except ValidationError as exc:
        assert "repo-relative" in str(exc)
    else:
        raise AssertionError("absolute paths must be rejected")


def test_run_record_carries_mart_version_and_result_pointer() -> None:
    record = Exp2RunMartRecord(
        record_id="exp2-naive/anthropic/01",
        arm="naive",
        model="claude-opus-4-6",
        run=1,
        prompt_version="exp2-naive",
        run_summary={
            "n_rows": 79,
            "classification": "report",
            "turns": 1,
            "tokens_out": 25522,
            "wall_s": 437.2,
            "cost_usd": 1.1551,
            "classifier_cost_usd": 0.002334,
            "narrative_chars": 50471,
        },
        result_file=_pointer("experiments/outputs/sota_exp2_naive_arm/anthropic_run01.json"),
    )

    assert record.mart_schema == "exp2_mart"
    assert record.mart_schema_version == 1
    assert record.record_kind == "run"
    assert record.run_summary.classification == "report"
    assert record.result_file.path.endswith("anthropic_run01.json")


def test_probe_record_requires_probe_pointer() -> None:
    record = Exp2ProbeMartRecord(
        record_id="exp2-naive/anthropic/01/turn-01",
        parent_record_id="exp2-naive/anthropic/01",
        arm="naive",
        model="claude-opus-4-6",
        run=1,
        probe_summary={"turn": 1, "probe_label": "report", "rows": 42},
        probe_file=_pointer("experiments/outputs/sota_exp2_naive_arm/probes/turn01.md"),
    )

    assert record.record_kind == "probe"
    assert record.parent_record_id == "exp2-naive/anthropic/01"
    assert record.probe_summary.turn == 1
    assert record.probe_file.path.endswith("turn01.md")


def test_score_record_rejects_verbatim_chat_payload_fields() -> None:
    try:
        Exp2ScoreMartRecord(
            record_id="exp2-naive/anthropic/01/score",
            arm="naive",
            model="claude-opus-4-6",
            run=1,
            score_summary={
                "n_rows": 79,
                "accuracy": {
                    "coverage": {"value": 0.4847, "annotation": ""},
                    "precision": {"value": 1.0, "annotation": ""},
                    "f1": {"value": 0.6529, "annotation": ""},
                    "fuel": {"value": 0.5063, "annotation": ""},
                    "status": {"value": 0.5316, "annotation": ""},
                    "province": {"value": 0.8101, "annotation": ""},
                },
                "coherence": {
                    "vocab_adherence": {"value": 0.6456, "annotation": ""},
                    "status_vocab_adherence": {"value": 1.0, "annotation": ""},
                },
                "provenance": {
                    "source_presence": {"value": 1.0, "annotation": ""},
                    "high_conf_dual_source": {"value": 1.0, "annotation": ""},
                },
                "temporality": {
                    "asof_presence": {"value": 1.0, "annotation": ""},
                    "plausible_range": {"value": 1.0, "annotation": ""},
                },
                "field_completeness": {
                    "core": {"value": 1.0, "annotation": ""},
                    "capacity": {"value": 1.0, "annotation": ""},
                },
            },
            result_file=_pointer("experiments/outputs/sota_exp2_naive_arm/anthropic_run01.json"),
            raw_payload={"content": "verbatim chat text"},
        )
    except ValidationError as exc:
        assert "raw_payload" in str(exc)
    else:
        raise AssertionError("verbatim payload fields must be rejected")
