# Skill Package Contract

## Dual-Mode Contract

`SKILL.md` guides ordinary agents, while `FLOWSCRIPT.md` defines harness execution. Both modes share one input schema, one set of script interfaces, and one artifact contract.

Use lowercase letters, digits, and hyphens for the directory and frontmatter `name`. Keep only `name` and `description` in SKILL.md frontmatter. Omit `transform.py` when there is no LLM transformation step, omit `finalize.py` when the main script produces the final result, and do not add redundant files such as a README.

## Inputs and Scripts

Store model instructions under `prompts/` and schemas for non-input LLM outputs under `schemas/`. Use JSON Schema Draft 2020-12 for `input_schema.json`. Keep required fields few and explicit, set `additionalProperties` deliberately, place stable defaults in the schema, and mark genuinely unknown business constraints with `TODO`. Return `needs_input` and `missing_fields` when a value requires user confirmation.

```text
python scripts/validate.py --input <input JSON> --output <status JSON> --normalized-output <normalized JSON>
python scripts/execute.py --input <normalized JSON> --output <result JSON> --status-output <status JSON>
```

Prefer the standard library. Use UTF-8, create declared output directories, and write both results and structured status files. Do not leave final results only on stdout, access undeclared paths, or silently call commands outside the package.

## Artifacts and Fallback

Persist every critical step, including LLM outputs. The artifact manifest must identify the primary result, editable artifacts, status files, and logs.

On a recoverable failure, write `runs/{run_id}/artifacts/fallback_context.json` with `original_user_input`, `failed_step`, `completed_steps`, `available_artifacts`, `error_logs`, and `suggested_recovery_actions`. Ordinary mode must read this file first and continue from the most recent valid artifact instead of discarding completed work.

`examples/input.example.json` must either pass validation or intentionally demonstrate `needs_input`. Store one JSON object per line in `tests/replay_cases.jsonl`, covering success, missing input, and invalid input when those branches apply.