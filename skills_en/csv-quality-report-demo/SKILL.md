---
name: csv-quality-report-demo
description: Generate synthetic CSV data with employee, region, amount, status, and date fields; filter it by an optional date range; and analyze data quality and business distributions by employee or region. Use when the user wants a multi-step FlowScript demonstration with controlled branches and fallback behavior, or a synthetic employee/region data-quality report.
---

# CSV Data Quality and Grouping Report Demo

Generate a deterministic, relatively large synthetic CSV from user-provided employees and regions. Filter it by date, profile the fields, calculate quality statistics, analyze groups by employee or region, and produce an English report. Do not read or modify external CSV files.

## Inputs

- `employees`: Required non-empty array of employee names.
- `regions`: Required non-empty array of region names.
- `group_by`: Required; either `employee` or `region`.
- `time_range`: Optional object containing `start_date` and `end_date`; defaults to the most recent 30 days through today.
- `record_count`: Optional number of synthetic historical records; defaults to `5000`.
- `seed`: Optional deterministic random seed; defaults to `42`.
- `report_title`: Optional; defaults to “Employee and Region Data Quality Report.”

Use `input_schema.json` as the source of truth for constraints. Ask the user when employees, regions, or the grouping dimension are missing; never invent them.

## Standard Agent Mode

1. Parse the user request into `resolved_params.json`.
2. Run `scripts/validate.py`. Ask for required information listed in `missing_fields`. The script normalizes an omitted date range to the most recent 30 days.
3. When the state is `valid`, run `scripts/execute.py` to create `runs/{run_id}/data/generated_data.csv` and a deterministic `profile.json` under `artifacts/`.
4. Use the field profiles and `cluster_analysis` to produce an English `interpretation.json` containing `summary`, `risks`, `recommendations`, and `cluster_insights`.
5. Run `scripts/validate_summary.py` to validate the interpretation structure.
6. Run `scripts/finalize.py` to create the final Markdown report.
7. If a step fails, read `fallback_context.json` and continue from the most recent valid artifact.

## FlowScript Mode

When the runtime supports FlowScript, use `FLOWSCRIPT.md` as the controlled execution configuration. Do not duplicate the DSL here.

## Generated Data

- `runs/{run_id}/data/generated_data.csv`: Synthetic analytical data with `order_id`, `employee_name`, `region`, `amount`, `status`, and `event_date`. It is neither user input nor the final report.

## Analysis Artifacts

- `profile.json`: Date filtering, field profiles, missing values, duplicate rows, and grouping statistics.
- `interpretation.json`: Script-validated English risks and grouping interpretation.
- `final_report.md`: Final English report.
- Structured status files, a manifest, and fallback context for each stage.

## Constraints

- Generate synthetic data only; never present synthetic results as real employee performance.
- Take employee and region names from the user; do not add undeclared names.
- Apply the normalized inclusive date range for filtering.
- Branch only on structured states.
- Do not generate the final report until the interpretation passes validation.
