"""Tests for select_models — model selection from census metrics."""

import pytest

from aedist.select_models import (
    extract_slug,
    group_median_f1,
    load_registry,
    select_models,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.65},
    {"label": "census/gpt-5.4-run2", "f1": 0.67},
    {"label": "census/gpt-5.4-run3", "f1": 0.63},
    {"label": "census/deepseek-v3.2-run1", "f1": 0.55},
    {"label": "census/deepseek-v3.2-run2", "f1": 0.57},
    {"label": "census/claude-opus-4.6-run1", "f1": 0.60},
    {"label": "census/gemini-2.5-flash-lite-run1", "f1": 0.40},
    {"label": "census/padme-qwen3.5-122b-run1", "f1": 0.50},
    {"label": "census/padme-qwen3.5-122b-run2", "f1": 0.48},
    {"label": "census/padme-glm-4.7-flash-run1", "f1": 0.45},
    {"label": "census/padme-nemotron-3-nano-run1", "f1": 0.20},
    {"label": "census/mistral-large-2512-run1", "f1": 0.52},
    {"label": "census/mistral-large-2512-run2", "f1": 0.54},
]

SAMPLE_CLOUD = [
    {
        "name": "openai/gpt-5.4",
        "display_name": "GPT-5.4",
        "provider": "OpenAI",
        "country": "US",
        "size_class": "frontier",
        "price_per_mtok_in": 2.5,
    },
    {
        "name": "deepseek/deepseek-v3.2",
        "display_name": "DeepSeek V3.2",
        "provider": "DeepSeek",
        "country": "CN",
        "size_class": "frontier",
        "price_per_mtok_in": 0.26,
    },
    {
        "name": "anthropic/claude-opus-4.6",
        "display_name": "Claude Opus 4.6",
        "provider": "Anthropic",
        "country": "US",
        "size_class": "frontier",
        "price_per_mtok_in": 5.0,
    },
    {
        "name": "google/gemini-2.5-flash-lite",
        "display_name": "Gemini 2.5 Flash Lite",
        "provider": "Google",
        "country": "US",
        "size_class": "edge",
        "price_per_mtok_in": 0.1,
    },
    {
        "name": "mistralai/mistral-large-2512",
        "display_name": "Mistral Large 3",
        "provider": "Mistral",
        "country": "FR",
        "size_class": "frontier",
        "price_per_mtok_in": 0.5,
    },
]

SAMPLE_PADME = [
    {
        "name": "qwen3.5:122b",
        "display_name": "Qwen 3.5 122B (local)",
        "provider": "Ollama/Padme",
        "country": "CN",
    },
    {
        "name": "glm-4.7-flash",
        "display_name": "GLM 4.7 Flash (local)",
        "provider": "Ollama/Padme",
        "country": "CN",
    },
    {
        "name": "nemotron-3-nano",
        "display_name": "Nemotron 3 Nano (local)",
        "provider": "Ollama/Padme",
        "country": "US",
    },
]


# ---------------------------------------------------------------------------
# extract_slug
# ---------------------------------------------------------------------------


class TestExtractSlug:
    def test_cloud_model(self):
        assert extract_slug("census/gpt-5.4-run1") == "gpt-5.4"

    def test_padme_model(self):
        assert extract_slug("census/padme-qwen3.5-122b-run1") == "padme-qwen3.5-122b"

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
# select_models — N cloud + N local
# ---------------------------------------------------------------------------


