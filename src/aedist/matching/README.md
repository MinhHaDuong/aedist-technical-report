# matching

Match LLM-extracted power plants against the reference table. Used by
`reconcile.py` to compute precision, coverage, and F1 scores.

## Algorithms

### `lp.py` — Linear programming matcher

Formulates plant matching as a mixed-integer linear program (MILP).
Builds a binary assignment matrix over candidate pairs scored by name
similarity (fuzzy string matching) and capacity closeness. Solves for
the optimal one-to-one assignment.

### `phased.py` — Phased matcher

Two-pass approach: exact name matches first, then fuzzy matching on
remaining unmatched plants.

### `common.py` — Shared helpers

Provides `build_result_row` for assembling a reconciliation dict from
a pair of matched/unmatched plant rows. Used by both matchers.

## Usage

The package exports `reconcile_lp` from `__init__.py`. The LP matcher
is the default used by the evaluation pipeline.
