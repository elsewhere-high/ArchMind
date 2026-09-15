#!/usr/bin/env python3
"""Static, offline contract test for the minimum Skill evidence toolchain.

The generated events are synthetic and live only in a TemporaryDirectory.
They are deleted at exit and can never be used as runtime evidence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
REAL_RUN = REPO / "samples/skill-evidence"
SCRIPTS = REPO / "scripts"
EXPECTED_PASS = (
    "SKILL_EVIDENCE_VALID\n"
    "run=run-002-skill-evidence-min-001\n"
    "uses=7\n"
    "unique_skills=5\n"
    "trace_complete=7/7\n"
    "downstream_verified=7/7\n"
    "input_unchanged=true\n"
)
DEFINITIONS = {
    ("planting-reviewer", "extract-review-context"): REPO / "packages/planting-reviewer/skills/extract-review-context/SKILL.md",
    ("planting-reviewer", "professional-issue-format"): REPO / "packages/planting-reviewer/skills/professional-issue-format/SKILL.md",
    ("stormwater-sponge-reviewer", "extract-review-context"): REPO / "packages/stormwater-sponge-reviewer/skills/extract-review-context/SKILL.md",
    ("stormwater-sponge-reviewer", "professional-issue-format"): REPO / "packages/stormwater-sponge-reviewer/skills/professional-issue-format/SKILL.md",
    ("review-coordinator", "cross-discipline-conflict-check"): REPO / "packages/review-coordinator/skills/cross-discipline-conflict-check/SKILL.md",
    ("review-coordinator", "review-summary"): REPO / "packages/review-coordinator/skills/review-summary/SKILL.md",
    ("evidence-verifier", "evidence-verification"): REPO / "packages/evidence-verifier/skills/evidence-verification/SKILL.md",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(*args: str, cwd: Path = REPO, expect: int = 0) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if result.returncode != expect:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expect}: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def envelope(root: Path, reference: str, consumer: str, source_refs: list[str]) -> None:
    inputs = [{"reference": ref, "sha256": digest(root / ref)} for ref in source_refs]
    write_json(
        root / reference,
        {
            "run_id": "run-002-skill-evidence-min-001",
            "task_id": "task-20260902-skill-evidence-min-001",
            "consumer_use_id": consumer,
            "inputs": inputs,
            "static_test_only": True,
        },
    )


def make_output(root: Path, use: dict[str, object]) -> None:
    target = root / str(use["output_reference"])
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".md":
        target.write_text("# Synthetic static test summary\n\nNot runtime evidence.\n", encoding="utf-8")
    else:
        write_json(target, {"static_test_only": True, "use_id": use["use_id"], "records": []})


def make_fragment(root: Path, use: dict[str, object], definition: Path) -> Path:
    number = int(str(use["use_id"]).split("-")[1])
    start = f"2026-09-02T00:00:{number:02d}.000Z"
    loaded = f"2026-09-02T00:00:{number:02d}.010Z"
    completed = f"2026-09-02T00:00:{number:02d}.020Z"
    output_path = (root / str(use["output_reference"])).resolve()
    fragment = {
        "fragment_schema_version": "1.0.0",
        "run_id": "run-002-skill-evidence-min-001",
        "task_id": "task-20260902-skill-evidence-min-001",
        "use_id": use["use_id"],
        "agent_id": use["agent_id"],
        "skill_name": use["skill_name"],
        "runtime_session_id": f"ephemeral-static-contract-session-{number:02d}",
        "native_skill_probe": {
            "available": False,
            "checked_at": start,
            "evidence": "NATIVE_SKILL_TOOL_UNAVAILABLE — ephemeral static contract test only"
        },
        "load_event": {
            "tool_name": "read_file",
            "tool_call_id": None,
            "tool_call_id_unavailable_reason": "Ephemeral static contract test has no runtime tool-call ID.",
            "started_at": start,
            "completed_at": loaded,
            "status": "success",
            "arguments": {"file_path": str(definition.resolve())}
        },
        "output_event": {
            "tool_name": "write_file",
            "tool_call_id": None,
            "tool_call_id_unavailable_reason": "Ephemeral static contract test has no runtime tool-call ID.",
            "started_at": loaded,
            "completed_at": completed,
            "status": "success",
            "arguments": {"file_path": str(output_path)}
        },
        "extracted_from": "ephemeral static test; deleted on exit; not AgentTeams evidence"
    }
    path = root / f"static-fragment-{number:02d}.json"
    write_json(path, fragment)
    return path


def static_source_checks() -> None:
    for path in REAL_RUN.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    for path in (
        SCRIPTS / "record-skill-use-min-001.py",
        SCRIPTS / "finalize-skill-evidence-summary-min-001.py",
        SCRIPTS / "validate-skill-evidence-min-001.py",
        SCRIPTS / "build-skill-evidence-manifest-min-001.py",
        Path(__file__),
    ):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    run("bash", "-n", str(SCRIPTS / "check-run002-immutability.sh"))
    guard = run(str(SCRIPTS / "check-run002-immutability.sh"))
    assert "INPUT_IMMUTABILITY_GUARD_PASS" in guard.stdout

    expected_only = {
        "02_runtime/README.md",
        "03_skill-traces/README.md",
        "04_outputs/README.md",
        "05_downstream/README.md",
        "06_validation/README.md",
        "07_manifest/README.md",
    }
    actual = {
        path.relative_to(REAL_RUN).as_posix()
        for name in ("02_runtime", "03_skill-traces", "04_outputs", "05_downstream", "06_validation", "07_manifest")
        for path in (REAL_RUN / name).rglob("*")
        if path.is_file()
    }
    if actual != expected_only:
        raise AssertionError(f"preparation directory contains runtime-like evidence: {sorted(actual - expected_only)}")


def synthetic_pipeline_test() -> None:
    with tempfile.TemporaryDirectory(prefix="skill-evidence-contract-") as temp:
        root = Path(temp) / "run-002-skill-evidence-min-001"
        shutil.copytree(REAL_RUN / "00_contracts", root / "00_contracts")
        shutil.copytree(REAL_RUN / "01_input", root / "01_input")
        for name in ("02_runtime", "03_skill-traces", "04_outputs", "05_downstream", "06_validation", "07_manifest"):
            (root / name).mkdir(parents=True, exist_ok=True)

        contract = json.loads((root / "00_contracts/run-contract.json").read_text(encoding="utf-8"))
        uses = {item["use_id"]: item for item in contract["skill_uses"]}
        source_hashes: dict[str, str] = {}

        for use_id in [f"USE-{number:02d}" for number in range(1, 8)]:
            if use_id == "USE-02":
                envelope(root, "05_downstream/planting-professional-input.json", use_id, ["04_outputs/planting-review-context.json"])
            elif use_id == "USE-04":
                envelope(root, "05_downstream/stormwater-professional-input.json", use_id, ["04_outputs/stormwater-review-context.json"])
            elif use_id == "USE-05":
                envelope(root, "05_downstream/cross-discipline-input.json", use_id, ["04_outputs/planting-review.json", "04_outputs/stormwater-sponge-review.json"])
            elif use_id == "USE-06":
                envelope(root, "05_downstream/evidence-verification-input.json", use_id, ["04_outputs/cross-discipline-result.json", "04_outputs/planting-review.json", "04_outputs/stormwater-sponge-review.json"])
            elif use_id == "USE-07":
                envelope(root, "05_downstream/review-summary-input.json", use_id, ["04_outputs/evidence-verification.json"])

            use = uses[use_id]
            definition = DEFINITIONS[(str(use["agent_id"]), str(use["skill_name"]))]
            make_output(root, use)
            fragment = make_fragment(root, use, definition)
            runtime_log = root / f"static-runtime-{use_id}.log"
            runtime_log.write_text(
                f"EPHEMERAL_STATIC_TEST_ONLY run=run-002-skill-evidence-min-001 use={use_id}\n",
                encoding="utf-8",
            )
            result = run(
                sys.executable,
                "-B",
                str(SCRIPTS / "record-skill-use-min-001.py"),
                "--run-root",
                str(root),
                "--use-id",
                use_id,
                "--skill-definition",
                str(definition),
                "--runtime-fragment",
                str(fragment),
                "--runtime-log-excerpt",
                str(runtime_log),
            )
            assert "SKILL_TRACE_RECORDED" in result.stdout
            source_hashes[use_id] = digest(root / str(use["output_reference"]))

        run(sys.executable, "-B", str(SCRIPTS / "finalize-skill-evidence-summary-min-001.py"), "--run-root", str(root))
        validation = run(sys.executable, "-B", str(SCRIPTS / "validate-skill-evidence-min-001.py"), "--run-root", str(root))
        assert validation.stdout == EXPECTED_PASS
        (root / "06_validation/final-validator.txt").write_text(validation.stdout, encoding="utf-8")
        manifest = run(sys.executable, "-B", str(SCRIPTS / "build-skill-evidence-manifest-min-001.py"), "--run-root", str(root))
        assert "SKILL_EVIDENCE_MANIFEST_READY" in manifest.stdout
        tampered = root / str(uses["USE-01"]["output_reference"])
        tampered.write_text(tampered.read_text(encoding="utf-8") + "\n ", encoding="utf-8")
        rejected = run(sys.executable, "-B", str(SCRIPTS / "validate-skill-evidence-min-001.py"), "--run-root", str(root), expect=1)
        assert "output_sha256 mismatch" in rejected.stderr


def main() -> int:
    static_source_checks()
    synthetic_pipeline_test()
    print("SKILL_EVIDENCE_PREPARATION_STATIC_TEST_PASS")
    print("synthetic_fixture_persisted=false")
    print("docker_calls=0")
    print("model_calls=0")
    print("matrix_messages=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
