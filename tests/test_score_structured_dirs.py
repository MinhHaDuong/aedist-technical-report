"""Adherence guard: every SCORE_STRUCTURED_DIRS entry must exist as a directory.

Ticket 0422. RED before the stale pre-rename entries are removed from
score.mk; GREEN after.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORE_MK = REPO_ROOT / "experiments" / "derived" / "score.mk"
OUTPUTS_DIR = REPO_ROOT / "experiments" / "outputs"


def _parse_score_structured_dirs() -> list[str]:
    text = SCORE_MK.read_text()
    m = re.search(r"SCORE_STRUCTURED_DIRS\s*:=\s*((?:[^\n\\]*\\\n)*[^\n]*)", text)
    if not m:
        return []
    raw = re.sub(r"\\\n\s*", " ", m.group(1))
    return raw.split()


@pytest.mark.parametrize("entry", _parse_score_structured_dirs())
def test_score_structured_dir_exists(entry):
    """Every SCORE_STRUCTURED_DIRS entry must be a live directory in outputs/.

    If extract has nothing to scan (record-only or dir was renamed/archived),
    the entry must be dropped from the list so it does not mislead readers or
    silently no-op.
    """
    d = OUTPUTS_DIR / entry
    assert d.is_dir(), (
        f"SCORE_STRUCTURED_DIRS entry '{entry}' does not exist under "
        f"experiments/outputs/. Rename it to the current dir name (if live "
        f"data is present) or drop it (if the dir is record-only or archived)."
    )
