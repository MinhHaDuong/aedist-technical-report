"""Tests for select_sweep2 — model selection from census metrics."""

import pytest

from aedist.select_sweep2 import (
    extract_slug,
    group_median_f1,
    load_registry,
    select_sweep2,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_METRICS = [
    {"label": "sweep1_census/gpt-5.4-run1", "f1": 0.65},
    {"label": "sweep1_census/gpt-5.4-run2", "f1": 0.67},
    {"label": "sweep1_census/gpt-5.4-run3", "f1": 0.63},
    {"label": "sweep1_census/deepseek-v3.2-run1", "f1": 0.55},
    {"label": "sweep1_census/deepseek-v3.2-run2", "f1": 0.57},
    {"label": "sweep1_census/claude-opus-4.6-run1", "f1": 0.60},
    {"label": "sweep1_census/gemini-2.5-flash-lite-run1", "f1": 0.40},
    {"label": "sweep1_census/padme-qwen3.5-122b-run1", "f1": 0.50},
    {"label": "sweep1_census/padme-qwen3.5-122b-run2", "f1": 0.48},
    {"label": "sweep1_census/padme-glm-4.7-flash-run1", "f1": 0.45},
    {"label": "sweep1_census/padme-nemotron-3-nano-run1", "f1": 0.20},
]

SAMPLE_CLOUD = [
    {"id": "openai/gpt-5.4", "name": "GPT-5.4", "provider": "OpenAI", "country": "US"},
    {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2", "provider": "DeepSeek", "country": "CN"},
    {"id": "anthropic/claude-opus-4.6", "name": "Claude Opus 4.6", "provider": "Anthropic", "country": "US"},
    {"id": "google/gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "provider": "Google", "country": "US"},
]

SAMPLE_PADME = [
    {"id": "qwen3.5:122b", "name": "Qwen 3.5 122B (local)", "provider": "Ollama/Padme", "country": "CN"},
    {"id": "glm-4.7-flash", "name": "GLM 4.7 Flash (local)", "provider": "Ollama/Padme", "country": "CN"},
    {"id": "nemotron-3-nano", "name": "Nemotron 3 Nano (local)", "provider": "Ollama/Padme", "country": "US"},
]


# ---------------------------------------------------------------------------
# extract_slug
# ---------------------------------------------------------------------------

class TestExtractSlug:
    def test_cloud_model(self):
        assert extract_slug("sweep1_census/gpt-5.4-run1") == "gpt-5.4"

    def test_padme_model(self):
        assert extract_slug("sweep1_census/padme-qwen3.5-122b-run1") == "padme-qwen3.5-122b"

    def test_no_directory(self):
        assert extract_slug("gpt-5.4-run1") == "gpt-5.4"


# ---------------------------------------------------------------------------
# group_median_f1
# ---------------------------------------------------------------------------

class TestGroupMedianF1:
    def test_median_three_runs(self):
        result = group_median_f1(SAMPLE_METRICS)
        assert result["gpt-5.4"] == pytest.approx(0.65)

    def test_median_two_runs(self):
        result = group_median_f1(SAMPLE_METRICS)
        assert result["deepseek-v3.2"] == pytest.approx(0.56)

    def test_single_run(self):
        result = group_median_f1(SAMPLE_METRICS)
        assert result["claude-opus-4.6"] == pytest.approx(0.60)


# ---------------------------------------------------------------------------
# select_sweep2 — N cloud + N local
# ---------------------------------------------------------------------------

class TestSelectSweep2:
    def _select(self, n=1):
        rankings = group_median_f1(SAMPLE_METRICS)
        cloud = load_registry(SAMPLE_CLOUD, is_padme=False)
        local = load_registry(SAMPLE_PADME, is_padme=True)
        return select_sweep2(rankings, cloud, local, n=n)

    def test_n1_gives_two_models(self):
        """--n 1 → 1 cloud + 1 local = 2 total."""
        selected = self._select(n=1)
        assert len(selected) == 2

    def test_n1_best_cloud_is_gpt(self):
        """Best cloud model is GPT-5.4 (F1=0.65)."""
        selected = self._select(n=1)
        cloud = [s for s in selected if "Padme" not in s.get("provider", "")]
        assert len(cloud) == 1
        assert cloud[0]["id"] == "openai/gpt-5.4"

    def test_n1_best_local_is_qwen(self):
        """Best local model is padme-qwen3.5-122b (F1=0.49)."""
        selected = self._select(n=1)
        local = [s for s in selected if "Padme" in s.get("provider", "")]
        assert len(local) == 1
        assert local[0]["id"] == "qwen3.5:122b"

    def test_n2_gives_four_models(self):
        """--n 2 → 2 cloud + 2 local = 4 total."""
        selected = self._select(n=2)
        assert len(selected) == 4
        cloud = [s for s in selected if "Padme" not in s.get("provider", "")]
        local = [s for s in selected if "Padme" in s.get("provider", "")]
        assert len(cloud) == 2
        assert len(local) == 2

    def test_n_larger_than_pool(self):
        """If n > available, return all available per track."""
        selected = self._select(n=100)
        cloud = [s for s in selected if "Padme" not in s.get("provider", "")]
        local = [s for s in selected if "Padme" in s.get("provider", "")]
        assert len(cloud) == 4  # all 4 cloud models
        assert len(local) == 3  # all 3 padme models

    def test_no_internal_fields(self):
        selected = self._select(n=2)
        for m in selected:
            assert "_slug" not in m
            assert "_median_f1" not in m
