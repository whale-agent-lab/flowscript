# 生成后校验清单

- [ ] 目录名与 frontmatter `name` 一致且命名合法。
- [ ] frontmatter 只含 `name` 和中文 `description`。
- [ ] `agents/openai.yaml` 界面字段为中文，`default_prompt` 提及 `$skill-name`。
- [ ] 标题、正文、Schema 描述、问题、消息、日志、示例和 TODO 为中文。
- [ ] 没有英文占位说明、无用途文件或 README 类重复文档。
- [ ] `FLOWSCRIPT.md` 有一个主 `flow` 块，声明版本、模式、schema 和步骤。
- [ ] 步骤 ID 唯一；脚本命令存在；引用指向前序已声明输出。
- [ ] script/validator 使用 executable + argv args，参数与脚本 CLI 一致，并声明 accepted_exit_codes、status_source 和 timeout_seconds。
- [ ] 每个 LLM 节点的 prompt、专用工具和输出 Schema 存在，输出声明包含 path 与 schema。
- [ ] 每个分支有 `when` 和 `next`，条件来自结构化字段。
- [ ] 失败状态通向澄清、fallback 或明确终止。
- [ ] Schema 是合法 JSON，声明 Draft 2020-12，字段说明为中文。
- [ ] Python 脚本通过 `python -m py_compile`，参数与 DSL 一致。
- [ ] 脚本写入结构化状态和声明 artifact；manifest 与实际路径一致。
- [ ] replay JSONL 逐行可解析。

最小命令：

```text
python -m json.tool input_schema.json
python -m py_compile scripts/validate.py scripts/execute.py
python scripts/validate.py --input examples/input.example.json --output runs/validation_status.json --normalized-output runs/valid_params.json
python scripts/execute.py --input runs/valid_params.json --output runs/result.json --status-output runs/execution_status.json
```

最终只汇报实际执行的校验，并列出真实业务 TODO、假设、依赖和待确认边界。
