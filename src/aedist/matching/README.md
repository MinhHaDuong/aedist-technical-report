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
remaining unmatched plants. Provides `build_reconciled_row` for
merging matched pairs into a unified record.

## Usage

The package exports `reconcile_lp` from `__init__.py`. The LP matcher
is the default used by the evaluation pipeline.
