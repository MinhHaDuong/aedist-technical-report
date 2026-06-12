"""Guard against silent row loss in the committed Exp2 cross-eval CSV.

The score.mk recipe wraps each score_mechanical call in `|| true`, so a
parse failure surfaces only as a missing row (ticket 0550: 4 claude-opus
runs vanished when strip_preamble dropped a fused header line). This test
re-derives the expected run set from the committed flat artifacts and
asserts the CSV covers it exactly.
"""

import csv
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DERIVED = REPO_ROOT / "experiments" / "derived"
CROSS_EVAL_CSV = DERIVED / "sota_cross_eval.csv"

ARM_DIRS = {
    "naive": "arm1_flat",
    "optimised": "arm2_flat",
    "arm3": "arm3_flat",
    "arm4": "arm4_flat",
}


def expected_runs() -> set[tuple[str, str, str]]:
    runs = set()
    for arm, dirname in ARM_DIRS.items():
        for path in (DERIVED / dirname).glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            model = payload.get("model")
            run = payload.get("run")
            if model is None or run is None:
                continue  # audit sidecars and other non-run JSON
            runs.add((arm, str(model), str(run)))
    return runs


@pytest.mark.adherence
def test_cross_eval_covers_every_committed_run():
    expected = expected_runs()
    assert expected, "no run JSONs found under experiments/derived/arm*_flat"
    with CROSS_EVAL_CSV.open(encoding="utf-8") as fh:
        rows = [(r["arm"], r["model"], r["run"]) for r in csv.DictReader(fh)]
    assert len(rows) == len(set(rows)), "duplicate (arm, model, run) rows"
    missing = expected - set(rows)
    extra = set(rows) - expected
    assert not missing, f"runs missing from sota_cross_eval.csv: {sorted(missing)}"
    assert not extra, f"rows without a committed run JSON: {sorted(extra)}"
