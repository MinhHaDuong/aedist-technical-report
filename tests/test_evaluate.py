"""Tests for _classify_orphan in aedist.evaluate."""

import pytest

from aedist.evaluate import _classify_orphan


class TestClassifyOrphan:
    """Classify JSON-only results (no CSV companion) by status."""

    def test_prose_only_is_refusal(self):
        raw = {"model": "test", "response": "I am unable to provide this information."}
        assert _classify_orphan(raw) == "refusal"

    def test_pipe_table_is_error(self):
        raw = {
            "model": "test",
            "response": "Here is the data:\n\n| Name | Fuel |\n|---|---|\n| Pha Lai | Coal |\n",
        }
        assert _classify_orphan(raw) == "error"

    def test_fenced_csv_is_error(self):
        raw = {
            "model": "test",
            "response": "```csv\nName,Fuel\nPha Lai,Coal\n```",
        }
        assert _classify_orphan(raw) == "error"

    def test_empty_response_is_empty(self):
        raw = {"model": "test", "response": ""}
        assert _classify_orphan(raw) == "empty"

    def test_missing_response_is_empty(self):
        raw = {"model": "test"}
        assert _classify_orphan(raw) == "empty"

    def test_whitespace_only_is_empty(self):
        raw = {"model": "test", "response": "   \n  "}
        assert _classify_orphan(raw) == "empty"

    def test_multiturn_prose_is_refusal(self):
        raw = {
            "model": "test",
            "turns": [
                {"role": "user", "content": "List thermal plants"},
                {"role": "assistant", "content": "I'm sorry, I cannot produce that table."},
            ],
        }
        assert _classify_orphan(raw) == "refusal"

    def test_multiturn_with_table_is_error(self):
        raw = {
            "model": "test",
            "turns": [
                {"role": "user", "content": "List thermal plants"},
                {"role": "assistant", "content": "| Name | Fuel |\n|---|---|\n| Pha Lai | Coal |"},
            ],
        }
        assert _classify_orphan(raw) == "error"

    def test_multiturn_empty_assistant_is_empty(self):
        raw = {
            "model": "test",
            "turns": [
                {"role": "user", "content": "List thermal plants"},
                {"role": "assistant", "content": ""},
            ],
        }
        assert _classify_orphan(raw) == "empty"

    def test_inline_csv_without_fencing_is_refusal(self):
        """Inline CSV (no fenced block or pipe table) is treated as refusal.

        The fallback_extract_inline_csv heuristic is too aggressive for
        classification — comma-separated phrases in refusal prose trigger
        false positives, so we only use strong table signals.
        """
        raw = {
            "model": "test",
            "response": "Name,Fuel,Status\nPha Lai,Coal,Operating\nUong Bi,Coal,Operating\n",
        }
        assert _classify_orphan(raw) == "refusal"
