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

## `pipeline-YYYY-MM-DD.ods`

The master spreadsheet for the Vietnam thermal-units reference list, maintained
in the author's "Market report on Gas to Power" project. One row per unit.
Imported here by `import.sh` (which copies from the author's working copy and
stamps with today's date; the master is absent from CI and from the workstation,
so `import.sh` is documentation-grade and is never run in CI).

To correct a data error (a duplicate name, a wrong capacity, a missing `Level`),
fix it **in the master**, then re-run `import.sh` to produce a new datestamped
snapshot. Config pins (e.g., `config.VN_THERMAL_MASTER_SNAPSHOT_ODS`) point at a
specific snapshot; downstream extraction reads from that pinned snapshot via
`data/reference/extract_ods.py`. See `data/reference/PROVENANCE.md` for the full
pipeline and the snapshot→release distinction.
