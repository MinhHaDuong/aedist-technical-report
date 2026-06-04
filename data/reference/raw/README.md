# `data/reference/raw/` — imported snapshots, do not hand-edit

**ATTENTION: do not edit any file in this directory by hand.**

This directory contains read-only snapshots imported from masters maintained
elsewhere. Editing a file here would silently desynchronise it from its master:
the next `import.sh` run would overwrite your change, and in the meantime the
snapshot would no longer reflect any authoritative source.

## `pipeline.ods`

The master spreadsheet for the Vietnam thermal-units reference list, maintained
in the author's "Market report on Gas to Power" project. One row per unit.
Imported here by `import.sh` (which copies from the author's working copy; the
master is absent from CI and from the workstation, so `import.sh` is
documentation-grade and is never run in CI).

To correct a data error (a duplicate name, a wrong capacity, a missing `Level`),
fix it **in the master**, then re-run `import.sh` to refresh this snapshot.
Downstream extraction reads from this snapshot via
`data/reference/extract_ods.py`; see `data/reference/PROVENANCE.md` for the full
pipeline.
