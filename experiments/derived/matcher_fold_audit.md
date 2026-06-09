# Ticket 0500 — diacritic-folding confound audit (audit only)

**Status:** audit steps 1–2 complete. Decision branch (step 3) recorded as a
recommendation; the production matcher is **not** changed (author-gated,
`needs-human`). Ticket 0500 stays open.

## Headline

**IMMATERIAL to the paper's reported Exp1/2/3 numbers. The ticket's core
premise is refuted: the production matcher already folds Vietnamese diacritics
on BOTH sides.** No fix, no re-score, no manuscript number changes warranted.

The 67%→88% GEM gap that motivated the ticket came from the **throwaway 0486
prototype** (`/tmp/wt-0486/explore_*.py`, now gone) which compared GEM names
against the reference *without* the cleaner. That prototype is not the path that
scores model output. The production scoring path does fold.

## Why the premise is false (structural proof)

The Exp1/2/3 accuracy path is:

```
score_mechanical.score_accuracy
  → reconcile.reconcile(reference, system)        # reconcile.py:285
     → plants_to_dataframe()                        # reconcile.py:66
        → PowerPlantDataframeCleaner.clean_dataframe → clean_name → clean_text
           # cleaner/cleaner.py:111-114: NFD decomposition + drop Mn + đ→d
     → matching.lp.reconcile()  on the folded `name_clean` column
```

`clean_text` ASCII-folds **and** normalizes Roman→Arabic numerals, applied to
**both** reference and system before the LP match. Literal demonstration
(production cleaner, production config):

| raw | `name_clean` |
|-----|--------------|
| `Cà Mau I` | `ca mau 1` |
| `Ca Mau 1` | `ca mau 1` |
| `Bà Rịa GT` | `ba ria gt` |
| `Nhà máy nhiệt điện Vĩnh Tân 4` | `vinh tan 4` |
| `Vinh Tan 4` | `vinh tan 4` |

The model's diacritic-vs-ASCII choice is erased *before* matching. The confound
structurally cannot exist in the scoring path.

## Step 1 — model-output naming characterization

`experiments/derived/matcher_fold_step1_naming.csv`. Fraction of each model's
raw plant-name strings carrying diacritics, Exp1 (70 runs):

| model | n_names | frac_diacritic | frac_ascii |
|-------|--------:|---------------:|-----------:|
| claude-haiku-4.5 | 297 | 1.00 | 0.00 |
| claude-opus-4.6 | 475 | 1.00 | 0.00 |
| claude-sonnet-4.6 | 560 | 1.00 | 0.00 |
| deepseek-v4-flash | 225 | 0.70 | 0.30 |
| deepseek-v4-pro | 298 | 1.00 | 0.00 |
| gpt-5.5 | 427 | 0.995 | 0.005 |
| gpt-oss-120b | 288 | 1.00 | 0.00 |
| gpt-oss-20b | 349 | 0.42 | 0.58 |
| mistral-large-2512 | 234 | 1.00 | 0.00 |
| mistral-medium-3-5 | 315 | 1.00 | 0.00 |
| mistral-small-2603 | 294 | 1.00 | 0.00 |
| qwen3.6-35b-a3b | 200 | 1.00 | 0.00 |
| qwen3.6-flash | 703 | 1.00 | 0.00 |
| qwen3.7-max | 218 | 1.00 | 0.00 |

Most models emit full diacritics; `gpt-oss-20b` (58% ASCII) and
`deepseek-v4-flash` (30% ASCII) are the ASCII emitters. **Notably, the confound
bites from the *reference* side, not the model side:** the 180-plant reference
is itself only 69% diacritic — 31% of reference rows are ASCII-stored
("Vung Ang 1", "Cong Thanh", "Cam Pha 3"). Folding bridges *both* directions.

## Step 2 — A/B re-score: production fold vs folding-DISABLED counterfactual

`experiments/derived/matcher_fold_ab_delta.csv`. Per-model mean over 5 runs.
`*_fold` = production (folding on). `*_nofold` = counterfactual with the
NFD/Mn diacritic strip removed from `clean_text`. **The informative
counterfactual is "what if folding were absent," because folding is already
present in production.**

