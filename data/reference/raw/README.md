# `data/reference/raw/` — datestamped immutable snapshots

**ATTENTION: do not edit any file in this directory by hand.**

This directory contains read-only **snapshots** imported from masters maintained
elsewhere. A snapshot's identity is *when it was captured* (datestamp); once
committed, a snapshot is immutable. Editing a file here would silently
desynchronise it from its master: the next `import.sh` run would refuse to
overwrite a committed snapshot, and your change would diverge from any
authoritative source.

## Snapshot policy (ticket 0430)

Every imported file is named `<name>-YYYY-MM-DD.<ext>` (capture date). Once a
snapshot is committed to git, it is never overwritten. A same-day re-import
before the first commit may overwrite; a committed snapshot never. See
`import.sh` for the overwrite guard.

## `wikipedia_*-YYYY-MM-DD.wikitext`

Raw wikitext snapshots of two English Wikipedia pages, captured 2026-06-09 via
the `?action=raw` endpoint (tickets 0486/0494 — source concordance and the
seeded recall bar):

- `wikipedia_coal_vietnam-2026-06-09.wikitext` —
  [List of coal power stations in Vietnam](https://en.wikipedia.org/wiki/List_of_coal_power_stations_in_Vietnam?action=raw)
- `wikipedia_power_vietnam-2026-06-09.wikitext` —
  [List of power stations in Vietnam](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?action=raw);
  the gas plants consumed downstream sit in its `==Gas turbines==` section.

Consumed by `src/aedist/tabulate_source_concordance.py`,
`src/aedist/tabulate_wikipedia_recall_bar.py`, and
`src/aedist/plot_longtail_recognition.py` (wired in `experiments/render.mk`).
These pages are not independent of the reference: the author's group seeded
reference-derived content into them in June 2019 — the edit-history provenance
(revision IDs, diffs) is documented in `data/reference/PROVENANCE.md`.

## `pipeline-YYYY-MM-DD.ods`

The master spreadsheet for the Vietnam thermal-units reference list, maintained
in the author's "Market report on Gas to Power" project. One row per asset at
its finest known grain — unit, plant, or complex — addressed by the
three-column `Complex | Plant | Unit` scheme (ticket 0439; conventions live in
the master's own `Conventions` sheet). Imported here by `import.sh` (which
copies from the author's working copy and stamps with today's date; the master
is absent from CI and from the workstation, so `import.sh` is
documentation-grade and is never run in CI).

To correct a data error (a duplicate designation, a wrong capacity, an
out-of-vocabulary status), fix it **in the master**, then re-run `import.sh`
to produce a new datestamped snapshot. Config pins (e.g., `config.VN_THERMAL_MASTER_SNAPSHOT_ODS`) point at a
specific snapshot; downstream extraction reads from that pinned snapshot via
`data/reference/extract_ods.py`. See `data/reference/PROVENANCE.md` for the full
pipeline and the snapshot→release distinction.
