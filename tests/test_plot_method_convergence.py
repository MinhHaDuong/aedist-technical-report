"""Tests for aedist.plot_method_convergence — strip plot CSV data."""

import csv

from conftest import patch_measurements_loader, write_measurements

from aedist.plot_method_convergence import core_models, load_convergence_data

# Sample data: 2 models × 2 methods × 2 runs each
SAMPLE_METRICS = [
    {
        "label": "census/modelA-run1",
        "f1": 0.70,
        "n_matched": 100,
        "n_hallucinated": 5,
        "n_missed": 63,
    },
    {
        "label": "census/modelA-run2",
        "f1": 0.72,
        "n_matched": 105,
        "n_hallucinated": 3,
        "n_missed": 58,
    },
    {
        "label": "census/modelB-run1",
        "f1": 0.50,
        "n_matched": 70,
        "n_hallucinated": 0,
        "n_missed": 93,
    },
    {
        "label": "rag/modelA-run1",
        "f1": 0.90,
        "n_matched": 150,
        "n_hallucinated": 10,
        "n_missed": 13,
    },
    {
        "label": "rag/modelA-run2",
        "f1": 0.88,
        "n_matched": 145,
        "n_hallucinated": 8,
        "n_missed": 18,
    },
    {
        "label": "rag/modelB-run1",
        "f1": 0.85,
        "n_matched": 140,
        "n_hallucinated": 2,
        "n_missed": 23,
    },
    # union artifact — should be excluded
    {
        "label": "rag/modelA-union",
        "f1": 0.95,
        "n_matched": 155,
        "n_hallucinated": 1,
        "n_missed": 8,
    },
]


def test_load_excludes_artifacts(tmp_path, monkeypatch):
    """Union/consolidated artifacts are excluded from convergence data."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    models = {r["model"] for r in rows}
    assert "modelA-union" not in models


def test_load_returns_tp_fp(tmp_path, monkeypatch):
    """Each row has integer tp and fp counts."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    for r in rows:
        assert isinstance(r["tp"], int)
        assert isinstance(r["fp"], int)
        assert r["tp"] >= 0
        assert r["fp"] >= 0


def test_load_has_correct_methods(tmp_path, monkeypatch):
    """Only included methods appear in output."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    methods = {r["method"] for r in rows}
    # census maps to "direct" (new vocabulary, ticket 0120), rag stays "rag"
    assert methods <= {"direct", "rag", "direct+multiturn", "rag_livesearch"}


def test_core_models_requires_all_methods(tmp_path, monkeypatch):
    """core_models returns only models present in every method."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    core = core_models(rows)
    # modelA appears in direct + rag (2 methods), modelB in direct + rag (2 methods)
    # Neither appears in all 4 methods, so core should be empty
    assert core == set()


def test_select_min_median_max_picks_three_representatives():
    """Per-model selection surfaces the min / median / max TP rep — not top-N."""
    from aedist.plot_method_convergence import _select_min_median_max

    rows = [
        {"model": "M", "tp": 21},
        {"model": "M", "tp": 65},
        {"model": "M", "tp": 70},
        {"model": "M", "tp": 100},
        {"model": "M", "tp": 163},
    ]
    picks = _select_min_median_max(rows)
    assert [r["tp"] for r in picks] == [21, 70, 163]


def test_select_min_median_max_passthrough_for_small_groups():
    """Models with ≤3 reps are returned in TP-ascending order, no down-selection."""
    from aedist.plot_method_convergence import _select_min_median_max

    rows = [{"model": "M", "tp": 50}, {"model": "M", "tp": 10}, {"model": "M", "tp": 30}]
    picks = _select_min_median_max(rows)
    assert [r["tp"] for r in picks] == [10, 30, 50]


def test_main_writes_csv(tmp_path, monkeypatch):
    """CLI writes well-formed CSV with expected columns."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "method_convergence.csv"

    from aedist.plot_method_convergence import main

    monkeypatch.setattr("sys.argv", ["plot_method_convergence", "--output", str(output_path)])
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) > 0
    assert set(reader.fieldnames) == {"method", "model", "tp", "fp", "fn", "local", "size_class"}


def test_fp_segments_are_red(tmp_path):
    """0438: false-positive (negative-x) dots use red (COLOR_ALERT).

    Goes red on revert — if the FP scatter reverts to per-family colour,
    the negative-x collections stop matching COLOR_ALERT and this fails.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgba

    from aedist.plot_method_convergence import write_pdf
    from aedist.util import COLOR_ALERT

    rows = [{"method": "direct", "model": "modelX", "tp": 50, "fp": 7, "fn": 100}]
    alert_rgba = to_rgba(COLOR_ALERT)

    captured = {}
    orig_savefig = plt.Figure.savefig

    def _capture(self, *a, **k):
        captured["fig"] = self
        return orig_savefig(self, *a, **k)

    plt.Figure.savefig = _capture
    try:
        write_pdf(rows, tmp_path / "fig.pdf")
    finally:
        plt.Figure.savefig = orig_savefig

    ax = captured["fig"].axes[0]
    neg = [
        c
        for c in ax.collections
        if len(c.get_offsets()) and (c.get_offsets()[:, 0] < 0).all()
    ]
    assert neg, "expected at least one FP (negative-x) scatter collection"
    for coll in neg:
        colors = coll.get_edgecolor()
        if not len(colors):
            colors = coll.get_facecolor()
        for c in colors:
            assert tuple(c) == alert_rgba, (
                f"FP dots must be red (COLOR_ALERT={COLOR_ALERT}); got {tuple(c)}"
            )
    plt.close(captured["fig"])
