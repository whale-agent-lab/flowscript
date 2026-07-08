---
name: flowscript-skill-generator
description: 为可脚本化任务创建、转换或改进 FlowScript 双模式技能包，生成中文的 SKILL.md、FLOWSCRIPT.md、输入 Schema、脚本或脚本占位、artifact/log 契约、受控分支、fallback 上下文和 replay 测试。用户提到 FlowScript、harness agent、受控工作流、DSL skill、workflow-capable skill，或要求把普通 skill 转成可由 harness 执行的技能时使用；仅需普通脚本、一次性提示词、概念分析或完整业务系统时不要使用。
---

# FlowScript 技能生成器

生成可复用、可测试、可版本化的 FlowScript 技能包。让普通 agent 按中文 Markdown 说明执行，让兼容的 harness agent 解析 `FLOWSCRIPT.md` 中的 DSL 受控执行。

## 中文输出要求

- 使用中文编写生成技能的说明、标题、字段描述、agent 提示、澄清问题、状态消息、日志消息、示例和 TODO。
- 保留必须稳定的机器标识，例如文件名、目录名、skill 名、JSON 键、DSL 关键字、状态枚举、命令行参数和代码标识符。
- 目标技能的 `SKILL.md` 使用英文小写连字符格式的 `name` 和中文 `description`。
- 目标技能的 `agents/openai.yaml` 使用中文 `display_name`、`short_description` 和 `default_prompt`；`default_prompt` 必须显式提及 `$skill-name`。
- 不翻译运行时字面量，例如 `controlled`、`valid`、`needs_input`、`invalid`、`success`、`recoverable_error` 和 `fatal_error`。

## 必需流程

1. 收集或合理推断技能名称、目的、触发条件、输入、输出、边界、确定性步骤、LLM 步骤、artifact 交接、分支和 fallback。
2. 判断 FlowScript 是否合适：任务应能拆成明确步骤，使用结构化 artifact 交接，并从受控执行中获益。
3. 信息不足但不影响整体结构时，生成合理草案并用 `TODO` 标明未知业务规则；只有缺失信息会实质改变安全边界或包结构时才提问。
4. 先设计契约，再创建文件；先定义 artifact，再定义脚本接口；先定义 fallback，再设计复杂分支。
5. 按需读取参考资料：
   - 设计 DSL 时读取 [references/flowscript_format.md](references/flowscript_format.md)。
   - 设计目录、脚本和 artifact 时读取 [references/skill_package_contract.md](references/skill_package_contract.md)。
   - 设计分支、澄清或回退时读取 [references/dsl_patterns.md](references/dsl_patterns.md)。
   - 完成后读取并执行 [references/validation_checklist.md](references/validation_checklist.md)。
6. 从 `templates/` 复制并改写所需模板；删除无意义占位符，仅保留真实未知项的 `TODO`。
7. 运行静态校验和最小测试，并用中文汇报文件、结果与剩余 TODO。

## 目标包最低要求

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

仅在流程确实需要时添加 `transform.py`、`finalize.py` 或其他脚本。不得为了填满目录而创建无用途文件。

## 生成约束

- 不在 `SKILL.md` 重复完整 DSL，只解释普通模式、输入输出及其与 `FLOWSCRIPT.md` 的关系。
- 将顺序、引用、输出路径和分支条件显式写入 `flow` 代码块。
- 将脚本命令写成 `executable`、argv `args`、`accepted_exit_codes`、`status_source` 和超时组成的可执行映射；不得只写自然语言式命令字符串。
- 每个 LLM 节点声明 prompt、专用工具和输出 Schema；模型只提交内容，Runtime 负责写入声明路径。
- 只基于结构化状态或校验结果分支，不以 LLM 自由文本作为唯一依据。
- 每个分支声明 `when` 和 `next`；每个失败路径连接到澄清、fallback 或明确终止。
- 关键步骤和 LLM 步骤都生成可检查的落盘 artifact；最终结果不得只写到 stdout。
- 统一脚本命令行接口，将输入输出限制到技能目录或声明的运行目录。
- 可恢复失败必须生成 fallback context，使普通模式能从已有 artifact 和日志继续。
- 优先使用标准库和项目现有风格。外部依赖写入相关脚本注释或契约，不额外创建 README。
- 不编造业务规则、权限模型、合规要求或生产级保证。

## 完成标准

确认目录与引用一致、JSON 可解析、Python 可编译、DSL 基本结构通过检查、示例与契约匹配。最终用中文列出生成路径、主要文件、实际校验、剩余业务 TODO 及待确认边界。
