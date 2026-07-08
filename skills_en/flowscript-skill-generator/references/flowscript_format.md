# FlowScript Format

`FLOWSCRIPT.md` combines human-readable guidance with a DSL that a harness can parse. Keep exactly one primary `flow` block per file.

## Field Requirements

- Set `version` to integer `1` and `mode` to `controlled`.
- Point `inputs.schema` to a JSON Schema inside the package.
- Define ordered steps with unique snake_case IDs.
- The minimum node types are `llm`, `validator`, `script`, and `terminal`.
- Reference only the user request, current input/output bindings, or outputs from preceding steps.
- Declare an output as a path string or an object with `path`, `schema`, and `required`.
- Give every unbranched step one `next`; give every branch both `when` and `next`.
- Use `${step_id.output.key}` for prior outputs and `${input.key}` / `${output.key}` for current command bindings.
- Read control state from structured status files, never from stdout or free-form LLM text.

## LLM Nodes

Every LLM node must declare its prompt, tool, and output schema explicitly:

```flow
- id: parse_request
  type: llm
  input_mode: skill_inputs
  prompt:
    zh: prompts/parse_request_cn.md
    en: prompts/parse_request_en.md
  tool:
    name: submit_skill_inputs
    description:
      zh: 提交结构化输入
      en: Submit structured skill inputs
  input:
    request: ${user.request}
  output:
    params:
      path: runs/{run_id}/resolved_params.json
      schema: input_schema.json
  next: validate_params
```

The model submits schema-constrained content only. The runtime chooses the declared path and emits the `write_json` tool call; do not let the model choose arbitrary paths.

## Script and Validator Nodes

Declare `command` as an executable mapping, not an opaque shell string:

```flow
command:
  executable: python
  args:
    - scripts/validate.py
    - --input
    - ${input.params}
    - --output
    - ${output.status}
  accepted_exit_codes: [0, 1, 2]
  status_source: ${output.status}
  timeout_seconds: 30
```

- Make `args` match the script CLI exactly.
- Use `accepted_exit_codes` for business-level outcomes; a nonzero code is not automatically a runtime failure.
- Every branched command node must declare `status_source`.
- Point `status_source` to a JSON status file used by branch conditions.
- Set a positive `timeout_seconds`.

## States and Terminals

Use the standard machine states `valid`, `needs_input`, `invalid`, `success`, `recoverable_error`, and `fatal_error`.

A validation runtime may stop unsupported paths explicitly:

```flow
- id: request_clarification
  type: terminal
  reason: needs_input
```
