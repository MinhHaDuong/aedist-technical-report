import json
from types import SimpleNamespace

from experiments.sota import exp2_naive_arm


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
