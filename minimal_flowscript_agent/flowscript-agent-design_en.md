# Minimal FlowScript Agent Design (English)

## 1. Goal

Build a validation-oriented FlowScript Runtime that reads `FLOWSCRIPT.md`, executes its DSL as a workflow, and emits a complete, inspectable Skill Agent invocation context.

The MVP validates these capabilities:

- Parse a `flow` DSL block.
- Use JSON Schema to guide a model in producing structured inputs.
- Convert script and validator nodes into `exec` tool calls.
- Convert LLM node results into `write_json` tool calls.
- Use `read_file` and `read_json` for statuses and artifacts.
- Select branches from structured status values.
- Record tool calls, tool results, node state, and final output.
- Select Chinese or English prompts from the host system language.

## 2. MVP Non-goals

- No ordinary-skill takeover for `fallback_skill_mode`.
- No pause/resume or multi-turn clarification.
- No parallelism, loops, dynamic nodes, or distributed execution.
- No model-selected shell commands.
- No remote filesystem or container orchestration.
- No attempt to support every possible FlowScript construct.

Tests must provide all required inputs so the CSV demo does not enter `needs_input` or fallback. If either path is reached, the Runtime records an unsupported terminal and stops.

## 3. Architecture

```text
User Request
    |
    v
FlowScript CLI
    |
    +--> FlowLoader --------> ExecutionPlan
    |                            |
    +--> PlanValidator           v
    |                       WorkflowEngine
    |                            |
    |             +--------------+--------------+
    |             |                             |
    |         FakeAgent                    StateStore
    |             |                             |
    |      +------+------+                 trace.jsonl
    |      |             |                 result.json
    |  ModelAdapter   ToolRuntime           skill_agent_context.json
    |                    |
    |          exec/read_file/write_json
    |                    |
    +----------------> Skill Directory
```

### 3.1 FlowLoader

Extract exactly one fenced `flow` block from `FLOWSCRIPT.md` and parse it with a safe YAML loader.

### 3.2 PlanValidator

Validate before execution:

- Supported `version` and `mode`.
- Unique step IDs.
- Existing `next` and branch targets.
- Supported node types.
- References to declared prior outputs.
- Output paths confined to the skill directory and `runs/{run_id}/`.
- Executable, argv, accepted exit codes, status source, and timeout for script nodes.
- Input, localized prompt, dedicated tool, and output schema for LLM nodes.

### 3.3 WorkflowEngine

The WorkflowEngine is the only component allowed to choose execution order. Neither the model nor FakeAgent may select the next node.

```python
current = plan.entry_step
while current != "end":
    step = plan.steps[current]
    result = executor_for(step.type).run(step, state)
    state.record(result)
    current = branch_engine.select(step, result) or step.next
```

### 3.4 FakeAgent

FakeAgent adapts model output to local tools and produces the invocation context visible as Skill Agent activity.

It is responsible for:

- Asking the model for schema-constrained data.
- Representing Runtime-decided operations as tool calls.
- Calling ToolRuntime.
- Recording tool results, artifacts, and node state.
- Rendering normalized OpenAI-style Skill Agent messages.

It does not control the workflow.

### 3.5 ToolRuntime

The MVP exposes:

```text
exec(argv, cwd, timeout_seconds)
read_file(path, encoding, max_bytes)
write_file(path, content, encoding, atomic)
read_json(path)
write_json(path, value, atomic)
stat_file(path)
```

Constraints:

- `exec` accepts argv only, never a shell command string.
- cwd is fixed to the skill root.
- Paths must remain under the skill root.
- The model cannot choose commands or write destinations.
- Writes must target outputs declared by the current DSL node.
- Every execution has a timeout and output-size limit.

### 3.6 ModelAdapter

The MVP uses a local OpenAI-compatible Chat Completions endpoint:

```text
model: qwen3.5-4b-mtp
endpoint: http://127.0.0.1:1234/v1/chat/completions
```

ModelAdapter builds `messages`, `tools`, and `tool_choice`, then normalizes the response into an internal `model_tool_call`. It supports both standard `assistant.tool_calls` and the Qwen XML tool-call representation returned through `reasoning_content`.

Authentication is disabled by default. When `MINIMIZE_AGENT_API_KEY` is set, the adapter sends `Authorization: Bearer ...`.

### 3.7 Bilingual Prompts and System Language

