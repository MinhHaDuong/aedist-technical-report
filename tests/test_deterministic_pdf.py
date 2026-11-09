"""Figure PDFs must not embed wall-clock timestamps (ticket 0574).

matplotlib stamps ``CreationDate``/``ModDate`` into every PDF unless
``SOURCE_DATE_EPOCH`` is set. ``aedist/__init__.py`` pins it, so every plot
script (all run as ``python -m aedist.plot_*``) is reproducible.
"""

import subprocess
import sys
import time

import pytest

_SNIPPET = """
import io, sys
import aedist
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([0, 1], [0, 1])
buf = io.BytesIO()
fig.savefig(buf, format="pdf", bbox_inches="tight")
sys.stdout.buffer.write(buf.getvalue())
"""


def _render() -> bytes:
    env = {k: v for k, v in __import__("os").environ.items() if k != "SOURCE_DATE_EPOCH"}
    return subprocess.run(
        [sys.executable, "-c", _SNIPPET], capture_output=True, check=True, env=env
    ).stdout


@pytest.mark.integration
def test_pdf_bytes_identical_across_runs() -> None:
    first = _render()
    time.sleep(2)  # PDF dates have 1 s resolution
    second = _render()
    assert first.startswith(b"%PDF")
    assert first == second
