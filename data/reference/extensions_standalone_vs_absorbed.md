# Extension-as-unit vs standalone: net error measurement (ticket 0445)

**Date:** 2026-06-06. **Inputs:** master variant snapshot
`pipeline+extensions-as-plants-2026-06-05.ods` (author hand edit of the
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

## Net TP/FP/FN on Exp2 (80 runs, 4 arms × 4 agents × 5 reps)

The author's objection to the Exp1 cut: the FN losses concentrate in small
parametric-only models that Exp2 does not use. Exp2's agents are the big four
(claude-opus-4-6, gpt-5.5, mistral-large-2512, qwen3.7-max), web-enabled.
Same measurement on the Exp2 final plant tables
(`experiments/derived/arm{1..4}_flat/*_run*.md`, the fp_audit sweep machinery,
reconcile + metrics.py match-type classification, both arms identical code):

| Arm | TP | FP | FN | FP+FN |
|---|---|---|---|---|
| Absorbed (170) | 5322 | 500 | 8278 | **8778** |
| Standalone (173) | 5456 | 366 | 8384 | **8750** |
| Δ (standalone − absorbed) | +134 | −134 | +106 | **−28** |

**On Exp2, standalone wins the ticket's own decision rule** (−28 of 8778,
≈0.3%): web-enabled agents recall the extension plants 134/240 ≈ 56% of the
time (vs 66/210 ≈ 31% parametric in Exp1), so the FP→TP flips outweigh the
+3-row denominator. Cross-checked against the committed artifact after
adoption: re-deriving raw counts from `exp2_mart.jsonl` `score_summary`
ratios (TP = coverage × N, FP = TP(1−p)/p) reproduces the absorbed arm
exactly (TP 5322 / FP 500 / FN 8278) and gives net **−36** for standalone
(TP +138 / FP −138 / FN +102) — same sign, magnitude within the ±0.5/run
rounding of 4-decimal ratios. Per arm×agent cell: standalone better in 9/16, worse in
7/16 — anthropic and openai improve in every arm (−5 to −15), mistral worsens
in every arm (+3 to +15, it emits few extension rows), qwen mixed.

For completeness, Exp1 restricted to the four Exp2 models: opus −5,
gpt-5.5 −1, mistral-large +15, qwen3.7-max +3 → net **+12**, absorbed —
the parametric regime under-emits extensions even for big models; web access
is what changes the economics.

## Reading

The decision rule's sign depends on the panel:

- **Exp1, full 14-model panel:** absorbed wins (+78 of 10571, ≈0.7%; 10/14
  models). The margin comes from small parametric-only models that never
  emit extensions and pay pure FN for the 3 extra rows.
- **Exp2, the big four web-enabled agents:** standalone wins (−28 of 8778,
  ≈0.3%), and every flip is FP→TP with zero new FPs there too.

Both margins are sub-percent — scoring buys neither variant a material
advantage, and the FN side of the ledger is not panel-neutral: whether the 3
extra rows belong in the denominator **is** the ontological question under
decision, made numerical. What the measurement does settle: the original
worry — "absorption only increased errors" — is **not supported** (absorption
costs the vetoed-extension FPs but matches the parent-grain reference rows);
and conversely the standalone cost is borne almost entirely by models that
Exp2 does not use. The matching-quality gain of standalone is real wherever
extensions are emitted: 0–4% capacity diffs instead of 26% strained-parent
matches, and on Exp2 the mở-rộng/extension FP class visible in the 0446
matrix disappears into TPs.

Cost asymmetry of the decision itself: keeping absorbed = zero further work,
rule-consistent, count stays 170. Switching = master edit + new snapshot +
PROVENANCE entry + before/after gate + re-score + figures, and 0444 macroizes
at 173.

## Decision and artifact path (author ruled standalone, 2026-06-06)

The author adopted **standalone** (v2.1, 173 plants): the Exp2 cut carries
the call — the FN losses concentrate in small parametric-only models the SOTA
experiment does not use, and the 0446-matrix mở-rộng FP class dissolves.

