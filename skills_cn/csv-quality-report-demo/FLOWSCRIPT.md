# FlowScript：员工与区域数据质量及聚类报告 Demo

## 目的

受控执行参数校验、模拟 CSV 生成、时间筛选、字段画像、员工或区域聚类、中文风险解读、解读复核和报告定稿。

## 普通 agent 阅读规则

按 `flow` 块顺序执行。员工、区域和聚类维度缺失时必须询问用户；时间范围缺省时由校验脚本取最近 30 天。LLM 只负责解析请求与解释画像，所有分支均由结构化状态决定。

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

    tool:
      name: submit_skill_inputs
      description:
        zh: 提交 CSV 模拟数据质量分析所需的结构化输入
        en: Submit structured inputs for synthetic CSV data-quality analysis
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
      timeout_seconds: 30
    input:
      params: ${parse_request.output.params}
    output:
      status: runs/{run_id}/artifacts/validation_status.json
      params: runs/{run_id}/valid_params.json
      fallback:
        path: runs/{run_id}/artifacts/fallback_context.json
        required: false
    branches:
      valid:
        when: ${validate_params.output.status.state} == "valid"
        next: generate_and_profile
      needs_input:
        when: ${validate_params.output.status.state} == "needs_input"
        next: request_clarification
      invalid:
        when: ${validate_params.output.status.state} == "invalid"
        next: fallback_skill_mode

  - id: generate_and_profile
    type: script
    command:
      executable: python
      args:
        - scripts/execute.py
        - --input
        - ${input.params}
        - --data-output
        - ${output.data}
        - --output
        - ${output.profile}
        - --status-output
        - ${output.status}
        - --fallback-output
        - ${output.fallback}
      accepted_exit_codes: [0, 1]
      status_source: ${output.status}
      timeout_seconds: 60
    input:
      params: ${validate_params.output.params}
    output:
      data: runs/{run_id}/data/generated_data.csv
      profile: runs/{run_id}/artifacts/profile.json
      status: runs/{run_id}/artifacts/profile_status.json
      fallback:
        path: runs/{run_id}/artifacts/fallback_context.json
        required: false
    branches:
      success:
        when: ${generate_and_profile.output.status.state} == "success"
        next: interpret_profile
      recoverable_error:
        when: ${generate_and_profile.output.status.state} == "recoverable_error"
        next: fallback_skill_mode
      fatal_error:
        when: ${generate_and_profile.output.status.state} == "fatal_error"
        next: end

  - id: interpret_profile
    type: llm
    prompt:
      zh: prompts/interpret_profile_cn.md

    tool:
      name: submit_interpretation
      description:
        zh: 提交基于画像的中文数据质量与聚类解读
        en: Submit a data-quality and grouping interpretation based on the profile
    input:
      profile: ${generate_and_profile.output.profile}
    output:
      interpretation:
        path: runs/{run_id}/artifacts/interpretation.json
        schema: schemas/interpretation.schema.json
    next: validate_interpretation

  - id: validate_interpretation
    type: validator
    command:
      executable: python
      args:
        - scripts/validate_summary.py
        - --input
        - ${input.interpretation}
        - --output
        - ${output.status}
        - --fallback-output
        - ${output.fallback}
      accepted_exit_codes: [0, 2]
      status_source: ${output.status}
      timeout_seconds: 30
    input:
      interpretation: ${interpret_profile.output.interpretation}
    output:
      status: runs/{run_id}/artifacts/interpretation_status.json
      fallback:
        path: runs/{run_id}/artifacts/fallback_context.json
        required: false
    branches:
      valid:
        when: ${validate_interpretation.output.status.state} == "valid"
        next: finalize_report
      invalid:
        when: ${validate_interpretation.output.status.state} == "invalid"
        next: fallback_skill_mode

  - id: finalize_report
    type: script
    command:
      executable: python
      args:
        - scripts/finalize.py
        - --params
        - ${input.params}
        - --profile
        - ${input.profile}
        - --interpretation
        - ${input.interpretation}
        - --data
        - ${input.data}
        - --output
        - ${output.report}
        - --status-output
        - ${output.status}
        - --manifest-output
        - ${output.manifest}
        - --fallback-output
        - ${output.fallback}
      accepted_exit_codes: [0, 1]
      status_source: ${output.status}
      timeout_seconds: 30
    input:
      profile: ${generate_and_profile.output.profile}
      interpretation: ${interpret_profile.output.interpretation}
      params: ${validate_params.output.params}
      data: ${generate_and_profile.output.data}
    output:
      report: runs/{run_id}/artifacts/final_report.md
      status: runs/{run_id}/artifacts/finalize_status.json
      manifest: runs/{run_id}/artifacts/artifacts_manifest.json
      fallback:
        path: runs/{run_id}/artifacts/fallback_context.json
        required: false
    branches:
      success:
        when: ${finalize_report.output.status.state} == "success"
        next: end
      recoverable_error:
        when: ${finalize_report.output.status.state} == "recoverable_error"
        next: fallback_skill_mode
      fatal_error:
        when: ${finalize_report.output.status.state} == "fatal_error"
        next: end

  - id: request_clarification
    type: terminal
    reason: needs_input_not_supported_by_mvp

  - id: fallback_skill_mode
    type: terminal
    reason: fallback_not_supported_by_mvp
```
