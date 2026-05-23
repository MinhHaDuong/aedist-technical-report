import json
import re
from types import SimpleNamespace

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
