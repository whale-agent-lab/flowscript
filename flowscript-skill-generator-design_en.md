# FlowScript Skill Generator Design Document

## 1. Background

FlowScript is a dual-mode skill format: ordinary agents can read and execute it as a Markdown skill, while harness agents can parse its DSL and execute it as a controlled workflow.

To enable Codex to generate this type of skill package reliably, a dedicated "meta-skill" is needed. This meta-skill does not perform business tasks directly; instead, it guides Codex in generating, validating, and iterating on a complete FlowScript skill package based on user requirements.

This document describes the design of `flowscript-skill-generator`.

## 2. Goals

The goal of `flowscript-skill-generator` is to help Codex generate convention-compliant FlowScript skill packages, including:

- A `SKILL.md` readable by ordinary agents
- A `FLOWSCRIPT.md` executable by harness agents
- An input parameter schema
- Script directories and script interface conventions
- Artifact and log directory conventions
- A controlled-branching DSL
- A context contract for falling back to ordinary skill mode
- Optional replay test and validation guidance

Its focus is not on generating one-off prompts, but on producing reusable, testable, versionable skill assets with execution constraints.

## 3. Non-Goals

This meta-skill is not responsible for:

- Replacing a complete workflow engine
- Automatically generating every complex branch
- Automatically guaranteeing the correctness of script logic
- Directly executing the target business skill
- Converting arbitrary natural-language tasks into production-grade workflows
- Handling compliance, permission, or security policies tightly coupled to a specific business domain

It is responsible only for generating the structure, contracts, and initial implementation draft of a FlowScript skill package.

## 4. Use Cases

A user asks Codex:

```text
Help me create a FlowScript skill for a type of scriptable task.
```

After loading `flowscript-skill-generator`, Codex should:

1. Understand the target skill's inputs, outputs, and execution boundaries.
2. Determine whether the skill is suitable for FlowScript.
3. Design the relationship between ordinary skill mode and FlowScript mode.
4. Generate the standard directory structure.
5. Write `SKILL.md`.
6. Write `FLOWSCRIPT.md`.
7. Write scripts or script stubs.
8. Write the input schema.
9. Write the artifact, log, and fallback contracts.
10. Generate minimal testing guidance.

## 5. Skill Package Structure

The generated target skill should use the following structure:

```text
skills/
  target-skill/
    SKILL.md
    FLOWSCRIPT.md
    input_schema.json
    scripts/
      validate.py
      execute.py
      transform.py
      finalize.py
    references/
      flow_contract.md
      artifact_contract.md
    tests/
      replay_cases.jsonl
    examples/
      input.example.json
      artifacts.example.json
```

The structure may be trimmed for different skills:

- If there is no LLM transform node, `transform.py` may be omitted.
- If the final artifact is generated directly by the main script, `finalize.py` may be omitted.
- If the skill is only a design draft, script placeholder files and interface documentation may be generated first.

## 6. Meta-Skill Structure

`flowscript-skill-generator` should itself exist as an ordinary skill:

```text
skills/
  flowscript-skill-generator/
    SKILL.md
    references/
      flowscript_format.md
      skill_package_contract.md
      dsl_patterns.md
      validation_checklist.md
    templates/
      SKILL.md.template
      FLOWSCRIPT.md.template
      input_schema.json.template
      validate.py.template
      execute.py.template
      replay_cases.jsonl.template
```

Where:

- `SKILL.md`: Tells Codex when to use this meta-skill and describes the generation process.
- `references/flowscript_format.md`: Describes the FlowScript DSL.
- `references/skill_package_contract.md`: Describes the target skill package structure.
- `references/dsl_patterns.md`: Describes patterns such as linear flows, controlled branches, and fallbacks.
- `references/validation_checklist.md`: Provides the post-generation checklist.
- `templates/`: Provides reusable templates.

## 7. Trigger Conditions

Codex should use this skill in the following situations:

- The user asks to create a FlowScript skill.
- The user asks to convert an ordinary skill to FlowScript.
- The user asks to create a dual-mode skill/workflow package for a scriptable task.
- The user asks to generate a skill package containing `SKILL.md`, `FLOWSCRIPT.md`, and scripts.
- The user mentions harness agents, controlled execution, DSL skills, or workflow-capable skills.

It should not be used automatically in the following situations:

- The user only asks for an ordinary script.
- The user only asks for a one-off prompt.
- The user only asks for an architectural analysis and does not need files generated.
- The user asks for a complete business system implementation rather than skill package design.

## 8. Input Collection

The meta-skill should first collect or infer the following information.

### 8.1 Basic Information

