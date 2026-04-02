Last updated: 2026-04-02

## Status

Wave 1 complete (7/7 WPs merged). Wave 2 (model census) scripts ready, blocked on infra.

## Blockers

1. OpenRouter API key expired — renew at openrouter.ai
2. Padme Ollama service not running — start with `ssh padme "ollama serve"`

## Next actions

1. Fix blockers, then run `bash scripts/sweep1_census.sh` from aedist/ (WP8)
2. Wave 3: Sweeps 2-5 (WP9-WP12) — after census selects top 5 models
3. Wave 4: Results → LaTeX tables (WP13) + Beamer slides (WP14)
4. Final PR and merge (WP15)
