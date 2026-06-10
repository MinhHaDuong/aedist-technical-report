"""Repo public-readiness files: LICENCE, CITATION.cff, README, pyproject.

These guard the artifacts created when the repo went public before the arXiv
deposit (ticket 0510). The licence is CC BY 4.0 (Attribution, NO ShareAlike).
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TITLE = (
    "Can Frontier AI Build a Statistical Register? "
    "A Benchmark and Research Programme on Vietnam's Thermal Power Fleet"
)
EXPECTED_ORCID = "https://orcid.org/0000-0001-9988-2100"


def test_licence_file_is_cc_by_4():
    licence = REPO_ROOT / "LICENCE"
    assert licence.exists(), "LICENCE file must exist at repo root"
    text = licence.read_text(encoding="utf-8")
    assert "Attribution 4.0" in text, "LICENCE must be CC BY 4.0"
    assert "ShareAlike" not in text, "CC BY 4.0 must NOT carry a ShareAlike clause"


def test_citation_cff_valid_and_correct():
    cff_path = REPO_ROOT / "CITATION.cff"
    assert cff_path.exists(), "CITATION.cff must exist at repo root"
    data = yaml.safe_load(cff_path.read_text(encoding="utf-8"))

    assert data["cff-version"] == "1.2.0"
    assert data["title"] == EXPECTED_TITLE
    assert data["license"] == "CC-BY-4.0"

    authors = data["authors"]
    assert isinstance(authors, list) and len(authors) == 1
    author = authors[0]
    assert author["family-names"] == "Ha-Duong"
    assert author["given-names"] == "Minh"
    assert author["orcid"] == EXPECTED_ORCID


def test_readme_license_section_is_public():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "All rights reserved" not in readme, (
        "README must not claim 'All rights reserved' once public"
    )
    # Positive claim: the public licence is named with a link.
    assert "CC BY 4.0" in readme
    assert "creativecommons.org/licenses/by/4.0" in readme


def test_pyproject_license_is_cc_by_4():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = { text = "CC-BY-4.0" }' in pyproject
    assert "CC-BY-SA-4.0" not in pyproject
