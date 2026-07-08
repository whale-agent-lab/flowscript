# 技能包契约

## 双模式与中文

`SKILL.md` 面向普通 agent，`FLOWSCRIPT.md` 面向 harness；两者共享 schema、脚本和 artifact。目录和 frontmatter `name` 使用小写连字符；frontmatter 只含 `name` 和中文 `description`。标题、正文、Schema 描述、示例、提示、状态消息和 UI 元数据使用中文；代码标识、路径、JSON 键和规定枚举可保留英文。

没有 LLM 转换时不创建 `transform.py`；主脚本直接产出最终结果时不创建 `finalize.py`；不创建 README 等重复文档。

## 输入与脚本

模型指令放在 `prompts/`；非输入类 LLM 输出 Schema 放在 `schemas/`。`input_schema.json` 使用 Draft 2020-12。必填字段少而明确，显式设置 `additionalProperties`，稳定默认值写入 schema，未知业务约束标记 `TODO`。需要确认的缺失值由验证器返回 `needs_input` 和 `missing_fields`。

```text
python scripts/validate.py --input <输入 JSON> --output <状态 JSON> --normalized-output <规范化参数 JSON>
python scripts/execute.py --input <参数 JSON> --output <结果 JSON> --status-output <状态 JSON>
```

脚本优先使用标准库和 UTF-8，创建输出父目录，写入结果与结构化状态，消息使用中文。不得只写 stdout、访问未声明路径或静默调用包外命令。

## Artifact 与 fallback

每个关键节点及 LLM 节点都落盘。manifest 至少声明主结果、可编辑 artifact、状态文件和日志。可恢复失败生成 `runs/{run_id}/artifacts/fallback_context.json`，包含 `original_user_input`、`failed_step`、`completed_steps`、`available_artifacts`、`error_logs` 和中文 `suggested_recovery_actions`。普通模式先读该文件，从最近有效 artifact 继续。

`examples/input.example.json` 应能通过验证或明确演示 `needs_input`。`tests/replay_cases.jsonl` 每行一个合法 JSON，按适用性覆盖成功、需要输入和无效输入。
