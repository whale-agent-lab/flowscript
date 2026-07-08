from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .errors import ToolExecutionError
from .trace_store import TraceStore


class ToolRuntime:
    def __init__(self, skill_root: Path, trace: TraceStore, *, max_read_bytes: int = 64_000) -> None:
        self.skill_root = skill_root.resolve()
        self.trace = trace
        self.max_read_bytes = max_read_bytes

    def resolve(self, value: str, *, must_exist: bool = False) -> Path:
        candidate = Path(value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.skill_root / candidate).resolve()
        try:
            resolved.relative_to(self.skill_root)
        except ValueError as exc:
            raise ToolExecutionError(f"path leaves skill root: {value}") from exc
        if must_exist and not resolved.exists():
            raise ToolExecutionError(f"path does not exist: {value}")
        return resolved

    def write_json(self, step_id: str, path: str, value: Any) -> None:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.trace.tool_exchange(
            step_id=step_id,
            tool_name="write_json",
            arguments={"path": path, "value": value},
            result={"status": "success", "path": path, "bytes": resolved.stat().st_size},
        )
        self.trace.event("artifact_written", step_id=step_id, payload={"path": path})

    def read_json(self, step_id: str, path: str) -> Any:
        resolved = self.resolve(path, must_exist=True)
        value = json.loads(resolved.read_text(encoding="utf-8"))
        self.trace.tool_exchange(
            step_id=step_id,
            tool_name="read_json",
            arguments={"path": path},
            result={"status": "success", "path": path, "value": value},
        )
        return value

    def read_file(self, step_id: str, path: str) -> str:
        resolved = self.resolve(path, must_exist=True)
        size = resolved.stat().st_size
        if size <= self.max_read_bytes:
            content = resolved.read_text(encoding="utf-8-sig")
            result: dict[str, Any] = {"status": "success", "path": path, "bytes": size, "content": content}
        else:
            raw = resolved.read_bytes()
            preview = raw[: min(4096, len(raw))].decode("utf-8-sig", errors="replace")
            result = {
                "status": "success",
                "path": path,
                "bytes": size,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "preview": preview,
            }
            if resolved.suffix.lower() == ".csv":
                with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
                    result["rows"] = max(0, sum(1 for _ in csv.reader(handle)) - 1)
        self.trace.tool_exchange(
            step_id=step_id,
            tool_name="read_file",
            arguments={"path": path, "max_bytes": self.max_read_bytes},
            result=result,
        )
        return result.get("content", result.get("preview", ""))

    def exec(
        self,
        step_id: str,
        argv: list[str],
        *,
        accepted_exit_codes: list[int],
        timeout_seconds: int = 60,
    ) -> subprocess.CompletedProcess[str]:
        if not argv:
            raise ToolExecutionError("exec argv cannot be empty")
        if argv[0].lower() not in {"python", "python3", "py"}:
            raise ToolExecutionError(f"unsupported executable: {argv[0]}")
        if len(argv) < 2:
            raise ToolExecutionError("python exec must name a script")
        script = self.resolve(argv[1], must_exist=True)
        if script.suffix.lower() != ".py":
            raise ToolExecutionError("python exec target must be a .py file")
        completed = subprocess.run(
            argv,
            cwd=self.skill_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )
        result = {
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-16_000:],
            "stderr": completed.stderr[-16_000:],
        }
        self.trace.tool_exchange(
            step_id=step_id,
            tool_name="exec",
            arguments={"argv": argv, "cwd": ".", "timeout_seconds": timeout_seconds},
            result=result,
        )
        if completed.returncode not in accepted_exit_codes:
            raise ToolExecutionError(
                f"unexpected exit code {completed.returncode}; accepted={accepted_exit_codes}"
            )
        return completed
