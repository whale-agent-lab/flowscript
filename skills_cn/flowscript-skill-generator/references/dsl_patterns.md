# DSL 模式

采用足以表达约束的最简单模式。模型只生成 Schema 约束内容；Runtime 负责顺序、命令、路径、落盘和分支。

## 输入解析模式

使用 `input_mode: skill_inputs`、prompt、专用工具和 `input_schema.json`。输出声明必须同时包含 `path` 和 `schema`。

## LLM 内容节点

解释、摘要和重写节点必须：

- 读取已声明 input artifact。
- 使用节点专用 prompt。
- 使用专用提交工具，而不是通用 `write_file`。
- 将输出 Schema 放在 `schemas/`。
- 由 Runtime 将工具参数写入声明路径。

## 确定性脚本节点

使用 `command.executable` 和 `command.args` 组成 argv。参数通过 `${input.*}` 与 `${output.*}` 明确绑定。声明 `accepted_exit_codes`、`status_source` 和超时。

## 受控分支

```flow
branches:
  valid:
    when: ${validate_params.output.status.state} == "valid"
    next: execute_main
  needs_input:
    when: ${validate_params.output.status.state} == "needs_input"
    next: request_clarification
```

分支只支持结构化字段的显式比较。禁止使用 `eval`、从 stdout 判断成功，或让模型决定分支。

## 验证型终止

尚未实现追问或 fallback 时，使用 `terminal` 节点明确停止，不伪造成功：

```flow
- id: execution_stopped
  type: terminal
  reason: execution_failed
```
