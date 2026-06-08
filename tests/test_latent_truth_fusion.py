"""Tests for aedist.fuse_runs — latent-truth multi-attribute PU fusion.

Unit tests only — no LLM calls, no I/O.

Named tests from the ticket exit criteria (descoped — per-attribute loss in 0481):
  1. test_pu_anchor_absence_is_not_negative
  2. test_reliability_not_pooled_across_strata
  3. test_status_compatible_function  (replaces vacuous vintage fuse test; original in 0481)
  4. test_anchor_agreement_discounted
  5. (coverage_frequency_c estimated, not 1.0 — rolled into test 1)

Fixture contract: make_runs() returns a RunSet accepted by fuse().
"""


from aedist.fuse_runs import RunSet, _status_compatible, fuse

# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------


def make_runs(
    anchored: set[str],
    run_assertions: list[set[str]],
    model_of_run: list[int],
    *,
    entity_capacity: dict[str, float] | None = None,
    entity_fuel: dict[str, str] | None = None,
    entity_status: dict[str, str] | None = None,
    model_vintage: dict[int, int] | None = None,
) -> RunSet:
    """Construct a RunSet for testing.

    Parameters
    ----------
    anchored:
        Entities present in the presence-only anchor (e.g. OSM/Wikipedia).
        Absence from this set is NOT a negative label.
    run_assertions:
        Each element is the set of entity names asserted by one run.
    model_of_run:
        ``model_of_run[i]`` is the model index for run i.
    entity_capacity:
        Optional per-entity capacity (MW) for numeric-attribute testing.
    entity_fuel:
        Optional per-entity fuel label for categorical-attribute testing.
    entity_status:
        Optional per-entity status string for time-indexed-attribute testing.
    model_vintage:
        Optional per-model training cutoff year (e.g. {0: 2022, 1: 2024}).
        Used by the time-indexed status loss so a model asserting an
        earlier lifecycle state is not penalised vs a model with a later
        cutoff.
    """
    return RunSet(
        anchored=anchored,
        run_assertions=run_assertions,
        model_of_run=model_of_run,
        entity_capacity=entity_capacity or {},
        entity_fuel=entity_fuel or {},
        entity_status=entity_status or {},
        model_vintage=model_vintage or {},
    )


# ---------------------------------------------------------------------------
# 1. PU anchor — absence is not a negative
# ---------------------------------------------------------------------------


def test_pu_anchor_absence_is_not_negative():
    """Dark plants asserted by 3/4 runs must survive despite anchor absence.

    PU scenario (Elkan & Noto 2008):
      - p_anchored ∈ anchor (operational core, easy to find).
      - p_dark ∉ anchor (hard tail, real but not in training-set registries).
      - p_dark asserted by runs 1, 2, 4 (3 of 4) with distinct models.

    Expected:
      - existence["p_dark"] > 0.5  (PU, not semi-supervised)
      - coverage_frequency_c < 1.0  (anchor does not cover all true positives)
      - coverage_frequency_c is estimated, not hard-coded.
    """
    runs = make_runs(
        anchored={"p_anchored"},
        run_assertions=[
            {"p_anchored", "p_dark"},
            {"p_anchored", "p_dark"},
            {"p_anchored"},
            {"p_anchored", "p_dark"},
        ],
        model_of_run=[0, 1, 2, 3],
    )
    post = fuse(runs, anchor_mode="pu")

    # The dark plant is asserted by 3 of 4 independent-ish runs.
    assert post.existence["p_dark"] > 0.5, (
        f"PU model must not suppress a dark plant asserted by 3/4 runs; "
        f"got existence={post.existence['p_dark']:.3f}"
    )

    # Anchor covers p_anchored but not p_dark: c < 1.
    # Analytically: 1 of 2 true entities is anchored → c ≈ 0.5 (SCAR approx).
    # We only require the estimator is not trivially 1.0.
    assert post.coverage_frequency_c < 1.0, (
        f"Coverage frequency c must be estimated below 1.0; got c={post.coverage_frequency_c:.3f}"
    )
    assert post.coverage_frequency_c > 0.0, (
        f"Coverage frequency c must be positive; got c={post.coverage_frequency_c:.3f}"
    )


