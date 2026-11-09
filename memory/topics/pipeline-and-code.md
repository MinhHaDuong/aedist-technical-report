# Pipeline and code — build phases, data integrity, Python pitfalls

Scope: what the build and the code base demand that is not obvious from
reading them. Policy of record: `docs/pipeline-phases.md` and the
[Makefile](../../Makefile) comments.

## Build phases (since 2026-06-04, tickets 0405/0406)

- P1 `experiments/acquire.mk`: money-gated API sweeps, all targets phony.
  P2 `experiments/derived/score.mk`: `measurements.jsonl`, marts,
  cross-evals; `rebuild-measurements` is deliberate and reviewed (it
  rebuilds every record). P3 `experiments/render.mk`: figures, tables and
  macros into `report/inputs/generated/`. P4 `report/`, `slides/`: writing
  builds only. The root holds the developer loop; `make world` rewrites
  committed scores and is never run casually.
- Live `experiments/outputs/<dir>/` hold `.record.json` pointers; raw
  replies live in `experiments/archive/outputs/<dir>/`. A wildcard on
  `outputs/` that expands empty while its archive sibling is full is the
  signature of a stale path.
- Clean-room checks of a writing build use `make -B -n`, not `make -n`:
  fresh timestamps hide recipes.
- Read-only permissions on experiment outputs are integrity signals: never
  `chmod` them to unblock git; ask what git is trying to do.
- An in-place migration of `measurements.jsonl` must also migrate the
  source `.record.json` files, or the next rebuild reverts it
  (`scripts/migrate_record_json.py` is the pattern).
- When an output path moves, update the Makefile, the script's argparse
  default and its docstring; grep `src/` for the old path.
- Pipeline shape the author wants: one script per table with `--input` /
  `--output`, Make for orchestration (no shell loops), reproducible
  single-target runs, progress output, checkpointing and quiet logging for
  batch work.

## Python pitfalls met here

- Pydantic models silently drop unknown keys unless `extra="forbid"`: a
  `seed=42` in 57 sweeps never reached the API before ticket 0139; treat
  pre-0139 MoE results as seed-uncontrolled. Before flipping `forbid` on a
  config-loading model, audit every config key against declared fields.
  Test schema extensions through their projection effect, not the
  constructor.
- `Path.with_suffix` on a dotted stem eats part of the name
  (`claude-haiku-4.5-run1`): build such names by string slicing.
- `csv.DictWriter` fieldnames change in the same edit as the row dict.
- A resolver (model → family, slug → colour) gets a test iterating every
  identifier present in `measurements.jsonl`, not only hand-made cases.
- Read the sibling module that already makes the same call before writing
  integration code; reusable helpers go to `src/aedist/util.py` with tests.
- `xargs` needs `env VAR=value cmd`; Makefiles pass `$(CURDIR)` paths to
  workers; scripts under `experiments/` importing `experiments.*` need
  `PYTHONPATH=.`.
- A pre-commit adherence hook (per clone, where installed; none is
  tracked) runs the working-tree tests against the index: order a commit series so each intermediate index is green, or
  slice with `git commit -- <paths>`. Run `ruff` and `pytest -m adherence`
  before every push.

## Sources

- Native notes: `project_phase_build_layout.md` a00ad1d3,
  `project_archive_move_record_only_outputs.md` fcbd96bf,
  `feedback_cleanroom_force_rebuild_test.md` bb8ed23c, `feedback_frozen_results_chmod.md` b73056d9,
  `feedback_namespace_migration_trap.md` 00557a07, `feedback_argparse_defaults_drift.md` 8b9ccc31,
  `feedback_one_script_one_table.md` 506b0089, `feedback_make_not_loops.md` 75b9f4b9,
  `feedback_reproducible_pipeline.md` 98722f85, `feedback_pipeline_ux.md` c04e1466,
  `feedback_fast_pipelines.md` 6706ccc7, `project_seed_silentdrop_bug.md` b004ed1c,
  `feedback_pydantic_forbid_extras_audit.md` 036570f0, `feedback_pydantic_unknown_kwargs.md` 778013e6,
  `feedback_pathlib_with_suffix_dotted_stems.md` f05e0fa5, `feedback_csv_writer_fieldnames.md` 28a3c65d,
  `feedback_semantic_completeness_resolvers.md` 65a379e1, `feedback_check_sister_files_first.md` 0917af22,
  `feedback_shared_utils.md` 369c2c63, `feedback_xargs_env_var.md` 8a0868e0,
  `feedback_uv_run_project_cwd.md` 87bd40ea, `feedback_exp2_interactive_smoke_pythonpath.md` 59f86d36,
  `feedback_precommit_hook_commit_ordering.md` 1bf64dcc,
  `feedback_run_adherence_locally_before_push.md` 2c6cfe0b; native `MEMORY.md` key
  insight on data integrity.
