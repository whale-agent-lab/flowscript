from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class TraceStore:
    def __init__(self, runtime_dir: Path, run_id: str, user_request: str) -> None:
        self.runtime_dir = runtime_dir
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.trace_path = runtime_dir / "trace.jsonl"
        self.context_path = runtime_dir / "skill_agent_context.json"
        self.result_path = runtime_dir / "result.json"
        self.seq = 0
        self.tool_seq = 0
        self.events: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = [{"role": "user", "content": user_request}]

    def event(self, event: str, *, step_id: str | None = None, actor: str = "runtime", payload: Any = None) -> None:
        self.seq += 1
        item = {
            "seq": self.seq,
            "timestamp": time.time(),
            "run_id": self.run_id,
            "step_id": step_id,
            "actor": actor,
            "event": event,
            "payload": payload if payload is not None else {},
        }
        self.events.append(item)
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    def next_tool_call_id(self) -> str:
        self.tool_seq += 1
        return f"call_{self.tool_seq:04d}"

    def tool_exchange(
        self,
        *,
        step_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        actor: str = "fake-agent",
        event_name: str = "tool_call",
    ) -> str:
        call_id = self.next_tool_call_id()
        self.messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }],
        })
        self.messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": json.dumps(result, ensure_ascii=False),
        })
        self.event(event_name, step_id=step_id, actor=actor, payload={
            "tool_call_id": call_id,
            "tool": tool_name,
            "arguments": arguments,
        })
        self.event("tool_result", step_id=step_id, actor="tool", payload={
            "tool_call_id": call_id,
            "tool": tool_name,
            "result": result,
        })
        return call_id

    def add_final_answer(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def flush_context(self) -> None:
        self.context_path.write_text(
            json.dumps(self.messages, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_result(self, result: dict[str, Any]) -> None:
        self.result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
