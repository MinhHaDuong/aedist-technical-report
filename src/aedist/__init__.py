"""aedist — AI-driven Energy Data Integration for Sustainable Transition."""

import os

__version__ = "0.2.0"

# Reproducible figure PDFs (ticket 0574): matplotlib's PDF backend stamps
# CreationDate/ModDate from the wall clock unless SOURCE_DATE_EPOCH is set.
# Every plot script runs as ``python -m aedist.plot_*``, so pinning it here is
# the one shared code path. 1767225600 = 2026-01-01T00:00:00Z; an explicit
# value in the caller's environment wins.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1767225600")
