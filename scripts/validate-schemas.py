#!/usr/bin/env python3
"""Validate only artifacts for which this public package has formal schemas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("INVALID validation_environment: install requirements-validation.txt", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_instance(label: str, schema_path: Path, instance) -> bool:
    schema = load(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        print(f"INVALID {label}")
        for error in errors:
            location = "/".join(str(item) for item in error.absolute_path) or "<root>"
            print(f"  {location}: {error.message}")
        return False
    print(f"VALID {label}")
    return True


def main() -> int:
    ok = True
    drawing_schema = ROOT / "schemas" / "drawing-facts-v0.1.schema.json"
    drawing_sample = ROOT / "samples" / "drawing-facts-contract-v0.1.example.json"
    ok &= validate_instance("drawing-facts-contract-v0.1.example.json", drawing_schema, load(drawing_sample))

    # run-001 predates the Contract and intentionally uses a smaller task-input shape.
    print("NOT_SCHEMA_COVERED samples/case-001/drawing-facts.json (simplified synthetic input)")

    issue_schema = ROOT / "docs" / "issue-schema.json"
    for path in sorted((ROOT / "tests" / "fixtures" / "review" / "worker-results").glob("*.json")):
        for index, issue in enumerate(load(path)):
            ok &= validate_instance(f"{path.name}[{index}]", issue_schema, issue)

    print("NOT_SCHEMA_COVERED tests/fixtures/review/evidence-verification.json")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, KeyError) as error:
        print(f"INVALID validation_input: {error}", file=sys.stderr)
        raise SystemExit(1)
