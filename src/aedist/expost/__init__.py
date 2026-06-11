"""Ex post extraction helpers for EXP3 derived outputs (ticket 0292).

Standalone home for the derivation logic previously inlined in
``experiments/sota/exp2_naive_arm.py``: source-section rendering,
numbered-bibliography parsing, Source-cell citation resolution with an
audit trail, and preamble stripping. The P2 extractors
(``aedist.extract_arm_single_turn`` / ``aedist.extract_arm_multi_turn``)
and the acquisition scripts both import from here so the data flow is
unified across arms.
"""

from .sources import (
    append_sources_section,
    parse_numbered_bibliography,
    render_mistral_content_with_sources,
    resolve_source_cells,
    strip_preamble,
)

__all__ = [
    "append_sources_section",
    "parse_numbered_bibliography",
    "render_mistral_content_with_sources",
    "resolve_source_cells",
    "strip_preamble",
]
