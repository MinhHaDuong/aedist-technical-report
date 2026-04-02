Last updated: 2026-04-02

## Status

Monorepo merged (PR #18). Census done (32 models, $0.73). Blocked on diacritics fix before F1 scores are meaningful. convert.py updated for flat output structure (#19). models_top5.yaml created with 4 frontier + 4 local models (#20).

## Blockers

1. **Matcher diacritics bug**: LLM outputs use ASCII names, reference uses Vietnamese diacritics. F1 near 0% is an artifact — GPT-5.4 actually found 76 plants. Fix: strip accents before fuzzy matching.

## Next actions

1. Fix diacritics in matcher, re-evaluate census (refine #20 ranking)
2. Run Sweep 2: information regimes (#10)
3. Generate tables, build slides (#14, #15)
