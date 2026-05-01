# Audit response: openai/gpt-5.4

**Date:** 2026-05-01T20:09:01.436310+00:00
**Tokens:** 4282 in / 452 out
**Wall time:** 8.23s

---

## (a) Strongest inconsistency
The core contradiction is between the thesis that deep research “**closes all four limits simultaneously**” and the paper’s own caveat that “**The data on disk today does not yet support that hypothesis**.” Earlier, it says the qualities “**saturate together at deep-research-with-`prompt_complete`**” and that “**Stage 5 (deep research) is forced once 3 and 4 are present**,” but the caveat reports “**Best deep-research-cell F1 = 0.557**” and that this cell “**currently sits below the regimes-scatter ceiling, not above it**.” That is not a minor caveat; it undercuts the narrative arc.

## (b) Weakest empirical claim
The weakest empirical claim is “**Stage 5 (deep research) is forced once 3 and 4 are present**” and especially that shipping within “**2–7 months**” means the composition is “**not a separate product decision but a near-mechanical join**.” This is a strong causal/structural inference from a tiny, likely selective sample (“**Across the four labs**”). Product-release timing is weak evidence for necessity.

## (c) Most likely methodological objection
The biggest reviewer objection is construct validity: you admit data and answer quality are “**bundled by the F1 metric on AEDIST**,” yet the framework makes strong distinctions among Coverage, Freshness, Articulation, and Coherence. Worse, the key ceiling claim may be an “**Evaluator artefact**” because “**the extractor may be choking on the framing instead of pulling the inventory table out**.” A reviewer will say the measurement pipeline cannot identify the proposed limits if the evaluator confounds formatting with extraction quality.

## (d) Claim to drop
Drop the claim that deep research “**caps both data quality … and answer quality**” / “**F1 → 1**.” The document itself says this is “**a hypothesis the present data does not corroborate**.” Keeping it invites a desk-reject-level credibility problem because your strongest headline claim is explicitly unsupported by current results.