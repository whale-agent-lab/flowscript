---
name: flowscript-skill-generator
description: Create, convert, or improve FlowScript-capable dual-mode skill packages with SKILL.md, FLOWSCRIPT.md, input schemas, scripts or script stubs, artifact and log contracts, controlled branches, fallback context, and replay tests. Use when the user mentions FlowScript, harness agents, controlled workflows, DSL skills, workflow-capable skills, or converting a regular skill into a harness-executable package. Do not use for a standalone script, a one-off prompt, conceptual analysis without file output, or a complete business system.
---

# FlowScript Skill Generator

Generate reusable, testable, versionable FlowScript skill packages that ordinary agents can follow as Markdown and compatible harness agents can execute as controlled workflows.

## Required Process

1. Collect or reasonably infer the skill name, purpose, triggers, inputs, outputs, boundaries, deterministic steps, LLM steps, artifact handoffs, branches, and fallback points.
2. Decide whether FlowScript is appropriate. Prefer it when the task can be decomposed into explicit steps, can exchange structured artifacts, and benefits from controlled execution.
3. If missing details do not change the overall structure, create a reasonable draft and mark unknown business rules with `TODO`. Ask the user only when missing information materially changes safety boundaries or package structure.
4. Design the contract before creating files. Define artifacts before script interfaces, and define fallback behavior before complex branches.
5. Read the references as needed:
   - Read [references/flowscript_format.md](references/flowscript_format.md) when designing the DSL.
   - Read [references/skill_package_contract.md](references/skill_package_contract.md) when designing directories, scripts, and artifacts.
   - Read [references/dsl_patterns.md](references/dsl_patterns.md) when designing branches, clarification, or fallback.
   - Read and apply [references/validation_checklist.md](references/validation_checklist.md) after generation.
6. Copy and adapt the required files from `templates/`. Remove meaningless placeholders and keep `TODO` only for genuinely unknown details.
7. Run static validation and minimal tests, then report generated files, validation results, and remaining TODOs.

## Minimum Target Package

```text
target-skill/
├── SKILL.md
├── FLOWSCRIPT.md
├── input_schema.json
├── prompts/
│   ├── parse_request_cn.md
│   └── parse_request_en.md
├── agents/openai.yaml
├── scripts/validate.py
├── scripts/execute.py
├── references/flow_contract.md
├── references/artifact_contract.md
├── tests/replay_cases.jsonl
└── examples/
    ├── input.example.json
    └── artifacts.example.json
```

Add `transform.py`, `finalize.py`, or other scripts only when the workflow needs them. Do not create files merely to fill out the tree.

## Generation Constraints

- Do not duplicate the full DSL in `SKILL.md`; explain ordinary mode, inputs, outputs, and the relationship to `FLOWSCRIPT.md`.
- Express ordering, references, output paths, and branch conditions explicitly in the `flow` block.
- Declare every script command as an executable mapping with argv `args`, `accepted_exit_codes`, `status_source`, and a timeout; do not use a prose-like command string.
- Give every LLM node a prompt, dedicated tool, and output schema. The model submits content; the runtime writes it to the declared path.
- Branch only on structured status or validation results. Do not use free-form LLM text as the sole branch signal.
- Give every branch a `when` and `next`. Route every failure path to clarification, fallback, or explicit termination.
- Persist inspectable artifacts for every critical step, including LLM steps. Never leave the final result only on stdout.
- Use consistent command-line interfaces and constrain input and output paths to the skill directory or a declared run directory.
- Generate fallback context for recoverable failures so ordinary skill mode can continue from existing artifacts and logs.
- Prefer the standard library and the project's existing style. Document external dependencies in the relevant script comments or contract; do not add a README.
- Do not invent business rules, permission models, compliance requirements, or production guarantees.

## Completion Criteria

Finish only after directory references are consistent, JSON parses, Python compiles, the DSL passes basic structural checks, and examples match the contracts. Report the generated path, primary files, checks actually run, remaining business TODOs, and boundaries that still need confirmation.