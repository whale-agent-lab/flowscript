# Minimal FlowScript Agent 设计（中文版）

## 1. 目标

实现一个验证型 FlowScript Runtime，能够读取技能目录中的 `FLOWSCRIPT.md`，按 DSL 顺序运行 workflow，并输出一条完整、可检查的 Skill 调用链路。

本版本只验证以下能力：

- 解析 `flow` DSL。
- 使用 JSON Schema 引导模型生成结构化输入。
- 将 DSL 的 script/validator 节点转换为 `exec` tool call。
- 将 LLM 节点的结构化结果转换为 `write_file` tool call。
- 使用 `read_file` 读取状态和 artifact。
- 根据结构化状态选择分支。
- 输出 tool call、tool result、节点状态和最终结果组成的完整 trace。

## 2. MVP 非目标

- 不实现 `fallback_skill_mode` 的普通 Skill 接管。
- 不实现暂停后恢复和多轮追问。
- 不实现并行、循环、动态节点或分布式执行。
- 不执行模型自由选择的 shell 命令。
- 不支持远程文件系统和容器调度。
- 不追求兼容任意 FlowScript，仅支持本文定义的最小子集。

测试时必须提供完整必填输入，使当前 CSV Demo 不进入 `needs_input` 或 fallback 分支。如果意外进入这些分支，Runtime 记录终止事件并停止。

## 3. 总体架构

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
    |      +------+------+                 run_state.json
    |      |             |                 trace.jsonl
    |  ModelAdapter   ToolRuntime           skill_agent_context.json
    |                    |
    |          exec/read_file/write_file
    |                    |
    +----------------> Skill Directory
```

### 3.1 FlowLoader

负责从 `FLOWSCRIPT.md` 提取 `flow` fenced block，并使用安全 YAML 解析器转换为内存对象。

### 3.2 PlanValidator

在运行前完成静态检查：

- `version` 和 `mode` 是否受支持。
- step `id` 是否唯一。
- `next` 和 branch 目标是否存在。
- 节点类型是否受支持。
- `${step.output.name}` 引用是否存在。
- 输出路径是否位于当前 Skill 或 `runs/{run_id}/` 中。
- script/validator 是否声明可执行文件、参数、状态文件和允许的退出码。
- LLM 节点是否声明输入、提示和输出 Schema。

### 3.3 WorkflowEngine

WorkflowEngine 是唯一能决定执行顺序的组件。模型和 FakeAgent 都不能自行选择下一节点。

核心循环：

```python
current = plan.entry_step
while current != "end":
    step = plan.steps[current]
    result = executor_for(step.type).run(step, state)
    state.record(result)
    current = branch_engine.select(step, result) or step.next