| Field | Description |
|---|---|
| `skill_name` | Skill name; the basis for the directory name and frontmatter `name` |
| `purpose` | Purpose of the skill |
| `trigger` | When to use the skill |
| `ordinary_agent_behavior` | How an ordinary agent executes it |
| `flowscript_behavior` | How a harness agent executes it |
| `expected_outputs` | Expected artifacts |

### 8.2 Input Parameters

| Field | Description |
|---|---|
| `required_inputs` | Required parameters |
| `optional_inputs` | Optional parameters |
| `defaults` | Default values |
| `clarification_rules` | When to ask the user for clarification |
| `validation_rules` | Programmatic validation rules |

### 8.3 Execution Steps

| Field | Description |
|---|---|
| `deterministic_steps` | Steps that should be executed by scripts |
| `llm_steps` | Transformation or interpretation steps that should be executed by the model |
| `artifact_handoffs` | File handoffs between steps |
| `branch_points` | Controlled branch points |
| `fallback_points` | Fallback points |

If the user has not provided enough information, Codex should generate a reasonable draft and mark `TODO` items in the documentation instead of inventing precise business rules.

## 9. Generation Process

When using this meta-skill, Codex should proceed in the following order.

```text
1. Read user request
2. Determine whether FlowScript is appropriate
3. Design target skill contract
4. Generate file tree
5. Write SKILL.md
6. Write FLOWSCRIPT.md
7. Write input_schema.json
8. Write scripts or script stubs
9. Write references and examples
10. Run static validation if possible
11. Summarize generated package and TODOs
```

Important constraints:

- Design the contracts before writing files.
- Define artifacts before defining scripts.
- Define fallbacks before defining complex branches.
- Do not hide business logic in natural language; express it in schemas, script interfaces, and artifact contracts whenever possible.

## 10. Generation Specification for the Target Skill's `SKILL.md`

`SKILL.md` is intended for ordinary agents and explains the skill's purpose and ordinary execution method.

Recommended structure:

```markdown
---
name: target-skill
description: Use this skill when ...
---

# Target Skill

## When To Use

Use this skill when ...

## Inputs

- ...

## Ordinary Agent Mode

When FlowScript mode is not available, follow these steps:

1. Read the user request.
2. Resolve inputs using `input_schema.json`.
3. Run or inspect scripts in `scripts/`.
4. Use artifacts under `runs/{run_id}/artifacts/`.
5. If execution fails, inspect logs and continue manually.

## FlowScript Mode

If the runtime supports FlowScript, use `FLOWSCRIPT.md` as the executable profile.

## Outputs

- ...

## Safety And Constraints

- Do not skip validation.
- Do not produce final output before required artifacts exist.
- Do not call scripts outside this skill directory unless explicitly allowed.
```

`SKILL.md` should not repeat the complete DSL from `FLOWSCRIPT.md`, but it should explain the relationship between the two files.

## 11. Generation Specification for the Target Skill's `FLOWSCRIPT.md`

`FLOWSCRIPT.md` is intended for harness agents while remaining readable by ordinary agents.

Recommended structure:

````markdown
# FlowScript: target-skill

## Purpose

Describe the constrained execution profile for this skill.

## Rules For Ordinary Agents

Follow the `flow` block in order.
If a branch condition is present, use the declared condition rather than inventing a new path.
If execution fails, inspect declared logs and fallback context.

