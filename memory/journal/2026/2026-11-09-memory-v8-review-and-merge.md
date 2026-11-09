# Memory v8 adoption: review catch and merge (PR #1187)

Date: 2026-11-09. Ticket: 0687. Follows
[the adoption entry](2026-11-09-memory-v8-adoption.md).

## Events

- The consolidation of 110 native notes into eight topics copied two
  experiment output paths as the notes gave them:
  `experiments/outputs/ablation/direct/p1_base/` and
  `experiments/outputs/sota_exp2_brerun1/`. Neither existed at the
  reviewed head 2c12ddb0: the Exp 2 outputs had moved to
  `experiments/archive/outputs/`, and the ablation path and the set
  `modelset_ablation_journal` were gone.
- Gaze (answer `rv-20261109-pr-1187-5118`, seats: OpenAI gpt-6-luna for
  public safety, Claude Sonnet for provenance, the gaze orchestrator for
  criteria) returned FINDINGS on that one verifiable item. The provenance
  seat sampled about four facts per topic; the other samples held.
- The OpenAI seat rated the home-directory slug in `memory/SOURCES.md` as
  blocking; gaze downgraded it because the same strings were already on
  main (`padme` in 241 tracked files, `/home/haduong` in 7). The fix
  commit da7711d8 kept the slug and the withheld notes' filenames for
  provenance, corrected both paths against `experiments/experiments.toml`
  and the archive, and recorded that `JobSpec` still sets
  `extra="forbid"`.
- verify-gate: APPROVED, round 1, on da7711d8. Auto-merge pinned to that
  head landed it after the `build` check; merge commit 87c62879.

## References

- PR #1187; review attribution:
  [2026-11-09-review-attribution-pr1187.md](../../evidence/attribution/2026-11-09-review-attribution-pr1187.md).
