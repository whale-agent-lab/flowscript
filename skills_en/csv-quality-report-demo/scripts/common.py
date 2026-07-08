"""Shared JSON, path, and fallback helpers for the demo skill scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_under_root(root: Path, value: str, *, must_exist: bool = False) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError("Paths must be relative to the skill directory.")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Paths must not escape the skill directory.") from exc
    if must_exist and not resolved.exists():
        raise ValueError(f"File does not exist: {value}")
    return resolved


def read_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")
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
        "suggested_recovery_actions": [
            "Check the input parameters",
            "Inspect the existing artifacts",
            "Fix and rerun the failed step",
            "Switch to standard skill mode and continue",
        ],
    })
