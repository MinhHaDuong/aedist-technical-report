"""Structural guard for ``.claude/rules-map.toml`` (ticket 0677).

The manifest maps path globs to doctype/lang axes for the review routing
(``prose_predicate.py --axes``); it holds mappings only, never rule text.
Resolution behaviour is tested upstream in the harness; this only keeps the
file parseable and well-formed.
"""

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANIFEST = Path(__file__).resolve().parent.parent / ".claude" / "rules-map.toml"
AXES = {"doctype", "lang"}


def _load() -> dict:
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_is_valid_toml() -> None:
    assert isinstance(_load(), dict)


def test_default_lang_is_set() -> None:
    lang = _load().get("default_lang")
    assert isinstance(lang, str) and lang


def test_each_map_entry_has_string_glob_and_known_keys() -> None:
    entries = _load().get("map", [])
    assert entries, "manifest declares no [[map]] entry"
    for entry in entries:
        assert isinstance(entry.get("glob"), str) and entry["glob"]
        assert set(entry) <= {"glob"} | AXES
        assert all(isinstance(entry[a], str) for a in AXES & set(entry))
