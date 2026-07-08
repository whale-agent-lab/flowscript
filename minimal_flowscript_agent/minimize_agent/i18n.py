"""Language detection and localized value selection."""

from __future__ import annotations

import locale
import os
from typing import Any


SUPPORTED_LANGUAGES = {"zh", "en"}

MESSAGES: dict[str, dict[str, str]] = {
    "model_tool_instruction": {
        "zh": "必须调用指定工具，不要输出解释。数组和对象参数必须使用合法 JSON；字符串只填写字段值，不要复述字段说明。",
        "en": "You must call the specified tool and return no explanation. Encode array and object parameters as valid JSON. For string parameters, provide only the field value and do not repeat the field description.",
    },
    "run_completed": {
        "zh": "FlowScript Skill 执行完成。",
        "en": "FlowScript Skill execution completed.",
    },
    "final_artifact": {
        "zh": "最终产物",
        "en": "Final artifact",
    },
    "run_failed": {
        "zh": "FlowScript Skill 执行失败",
        "en": "FlowScript Skill execution failed",
    },
}


def detect_language(override: str | None = None) -> str:
    """Return zh or en from an explicit override, environment, or system locale."""
    if override and override != "auto":
        normalized = normalize_language(override)
        if normalized:
            return normalized
        raise ValueError(f"Unsupported language: {override}")

    env_override = os.getenv("MINIMAL_FLOWSCRIPT_AGENT_LANG")
    if env_override:
        normalized = normalize_language(env_override)
        if normalized:
            return normalized

    candidates: list[str] = []
    try:
        current = locale.getlocale()
        if current and current[0]:
            candidates.append(current[0])
    except ValueError:
        pass
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.getenv(name)
        if value:
            candidates.append(value)
    for candidate in candidates:
        normalized = normalize_language(candidate)
        if normalized:
            return normalized
    return "en"


def normalize_language(value: str) -> str | None:
    text = value.strip().lower().replace("-", "_")
    if text.startswith("zh") or "chinese" in text or text in {"cn", "中文"}:
        return "zh"
    if text.startswith("en") or "english" in text:
        return "en"
    return None


def localized(value: Any, language: str) -> Any:
    """Select a localized DSL value; pass scalar values through unchanged."""
    if not isinstance(value, dict):
        return value
    if language in value:
        return value[language]
    fallback = "en" if language == "zh" else "zh"
    if fallback in value:
        return value[fallback]
    raise ValueError(f"Localized value has no {language!r} or fallback entry")


def tr(key: str, language: str) -> str:
    return MESSAGES[key][language]
