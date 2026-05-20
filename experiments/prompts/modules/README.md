# Prompt modules — verbatim extraction from prompt_complete.txt

Each `.txt` file is a **verbatim paragraph extraction** from
`experiments/prompts/prompt_complete.txt`. No abstraction, no rewording.
Modules include their section headers (`## Goal`, `## Structured power
plants table`, etc.). Assembling all modules reproduces the complete prompt
(modulo whitespace).

The file naming scheme uses ordering prefixes so lexicographic sort by
filename matches the natural reading order of the assembled prompt:

| File | Role |
|---|---|
| `1_persona.txt` | Opening role statement |
| `2_goal.txt` | Task declaration (always included) |
| `3_overview.txt` | Sector overview |
| `4_narratives.txt` | Per-plant discussion |
| `5_table.txt` | Structured table specification (always included) |
| `6_bibliography.txt` | Annotated bibliography |
| `A_Statistics.txt` | Cross-tabulations |
| `B_Temporality.txt` | Observed vs projected discipline |
| `C_Uncertainty.txt` | Confidence levels and source guardrails |
| `D_Completeness.txt` | Exhaustiveness across lifecycle stages |

## Assembly

`harness.assemble_prompt(modules_dir, module_names)` composes the final
prompt at call time. The two modules in `ALWAYS_MODULES`
(`2_goal` and `5_table`) are always included; the caller's `module_names`
list adds optional modules. The union is sorted lexicographically by
filename and joined with `"\n\n"`.

The locked Experiment 1 baseline is `assemble_prompt(modules_dir, [])` —
just the always-pair (`2_goal` + `5_table`). Ablations opt in by listing
additional modules in the sweep's `prompt_modules` field in
`experiments.toml` (drop `2_goal` and `5_table` from those lists since
they are always included).

`assemble_prompt` raises `ValueError` when `module_names` contains a name
that does not resolve to a `<name>.txt` file in `modules_dir`.

## Inspection

`make show-prompts` prints all composition variants with line counts.
