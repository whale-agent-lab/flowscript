from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .engine import WorkflowEngine
from .fake_agent import FakeAgent
from .flow_loader import load_flow, validate_plan
from .i18n import detect_language
from .model_adapter import ModelAdapter
from .trace_store import TraceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a validation-only FlowScript workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run a skill workflow")
    run.add_argument("--skill", required=True, help="Path to the FlowScript skill directory")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", help="Natural-language user request")
    source.add_argument("--input-json", help="Structured input JSON; skips the first model call")
    run.add_argument("--run-id", default=None)
    run.add_argument("--model", default="qwen3.5-0.8b")
    run.add_argument("--endpoint", default="http://127.0.0.1:1234/v1/chat/completions")
    run.add_argument("--model-timeout", type=int, default=120)
    run.add_argument("--language", choices=["auto", "zh", "en"], default="auto")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "run":
        return 2
    skill_root = Path(args.skill).resolve()
    if not skill_root.is_dir():
        print(f"Skill directory does not exist: {skill_root}", file=sys.stderr)
        return 2
    structured_input = None
    if args.input_json:
        input_path = Path(args.input_json).resolve()
        structured_input = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(structured_input, dict):
            print("--input-json must contain a JSON object", file=sys.stderr)
            return 2
        user_request = json.dumps(structured_input, ensure_ascii=False)
    else:
        user_request = args.request
    run_id = args.run_id or datetime.now().strftime("run-%Y%m%d-%H%M%S")
    runtime_dir = skill_root / "runs" / run_id / "runtime"
    if (runtime_dir / "trace.jsonl").exists():
        print(f"Run already exists and cannot be resumed in MVP: {run_id}", file=sys.stderr)
        return 2
    trace = TraceStore(runtime_dir, run_id, user_request)
    try:
        flow = load_flow(skill_root)
        validate_plan(flow, skill_root)
        language = detect_language(args.language)
        model = ModelAdapter(args.endpoint, args.model, args.model_timeout, language)
        fake_agent = FakeAgent(model, trace)
        engine = WorkflowEngine(
            skill_root=skill_root,
            flow=flow,
            run_id=run_id,
            user_request=user_request,
            fake_agent=fake_agent,
            trace=trace,
            structured_input=structured_input,
            language=language,
        )
        result = engine.run()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"FlowScript run failed: {exc}", file=sys.stderr)
        print(f"Context: {trace.context_path}", file=sys.stderr)
        print(f"Trace: {trace.trace_path}", file=sys.stderr)
        return 1