```flow
version: 1
mode: controlled

inputs:
  schema: input_schema.json

steps:
  - id: parse_request
    type: llm
    input_mode: skill_inputs
    prompt:
      zh: prompts/parse_request_cn.md
      en: prompts/parse_request_en.md
    tool:
      name: submit_skill_inputs
      description:
        zh: 提交 Schema 约束的技能输入
        en: Submit schema-constrained skill inputs
    input:
      request: ${user.request}
    output:
      params:
        path: runs/{run_id}/resolved_params.json
        schema: input_schema.json
    next: validate_params

  - id: validate_params
    type: validator
    command:
      executable: python
      args: [scripts/validate.py, --input, '${input.params}', --output, '${output.status}', --normalized-output, '${output.params}']
      accepted_exit_codes: [0, 1, 2]
      status_source: '${output.status}'
      timeout_seconds: 30
    input:
      params: ${parse_request.output.params}
    output:
      status: runs/{run_id}/artifacts/validation_status.json
      params: runs/{run_id}/valid_params.json
    branches:
      valid:
        when: ${validate_params.output.status.state} == "valid"
        next: execute_main
      needs_input:
        when: ${validate_params.output.status.state} == "needs_input"
        next: request_clarification
      invalid:
        when: ${validate_params.output.status.state} == "invalid"
        next: fallback_skill_mode

  - id: execute_main
    type: script
    command:
      executable: python
      args: [scripts/execute.py, --input, '${input.params}', --output, '${output.result}', --status-output, '${output.status}']
      accepted_exit_codes: [0, 1]
      status_source: '${output.status}'
      timeout_seconds: 60
    input:
      params: ${validate_params.output.params}
    output:
      result: runs/{run_id}/artifacts/result.json
      status: runs/{run_id}/artifacts/execution_status.json
    branches:
      success:
        when: ${execute_main.output.status.state} == "success"
        next: transform_artifact
      recoverable_error:
        when: ${execute_main.output.status.state} == "recoverable_error"
        next: fallback_skill_mode

  - id: transform_artifact
    type: llm
    prompt:
      zh: prompts/transform_artifact_cn.md
      en: prompts/transform_artifact_en.md
    tool:
      name: submit_transformed_artifact
      description:
        zh: 提交 Schema 约束的转换产物
        en: Submit the schema-constrained transformed artifact
    input:
      result: ${execute_main.output.result}
    output:
      transformed:
        path: runs/{run_id}/artifacts/transformed.json
        schema: schemas/transformed.schema.json
    next: finalize_artifact

  - id: finalize_artifact
    type: script
    command:
      executable: python
      args: [scripts/finalize.py, --input, '${input.transformed}', --output, '${output.artifact}']
      accepted_exit_codes: [0]
      timeout_seconds: 30
    input:
      transformed: ${transform_artifact.output.transformed}
    output:
      artifact: runs/{run_id}/artifacts/final_artifact.json

  - id: request_clarification
    type: llm
    output:
      question: runs/{run_id}/artifacts/clarification.md
    next: end

  - id: fallback_skill_mode
    type: fallback
    target: skill_mode
```
````

Notes:

- `mode: controlled` indicates support for controlled branching.
- Branches must be based on structured output rather than free-form natural-language judgment.
- `fallback_skill_mode` should generate fallback context.

## 12. Input Schema Specification

`input_schema.json` should use standard JSON Schema whenever possible.

Example:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TargetSkillInput",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "source": {
      "type": "string",
      "description": "Primary input source."
    },
    "options": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "required": ["source"]
}
```

Generation rules:

- Required fields must be few and clearly defined.
- Default values should be specified in the schema or in `validate.py`.
- Uncertain fields should be marked as `TODO`.
- Fields requiring user confirmation should cause `validate.py` to return `needs_input`.

## 13. Script Interface Specification

Scripts should use a consistent command-line interface whenever possible.

Recommended input:

```bash
python scripts/validate.py \
  --input runs/{run_id}/resolved_params.json \
  --output runs/{run_id}/artifacts/validation_status.json
