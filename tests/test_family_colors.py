"""Unit tests for the language-family color helper (ticket 0194).

The helper ``aedist.util.family_color`` is the single function any plot
script may call to colour-code a model by its language family
(EN / FR / ZH). Tests pin down:

- Same-family models share a colour.
- Different families produce different colours.
- Unknown models fall back to the neutral hue.
- Direct family codes (``"EN"``, etc.) round-trip.
"""

from aedist.util import family_color


def test_en_models_share_color():
    assert family_color("anthropic/claude-opus-4.6") == family_color("openai/gpt-5.5")


def test_en_vs_fr_differ():
    assert family_color("anthropic/claude-opus-4.6") != family_color(
        "mistralai/mistral-large-2512"
    )


def test_fr_vs_zh_differ():
    assert family_color("mistralai/mistral-large-2512") != family_color("deepseek/deepseek-v3.2")


def test_zh_models_share_color():
    # Two different ZH labs, same family
    assert family_color("deepseek/deepseek-v3.2") == family_color("qwen/qwen3-max-thinking")


def test_unknown_model_returns_fallback():
    # Hand-crafted slug that matches no provider and no prefix
    fallback = family_color("not-a-real-model-zzz")
    # Same call returns the same colour, and it is the documented gray fallback.
    assert fallback == family_color("another-unknown-slug-zzz")
    assert fallback == "#999999"


def test_direct_family_codes():
    en = family_color("EN")
    fr = family_color("FR")
    zh = family_color("ZH")
    assert en != fr and fr != zh and en != zh
    # Should match what a slug-derived call returns
    assert family_color("anthropic/claude-opus-4.6") == en
    assert family_color("mistralai/mistral-large-2512") == fr
    assert family_color("qwen/qwen3-max-thinking") == zh


def test_provider_prefix_stripped():
    # Same raw model resolved with or without the openrouter prefix
    assert family_color("openrouter/deepseek-v3.2") == family_color("deepseek-v3.2")


def test_empty_input_returns_fallback():
    assert family_color("") == "#999999"


def test_returns_hex_string():
    val = family_color("EN")
    assert isinstance(val, str)
    assert val.startswith("#")
    assert len(val) == 7
