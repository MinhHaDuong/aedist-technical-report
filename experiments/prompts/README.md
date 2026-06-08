# Prompts

Prompt templates used by the sweep configurations in `experiments.toml`.

| File | Used by sweeps | Description |
|------|---------------|-------------|
| `prompt_extract.txt` | census, census_local, multiturn, web, rag, decomposed | Main structured extraction prompt: list Vietnamese thermal plants as CSV |
| `prompt_cited.txt` | sourced | Same extraction task but requires source citations per entry |
| `prompt_complete.txt` | frontier | Comprehensive report prompt for reasoning models |
| `prompt_scenarios.txt` | frontier_scenarios | Scenario-based assessment variant |
| `prompt_followups.txt` | multiturn | Follow-up questions for multi-turn conversations |

---

## ADR: Prompt modularization scope for Exp 2 and Exp 3 (ticket 0269)

**Decision: accepted divergence (option c).** Exp 1 modules and Exp 2/3 prompts
remain independent sources of truth. The naive arm prompt (`protocol_07_naive_prompt.md`)
is a frozen experimental stimulus and must not be modified or regenerated.

### Divergence map

| Source | Columns | Sections not in Exp 1 modules |
|--------|---------|-------------------------------|
| `modules/2_goal.txt` + `modules/5_table.txt` (Exp 1 baseline) | 13 | — |
| `sota/protocol_07_naive_prompt.md` (Exp 2 naive arm — frozen) | 15 | QUALITY DIMENSIONS, CONTEXT (source rules, confidence vocab, asset-row rules) |
| `sota/protocol_02_metaprompt.md` (Exp 2/3 optimised arm — frozen) | 15 | ROLE, QUALITY DIMENSIONS, FORMAT, CONTEXT (budget, planning, tools, source rules, confidence vocab, asset-row rules) |

The two extra columns in Exp 2/3 (`Status as-of-date`, `Confidence`) and the
whole-section additions (source admissibility, confidence calibration, asset-row
rules) have no module counterpart. Option (a) — assembling the naive prompt from
modules — would produce a semantically different prompt (it would include
`3_overview.txt` and `A_Statistics.txt` that the naive prompt explicitly bans).
Option (b) — regenerating the frozen file — is excluded by the stimulus-freeze
constraint. Both options require authoring new modules that do not correspond to
`prompt_complete.txt`, breaking the `test_modules_cover_prompt_complete` invariant.

The sections shared verbatim between the naive prompt and the metaprompt (source
quality management, calibrated confidence vocabulary, asset-row rules) suggest a
future extraction opportunity if a third experiment warrants a new prompt with the
same rules, but that refactoring would require unfreezing or replacing the existing
stimuli — out of scope here.

### Evidence-pack preamble (Exp 3)

The one concrete modularization performed: `harness.assemble_evidence_pack()` now
reads its introductory sentence from `modules/7_evidence.txt` instead of a
hardcoded string. This gives the text a version-controlled home alongside the other
modules, making future updates auditable. The `7_evidence` module is **not** part
of `assemble_prompt()` / Exp 1 assembly; `test_modules_cover_prompt_complete`
explicitly excludes it.
