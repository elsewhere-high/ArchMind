#!/usr/bin/env python3
"""Strict validator for seven complete Skill-use traces and their downstream chain.

This validator requires actual complete traces; sample preparation alone cannot pass.
It must remain non-zero until the full strong-evidence contract is genuinely satisfied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


RUN_ID = "run-002-skill-evidence-min-001"
TASK_ID = "task-20260902-skill-evidence-min-001"
EXPECTED_SKILLS = {
    "extract-review-context",
    "professional-issue-format",
    "cross-discipline-conflict-check",
    "evidence-verification",
    "review-summary",
}
REQUIRED_TRACE_FIELDS = {
    "trace_id", "use_id", "run_id", "task_id", "agent_id", "skill_name", "skill_version",
    "implementation_type", "invocation_mode", "discovered_at", "loaded_at", "invoked_at",
    "completed_at", "skill_definition_path", "skill_definition_snapshot_reference",
    "skill_definition_sha256", "input_reference", "input_sha256", "output_reference",
    "output_sha256", "status", "duration_ms", "failure_reason", "downstream_consumer",
    "downstream_reference", "downstream_effect", "runtime_session_id", "runtime_tool_name",
    "runtime_tool_call_id", "runtime_tool_call_id_reason", "runtime_evidence_reference",
    "runtime_evidence_sha256", "native_skill_tool_status",
    "runtime_log_excerpt_reference", "runtime_log_excerpt_sha256",
    "native_skill_tool_unavailable_reason", "recorded_at", "recorder_version",
}
PLACEHOLDER_ID = re.compile(r"(?:fake|placeholder|example|todo|invented)", re.I)
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "samples" / "skill-evidence"
REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolved(root: Path, ref: str) -> Path:
    path = (root / ref).resolve()
    if path != root.resolve() and root.resolve() not in path.parents:
        raise ValueError(f"reference escapes run root: {ref}")
    return path


def validate_run(root: Path, check_guard: bool = True) -> list[str]:
    errors: list[str] = []
    contract_path = root / "00_contracts/run-contract.json"
    if not contract_path.is_file():
        return ["missing run contract"]
    contract = read_json(contract_path)
    if contract.get("run_id") != RUN_ID or contract.get("task_id") != TASK_ID:
        errors.append("run/task identity mismatch")
    expected_uses = {item["use_id"]: item for item in contract.get("skill_uses", [])}
    if len(expected_uses) != 7:
        errors.append("contract does not define seven unique uses")

    traces: dict[str, dict[str, Any]] = {}
    trace_files = sorted((root / "03_skill-traces").glob("TRACE-SEMIN001-0[1-7].json"))
    if len(trace_files) != 7:
        errors.append(f"expected 7 trace files, found {len(trace_files)}")
    runtime_ids: set[str] = set()
    for trace_file in trace_files:
        try:
            trace = read_json(trace_file)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid trace {trace_file.name}: {exc}")
            continue
        missing = sorted(REQUIRED_TRACE_FIELDS - set(trace))
        if missing:
            errors.append(f"{trace_file.name} missing fields: {','.join(missing)}")
            continue
        use_id = trace["use_id"]
        expected = expected_uses.get(use_id)
        if not expected:
            errors.append(f"unexpected use_id {use_id}")
            continue
        traces[use_id] = trace
        for key in ("trace_id", "agent_id", "skill_name", "skill_version", "input_reference", "output_reference", "downstream_consumer", "downstream_reference", "downstream_effect"):
            if trace.get(key) != expected.get(key):
                errors.append(f"{use_id} {key} mismatch")
        if trace.get("run_id") != RUN_ID or trace.get("task_id") != TASK_ID:
            errors.append(f"{use_id} identity mismatch")
        if trace.get("implementation_type") != "DOCUMENTED_ONLY":
            errors.append(f"{use_id} mislabels implementation type")
        if trace.get("status") != "SUCCESS" or trace.get("failure_reason") is not None:
            errors.append(f"{use_id} is not a successful trace")
        if not isinstance(trace.get("duration_ms"), int) or trace["duration_ms"] < 0:
            errors.append(f"{use_id} invalid duration_ms")

        for ref_key, hash_key in (
            ("skill_definition_snapshot_reference", "skill_definition_sha256"),
            ("input_reference", "input_sha256"),
            ("output_reference", "output_sha256"),
            ("runtime_evidence_reference", "runtime_evidence_sha256"),
            ("runtime_log_excerpt_reference", "runtime_log_excerpt_sha256"),
        ):
            ref = trace.get(ref_key)
            if not isinstance(ref, str):
                errors.append(f"{use_id} missing {ref_key}")
                continue
            try:
                path = resolved(root, ref)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not path.is_file():
                errors.append(f"{use_id} missing file {ref}")
            elif sha256(path) != trace.get(hash_key):
                errors.append(f"{use_id} {hash_key} mismatch")
        if trace.get("skill_definition_sha256") != expected.get("definition_sha256"):
            errors.append(f"{use_id} unexpected Skill definition hash")

        call_id = trace.get("runtime_tool_call_id")
        if call_id is None:
            if not trace.get("runtime_tool_call_id_reason"):
                errors.append(f"{use_id} null runtime_tool_call_id without reason")
        else:
            if not isinstance(call_id, str) or not call_id or PLACEHOLDER_ID.search(call_id):
                errors.append(f"{use_id} invalid or placeholder runtime_tool_call_id")
            elif call_id in runtime_ids:
                errors.append(f"duplicate runtime_tool_call_id {call_id}")
            runtime_ids.add(call_id)

        try:
            fragment = read_json(resolved(root, trace["runtime_evidence_reference"]))
            load = fragment["load_event"]
            if fragment.get("runtime_session_id") != trace.get("runtime_session_id"):
                errors.append(f"{use_id} runtime session mismatch")
            if load.get("tool_call_id") != call_id:
                errors.append(f"{use_id} runtime tool call mismatch")
            if load.get("tool_name") != trace.get("runtime_tool_name"):
                errors.append(f"{use_id} runtime tool name mismatch")
            if trace.get("invocation_mode") == "DOCUMENTED_ONLY_LOAD_AND_APPLY":
                if load.get("tool_name") != "read_file" or fragment.get("native_skill_probe", {}).get("available") is not False:
                    errors.append(f"{use_id} lacks documented-only read_file proof")
                if "NATIVE_SKILL_TOOL_UNAVAILABLE" not in str(fragment.get("native_skill_probe", {}).get("evidence")):
                    errors.append(f"{use_id} lacks native-tool-unavailable evidence")
            elif trace.get("invocation_mode") == "NATIVE_SKILL_TOOL":
                if load.get("tool_name") != "Skill" or fragment.get("native_skill_probe", {}).get("available") is not True:
                    errors.append(f"{use_id} lacks native Skill tool proof")
            else:
                errors.append(f"{use_id} invalid invocation mode")
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{use_id} invalid runtime fragment: {exc}")

    if set(traces) != set(expected_uses):
        errors.append("trace use IDs do not match contract")
    if {trace["skill_name"] for trace in traces.values()} != EXPECTED_SKILLS:
        errors.append("unique skills are not 5/5")
    if any(trace.get("agent_id") == "hardscape-reviewer" for trace in traces.values()):
        errors.append("hardscape-reviewer must not participate")

    ledger_path = root / "03_skill-traces/skill-call-ledger.json"
    if not ledger_path.is_file():
        errors.append("missing aggregate ledger")
    else:
        ledger = read_json(ledger_path)
        entries = ledger.get("entries", [])
        if ledger.get("actual_uses") != 7 or ledger.get("unique_skills") != 5 or len(entries) != 7:
            errors.append("ledger counts mismatch")
        for entry in entries:
            try:
                path = resolved(root, entry["trace_file"])
                if sha256(path) != entry["trace_file_sha256"]:
                    errors.append(f"ledger trace hash mismatch: {entry['trace_file']}")
                if read_json(path) != entry["trace"]:
                    errors.append(f"ledger trace content mismatch: {entry['trace_file']}")
            except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"invalid ledger entry: {exc}")

    verified_edges = 0
    for edge in contract.get("downstream_edges", []):
        source = traces.get(edge["source_use"])
        if not source:
            continue
        envelope_path = resolved(root, edge["input_envelope"])
        if not envelope_path.is_file():
            errors.append(f"{edge['edge_id']} missing downstream envelope")
            continue
        envelope = read_json(envelope_path)
        if edge["consumer_use"] is None:
            if (envelope.get("source_review_summary_reference") == source["output_reference"] and
                    envelope.get("source_review_summary_sha256") == source["output_sha256"]):
                verified_edges += 1
            else:
                errors.append(f"{edge['edge_id']} final summary does not consume USE-07 output")
            continue
        consumer = traces.get(edge["consumer_use"])
        inputs = envelope.get("inputs", []) if isinstance(envelope, dict) else []
        has_source = any(item.get("reference") == source["output_reference"] and item.get("sha256") == source["output_sha256"] for item in inputs if isinstance(item, dict))
        if not has_source:
            errors.append(f"{edge['edge_id']} missing source output hash in downstream envelope")
            continue
        if not consumer or consumer.get("input_reference") != edge["input_envelope"] or consumer.get("input_sha256") != sha256(envelope_path):
            errors.append(f"{edge['edge_id']} consumer trace does not match downstream envelope")
            continue
        verified_edges += 1
    if verified_edges != 7:
        errors.append(f"downstream verification incomplete: {verified_edges}/7")

    if check_guard:
        guard = subprocess.run(
            [str(REPO_ROOT / "scripts/check-run002-immutability.sh")],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if guard.returncode != 0 or "INPUT_IMMUTABILITY_GUARD_PASS" not in guard.stdout:
            errors.append("sample input immutability guard failed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        errors = validate_run(args.run_root.resolve())
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        errors = [f"validator exception: {exc}"]
    if errors:
        print("SKILL_EVIDENCE_STRONG_NOT_ACHIEVED", file=sys.stderr)
        print("completion_status=PARTIAL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("SKILL_EVIDENCE_VALID")
    print(f"run={RUN_ID}")
    print("uses=7")
    print("unique_skills=5")
    print("trace_complete=7/7")
    print("downstream_verified=7/7")
    print("input_unchanged=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