```

### 3.4 FakeAgent

FakeAgent 是模型调用与底层工具之间的适配层，同时负责产生对 Skill Agent 可见的完整调用链路。

它不决定 workflow，只负责：

- 调用模型生成 Schema 约束的数据。
- 将 Runtime 已决定的动作表示为 tool call。
- 调用 ToolRuntime。
- 记录 tool result、artifact 和节点状态。
- 把原始事件渲染为 Skill Agent 容易理解的 transcript。

### 3.5 ToolRuntime

MVP 提供以下工具：

```text
exec(argv, cwd, timeout_seconds)
read_file(path, encoding, max_bytes)
write_file(path, content, encoding, atomic)
read_json(path)
write_json(path, value, atomic)
stat_file(path)
```

约束：

- `exec` 只接受 argv 数组，不接受 shell 字符串。
- cwd 固定为 Skill 根目录。
- 路径必须位于 Skill 根目录内。
- 模型不能直接指定命令和写入路径。
- 写入路径必须是 DSL 当前节点声明的 output。
- 所有调用必须设置超时和最大输出长度。

### 3.6 ModelAdapter

MVP 使用本地 OpenAI-compatible Chat Completions 接口：

```text
model: qwen3.5-4b-mtp
endpoint: http://127.0.0.1:1234/v1/chat/completions
```

ModelAdapter 负责构造 `messages`、`tools` 和 `tool_choice`，并把响应统一转换为内部 `model_tool_call`。默认本地接口不需要鉴权；实现保留可选的 `MINIMIZE_AGENT_API_KEY`，设置后才发送 `Authorization: Bearer ...`。

Runtime 启动时执行一次轻量兼容性检查，确认接口能返回 OpenAI 风格的 `assistant.tool_calls`。验证型 MVP 不为不兼容格式做复杂适配；若服务端不能返回 tool calls，应直接给出明确错误。
### 3.7 双语与系统语言

Runtime 默认读取操作系统 locale，中文环境选择 `zh`，其他环境选择 `en`。优先级为：

1. CLI `--language zh|en`。
2. 环境变量 `MINIMAL_FLOWSCRIPT_AGENT_LANG`。
3. 系统 locale 与 `LANG`/`LC_*`。
4. 无法识别时回退英文。

DSL 中的模型 prompt 和工具说明使用双语映射：

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

Runtime 只读取当前语言版本；代码内追加给模型的强制工具调用指令和最终 Skill Agent 消息也从双语消息表选择。

## 4. 节点执行方式

### 4.1 `llm` 输入解析节点

对于 `parse_request`：

1. 读取 `inputs.schema` 指向的 JSON Schema。
2. 动态生成模型工具 `submit_skill_inputs`。
3. 将用户自然语言请求交给模型。
4. 模型调用 `submit_skill_inputs` 并返回参数。
5. FakeAgent 校验参数结构。
6. FakeAgent 发出 `write_json` tool call，将参数写入节点声明的 output。

示例事件：

```json
{"event":"model_tool_call","step_id":"parse_request","tool":"submit_skill_inputs","arguments":{"employees":["张伟"],"regions":["华东"],"group_by":"employee"}}
{"event":"tool_call","step_id":"parse_request","tool":"write_json","arguments":{"path":"runs/demo/resolved_params.json"}}
{"event":"tool_result","step_id":"parse_request","tool":"write_json","status":"success"}
```

### 4.2 `script` 和 `validator` 节点

1. 解析输入和输出引用。
2. 根据 DSL 的 executable 和 args 生成 argv。
3. FakeAgent 发出 `exec` tool call。
4. ToolRuntime 执行脚本并返回 exit code、stdout、stderr。
5. FakeAgent 使用 `read_json` 读取状态文件。
6. WorkflowEngine 根据状态文件选择分支。

模型不参与命令生成和分支判断。

### 4.3 `llm` 内容生成节点

对于 `interpret_profile`：

1. FakeAgent 根据节点 input 发出 `read_file` 或 `read_json`。
2. ModelAdapter 将输入、节点 prompt 和输出 Schema 发送给模型。
3. 模型调用节点专用工具，例如 `submit_interpretation`。
4. FakeAgent 校验结果并发出 `write_json`。
5. WorkflowEngine 进入下一节点。

不建议把通用 `write_file` 直接暴露给模型。模型只提交内容，写入位置由 Runtime 决定。

### 4.4 `end`、追问和 fallback

MVP 只正常支持 `end`。

- 到达 `end`：读取主产物并生成最终 transcript。
- 到达 `request_clarification`：记录 `unsupported_terminal`，输出缺失字段后停止。
- 到达 `fallback_skill_mode`：记录 `unsupported_terminal`，输出失败节点和已有 artifact 后停止。

这两种终止仍保留完整调用链路，但不继续处理。

## 5. 当前 DSL 需要的最小补充

现有 DSL 中的：

```yaml
command: python scripts/validate.py
```

不足以让通用 Runtime 推断 CLI 参数。建议改成：

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
    - --fallback-output
    - ${output.fallback}
  accepted_exit_codes: [0, 1, 2]
  status_source: ${output.status}
```

LLM 节点建议补充：

```yaml
- id: interpret_profile
  type: llm
  prompt: prompts/interpret_profile.md
  input:
    profile: ${generate_and_profile.output.profile}
  output:
    interpretation:
      path: runs/{run_id}/artifacts/interpretation.json
      schema: schemas/interpretation.schema.json
  next: validate_interpretation
```

为了保持 MVP 简单，不从 Markdown 描述中推断这些契约。

DSL 扩展允许直接修改以下内容：

- 当前 Demo 的 `skills_cn/csv-quality-report-demo/FLOWSCRIPT.md`。
- 中英文 `flowscript-skill-generator` 的格式说明、DSL patterns、校验清单和 `FLOWSCRIPT.md.template`。
- 中英文 FlowScript Skill Generator 设计文档中对应的示例和生成规则。

这样当前 Demo 与后续生成的新 Skill 使用同一套可执行 DSL，不在 Runtime 中维护 Demo 专用映射。

## 6. 分支求值

MVP 只支持以下形式：

```text
${step.output.status.state} == "value"
${step.output.status.state} != "value"
```

实现受限表达式解析器，不使用 Python `eval`。

求值前由 Runtime 读取引用的 JSON 文件。若字段不存在，节点失败并停止运行。

## 7. Trace 与 Skill 调用链路

### 7.1 原始 Workflow 事件

写入：

```text
runs/{run_id}/runtime/trace.jsonl
```

该文件供 Runtime 调试和测试使用，不是主要交付给 Skill Agent 的上下文。

每条事件至少包含：

