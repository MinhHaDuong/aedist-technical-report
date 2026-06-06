# Extension-as-unit vs standalone: net error measurement (ticket 0445)

**Date:** 2026-06-06. **Inputs:** master variant snapshot
`pipeline-2026-06-05+extensions-as-plants.ods` (author hand edit of the
2026-06-05 master, NOT committed — see "Artifact path" below), scored against
the 70 archived `exp1_batch2` run CSVs (14 models × 5 reps; declined runs have
no CSV and are absent from both arms identically). Zero API spend: LP matcher
re-runs only, both arms scored fresh with the same code
(test-one check: fresh absorbed score of `claude-haiku-4.5-run1` reproduced the
committed record exactly, tp=30/fp=21/fn=140).

## The variant

Exactly 8 cells in 4 rows of the master's `Power plants` sheet: each extension
row's `Plant` cell gets the ` extension` suffix and its `Unit` cell is emptied
(row-is-the-plant semantics). All other sheets byte-identical.

| Row | Absorbed (Plant / Unit) | Standalone (Plant / Unit) |
|---|---|---|
| 34 | Duyen Hai 3 / Extension | Duyen Hai 3 extension / ∅ |
| 235 | Uong Bi I / extension | Uong Bi I extension / ∅ |
| 238 | Uong Bi II / extension | Uong Bi II extension / ∅ |
| 249 | Vinh Tan 4 / extension | Vinh Tan 4 extension / ∅ |

## Effect on the plant release (extract → aggregate → classify)

Plant count **170 → 173, not 174**: in the absorbed reference, `Uong Bi II`'s
*only* constituent row is its extension, so making it standalone replaces the
parent 1:1 instead of adding a row.

| Plant | Absorbed | Standalone variant |
|---|---|---|
| Duyen Hai 3 | 1904 MW | 1244 MW (+ Duyen Hai 3 extension, 660 MW) |
| Uong Bi I | 405 MW, operating | **105 MW, retired** (+ Uong Bi I extension, 300 MW, operating) |
| Uong Bi II | 330 MW, operating | *(gone)* → Uong Bi II extension, 330 MW, operating |
| Vinh Tan 4 | 1800 MW | 1200 MW (+ Vinh Tan 4 extension, 600 MW) |

Note the `Uong Bi I` status flip: its remaining Units 1–2 are retired; the
extension was the only operating capacity. Any status-filtered cohort changes
membership under the variant, not just names.

## Net TP/FP/FN (70 runs)

| Arm | TP | FP | FN | FP+FN |
|---|---|---|---|---|
| Absorbed (170 plants) | 3106 | 1777 | 8794 | **10571** |
| Standalone (173 plants) | 3172 | 1711 | 8938 | **10649** |
| Δ (standalone − absorbed) | +66 | −66 | +144 | **+78** |

- **The ticket's decision rule (lower FP+FN, TP recall in view): absorbed
  wins** — by 78 aggregate, by per-model net error in **10 of 14 models**
  (only claude-sonnet-4.6 −15, claude-opus-4.6 −5, deepseek-v4-pro −1 and
  gpt-5.5 −1 favor standalone), and recall is a wash, so the rule is not
  rescued by its recall clause.
- Decomposition: the variant flips **66 FP → TP** (extension emissions that
  the LP vetoed against the absorbed parent now match their own row, e.g.
  « Nhiệt điện Duyên Hải 3 mở rộng » → `Duyen Hai 3 extension`, exact, 4.2%
  capacity diff vs vetoed before). It introduces **zero** new FPs. The +144 FN
  is arithmetic: +3 reference slots × 70 runs = +210 potential FN, minus the
  66 newly matched. FN ≡ ref_size − TP throughout (declines identical in both
  arms).
- **Per-run:** net error worse in 46/70 runs, better in 24/70. The gains are
  confined to the 4 extension-emitting models; the other 10 (gpt-oss-120b/20b,
  mistral-large-2512, qwen3.6-35b-a3b, qwen3.6-flash with ΔTP=0, plus the
  partial emitters) pay for reference rows they never recall.
- **F1 (denominator-normalized):** absorbed 0.3673 vs standalone 0.3703 mean;
  35 runs improve / 31 worsen under standalone. Recall on own reference:
  26.1% vs 26.2% — a wash.
- Matcher-side prerequisite already in place: `src/aedist/cleaner/config.json`
  substitutes `mo rong|mr → extension` after diacritics stripping, so
  Vietnamese extension emissions normalize onto the standalone names exactly.

## Reading

By the ticket's stated rule, **absorbed wins** (+78 of 10571, ≈0.7%; 10/14
models; recall a wash). The case for standalone exists but requires
*overriding that rule*: its margin comes from F1 (0.3673 → 0.3703, 35
improve / 31 worsen — marginal) and from discounting the FN that the 3 extra
reference rows generate. That discount is not a correction one can neutrally
apply — whether those rows belong in the denominator **is** the ontological
question under decision, made numerical. Scoring cannot discriminate here
because scoring presupposes the answer.

What the measurement does settle: the original worry — "absorption only
increased errors" — is **not supported**. Absorption costs the 66
vetoed-extension FPs but matches 210 FN slots' worth of reference at the
parent grain; the matching-quality gain of standalone is real (FP→TP flips,
0–4% capacity diffs instead of 26% strained-parent matches) but confined to
the 4 models that emit extensions at all. Neither variant buys a material
scoring advantage; the choice rests on which grain is truer to the asset
inventory (is "Vinh Tan 4 extension" a plant or a unit of Vinh Tan 4?).

Cost asymmetry of the decision itself: keeping absorbed = zero further work,
rule-consistent, count stays 170. Switching = master edit + new snapshot +
PROVENANCE entry + before/after gate + re-score + figures, and 0444 macroizes
at 173.

## Artifact path (if standalone is adopted)

`data/reference/raw/` is immutable/import-only: the hand-made
`pipeline-2026-06-05+extensions-as-plants.ods` must NOT be committed there.
Adoption path per 0445/0413 discipline: edit the master in the Gas-to-Power
project, re-run `import.sh` for a new datestamped snapshot, new PROVENANCE
version entry, before/after gate, re-score, figures — and the settled count
for `\NumRefPlants` (0444) becomes **173**. If absorbed is kept, this note is
the informed-choice justification and the settled count stays **170**.

## Reproduction

```sh
# variant ODS = 8-cell edit of pipeline-2026-06-05.ods described above
uv run python data/reference/extract_ods.py --input <variant.ods> --output /tmp/units_var.csv
uv run python data/reference/aggregate_units.py --input /tmp/units_var.csv --output /tmp/plants_var.csv
uv run python data/reference/add_classifications.py --input /tmp/plants_var.csv --output /tmp/plants_var_classified.csv --fuel-col fuel
find experiments/outputs/exp1_batch2 -name '*.csv' -print0 | \
  xargs -0 -P8 -I{} uv run python -m aedist.evaluate evaluate {} \
    --reference /tmp/plants_var_classified.csv --output /tmp/rescore_var
# aggregate result_summary.tp/fp/fn over the 70 record.json per arm
```
