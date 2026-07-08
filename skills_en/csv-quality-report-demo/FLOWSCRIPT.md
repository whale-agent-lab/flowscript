# FlowScript: Employee and Region Data Quality and Grouping Report Demo

## Purpose

Run parameter validation, synthetic CSV generation, date filtering, field profiling, employee or region grouping, English risk interpretation, interpretation validation, and report finalization as a controlled workflow.

## Standard Agent Reading Rules

Execute the `flow` block in order. Ask the user when employees, regions, or the grouping dimension are missing. When the date range is omitted, let the validation script use the most recent 30 days. The LLM only parses requests and interprets profiles; structured states determine every branch.

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

      en: prompts/parse_request_en.md
    tool:
      name: submit_skill_inputs
      description:
        zh: Submit structured inputs for synthetic CSV data-quality analysis
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

      en: prompts/interpret_profile_en.md
    tool:
      name: submit_interpretation
      description:
        zh: Submit an English data-quality and grouping interpretation based on the profile
        en: Submit an English data-quality and grouping interpretation based on the profile
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
