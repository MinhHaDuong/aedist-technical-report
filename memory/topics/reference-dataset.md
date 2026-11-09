# Reference dataset — the Vietnamese thermal plants registry

Scope: how the reference is versioned, counted and edited. Provenance of
record: [data/reference/PROVENANCE.md](../../data/reference/PROVENANCE.md).

## Size and versions

- **Never hardcode the plant count.** `evaluate.reference_plant_count()` on
  `data/reference/vietnam_thermal_plants_v2_classified.csv` is the source of
  truth; manuscript numbers go through the `\NumRefPlants` macro. Lying
  labels bit four render scripts in one day before the ratchet (0447).
- History: 170 (v2, 0413) → 173 (v2.1, 0445, extensions standalone, PR #780)
  → 176 (v2.2, 0472) → 180 (v2.3, 0395) → **177 (v2.4)**, three potential
  sites removed. `tests/test_reference_count.py` asserts 177 (checked
  2026-11-09).
- The pinned ODS snapshot is a hand edit; the master spreadsheet was
  reverse-synced by ticket 0458 (closed 2026-06-09, convergence gate green
  at 177, `data/reference/MASTER_REVERSE_SYNC_0458.md`). A future re-pin
  must check convergence first, or an adoption silently reverts.

## Editing rules

- **No invented names.** A designation in the reference must be attested
  by a source ("Il n'est pas permis d'inventer un nom de projet"). When two
  rows legitimately share a name, disambiguate structurally (distinct
  `status`, disjoint `units_included`, guarded by
  `tests/test_reference_integrity.py`), never by a synthesized name.
- **Verbatim by construction.** Line-shaped edits to data files use line
  filters (grep/sed/awk) with count guards, not parse/serialize round-trips,
  which normalise line endings, quoting and floats invisibly. End by diffing
  output against source.
- **Dictated constants are checked against disk.** A mapping or vocabulary
  given in a handoff is verified against the consuming data
  (`value_counts()`) and code before commit; self-consistent tests prove
  implementation, not correctness.
- **ODS edits**: odfpy mutation is broken (asymmetric element cache);
  parse `content.xml` with stdlib ElementTree, split repeated-column runs
  only around target cells, rezip every other member byte-identical
  (`mimetype` first, stored). Keep a `.bak` and a full-grid pandas diff
  before/after; abort if the expected current cell value changed.
  LibreOffice UI work (validity lists, conditional formats) stays with the
  author.

## Sources

- Native notes: `project_reference_v2_adopted.md` 6cb95d62,
  `feedback_no_invented_names.md` 1034e4e9, `feedback_verbatim_by_construction.md` 4dd29134,
  `feedback_dictated_constants_verify_disk.md` fe158c94,
  `project_ods_xml_surgery_pattern.md` 7cd84355; native `MEMORY.md` key insight on
  the 177-plant reference.
- Superseded detail: the note's "180 is canonical" (2026-06-09) is replaced
  by 177 (v2.4) per the current test and ticket 0458's closing line.
