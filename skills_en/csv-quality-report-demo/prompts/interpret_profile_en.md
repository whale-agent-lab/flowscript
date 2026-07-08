# Profile Interpretation

Read the supplied synthetic-data profile, produce an English data-quality and grouping interpretation, and call `submit_interpretation`.

Rules:

- Use `summary` to describe the filter range, record volume, main quality observations, and grouping dimension.
- In `risks`, describe only observable missing-value, duplicate-row, or measurement risks from the profile.
- In `recommendations`, provide actionable data-governance steps corresponding to those risks.
- In `cluster_insights`, summarize differences in record counts, amounts, and completion rates across employees or regions.
- State clearly that the data is synthetic; do not interpret differences as real employee performance.
- Every array must contain at least one non-empty English string.
- Call the tool only; do not output explanations or Markdown.
