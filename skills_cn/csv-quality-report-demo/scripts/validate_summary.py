"""复核 LLM 数据质量与聚类解读的结构。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from common import read_object, resolve_under_root, write_fallback, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="复核中文数据质量与聚类解读。")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fallback-output", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    output = resolve_under_root(root, args.output)
    fallback_output = resolve_under_root(root, args.fallback_output)
    data: object = {}
    try:
        data = read_object(resolve_under_root(root, args.input, must_exist=True))
        if not isinstance(data.get("summary"), str) or not data["summary"].strip():
            raise ValueError("summary 必须是非空字符串。")
        for field in ("risks", "recommendations", "cluster_insights"):
            value = data.get(field)
            if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"{field} 必须是至少包含一个非空字符串的数组。")
        write_json(output, {"state": "valid", "message": "中文数据质量与聚类解读结构复核通过。", "missing_fields": [], "warnings": []})
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        message = f"中文解读无效：{exc}"
        write_json(output, {"state": "invalid", "message": message, "missing_fields": [], "warnings": []})
        write_fallback(fallback_output, original_input=data, failed_step="validate_interpretation", completed_steps=["parse_request", "validate_params", "generate_and_profile", "interpret_profile"], available_artifacts=[args.input], message=message)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
