# FlowScript Skill Generator 设计文档

## 1. 背景

FlowScript 是一种双模式技能格式：普通 agent 可以把它作为 Markdown skill 阅读和执行，harness agent 则可以解析其中的 DSL，并将其作为受控 workflow 执行。

为了让 Codex 稳定生成这种技能包，需要一个专门的“元 skill”。这个元 skill 不直接完成业务任务，而是指导 Codex 根据用户需求生成、校验和迭代一个完整的 FlowScript skill package。

本文档描述 `flowscript-skill-generator` 的设计。

## 2. 目标

`flowscript-skill-generator` 的目标是帮助 Codex 生成符合约定的 FlowScript 技能包，包括：

- 普通 agent 可读的 `SKILL.md`
- harness agent 可执行的 `FLOWSCRIPT.md`
- 输入参数 schema
- 脚本目录与脚本接口约定
- artifact/log 目录约定
- 受控分支 DSL
- fallback 到普通 skill mode 的上下文契约
- 可选的 replay test / validation 说明

它的重点不是生成一次性 prompt，而是生成可以被复用、测试、版本化和执行约束的技能资产。

## 3. 非目标

该元 skill 不负责：

- 替代完整 workflow engine
- 自动生成所有复杂分支
- 自动保证脚本逻辑正确
- 直接执行目标业务技能
- 将任意自然语言任务转换为生产级 workflow
- 处理和具体业务强绑定的合规、权限或安全策略

它只负责生成 FlowScript 技能包的结构、契约和初始实现草案。

## 4. 使用场景

用户向 Codex 提出：

```text
帮我创建一个 FlowScript 技能，用来完成某类可脚本化任务。
```

Codex 加载 `flowscript-skill-generator` 后，应完成：

1. 理解目标技能的输入、输出和执行边界。
2. 判断该技能是否适合 FlowScript。
3. 设计普通 skill mode 和 FlowScript mode 的关系。
4. 生成标准目录结构。
5. 编写 `SKILL.md`。
6. 编写 `FLOWSCRIPT.md`。
7. 编写或占位脚本。
8. 编写输入 schema。
9. 编写 artifact/log/fallback 契约。
10. 生成最小测试说明。

## 5. Skill 包结构

生成的目标技能建议采用以下结构：

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

不同技能可以裁剪：

- 如果没有 LLM transform 节点，可以省略 `transform.py`。
- 如果最终产物直接由主脚本生成，可以省略 `finalize.py`。
- 如果技能仅作为设计草案，可以先生成脚本占位文件和接口说明。

## 6. 元 Skill 自身结构

`flowscript-skill-generator` 自身也应作为一个普通 skill 存在：

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

其中：

- `SKILL.md`：告诉 Codex 何时使用该元 skill，以及生成流程。
- `references/flowscript_format.md`：描述 FlowScript DSL。
- `references/skill_package_contract.md`：描述目标技能包结构。
- `references/dsl_patterns.md`：描述线性 flow、受控分支、fallback 等模式。
- `references/validation_checklist.md`：生成后检查清单。
- `templates/`：提供可复用模板。

## 7. 触发条件

Codex 应在以下情况使用该 skill：

- 用户要求创建 FlowScript skill。
- 用户要求把普通 skill 转成 FlowScript。
- 用户要求为某个脚本化任务创建 skill/workflow 双模式技能。
- 用户要求生成 `SKILL.md` + `FLOWSCRIPT.md` + scripts 的技能包。
- 用户提到 harness agent、受控执行、DSL skill、workflow-capable skill。

不应在以下情况自动使用：

- 用户只是要求写普通脚本。
- 用户只是要求写一次性 prompt。
- 用户只是要求分析架构概念，不需要产出文件。
- 用户要求完整业务系统实现，而不是技能包设计。

## 8. 输入信息收集

元 skill 应先收集或推断以下信息。

### 8.1 基础信息

| 字段 | 说明 |
|---|---|
| `skill_name` | 技能名称，目录名和 frontmatter name 的基础 |
| `purpose` | 技能目的 |
| `trigger` | 何时使用该技能 |
| `ordinary_agent_behavior` | 普通 agent 如何执行 |
| `flowscript_behavior` | harness agent 如何执行 |
| `expected_outputs` | 预期产物 |

### 8.2 输入参数

| 字段 | 说明 |
|---|---|
| `required_inputs` | 必填参数 |
| `optional_inputs` | 可选参数 |
| `defaults` | 默认值 |
| `clarification_rules` | 何时需要向用户反问 |
| `validation_rules` | 程序化校验规则 |

### 8.3 执行步骤

| 字段 | 说明 |
|---|---|
| `deterministic_steps` | 应由脚本执行的步骤 |
| `llm_steps` | 应由模型执行的转换或解释步骤 |
| `artifact_handoffs` | 每步之间的文件交接 |
| `branch_points` | 受控分支点 |
| `fallback_points` | 回退点 |

