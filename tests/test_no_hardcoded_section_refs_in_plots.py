"""Guard against hand-typed section numbers in plot scripts (ticket 0521).

Plot scripts have no access to pandoc-crossref numbering, so any §N literal
baked into a matplotlib annotation or docstring will silently rot when sections
are reordered. Refer to concepts by name instead.
"""

import re
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "aedist"
_SECTION_REF = re.compile(r"§\d")


@pytest.mark.adherence
def test_no_section_number_literals_in_plot_scripts():
    hits: list[str] = []
    for p in sorted(_SRC.glob("plot_*.py")):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if _SECTION_REF.search(line):
                hits.append(f"{p.name}:{i}: {line.strip()}")
    assert not hits, "Hand-typed §N in plot scripts:\n" + "\n".join(hits)
