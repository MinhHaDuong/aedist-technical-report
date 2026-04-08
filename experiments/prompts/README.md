# Prompts

Prompt templates used by the sweep configurations in `experiments.toml`.

| File | Used by sweeps | Description |
|------|---------------|-------------|
| `prompt_structured.txt` | census, census_local, multiturn, web, rag, decomposed | Main structured prompt: list Vietnamese thermal plants as CSV |
| `prompt_structured_sourced.txt` | sourced | Same task but requires source citations per entry |
| `prompt_frontier.txt` | frontier | Comprehensive report prompt for reasoning models |
| `prompt_frontier_scenarios.txt` | frontier | Scenario-based assessment variant |
| `prompt_frontier_skill.txt` | frontier | Skill/capability assessment variant |
| `followups.txt` | multiturn | Follow-up questions for multi-turn conversations |
