# 流程契约

流程依次执行请求解析、输入校验、模拟数据生成与画像、LLM 中文解读、解读复核和报告定稿。

员工列表、区域列表和聚类维度是必填输入。时间范围可选；省略时校验脚本写入截至当天的最近 30 天闭区间。LLM 解读必须输出 JSON 对象，包含非空字符串 `summary`，以及字符串数组 `risks`、`recommendations` 和 `cluster_insights`。

所有分支只读取状态文件的 `state`。`valid` 或 `success` 才能前进；`needs_input` 进入澄清；`invalid` 与 `recoverable_error` 在对应脚本写入 fallback context 后切换到普通模式；`fatal_error` 写入状态后终止。
