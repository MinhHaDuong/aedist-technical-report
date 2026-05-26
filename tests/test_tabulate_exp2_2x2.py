"""Aggregation logic for the Exp2 2x2 factorial table.

Agent is the unit of replication; factor effects are within-agent contrasts
averaged across agents that have the metric in all four arms. F1 and cost are
assessed independently, so an agent missing F1 in the multi-turn arms can still
anchor the cost contrast.
"""

import math

from aedist.tabulate_exp2_2x2 import (
    cell_table,
    collapse_runs,
    factor_effects,
    render_tex,
)


def _rec(agent, arm, run, f1, cost):
    return {"arm": arm, "agent": agent, "model": agent, "run": str(run), "cost": cost, "f1": f1}


def _render_inputs():
    cell = {"f1_mean": 0.5, "f1_sd": 0.1, "cost_ratio": 1.0, "cost_abs": 0.65}
    cells = {a: dict(cell) for a in ("naive", "optimised", "arm3", "arm4")}
    eff = {k: {"effect": 0.1, "k_positive": 3, "n": 4} for k in ("docs", "mode", "interaction")}
    return cells, eff, dict(eff)


def test_render_tex_lang_switches_labels():
    cells, f1_eff, cost_eff = _render_inputs()
    en = render_tex(cells, f1_eff, cost_eff, lang="en")
    fr = render_tex(cells, f1_eff, cost_eff, lang="fr")
    assert "Without docs" in en and "Single query" in en
    assert "Sans documents" in fr and "Requête unique" in fr
    assert "Without docs" not in fr
    # numbers are locale-neutral and identical across languages
    assert "0.500" in en and "0.500" in fr
    assert en.strip().endswith("\\end{tabular}")


def _f1_records():
    # a1, a2 complete on F1; a3 missing F1 in the multi-turn arms.
    data = {
        "a1": {"naive": 0.5, "optimised": 0.4, "arm3": 0.7, "arm4": 0.6},
        "a2": {"naive": 0.3, "optimised": 0.2, "arm3": 0.5, "arm4": 0.5},
        "a3": {"naive": 0.4, "optimised": None, "arm3": 0.6, "arm4": None},
    }
    recs = []
    for agent, arms in data.items():
        for arm, f1 in arms.items():
            recs.append(_rec(agent, arm, 1, f1, cost=1.0))
    return recs


def test_collapse_runs_averages_and_counts():
    recs = [
        _rec("a1", "naive", 1, 0.4, 1.0),
        _rec("a1", "naive", 2, 0.6, 3.0),
        _rec("a1", "naive", 3, None, 2.0),  # unscored run still has cost
    ]
    collapsed = collapse_runs(recs)
    cell = collapsed[("a1", "naive")]
    assert cell["f1_mean"] == 0.5  # mean of 0.4, 0.6
    assert cell["n_f1"] == 2
    assert cell["n_total"] == 3
    assert cell["cost_mean"] == 2.0  # mean of 1, 3, 2


def test_f1_docs_effect_and_consistency():
    eff = factor_effects(collapse_runs(_f1_records()), "f1_mean", log_scale=False)
    docs = eff["docs"]
    # a1: 0.65-0.45=0.20 ; a2: 0.50-0.25=0.25 ; a3 excluded (incomplete)
    assert docs["n"] == 2
    assert "a3" not in docs["per_agent"]
    assert math.isclose(docs["mean"], 0.225)
    assert docs["k_positive"] == 2  # both agents positive


def test_f1_interaction_sign_split():
    eff = factor_effects(collapse_runs(_f1_records()), "f1_mean", log_scale=False)
    inter = eff["interaction"]
    # a1: 0.0 ; a2: +0.1 -> mean 0.05, only one strictly positive
    assert math.isclose(inter["mean"], 0.05)
    assert inter["k_positive"] == 1
    assert inter["n"] == 2


def test_cost_effect_is_multiplicative_ratio():
    # one agent, costs double with docs: naive=1, optimised=2, arm3=2, arm4=4
    recs = [
        _rec("a1", "naive", 1, 0.5, 1.0),
        _rec("a1", "optimised", 1, 0.5, 2.0),
        _rec("a1", "arm3", 1, 0.5, 2.0),
        _rec("a1", "arm4", 1, 0.5, 4.0),
    ]
    eff = factor_effects(collapse_runs(recs), "cost_mean", log_scale=True)
    assert math.isclose(eff["docs"]["effect"], 2.0)  # docs doubles cost
    assert math.isclose(eff["mode"]["effect"], 2.0)  # multi-turn doubles cost


def test_cost_contrast_keeps_agent_that_lacks_f1():
    """Coverage asymmetry: an agent with cost everywhere but F1 only in the
    single-query arms anchors the cost contrast (n=2) but not the F1 one (n=1)."""
    recs = _f1_records()
    # give every record a cost in all four arms (a3 included)
    for r in recs:
        r["cost"] = {"naive": 1.0, "optimised": 2.0, "arm3": 2.0, "arm4": 4.0}[r["arm"]]
    # a3 has no optimised/arm4 record at all in _f1_records -> add cost-only runs
    for arm, cost in (("optimised", 2.0), ("arm4", 4.0)):
        recs.append(_rec("a3", arm, 1, None, cost))
    collapsed = collapse_runs(recs)
    f1_eff = factor_effects(collapsed, "f1_mean", log_scale=False)
    cost_eff = factor_effects(collapsed, "cost_mean", log_scale=True)
    assert f1_eff["docs"]["n"] == 2  # a3 excluded (no F1 in multi-turn)
    assert cost_eff["docs"]["n"] == 3  # a3 included (cost everywhere)


def test_cell_table_cost_ratio_normalised_to_naive():
    recs = [
        _rec("a1", "naive", 1, 0.5, 2.0),
        _rec("a1", "arm3", 1, 0.7, 6.0),
        _rec("a2", "naive", 1, 0.3, 1.0),
        _rec("a2", "arm3", 1, 0.5, 2.0),
    ]
    cells = cell_table(collapse_runs(recs))
    # per-agent arm3/naive ratios: a1=3.0, a2=2.0 -> geomean = sqrt(6) ~ 2.449
    assert math.isclose(cells["arm3"]["cost_ratio"], math.sqrt(6.0))
    assert math.isclose(cells["naive"]["cost_ratio"], 1.0)
    assert math.isclose(cells["arm3"]["f1_mean"], 0.6)  # mean(0.7, 0.5)
