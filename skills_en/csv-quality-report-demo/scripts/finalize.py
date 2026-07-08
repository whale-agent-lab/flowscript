"""Combine a synthetic-data profile and English interpretation into a Markdown report and manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
from common import read_object, resolve_under_root, write_fallback, write_json


def escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the final employee and region data-quality report.")
    parser.add_argument("--params", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--interpretation", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--status-output", required=True)
    parser.add_argument("--manifest-output", required=True)
    parser.add_argument("--fallback-output", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    output = resolve_under_root(root, args.output)
    status_output = resolve_under_root(root, args.status_output)
    manifest_output = resolve_under_root(root, args.manifest_output)
    fallback_output = resolve_under_root(root, args.fallback_output)
    try:
        params = read_object(resolve_under_root(root, args.params, must_exist=True))
        profile = read_object(resolve_under_root(root, args.profile, must_exist=True))
        interpretation = read_object(resolve_under_root(root, args.interpretation, must_exist=True))
        resolve_under_root(root, args.data, must_exist=True)
        time_filter = profile["time_filter"]
        dimension_label = "Employee" if profile["cluster_dimension"] == "employee" else "Region"
        lines = [
            f"# {params['report_title']}", "",
            "> This report uses deterministic synthetic data for workflow demonstration only. It does not represent actual employee performance.", "",
            f"- Synthetic data: `{Path(args.data).as_posix()}`",
            f"- Generated records: {profile['generation']['generated_row_count']}",
            f"- Filter range: {time_filter['start_date']} to {time_filter['end_date']}",
            f"- Default date range used: {'Yes' if time_filter['defaulted'] else 'No'}",
            f"- Records after filtering: {profile['analyzed_row_count']}",
            f"- Grouping dimension: {dimension_label}",
            f"- Duplicate rows: {profile['duplicate_row_count']}", "",
            "## Overall Interpretation", "", interpretation["summary"], "",
            f"## Grouped by {dimension_label}", "",
            f"| {dimension_label} | Records | Valid Amounts | Total Amount | Average Amount | Completed | Completion Rate |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for cluster in profile["cluster_analysis"]:
            average = "-" if cluster["average_amount"] is None else f"{cluster['average_amount']:.2f}"
            lines.append(
                f"| {escape(cluster['group_value'])} | {cluster['row_count']} | {cluster['amount_present_count']} | "
                f"{cluster['total_amount']:.2f} | {average} | {cluster['completed_count']} | {cluster['completion_rate']:.2%} |"
            )
        lines.extend(["", "### Group Insights", ""])
        lines.extend(f"- {item}" for item in interpretation["cluster_insights"])
        lines.extend([
            "", "## Field Profiles", "",
            "| Field | Missing | Missing Rate | Unique Values | Numeric Values | Samples |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for column in profile["columns"]:
            samples = ", ".join(escape(value) for value in column["sample_values"])
            lines.append(f"| {escape(column['name'])} | {column['missing_count']} | {column['missing_rate']:.2%} | {column['unique_count']} | {column['numeric_value_count']} | {samples} |")
        lines.extend(["", "## Risks", ""])
        lines.extend(f"- {item}" for item in interpretation["risks"])
        lines.extend(["", "## Recommendations", ""])
        lines.extend(f"- {item}" for item in interpretation["recommendations"])
        lines.extend(["", "## Notes", "", "Quality and grouping statistics apply only to the selected inclusive date range. Do not use synthetic data for real evaluations, rewards, disciplinary actions, or personnel decisions.", ""])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines), encoding="utf-8")
        write_json(status_output, {"state": "success", "message": "The final English grouped data-quality report was generated successfully.", "warnings": []})
        write_json(manifest_output, {
            "primary_result": Path(args.output).as_posix(),
            "data_files": [Path(args.data).as_posix()],
            "editable_artifacts": [Path(args.interpretation).as_posix()],
            "status_files": [str(Path(args.status_output).parent / name).replace("\\", "/") for name in ("validation_status.json", "profile_status.json", "interpretation_status.json", "finalize_status.json")],
            "logs": [],
        })
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        message = f"Final report generation failed: {exc}"
        write_json(status_output, {"state": "recoverable_error", "message": message, "warnings": []})
        write_fallback(fallback_output, original_input={"params": args.params, "profile": args.profile, "interpretation": args.interpretation, "data": args.data}, failed_step="finalize_report", completed_steps=["parse_request", "validate_params", "generate_and_profile", "interpret_profile", "validate_interpretation"], available_artifacts=[args.params, args.data, args.profile, args.interpretation], message=message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
