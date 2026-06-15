"""Adherence guard for ticket 0630 — citation cull.

Mechanical checks only (polarity rule, .claude/rules/writing.md §CI test polarity):
1. The cited-key count in slides/manuscript/main.tex is ≤ 30.
2. No \\cite key in main.tex references a key absent from report/refs.bib.

These are structural/mechanical invariants, not positive authorial-phrasing pins.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_TEX = REPO_ROOT / "slides" / "manuscript" / "main.tex"
REFS_BIB = REPO_ROOT / "report" / "refs.bib"

# Upper bound on cited-key count after the cull; raised slightly above 28 to
# tolerate minor future additions without requiring an immediate test update.
CITE_COUNT_CEILING = 30


def _cited_keys(tex: str) -> set[str]:
    """Return the set of distinct cite keys referenced in main.tex."""
    keys: set[str] = set()
    for m in re.finditer(r"\\cite[a-z]*\{([^}]+)\}", tex, re.DOTALL):
        for k in m.group(1).split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


def _bib_keys(bib: str) -> set[str]:
    """Return all entry keys defined in refs.bib."""
    return set(re.findall(r"@\w+\{([^,\s]+),", bib))


def test_cite_count_at_most_ceiling() -> None:
    """Cited-key count is ≤ CITE_COUNT_CEILING after ticket-0630 cull."""
    tex = MAIN_TEX.read_text(encoding="utf-8")
    keys = _cited_keys(tex)
    assert len(keys) <= CITE_COUNT_CEILING, (
        f"Expected ≤ {CITE_COUNT_CEILING} cited keys; found {len(keys)}: "
        + ", ".join(sorted(keys))
    )


def test_no_dangling_cite_keys() -> None:
    """Every \\cite key in main.tex resolves to an entry in refs.bib."""
    tex = MAIN_TEX.read_text(encoding="utf-8")
    bib = REFS_BIB.read_text(encoding="utf-8")
    cited = _cited_keys(tex)
    defined = _bib_keys(bib)
    dangling = cited - defined
    assert not dangling, (
        "Dangling \\cite keys (cited in main.tex but not in refs.bib): "
        + ", ".join(sorted(dangling))
    )


def test_culled_keys_absent() -> None:
    """The ten keys removed by ticket 0630 do not appear in main.tex."""
    culled = {
        "Singhania-Sneha2022:lm-kbc",
        "Tenckhoff-Sonke2026:llmstructbench",
        "Wu-Xianjie2025:tablebench",
        "Lin-Stephanie2022:truthfulqa",
        "Wang2022:self-consistency",
        "UN2014:fundamental-principles",
        "Eurostat2019:energy-balance-guide",
        "Xie-Tianbao2024:osworld",
        "Sun-2025:skill-aggregation",
        "HaDuong2005",
    }
    tex = MAIN_TEX.read_text(encoding="utf-8")
    cited = _cited_keys(tex)
    still_present = culled & cited
    assert not still_present, (
        "Ticket-0630-culled keys still cited in main.tex: "
        + ", ".join(sorted(still_present))
    )
