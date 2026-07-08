"""Generate synthetic CSV data, filter it by date, and output profiles and grouping statistics."""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import fmean
from common import read_object, resolve_under_root, write_fallback, write_json


HEADERS = ["order_id", "employee_name", "region", "amount", "status", "event_date"]


def as_number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_column_profile(name: str, rows: list[dict[str, str]]) -> dict:
    values = [row.get(name, "") for row in rows]
    present = [value for value in values if value != ""]
    numbers = [number for value in present if (number := as_number(value)) is not None]
    result = {
        "name": name,
        "missing_count": len(values) - len(present),
        "missing_rate": round((len(values) - len(present)) / len(values), 4) if values else 0.0,
        "unique_count": len(set(present)),
        "sample_values": list(dict.fromkeys(present))[:5],
        "numeric_value_count": len(numbers),
    }
    if numbers:
        result["numeric_stats"] = {"min": min(numbers), "max": max(numbers), "mean": round(fmean(numbers), 4)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and analyze a synthetic employee and region CSV.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--data-output", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--status-output", required=True)
    parser.add_argument("--fallback-output", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    data_output = resolve_under_root(root, args.data_output)
    output = resolve_under_root(root, args.output)
    status_output = resolve_under_root(root, args.status_output)
    fallback_output = resolve_under_root(root, args.fallback_output)
    params: dict = {}
    try:
        params = read_object(resolve_under_root(root, args.input, must_exist=True))
        employees = params["employees"]
        regions = params["regions"]
        group_by = params["group_by"]
        record_count = int(params["record_count"])
        rng = random.Random(int(params["seed"]))
        start_date = date.fromisoformat(params["time_range"]["start_date"])
        end_date = date.fromisoformat(params["time_range"]["end_date"])
        selected_span = (end_date - start_date).days
        history_start = min(start_date, end_date - timedelta(days=179))
        history_span = (end_date - history_start).days

        rows: list[dict[str, str]] = []
        statuses = ["Completed", "In Progress", "Pending", "Cancelled"]
        weights = [65, 15, 12, 8]
        for index in range(record_count):
            if index > 0 and index % 211 == 0:
                rows.append(dict(rows[-1]))
                continue
            employee = employees[rng.randrange(len(employees))]
            region = regions[rng.randrange(len(regions))]
            if index % 5:
                event_date = start_date + timedelta(days=rng.randint(0, selected_span))
            else:
                event_date = history_start + timedelta(days=rng.randint(0, history_span))
            amount = "" if index % 53 == 0 else f"{rng.uniform(45, 995):.2f}"
            status = "" if index % 101 == 0 else rng.choices(statuses, weights=weights, k=1)[0]
            rows.append({
                "order_id": f"SIM-{index + 1:06d}",
                "employee_name": employee,
                "region": region,
                "amount": amount,
                "status": status,
                "event_date": event_date.isoformat(),
            })

        data_output.parent.mkdir(parents=True, exist_ok=True)
        with data_output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(rows)

        selected_rows = [row for row in rows if params["time_range"]["start_date"] <= row["event_date"] <= params["time_range"]["end_date"]]
        if not selected_rows:
            raise ValueError("No analyzable data remains after date filtering.")
        row_tuples = [tuple(row[name] for name in HEADERS) for row in selected_rows]
        group_field = "employee_name" if group_by == "employee" else "region"
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in selected_rows:
            groups[row[group_field]].append(row)
        clusters = []
        for value, group_rows in sorted(groups.items()):
            amounts = [number for row in group_rows if (number := as_number(row["amount"])) is not None]
            completed = sum(row["status"] == "Completed" for row in group_rows)
            clusters.append({
                "group_value": value,
                "row_count": len(group_rows),
                "amount_present_count": len(amounts),
                "total_amount": round(sum(amounts), 2),
                "average_amount": round(fmean(amounts), 2) if amounts else None,
                "completed_count": completed,
                "completion_rate": round(completed / len(group_rows), 4),
            })

        profile = {
            "data_file": Path(args.data_output).as_posix(),
            "synthetic_data": True,
            "generation": {
                "seed": params["seed"],
                "generated_row_count": len(rows),
                "history_start_date": history_start.isoformat(),
                "history_end_date": end_date.isoformat(),
            },
            "time_filter": {**params["time_range"], "filtered_row_count": len(selected_rows)},
            "analyzed_row_count": len(selected_rows),
            "column_count": len(HEADERS),
            "duplicate_row_count": len(row_tuples) - len(set(row_tuples)),
            "columns": [build_column_profile(name, selected_rows) for name in HEADERS],
            "cluster_dimension": group_by,
            "cluster_field": group_field,
            "cluster_analysis": clusters,
        }
        write_json(output, profile)
        warnings = []
        if len(selected_rows) < len(rows):
            warnings.append(f"Date filtering retained {len(selected_rows)}/{len(rows)} records.")
        write_json(status_output, {"state": "success", "message": "Synthetic CSV generation, date filtering, profiling, and grouping statistics completed.", "warnings": warnings})
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        message = f"Synthetic data generation or profiling failed: {exc}"
        write_json(status_output, {"state": "recoverable_error", "message": message, "warnings": []})
        write_fallback(fallback_output, original_input=params, failed_step="generate_and_profile", completed_steps=["parse_request", "validate_params"], available_artifacts=[args.input], message=message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
