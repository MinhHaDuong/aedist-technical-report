# Prompts

Prompt templates used by the sweep configurations in `experiments.toml`.

| File | Used by sweeps | Description |
|------|---------------|-------------|
| `prompt_extract.txt` | census, census_local, multiturn, web, rag, decomposed | Main structured extraction prompt: list Vietnamese thermal plants as CSV |
| `prompt_cited.txt` | sourced | Same extraction task but requires source citations per entry |
| `prompt_complete.txt` | frontier | Comprehensive report prompt for reasoning models |
| `prompt_scenarios.txt` | frontier_scenarios | Scenario-based assessment variant |
| `prompt_followups.txt` | multiturn | Follow-up questions for multi-turn conversations |
