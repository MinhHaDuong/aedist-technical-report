# Experiment data

Data artifacts produced by or used in experiment runs.

## Contents

- **`rag_corpus`** — Symlink to `../../data/rag_corpus`. The canonical
  corpus lives in `data/rag_corpus`; do not add files here.

- **`converter_test/`** — PDF-to-markdown converter benchmark comparing
  6 tools on a 173-page Vietnamese government document. See its own
  [README.md](converter_test/README.md) for detailed results.

- **`web_portal_test.md`** — Web portal accessibility test (Tavily API)
  for Vietnamese government data sources. Conclusion: web search finds
  sources but cannot extract structured tabular data.
