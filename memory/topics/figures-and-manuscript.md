# Figures and manuscript — verification habits that held

Scope: how figures, tables and prose of the preprint are checked. Rules of
record: [.claude/rules/writing.md](../../.claude/rules/writing.md) (macros,
CI polarity, figures as artifacts) and
[.claude/rules/workflow.md](../../.claude/rules/workflow.md) (derive prose
from generated artifacts).

## Numbers and claims

- Agent-surveyed numbers are hypotheses; committed artifacts are the truth.
  Verify every model-specific claim against `measurements.jsonl` or the run
  records, never against a summary table (PR #371 shipped a reversed
  comparison and a wrong extreme).
- Before writing a figure script, run a throwaway computation on the raw
  data and check it against the prose claims it will support.
- A display-name fix sweeps `*.tex *.md *.yaml *.toml` **and** the label
  maps in `src/aedist/plot_*.py`; disambiguate tokens that name different
  registry entries; never edit archived run records or protocol specs.

## Figures

- After patching a plot script, rebuild before staging: a PDF already in
  the working tree may predate the fix (its size should move in the
  expected direction).
- Visual criteria are checked on the worst-case panel (longest or two-line
  titles), cropped at 200 dpi or more, never on a convenient easy panel.
- `ax.plot`/`add_line` outside the data range autoscales one panel of a
  shared-rows figure; `ax.text` does not. Pin limits on every panel after
  all artists; check alignment by measuring pixels, not by eye.
- Beamer `[plain]` full-page figures: `width=\paperwidth,height=\paperheight,keepaspectratio`
  (inside a column: `width=\textwidth`).

## Tables, captions, pagination

- After any change touching a table, render the PDF and check every table's
  column fit (`tectonic -r 2 --keep-logs`, then `Overfull \hbox` in the log);
  prefer `tabularx` for the wide text column (author, 2026-06-15).
- Captions state what the figure shows and how to read it: caveats, hedges
  and method qualifications go to the body or an annex (author, 2026-06-15).
- Widows: shave signposts, roadmaps and recaps first; verify by rendering
  the exact page to PNG (`pdftoppm -f N -l N`) and reading it; render with
  every related PR merged, since earlier shaves move later pages.

## Edits across waves

- Anchor on stable identifiers (labels, slugs), never on line numbers,
  section titles or annex letters: each merged wave moves them. Record the
  measured-at commit with any line hint.
- During a live editing session, a background watcher that rebuilds on save
  and exits only on failure lets the agent fix each break as it happens.

## Sources

- Native notes: `feedback_verify_prose_claims.md` 0d76e0e9, `feedback_compute_before_figure.md` 5ff5ff2b,
  `feedback_display_name_sweep_includes_plot_scripts.md` 3acef67a,
  `feedback_verify_artifacts_after_fix.md` 6cdf7142,
  `feedback_figure_verify_worst_case_panel.md` 6c6000e3,
  `feedback_matplotlib_annotation_autoscale.md` ad332ab7,
  `feedback_beamer_plain_frame_sizing.md` 884bfa8f, `feedback_render_and_adjust_tables.md` 581c7f79,
  `feedback_no_caveats_in_captions.md` 00067fef, `feedback_pagination_widow_verification.md` 0e6c9573,
  `feedback_stale_line_numbers_across_waves.md` 156b17ce,
  `feedback_live_edit_build_watcher.md` dfa57181; native `MEMORY.md` key insights on
  stable anchors, agent-surveyed numbers and rebuild-before-commit.