# ---------------------------------------------------------------------------
# 2. Reliability stratified by status — not pooled
# ---------------------------------------------------------------------------


def test_reliability_not_pooled_across_strata():
    """A model strong on operational plants and weak on planned must get two
    distinct (sensitivity, specificity) values — one per status stratum.

    Design:
      - status_stratum is assigned per entity (operational vs planned).
      - Model 0 correctly asserts all operational plants but misses all planned.
        → high sensitivity on operational, low sensitivity on planned.
      - We verify the two strata produce different spec/sens, not a single pool.
    """
    runs = make_runs(
        anchored={"op1", "op2"},
        run_assertions=[
            {"op1", "op2"},           # model 0 run 1: only operational
            {"op1", "op2"},           # model 0 run 2: only operational
            {"op1", "op2", "pl1"},    # model 1 run 1: all plants
            {"op1", "op2", "pl1"},    # model 1 run 2: all plants
        ],
        model_of_run=[0, 0, 1, 1],
        entity_status={
            "op1": "operational",
            "op2": "operational",
            "pl1": "planned",
        },
    )
    post = fuse(runs, anchor_mode="pu")

    # Model 0 should have different sensitivity in operational vs planned strata.
    sens_0_op = post.reliability[(0, "operational")][0]
    sens_0_pl = post.reliability[(0, "planned")][0]

    # Model 0 never asserts pl1 → its planned-stratum sensitivity must be
    # noticeably lower than operational (where it always asserts correctly).
    assert sens_0_op > sens_0_pl + 0.1, (
        f"Model 0 operational sensitivity {sens_0_op:.3f} must exceed "
        f"planned sensitivity {sens_0_pl:.3f} by a clear margin"
    )


# ---------------------------------------------------------------------------
# 3. Status vintage — _status_compatible() function unit test
#
# NOTE: The original exit criterion ("time-indexed DS for status with model
# training-cutoff as covariate, test_status_vintage_not_penalized") is deferred
# to child ticket 0481, which adds per-run attribute observations to RunSet.
# Without per-run attributes, a model reporting 'constructing' vs 'operational'
# cannot be represented — run_assertions carries presence only.
#
# This test verifies the _status_compatible() helper that 0481 will use.
# ---------------------------------------------------------------------------


def test_status_compatible_function():
    """_status_compatible() must implement time-indexed forward-lifecycle logic.

    Rules:
      - Same status → always compatible.
      - Earlier lifecycle state + older model vintage → compatible (forward progression).
      - Later lifecycle state (model claims future) → incompatible.
      - Unknown/cancelled status → only compatible with itself.
    """
    # Same status: always compatible regardless of vintage
    assert _status_compatible("operational", "operational", 2022, 2024)
    assert _status_compatible("planned", "planned", 2024, 2024)

    # Forward progression: model saw 'constructing', truth is now 'operational'
    # Model vintage 2022 < ref_year 2024 → compatible
    assert _status_compatible("constructing", "operational", 2022, 2024)

    # Forward progression: 'planned' → 'constructing' → 'operational'
    assert _status_compatible("planned", "operational", 2020, 2024)

    # Backward regression: model claims future state (should be incompatible)
    # Model with 2022 vintage claims 'operational' but truth was 'planned' in 2022
    assert not _status_compatible("operational", "planned", 2022, 2024)

    # Unknown status: compatible only with itself
    assert _status_compatible("unknown", "unknown", 2022, 2024)
    assert not _status_compatible("unknown", "operational", 2022, 2024)

    # Cancelled is a branch (order -1): compatible only with itself
    assert _status_compatible("cancelled", "cancelled", 2022, 2024)
    assert not _status_compatible("cancelled", "operational", 2022, 2024)


# ---------------------------------------------------------------------------
# 4. Anchor-agreement discounted
# ---------------------------------------------------------------------------


