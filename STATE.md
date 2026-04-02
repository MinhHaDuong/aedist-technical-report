Last updated: 2026-04-02

## Status

Monorepo merged. Census done (32 models, $0.73). Diacritics was not a bug — cleaner already strips accents. The earlier 0% F1 was from running old code. Re-evaluating with current code.

## Blockers

None

## Next actions

1. Re-evaluate census with current code (running now)
2. Select top 5 + best local model → models_top5.yaml (#20)
3. Run Sweep 2: information regimes (#10)
4. Update convert.py for flat output structure (#19)
5. Generate tables, build slides (#14, #15)
