"""Regression: ruff stripped make_client_for_route imports in 5/6 query modules (PR #326).

The import is used only inside ``if args.model_set:`` branches, so ruff sees
it as unused and removes it.  Python's late name resolution means the
NameError surfaces only at production runtime.  This test verifies each
module still imports the canonical function from harness.
"""

import importlib

import pytest

from aedist import harness

QUERY_MODULES = [
    "aedist.query",
    "aedist.query_direct",
    "aedist.query_rag",
    "aedist.query_multiturn",
    "aedist.query_livesearch",
    "aedist.query_per_fuel",
]


@pytest.mark.parametrize("mod_name", QUERY_MODULES)
def test_make_client_for_route_imported(mod_name):
    """Each query module must re-export make_client_for_route from harness."""
    mod = importlib.import_module(mod_name)
    assert hasattr(mod, "make_client_for_route"), (
        f"{mod_name} is missing make_client_for_route — ruff may have stripped the import"
    )
    assert mod.make_client_for_route is harness.make_client_for_route
