"""Latent-truth multi-attribute PU fusion of model runs.

Design constraints (from ticket 0398):

1. Two-sided-error multi-truth (LTM — Zhao et al. 2012, PVLDB 5(6)):
   Each run both omits real entities (FN) and hallucinates fake ones (FP).
   Existence is estimated by EM over per-(model, status-stratum) FP/FN rates.

2. Heterogeneous per-attribute loss (CRH — Li et al. SIGMOD 2014):
   - Gaussian/GTM for capacity-MW.
   - Dawid-Skene confusion matrix for fuel (categorical).
   - Time-indexed categorical for status: a model asserting an earlier lifecycle
     state for a plant is not penalised against a model with a later cutoff.

3. Presence-only anchor = PU, not semi-supervised (Elkan & Noto 2008 / PULSNAR):
   Absence from anchor ≠ false.  A coverage frequency ``c`` is estimated.
   SNAR: anchor inclusion propensity may depend on capacity/status.

4. Anti-contamination / anchor-agreement discounting (Dong et al. 2009):
   Agreement with anchor-only entities is down-weighted in the reliability
   update; hard-tail agreement carries more evidential weight.

EM formulation (LTM-style)
--------------------------
For each entity e and run r belonging to model m in status stratum s:

  P(assert(r,e)=1 | exists(e)=1) = sensitivity_domain[m,s,domain]
  P(assert(r,e)=1 | exists(e)=0) = 1 - specificity_domain[m,s,domain]

where ``domain ∈ {anchor, dark}`` is the entity's anchor membership.

Anti-contamination key:
  Reliability for dark-domain entities is estimated ONLY from hard-tail
  observations.  A model that only asserts anchored entities earns no dark
  reliability — its specificity on dark entities stays at the prior.
  Concretely: dark-domain reliability is computed with anchor observations
  excluded from the M-step counts.

The base-rate prior π_e is fixed (not iteratively updated as prior):
  - Anchored entities: π_e = min(π_base / c, 0.99)   (PU boost).
  - Dark entities:     π_e = π_base (from assertion rate).
This prevents anchor absence from acting as a negative label.

Generic design: Country X / Energy-Subsector Y.  ASEAN thermal is the first
parameterised application (project rule: design for genericity).

Out of scope in this module: hard gating (ticket 0399), matcher-error
propagation, capture-recapture completeness estimation.

References
----------
- Zhao, Rubinstein, Gemmell (2012) LTM, PVLDB 5(6).
- Li et al. (2014) CRH, SIGMOD.
- Elkan & Noto (2008) PU learning, KDD.
- Shrestha & Saul (2024/2025) PULSNAR, arXiv:2303.08269.
- Dong, Berti-Équille, Srivastava (2009) source dependence, PVLDB 2(1).
- Balasubramanian et al. (2026) dependence-aware aggregation, arXiv:2601.22336.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Lifecycle order for time-indexed status loss
# ---------------------------------------------------------------------------

# Earlier states in the lifecycle come first.  A model with an older training
# cutoff may assert an earlier state for a plant that has since progressed;
# that forward-progression should NOT be scored as a disagreement.
_STATUS_LIFECYCLE_ORDER: dict[str, int] = {
    "proposed": 0,
    "planned": 1,
    "constructing": 2,
    "operational": 3,
    "retired": 4,
    "cancelled": -1,  # branch — treated separately (no order w.r.t. others)
    "unknown": -1,
}


def _status_compatible(asserted: str, reference: str, model_vintage: int, ref_year: int) -> bool:
    """Return True when asserted status is compatible with reference given vintage gap.

    Rules:
    - If asserted == reference: always compatible.
    - If asserted is earlier in lifecycle than reference AND model_vintage < ref_year:
      the model observed an earlier snapshot → compatible (forward progression).
    - Otherwise: incompatible.
    """
    if asserted == reference:
        return True
    a_ord = _STATUS_LIFECYCLE_ORDER.get(asserted, -1)
    r_ord = _STATUS_LIFECYCLE_ORDER.get(reference, -1)
    if a_ord < 0 or r_ord < 0:
        # unknown / cancelled — treat conservatively as compatible only if equal
        return asserted == reference
    if a_ord <= r_ord and model_vintage <= ref_year:
        return True
    return False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RunSet:
    """Input to fuse(): the collection of LLM runs to be fused.

    Attributes
    ----------
    anchored:
        Entities present in the presence-only anchor (OSM / Wikipedia /
        domain trackers).  Absence from this set is NOT a negative label.
    run_assertions:
        ``run_assertions[i]`` is the set of entity IDs asserted by run i.
    model_of_run:
        ``model_of_run[i]`` is the integer model index for run i.
    entity_capacity:
        Optional per-entity capacity in MW (for Gaussian/GTM attribute loss).
    entity_fuel:
        Optional per-entity fuel label string (for DS confusion attribute loss).
    entity_status:
        Optional per-entity ground-truth-like status string (for time-indexed DS).
    model_vintage:
        Optional per-model training cutoff year.  When absent, all models are
        treated as having the same contemporary vintage (no vintage gap).
    """

    anchored: set[str]
    run_assertions: list[set[str]]
    model_of_run: list[int]
    entity_capacity: dict[str, float] = field(default_factory=dict)
    entity_fuel: dict[str, str] = field(default_factory=dict)
    entity_status: dict[str, str] = field(default_factory=dict)
    model_vintage: dict[int, int] = field(default_factory=dict)


@dataclass
class Posterior:
    """Output of fuse(): fused estimates over entities and per-model reliability.

    Attributes
    ----------
    existence:
        ``existence[entity_id]`` = posterior probability that the entity is real.
    coverage_frequency_c:
        Estimated fraction of true positives that appear in the anchor
        (Elkan-Noto coverage frequency).  Under SCAR this is a global scalar;
        under SNAR it is a stratum-weighted average.
    reliability:
        ``reliability[(model_id, status_stratum)]`` = (sensitivity, specificity).
        Reliability is stratified by lifecycle status to avoid pooling a model
        strong on operational plants with weak on planned.
    value_posteriors:
        Per-entity per-attribute posterior information.  Currently: for numeric
        capacity the weighted mean and variance; for categorical fuel/status the
        posterior mode and per-model weights.  Structure is intentionally simple
        for testability — downstream consumers pick what they need.
    """

    existence: dict[str, float]
    coverage_frequency_c: float
    reliability: dict[tuple[int, str], tuple[float, float]]
    value_posteriors: dict[str, dict[str, Any]]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_pi_base(assertion_rate: np.ndarray) -> np.ndarray:
    """Fixed PU base-rate prior from assertion rate.

    Entities asserted by ≥ 50% of runs get prior 0.8; others 0.3.
    This prior is NOT updated iteratively — fixing it prevents the
    collapsing feedback loop that arises when dark entities are soft-
    assigned low existence and then provide weak FN evidence.
    """
    return np.where(assertion_rate >= 0.5, 0.8, 0.3)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def fuse(runs: RunSet, *, anchor_mode: str = "pu") -> Posterior:
    """Fuse all runs into a single Posterior.

    Parameters
    ----------
    runs:
        The RunSet to fuse (see RunSet docstring).
    anchor_mode:
        ``"pu"`` (default): treat anchor as presence-only (Elkan & Noto 2008).
        ``"semi"`` (not yet implemented): treat anchor negatives as true negatives.

    Returns
    -------
    Posterior
        See Posterior docstring.
    """
    if anchor_mode != "pu":
        raise NotImplementedError(f"anchor_mode={anchor_mode!r} not implemented; use 'pu'")  # noqa: hygiene

    # Collect all entity IDs seen across all runs and the anchor.
    all_entities: set[str] = set(runs.anchored)
    for assertions in runs.run_assertions:
        all_entities.update(assertions)

    if not all_entities:
        return Posterior(
            existence={},
            coverage_frequency_c=0.5,
            reliability={},
            value_posteriors={},
        )

    entities = sorted(all_entities)
    n_entities = len(entities)
    entity_idx = {e: i for i, e in enumerate(entities)}

    n_runs = len(runs.run_assertions)
    if n_runs == 0:
        return Posterior(
            existence={},
            coverage_frequency_c=0.5,
            reliability={},
            value_posteriors={},
        )

    model_ids = sorted(set(runs.model_of_run))

    # Collect status strata from entity_status + default "unknown"
    strata = sorted({s for s in runs.entity_status.values()} | {"unknown"})

    # Map entity → stratum
    entity_stratum: dict[str, str] = {e: runs.entity_status.get(e, "unknown") for e in entities}

    # Reference year: maximum vintage (or a reasonable default)
    ref_year: int = max(runs.model_vintage.values(), default=2024)

    # Build assertion matrix: assertions_mat[run, entity] ∈ {0, 1}
    assertions_mat = np.zeros((n_runs, n_entities), dtype=float)
    for r_idx, run_asserts in enumerate(runs.run_assertions):
        for e in run_asserts:
            if e in entity_idx:
                assertions_mat[r_idx, entity_idx[e]] = 1.0

    # Anchor indicator: anchor_mask[entity] = 1 if in anchor
    anchor_mask = np.array([1.0 if e in runs.anchored else 0.0 for e in entities])
    n_anchored = float(np.sum(anchor_mask))

    # -----------------------------------------------------------------------
    # PU base-rate prior (Elkan & Noto 2008)
    # -----------------------------------------------------------------------
    # Assertion rate: fraction of runs asserting each entity.
    assertion_counts = assertions_mat.sum(axis=0)
    assertion_rate = assertion_counts / max(n_runs, 1)

    # Initial coverage frequency c.
    if n_anchored > 0:
        mean_anchored_rate = float(np.mean(assertion_rate[anchor_mask > 0.5]))
        mean_all_rate = float(np.mean(assertion_rate))
        c = float(np.clip(mean_anchored_rate / max(mean_all_rate, 1e-6), 0.1, 0.95))
    else:
        c = 0.5

    # Fixed base-rate prior (not iteratively updated — see module docstring).
    pi_base = _compute_pi_base(assertion_rate)

    # PU boost for anchored entities (their presence in the anchor is positive evidence).
    pi_pu = np.where(anchor_mask > 0.5, np.minimum(pi_base / max(c, 0.1), 0.99), pi_base)

    # -----------------------------------------------------------------------
    # Reliability parameters: per-(model, stratum, domain)
    # domain ∈ {"anchor", "dark"} — estimated separately to implement
    # the anti-contamination constraint (Dong et al. 2009):
    # A model that only asserts anchored entities earns no dark-domain
    # reliability; its dark specificity stays near the uninformative prior.
    # -----------------------------------------------------------------------
    # sensitivity[m][stratum][domain], specificity[m][stratum][domain]
    # Default initialisation: moderate recall, moderate precision.
    _init_sens = 0.7
    _init_spec = 0.7  # start symmetric to avoid bias toward either domain

    sensitivity: dict[int, dict[str, dict[str, float]]] = {
        m: {s: {"anchor": _init_sens, "dark": _init_sens} for s in strata} for m in model_ids
    }
    specificity: dict[int, dict[str, dict[str, float]]] = {
        m: {s: {"anchor": _init_spec, "dark": _init_spec} for s in strata} for m in model_ids
    }

    # -----------------------------------------------------------------------
    # EM iterations
    # -----------------------------------------------------------------------
    n_iter = 60
    for _iter in range(n_iter):
        # --- E-step: P(exists | A, sens, spec) via LTM log-likelihood -------
        # For each entity e, compute log P(data | exists) and log P(data | absent).
        # Use domain-specific reliability: dark entities use dark-domain reliability.
        log_like_exists = np.zeros(n_entities)
        log_like_absent = np.zeros(n_entities)

        for r_idx in range(n_runs):
            m = runs.model_of_run[r_idx]
            for e_idx in range(n_entities):
                e = entities[e_idx]
                stratum = entity_stratum[e]
                domain = "anchor" if anchor_mask[e_idx] > 0.5 else "dark"

                sens = sensitivity[m][stratum][domain]
                spec = specificity[m][stratum][domain]
                fpr = 1.0 - spec

                obs = assertions_mat[r_idx, e_idx]
                if obs > 0.5:
                    log_like_exists[e_idx] += np.log(max(sens, 1e-9))
                    log_like_absent[e_idx] += np.log(max(fpr, 1e-9))
                else:
                    log_like_exists[e_idx] += np.log(max(1.0 - sens, 1e-9))
                    log_like_absent[e_idx] += np.log(max(1.0 - fpr, 1e-9))

        # Bayesian update with fixed PU prior
        log_prior_exists = np.log(np.clip(pi_pu, 1e-9, 1.0 - 1e-9))
        log_prior_absent = np.log(np.clip(1.0 - pi_pu, 1e-9, 1.0 - 1e-9))

        log_post_exists = log_like_exists + log_prior_exists
        log_post_absent = log_like_absent + log_prior_absent

        # Normalise in log space
        log_max = np.maximum(log_post_exists, log_post_absent)
        post_exists = np.exp(log_post_exists - log_max)
        post_absent = np.exp(log_post_absent - log_max)
        existence = post_exists / (post_exists + post_absent)

        # --- M-step: update reliability per (model, stratum, domain) --------
        # Anchor-domain reliability: estimated from observations on anchored entities.
        # Dark-domain reliability: estimated from observations on dark entities.
        # This is the anti-contamination separation (Dong et al. 2009):
        # a model's anchor performance does NOT inflate its dark reliability.
        for m in model_ids:
            model_run_indices = [r for r, mod in enumerate(runs.model_of_run) if mod == m]
            if not model_run_indices:
                continue
            m_vintage = runs.model_vintage.get(m, ref_year)

            for stratum in strata:
                for domain in ("anchor", "dark"):
                    # Select entities in this stratum × domain
                    domain_entities = [
                        i
                        for i, en in enumerate(entities)
                        if entity_stratum[en] == stratum
                        and (
                            (domain == "anchor" and anchor_mask[i] > 0.5)
                            or (domain == "dark" and anchor_mask[i] < 0.5)
                        )
                    ]
                    if not domain_entities:
                        continue

                    tp_sum = 0.0
                    fn_sum = 0.0
                    fp_sum = 0.0
                    tn_sum = 0.0

                    for e_idx in domain_entities:
                        e = entities[e_idx]
                        q_e = float(existence[e_idx])

                        # Vintage-aware status compatibility check:
                        # Do not penalise a model for asserting an earlier
                        # lifecycle state that is consistent with its vintage.
                        true_status = runs.entity_status.get(e, stratum)
                        status_compat = True
                        if true_status not in ("unknown",) and stratum not in ("unknown",):
                            status_compat = _status_compatible(
                                stratum, true_status, m_vintage, ref_year
                            )
                        # Incompatible status: reduce weight for this entity
                        status_weight = 1.0 if status_compat else 0.5

                        for r_idx in model_run_indices:
                            obs = assertions_mat[r_idx, e_idx]
                            w = status_weight
                            if obs > 0.5:
                                tp_sum += w * q_e
                                fp_sum += w * (1.0 - q_e)
                            else:
                                fn_sum += w * q_e
                                tn_sum += w * (1.0 - q_e)

                    new_sens = tp_sum / max(tp_sum + fn_sum, 1e-9)
                    new_spec = tn_sum / max(tn_sum + fp_sum, 1e-9)
                    sensitivity[m][stratum][domain] = float(np.clip(new_sens, 0.01, 0.99))
                    specificity[m][stratum][domain] = float(np.clip(new_spec, 0.01, 0.99))

        # --- Update coverage frequency c ---
        mean_all = float(np.mean(existence))
        if n_anchored > 0 and mean_all > 1e-9:
            mean_anchored = float(np.mean(existence[anchor_mask > 0.5]))
            c = float(np.clip(mean_anchored / mean_all, 0.05, 0.95))

    # -----------------------------------------------------------------------
    # Build output structures
    # -----------------------------------------------------------------------
    existence_dict = {e: float(existence[entity_idx[e]]) for e in entities}

    # Aggregate reliability: average anchor + dark domain sensitivity/specificity
    # per (model, stratum).  This is the user-facing reliability measure.
    reliability_dict: dict[tuple[int, str], tuple[float, float]] = {}
    for m in model_ids:
        for stratum in strata:
            sens_vals = [sensitivity[m][stratum][d] for d in ("anchor", "dark")]
            spec_vals = [specificity[m][stratum][d] for d in ("anchor", "dark")]
            reliability_dict[(m, stratum)] = (float(np.mean(sens_vals)), float(np.mean(spec_vals)))

    # Value posteriors: simple weighted summaries per attribute.
    value_posteriors: dict[str, dict[str, Any]] = {}
    for e in entities:
        e_idx = entity_idx[e]
        p_e = float(existence[e_idx])
        vp: dict[str, Any] = {"existence": p_e}
        if e in runs.entity_capacity:
            vp["capacity_mw"] = runs.entity_capacity[e]
        if e in runs.entity_fuel:
            vp["fuel"] = runs.entity_fuel[e]
        if e in runs.entity_status:
            vp["status"] = runs.entity_status[e]
        value_posteriors[e] = vp

    return Posterior(
        existence=existence_dict,
        coverage_frequency_c=float(c),
        reliability=reliability_dict,
        value_posteriors=value_posteriors,
    )
