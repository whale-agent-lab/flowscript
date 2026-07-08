# Artifact 契约

运行目录为
运行目录为 `runs/{run_id}/`。生成数据与分析产物分开存放：`data/` 保存脚本生成、供后续步骤读取的数据；`artifacts/` 保存画像、解读、状态和最终报告。

关键文件：

- `valid_params.json`：规范化输入，包含员工、区域、聚类维度和明确时间闭区间。
- `data/generated_data.csv`：脚本生成的模拟历史数据，列为订单、员工、区域、金额、状态和时间；它不是用户输入，也不是最终交付报告。
- `artifacts/profile.json`：时间筛选结果、字段画像、缺失值、唯一值、数值统计、重复行和聚类统计。
- `artifacts/interpretation.json`：中文摘要、风险、建议和聚类洞察。
- `artifacts/final_report.md`：主要交付物。
- `artifacts/*_status.json`：结构化状态。
- `artifacts/fallback_context.json`：失败步骤、已完成步骤、可用 artifact、错误日志和中文恢复动作。
- `artifacts/artifacts_manifest.json`：最终产物清单。

脚本写出的 JSON 使用 UTF-8，机器状态保留英文，其余消息使用中文。模拟数据不得被描述为真实员工绩效数据。
