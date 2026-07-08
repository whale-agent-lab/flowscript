# 输入解析

从用户请求中提取结构化参数并调用 `submit_skill_inputs`。

规则：

- `employees`、`regions` 和 `group_by` 必须来自用户请求，不得编造。
- “按员工”映射为 `group_by: employee`；“按区域”映射为 `group_by: region`。
- 只有用户明确给出开始和结束日期时才填写 `time_range`。
- 未明确提供的 `record_count`、`seed` 和 `report_title` 可以省略，由校验脚本补默认值。
- 数组参数必须使用 JSON 数组。
- 只调用工具，不输出解释或 Markdown。
