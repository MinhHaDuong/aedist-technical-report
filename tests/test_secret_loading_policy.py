"""Secret-loading policy adherence guard (ticket 0240).

Policy (documented in experiments/common.mk):
- API keys live in the project ``.env`` file.
- The ``UV_RUN`` Make variable injects them via ``uv run --env-file ../.env``.
- Source code reads keys only from its environment (``os.environ.get``).
- Source code **must not** call ``load_dotenv()`` — that couples library
  code to a file-loading side-effect.
- Source code **must not** read key files from ``~/.config/keys/`` or any
  other hardcoded path — that silently bypasses the Make-level injection.

Approved exceptions
-------------------
The following modules pre-date the policy consolidation (ticket 0240) and
contain file-fallback key loading. They are allowlisted here so the guard
passes on current code; the intent is to shrink this list in follow-up work.

- ``adapter_mistral.py`` — reads ``~/.config/keys/mistral.env``
- ``adapter_openai_responses.py`` — reads ``~/.config/keys/openai.env``
- ``adapter_qwen_dashscope.py`` — reads ``~/.config/keys/alibaba.env``
- ``query_anthropic.py`` — accepts ``--key-file`` defaulting to
  ``~/.config/keys/anthropic.env``
- ``prototype_v1_verify_agent.py`` — reads ``~/.claude/.env`` (pre-policy
  prototype; never wired into the main pipeline)

Any new module exhibiting these patterns must be explicitly added here or
the pattern eliminated; adding an exception is a conscious decision, not
drift.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "aedist"

# ── patterns that violate the policy ─────────────────────────────────────────

# ``load_dotenv()`` calls (python-dotenv) — couples library code to a file path.
_LOAD_DOTENV_RE = re.compile(r"\bload_dotenv\s*\(")

# Direct reads of a key file under any absolute home-relative path such as
# ``~/.config/keys/…`` or ``Path.home() / ".config" / "keys" / …`` or
# ``Path.home() / ".claude" / ".env"``.
_KEY_FILE_RE = re.compile(
    r"""
    (?:
        ["']~[/\\]\.config[/\\]keys     # literal "~/.config/keys..."
        | ["']~[/\\]\.claude[/\\]       # literal "~/.claude/..."
        | [Pp]ath\.home\(\)\s*/\s*["']\.config["']   # Path.home() / ".config"
        | [Pp]ath\.home\(\)\s*/\s*["']\.claude["']   # Path.home() / ".claude"
    )
    """,
    re.VERBOSE,
)

# ── allowlist: filenames exempt from the guard ───────────────────────────────

APPROVED_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "adapter_mistral.py",
        "adapter_openai_responses.py",
        "adapter_qwen_dashscope.py",
        "query_anthropic.py",
        "prototype_v1_verify_agent.py",
    }
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _source_files() -> list[Path]:
    return sorted(SRC_DIR.glob("*.py"))


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """Return (lineno, text) for lines that are not full-line comments."""
    result: list[tuple[int, str]] = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue  # skip full-line comments — doc prose is fine
        result.append((i, line))
    return result


def _scan(pattern: re.Pattern[str]) -> list[str]:
    """Return violation strings for all non-allowlisted files matching *pattern*."""
    violations: list[str] = []
    for src in _source_files():
        if src.name in APPROVED_EXCEPTIONS:
            continue
        for lineno, line in _code_lines(src):
            if pattern.search(line):
                violations.append(
                    f"{src.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}"
                )
    return violations


# ── tests ─────────────────────────────────────────────────────────────────────


def test_no_load_dotenv():
    """No ``load_dotenv()`` call in non-allowlisted src/aedist modules."""
    violations = _scan(_LOAD_DOTENV_RE)
    assert not violations, (
        f"{len(violations)} load_dotenv() call(s) — "
        "use ``uv run --env-file ../.env`` at the Make level instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_key_file_reads():
    """No direct key-file reads (``~/.config/keys/…`` or ``~/.claude/…``) in
    non-allowlisted src/aedist modules."""
    violations = _scan(_KEY_FILE_RE)
    assert not violations, (
        f"{len(violations)} key-file read(s) outside approved adapters — "
        "read from the environment (``os.environ.get``) instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


# ── positive controls: detector must not pass on known violations ─────────────


def test_detector_catches_load_dotenv():
    """_LOAD_DOTENV_RE must fire on a seeded violation string."""
    fixture = "load_dotenv()"
    assert _LOAD_DOTENV_RE.search(fixture), (
        "Detector regex did not match seeded load_dotenv() string — regex is broken"
    )


def test_detector_catches_config_keys_literal():
    """_KEY_FILE_RE must fire on a ``~/.config/keys/`` literal."""
    fixture = 'key_file = "~/.config/keys/mistral.env"'
    assert _KEY_FILE_RE.search(fixture), (
        "Detector regex did not match seeded ~/.config/keys/ literal — regex is broken"
    )


def test_detector_catches_path_home_config():
    """_KEY_FILE_RE must fire on the ``Path.home() / ".config"`` pattern."""
    fixture = 'path = Path.home() / ".config" / "keys" / "foo.env"'
    assert _KEY_FILE_RE.search(fixture), (
        'Detector regex did not match seeded Path.home() / ".config" pattern — regex is broken'
    )


def test_detector_catches_path_home_claude():
    """_KEY_FILE_RE must fire on the ``Path.home() / ".claude"`` pattern."""
    fixture = 'env_file = Path.home() / ".claude" / ".env"'
    assert _KEY_FILE_RE.search(fixture), (
        'Detector regex did not match seeded Path.home() / ".claude" pattern — regex is broken'
    )
