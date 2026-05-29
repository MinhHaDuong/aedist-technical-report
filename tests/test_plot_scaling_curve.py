"""Tests for aedist.plot_scaling_curve data collection."""

from types import SimpleNamespace

from aedist.plot_scaling_curve import (
    _CLOUD_REFS_FALLBACK,
    _compute_cloud_refs,
    collect_data,
)


def _rec(method: str, model: str, f1, pv=None):
    return SimpleNamespace(
        method=SimpleNamespace(value=method),
        method_params=SimpleNamespace(model=model, prompt_version=pv),
        result_summary=SimpleNamespace(f1=f1),
    )


def test_collect_data_groups_by_family_method_params(monkeypatch) -> None:
    records = [
        _rec("direct", "qwen3.5:2b", 0.5),
        _rec("rag", "qwen3.5:2b", 0.6),
        _rec("direct", "gemma4:e4b", 0.4),
        _rec("direct", "unknown-model", 0.9),  # not in lookup -> ignored
        _rec("direct", "qwen3.5:2b", None),  # no f1 -> ignored
        _rec("direct", "qwen3.5:2b", 0.7, pv="_extracted"),  # extracted -> ignored
        _rec("multiturn", "qwen3.5:2b", 0.8),  # other method -> ignored
    ]
    monkeypatch.setattr("aedist.plot_scaling_curve.load", lambda: records)

    data = collect_data()
    assert data["Qwen 3.5"]["direct"][2] == [0.5]
    assert data["Qwen 3.5"]["rag"][2] == [0.6]
    assert data["Gemma 4"]["direct"][4] == [0.4]


def test_compute_cloud_refs_falls_back_when_no_data(monkeypatch) -> None:
    monkeypatch.setattr("aedist.plot_scaling_curve.load", lambda: [])
    assert _compute_cloud_refs() == dict(_CLOUD_REFS_FALLBACK)


def test_compute_cloud_refs_takes_max_per_slug_and_strips_run_suffix(monkeypatch) -> None:
    records = [
        _rec("rag", "gpt-5.4-run1", 0.80),
        _rec("rag", "gpt-5.4-run2", 0.90),  # best for the gpt-5.4 slug
        _rec("rag", "qwen3.5:2b", 0.99),  # local model -> excluded
        _rec("direct", "gpt-5.4-run3", 0.95),  # not rag -> excluded
    ]
    monkeypatch.setattr("aedist.plot_scaling_curve.load", lambda: records)
    assert _compute_cloud_refs() == {"gpt-5.4 (best run)": 0.90}
