"""Regression test: query_*.py modules must use Ollama native /api/chat.

Ticket 0155 — guards against re-introducing the bug (pre-d27c393) where
query_direct.py and query_multiturn.py called query_single_turn for Ollama
models, silently ignoring num_ctx via the OpenAI /v1/ shim.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# ---------------------------------------------------------------------------
# Registry: deliberate friction for new query modules
# ---------------------------------------------------------------------------

OLLAMA_DISPATCH = {"query_direct", "query_multiturn", "query_rag"}
NO_OLLAMA_DISPATCH = {
    "query",
    "query_fusion",
    "query_livesearch",
    "query_per_fuel",
    "query_verification",
}


@pytest.mark.adherence
def test_all_query_modules_registered():
    """New query_*.py must be in OLLAMA_DISPATCH or NO_OLLAMA_DISPATCH."""
    query_dir = Path(__file__).parent.parent / "src" / "aedist"
    discovered = {p.stem for p in query_dir.glob("query*.py")}
    registered = OLLAMA_DISPATCH | NO_OLLAMA_DISPATCH
    unregistered = discovered - registered
    assert not unregistered, (
        f"Unregistered query module(s): {unregistered}. "
        f"Add to OLLAMA_DISPATCH (uses query_ollama_native) or "
        f"NO_OLLAMA_DISPATCH in tests/test_ollama_native_api.py."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ollama_response():
    resp = MagicMock()
    resp.json.return_value = {
        "message": {"content": "Plant A,coal,100,operating", "role": "assistant"},
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "eval_count": 50,
    }
    resp.raise_for_status = MagicMock()
    return resp


def _ollama_model(context_window=32768):
    return {
        "id": "test-ollama:9b",
        "name": "Test Ollama 9B",
        "router": "ollama",
        "router_model": "test-ollama:9b",
        "context_window": context_window,
        "price_per_mtok_in": 0,
        "price_per_mtok_out": 0,
        "country": "CN",
        "architecture": "dense",
        "size_class": "edge",
    }


def _write_models_yaml(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(yaml.dump([_ollama_model()]))
    return p


def _write_prompt(tmp_path, text="List power plants."):
    p = tmp_path / "prompt.txt"
    p.write_text(text)
    return p


def _assert_ollama_native_call(mock_httpx_post):
    assert mock_httpx_post.call_count >= 1, "httpx.post never called — Ollama dispatch failed"
    url = mock_httpx_post.call_args[0][0]
    payload = mock_httpx_post.call_args[1]["json"]
    assert url.endswith("/api/chat"), f"Expected /api/chat, got {url}"
    assert "num_ctx" in payload.get("options", {}), (
        f"num_ctx missing from options: {payload.get('options')}"
    )
    assert payload["stream"] is False
    return payload


# ---------------------------------------------------------------------------
# Base function: query_ollama_native
# ---------------------------------------------------------------------------


def test_query_ollama_native_url_and_options():
    from aedist.harness import query_ollama_native

    with patch("httpx.post", return_value=_ollama_response()) as mock_post:
        result = query_ollama_native(
            "http://localhost:11434/v1",
            "test-ollama:9b",
            [{"role": "user", "content": "hello"}],
            num_ctx=32768,
        )

    payload = _assert_ollama_native_call(mock_post)
    assert payload["options"]["num_ctx"] == 32768
    assert result["content"] == "Plant A,coal,100,operating"


def test_query_ollama_native_strips_v1():
    from aedist.harness import query_ollama_native

    with patch("httpx.post", return_value=_ollama_response()) as mock_post:
        query_ollama_native(
            "http://localhost:11434/v1",
            "m",
            [{"role": "user", "content": "x"}],
            num_ctx=8192,
        )

    assert mock_post.call_args[0][0] == "http://localhost:11434/api/chat"


def test_query_ollama_native_num_predict():
    from aedist.harness import query_ollama_native

    with patch("httpx.post", return_value=_ollama_response()) as mock_post:
        query_ollama_native(
            "http://localhost:11434/v1",
            "m",
            [{"role": "user", "content": "x"}],
            num_ctx=16384,
            num_predict=4096,
        )

    assert mock_post.call_args[1]["json"]["options"]["num_predict"] == 4096


# ---------------------------------------------------------------------------
# Per-module dispatch: query_direct
# ---------------------------------------------------------------------------


@patch("httpx.post")
@patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"})
def test_query_direct_ollama_uses_native_api(mock_httpx_post, tmp_path):
    # patch.dict keeps make_client() intact so query_direct.make_client is
    # never bound to a MagicMock (which would pollute later tests via sys.modules)
    mock_httpx_post.return_value = _ollama_response()
    _write_models_yaml(tmp_path)
    _write_prompt(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with patch.object(
        sys,
        "argv",
        [
            "query_direct",
            "--models",
            str(tmp_path / "models.yaml"),
            "--prompt",
            str(tmp_path / "prompt.txt"),
            "--output",
            str(output_dir),
            "--repeat",
            "1",
            "--budget-usd",
            "10",
            "--max-tokens",
            "4096",
        ],
    ):
        from aedist.query_direct import main

        main()

    _assert_ollama_native_call(mock_httpx_post)


# ---------------------------------------------------------------------------
# Per-module dispatch: query_multiturn
# ---------------------------------------------------------------------------


@patch("httpx.post")
@patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"})
def test_query_multiturn_ollama_uses_native_api(mock_httpx_post, tmp_path):
    mock_httpx_post.return_value = _ollama_response()
    _write_models_yaml(tmp_path)
    _write_prompt(tmp_path)
    followups = tmp_path / "followups.txt"
    followups.write_text("")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with patch.object(
        sys,
        "argv",
        [
            "query_multiturn",
            "--prompt",
            str(tmp_path / "prompt.txt"),
            "--followups",
            str(followups),
            "--models",
            str(tmp_path / "models.yaml"),
            "--output",
            str(output_dir),
            "--repeat",
            "1",
            "--budget-usd",
            "10",
        ],
    ):
        from aedist.query_multiturn import main

        main()

    _assert_ollama_native_call(mock_httpx_post)


# ---------------------------------------------------------------------------
# Per-module dispatch: query_rag
# ---------------------------------------------------------------------------


@patch("httpx.post")
@patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"})
def test_query_rag_ollama_uses_native_api(mock_httpx_post, tmp_path):
    mock_httpx_post.return_value = _ollama_response()
    _write_models_yaml(tmp_path)
    _write_prompt(tmp_path)
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "ref.md").write_text("# Reference\nPlant A uses coal, 100 MW, operating.")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with patch.object(
        sys,
        "argv",
        [
            "query_rag",
            "--prompt",
            str(tmp_path / "prompt.txt"),
            "--corpus",
            str(corpus_dir),
            "--models",
            str(tmp_path / "models.yaml"),
            "--output",
            str(output_dir),
            "--repeat",
            "1",
            "--budget-usd",
            "10",
        ],
    ):
        from aedist.query_rag import main

        main()

    _assert_ollama_native_call(mock_httpx_post)
