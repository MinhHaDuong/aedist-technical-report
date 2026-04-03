Last updated: 2026-04-03

## Status

Pipeline end-to-end via Makefile. Census done (33 models, F1 2–66%, $0.73). 130 tests pass. Sweep 2 multiturn complete ($2.81). RAG corpus pipeline merged (PR #71): fully local via GROBID + Ollama. Sweep 2 RAG and web pending corpus build.

## Blockers

- Makefile OPENROUTER_API_KEY guard blocks non-OpenRouter targets (#75)

## Next actions

1. Build RAG corpus: `make build-corpus QUERY="quy hoạch điện"` (#10)
2. Run Sweep 2 RAG + web after corpus ready (#10)
3. Cost data for Pareto chart (#59)
4. Tabulate relances and comparaison after Sweep 2 (#47, #48)
5. Reframe slides: methods not models
