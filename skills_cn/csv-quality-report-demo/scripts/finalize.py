"""组合模拟数据画像与中文解读，生成最终 Markdown 报告和 manifest。"""

from __future__ import annotations

import argparse
from pathlib import Path
from common import read_object, resolve_under_root, write_fallback, write_json


def escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成最终员工与区域数据质量报告。")
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
        dimension_label = "员工" if profile["cluster_dimension"] == "employee" else "区域"
        lines = [
            f"# {params['report_title']}", "",
            "> 本报告使用确定性模拟数据，仅用于流程演示，不代表真实员工绩效。", "",
            f"- 模拟数据：`{Path(args.data).as_posix()}`",
            f"- 生成记录数：{profile['generation']['generated_row_count']}",
            f"- 筛选时间：{time_filter['start_date']} 至 {time_filter['end_date']}",
            f"- 是否使用默认时间：{'是' if time_filter['defaulted'] else '否'}",
            f"- 筛选后记录数：{profile['analyzed_row_count']}",
            f"- 聚类维度：{dimension_label}",
            f"- 重复行数：{profile['duplicate_row_count']}", "",
            "## 总体解读", "", interpretation["summary"], "",
            f"## 按{dimension_label}聚类", "",
            f"| {dimension_label} | 记录数 | 有效金额数 | 总金额 | 平均金额 | 完成数 | 完成率 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for cluster in profile["cluster_analysis"]:
            average = "-" if cluster["average_amount"] is None else f"{cluster['average_amount']:.2f}"
            lines.append(
                f"| {escape(cluster['group_value'])} | {cluster['row_count']} | {cluster['amount_present_count']} | "
                f"{cluster['total_amount']:.2f} | {average} | {cluster['completed_count']} | {cluster['completion_rate']:.2%} |"
            )
        lines.extend(["", "### 聚类洞察", ""])
        lines.extend(f"- {item}" for item in interpretation["cluster_insights"])
        lines.extend([
            "", "## 字段画像", "",
            "| 字段 | 缺失数 | 缺失率 | 唯一值数 | 数值数 | 示例 |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for column in profile["columns"]:
            samples = "、".join(escape(value) for value in column["sample_values"])
            lines.append(f"| {escape(column['name'])} | {column['missing_count']} | {column['missing_rate']:.2%} | {column['unique_count']} | {column['numeric_value_count']} | {samples} |")
        lines.extend(["", "## 风险", ""])
        lines.extend(f"- {item}" for item in interpretation["risks"])
        lines.extend(["", "## 建议", ""])
        lines.extend(f"- {item}" for item in interpretation["recommendations"])
        lines.extend(["", "## 说明", "", "质量与聚类统计只针对选定时间闭区间。模拟数据不得用于真实考核、奖惩或人员决策。", ""])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines), encoding="utf-8")
        write_json(status_output, {"state": "success", "message": "最终中文聚类质量报告生成完成。", "warnings": []})
        write_json(manifest_output, {
            "primary_result": Path(args.output).as_posix(),
            "data_files": [Path(args.data).as_posix()],
            "editable_artifacts": [Path(args.interpretation).as_posix()],
            "status_files": [str(Path(args.status_output).parent / name).replace("\\", "/") for name in ("validation_status.json", "profile_status.json", "interpretation_status.json", "finalize_status.json")],
            "logs": [],
        })
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        message = f"最终报告生成失败：{exc}"
        write_json(status_output, {"state": "recoverable_error", "message": message, "warnings": []})
        write_fallback(fallback_output, original_input={"params": args.params, "profile": args.profile, "interpretation": args.interpretation, "data": args.data}, failed_step="finalize_report", completed_steps=["parse_request", "validate_params", "generate_and_profile", "interpret_profile", "validate_interpretation"], available_artifacts=[args.params, args.data, args.profile, args.interpretation], message=message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
