#!/usr/bin/env python3
"""Record one real declarative Skill use from raw runtime evidence.

This observer never executes a Core Skill and never invents a runtime ID. It
hashes files that already exist, validates a raw session/tool fragment, writes
one immutable trace, and rebuilds the aggregate ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_ID = "run-002-skill-evidence-min-001"
TASK_ID = "task-20260902-skill-evidence-min-001"
RECORDER_VERSION = "skill-evidence-recorder-v1"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "samples" / "skill-evidence"


class RecordError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecordError(f"invalid timestamp: {value}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"cannot read JSON {path}: {exc}") from exc


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def resolve_reference(run_root: Path, reference: str) -> Path:
    candidate = (run_root / reference).resolve()
    root = run_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise RecordError(f"reference escapes run root: {reference}")
    return candidate


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecordError(message)


def contract_use(contract: dict[str, Any], use_id: str) -> dict[str, Any]:
    matches = [item for item in contract["skill_uses"] if item["use_id"] == use_id]
    require(len(matches) == 1, f"unknown or duplicate use_id: {use_id}")
    return matches[0]


def same_path(argument: Any, expected: Path) -> bool:
    if not isinstance(argument, str) or not argument:
        return False
    try:
        return Path(argument).resolve() == expected.resolve()
    except OSError:
        return argument == str(expected)


def copy_evidence(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        require(sha256_file(source) == sha256_file(target), f"refusing to overwrite different evidence: {target}")
        return
    shutil.copyfile(source, target)


def rebuild_ledger(run_root: Path) -> None:
    entries: list[dict[str, Any]] = []
    for trace_path in sorted((run_root / "03_skill-traces").glob("TRACE-SEMIN001-0[1-7].json")):
        trace = load_json(trace_path)
        entries.append({
            "trace_file": trace_path.relative_to(run_root).as_posix(),
            "trace_file_sha256": sha256_file(trace_path),
            "trace": trace,
        })
    ledger = {
        "ledger_schema_version": "1.0.0",
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": utc_now(),
        "expected_uses": 7,
        "actual_uses": len(entries),
        "unique_skills": len({entry["trace"]["skill_name"] for entry in entries}),
        "entries": entries,
    }
    atomic_json(run_root / "03_skill-traces" / "skill-call-ledger.json", ledger)


def record(args: argparse.Namespace) -> Path:
    run_root = args.run_root.resolve()
    contract = load_json(run_root / "00_contracts" / "run-contract.json")
    require(contract["run_id"] == RUN_ID and contract["task_id"] == TASK_ID, "contract identity mismatch")
    expected = contract_use(contract, args.use_id)

    skill_definition = args.skill_definition.resolve()
    require(skill_definition.is_file(), f"missing Skill definition: {skill_definition}")
    runtime_skill_definition = Path(args.runtime_skill_definition_path) if args.runtime_skill_definition_path else skill_definition
    definition_hash = sha256_file(skill_definition)
    require(definition_hash == expected["definition_sha256"], "Skill definition hash mismatch")

    input_path = resolve_reference(run_root, expected["input_reference"])
    require(input_path.is_file(), f"missing input: {input_path}")
    input_hash = sha256_file(input_path)

    output_path = resolve_reference(run_root, expected["output_reference"])
    runtime_source = args.runtime_fragment.resolve()
    require(runtime_source.is_file(), f"missing runtime evidence fragment: {runtime_source}")
    runtime_log_source = args.runtime_log_excerpt.resolve()
    require(runtime_log_source.is_file(), f"missing runtime log excerpt: {runtime_log_source}")
    fragment = load_json(runtime_source)

    for field in ("run_id", "task_id", "use_id", "agent_id", "skill_name"):
        expected_value = expected.get(field, contract.get(field))
        require(fragment.get(field) == expected_value, f"runtime fragment {field} mismatch")

    session_id = fragment.get("runtime_session_id")
    require(isinstance(session_id, str) and session_id, "runtime_session_id is required")
    probe = fragment.get("native_skill_probe", {})
    load_event = fragment.get("load_event", {})
    output_event = fragment.get("output_event", {})
    require(probe.get("available") in (True, False), "native Skill probe result missing")
    require(load_event.get("status") in ("success", "failed"), "invalid load event status")
    require(output_event.get("status") in ("success", "failed"), "invalid output event status")

    load_arguments = load_event.get("arguments", {})
    if probe["available"]:
        require(load_event.get("tool_name") == "Skill", "native Skill probe says available but load tool is not Skill")
        require(load_arguments.get("skill") == expected["skill_name"], "native Skill name mismatch")
        invocation_mode = "NATIVE_SKILL_TOOL"
        native_status = "NATIVE_SKILL_TOOL_USED"
        unavailable_reason = None
    else:
        evidence = probe.get("evidence")
        require(isinstance(evidence, str) and "NATIVE_SKILL_TOOL_UNAVAILABLE" in evidence,
                "unavailable probe must preserve NATIVE_SKILL_TOOL_UNAVAILABLE evidence")
        require(load_event.get("tool_name") == "read_file", "documented-only mode requires a real read_file load")
        require(same_path(load_arguments.get("file_path"), runtime_skill_definition), "read_file Skill path mismatch")
        invocation_mode = "DOCUMENTED_ONLY_LOAD_AND_APPLY"
        native_status = "NATIVE_SKILL_TOOL_UNAVAILABLE"
        unavailable_reason = evidence

    output_arguments = output_event.get("arguments", {})
    output_arg = output_arguments.get("file_path", output_arguments.get("output_reference"))
    runtime_output_path = Path(args.runtime_output_path) if args.runtime_output_path else output_path
    require(same_path(output_arg, runtime_output_path), "output tool reference mismatch")

    load_id = load_event.get("tool_call_id")
    load_id_reason = load_event.get("tool_call_id_unavailable_reason")
    if load_id is None:
        require(isinstance(load_id_reason, str) and load_id_reason, "null tool_call_id requires reason")
    else:
        require(isinstance(load_id, str) and load_id, "invalid runtime tool call id")
        require(load_id_reason is None, "tool call id reason must be null when an id exists")

    discovered_at = probe.get("checked_at")
    loaded_at = load_event.get("completed_at")
    invoked_at = loaded_at
    completed_at = output_event.get("completed_at")
    for value in (discovered_at, load_event.get("started_at"), loaded_at, output_event.get("started_at"), completed_at):
        require(isinstance(value, str), "runtime timestamps are required")
        parse_time(value)
    duration_ms = max(0, round((parse_time(completed_at) - parse_time(invoked_at)).total_seconds() * 1000))

    success = load_event["status"] == "success" and output_event["status"] == "success"
    if success:
        require(output_path.is_file(), f"missing successful output: {output_path}")
        output_reference: str | None = expected["output_reference"]
        output_hash: str | None = sha256_file(output_path)
        failure_reason = None
        status = "SUCCESS"
    else:
        require(args.failure_reason, "failed runtime evidence requires --failure-reason")
        output_reference = expected["output_reference"] if output_path.is_file() else None
        output_hash = sha256_file(output_path) if output_path.is_file() else None
        failure_reason = args.failure_reason
        status = "FAILED"

    trace_id = expected["trace_id"]
    snapshot_ref = f"02_runtime/skill-definitions/{expected['agent_id']}/{expected['skill_name']}/SKILL.md"
    snapshot_path = resolve_reference(run_root, snapshot_ref)
    copy_evidence(skill_definition, snapshot_path)

    runtime_ref = f"02_runtime/session-fragments/{trace_id}.json"
    runtime_path = resolve_reference(run_root, runtime_ref)
    copy_evidence(runtime_source, runtime_path)

    runtime_log_ref = f"02_runtime/log-excerpts/{trace_id}.log"
    runtime_log_path = resolve_reference(run_root, runtime_log_ref)
    copy_evidence(runtime_log_source, runtime_log_path)

    trace = {
        "trace_schema_version": "1.0.0",
        "trace_id": trace_id,
        "use_id": expected["use_id"],
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "agent_id": expected["agent_id"],
        "skill_name": expected["skill_name"],
        "skill_version": expected["skill_version"],
        "implementation_type": "DOCUMENTED_ONLY",
        "invocation_mode": invocation_mode,
        "native_skill_tool_status": native_status,
        "native_skill_tool_unavailable_reason": unavailable_reason,
        "discovered_at": discovered_at,
        "loaded_at": loaded_at,
        "invoked_at": invoked_at,
        "completed_at": completed_at,
        "skill_definition_path": str(runtime_skill_definition),
        "skill_definition_snapshot_reference": snapshot_ref,
        "skill_definition_sha256": definition_hash,
        "input_reference": expected["input_reference"],
        "input_sha256": input_hash,
        "output_reference": output_reference,
        "output_sha256": output_hash,
        "status": status,
        "duration_ms": duration_ms,
        "failure_reason": failure_reason,
        "downstream_consumer": expected["downstream_consumer"],
        "downstream_reference": expected["downstream_reference"],
        "downstream_effect": expected["downstream_effect"],
        "runtime_session_id": session_id,
        "runtime_tool_name": load_event["tool_name"],
        "runtime_tool_call_id": load_id,
        "runtime_tool_call_id_reason": load_id_reason,
        "runtime_evidence_reference": runtime_ref,
        "runtime_evidence_sha256": sha256_file(runtime_path),
        "runtime_log_excerpt_reference": runtime_log_ref,
        "runtime_log_excerpt_sha256": sha256_file(runtime_log_path),
        "recorded_at": utc_now(),
        "recorder_version": RECORDER_VERSION,
    }

    trace_path = run_root / "03_skill-traces" / f"{trace_id}.json"
    require(not trace_path.exists(), f"refusing to overwrite trace: {trace_path}")
    atomic_json(trace_path, trace)
    rebuild_ledger(run_root)
    return trace_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--use-id", required=True)
    parser.add_argument("--skill-definition", required=True, type=Path)
    parser.add_argument("--runtime-skill-definition-path")
    parser.add_argument("--runtime-output-path")
    parser.add_argument("--runtime-fragment", required=True, type=Path)
    parser.add_argument("--runtime-log-excerpt", required=True, type=Path)
    parser.add_argument("--failure-reason")
    args = parser.parse_args()
    try:
        path = record(args)
    except RecordError as error:
        print(f"SKILL_TRACE_RECORD_FAILED: {error}", file=sys.stderr)
        return 1
    print(f"SKILL_TRACE_RECORDED {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