The Runtime selects `zh` for a Chinese system locale and `en` otherwise. Resolution order:

1. CLI `--language zh|en`.
2. `MINIMAL_FLOWSCRIPT_AGENT_LANG`.
3. Operating-system locale and `LANG`/`LC_*`.
4. English fallback.

Prompt paths and tool descriptions are declared as localized DSL mappings:

```flow
prompt:
  zh: prompts/parse_request_cn.md
  en: prompts/parse_request_en.md
tool:
  name: submit_skill_inputs
  description:
    zh: 提交结构化输入
    en: Submit structured inputs
```

Only the selected prompt is read. Runtime-injected tool instructions and final Skill Agent messages use the same language selection.

## 4. Node Execution

### 4.1 LLM Input Parsing

For `parse_request`:

1. Read the localized prompt and `inputs.schema`.
2. Create a schema-backed `submit_skill_inputs` tool.
3. Send the user request to the model.
4. Normalize the model tool call.
5. Validate the arguments.
6. Emit `write_json` for the declared output path.

Example events:

```json
{"event":"model_tool_call","step_id":"parse_request","tool":"submit_skill_inputs","arguments":{"employees":["Alice"],"regions":["East"],"group_by":"employee"}}
{"event":"tool_call","step_id":"parse_request","tool":"write_json","arguments":{"path":"runs/demo/resolved_params.json"}}
{"event":"tool_result","step_id":"parse_request","tool":"write_json","status":"success"}
```

### 4.2 Script and Validator Nodes

1. Resolve input/output references.
2. Build argv from `command.executable` and `command.args`.
3. Emit and execute an `exec` tool call.
4. Capture exit code, stdout, and stderr.
5. Read the declared JSON status file.
6. Let WorkflowEngine select the branch.

The model never constructs commands and never decides branches.

### 4.3 LLM Content Nodes

For `interpret_profile`:

1. Read the declared input artifact.
2. Read the localized prompt and output schema.
3. Ask the model to call a dedicated submission tool.
4. Validate the normalized tool arguments.
5. Emit `write_json` to the declared path.

Do not expose generic `write_file` to the model. The model submits content; the Runtime controls persistence.

### 4.4 End and Unsupported Terminals

The MVP supports normal `end` completion only.

- `end`: read the primary artifact and append the final Skill Agent answer.
- Clarification terminal: record `unsupported_terminal` and stop.
- Fallback terminal: record `unsupported_terminal` and stop.

The failed run still retains its complete invocation context.

## 5. Minimum Executable DSL Additions

Opaque commands such as this are insufficient:

```yaml
command: python scripts/validate.py
```

Use an executable mapping:

```yaml
command:
  executable: python
  args:
    - scripts/validate.py
    - --input
    - ${input.params}
    - --output
    - ${output.status}
    - --normalized-output
    - ${output.params}
  accepted_exit_codes: [0, 1, 2]
  status_source: ${output.status}
  timeout_seconds: 30
```

LLM nodes declare localized prompts, a dedicated tool, and an output schema:

```yaml
- id: interpret_profile
  type: llm
  prompt:
    zh: prompts/interpret_profile_cn.md
    en: prompts/interpret_profile_en.md
  tool:
    name: submit_interpretation
    description:
      zh: 提交画像解读
      en: Submit the profile interpretation
  input:
    profile: ${generate_and_profile.output.profile}
  output:
    interpretation:
      path: runs/{run_id}/artifacts/interpretation.json
      schema: schemas/interpretation.schema.json
  next: validate_interpretation
```

The Runtime does not infer these contracts from prose.

The same format must be reflected in:

- The CSV demo `FLOWSCRIPT.md`.
- Chinese and English FlowScript Skill Generator references and templates.
- Chinese and English generator design documents.

## 6. Branch Evaluation

The MVP supports explicit equality and inequality comparisons only:

```text
${step.output.status.state} == "value"
${step.output.status.state} != "value"
```

Use a restricted parser, never Python `eval`. The Runtime reads the referenced JSON file before comparison and fails if the field is absent.

## 7. Trace and Skill Agent Invocation Context

### 7.1 Internal Workflow Trace

Write internal events to:

```text
runs/{run_id}/runtime/trace.jsonl
```

This file is for Runtime debugging and tests, not the primary Skill Agent output.

Each event includes sequence, timestamp, run ID, step ID, actor, event type, and payload. Event types include:

