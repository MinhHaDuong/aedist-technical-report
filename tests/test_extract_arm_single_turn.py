import csv
import json

import pytest

from aedist.build_exp2_mart import build_exp2_mart
from aedist.extract_arm_single_turn import (
    _extract_bibliography_entries,
    flatten_single_turn_arm,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_cross_eval_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _score_row(arm, model, run):
    return {
        "arm": arm,
        "model": model,
        "run": str(run),
        "prompt_version": "exp2",
        "n_rows": "1",
        "accuracy_coverage": "0.5000",
        "accuracy_coverage_annotation": "",
        "accuracy_precision": "1.0000",
        "accuracy_precision_annotation": "",
        "accuracy_f1": "0.6667",
        "accuracy_f1_annotation": "",
        "accuracy_fuel": "1.0000",
        "accuracy_fuel_annotation": "",
        "accuracy_status": "1.0000",
        "accuracy_status_annotation": "",
        "accuracy_province": "1.0000",
        "accuracy_province_annotation": "",
        "coherence_vocab_adherence": "1.0000",
        "coherence_vocab_adherence_annotation": "",
        "coherence_status_vocab_adherence": "1.0000",
        "coherence_status_vocab_adherence_annotation": "",
        "provenance_source_presence": "1.0000",
        "provenance_source_presence_annotation": "",
        "provenance_high_conf_dual_source": "1.0000",
        "provenance_high_conf_dual_source_annotation": "",
        "temporality_asof_presence": "1.0000",
        "temporality_asof_presence_annotation": "",
        "temporality_plausible_range": "1.0000",
        "temporality_plausible_range_annotation": "",
        "field_completeness_core": "1.0000",
        "field_completeness_core_annotation": "",
        "field_completeness_capacity": "1.0000",
        "field_completeness_capacity_annotation": "",
    }


@pytest.mark.parametrize(
    "heading",
    ["## Sources", "## References", "## Bibliography", "## Annotated Bibliography"],
)
def test_extract_bibliography_entries_heading_variants(heading):
    markdown = f"""# Report

{heading}

**[1]** First source.

2. Second source.

## Next Section
Ignored.
"""
    assert _extract_bibliography_entries(markdown) == ["First source.", "Second source."]


def test_extract_bibliography_entries_empty_section():
    markdown = "# Report\n\n## Sources\n\n## Next Section\nText.\n"
    assert _extract_bibliography_entries(markdown) == []


def test_extract_bibliography_entries_no_section():
    assert _extract_bibliography_entries("Just a table.\n| A | B |\n") == []


def test_flatten_single_turn_arm_outputs_mart_compatible_files(tmp_path):
    input_dir = tmp_path / "arm1"
    output_dir = tmp_path / "arm1_flat"
    optimised_dir = tmp_path / "optimised"
    run_dir = input_dir / "run01"
    run_dir.mkdir(parents=True)
    optimised_dir.mkdir()

    _write_json(
        run_dir / "anthropic.json",
        {
            "agent": "anthropic",
            "run": 1,
            "model": "claude-opus-4-6",
            "classification": "report",
            "tokens_out": 12,
            "wall_s": 1.2,
            "cost_usd": 0.3,
            "classifier_cost_usd": 0.01,
            "narrative_chars": 120,
        },
    )
    _write_json(
        run_dir / "anthropic-direct-claude-opus-4-6-run1.json",
        {
            "run_record": {
                "method_params": {
                    "extra": {
                        "messages": [
                            {"role": "user", "content": "prompt"},
                            {
                                "role": "assistant",
                                "content": "| A | B |\n|---|---|\n| x | y |\n\n## Bibliography\n\n**[1]** Anthropic source.",
                            },
                        ]
                    }
                }
            }
        },
    )
    _write_json(
        run_dir / "openai.json",
        {
            "agent": "openai",
            "run": 1,
            "model": "gpt-5.5",
            "classification": "report",
            "tokens_out": 14,
            "wall_s": 1.4,
            "cost_usd": 0.4,
            "classifier_cost_usd": 0.02,
            "narrative_chars": 140,
        },
    )
    _write_json(
        run_dir / "openai_probe.raw.json",
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "| A | B |\n|---|---|\n| q | z |\n\n## Sources\n\n1. OpenAI source.",
                        }
                    ],
                }
            ]
        },
    )
    _write_json(
        run_dir / "mistral.json",
        {
            "agent": "mistral",
            "run": 1,
            "model": "mistral-large-2512",
            "classification": "report",
            "tokens_out": 16,
            "wall_s": 1.6,
            "cost_usd": 0.5,
            "classifier_cost_usd": 0.03,
            "narrative_chars": 160,
        },
    )
    _write_json(
        run_dir / "mistral_probe.raw.json",
        {
            "outputs": [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "| A | B |\n|---|---|\n| m | n |\n\n## References\n\n- Mistral source.",
                        },
                        {"type": "tool_reference", "url": "https://example.com"},
                    ],
                }
            ]
        },
    )

    written = flatten_single_turn_arm(input_dir, output_dir)

    assert len(written) == 9
    anthropic_meta = json.loads((output_dir / "anthropic_run01.json").read_text(encoding="utf-8"))
    assert anthropic_meta["class_trace"] == ["report"]
    assert anthropic_meta["n_bib_entries"] == 1
    assert (output_dir / "anthropic_run01_bib.md").read_text(
        encoding="utf-8"
    ) == "- Anthropic source.\n"
    assert (output_dir / "mistral_run01_bib.md").read_text(
        encoding="utf-8"
    ) == "- Mistral source.\n"
    assert (output_dir / "openai_run01_bib.md").read_text(encoding="utf-8") == "- OpenAI source.\n"

    _write_json(
        optimised_dir / "anthropic_run01.json",
        {
            "model": "claude-opus-4-6",
            "run": 1,
            "arm": "optimised",
            "classification": "report",
            "turns": 3,
            "narrative_chars": 8,
            "total_cost_usd": 1.0,
        },
    )
    (optimised_dir / "anthropic_run01.md").write_text(
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| B | Gas | 2 | Operating | 1984 | HN |\n",
        encoding="utf-8",
    )
    probe_dir = optimised_dir / "probes" / "anthropic_run01"
    probe_dir.mkdir(parents=True)
    _write_json(probe_dir / "anthropic_turn_01.classification.json", {"class": "report"})
    _write_json(
        probe_dir / "anthropic_turn_01.raw.json",
        {"content": [{"type": "text", "text": "| B | 2 |\n"}]},
    )

    _write_cross_eval_csv(
        tmp_path / "sota_cross_eval.csv",
        [
            _score_row("naive", "claude-opus-4-6", 1),
            _score_row("naive", "gpt-5.5", 1),
            _score_row("naive", "mistral-large-2512", 1),
            _score_row("optimised", "claude-opus-4-6", 1),
        ],
    )

    records = build_exp2_mart(
        naive_dir=output_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=tmp_path / "sota_cross_eval.csv",
        repo_root=tmp_path,
    )

    run_records = [
        record for record in records if record.record_kind == "run" and record.arm == "naive"
    ]
    assert len(run_records) == 3
