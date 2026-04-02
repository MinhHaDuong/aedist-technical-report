Last updated: 2026-04-02

## Status

Monorepo merged (PR #18). Census done (32 models, $0.73). Blocked on diacritics fix before F1 scores are meaningful.

## Blockers

1. **Matcher diacritics bug**: LLM outputs use ASCII names, reference uses Vietnamese diacritics. F1 near 0% is an artifact — GPT-5.4 actually found 76 plants. Fix: strip accents before fuzzy matching.

## Next actions

1. Fix diacritics in matcher, re-evaluate census (#20 depends on this)
2. Update convert.py for flat output structure (#19)
3. Select top 5 + best local model → models_top5.yaml (#20)
4. Run Sweep 2: information regimes (#10)
5. Generate tables, build slides (#14, #15)