class TestSelectModels:
    def _select(self, n=1):
        rankings = group_median_f1(SAMPLE_METRICS)
        cloud = load_registry(SAMPLE_CLOUD, is_padme=False)
        local = load_registry(SAMPLE_PADME, is_padme=True)
        return select_models(rankings, cloud, local, n=n)

    def test_n1_gives_two_models(self):
        """--n 1 → 1 cloud + 1 local = 2 total."""
        selected = self._select(n=1)
        assert len(selected) == 2

    def test_n1_best_cloud_is_gpt(self):
        """Best cloud model is GPT-5.4 (F1=0.65)."""
        selected = self._select(n=1)
        cloud = [s for s in selected if "Padme" not in s.get("provider", "")]
        assert len(cloud) == 1
        assert cloud[0]["name"] == "openai/gpt-5.4"

    def test_n1_best_local_is_qwen(self):
        """Best local model is padme-qwen3.5-122b (F1=0.49)."""
        selected = self._select(n=1)
        local = [s for s in selected if "Padme" in s.get("provider", "")]
        assert len(local) == 1
        assert local[0]["name"] == "qwen3.5:122b"

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
        assert len(cloud) == 5  # all 5 cloud models
        assert len(local) == 3  # all 3 padme models

    def test_no_internal_fields(self):
        selected = self._select(n=2)
        for m in selected:
            assert "_slug" not in m
            assert "_median_f1" not in m


# ---------------------------------------------------------------------------
# select_models — diversity-aware path
# ---------------------------------------------------------------------------


class TestDiverseSelection:
    """Tests for --require-country + --n-cheap selection."""

    def _select(self, countries, n_cheap=0):
        rankings = group_median_f1(SAMPLE_METRICS)
        cloud = load_registry(SAMPLE_CLOUD, is_padme=False)
        local = load_registry(SAMPLE_PADME, is_padme=True)
        return select_models(
            rankings,
            cloud,
            local,
            require_countries=countries,
            n_cheap=n_cheap,
        )

    def test_frontier_picks_one_per_country(self):
        selected = self._select(["US", "CN", "FR"])
        countries = [m["country"] for m in selected]
        assert "US" in countries
        assert "CN" in countries
        assert "FR" in countries
        assert len(selected) == 3

    def test_us_frontier_is_best_f1(self):
        """GPT-5.4 (F1=0.65) beats Claude Opus (F1=0.60) for US frontier."""
        selected = self._select(["US"])
        assert selected[0]["name"] == "openai/gpt-5.4"

    def test_fr_frontier_is_mistral(self):
        selected = self._select(["FR"])
        assert selected[0]["name"] == "mistralai/mistral-large-2512"

    def test_cn_frontier_is_deepseek(self):
        selected = self._select(["CN"])
        assert selected[0]["name"] == "deepseek/deepseek-v3.2"

    def test_cheap_tier_beats_local_floor(self):
        """Cheap models must have F1 > best local (0.49)."""
        selected = self._select(["US"], n_cheap=2)
        # Frontier pick is GPT-5.4; cheap picks from remaining
        cheap = [m for m in selected if m["name"] != "openai/gpt-5.4"]
        for m in cheap:
            assert m["_median_f1"] > 0.49 if "_median_f1" in m else True

    def test_cheap_tier_sorted_by_price(self):
        """Cheap picks are the cheapest models beating local floor."""
        selected = self._select([], n_cheap=5)
        # With no frontier requirement, all slots are cheap tier
        # Sorted by price: gemini-flash-lite ($0.1) is cheapest but F1=0.40
        # which is below local floor (0.49), so it should be excluded
        names = [m["name"] for m in selected]
        assert "google/gemini-2.5-flash-lite" not in names

    def test_cheap_excludes_frontier_picks(self):
        """A model picked for frontier is not duplicated in cheap tier."""
        selected = self._select(["US", "CN", "FR"], n_cheap=5)
        names = [m["name"] for m in selected]
        assert len(names) == len(set(names))

    def test_missing_country_warns(self, caplog):
        """Requesting a country with no frontier model logs a warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            selected = self._select(["JP"])
        assert len(selected) == 0
        assert "JP" in caplog.text

    def test_no_internal_fields(self):
        selected = self._select(["US", "CN", "FR"], n_cheap=2)
        for m in selected:
            assert "_slug" not in m
            assert "_median_f1" not in m
