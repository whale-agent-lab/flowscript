# FlowScript 格式

`FLOWSCRIPT.md` 同时承载中文说明和 harness 可解析 DSL。每个文件只放一个主 `flow` 代码块。

## 字段要求

- `version` 当前为整数 `1`；`mode` 使用 `controlled`。
- `inputs.schema` 指向包内 JSON Schema。
- `steps` 是有序步骤列表；`id` 使用小写蛇形命名且唯一。
- 支持的最小节点类型为 `llm`、`validator`、`script` 和 `terminal`。
- `input` 只引用用户请求、当前节点 input/output 或前序步骤输出。
- `output` 使用路径字符串，或使用包含 `path`、`schema`、`required` 的对象。
- 无分支步骤声明唯一 `next`；每个分支声明 `when` 和 `next`。
- 使用 `${step_id.output.key}` 引用前序输出；使用 `${input.key}`、`${output.key}` 绑定当前命令参数。
- 控制状态只从结构化状态文件读取，不从 stdout 或 LLM 自由文本推断。

## LLM 节点

每个 LLM 节点必须显式声明 prompt、工具和输出 Schema：

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

模型只提交 Schema 约束的内容。Runtime 决定写入路径并生成 `write_json` tool call，不向模型暴露任意文件路径。

## Script 与 Validator 节点

`command` 必须是可执行映射，不使用不可解析的 shell 字符串：

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

- `args` 必须与脚本 CLI 完全一致。
- `accepted_exit_codes` 声明业务允许的退出码；非零退出码不自动等于 Runtime 失败。
- 有分支的脚本节点必须声明 `status_source`。
- `status_source` 指向 JSON 状态文件，分支读取其中的字段。
- `timeout_seconds` 必须为正整数。

## 状态与终止

机器状态值保持英文：`valid`、`needs_input`、`invalid`、`success`、`recoverable_error`、`fatal_error`。

验证型 Runtime 可以用 `terminal` 显式停止暂不支持的路径：

```flow
- id: request_clarification
  type: terminal
  reason: needs_input
```
