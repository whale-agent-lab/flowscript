from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .errors import FlowScriptError, PlanValidationError, UnsupportedTerminalError
from .fake_agent import FakeAgent
from .flow_loader import output_path
from .i18n import localized, tr
from .schema_subset import validate
from .tool_runtime import ToolRuntime
from .trace_store import TraceStore


FULL_REFERENCE = re.compile(r"^\$\{([^}]+)\}$")
BRANCH_EXPRESSION = re.compile(r'^\$\{([^}]+)\}\s*(==|!=)\s*"([^"]*)"$')


class WorkflowEngine:
    def __init__(
        self,
        *,
        skill_root: Path,
        flow: dict[str, Any],
        run_id: str,
        user_request: str,
        fake_agent: FakeAgent,
        trace: TraceStore,
        structured_input: dict[str, Any] | None = None,
        language: str = "en",
    ) -> None:
        self.skill_root = skill_root.resolve()
        self.flow = flow
        self.run_id = run_id
        self.user_request = user_request
        self.fake_agent = fake_agent
        self.trace = trace
        self.tools = ToolRuntime(self.skill_root, trace)
        self.structured_input = structured_input
        self.language = language
        self.steps = {step["id"]: step for step in flow["steps"]}
        self.outputs: dict[str, dict[str, str]] = {}
        self.completed_steps: list[str] = []
        self.branches: list[dict[str, str]] = []
        self.started_at = time.monotonic()

    def run(self) -> dict[str, Any]:
        current = self.flow["steps"][0]["id"]
        self.trace.event("run_started", payload={"entry_step": current, "skill_root": str(self.skill_root)})
        try:
            while current != "end":
                step = self.steps[current]
                self.trace.event("node_started", step_id=current, payload={"type": step["type"]})
                if step["type"] == "terminal":
                    reason = step.get("reason", "unsupported_terminal")
                    self.trace.event("unsupported_terminal", step_id=current, payload={"reason": reason})
                    raise UnsupportedTerminalError(f"reached unsupported terminal {current}: {reason}")
                if step["type"] == "llm":
                    self._run_llm(step)
                elif step["type"] in {"script", "validator"}:
                    self._run_command(step)
                else:
                    raise PlanValidationError(f"unsupported step type: {step['type']}")
                self.completed_steps.append(current)
                self.trace.event("node_completed", step_id=current, payload={"outputs": self.outputs[current]})
                current = self._select_next(step)

            primary = self._find_primary_artifact()
            report_content = self.tools.read_file("end", primary) if primary else ""
            final_answer = tr("run_completed", self.language)
            if primary:
                final_answer += f"\n\n{tr('final_artifact', self.language)}: `{primary}`"
            if report_content:
                final_answer += f"\n\n{report_content}"
            self.trace.add_final_answer(final_answer)
            self.trace.event("run_completed", payload={"primary_artifact": primary})
            result = self._result("success", primary_artifact=primary)
            self.trace.write_result(result)
            return result
        except Exception as exc:
            self.trace.event("node_failed", step_id=current, payload={"error": str(exc), "type": type(exc).__name__})
            self.trace.add_final_answer(f"{tr('run_failed', self.language)}: {exc}")
            result = self._result("failed", error=str(exc), error_type=type(exc).__name__)
            self.trace.write_result(result)
            raise
        finally:
            self.trace.flush_context()

    def _run_llm(self, step: dict[str, Any]) -> None:
        step_id = step["id"]
        outputs = self._render_outputs(step)
        self.outputs[step_id] = outputs
        output_name, output_spec = next(iter(step["output"].items()))
        if not isinstance(output_spec, dict):
            raise PlanValidationError(f"{step_id}: LLM output must use path/schema mapping")
        prompt_path = localized(step["prompt"], self.language)
        prompt = self.tools.read_file(step_id, prompt_path)
        schema = self.tools.read_json(step_id, output_spec["schema"])
        input_value = self._materialize_llm_input(step)
        tool_name = step["tool"]["name"]
        tool_description = localized(step["tool"].get("description", f"Submit output for {step_id}"), self.language)

        if self.structured_input is not None and step.get("input_mode") == "skill_inputs":
            arguments = self.structured_input
            validate(arguments, schema)
            self.trace.tool_exchange(
                step_id=step_id,
                tool_name=tool_name,
                arguments=arguments,
                result={"status": "accepted", "source_format": "structured_input"},
                actor="model",
                event_name="model_tool_call",
            )
        else:
            arguments = self.fake_agent.generate_tool_arguments(
                step_id=step_id,
                prompt=prompt,
                input_value=input_value,
                tool_name=tool_name,
                tool_description=tool_description,
                schema=schema,
            )
        self.tools.write_json(step_id, outputs[output_name], arguments)

    def _run_command(self, step: dict[str, Any]) -> None:
        step_id = step["id"]
        inputs = self._resolve_inputs(step)
        outputs = self._render_outputs(step)
        self.outputs[step_id] = outputs
        command = step["command"]
        argv = [command["executable"]]
        for raw in command["args"]:
            argv.append(str(self._resolve_value(raw, inputs, outputs)))
        self.tools.exec(
            step_id,
            argv,
            accepted_exit_codes=command["accepted_exit_codes"],
            timeout_seconds=int(command.get("timeout_seconds", 60)),
        )
        for name, spec in step.get("output", {}).items():
            required = not isinstance(spec, dict) or spec.get("required", True)
            path = outputs[name]
            exists = self.tools.resolve(path).exists()
            if required and not exists:
                raise FlowScriptError(f"{step_id}: required output was not created: {path}")
            if exists:
                self.trace.event("artifact_written", step_id=step_id, payload={"name": name, "path": path})

    def _materialize_llm_input(self, step: dict[str, Any]) -> Any:
        values = self._resolve_inputs(step)
        materialized: dict[str, Any] = {}
        for name, value in values.items():
            if name == "request" and value == self.user_request:
                materialized[name] = value
                continue
            if isinstance(value, str):
                path = self.tools.resolve(value)
                if path.is_file():
                    materialized[name] = (
                        self.tools.read_json(step["id"], value)
                        if path.suffix.lower() == ".json"
                        else self.tools.read_file(step["id"], value)
                    )
                    continue
            materialized[name] = value
        if len(materialized) == 1:
            return next(iter(materialized.values()))
        return materialized

    def _resolve_inputs(self, step: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, raw in step.get("input", {}).items():
            result[name] = self._resolve_value(raw, result, self.outputs.get(step["id"], {}))
        return result

    def _render_outputs(self, step: dict[str, Any]) -> dict[str, str]:
        return {
            name: output_path(spec).replace("{run_id}", self.run_id)
            for name, spec in step.get("output", {}).items()
        }

    def _resolve_value(self, raw: Any, current_inputs: dict[str, Any], current_outputs: dict[str, str]) -> Any:
        if not isinstance(raw, str):
            return raw
        match = FULL_REFERENCE.match(raw)
        if not match:
            return raw.replace("{run_id}", self.run_id)
        token = match.group(1)
        if token == "user.request":
            return self.user_request
        parts = token.split(".")
        if parts[0] == "input" and len(parts) == 2:
            return current_inputs[parts[1]]
        if parts[0] == "output" and len(parts) == 2:
            return current_outputs[parts[1]]
        if len(parts) >= 3 and parts[1] == "output":
            return self.outputs[parts[0]][parts[2]]
        raise FlowScriptError(f"unsupported reference: {raw}")

    def _select_next(self, step: dict[str, Any]) -> str:
        if "branches" not in step:
            return step.get("next", "end")
        cache: dict[str, Any] = {}
        for branch_name, branch in step["branches"].items():
            match = BRANCH_EXPRESSION.match(branch["when"])
            if not match:
                raise FlowScriptError(f"unsupported branch expression: {branch['when']}")
            token, operator, expected = match.groups()
            actual = self._branch_value(step["id"], token, cache)
            selected = actual == expected if operator == "==" else actual != expected
            if selected:
                target = branch["next"]
                self.branches.append({"step_id": step["id"], "branch": branch_name, "next": target})
                self.trace.event("branch_selected", step_id=step["id"], payload={
                    "branch": branch_name,
                    "actual": actual,
                    "operator": operator,
                    "expected": expected,
                    "next": target,
                })
                return target
        raise FlowScriptError(f"{step['id']}: no branch condition matched")

    def _branch_value(self, current_step: str, token: str, cache: dict[str, Any]) -> Any:
        parts = token.split(".")
        if len(parts) < 4 or parts[1] != "output":
            raise FlowScriptError(f"branch reference must target output JSON field: {token}")
        path = self.outputs[parts[0]][parts[2]]
        if path not in cache:
            cache[path] = self.tools.read_json(current_step, path)
        value = cache[path]
        for field in parts[3:]:
            if not isinstance(value, dict) or field not in value:
                raise FlowScriptError(f"branch field does not exist: {token}")
            value = value[field]
        return value

    def _find_primary_artifact(self) -> str | None:
        for step_id in reversed(self.completed_steps):
            for key in ("report", "result", "artifact"):
                if key in self.outputs.get(step_id, {}):
                    path = self.outputs[step_id][key]
                    if self.tools.resolve(path).is_file():
                        return path
        return None

    def _result(self, status: str, **extra: Any) -> dict[str, Any]:
        return {
            "status": status,
            "run_id": self.run_id,
            "language": self.language,
            "completed_steps": self.completed_steps,
            "branches": self.branches,
            "skill_agent_context": str(self.trace.context_path.relative_to(self.skill_root)).replace("\\", "/"),
            "trace": str(self.trace.trace_path.relative_to(self.skill_root)).replace("\\", "/"),
            "tool_call_count": self.trace.tool_seq,
            "model_call_count": self.fake_agent.model_calls,
            "elapsed_seconds": round(time.monotonic() - self.started_at, 3),
            **extra,
        }
