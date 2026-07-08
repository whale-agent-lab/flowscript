from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .errors import PlanValidationError


FLOW_BLOCK = re.compile(r"```flow\s*\n(.*?)\n```", re.DOTALL)
REFERENCE = re.compile(r"\$\{([^}]+)\}")


def load_flow(skill_root: Path) -> dict[str, Any]:
    path = skill_root / "FLOWSCRIPT.md"
    if not path.is_file():
        raise PlanValidationError(f"missing FLOWSCRIPT.md: {path}")
    text = path.read_text(encoding="utf-8")
    matches = FLOW_BLOCK.findall(text)
    if len(matches) != 1:
        raise PlanValidationError(f"expected exactly one flow block, found {len(matches)}")
    try:
        flow = yaml.safe_load(matches[0])
    except yaml.YAMLError as exc:
        raise PlanValidationError(f"invalid flow YAML: {exc}") from exc
    if not isinstance(flow, dict):
        raise PlanValidationError("flow block must contain a mapping")
    return flow


def output_path(spec: Any) -> str:
    if isinstance(spec, str):
        return spec
    if isinstance(spec, dict) and isinstance(spec.get("path"), str):
        return spec["path"]
    raise PlanValidationError(f"invalid output declaration: {spec!r}")


def validate_plan(flow: dict[str, Any], skill_root: Path) -> None:
    if flow.get("version") != 1:
        raise PlanValidationError("only FlowScript version 1 is supported")
    if flow.get("mode") != "controlled":
        raise PlanValidationError("only controlled mode is supported")
    schema_path = flow.get("inputs", {}).get("schema")
    if not isinstance(schema_path, str) or not (skill_root / schema_path).is_file():
        raise PlanValidationError("inputs.schema must point to an existing file")
    steps = flow.get("steps")
    if not isinstance(steps, list) or not steps:
        raise PlanValidationError("steps must be a non-empty list")
    ids = [step.get("id") for step in steps if isinstance(step, dict)]
    if len(ids) != len(steps) or any(not isinstance(value, str) for value in ids):
        raise PlanValidationError("every step must have a string id")
    if len(ids) != len(set(ids)):
        raise PlanValidationError("step ids must be unique")
    known = set(ids) | {"end"}
    seen: set[str] = set()
    supported = {"llm", "script", "validator", "terminal"}
    for step in steps:
        step_id = step["id"]
        step_type = step.get("type")
        if step_type not in supported:
            raise PlanValidationError(f"{step_id}: unsupported type {step_type!r}")
        for target in _targets(step):
            if target not in known:
                raise PlanValidationError(f"{step_id}: unknown target {target!r}")
        _validate_references(step, seen, step_id)
        outputs = step.get("output", {})
        if not isinstance(outputs, dict):
            raise PlanValidationError(f"{step_id}: output must be a mapping")
        for spec in outputs.values():
            rendered = output_path(spec).replace("{run_id}", "validation")
            _assert_under_skill(skill_root, rendered, step_id)
        if step_type in {"script", "validator"}:
            _validate_command(step, skill_root)
        if step_type == "llm":
            _validate_llm(step, skill_root)
        seen.add(step_id)


def _targets(step: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    if "next" in step:
        targets.append(step["next"])
    for branch in step.get("branches", {}).values():
        if not isinstance(branch, dict) or "when" not in branch or "next" not in branch:
            raise PlanValidationError(f"{step.get('id')}: every branch needs when and next")
        targets.append(branch["next"])
    return targets


def _validate_references(step: dict[str, Any], seen: set[str], step_id: str) -> None:
    text = yaml.safe_dump(step, allow_unicode=True)
    for token in REFERENCE.findall(text):
        if token.startswith(("input.", "output.", "user.")):
            continue
        owner = token.split(".", 1)[0]
        if owner not in seen and owner != step_id:
            raise PlanValidationError(f"{step_id}: reference points to non-previous step: {token}")


def _validate_command(step: dict[str, Any], skill_root: Path) -> None:
    step_id = step["id"]
    command = step.get("command")
    if not isinstance(command, dict):
        raise PlanValidationError(f"{step_id}: command must be a mapping")
    if command.get("executable") not in {"python", "python3", "py"}:
        raise PlanValidationError(f"{step_id}: only Python commands are supported")
    args = command.get("args")
    if not isinstance(args, list) or not args or not isinstance(args[0], str):
        raise PlanValidationError(f"{step_id}: command.args must start with a script path")
    script = (skill_root / args[0]).resolve()
    _assert_resolved_under(skill_root, script, step_id)
    if not script.is_file():
        raise PlanValidationError(f"{step_id}: script does not exist: {args[0]}")
    codes = command.get("accepted_exit_codes")
    if not isinstance(codes, list) or any(not isinstance(code, int) for code in codes):
        raise PlanValidationError(f"{step_id}: accepted_exit_codes must be integers")
    if step.get("branches") and not isinstance(command.get("status_source"), str):
        raise PlanValidationError(f"{step_id}: branched command needs status_source")


def _validate_llm(step: dict[str, Any], skill_root: Path) -> None:
    step_id = step["id"]
    prompt = step.get("prompt")
    if isinstance(prompt, str):
        prompt_paths = [prompt]
    elif (
        isinstance(prompt, dict)
        and prompt
        and set(prompt).issubset({"zh", "en"})
        and all(isinstance(value, str) for value in prompt.values())
    ):
        prompt_paths = list(prompt.values())
    else:
        raise PlanValidationError(
            f"{step_id}: prompt must be a path or a non-empty zh/en mapping"
        )
    missing_prompts = [value for value in prompt_paths if not (skill_root / value).is_file()]
    if missing_prompts:
        raise PlanValidationError(f"{step_id}: prompt files do not exist: {missing_prompts}")
    tool = step.get("tool")
    if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
        raise PlanValidationError(f"{step_id}: LLM node needs tool.name")
    outputs = step.get("output", {})
    if len(outputs) != 1:
        raise PlanValidationError(f"{step_id}: MVP LLM node must have exactly one output")
    spec = next(iter(outputs.values()))
    if not isinstance(spec, dict) or not isinstance(spec.get("schema"), str):
        raise PlanValidationError(f"{step_id}: LLM output needs path and schema")
    if not (skill_root / spec["schema"]).is_file():
        raise PlanValidationError(f"{step_id}: output schema does not exist")


def _assert_under_skill(skill_root: Path, value: str, step_id: str) -> None:
    _assert_resolved_under(skill_root, (skill_root / value).resolve(), step_id)


def _assert_resolved_under(skill_root: Path, path: Path, step_id: str) -> None:
    try:
        path.relative_to(skill_root.resolve())
    except ValueError as exc:
        raise PlanValidationError(f"{step_id}: path leaves skill root: {path}") from exc