```

Recommended output:

```json
{
  "state": "valid",
  "message": "",
  "missing_fields": [],
  "warnings": []
}
```

Status values:

| Status | Meaning |
|---|---|
| `valid` | Execution may continue |
| `needs_input` | The user must be asked for clarification |
| `invalid` | Execution cannot continue; fall back or terminate |
| `success` | Execution succeeded |
| `recoverable_error` | Recoverable error |
| `fatal_error` | Unrecoverable error |

Script constraints:

- Scripts must not read arbitrary paths directly.
- Scripts must not write the final result only to stdout.
- Scripts must write declared artifacts.
- Scripts must write structured status data.
- Errors should be written to `logs/error.log` or a declared error artifact.

## 14. Artifact Contract

The target skill should generate `artifacts_manifest.json`.

Example:

```json
{
  "primary_result": "artifacts/final_artifact.json",
  "editable_artifacts": [
    "artifacts/transformed.json"
  ],
  "status_files": [
    "artifacts/validation_status.json",
    "artifacts/execution_status.json"
  ],
  "logs": [
    "logs/validation.log",
    "logs/execute.log",
    "logs/error.log"
  ]
}
```

Artifact design principles:

- Every key node should have inspectable output.
- Output from LLM nodes should also be persisted to disk.
- For subsequent user edits, modify artifacts first instead of reinterpreting the original request.
- During fallback, readable artifacts should be included in the context.

## 15. Fallback Context Contract

When FlowScript execution fails, the following should be generated:

```json
{
  "original_user_input": "...",
  "failed_step": "execute_main",
  "completed_steps": [
    "parse_request",
    "validate_params"
  ],
  "available_artifacts": [
    "runs/{run_id}/valid_params.json"
  ],
  "error_logs": [
    "runs/{run_id}/logs/error.log"
  ],
  "suggested_recovery_actions": [
    "inspect params",
    "inspect logs",
    "rerun failed step",
    "continue in ordinary skill mode"
  ]
}
```

When ordinary skill mode takes over, it should read this file first.

## 16. Controlled Branch Generation Rules

When generating branches, the meta-skill should follow these rules:

- Branches must be based on structured status fields.
- Branch conditions must be declared explicitly in the DSL.
- "The model thinks a branch should be taken" must not be the sole decision criterion.
- Every branch must have a `next` target.
- Every failure branch must connect to a fallback, clarification, or explicit termination node.
- Complex branches may be decomposed into validator + condition + script instead of being written as long natural-language passages.

Recommended branch sources:

| Source | Recommended? |
|---|---|
| `validation_status.json.state` | Recommended |
| `execution_status.json.state` | Recommended |
| JSON Schema validator result | Recommended |
| Script exit code + status file | Recommended |
| LLM natural-language interpretation | Not recommended |
| Unstructured stdout | Not recommended |

## 17. Codex Execution Constraints

When using this meta-skill to generate a skill package, Codex should follow these constraints:

- Follow the existing project style; do not force the introduction of a complex framework.
- Keep file edits to the minimum necessary scope.
- Prefer the standard library when generating scripts.
- When external dependencies are required, document them explicitly in the README or script comments.
- Use `TODO` for uncertain business logic; do not invent details.
- Run feasible static checks after generation.
- If Python scripts are generated, run at least `python -m py_compile`.
- If a JSON Schema is generated, verify at least that the JSON can be parsed.

## 18. Post-Generation Checklist

After generation, Codex should verify the following:

- [ ] The directory structure is complete.
- [ ] `SKILL.md` is readable by ordinary agents.
- [ ] `FLOWSCRIPT.md` contains a `flow` block.
- [ ] `input_schema.json` is valid JSON.
- [ ] Every DSL step has a unique `id`.
- [ ] Every script step has a `command`.
- [ ] Every step's input references exist.
- [ ] Every step's output paths are explicit.
- [ ] Every branch has `when` and `next`.
- [ ] A fallback node exists.
- [ ] The artifact manifest is clearly designed.
- [ ] Script interfaces are consistent.
- [ ] No company-specific, business-specific, or private context is used.

## 19. Minimal Meta-Skill `SKILL.md` Draft

The following is a draft of `flowscript-skill-generator/SKILL.md`.

```markdown
---
name: flowscript-skill-generator
description: Use this skill when the user wants to create, convert, or improve a FlowScript-capable agent skill with SKILL.md, FLOWSCRIPT.md, input schemas, scripts, artifacts, and fallback contracts.
---

# FlowScript Skill Generator

## When To Use

Use this skill when the user asks to:

- create a FlowScript skill
- convert a normal skill into a FlowScript skill
- generate a skill/workflow dual-mode package
- design a harness-executable skill
- create SKILL.md plus FLOWSCRIPT.md plus scripts

## Goal

Generate a reusable skill package that ordinary agents can read as Markdown and compatible harness agents can execute as a controlled workflow.

## Required Process

1. Clarify the target skill's purpose, inputs, outputs, and boundaries.
2. Decide whether FlowScript is appropriate.
3. Design the target skill package structure.
4. Generate SKILL.md for ordinary agent mode.
5. Generate FLOWSCRIPT.md for harness mode.
6. Generate input_schema.json.
7. Generate scripts or script stubs.
8. Generate artifact and fallback contracts.
9. Add validation checklist and TODOs.

## Rules

- Keep the package generic and portable.
- Do not hide execution order in prose if it can be expressed in the flow block.
- Do not use undeclared scripts or artifacts.
- Use structured status files for branches.
- Use fallback_skill_mode for recoverable failures.
- Mark uncertain logic as TODO.

## Output

Return:

- generated files
- file tree
- validation summary
- remaining TODOs
```

## 20. Future Iterations

This meta-skill can be enhanced in stages:

| Stage | Capability |
|---|---|
| v0.1 | Generate basic `SKILL.md` + `FLOWSCRIPT.md` |
| v0.2 | Generate a schema and script stubs |
| v0.3 | Generate controlled branches |
| v0.4 | Generate replay tests |
| v0.5 | Generate a FlowScript draft from an existing trace |
| v0.6 | Generate a visual workflow sketch |
| v0.7 | Integrate with a harness static validator |

## 21. Summary

`flowscript-skill-generator` is a meta-skill for Codex that reliably generates FlowScript skill packages. It codifies FlowScript's core ideas into a reusable generation process:

```text
An ordinary-agent-readable SKILL.md
+ a harness-agent-executable FLOWSCRIPT.md
+ an explicit input schema
+ scripted deterministic steps
+ structured artifacts
+ controlled branches
+ fallback to ordinary skill mode
```

The value of this meta-skill lies in lowering the barrier to creating FlowScript skills while preserving the readability, testability, and execution constraints of each skill package.
