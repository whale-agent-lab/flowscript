# Input Parsing

Extract structured parameters from the user request and call `submit_skill_inputs`.

Rules:

- `employees`, `regions`, and `group_by` must come from the user request; do not invent them.
- Map requests to group by employee to `group_by: employee`, and requests to group by region to `group_by: region`.
- Include `time_range` only when the user explicitly provides both start and end dates.
- Omit `record_count`, `seed`, and `report_title` when the user does not specify them; the validation script supplies defaults.
- Encode array parameters as JSON arrays.
- Call the tool only; do not output explanations or Markdown.