| model | tp_fold | tp_nofold | ΔTP | f1_fold | f1_nofold | ΔF1 |
|-------|--------:|----------:|----:|--------:|----------:|----:|
| claude-haiku-4.5 | 33.0 | 15.4 | +17.6 | 0.275 | 0.129 | +0.147 |
| claude-opus-4.6 | 90.6 | 64.4 | +26.2 | 0.659 | 0.469 | +0.190 |
| claude-sonnet-4.6 | 92.8 | 67.0 | +25.8 | 0.633 | 0.459 | +0.174 |
| deepseek-v4-flash | 42.8 | 27.8 | +15.0 | 0.369 | 0.240 | +0.129 |
| deepseek-v4-pro | 57.0 | 40.6 | +16.4 | 0.468 | 0.333 | +0.135 |
| gpt-5.5 | 83.2 | 62.0 | +21.2 | 0.627 | 0.467 | +0.160 |
| gpt-oss-120b | 16.6 | 13.6 | +3.0 | 0.138 | 0.112 | +0.025 |
| gpt-oss-20b | 2.6 | 2.0 | +0.6 | 0.024 | 0.018 | +0.006 |
| mistral-large-2512 | 46.0 | 33.0 | +13.0 | 0.401 | 0.288 | +0.113 |
| mistral-medium-3-5 | 57.4 | 45.4 | +12.0 | 0.471 | 0.373 | +0.098 |
| mistral-small-2603 | 50.2 | 34.4 | +15.8 | 0.417 | 0.286 | +0.131 |
| qwen3.6-35b-a3b | 23.4 | 14.4 | +9.0 | 0.209 | 0.129 | +0.080 |
| qwen3.6-flash | 19.6 | 13.6 | +6.0 | 0.157 | 0.108 | +0.049 |
| qwen3.7-max | 46.0 | 31.2 | +14.8 | 0.403 | 0.274 | +0.129 |

**Interpretation.** Folding is **load-bearing** (mean ≈ +0.12 F1, up to +0.19)
**AND already correctly applied in production**. The disable-folding column is
*not* the production state — it is what the numbers *would* be if folding were
absent. So:

- The paper's reported numbers are the `*_fold` (high) numbers.
- The undercount the ticket feared (fold missing → model TPs lost → "models
  fall short of research-grade recall" spuriously inflated) **does not occur**.
- If anything this *strengthens* the headline finding: even with folding
  generously crediting every diacritic/ASCII/numeral variant, models still fall
  short; without folding they would look worse.

**Sanity gate.** The `*_fold` branch reproduces the committed
`exp1_cross_eval.csv` run-pattern exactly (e.g. claude-haiku-4.5 runs
1/3/5 low, 2/4 high) at a uniform ~0.008 F1 offset. The offset is a known
artifact: `exp1_cross_eval.csv` was last touched by `fix(0453): restore
pre-rerun F1` and predates a clean re-score against the 180-plant reference; the
A/B *delta* is computed within one consistent reference and is unaffected.

## Verified recovered match-pairs (genuine same-plant variants)

From `claude-opus-4.6-run1` (matched under fold, lost under nofold). All are
ASCII-reference ↔ diacritic-model or numeral variants — genuine:

| reference (ASCII or mixed) | model (diacritic) | variant kind |
|----------------------------|-------------------|--------------|
| `Cong Thanh` | `Nhiệt điện Công Thanh` | ASCII ref ↔ diacritic model (the confound) |
| `Cà Mau I` | `Nhiệt điện Cà Mau 1` | Roman→Arabic numeral |
| `An Khánh - Bac Giang` | `Nhiệt điện An Khánh – Bắc Giang (TBKHÍ)` | partial diacritic + facility prefix |
| `Bạc Liêu 1` | `Nhiệt điện Bạc Liêu (than)` | facility prefix + fuel suffix |
| `Cao Ngạn` | `Nhiệt điện Cao Ngạn` | facility prefix only |

## False-positive collision check

**Zero folding-induced false positives.** The LP matcher enforces a global 1:1
assignment, so within any single run no reference matches two systems and no
system matches two references (verified on opus-run1: 0 collisions, 89 pairs).

A scan of all 70 Exp1 runs found 16 runs with one system row matching two
reference plants — but these are **combined-grain rows** ("Nhà máy điện Cà Mau
1 & 2" → reference "Ca Mau 1" + "Ca Mau 2"), the deliberate `_split_combined_units`
behavior (matching/lp.py), **not** a folding artifact. Confirmed by running
qwen3.7-max-run4 under fold vs nofold: the collision count is **identical (6 = 6)**
in both — folding adds genuine TP (35→44) and introduces **no** new collisions.
The grain issue is orthogonal and already tracked in ticket 0498.

## Recommendation (decision is the author's)

1. **IMMATERIAL to reported numbers — close as a non-finding, no production
   matcher change, no re-score, no manuscript edit.** The premise ("matcher does
   not fold") is false for the production path; the GEM 67/88 gap was a
   prototype-only artifact.

2. **Follow-up worth a guard (offer, needs-human):** the diacritic fold in
   `clean_text` is load-bearing (~0.12 F1/model) but **untested**. A future
   refactor that drops the NFD/Mn strip would silently cut F1 across every model
   and spuriously *strengthen* the "models fall short" finding. Recommend a
   regression test asserting a known diacritic/ASCII pair
   ("Cong Thanh" ↔ "Công Thanh", "Cà Mau I" ↔ "Ca Mau 1") matches through the
   scoring matcher — protecting behavior that already exists. (Ticket 0500's
   step-3 test was conditioned on a fix being warranted; this guard is for the
   *existing* fold, a slightly different rationale.)

## Reproduction

Throwaway harness: `/tmp/audit_0500/run_audit.py` (not productionized — it
monkeypatches `clean_text` to disable folding; an experimental scoring path,
deliberately kept out of `src/`). Artifacts committed:
`matcher_fold_ab_delta.csv`, `matcher_fold_step1_naming.csv`, this note.
