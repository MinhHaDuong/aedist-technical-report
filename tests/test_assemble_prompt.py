"""Tests for the post-rename ``assemble_prompt`` contract (ticket 0175).

The new contract:
- ``2_goal`` and ``5_table`` are always included (the ``ALWAYS_MODULES`` pair).
- Caller-supplied ``module_names`` are unioned with the always-pair.
- The result is assembled in filename lex order, joined with ``"\\n\\n"``.
- Unknown names raise ``ValueError``.
"""

from pathlib import Path

import pytest

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
MODULES_DIR = EXPERIMENTS_DIR / "prompts" / "modules"


def _content(stem: str) -> str:
    return (MODULES_DIR / f"{stem}.txt").read_text().strip()


def test_empty_list_yields_goal_plus_table_only():
    """assemble_prompt(modules_dir, []) returns 2_goal + 5_table, in order, joined by blank line."""
    from aedist.harness import assemble_prompt

    result = assemble_prompt(MODULES_DIR, [])
    expected = _content("2_goal") + "\n\n" + _content("5_table")
    assert result == expected


def test_optional_modules_assembled_in_lex_order():
    """assemble_prompt unions caller's list with the always-pair, lex-sorts by filename."""
    from aedist.harness import assemble_prompt

    result = assemble_prompt(MODULES_DIR, ["A_Statistics", "1_persona"])
    # Lex order: 1_persona, 2_goal, 5_table, A_Statistics
    expected = "\n\n".join(
        [
            _content("1_persona"),
            _content("2_goal"),
            _content("5_table"),
            _content("A_Statistics"),
        ]
    )
    assert result == expected


def test_unknown_name_raises_value_error():
    """assemble_prompt raises ValueError on names that don't resolve to a file."""
    from aedist.harness import assemble_prompt

    with pytest.raises(ValueError, match="Unknown prompt modules"):
        assemble_prompt(MODULES_DIR, ["does_not_exist"])


def test_always_pair_not_duplicated_when_explicitly_listed():
    """Listing 2_goal or 5_table explicitly does not duplicate them in the output."""
    from aedist.harness import assemble_prompt

    a = assemble_prompt(MODULES_DIR, [])
    b = assemble_prompt(MODULES_DIR, ["2_goal", "5_table"])
    assert a == b


def test_build_messages_no_system_returns_user_only():
    """build_messages with no system_instruction returns a single user message."""
    from aedist.harness import build_messages

    msgs = build_messages("hello", None)
    assert msgs == [{"role": "user", "content": "hello"}]


def test_build_messages_with_system_prepends_system_role():
    """build_messages with non-empty system_instruction prepends a system message."""
    from aedist.harness import build_messages

    msgs = build_messages("hello", "do not search")
    assert msgs == [
        {"role": "system", "content": "do not search"},
        {"role": "user", "content": "hello"},
    ]


def test_build_messages_empty_system_treated_as_none():
    """Empty-string system_instruction is treated as no system message."""
    from aedist.harness import build_messages

    msgs = build_messages("hello", "")
    assert msgs == [{"role": "user", "content": "hello"}]
