"""Ticket 0254 — Exp2 « Jeu de données et statistiques descriptives » section.

The section fills §sec:exp2-sota:donnees in report/report.tex from committed,
post-re-baseline artifacts only. This adherence test pins the load-bearing
invariants the ticket's FIRST TEST spec demands:

1. The Claude-optimised 0/5 exclusion prose must name the *dimension* — the
   exclusion is bibliography-parse validity (n_rows>0 in the bib parser), NOT
   F1-scorability (the 2x2 cell still scores Claude optimised at 5/5). A flat
   "Claude excluded" would contradict the F1 table; the dimension word must be
   present.
2. The unregistered with-docs arms (arm3/arm4) must be labelled « exploratoire »
   so they are never silently mixed with the two registered arms.
3. Every \\includegraphics target the section adds must exist in
   inputs/generated/ (no dangling figure include).

The checks read report.tex source (and the build-time PDF when present) rather
than re-deriving numbers, so they stay fast and offline.
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_TEX = REPO_ROOT / "report" / "report.tex"
GENERATED = REPO_ROOT / "report" / "inputs" / "generated"


def _donnees_section() -> str:
    """The text of §sec:exp2-sota:donnees up to the next \\section."""
    text = REPORT_TEX.read_text(encoding="utf-8")
    start = text.index(r"\label{sec:exp2-sota:donnees}")
    rest = text[start:]
    nxt = rest.index(r"\section{", 1)
    return rest[:nxt]


def test_section_exists_and_nonempty():
    section = _donnees_section()
    # More than the bare stub TODO line.
    body = section.replace("% TODO", "").strip()
    assert len(body) > 400, "donnees section is still a stub"


def test_exclusion_names_the_parse_dimension():
    section = _donnees_section().lower()
    assert "0/5" in section or "0\\,/\\,5" in section, "Claude-optimised 0/5 fraction absent"
    # The exclusion dimension must be named: bibliography/inventory parsing.
    assert any(
        token in section for token in ("parsable", "parsabilit", "n_rows", "analyse de la bibliograph", "parsing")
    ), "0/5 exclusion does not name the bib-parse dimension"
    # And it must distinguish from F1-scorability (the cell stays 5/5).
    assert "f1" in section, "section must reference the F1 scorability path it does NOT exclude on"


def test_with_docs_arms_labelled_exploratory():
    section = _donnees_section().lower()
    assert "exploratoire" in section, "arm3/arm4 (with-docs) not labelled exploratoire"


def test_registered_two_arms_named():
    section = _donnees_section().lower()
    assert "naïf" in section or "naif" in section
    assert "optimisé" in section or "optimise" in section


def test_includegraphics_targets_exist():
    section = _donnees_section()
    for match in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", section):
        target = match.group(1)
        # Resolve relative to report/ root; allow with/without extension.
        candidates = [
            (REPO_ROOT / "report" / target),
            (REPO_ROOT / "report" / (target + ".pdf")),
        ]
        assert any(c.exists() for c in candidates), f"missing figure target: {target}"


def test_no_orphan_outline_or_view_artifacts():
    section = _donnees_section()
    assert "tab_exp2_outline_dataset" not in section, "must not ship the <to fill> placeholder"
    assert "_view" not in section, "full-DAG *_view artifacts are banned in the writing build"


@pytest.mark.integration
def test_pdf_renders_exclusion_prose():
    """When the report PDF is present, confirm the exclusion prose survived typesetting."""
    pdf = REPO_ROOT / "report" / "report.pdf"
    if not pdf.exists():
        pytest.skip("report.pdf not built")
    try:
        text = subprocess.run(
            ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("pdftotext unavailable")
    assert "exploratoire" in text.lower()
    assert "0/5" in text