- `run_started`
- `node_started`
- `model_request`
- `model_tool_call`
- `tool_call`
- `tool_result`
- `artifact_written`
- `branch_selected`
- `node_completed`
- `node_failed`
- `unsupported_terminal`
- `run_completed`

### 7.2 Skill Agent Context

The primary output is:

```text
runs/{run_id}/runtime/skill_agent_context.json
```

It simulates a normal Skill Agent conversation. `assistant` represents the Skill Agent, and Runtime/FakeAgent operations appear as that agent's tool calls.

```json
[
  {"role":"user","content":"Analyze Alice and Bob in East and South by employee"},
  {"role":"assistant","tool_calls":[{"id":"call_1","type":"function","function":{"name":"write_json","arguments":"{}"}}]},
  {"role":"tool","tool_call_id":"call_1","content":"{\"status\":\"success\"}"},
  {"role":"assistant","tool_calls":[{"id":"call_2","type":"function","function":{"name":"exec","arguments":"{}"}}]},
  {"role":"tool","tool_call_id":"call_2","content":"{\"exit_code\":0}"}
]
```

The context contains, in order:

1. User request.
2. Schema-backed input submission.
3. `write_json` and result.
4. `exec` calls and results.
5. `read_file`/`read_json` calls and results.
6. LLM output submission and persistence.
7. Final artifact read.
8. Final localized Skill Agent answer.

Internal node-start and branch-evaluator details stay in `trace.jsonl`.

A complete call chain does not embed every large file:

- Small JSON and text artifacts may be included in full.
- Large CSV files use path, byte size, row count, SHA-256, and preview.
- Long stdout/stderr is truncated with a reference to the original log.

### 7.3 Result Summary

Write:

```text
runs/{run_id}/runtime/result.json
```

Include final status, completed steps, selected branches, primary artifact, context and trace paths, tool/model call counts, language, and elapsed time.

## 8. Directory Layout

```text
minimal_flowscript_agent/
├── flowscript-agent-design_cn.md
├── flowscript-agent-design_en.md
├── pyproject.toml
└── minimize_agent/
    ├── __main__.py
    ├── cli.py
    ├── engine.py
    ├── errors.py
    ├── fake_agent.py
    ├── flow_loader.py
    ├── i18n.py
    ├── model_adapter.py
    ├── schema_subset.py
    ├── tool_runtime.py
    └── trace_store.py
```

## 9. CLI

Natural-language input with automatic system-language detection:

```bash
python -m minimize_agent run \
  --skill ../skills_cn/csv-quality-report-demo \
  --request "Employees are Alice and Bob; regions are East and South; group by employee" \
  --run-id demo-agent \
  --language auto
```

Force a language when testing:

```bash
python -m minimize_agent run \
  --skill ../skills_cn/csv-quality-report-demo \
  --request "..." \
  --run-id demo-agent-en \
  --language en
```

Structured input can bypass the first model call:

```bash
python -m minimize_agent run \
  --skill ../skills_cn/csv-quality-report-demo \
  --input-json request.json \
  --run-id demo-agent-json
```

## 10. Acceptance Criteria

A successful CSV demo run must satisfy:

1. DSL static validation succeeds.
2. Inputs come from the schema tool or structured JSON.
3. Every script/validator node emits visible `exec` call and result messages.
4. Every LLM node emits a model tool call and `write_json` exchange.
5. Status reads and branch selections appear in the internal trace.
6. The final report is generated.
7. `skill_agent_context.json` reconstructs the full Skill Agent tool chain.
8. Large CSV content is summarized rather than embedded.
9. The model cannot change order, commands, paths, or branches.
10. `zh` and `en` select their corresponding prompts and final messages.

## 11. Confirmed Decisions and Defaults

Confirmed:

1. Model: `qwen3.5-4b-mtp`.
2. Endpoint: `http://127.0.0.1:1234/v1/chat/completions`.
3. The primary deliverable is the Skill Agent invocation context.
4. Workflow trace is internal debugging data.
5. The current DSL and FlowScript Skill Generator may be updated.

Defaults:

- Python 3.11+ single-process local execution.
- No Authorization header unless `MINIMIZE_AGENT_API_KEY` is set.
- `PyYAML` plus a built-in JSON Schema subset validator.
- System-locale language selection with CLI/environment override.
- Full content for small files; metadata, hash, and preview for large files.
- Local Python execution without Docker.
- Primary context filename: `skill_agent_context.json`.