如果用户没有提供足够信息，Codex 应先生成合理草案，并在文档中标记 `TODO`，而不是编造精确业务规则。

## 9. 生成流程

Codex 使用该元 skill 时，应按以下顺序执行。

```text
1. 阅读用户请求
2. 判断是否适合使用 FlowScript
3. 设计目标技能契约
4. 生成文件树
5. 编写 SKILL.md
6. 编写 FLOWSCRIPT.md
7. 编写 input_schema.json
8. 编写脚本或脚本桩
9. 编写参考资料和示例
10. 在可行时运行静态校验
11. 总结生成的技能包和待办事项
```

重要约束：

- 先设计契约，再写文件。
- 先定义 artifact，再定义脚本。
- 先定义 fallback，再定义复杂分支。
- 不要把业务逻辑藏在自然语言里，应尽量落到 schema、脚本接口和 artifact contract。

## 10. 目标技能的 `SKILL.md` 生成规范

`SKILL.md` 面向普通 agent，负责解释技能用途和普通执行方式。

推荐结构：

```markdown
---
name: target-skill
description: 当……时使用此技能。
---

# 目标技能

## 何时使用

当……时使用此技能。

## 输入

- ...

## 普通 Agent 模式

当 FlowScript 模式不可用时，请按以下步骤操作：

1. 阅读用户请求。
2. 使用 `input_schema.json` 解析输入。
3. 运行或检查 `scripts/` 中的脚本。
4. 使用 `runs/{run_id}/artifacts/` 下的 artifact。
5. 如果执行失败，检查日志并手动继续。

## FlowScript 模式

如果运行时支持 FlowScript，则使用 `FLOWSCRIPT.md` 作为可执行配置。

## 输出

- ...

## 安全与约束

- 不要跳过校验。
- 在所需 artifact 存在之前，不要生成最终输出。
- 除非明确允许，否则不要调用此技能目录之外的脚本。
```

`SKILL.md` 不应重复 `FLOWSCRIPT.md` 的完整 DSL，但应说明两者关系。

## 11. 目标技能的 `FLOWSCRIPT.md` 生成规范

`FLOWSCRIPT.md` 面向 harness agent，同时保留普通 agent 可读性。

推荐结构：

````markdown
# FlowScript：target-skill

## 用途

描述此技能的受约束执行配置。

## 普通 Agent 的执行规则

按顺序执行 `flow` 块。
如果存在分支条件，请使用已声明的条件，不要自行创建新路径。
如果执行失败，请检查已声明的日志和 fallback context。

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

注意：

- `mode: controlled` 表示支持受控分支。
- 分支必须来自结构化输出，不应来自自然语言自由判断。
- `fallback_skill_mode` 应生成 fallback context。

## 12. 输入 Schema 规范

`input_schema.json` 应尽量使用标准 JSON Schema。

示例：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TargetSkillInput",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "source": {
      "type": "string",
      "description": "主要输入来源。"
    },
    "options": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "required": ["source"]
}
```

生成规则：

- 必填字段必须少而清晰。
- 默认值应写入 schema 或 `validate.py`。
- 不确定字段应标记为 `TODO`。
- 需要用户确认的字段应由 `validate.py` 返回 `needs_input`。

## 13. 脚本接口规范

脚本应尽量统一命令行接口。

推荐输入：

```bash
python scripts/validate.py \
  --input runs/{run_id}/resolved_params.json \
  --output runs/{run_id}/artifacts/validation_status.json