```json
{
  "seq": 12,
  "run_id": "demo",
  "step_id": "validate_params",
  "actor": "fake-agent",
  "event": "tool_call",
  "tool_call_id": "call_0012",
  "payload": {}
}
```

事件类型：

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

### 7.2 Skill Agent 调用链路上下文

写入主要交付文件：

```text
runs/{run_id}/runtime/skill_agent_context.json
```

它不是 Workflow 节点日志，而是一段模拟“Skill Agent 正常执行技能”的完整上下文。对外呈现时，`assistant` 就代表 Skill Agent；Runtime/FakeAgent 生成的文件和命令操作表现为该 Agent 发出的 tool calls。

使用 OpenAI Chat Completions 风格消息结构：

```json
[
  {"role":"user","content":"按员工分析张伟和李娜在华东、华南的数据"},
  {"role":"assistant","tool_calls":[{"id":"call_1","name":"write_json","arguments":{}}]},
  {"role":"tool","tool_call_id":"call_1","content":"{\"status\":\"success\"}"},
  {"role":"assistant","tool_calls":[{"id":"call_2","name":"exec","arguments":{}}]},
  {"role":"tool","tool_call_id":"call_2","content":"{\"exit_code\":0}"}
]
```

上下文按实际执行顺序包含：

1. 用户请求。
2. 模型通过 Schema 工具提交结构化输入。
3. Skill Agent 的 `write_json` 调用及结果。
4. Skill Agent 的 `exec` 调用及结果。
5. Skill Agent 的 `read_file`/`read_json` 调用及结果。
6. LLM 节点的结构化 tool call 和对应写文件调用。
7. 最终报告读取结果。
8. Skill Agent 的最终回答。

`node_started`、内部引用解析和 branch evaluator 等 Workflow 实现细节只进入 `trace.jsonl`，不混入 Skill Agent 上下文，避免上层 Agent 把 Runtime 内部事件误认为自己可调用的工具。

完整链路是“调用完整”，不等于把大文件全部嵌入上下文：

- JSON 状态和小型 artifact 可以记录完整内容。
- CSV 等大文件记录路径、字节数、行数、SHA-256 和内容预览。
- stdout/stderr 超长时截断，并记录原始日志路径。
### 7.3 最终结果

写入：

```text
runs/{run_id}/runtime/result.json
```

包含：

- 最终状态。
- 已执行节点。
- 分支选择。
- 主产物路径。
- trace 和 Skill Agent context 路径。
- 总 tool call 数。
- 模型调用次数。
- 总耗时。

## 8. 建议目录结构

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
## 9. CLI 草案

```bash
python -m minimize_agent run \
  --skill ../skills_cn/csv-quality-report-demo \
  --request "员工是张伟和李娜，区域是华东和华南，按员工分析" \
  --run-id demo-agent \
  --language auto
```

可选提供结构化输入，跳过自然语言解析模型调用：

```bash
python -m minimize_agent run \
  --skill ../skills_cn/csv-quality-report-demo \
  --input-json request.json \
  --run-id demo-agent \
  --language auto
```

## 10. 验收标准

使用 CSV Demo 完成一次成功运行，并满足：

1. DSL 静态校验通过。
2. 输入由 JSON Schema 工具产生或由结构化 JSON 提供。
3. 每个 script/validator 节点产生可见的 `exec` call 和 result。
4. 每个 LLM 节点产生模型请求、结构化结果和 `write_json` call。
5. 每次状态读取和分支选择都出现在 trace 中。
6. 最终报告生成成功。
7. `skill_agent_context.json` 能按顺序还原 Skill Agent 的完整工具调用过程。
8. 大型 CSV 不直接塞入 Skill Agent context。
9. 模型不能修改执行顺序、命令、路径和分支。

## 11. 已确认决策与剩余默认值

已确认：

1. 主要输出是 Skill Agent 的完整调用链路上下文，不实时注入另一个真实上层 Agent。
2. Workflow 原始 trace 仅用于调试。
3. 允许修改当前 DSL 和 FlowScript Skill Generator 的规则与模板。

采用以下默认值：

- 默认不发送 Authorization；可通过 `MINIMIZE_AGENT_API_KEY` 开启。
- 依赖只使用 `PyYAML`；HTTP 使用标准库，MVP 内置当前 Demo 所需的 JSON Schema 子集校验器。
- 小文件在 Skill Agent context 中记录全文；大型 CSV 记录 metadata、SHA-256 和 preview。
- `exec` 直接运行本机 Python，不使用 Docker。
- 主要交付文件名为 `skill_agent_context.json`。`n- 模型 prompt、工具描述和最终消息按系统语言在中文与英文之间切换。

按这些默认值即可进入 MVP 实现，不再需要额外产品信息。