"""Demo 技能脚本共享的 JSON、路径与 fallback 工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_under_root(root: Path, value: str, *, must_exist: bool = False) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError("路径必须相对于技能目录。")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("路径不得离开技能目录。") from exc
    if must_exist and not resolved.exists():
        raise ValueError(f"文件不存在：{value}")
    return resolved


def read_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("输入必须是 JSON 对象。")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_fallback(
    path: Path,
    *,
    original_input: Any,
    failed_step: str,
    completed_steps: list[str],
    available_artifacts: list[str],
    message: str,
) -> None:
    write_json(path, {
        "original_user_input": original_input,
        "failed_step": failed_step,
        "completed_steps": completed_steps,
        "available_artifacts": available_artifacts,
        "error_logs": [],
        "message": message,
        "suggested_recovery_actions": ["检查输入参数", "检查已有 artifact", "修正失败步骤后单独重跑", "切换到普通 skill mode 继续"],
    })