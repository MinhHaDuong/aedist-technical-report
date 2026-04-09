"""Tests for unstable ranking flags in tabulate_comparaison."""

from aedist.tabulate_comparaison import generate_comparaison_table


# Two models with nearly identical F1 — should be flagged as "not robust"
CLOSE_PAIR_METRICS = [
    # Census runs for model-A (F1 ~0.65)
    {"label": "census/model-a-run1", "coverage": 0.50, "f1": 0.64},
    {"label": "census/model-a-run2", "coverage": 0.51, "f1": 0.66},
    {"label": "census/model-a-run3", "coverage": 0.49, "f1": 0.65},
    # RAG runs for model-A (F1 ~0.72)
    {"label": "rag/model-a-run1", "coverage": 0.55, "f1": 0.71},
    {"label": "rag/model-a-run2", "coverage": 0.56, "f1": 0.73},
    {"label": "rag/model-a-run3", "coverage": 0.54, "f1": 0.72},
    # Census runs for model-b (F1 ~0.65, very close to model-A)
    {"label": "census/model-b-run1", "coverage": 0.49, "f1": 0.63},
    {"label": "census/model-b-run2", "coverage": 0.50, "f1": 0.67},
    {"label": "census/model-b-run3", "coverage": 0.50, "f1": 0.65},
    # RAG runs for model-b (F1 ~0.72, very close to model-A)
    {"label": "rag/model-b-run1", "coverage": 0.54, "f1": 0.71},
    {"label": "rag/model-b-run2", "coverage": 0.55, "f1": 0.73},
    {"label": "rag/model-b-run3", "coverage": 0.54, "f1": 0.72},
]

# Two models with well-separated F1 — should NOT be flagged
SEPARATED_PAIR_METRICS = [
    # Census runs for model-a (F1 ~0.65)
    {"label": "census/model-a-run1", "coverage": 0.50, "f1": 0.64},
    {"label": "census/model-a-run2", "coverage": 0.51, "f1": 0.66},
    {"label": "census/model-a-run3", "coverage": 0.49, "f1": 0.65},
    # RAG runs for model-a (F1 ~0.72)
    {"label": "rag/model-a-run1", "coverage": 0.55, "f1": 0.71},
    {"label": "rag/model-a-run2", "coverage": 0.56, "f1": 0.73},
    {"label": "rag/model-a-run3", "coverage": 0.54, "f1": 0.72},
    # Census runs for model-c (F1 ~0.40, well separated)
    {"label": "census/model-c-run1", "coverage": 0.30, "f1": 0.39},
    {"label": "census/model-c-run2", "coverage": 0.31, "f1": 0.41},
    {"label": "census/model-c-run3", "coverage": 0.30, "f1": 0.40},
    # RAG runs for model-c (F1 ~0.50, well separated)
    {"label": "rag/model-c-run1", "coverage": 0.35, "f1": 0.49},
    {"label": "rag/model-c-run2", "coverage": 0.36, "f1": 0.51},
    {"label": "rag/model-c-run3", "coverage": 0.35, "f1": 0.50},
]


def test_close_pair_flagged_not_robust():
    """Model pairs with <5pp F1 difference and overlapping CIs get 'not robust' flag."""
    latex, n = generate_comparaison_table(CLOSE_PAIR_METRICS)
    assert n == 2
    assert "not robust" in latex.lower()


def test_separated_pair_not_flagged():
    """Well-separated model pairs do not get 'not robust' flag."""
    latex, n = generate_comparaison_table(SEPARATED_PAIR_METRICS)
    assert n == 2
    assert "not robust" not in latex.lower()
