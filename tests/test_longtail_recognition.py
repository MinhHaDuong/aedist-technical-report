"""Tests for the long-tail recognition figure (tickets 0514, 0537).

The figure shows, for each of the reference plants sorted by visibility, which
recognition layers document it (Gold, GEM, Wikipedia, OSM). The plot script
reads a committed per-plant layer CSV; caption/coverage counts are re-derived
from that CSV, never hardcoded (derive-prose-from-artifacts rule).

These tests exercise the pure table-building / coverage-counting logic with
small synthetic inputs (no slow LP reconciliation), assert the layer CSV — when
generated — has one row per reference plant and the expected columns, and check
that the script carries an argparse entry point and re-derives layer totals from
the table (no hardcoded per-layer constants).
"""

import csv
import inspect
from pathlib import Path

from aedist import plot_longtail_recognition as mod
from aedist.config import LONGTAIL_LAYERS_CSV
from aedist.evaluate import reference_plant_count

_SCRIPT = Path(mod.__file__)


def _sample_rows() -> list[dict]:
    """Three plants spanning head / middle / tail visibility."""
    return [
        # documented everywhere -> head
        mod.build_row(
            0, "Alpha", "operational", in_gem=True, in_wiki=True, in_osm=True
        ),
        # GEM only -> tail
        mod.build_row(
            1, "Beta", "proposed", in_gem=True, in_wiki=False, in_osm=False
        ),
        # Gold-only (no public source) -> deep tail
        mod.build_row(
            2, "Gamma", "cancelled", in_gem=False, in_wiki=False, in_osm=False
        ),
    ]


# --- script shape -----------------------------------------------------------


def test_script_has_argparse_entry_point() -> None:
    src = _SCRIPT.read_text(encoding="utf-8")
    assert "argparse" in src
    assert "ArgumentParser" in src
    assert 'if __name__ == "__main__"' in src


def test_layer_columns_cover_the_four_layers() -> None:
    # Gold is universal (all reference plants) so it need not be a column, but
    # the three differentiating layers must each have a column.
    cols = set(mod.LAYER_COLUMNS)
    assert {"in_gem", "in_wiki", "in_osm"} <= cols
    assert "plant_id" in cols and "plant_name" in cols


def test_osm_layer_replaces_census() -> None:
    """Ticket 0537: the OSM layer replaces the language-model census layer."""
    cols = set(mod.LAYER_COLUMNS)
    assert "in_osm" in cols
    assert "census_count" not in cols
    assert "OSM" in mod._LAYER_ROWS
    assert "Census" not in mod._LAYER_ROWS
    row = mod.build_row(
        3, "Delta", "operational", in_gem=False, in_wiki=False, in_osm=True
    )
    assert row["in_osm"] == 1
    assert "census_count" not in row


def test_coverage_counts_has_osm_not_census() -> None:
    counts = mod.coverage_counts(_sample_rows())
    assert "osm" in counts
    assert "census" not in counts


# --- pure table logic -------------------------------------------------------


def test_build_row_records_layer_membership() -> None:
    row = mod.build_row(
        7, "Foo", "operational", in_gem=True, in_wiki=False, in_osm=False
    )
    assert row["plant_id"] == 7
    assert row["plant_name"] == "Foo"
    assert row["in_gem"] == 1
    assert row["in_wiki"] == 0
    assert row["in_osm"] == 0
    # every reference plant is Gold by construction
    assert row["in_gold"] == 1


def test_coverage_counts_re_derived_from_rows() -> None:
    rows = _sample_rows()
    counts = mod.coverage_counts(rows)
    assert counts["n_reference"] == 3
    assert counts["gold"] == 3  # all reference plants are Gold
    assert counts["gem"] == 2
    assert counts["wiki"] == 1
    assert counts["osm"] == 1  # only one plant present in OSM


def test_coverage_counts_internally_consistent() -> None:
    rows = _sample_rows()
    counts = mod.coverage_counts(rows)
    n = counts["n_reference"]
    # no layer can document more plants than exist, and Gold is the ceiling
    for layer in ("gold", "gem", "wiki", "osm"):
        assert 0 <= counts[layer] <= n
    assert counts["gold"] == n


def test_visibility_sort_descending_and_deterministic() -> None:
    rows = _sample_rows()
    ordered = mod.sort_by_visibility(rows)
    vis = [mod.visibility_key(r) for r in ordered]
    assert vis == sorted(vis, reverse=True)
    # head is the everywhere-documented plant, tail is the gold-only one
    assert ordered[0]["plant_name"] == "Alpha"
    assert ordered[-1]["plant_name"] == "Gamma"
    # deterministic: stable across calls
    assert [r["plant_id"] for r in mod.sort_by_visibility(rows)] == [
        r["plant_id"] for r in ordered
    ]


# --- no hardcoded layer totals in the script --------------------------------


def test_render_re_derives_counts_no_hardcoded_totals() -> None:
    """The render path must compute layer totals from the table, not literals.

    Guards the derive-prose-from-artifacts rule: 157 (GEM) and 130 (Wikipedia)
    are committed concordance numbers, but they must NOT appear as literals in
    the plotting/caption code — the figure recomputes them from the CSV.
    """
    src = inspect.getsource(mod)
    # coverage_counts must be called by the rendering / caption path
    assert "coverage_counts" in src
    for literal in ("157", "130"):
        assert literal not in src, f"hardcoded layer total {literal!r} in script"


# --- generated CSV (only if the committed artifact exists) ------------------


def test_generated_csv_has_one_row_per_plant() -> None:
    if not LONGTAIL_LAYERS_CSV.exists():
        # CSV is a generated handoff artifact; skip when not yet built.
        import pytest

        pytest.skip(f"{LONGTAIL_LAYERS_CSV} not generated")
    with LONGTAIL_LAYERS_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == reference_plant_count()
    header = set(rows[0].keys())
    assert {"plant_id", "plant_name", "in_gem", "in_wiki", "in_osm"} <= header
    assert "census_count" not in header
    # internal consistency on the real artifact
    int_rows = [
        {
            "in_gem": int(r["in_gem"]),
            "in_wiki": int(r["in_wiki"]),
            "in_osm": int(r["in_osm"]),
        }
        for r in rows
    ]
    n = len(int_rows)
    assert sum(r["in_gem"] for r in int_rows) <= n
    assert sum(r["in_wiki"] for r in int_rows) <= n
    assert sum(r["in_osm"] for r in int_rows) <= n
