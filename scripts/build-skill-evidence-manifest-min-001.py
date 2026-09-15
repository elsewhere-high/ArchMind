#!/usr/bin/env python3
"""Build the final SHA-256 manifest after the evidence validator passes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


RUN_ID = "run-002-skill-evidence-min-001"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "samples" / "skill-evidence"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temp_name, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.run_root.resolve()
    validation = root / "06_validation/final-validator.txt"
    required = "SKILL_EVIDENCE_VALID\nrun=run-002-skill-evidence-min-001\nuses=7\nunique_skills=5\ntrace_complete=7/7\ndownstream_verified=7/7\ninput_unchanged=true\n"
    if not validation.is_file() or validation.read_text(encoding="utf-8") != required:
        raise SystemExit("FINAL_MANIFEST_REQUIRES_EXACT_VALIDATOR_PASS")
    sums_path = root / "07_manifest/sha256sums.txt"
    manifest_path = root / "07_manifest/final-manifest.json"
    if sums_path.exists() or manifest_path.exists():
        raise SystemExit("FINAL_MANIFEST_REFUSES_OVERWRITE")
    files = sorted(path for path in root.rglob("*") if path.is_file() and path not in {sums_path, manifest_path})
    records = [(sha256(path), path.relative_to(root).as_posix()) for path in files]
    sums_text = "".join(f"{digest}  {name}\n" for digest, name in records)
    atomic_text(sums_path, sums_text)
    sums_sha = sha256(sums_path)
    aggregate_records = sorted(records + [(sums_sha, "07_manifest/sha256sums.txt")], key=lambda item: item[1])
    aggregate_input = "".join(f"{digest}  {name}\n" for digest, name in aggregate_records).encode("utf-8")
    aggregate = hashlib.sha256(aggregate_input).hexdigest()
    manifest = {
        "manifest_version": "skill-evidence-min-001-final-v1",
        "run_id": RUN_ID,
        "task_id": "task-20260902-skill-evidence-min-001",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "file_count_excluding_manifest": len(aggregate_records),
        "sha256sums_sha256": sums_sha,
        "aggregate_sha256": aggregate,
        "manifest_self_excluded": True,
        "validator_result": "PASS",
        "input_unchanged": True,
    }
    atomic_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"SKILL_EVIDENCE_MANIFEST_READY aggregate_sha256={aggregate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
