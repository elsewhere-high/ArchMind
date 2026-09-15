#!/usr/bin/env python3
"""Create the deterministic final consumer of the review-summary output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


RUN_ID = "run-002-skill-evidence-min-001"
TASK_ID = "task-20260902-skill-evidence-min-001"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "samples" / "skill-evidence"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp_name, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.run_root.resolve()
    trace_path = root / "03_skill-traces/TRACE-SEMIN001-07.json"
    summary_path = root / "04_outputs/team-summary.md"
    target = root / "05_downstream/final-evidence-only-summary.json"
    if target.exists():
        raise SystemExit(f"FINAL_EVIDENCE_SUMMARY_REFUSES_OVERWRITE: {target}")
    if not trace_path.is_file() or not summary_path.is_file():
        raise SystemExit("FINAL_EVIDENCE_SUMMARY_MISSING_USE07_TRACE_OR_OUTPUT")
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    summary_hash = digest(summary_path)
    if trace.get("output_sha256") != summary_hash:
        raise SystemExit("FINAL_EVIDENCE_SUMMARY_USE07_HASH_MISMATCH")
    value = {
        "summary_type": "SKILL_EVIDENCE_ONLY",
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "source_trace_id": "TRACE-SEMIN001-07",
        "source_review_summary_reference": "04_outputs/team-summary.md",
        "source_review_summary_sha256": summary_hash,
        "effect": "Consumed review-summary output as the final non-Human evidence-only summary.",
        "human_gate_entered": False,
        "human_decision_generated": False,
    }
    atomic_json(target, value)
    print(f"FINAL_EVIDENCE_ONLY_SUMMARY_READY {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
