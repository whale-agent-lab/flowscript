"""Validate the structure of an LLM data-quality and grouping interpretation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from common import read_object, resolve_under_root, write_fallback, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an English data-quality and grouping interpretation.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fallback-output", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    output = resolve_under_root(root, args.output)
    fallback_output = resolve_under_root(root, args.fallback_output)
    data: object = {}
    try:
        data = read_object(resolve_under_root(root, args.input, must_exist=True))
        if not isinstance(data.get("summary"), str) or not data["summary"].strip():
            raise ValueError("summary must be a non-empty string.")
        for field in ("risks", "recommendations", "cluster_insights"):
            value = data.get(field)
            if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"{field} must be an array containing at least one non-empty string.")
        write_json(output, {"state": "valid", "message": "The English data-quality and grouping interpretation passed structural validation.", "missing_fields": [], "warnings": []})
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        message = f"Invalid English interpretation: {exc}"
        write_json(output, {"state": "invalid", "message": message, "missing_fields": [], "warnings": []})
        write_fallback(fallback_output, original_input=data, failed_step="validate_interpretation", completed_steps=["parse_request", "validate_params", "generate_and_profile", "interpret_profile"], available_artifacts=[args.input], message=message)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
