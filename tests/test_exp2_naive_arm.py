import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from experiments.sota import exp2_naive_arm
from experiments.sota.exp2_naive_arm import _write_summary_md


def test_write_summary_md_timestamped_filename(tmp_path):
    summary = [
        {
            "agent": "mistral",
            "run": 1,
            "model": "m",
            "classification": "report",
            "cost_usd": 0.1,
            "wall_s": 5.0,
            "narrative_chars": 100,
        },
        {
            "agent": "openai",
            "run": 1,
            "model": "o",
            "classification": "report",
            "cost_usd": 0.2,
            "wall_s": 8.0,
            "narrative_chars": 200,
        },
    ]
    path = _write_summary_md(tmp_path, summary)
    assert re.match(r"summary_\d{8}T\d{4}Z_mistral_openai\.md", path.name)
    content = path.read_text(encoding="utf-8")
    assert "mistral" in content
    assert "openai" in content


def test_probe_mistral_parses_flat_string_content(monkeypatch, tmp_path):
    class _Record(SimpleNamespace):
        resource_use = SimpleNamespace(cost_usd=0.12, tokens_out=42)
        tool_calls_cost_usd = 0.0

    def fake_run(prompt, *, output_path, **kwargs):  # noqa: ARG001
        output_path.write_text(
            json.dumps({"outputs": [{"type": "message.output", "content": "stub narrative"}]})
        )
        return _Record()

    monkeypatch.setattr(exp2_naive_arm, "load_model_meta", lambda family: {"model_id": family})
    monkeypatch.setattr("aedist.adapter_mistral.run", fake_run)

    result = exp2_naive_arm.probe_mistral("prompt", tmp_path)

    assert result["narrative"] == "stub narrative"
    assert result["cost_usd"] == 0.12


# ---------------------------------------------------------------------------
# Regression guards — must pass before and after the --evidence-pack-manifest patch
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "experiments" / "evidence_packs" / "all18tables.yaml"


def _fake_result() -> dict:
    return {
        "narrative": "## Inventory\n| Plant | Cap |\n|---|---|\n| TestPlant | 500 MW |",
        "cost_usd": 0.01,
        "tokens_out": 50,
        "wall_s": 1.0,
        "model": "test-model-id",
    }


@pytest.fixture()
def patched_probers(monkeypatch):
    """Replace all probers with stubs; return dict mapping agent → prompt received."""
    from experiments.sota import dialogue_classifier

    captured: dict[str, str] = {}

    def make_prober(name: str):
        def prober(prompt: str, output_dir: Path) -> dict:
            captured[name] = prompt
            return _fake_result()

        return prober

    monkeypatch.setattr(
        exp2_naive_arm, "PROBERS", {a: make_prober(a) for a in exp2_naive_arm.AGENTS}
    )

    mock_cls = MagicMock()
    mock_cls.class_ = "report"
    mock_cls.classifier_cost_usd = 0.0
    monkeypatch.setattr(dialogue_classifier, "classify_report", lambda _: mock_cls)

    return captured


def test_load_naive_prompt_returns_nonempty_string():
    prompt = exp2_naive_arm.load_naive_prompt()
    assert isinstance(prompt, str) and len(prompt) > 100


def test_load_naive_prompt_strips_meta_framing():
    prompt = exp2_naive_arm.load_naive_prompt()
    assert not prompt.startswith("This is the prompt")
    assert not prompt.startswith("---")


def test_main_without_manifest_passes_baseline_prompt(patched_probers, tmp_path):
    expected = exp2_naive_arm.load_naive_prompt()
    exp2_naive_arm.main(["--agents", "mistral", "--n", "1", "--output-dir", str(tmp_path)])
    assert patched_probers["mistral"] == expected


# ---------------------------------------------------------------------------
# TDD tests — currently FAILING; pass after the --evidence-pack-manifest patch
# ---------------------------------------------------------------------------


def test_main_accepts_evidence_pack_manifest_flag(patched_probers, tmp_path):
    ret = exp2_naive_arm.main(
        [
            "--agents",
            "mistral",
            "--n",
            "1",
            "--output-dir",
            str(tmp_path),
            "--evidence-pack-manifest",
            str(MANIFEST_PATH),
        ]
    )
    assert ret == 0


def test_main_with_manifest_augments_prompt(patched_probers, tmp_path):
    exp2_naive_arm.main(
        [
            "--agents",
            "mistral",
            "--n",
            "1",
            "--output-dir",
            str(tmp_path),
            "--evidence-pack-manifest",
            str(MANIFEST_PATH),
        ]
    )
    assert "# Evidence pack" in patched_probers["mistral"]
    assert "Chunk 1" in patched_probers["mistral"]


def test_main_without_manifest_prompt_not_augmented(patched_probers, tmp_path):
    exp2_naive_arm.main(["--agents", "mistral", "--n", "1", "--output-dir", str(tmp_path)])
    assert "# Evidence pack" not in patched_probers["mistral"]


def test_meta_record_includes_manifest_when_set(patched_probers, tmp_path):
    exp2_naive_arm.main(
        [
            "--agents",
            "mistral",
            "--n",
            "1",
            "--output-dir",
            str(tmp_path),
            "--evidence-pack-manifest",
            str(MANIFEST_PATH),
        ]
    )
    record = json.loads((tmp_path / "mistral.json").read_text())
    assert record.get("evidence_pack_manifest") == str(MANIFEST_PATH)
