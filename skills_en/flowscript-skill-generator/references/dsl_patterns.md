# DSL Patterns

Use the smallest pattern that expresses the constraints. The model generates schema-constrained content only; the runtime owns order, commands, paths, persistence, and branches.

## Input Parsing

Use `input_mode: skill_inputs`, a prompt, a dedicated tool, and `input_schema.json`. Declare both `path` and `schema` for the output.

## LLM Content Nodes

Interpretation, summarization, and rewrite nodes must:

- Read declared input artifacts.
- Use a node-specific prompt.
- Use a dedicated submission tool rather than generic `write_file`.
- Store the output schema under `schemas/`.
- Let the runtime write tool arguments to the declared path.

## Deterministic Script Nodes

Build argv from `command.executable` and `command.args`. Bind paths explicitly through `${input.*}` and `${output.*}`. Declare accepted exit codes, a status source, and a timeout.

## Controlled Branches

```flow
branches:
  valid:
    when: ${validate_params.output.status.state} == "valid"
    next: execute_main
  needs_input:
    when: ${validate_params.output.status.state} == "needs_input"
    next: request_clarification
```

Branch only on explicit structured-field comparisons. Do not use `eval`, infer success from stdout, or let the model choose a branch.

## Validation-Only Terminals

When clarification or fallback is not implemented, stop explicitly with a `terminal` node instead of pretending the run succeeded:

```flow
- id: execution_stopped
  type: terminal
  reason: execution_failed
```
