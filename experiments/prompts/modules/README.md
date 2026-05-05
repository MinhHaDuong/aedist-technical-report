# Prompt modules — verbatim extraction from prompt_complete.txt

Each `.txt` file is a **verbatim paragraph extraction** from
`experiments/prompts/prompt_complete.txt`. No abstraction, no rewording.
Modules include their section headers (`## 1.`, `### Structured table`, etc.).
Assembling all modules reproduces the complete prompt (modulo whitespace).
This is enforced by `tests/test_modules_match_prompt_complete.py`.

`base.txt` is always included. Other modules are optional.

## Assembly

`harness.assemble_prompt(modules_dir, module_names)` composes the final
prompt. Module ordering is deterministic:

1. **persona** (prepended before base) — opening sentence
2. **overview** (prepended before base) — §1 Sector Overview
3. **base** (always present) — §2 Plant-by-Plant Inventory table spec (12 columns incl. Source 1/2)
4. **narratives** (appended) — §2 Per-plant discussion (history, issues, HIGH/MEDIUM/LOW confidence)
5. **statistics** (appended) — §3 cross-tabs a–c
6. **data_quality_table** (appended) — §3 d) confidence × fuel cross-tab
7. **bibliography** (appended) — §4 Annotated Bibliography
8. **sourcing_ground** (appended) — Quality instructions header + bullets 1–2 (primary sources, cite or mark LOW)
9. **citation_columns** (appended) — Quality bullet 3 (URL fabrication guardrail)
10. **observed_vs_projected** (appended) — Quality bullet 4 (OBSERVED vs PROJECTED)
11. **pdp_completeness** (appended) — Quality bullets 5–7 (PDP coverage, exhaustiveness, MWe units)

The order is defined in `_MODULE_ORDER` in `src/aedist/harness.py`.

## Ablation semantics

`base.txt` includes Source 1/Source 2 in the table header (verbatim from
prompt_complete §2). Ablating `citation_columns` removes the URL-fabrication
guardrail but not the structural source-column requirement. This tests
whether the guardrail matters, not whether sources are requested at all.

## Inspection

`make show-prompts` prints all composition variants with line counts.
