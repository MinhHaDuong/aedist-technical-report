"""Preprint figures must be in English (ticket 0455).

Author directive (2026-06-06): every figure included by the arXiv preprint
(``slides/manuscript/main.md``) must be English. This ratchets that invariant
by extracting the text layer of each figure PDF the manuscript includes and
asserting none of a set of *discriminating* French label strings appears.

Only unsuffixed PDFs (the ones main.md includes) are checked. The ``_fr``
variants that feed the French conference deck (slides.tex) are deliberately
French and must NOT be checked here.

Discriminating tokens only: words that are unambiguously French in this corpus
(``Exactitude``, ``Combustible``, ``carré``, ...). Tokens that collide with
English (``Source``, ``Province``, ``Date``, ``correct``) are excluded to avoid
false positives.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"

# Markdown image syntax: ![...](path). We resolve relative to main.md's dir.
_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+?\.pdf)\)")

# French label strings that genuinely land in these figures' text layers and do
# not collide with English. Derived from the pre-fix pdftotext dump (0455).
FRENCH_LABELS = [
    "Exactitude",
    "Combustible",
    "Vocabulaire",
    "respecté",
    "Cohérence",
    "Temporalité",
    "Répartition",
    "Diversité",
    "Actifs trouvés",
    "Actifs corrects",
    "correcte",
    "Profil de qualité",
    "Expérience",
    "carré",
    "avec documents",
    "sans documents",
]


def _included_figure_pdfs() -> list[Path]:
    """Every figure PDF referenced by main.md, resolved to an absolute path.

    Pandoc builds from ``slides/`` (cwd) with ``--resource-path=.``, so the
    ``../report/...`` paths in main.md resolve relative to ``slides/``, not to
    main.md's own directory.
    """
    text = MAIN_MD.read_text(encoding="utf-8")
    base = MAIN_MD.parent.parent  # slides/ — pandoc's working directory
    return [(base / rel.strip()).resolve() for rel in _IMG_RE.findall(text)]


def _pdf_text(pdf: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not available")
def test_preprint_figures_have_no_french_labels():
    pdfs = _included_figure_pdfs()
    assert pdfs, "no figure includes found in main.md — parse regression"

    violations: list[str] = []
    for pdf in pdfs:
        assert pdf.exists(), f"main.md includes a missing figure: {pdf}"
        # Suffixed _fr variants are intentionally French; main.md never includes
        # them, but guard anyway in case the include list ever changes.
        if pdf.stem.endswith("_fr"):
            continue
        text = _pdf_text(pdf)
        found = sorted({label for label in FRENCH_LABELS if label in text})
        if found:
            violations.append(f"{pdf.name}: {', '.join(found)}")

    assert not violations, (
        "French label strings found in preprint figure(s) included by main.md "
        "(figures must be English, ticket 0455):\n"
        + "\n".join(f"  {v}" for v in violations)
    )
