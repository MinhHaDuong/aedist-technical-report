# Prompt modules — verbatim extraction from prompt_complete.txt

Each `.txt` file is a **verbatim paragraph extraction** from
`experiments/prompts/prompt_complete.txt`. No abstraction, no rewording.
Assembling all modules reproduces the complete prompt (minus section headers).
This is enforced by `tests/test_modules_match_prompt_complete.py`.

`base.txt` is always included. Other modules are optional.

## Assembly

`harness.assemble_prompt(modules_dir, module_names)` composes the final
prompt. Module ordering is deterministic:

1. **persona** (prepended before base) — opening sentence, §intro
2. **overview** (prepended before base) — §1 Sector Overview content
3. **base** (always present) — §2 table spec with all 12 columns
4. **narratives** (appended) — §2 per-plant discussion: history + issues
5. **sourcing_ground** (appended) — §2 confidence rubric + Quality source-confidence rule
6. **statistics** (appended) — §3 cross-tabs a–c
7. **data_quality_table** (appended) — §3 d) confidence × fuel cross-tab
8. **bibliography** (appended) — §4 annotated bibliography
9. **citation_columns** (appended) — Quality: primary-source priority + URL fabrication guardrail
10. **observed_vs_projected** (appended) — Quality: OBSERVED vs PROJECTED distinction
11. **pdp_completeness** (appended) — Quality: PDP coverage + exhaustiveness + MWe units

The order is defined in `_MODULE_ORDER` in `src/aedist/harness.py`.

## Ablation semantics

`base.txt` includes Source 1/Source 2 in the table header (verbatim from
prompt_complete §2). Ablating `citation_columns` removes the quality
guardrails on sources (primary-source priority, URL fabrication warning)
but not the structural source-column requirement. This tests whether the
guardrail matters, not whether sources are requested at all.

`sourcing_ground` merges text from two sections of prompt_complete: the
confidence rubric from §2 and the source-confidence quality rule. Both
concern the same concept (confidence assessment) and ablate as one unit.

## Inspection

`make show-prompts` prints all composition variants with line counts.
