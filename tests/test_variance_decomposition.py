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


def test_empty_records():
    """Empty input returns zero-filled result."""
    from aedist.variance_decomposition import variance_decomposition

    result = variance_decomposition([])
    assert result["n_records"] == 0
    assert result["n_groups"] == 0
    assert result["eta_sq_model"] == 0.0


def test_filtered_out_records():
    """Records with error status or None F1 are excluded."""
    from aedist.variance_decomposition import variance_decomposition

    records = [
        RunRecord(
            method="rag",
            method_params=MethodParams(model="A", prompt_version="test"),
            resource_use=ResourceUse(),
            result_file="test.csv",
            result_summary=ResultSummary(status="error", f1=0.9, n_plants=10, tp=5, fp=0, fn=5),
        ),
        RunRecord(
            method="rag",
            method_params=MethodParams(model="B", prompt_version="test"),
            resource_use=ResourceUse(),
            result_file="test.csv",
            result_summary=ResultSummary(status="ok", f1=None),
        ),
    ]
    result = variance_decomposition(records)
    assert result["n_records"] == 0


def test_balanced_subdesign_selection():
    """The largest balanced sub-design is found even with sparse cells.

    With 3 models x 2 methods fully crossed, plus a 4th model in only 1 method,
    the ANOVA should use the 3x2 cross (not collapse to nothing).
    """
    from aedist.variance_decomposition import variance_decomposition

    records = []
    # 3 models x 2 methods, 2 replicates each
    for model in ["A", "B", "C"]:
        for method in ["rag", "single"]:
            for f1 in [0.70, 0.80]:
                records.append(make_record(model, method, f1))
    # 4th model in only 1 method — should be excluded from the cross
    records.append(make_record("D", "rag", 0.60))
    records.append(make_record("D", "rag", 0.65))

    result = variance_decomposition(records)
    assert result["n_groups"] == 6  # 3 models x 2 methods


def test_one_way_model_fallback():
    """Single-method data falls back to one-way ANOVA on model."""
    from aedist.variance_decomposition import variance_decomposition

    records = [
        make_record("A", "rag", 0.90),
        make_record("A", "rag", 0.85),
        make_record("B", "rag", 0.50),
        make_record("B", "rag", 0.55),
    ]
    result = variance_decomposition(records)
    assert result["eta_sq_model"] > 0.90
    assert result["eta_sq_method"] == 0.0


def test_ss_partition():
    """SS components sum to SS total in the ANOVA output."""
    from aedist.variance_decomposition import two_way_anova

    data = {
        ("A", "x"): [10.0, 12.0],
        ("A", "y"): [8.0, 6.0],
        ("B", "x"): [2.0, 4.0],
        ("B", "y"): [3.0, 5.0],
    }
    result = two_way_anova(data)
    ss_sum = result["ss_a"] + result["ss_b"] + result["ss_ab"] + result["ss_resid"]
    assert abs(ss_sum - result["ss_total"]) < 1e-10


def test_omega_squared_present():
    """Two-way ANOVA returns omega-squared values."""
    from aedist.variance_decomposition import two_way_anova

    data = {
        ("A", "x"): [10.0, 12.0],
        ("A", "y"): [8.0, 6.0],
        ("B", "x"): [2.0, 4.0],
        ("B", "y"): [3.0, 5.0],
    }
    result = two_way_anova(data)
    assert "omega_sq_a" in result
    assert "omega_sq_b" in result
    assert "omega_sq_ab" in result
    assert result["omega_sq_a"] >= 0
    assert result["omega_sq_b"] >= 0
    assert result["omega_sq_ab"] >= 0


def test_f_statistics_present():
    """Two-way ANOVA returns F-statistics and p-values."""
    from aedist.variance_decomposition import two_way_anova

    data = {
        ("A", "x"): [10.0, 12.0],
        ("A", "y"): [8.0, 6.0],
        ("B", "x"): [2.0, 4.0],
        ("B", "y"): [3.0, 5.0],
    }
    result = two_way_anova(data)
    for key in ["f_a", "f_b", "f_ab", "p_a", "p_b", "p_ab"]:
        assert key in result
    assert all(result[k] >= 0 for k in ["f_a", "f_b", "f_ab"])
    assert all(0 <= result[k] <= 1 for k in ["p_a", "p_b", "p_ab"])


def test_large_f_gives_small_p():
    """A large effect should produce a large F and small p-value."""
    from aedist.variance_decomposition import two_way_anova

    data = {
        ("A", "x"): [100.0, 101.0],
        ("A", "y"): [100.0, 101.0],
        ("B", "x"): [1.0, 2.0],
        ("B", "y"): [1.0, 2.0],
    }
    result = two_way_anova(data)
    assert result["f_a"] > 10
    assert result["p_a"] < 0.05


def test_subdesign_composition_in_output():
    """Variance decomposition output includes sub-design composition."""
    from aedist.variance_decomposition import variance_decomposition

    records = []
    for model in ["A", "B"]:
        for method in ["rag", "single"]:
            for f1 in [0.70, 0.80]:
                records.append(make_record(model, method, f1))
    result = variance_decomposition(records)
    assert "models_included" in result
    assert "methods_included" in result
    assert "n_records_excluded" in result
    assert set(result["models_included"]) == {"A", "B"}
    assert set(result["methods_included"]) == {"rag", "single"}


def test_omega_squared_in_decomposition():
    """Variance decomposition output includes omega-squared."""
    from aedist.variance_decomposition import variance_decomposition

    records = []
    for model in ["A", "B"]:
        for method in ["rag", "single"]:
            for f1 in [0.70, 0.80]:
                records.append(make_record(model, method, f1))
    result = variance_decomposition(records)
    assert "omega_sq_model" in result
    assert "omega_sq_method" in result
    assert "omega_sq_interaction" in result
