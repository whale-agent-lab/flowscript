# Post-Generation Validation Checklist

- [ ] The directory name matches the frontmatter `name` and follows naming rules.
- [ ] Frontmatter contains only `name` and a description that covers capabilities and triggers.
- [ ] `agents/openai.yaml` is current and `default_prompt` mentions `$skill-name`.
- [ ] No template placeholders, unused files, or redundant README-style documents remain.
- [ ] `FLOWSCRIPT.md` contains one primary `flow` block with version, mode, schema, and steps.
- [ ] Step IDs are unique; script commands point to existing files; references target declared outputs from preceding steps.
- [ ] Every script/validator uses executable + argv args that match its CLI and declares accepted_exit_codes, status_source, and timeout_seconds.
- [ ] Every LLM node has an existing prompt, dedicated tool, and output schema; its output declares both path and schema.
- [ ] Every branch has `when` and `next`, and each condition uses structured state.
- [ ] Failure states lead to clarification, fallback, or explicit termination.
- [ ] The schema is valid JSON, declares Draft 2020-12, and matches the example input.
- [ ] Python scripts pass `python -m py_compile` and their parameters match the DSL.
- [ ] Scripts write structured status and declared artifacts; the manifest matches actual paths.
- [ ] Every replay JSONL line parses independently.

Minimum commands:

```text
python -m json.tool input_schema.json
python -m py_compile scripts/validate.py scripts/execute.py
python scripts/validate.py --input examples/input.example.json --output runs/validation_status.json --normalized-output runs/valid_params.json
python scripts/execute.py --input runs/valid_params.json --output runs/result.json --status-output runs/execution_status.json
```

Report only checks that actually ran. List remaining business TODOs, assumptions, dependencies, and boundaries that still need confirmation.