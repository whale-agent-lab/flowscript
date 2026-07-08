from __future__ import annotations

import json
from typing import Any

from .model_adapter import ModelAdapter
from .schema_subset import validate
from .trace_store import TraceStore


class FakeAgent:
    def __init__(self, model: ModelAdapter, trace: TraceStore) -> None:
        self.model = model
        self.trace = trace
        self.model_calls = 0

    def generate_tool_arguments(
        self,
        *,
        step_id: str,
        prompt: str,
        input_value: Any,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.model_calls += 1
        user_content = input_value if isinstance(input_value, str) else json.dumps(input_value, ensure_ascii=False, indent=2)
        self.trace.event("model_request", step_id=step_id, actor="fake-agent", payload={
            "model": self.model.model,
            "endpoint": self.model.endpoint,
            "tool": tool_name,
        })
        result = self.model.call_tool(
            prompt=prompt,
            user_content=user_content,
            tool_name=tool_name,
            tool_description=tool_description,
            schema=schema,
        )
        if result.name != tool_name:
            raise ValueError(f"model called {result.name!r}; expected {tool_name!r}")
        validate(result.arguments, schema)
        self.trace.tool_exchange(
            step_id=step_id,
            tool_name=tool_name,
            arguments=result.arguments,
            result={"status": "accepted", "source_format": result.source_format},
            actor="model",
            event_name="model_tool_call",
        )
        return result.arguments