```

推荐输出：

```json
{
  "state": "valid",
  "message": "",
  "missing_fields": [],
  "warnings": []
}
```

状态枚举：

| 状态 | 含义 |
|---|---|
| `valid` | 可继续执行 |
| `needs_input` | 需要向用户反问 |
| `invalid` | 无法执行，应 fallback 或终止 |
| `success` | 执行成功 |
| `recoverable_error` | 可恢复错误 |
| `fatal_error` | 不可恢复错误 |

脚本约束：

- 不应直接读取任意路径。
- 不应把最终结果只写到 stdout。
- 必须写入声明的 artifact。
- 必须写入结构化 status。
- 错误应写入 `logs/error.log` 或声明的 error artifact。

## 14. Artifact 契约

目标技能应生成 `artifacts_manifest.json`。

示例：

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

artifact 设计原则：

- 每个关键节点都应有可检查输出。
- LLM 节点输出也应落盘。
- 用户二次修改应优先修改 artifact，而不是重新理解原始请求。
- fallback 时应把可读 artifact 列入上下文。

## 15. Fallback Context 契约

当 FlowScript 执行失败时，应生成：

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

普通 skill mode 接管时，应优先读取该文件。

## 16. 受控分支生成规则

元 skill 生成分支时应遵守：

- 分支必须基于结构化状态字段。
- 分支条件必须显式写在 DSL 中。
- 不允许使用“模型觉得应该进入某分支”作为唯一判断。
- 每个分支都必须有 `next`。
- 每个失败分支都必须连接到 fallback、clarification 或明确终止节点。
- 复杂分支可以拆成 validator + condition + script，而不是写成大段自然语言。

推荐分支来源：

| 来源 | 是否推荐 |
|---|---|
| `validation_status.json.state` | 推荐 |
| `execution_status.json.state` | 推荐 |
| JSON Schema validator 结果 | 推荐 |
| 脚本 exit code + status file | 推荐 |
| LLM 自然语言解释 | 不推荐 |
| 未结构化 stdout | 不推荐 |

## 17. Codex 执行约束

Codex 使用该元 skill 生成技能包时，应遵守：

- 使用现有项目风格，不强行引入复杂框架。
- 文件编辑应保持最小必要范围。
- 生成脚本时优先使用标准库。
- 需要外部依赖时必须明确写入 README 或脚本注释。
- 对不确定业务逻辑使用 `TODO`，不要编造。
- 生成后应运行可行的静态检查。
- 如果生成 Python 脚本，至少运行 `python -m py_compile`。
- 如果生成 JSON Schema，至少检查 JSON 可解析。

## 18. 生成后检查清单

Codex 完成生成后，应检查：

- [ ] 目录结构完整。
- [ ] `SKILL.md` 能被普通 agent 阅读。
- [ ] `FLOWSCRIPT.md` 包含 `flow` block。
- [ ] `input_schema.json` 是合法 JSON。
- [ ] 每个 DSL step 都有唯一 `id`。
- [ ] 每个 script step 都有 `command`。
- [ ] 每个 step 的输入引用存在。
- [ ] 每个 step 的输出路径明确。
- [ ] 每个 branch 都有 `when` 和 `next`。
- [ ] fallback 节点存在。
- [ ] artifact manifest 设计清晰。
- [ ] 脚本接口一致。
- [ ] 未使用公司、业务或私有上下文。

## 19. 最小元 Skill `SKILL.md` 草案

下面是 `flowscript-skill-generator/SKILL.md` 的草案。

```markdown
---
name: flowscript-skill-generator
description: 当用户希望创建、转换或改进支持 FlowScript 的 Agent 技能，并为其提供 SKILL.md、FLOWSCRIPT.md、输入 Schema、脚本、artifact 和 fallback 契约时，使用此技能。
---

# FlowScript 技能生成器

## 何时使用

当用户提出以下要求时，使用此技能：

- 创建 FlowScript 技能
- 将普通技能转换为 FlowScript 技能
- 生成技能/工作流双模式包
- 设计可由 harness 执行的技能
- 创建 SKILL.md、FLOWSCRIPT.md 及配套脚本

## 目标

生成可复用的技能包，使普通 Agent 能以 Markdown 形式阅读，并使兼容的 harness Agent 能将其作为受控工作流执行。

## 必需流程

1. 明确目标技能的用途、输入、输出和边界。
2. 判断是否适合使用 FlowScript。
3. 设计目标技能包的结构。
4. 为普通 Agent 模式生成 SKILL.md。
5. 为 harness 模式生成 FLOWSCRIPT.md。
6. 生成 input_schema.json。
7. 生成脚本或脚本桩。
8. 生成 artifact 和 fallback 契约。
9. 添加校验清单和待办事项。

## 规则

- 保持技能包的通用性和可移植性。
- 如果执行顺序可以在 `flow` 块中表达，就不要将其隐藏在描述性文字中。
- 不要使用未声明的脚本或 artifact。
- 使用结构化状态文件进行分支判断。
- 对可恢复的失败使用 `fallback_skill_mode`。
- 将不确定的逻辑标记为 `TODO`。

## 输出

返回：

- 生成的文件
- 文件树
- 校验摘要
- 剩余的待办事项
```

## 20. 后续迭代

该元 skill 可以分阶段增强：

| 阶段 | 能力 |
|---|---|
| v0.1 | 生成基础 `SKILL.md` + `FLOWSCRIPT.md` |
| v0.2 | 生成 schema 和脚本 stub |
| v0.3 | 生成受控分支 |
| v0.4 | 生成 replay test |
| v0.5 | 从已有 trace 生成 FlowScript draft |
| v0.6 | 生成可视化 workflow 草图 |
| v0.7 | 接入 harness 静态校验器 |

## 21. 总结

`flowscript-skill-generator` 是一个面向 Codex 的元 skill，用来稳定生成 FlowScript 技能包。它把 FlowScript 的核心思想固化为可复用生成流程：

```text
普通 agent 可读的 SKILL.md
+ harness agent 可执行的 FLOWSCRIPT.md
+ 明确输入 schema
+ 脚本化确定性步骤
+ 结构化 artifact
+ 受控分支
+ fallback 到普通 skill mode
```

该元 skill 的价值在于降低 FlowScript 技能创建门槛，同时保持技能包的可读性、可测试性和可执行约束。
