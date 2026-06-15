"""Tickets 0607, 0608, 0610 — §3 prose tightening.

Negative guards only (CI polarity rule, ticket 0557):
- 0607: old §3 opener "Datasets can be assessed on four dimensions" is gone.
- 0608: old phrasing "The decomposition compresses three" is gone.
- 0610: dropped closing paragraph signature "The task is not simply to generate
  a plausible inventory-shaped answer" is absent from the body.
"""

import pytest
from manuscript_source import body

pytestmark = pytest.mark.adherence


def test_old_s3_opener_absent() -> None:
    """0607: generic opener replaced; old phrasing must not reappear."""
    assert "Datasets can be assessed on four dimensions" not in body(), (
        "old §3 opener 'Datasets can be assessed on four dimensions' must be "
        "absent — replaced by 'We benchmark model-produced datasets …' (ticket 0607)"
    )


def test_old_decomposition_compresses_absent() -> None:
    """0608: 'compresses three' replaced by 'draws on'; old form must not reappear."""
    assert "The decomposition compresses three" not in body(), (
        "old phrasing 'The decomposition compresses three' must be absent — "
        "replaced by 'draws on' (ticket 0608)"
    )


def test_dropped_s3_closing_paragraph_absent() -> None:
    """0610: redundant §3 closing paragraph dropped; signature phrase must be gone."""
    assert "The task is not simply to generate a plausible inventory-shaped answer" not in body(), (
        "dropped §3 closing paragraph signature must be absent from the body "
        "(ticket 0610)"
    )
