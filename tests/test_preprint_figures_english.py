"""Preprint figures must be in English (ticket 0455).

Author directive (2026-06-06): every figure included by the arXiv preprint
(``slides/manuscript/main.tex``) must be English. This ratchets that invariant
by extracting the text layer of each figure PDF the manuscript includes and
asserting none of a set of *discriminating* French label strings appears.

Only unsuffixed PDFs (the ones main.tex includes) are checked. The ``_fr``
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
MAIN_TEX = REPO_ROOT / "slides" / "manuscript" / "main.tex"

# \includegraphics[...]{path.pdf} — figure includes (the \includepdf
# recognition matrix is checked too; it is English by construction but cheap
# to scan).
_IMG_RE = re.compile(r"\\include(?:graphics|pdf)(?:\[[^\]]*\])?\{([^}]+?\.pdf)\}")

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
    """Every figure PDF referenced by main.tex, resolved to an absolute path.

    Tectonic resolves includes relative to the input file's directory, so the
    ``../../report/...`` paths in main.tex resolve relative to
    ``slides/manuscript/``.
    """
    text = MAIN_TEX.read_text(encoding="utf-8")
    base = MAIN_TEX.parent  # slides/manuscript/ — tectonic's resolution root
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
    assert pdfs, "no figure includes found in main.tex — parse regression"

    violations: list[str] = []
    for pdf in pdfs:
        assert pdf.exists(), f"main.tex includes a missing figure: {pdf}"
        # Suffixed _fr variants are intentionally French; main.tex never includes
        # them, but guard anyway in case the include list ever changes.
        if pdf.stem.endswith("_fr"):
            continue
        text = _pdf_text(pdf)
        found = sorted({label for label in FRENCH_LABELS if label in text})
        if found:
            violations.append(f"{pdf.name}: {', '.join(found)}")

    assert not violations, (
        "French label strings found in preprint figure(s) included by main.tex "
        "(figures must be English, ticket 0455):\n"
        + "\n".join(f"  {v}" for v in violations)
    )
