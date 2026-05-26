# Archived: arm4 (5D) run01 — qwen old-model output

**Archived 2026-05-26. Excluded from analysis. Superseded by a rerun.**

This `qwen_run01/` is the original Experiment 2 / arm4 (5D = multi-turn + evidence
pack) run01 output for the qwen agent. It was produced during the **original sweep
(2026-05-23)** on the **superseded model `qwen3-max-2026-01-23`**.

All other canonical qwen data in this experiment uses `qwen3.7-max-2026-05-20`
(the agent registry resolves `qwen` to that model). arm4 qwen runs 02–05 are the
later top-up reruns on the correct model. This run01 is the lone old-model
straggler.

Investigation (2026-05-26) confirmed it is **not a mislabel**: the request was
dispatched to DashScope (`dashscope-intl.aliyuncs.com`) with `model:
qwen3-max-2026-01-23` recorded in `qwen_phase_a.json` `method_params`. It genuinely
ran on the old model, so mixing it into the qwen arm4 cell would conflate two model
versions.

**Replacement:** re-run on 2026-05-26 with `qwen3.7-max-2026-05-20`, verified, and
moved into the canonical location `outputs/sota_exp3_arm4_batch1/run01/qwen_run01/`.
This directory is kept only for provenance/audit.
