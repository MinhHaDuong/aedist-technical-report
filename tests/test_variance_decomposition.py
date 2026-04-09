"""Tests for aedist.variance_decomposition — two-way ANOVA on F1 scores."""

from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord


def make_record(model: str, method: str, f1: float) -> RunRecord:
    """Create a minimal RunRecord for variance decomposition tests."""
    return RunRecord(
        method=method,
        method_params=MethodParams(model=model, prompt_version="test"),
        resource_use=ResourceUse(),
        result_file=f"test/{model}-{method}.csv",
        result_summary=ResultSummary(status="ok", f1=f1, n_plants=10, tp=5, fp=0, fn=5),
    )


def make_close_pair_records(
    f1_a: float = 0.92, f1_b: float = 0.915, spread: float = 0.04
) -> list[RunRecord]:
    """Create records for two models with overlapping F1 distributions.

    Defaults chosen so that with 12 samples per model the bootstrap CIs
    overlap and the mean difference is < 5 pp.
    """
    import random

    rng = random.Random(42)
    records = []
    for method in ["single", "rag", "multiturn", "web"]:
        for _ in range(3):
            records.append(make_record("model-A", method, f1_a + rng.uniform(-spread, spread)))
            records.append(make_record("model-B", method, f1_b + rng.uniform(-spread, spread)))
    return records


def test_variance_decomposition_perfect_separation():
    """When groups are perfectly separated, eta_sq_between ~ 1.0."""
    from aedist.variance_decomposition import variance_decomposition

    records = [
        make_record(model="A", method="rag", f1=0.90),
        make_record(model="A", method="rag", f1=0.91),
        make_record(model="B", method="rag", f1=0.50),
        make_record(model="B", method="rag", f1=0.51),
    ]
    result = variance_decomposition(records)
    assert result["eta_sq_residual"] < 0.05


def test_variance_decomposition_pure_noise():
    """When all groups have same mean, eta_sq_between ~ 0.0."""
    from aedist.variance_decomposition import variance_decomposition

    records = [
        make_record(model="A", method="rag", f1=v) for v in [0.70, 0.90, 0.80]
    ] + [make_record(model="B", method="rag", f1=v) for v in [0.72, 0.88, 0.82]]
    result = variance_decomposition(records)
    assert result["eta_sq_model"] < 0.10


def test_unstable_pair_detection():
    """Pairs with overlapping CIs flagged as unstable."""
    from aedist.variance_decomposition import variance_decomposition

    records = make_close_pair_records(f1_a=0.92, f1_b=0.915, spread=0.04)
    result = variance_decomposition(records)
    assert len(result["unstable_pairs"]) > 0
