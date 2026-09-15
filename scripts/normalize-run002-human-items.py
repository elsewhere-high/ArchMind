#!/usr/bin/env python3
"""Normalize immutable Run-002 Human Items for the Human Gate.

This adapter only creates a new canonical document. It never edits the source
Human Items, changes task state, or creates a HumanDecision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


NORMALIZATION_VERSION = "run002-human-item-adapter-v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_source(path: str) -> tuple[Any, bytes, str]:
    if path == "-":
        raw = sys.stdin.buffer.read()
        label = "stdin"
    else:
        source_path = Path(path)
        raw = source_path.read_bytes()
        label = str(source_path)
    return json.loads(raw.decode("utf-8")), raw, label


def extract_items(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        items = document
    elif isinstance(document, dict):
        items = document.get("human_items", document.get("human_confirmation_items"))
    else:
        items = None
    if not isinstance(items, list):
        raise ValueError("source must be an array or contain human_items/human_confirmation_items")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError("every source Human Item must be an object")
    return items


def normalize_document(
    document: Any,
    *,
    source_label: str,
    source_artifact_hash: str,
    run_id: str,
    task_id: str,
    expected_count: int,
) -> dict[str, Any]:
    source_items = extract_items(document)
    if len(source_items) != expected_count:
        raise ValueError(
            f"expected {expected_count} source Human Items, found {len(source_items)}"
        )

    canonical_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source_item in source_items:
        source_item_id = source_item.get("item_id")
        if not isinstance(source_item_id, str) or not source_item_id:
            raise ValueError("every source Human Item must have a non-empty item_id")
        if source_item_id in seen:
            raise ValueError(f"duplicate source item_id: {source_item_id}")
        seen.add(source_item_id)

        canonical_item = {
            key: value for key, value in source_item.items() if key != "item_id"
        }
        canonical_item.update(
            {
                "human_item_id": source_item_id,
                "source_item_id": source_item_id,
                "source_hash": sha256_bytes(canonical_bytes(source_item)),
                "normalization_version": NORMALIZATION_VERSION,
                "status": "pending_human",
                "requires_human_review": True,
            }
        )
        canonical_items.append(canonical_item)

    return {
        "run_id": run_id,
        "task_id": task_id,
        "normalization_version": NORMALIZATION_VERSION,
        "source_artifact": source_label,
        "source_artifact_hash": source_artifact_hash,
        "human_items": canonical_items,
    }


def write_output(path: str, document: dict[str, Any]) -> None:
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if path == "-":
        sys.stdout.write(payload)
        return

    output_path = Path(path)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="source Human Items path, or - for stdin")
    parser.add_argument("--output", required=True, help="new canonical path, or - for stdout")
    parser.add_argument("--run-id", default="run-002-human-gate")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--expected-count", type=int, default=12)
    parser.add_argument(
        "--source-artifact-label",
        help="immutable source reference recorded when --input is stdin",
    )
    args = parser.parse_args()

    document, raw, detected_label = load_source(args.input)
    source_label = args.source_artifact_label or detected_label
    canonical = normalize_document(
        document,
        source_label=source_label,
        source_artifact_hash=sha256_bytes(raw),
        run_id=args.run_id,
        task_id=args.task_id,
        expected_count=args.expected_count,
    )
    write_output(args.output, canonical)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"RUN002_HUMAN_ITEM_NORMALIZATION_FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
