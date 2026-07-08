from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .errors import ModelProtocolError
from .i18n import tr


FUNCTION_PATTERN = re.compile(r"<function=([^>]+)>(.*?)</function>", re.DOTALL)
PARAM_PATTERN = re.compile(r"<parameter=([^>]+)>(.*?)</parameter>", re.DOTALL)


@dataclass
class ModelToolResult:
    name: str
    arguments: dict[str, Any]
    raw_response: dict[str, Any]
    source_format: str


class ModelAdapter:
    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:1234/v1/chat/completions",
        model: str = "qwen3.5-0.8b",
        timeout_seconds: int = 120,
        language: str = "en",
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.language = language

    def call_tool(
        self,
        *,
        prompt: str,
        user_content: str,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
    ) -> ModelToolResult:
        system = prompt.strip() + "\n\n" + tr("model_tool_instruction", self.language)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "tools": [{
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": schema,
                },
            }],
            "tool_choice": "required",
            "temperature": 0,
        }
        raw = self._post(payload)
        return self._normalize(raw, tool_name, schema)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("MINIMIZE_AGENT_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelProtocolError(f"model request failed: {exc}") from exc

    def _normalize(self, raw: dict[str, Any], expected_name: str, schema: dict[str, Any]) -> ModelToolResult:
        try:
            message = raw["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelProtocolError("response has no choices[0].message") from exc
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            function = tool_calls[0].get("function", {})
            name = function.get("name") or expected_name
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise ModelProtocolError("standard tool arguments are not valid JSON") from exc
            if not isinstance(arguments, dict):
                raise ModelProtocolError("standard tool arguments must be an object")
            arguments = _coerce_arguments(arguments, schema)
            return ModelToolResult(name, arguments, raw, "openai_tool_calls")

        combined = "\n".join(
            value for value in (message.get("reasoning_content"), message.get("content"))
            if isinstance(value, str) and value.strip()
        )
        xml = FUNCTION_PATTERN.search(combined)
        if xml:
            name = html.unescape(xml.group(1).strip())
            raw_arguments = {
                html.unescape(match.group(1).strip()): html.unescape(match.group(2).strip())
                for match in PARAM_PATTERN.finditer(xml.group(2))
            }
            arguments = _coerce_arguments(raw_arguments, schema)
            return ModelToolResult(name, arguments, raw, "qwen_reasoning_xml")

        parsed = _extract_json_object(combined)
        if parsed is not None:
            return ModelToolResult(expected_name, _coerce_arguments(parsed, schema), raw, "json_fallback")
        raise ModelProtocolError("model returned neither tool_calls, Qwen tool XML, nor a JSON object")


def _coerce_arguments(values: dict[str, str], schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    return {
        name: _coerce_value(value, properties.get(name, {}))
        for name, value in values.items()
    }


def _coerce_value(value: Any, schema: dict[str, Any]) -> Any:
    kind = schema.get("type")
    if kind == "object" and isinstance(value, dict):
        properties = schema.get("properties", {})
        return {
            name: _coerce_value(item, properties.get(name, {}))
            for name, item in value.items()
        }
    if kind == "array" and isinstance(value, list):
        item_schema = schema.get("items", {})
        return [_coerce_value(item, item_schema) for item in value]
    if not isinstance(value, str):
        return value

    text = value.strip()
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        loaded = None
    else:
        if kind == "object" and isinstance(loaded, dict):
            return _coerce_value(loaded, schema)
        if kind == "array" and isinstance(loaded, list):
            return _coerce_value(loaded, schema)
        if kind not in {"array", "object"}:
            return loaded

    if kind == "array":
        stripped = text.strip("[]")
        parts = [part.strip().strip(chr(34) + "'") for part in re.split(r"[,;\n]", stripped) if part.strip()]
        item_schema = schema.get("items", {})
        return [_coerce_value(part, item_schema) for part in parts]
    if kind == "integer":
        match = re.search(r"-?\d+", text)
        if match:
            return int(match.group(0))
    if kind == "number":
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if match:
            return float(match.group(0))
    if kind == "boolean":
        return text.lower() in {"true", "yes", "1", "y", "on"}
    if kind == "object":
        return text
    return text.strip(chr(34) + "'")


def _extract_json_object(text: str) -> dict[str, Any] | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    if not candidate:
        return None
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