def test_anchor_agreement_discounted():
    """A model that only ever reproduces anchored plants must not earn high
    reliability from that agreement.

    Design:
      - anchor = {'easy1', 'easy2'} (the well-known operational core).
      - 'hard1' is a real plant not in the anchor (hard tail the model could
        not have copied from training data).
      - model 0 (copycat): asserts only anchor plants, never hard tail.
      - model 1 (genuine): asserts anchor plants AND hard tail.
      - Fused existence of 'hard1' is driven by model 1 alone; model 0 gets
        no credit for anchor-only agreement.

    Assertion: model 0's reliability must be lower than model 1's, or at most
    equal — it must NOT exceed model 1's reliability by a significant margin.
    """
    runs = make_runs(
        anchored={"easy1", "easy2"},
        run_assertions=[
            {"easy1", "easy2"},              # model 0 run 1: anchor only
            {"easy1", "easy2"},              # model 0 run 2: anchor only
            {"easy1", "easy2"},              # model 0 run 3: anchor only
            {"easy1", "easy2", "hard1"},     # model 1 run 1: genuine
            {"easy1", "easy2", "hard1"},     # model 1 run 2: genuine
            {"easy1", "easy2", "hard1"},     # model 1 run 3: genuine
        ],
        model_of_run=[0, 0, 0, 1, 1, 1],
    )
    post = fuse(runs, anchor_mode="pu")

    # Aggregate reliability: average sensitivity across strata.
    def mean_reliability(model_id: int) -> float:
        strata = [v for (m, _), v in post.reliability.items() if m == model_id]
        if not strata:
            return 0.0
        return sum(s for s, _ in strata) / len(strata)

    rel_0 = mean_reliability(0)
    rel_1 = mean_reliability(1)

    # Model 0 (anchor-only) must not be rated significantly more reliable than
    # model 1 (which correctly reports hard-tail entities too).
    # Under anchor discounting, rel_0 ≤ rel_1 or at most very close.
    assert rel_0 <= rel_1 + 0.15, (
        f"Anchor-only model (rel={rel_0:.3f}) should not substantially outperform "
        f"genuine model (rel={rel_1:.3f}). Anchor agreement must be discounted."
    )

    # hard1 must still have positive existence (model 1 is genuine).
    assert post.existence.get("hard1", 0.0) > 0.3, (
        f"hard1 asserted by genuine model 1; existence must be > 0.3, got "
        f"{post.existence.get('hard1', 0.0):.3f}"
    )


# ---------------------------------------------------------------------------
# Structural / interface tests
# ---------------------------------------------------------------------------


def test_posterior_has_required_attributes():
    """fuse() returns a Posterior with existence, coverage_frequency_c,
    reliability, and value_posteriors."""
    runs = make_runs(
        anchored={"p1"},
        run_assertions=[{"p1", "p2"}, {"p1"}],
        model_of_run=[0, 1],
    )
    post = fuse(runs, anchor_mode="pu")

    assert hasattr(post, "existence")
    assert hasattr(post, "coverage_frequency_c")
    assert hasattr(post, "reliability")
    assert hasattr(post, "value_posteriors")

    # existence should cover all asserted entities.
    assert "p1" in post.existence
    assert "p2" in post.existence

    # Each existence value is a proper probability.
    for eid, prob in post.existence.items():
        assert 0.0 <= prob <= 1.0, f"existence[{eid!r}]={prob} out of [0,1]"


def test_empty_runs_returns_empty_posterior():
    """fuse() on zero runs must not crash; returns empty existence."""
    runs = make_runs(
        anchored=set(),
        run_assertions=[],
        model_of_run=[],
    )
    post = fuse(runs, anchor_mode="pu")
    assert post.existence == {}
    assert 0.0 <= post.coverage_frequency_c <= 1.0


def test_single_unanimous_run_high_existence():
    """A single run asserting one entity must yield existence > 0 when the
    entity is also in the anchor (high prior confidence)."""
    runs = make_runs(
        anchored={"p1"},
        run_assertions=[{"p1"}],
        model_of_run=[0],
    )
    post = fuse(runs, anchor_mode="pu")
    assert post.existence["p1"] > 0.5
