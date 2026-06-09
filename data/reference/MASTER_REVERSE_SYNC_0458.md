# Master reverse-sync handover (ticket 0458)

Apply this at the **master machine** (where `pipeline.ods` lives). It replays the
three edit-sets currently applied only on the analysis side, so a fresh
`import.sh` snapshot regenerates the **177-plant v2.4 reference** instead of
silently reverting it (`config.VN_THERMAL_MASTER_SNAPSHOT_ODS` re-pin would
otherwise drop the adoption — see the guard comment at that pin and PROVENANCE.md
§ v2.4 / § v2.3).

Target state (verified against the committed `vietnam_thermal_plants_v2_classified.csv`,
2026-06-09): **177 plants** — the 4 extension rows + 3 Kiên Lương + 1 Yên Hưng
below are present; Kim Sơn / Rạng Đông / Phú Thọ are absent.

## Edit-set 1 — standalone extensions (0445)

For each extension row in the master `Power plants` sheet: set `Plant` to the
full extension name and **clear** `Unit` (row-is-the-plant). Resulting plant
rows must match:

| Plant | Province | Fuel | MWe | Status |
|---|---|---|---|---|
| `Duyen Hai 3 extension` | Tra Vinh | coal | 660 | 6 operating |
| `Uong Bi I extension` | Quảng Ninh | coal | 300 | 6 operating |
| `Uong Bi II extension` | Quảng Ninh | coal | 330 | 6 operating |
| `Vinh Tan 4 extension` | Bình Thuận | coal | 600 | 6 operating |

Also log the change in the master's own `Change log` sheet (master discipline —
the analysis-side edit could not touch it meaningfully).

## Edit-set 2 — Kiên Lương complex (0472)

Replay the 4-row insertion (`add_kien_luong.py` is the analysis-side source).
Distinct from the existing "TBKHH Kiên Giang I, II" gas entry; replay verbatim:

| Plant | Province | Fuel | MWe | Status |
|---|---|---|---|---|
| `Kiên Lương 1` | Kiên Giang | coal | 1200 | 9 cancelled |
| `Kiên Lương 2` | Kiên Giang | coal | 1200 | 9 cancelled |
| `Kiên Lương 3` | Kiên Giang | coal | 2000 | 9 cancelled |

## Edit-set 3 — the 0395 additions, **with the project-vs-potential-site boundary**

The 0395 script added four rows. Under the PROVENANCE.md scope boundary
("a project is not a potential site"), replay **only the project**:

- **REPLAY as a row — Yên Hưng**:

  | Plant | Province | Fuel | MWe | Status |
  |---|---|---|---|---|
  | `Yên Hưng` | Quảng Ninh | coal | 1200 | 1 announced |

  PDP7 Annex 1 + Annex 2 attest it; a planned project genuinely missing from the
  gold list.

- **DO NOT replay as rows — Kim Sơn, Rạng Đông, Phú Thọ**: Study E542 PL9.2 draft
  *potential sites* (candidate locations, not projects). Record each as an
  **alias / note** against the corresponding PDP7 northern entry — the three
  `NĐ Miền Bắc 1 / 2 / 3` rows (status `9 cancelled`) — under PROVENANCE.md
  "Traceability without counting".

  ⚠ **Name collision**: an existing plant `Rang Dong cogeneration` is already in
  the reference and is a *different* asset. Alias the E542 "Rạng Đông" potential
  site against the `NĐ Miền Bắc` entry, **not** against `Rang Dong cogeneration`.

After all three edit-sets the master `Power plants` sheet extracts to **177**
plants (173 extensions-adopted + 4 Kiên Lương + 1 Yên Hưng − 0 potential sites),
not 180.

## Convergence gate (run before re-pinning config)

Produce a fresh `import.sh` snapshot, then:

```sh
python data/reference/verify_master_convergence.py \
    --snapshot data/reference/raw/pipeline+0458-YYYY-MM-DD.ods
```

- **`OK: … byte-identical (177 plants)`** → safe to proceed.
- **`DIVERGENCE`** → the diff lists exactly which plant rows are extra (un-applied
  removal / spurious add) or missing (un-replayed edit-set). Fix the master and
  re-run; do not re-pin until it prints OK.

The gate also runs in CI against the currently pinned snapshot
(`tests/test_master_convergence_0458.py`), so the released reference cannot drift
from its snapshot source unnoticed.

## After convergence

1. Re-pin `config.VN_THERMAL_MASTER_SNAPSHOT_ODS` to the new dated snapshot.
2. Remove the 0445 snapshot-exception comment block at that pin.
3. Resolve the PROVENANCE.md "Snapshot provenance exception" paragraph (all three
   edit-sets now replayed).
4. Tick the 0458 exit criteria.
