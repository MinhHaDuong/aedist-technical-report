# Experiment design rules — AEDIST

## Design for genericity

Lead with the generic abstraction; isolate the first application as a parameterized instance. Pipeline specs, architecture docs, and MASTERPLAN phases describe the general mechanism (Country X, Energy Subsector Y) first, then add "First application: ..." with country-specific details. Code: parameterize by country/subsector, don't hardcode PDP8/EVN details.

## Pinned reps are the control

When N reps are already pinned to the same value of a parameter (e.g. temperature=0.0), those reps **are** the reproducibility measurement for that parameter. Do not add a separate control or warmup call at the same value — it adds no information the existing reps are not already providing.

**Why:** Ticket 0073 proposed a warmup T=0 call before N T=0 reps. The user corrected in one sentence: the N reps' variance is the chain-reproducibility measurement.
