Last updated: 2026-04-02

## Status

Wave 1 complete. Census queries done (32 models, 97 JSON, $0.73 spent). Evaluation pipeline has a matching bug — diacritics prevent name reconciliation.

## Blockers

1. **Matcher diacritics bug**: LLM outputs use ASCII ("Vung Ang"), reference uses Vietnamese ("An Khánh"). Fuzzy matcher doesn't bridge. F1 scores near 0% are artifacts. GPT-5.4 actually found 76 plants.
2. Padme model pulls failed (network timeout) — retry later.

## Next actions

1. Fix diacritics normalization in cleaner/matcher — strip accents before comparison
2. Re-run evaluate-all with fixed matcher → real F1 scores
3. Run summarize_sweep.py → census results table
4. Select top 5 + best local for Sweep 2
5. Waves 3-4: information regimes, tables, slides
