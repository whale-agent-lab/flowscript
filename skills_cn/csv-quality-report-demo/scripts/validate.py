"""校验模拟 CSV 报告参数并生成规范化输入。"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from common import read_object, resolve_under_root, write_fallback, write_json


def normalize_names(value: Any, field: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{field} 必须是包含 1 到 {maximum} 个名称的数组。")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} 中的名称必须是非空字符串。")
    names = [item.strip() for item in value]
    if len(set(names)) != len(names):
        raise ValueError(f"{field} 去除首尾空白后不得重复。")
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="校验员工与区域模拟数据报告输入。")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--normalized-output", required=True)
    parser.add_argument("--fallback-output", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    output = resolve_under_root(root, args.output)
    normalized_output = resolve_under_root(root, args.normalized_output)
    fallback_output = resolve_under_root(root, args.fallback_output)
    raw: object = {}
    try:
        raw = read_object(resolve_under_root(root, args.input, must_exist=True))
        required = ("employees", "regions", "group_by")
        missing = [field for field in required if raw.get(field) in (None, "", [])]
        time_range = raw.get("time_range")
        if time_range is not None:
            if not isinstance(time_range, dict):
                raise ValueError("time_range 必须是对象。")
            missing.extend(
                f"time_range.{field}"
                for field in ("start_date", "end_date")
                if not time_range.get(field)
            )
        if missing:
            write_json(output, {
                "state": "needs_input",
                "message": "请提供员工、区域和聚类维度；若填写时间范围，需同时提供开始与结束日期。",
                "missing_fields": missing,
                "warnings": [],
            })
            return 1

        employees = normalize_names(raw["employees"], "employees", 100)
        regions = normalize_names(raw["regions"], "regions", 50)
        group_by = raw["group_by"]
        if group_by not in {"employee", "region"}:
            raise ValueError("group_by 必须是 employee 或 region。")

        today = date.today()
        defaulted_time = time_range is None
        if defaulted_time:
            start_date = today - timedelta(days=29)
            end_date = today
        else:
            unknown_time = sorted(set(time_range) - {"start_date", "end_date"})
            if unknown_time:
                raise ValueError(f"time_range 存在未声明字段：{', '.join(unknown_time)}")
            try:
                start_date = date.fromisoformat(str(time_range["start_date"]))
                end_date = date.fromisoformat(str(time_range["end_date"]))
            except ValueError as exc:
                raise ValueError("time_range 日期必须使用 YYYY-MM-DD 格式。") from exc
            if start_date > end_date:
                raise ValueError("time_range.start_date 不得晚于 end_date。")
            if (end_date - start_date).days > 730:
                raise ValueError("time_range 最长支持 731 天。")

        record_count = raw.get("record_count", 5000)
        if isinstance(record_count, bool) or not isinstance(record_count, int) or not 100 <= record_count <= 100_000:
            raise ValueError("record_count 必须是 100 到 100000 之间的整数。")
        seed = raw.get("seed", 42)
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2_147_483_647:
            raise ValueError("seed 必须是 0 到 2147483647 之间的整数。")
        title = raw.get("report_title", "员工与区域数据质量报告")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("report_title 必须是非空字符串。")
        allowed = {"employees", "regions", "group_by", "time_range", "record_count", "seed", "report_title"}
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise ValueError(f"存在未声明字段：{', '.join(unknown)}")

        normalized = {
            "employees": employees,
            "regions": regions,
            "group_by": group_by,
            "time_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "defaulted": defaulted_time,
            },
            "record_count": record_count,
            "seed": seed,
            "report_title": title.strip(),
        }
        write_json(normalized_output, normalized)
        message = "输入校验通过。" + (" 时间范围已默认设为最近 30 天。" if defaulted_time else "")
        write_json(output, {"state": "valid", "message": message, "missing_fields": [], "warnings": []})
        return 0
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        message = f"输入无效：{exc}"
        write_json(output, {"state": "invalid", "message": message, "missing_fields": [], "warnings": []})
        write_fallback(fallback_output, original_input=raw, failed_step="validate_params", completed_steps=["parse_request"], available_artifacts=[], message=message)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
