Last updated: 2026-04-03

## Status

Pipeline end-to-end via Makefile. Census done (28 cloud + 8 local models, best 107/163 plants, $0.73). 182 tests pass. Sweep 2 RAG complete (5 models × 3 runs, $0.89) — Mistral Small 4 finds 141/163 plants at $0.15/Mtok, beating GPT-5.4 at $2.50/Mtok. Sweep 2 multiturn running on Padme. Gold truth corpus: 18 manually verified tables (155 KB) from PDP7/PDP7A/PDP8/EVN/E542. Model selection with diversity constraints: --require-country for geographic representation (#88, PR #89). Slides wired to real data (PR #91).

## Blockers

- Makefile OPENROUTER_API_KEY guard blocks non-OpenRouter targets (#75)
- evaluate-all overwrites all_metrics.json instead of appending (#92)
- Padme: Gemma 4 model pulls still in progress (gemma4:26b + gemma4:31b)

## Next actions

1. Pull and evaluate sweep 2 multiturn results, wire into slides
2. Tabulate relances and comparaison (#47, #48)
3. Add Protocol interface + registry dispatch (#82)
4. LP solver warm start for faster evaluation (#90)
5. Table conversion benchmark across backends (#85)
6. Layout-aware converters: Marker + MinerU (#81, #83, #84)

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 28 cloud + 8 local models, best 107/163, $0.73
- [x] Gold truth RAG corpus: 18 tables from official sources
- [x] Sweep 2 RAG: 5 models × 3 runs, $0.89
- [x] Diversity model selection: 1 US + 1 CN + 1 FR frontier + 2 cheap (#88)
- [x] Slides wired to real data: census bars, regime comparison, cost/time scatter
- [ ] Sweep 2 multiturn: running on Padme
- [ ] Tabulate relances and comparaison (#47, #48)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Makefile: guard OPENROUTER_API_KEY only for sweep targets (#75)
- evaluate-all append/merge instead of overwrite (#92)
- LP solver warm start (#90)
- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep (#11) — needs reasoning models on Padme
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
