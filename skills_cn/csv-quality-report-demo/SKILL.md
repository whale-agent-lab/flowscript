---
name: csv-quality-report-demo
description: 生成包含员工、区域、金额、状态和时间字段的模拟 CSV 数据，按可选时间范围筛选，并按员工或区域聚类分析数据质量与业务分布。用户要求演示带受控分支和 fallback 的多步 FlowScript，或需要员工/区域维度的模拟数据质量报告时使用。
---

# CSV 数据质量与聚类报告 Demo

根据用户提供的员工和区域生成较大规模的确定性模拟 CSV，按时间筛选后完成字段画像、质量统计、员工或区域聚类分析，并生成中文报告。不读取或修改外部 CSV。

## 输入

- `employees`：必填，非空员工名称数组。
- `regions`：必填，非空区域名称数组。
- `group_by`：必填，`employee` 或 `region`，决定聚类维度。
- `time_range`：可选，包含 `start_date` 和 `end_date`；省略时使用截至当天的最近 30 天。
- `record_count`：可选，模拟历史记录数，默认 `5000`。
- `seed`：可选，确定性随机种子，默认 `42`。
- `report_title`：可选，默认“员工与区域数据质量报告”。

输入约束以 `input_schema.json` 为准。缺少员工、区域或聚类维度时必须向用户询问，不得自行编造。

## 普通 agent 模式

1. 将用户请求解析为 `resolved_params.json`。
2. 运行 `scripts/validate.py`；根据 `missing_fields` 用中文询问必填信息。时间缺省由脚本规范化为最近 30 天。
3. 状态为 `valid` 后运行 `scripts/execute.py`，在 `runs/{run_id}/data/` 生成 `generated_data.csv`，并在 `artifacts/` 生成确定性的 `profile.json`。
4. 根据字段画像与 `cluster_analysis` 生成中文 `interpretation.json`，包含 `summary`、`risks`、`recommendations` 和 `cluster_insights`。
5. 运行 `scripts/validate_summary.py` 复核解读结构。
6. 运行 `scripts/finalize.py`，生成最终 Markdown 报告。
7. 任一步失败时读取 `fallback_context.json`，从最近的有效 artifact 继续。

## FlowScript 模式

运行时支持 FlowScript 时，使用 `FLOWSCRIPT.md` 作为受控执行配置，不在本文件中复制 DSL。

## 生成数据

- `runs/{run_id}/data/generated_data.csv`：包含 `order_id`、`employee_name`、`region`、`amount`、`status`、`event_date` 的模拟分析数据，不是用户输入，也不是最终报告。

## 分析产物

- `profile.json`：时间筛选、字段画像、缺失值、重复行和聚类统计。
- `interpretation.json`：经脚本复核的中文风险与聚类解读。
- `final_report.md`：最终中文报告。
- 各阶段结构化状态、manifest 和 fallback context。

## 约束

- 只生成模拟数据，不把模拟结果表述为真实员工绩效。
- 员工和区域必须来自用户输入；不得补充未声明的名称。
- 时间筛选必须使用规范化后的闭区间。
- 只基于结构化状态进入分支。
- 在解读通过复核前不生成最终报告。
