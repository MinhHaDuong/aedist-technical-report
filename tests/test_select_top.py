"""Tests for select_top — model selection from census metrics."""

import pytest

from aedist.select_top import (
    extract_slug,
    group_median_f1,
    load_registry,
    select_top_diverse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_METRICS = [
    {"label": "sweep1_census/gpt-5.4-run1", "f1": 0.65, "coverage": 0.60, "precision": 0.70, "n_matched": 42, "n_reference": 70},
    {"label": "sweep1_census/gpt-5.4-run2", "f1": 0.67, "coverage": 0.62, "precision": 0.72, "n_matched": 43, "n_reference": 70},
    {"label": "sweep1_census/gpt-5.4-run3", "f1": 0.63, "coverage": 0.58, "precision": 0.68, "n_matched": 41, "n_reference": 70},
    {"label": "sweep1_census/deepseek-v3.2-run1", "f1": 0.55, "coverage": 0.50, "precision": 0.60, "n_matched": 35, "n_reference": 70},
    {"label": "sweep1_census/deepseek-v3.2-run2", "f1": 0.57, "coverage": 0.52, "precision": 0.62, "n_matched": 36, "n_reference": 70},
    {"label": "sweep1_census/padme-qwen3.5-122b-run1", "f1": 0.50, "coverage": 0.45, "precision": 0.55, "n_matched": 32, "n_reference": 70},
    {"label": "sweep1_census/padme-qwen3.5-122b-run2", "f1": 0.48, "coverage": 0.43, "precision": 0.53, "n_matched": 30, "n_reference": 70},
    {"label": "sweep1_census/claude-opus-4.6-run1", "f1": 0.60, "coverage": 0.55, "precision": 0.65, "n_matched": 39, "n_reference": 70},
    {"label": "sweep1_census/gemini-2.5-flash-lite-run1", "f1": 0.40, "coverage": 0.35, "precision": 0.45, "n_matched": 25, "n_reference": 70},
    {"label": "sweep1_census/gpt-5-nano-run1", "f1": 0.30, "coverage": 0.25, "precision": 0.35, "n_matched": 18, "n_reference": 70},
    {"label": "sweep1_census/mistral-small-2603-run1", "f1": 0.35, "coverage": 0.30, "precision": 0.40, "n_matched": 21, "n_reference": 70},
]

SAMPLE_REGISTRY = [
    {"id": "openai/gpt-5.4", "name": "GPT-5.4", "provider": "OpenAI", "country": "US", "price_per_mtok_out": 15.0},
    {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2", "provider": "DeepSeek", "country": "CN", "price_per_mtok_out": 0.38},
    {"id": "anthropic/claude-opus-4.6", "name": "Claude Opus 4.6", "provider": "Anthropic", "country": "US", "price_per_mtok_out": 25.0},
    {"id": "google/gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "provider": "Google", "country": "US", "price_per_mtok_out": 0.4},
    {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano", "provider": "OpenAI", "country": "US", "price_per_mtok_out": 0.4},
    {"id": "mistralai/mistral-small-2603", "name": "Mistral Small 4", "provider": "Mistral", "country": "FR", "price_per_mtok_out": 0.6},
]

SAMPLE_PADME = [
    {"id": "qwen3.5:122b", "name": "Qwen 3.5 122B (local)", "provider": "Ollama/Padme", "country": "CN", "price_per_mtok_out": 0.0},
]


# ---------------------------------------------------------------------------
# extract_slug
# ---------------------------------------------------------------------------

class TestExtractSlug:
    def test_cloud_model(self):
        assert extract_slug("sweep1_census/gpt-5.4-run1") == "gpt-5.4"

    def test_padme_model(self):
        assert extract_slug("sweep1_census/padme-qwen3.5-122b-run1") == "padme-qwen3.5-122b"

    def test_multi_digit_run(self):
        assert extract_slug("sweep1_census/deepseek-v3.2-run12") == "deepseek-v3.2"

    def test_no_directory_prefix(self):
        assert extract_slug("gpt-5.4-run1") == "gpt-5.4"

    def test_complex_name_with_hyphens(self):
        assert extract_slug("sweep1_census/gemini-2.5-flash-lite-run1") == "gemini-2.5-flash-lite"

    def test_mistral_model(self):
        assert extract_slug("sweep1_census/mistral-small-2603-run1") == "mistral-small-2603"


# ---------------------------------------------------------------------------
# group_median_f1
# ---------------------------------------------------------------------------

class TestGroupMedianF1:
    def test_median_three_runs(self):
        """Median of [0.63, 0.65, 0.67] is 0.65."""
        result = group_median_f1(SAMPLE_METRICS)
        assert result["gpt-5.4"] == pytest.approx(0.65)

    def test_median_two_runs(self):
        """Median of [0.55, 0.57] is 0.56."""
        result = group_median_f1(SAMPLE_METRICS)
        assert result["deepseek-v3.2"] == pytest.approx(0.56)

    def test_single_run(self):
        """Single run → that value."""
        result = group_median_f1(SAMPLE_METRICS)
        assert result["claude-opus-4.6"] == pytest.approx(0.60)

    def test_all_models_present(self):
        result = group_median_f1(SAMPLE_METRICS)
        assert len(result) == 7  # 7 distinct model slugs


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------

class TestLoadRegistry:
    def test_cloud_slug_mapping(self):
        registry = load_registry(SAMPLE_REGISTRY, is_padme=False)
        assert "gpt-5.4" in registry
        assert "claude-opus-4.6" in registry
        assert "mistral-small-2603" in registry

    def test_padme_slug_mapping(self):
        registry = load_registry(SAMPLE_PADME, is_padme=True)
        assert "padme-qwen3.5-122b" in registry

    def test_combined_registries(self):
        cloud = load_registry(SAMPLE_REGISTRY, is_padme=False)
        padme = load_registry(SAMPLE_PADME, is_padme=True)
        combined = {**cloud, **padme}
        assert len(combined) == 7


# ---------------------------------------------------------------------------
# select_top_diverse
# ---------------------------------------------------------------------------

class TestSelectTopDiverse:
    def _make_rankings(self):
        """Build ranking + combined registry for selection tests."""
        rankings = group_median_f1(SAMPLE_METRICS)
        cloud = load_registry(SAMPLE_REGISTRY, is_padme=False)
        padme = load_registry(SAMPLE_PADME, is_padme=True)
        combined = {**cloud, **padme}
        return rankings, combined

    def test_respects_n(self):
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=3)
        assert len(selected) == 3

    def test_top_by_f1(self):
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=5)
        ids = [s["id"] for s in selected]
        # Best F1 model (gpt-5.4) must be included
        assert "openai/gpt-5.4" in ids

    def test_diversity_local(self):
        """At least one local (Padme) model included."""
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=5)
        providers = [s["provider"] for s in selected]
        assert any("Padme" in p for p in providers)

    def test_diversity_cn(self):
        """At least one Chinese model included."""
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=5)
        countries = [s["country"] for s in selected]
        assert "CN" in countries

    def test_diversity_us(self):
        """At least one US model included."""
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=5)
        countries = [s["country"] for s in selected]
        assert "US" in countries

    def test_diversity_cheap(self):
        """At least one cheap model (<$1/Mtok output) included."""
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=5)
        prices = [s["price_per_mtok_out"] for s in selected]
        assert any(p < 1.0 for p in prices)

    def test_output_has_no_internal_fields(self):
        """Output models should not have internal _slug or _median_f1 fields."""
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=3)
        for model in selected:
            assert "_slug" not in model, f"_slug leaked into output: {model}"
            assert "_median_f1" not in model, f"_median_f1 leaked into output: {model}"

    def test_n_larger_than_pool(self):
        """If n > available models, return all available."""
        rankings, combined = self._make_rankings()
        selected = select_top_diverse(rankings, combined, n=100)
        assert len(selected) == len(combined)