The canonical path (edit the master, re-run `import.sh`) was impractical: the
master lives on the author's other machine. The hand-derived variant is
therefore committed as `raw/pipeline+extensions-as-plants-2026-06-05.ods`
(datestamp = the underlying capture; the `+extensions-as-plants` infix keeps
it out of the `pipeline-YYYY-MM-DD.ods` import-name family) and pinned by
`config.VN_THERMAL_MASTER_SNAPSHOT_ODS`, with the provenance exception
recorded in `PROVENANCE.md` § v2.1. **The master does not yet carry the
edit** — ticket 0458 (needs-human, deferred) tracks replaying it before any
future import/re-pin; until then a fresh import would silently revert the
adoption. `\NumRefPlants` (0444) macroizes at **173**.

## Artifact-level deltas (adoption gate, v2 → v2.1)

Every reference-dependent artifact regenerated; each delta traces to the
4-row grain change or its re-score:

| Artifact | Delta | Traces to |
|---|---|---|
| `vietnam_thermal_*_v2*.csv` | 254 units relabeled on 4 rows; 170 → 173 plants | the 8-cell edit |
| `measurements.jsonl` | exactly 70 exp1_batch2 rows replaced (tp+fn ≡ 173); universe fixed at 562 | re-score |
| `exp2_mart.jsonl` | 160 rows, `score_summary` changes on the 80 scored runs only | re-score |
| `sota_cross_eval.csv` / `exp1_cross_eval.csv` | all rows re-scored, `reference=v2_classified` | re-score |
| `macros.tex` / `macros_slides.tex` | `\NumRefPlants` 170 → 173 | count |
| `macros_exp1_matrix.tex` | `\ExpOneMatrixPlants` 170 → 173; FP-panel count recomputed | count + FP→TP flips |
| `fig_exp1_recognition_matrix*.pdf` (en/fr/strong/top) | +4 extension columns (−1 Uong Bi II), Uong Bi I moves to Retired band; recoverable mở-rộng FPs leave the top-40 panel | grain change |
| `tab_reconciliation.tex` | Expert plants 170 → 173 | count |
| `tab_status_difficulty.tex` | Ensemble 173; operational 56, retired 2 | status flip |
| `macros_p1_base.tex` | `\CensusTPMax` 113 → 116 (best run recalls the 3 extra plants) | re-score |
| exp2 figures/tables (`fig_exp2_*`, `tab_exp2_2x2*`) | coverage denominators and scores re-derived | re-score |
| `tab_census.tex`, `macros_census.tex` | **unchanged** — frozen v1-era relics (PROVENANCE re-score scope; deferred 0444). Their render recipes crash on the post-0422 mart (zero `census` rows) — pre-existing at HEAD, not introduced here | — |
| `tab_self_consistency.tex`, `tab_verification.tex` | regenerated but **still render from v1-era mart rows** (rag_consistency 26, verification 4 — kept v1-scored, same scope as 0413; deferred 0444). Deliberate mixed vintage, not an oversight | — |

Status distribution shift (v1-compat projection): operational 54 → 56,
retired 1 → 2, others unchanged (sum 173) — verified from the release CSV.

## Re-score protocol note (v2.1 flip)

A reference flip changes *scores*, not the mart's *row universe*. The
committed `measurements.jsonl` universe (562 rows) is not reproducible by a
fresh `rebuild-measurements`: the census-era records are restorable-only
(raw replies archived, 0422), and the Exp2 turn records — present in the
tree but created *after* mart assembly in the canonical `all-outcomes`
ordering — pollute any assemble that runs while they sit on disk (+149
rows). The v2.1 re-score therefore re-evaluated the reference-dependent
records in place (exp1_batch2, exp1/sota cross-evals, exp2_mart) and patched
exactly those 70 exp1 rows into the committed mart, mirroring the 0413
scope: census/SC rows remain v1-era record (deferred, 0444). Transient
`reconciliation_*.csv` siblings must be cleaned from `outputs/exp1_batch2/`
before `score_exp1` runs — its filename glob swallows them as models.

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
