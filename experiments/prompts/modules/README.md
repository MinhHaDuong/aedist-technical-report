# Prompt modules

Each `.txt` file is a self-contained prompt component.
`base.txt` is always included. Other modules are optional.

## Assembly

`harness.assemble_prompt(modules_dir, module_names)` composes the final
prompt. Module ordering is deterministic:

1. **persona** (prepended before base)
2. **base** (always present)
3. **overview** (appended)
4. **sourcing** (appended)
5. **narratives** (appended)
6. **bibliography** (appended)
7. **statistics** (appended)

The order is defined in `_MODULE_ORDER` in `src/aedist/harness.py`.
To add a new module: create the `.txt` file here and add its name to
`_MODULE_ORDER` at the appropriate position.

## Inspection

`make show-prompts` prints all composition variants with line counts.
