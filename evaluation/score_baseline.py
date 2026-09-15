#!/usr/bin/env python3
"""Score synthetic review fixtures without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation/dataset/eval-set-v0.1.jsonl"
RESULT = ROOT / "evaluation/baseline/result.json"
REPORT = ROOT / "evaluation/baseline/report.md"

ISSUE_SCHEMA = "docs/issue-schema.json"
DECISION_SCHEMA = "schemas/human-decision-v0.2.schema.json"
RUN1_VERIFICATION = "tests/fixtures/review/evidence-verification.json"


def load_json(relative_path: str) -> Any:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hash(relative_path: str) -> str:
    return sha256_file(ROOT / relative_path)


def issue_requirements() -> dict[str, Any]:
    schema = load_json(ISSUE_SCHEMA)
    return {
        "record_type": "professional_issue",
        "schema_path": ISSUE_SCHEMA,
        "required_fields": schema["required"],
        "evidence_reference_check": "issue_evidence_array",
        "insufficient_evidence_check": "professional_issue",
        "human_gate_readiness_check": None,
    }


def confirmation_requirements() -> dict[str, Any]:
    return {
        "record_type": "human_confirmation_item",
        "schema_path": None,
        "schema_scope_note": "No existing project JSON Schema covers this Run-001 verifier record.",
        "required_fields": [
            "item_id",
            "related_issues",
            "description",
            "requires_design_intent_confirmation",
        ],
        "evidence_reference_check": "related_issues",
        "insufficient_evidence_check": None,
        "human_gate_readiness_check": "run001_confirmation_item",
    }


def decision_requirements() -> dict[str, Any]:
    schema = load_json(DECISION_SCHEMA)
    return {
        "record_type": "human_decision",
        "schema_path": DECISION_SCHEMA,
        "required_fields": schema["required"],
        "evidence_reference_check": "decision_references",
        "insufficient_evidence_check": "human_decision",
        "human_gate_readiness_check": "human_decision",
    }


def gate_state_requirements() -> dict[str, Any]:
    return {
        "record_type": "human_gate_state_snapshot",
        "schema_path": None,
        "schema_scope_note": (
            "This Final Freeze snapshot is not the run-state-v0.1 payload and is not scored "
            "against that schema."
        ),
        "required_fields": [
            "run_id",
            "task_id",
            "status",
            "human_gate_closed",
            "human_items",
            "pending",
            "processed",
            "decisions",
            "canonical_human_items",
            "run_state",
            "validator",
        ],
        "evidence_reference_check": "final_gate_references",
        "insufficient_evidence_check": None,
        "human_gate_readiness_check": "final_gate_state",
    }


def make_case(
    case_id: str,
    source_run: str,
    source_artifact: str,
    selector: dict[str, Any],
    actual_record: Any,
    requirements: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "source_run": source_run,
        "source_artifact": source_artifact,
        "source_sha256": source_hash(source_artifact),
        "source_selector": selector,
        "actual_record": actual_record,
        "evaluation_requirements": requirements,
    }


def build_dataset() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    worker_files = [
        "tests/fixtures/review/worker-results/hardscape-review.json",
        "tests/fixtures/review/worker-results/planting-review.json",
        "tests/fixtures/review/worker-results/stormwater-sponge-review.json",
    ]
    for artifact in worker_files:
        records = load_json(artifact)
        for index, record in enumerate(records):
            cases.append(
                make_case(
                    f"sample-issue-{record['issue_id']}",
                    "synthetic-review",
                    artifact,
                    {"kind": "array_index", "index": index},
                    record,
                    issue_requirements(),
                )
            )

    verification = load_json(RUN1_VERIFICATION)
    for index, record in enumerate(verification["human_confirmation_items"]):
        cases.append(
            make_case(
                f"sample-human-{record['item_id']}",
                "synthetic-review",
                RUN1_VERIFICATION,
                {
                    "kind": "object_array_index",
                    "key": "human_confirmation_items",
                    "index": index,
                },
                record,
                confirmation_requirements(),
            )
        )

    DATASET.parent.mkdir(parents=True, exist_ok=True)
    with DATASET.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    return cases


def json_type_matches(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return True


def schema_errors(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        accepted = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(json_type_matches(instance, item) for item in accepted):
            return [f"{path}: expected type {accepted}"]

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: value does not equal const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value is not in enum")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: does not match pattern")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}: invalid date-time")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above maximum")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than minItems")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in instance]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]"))

    if isinstance(instance, dict):
        for field in schema.get("required", []):
            if field not in instance:
                errors.append(f"{path}: missing required field {field}")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                errors.extend(schema_errors(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: additional property {key}")

    for condition in schema.get("allOf", []):
        if_schema = condition.get("if")
        then_schema = condition.get("then")
        if if_schema is not None and then_schema is not None:
            if not schema_errors(instance, if_schema, path):
                errors.extend(schema_errors(instance, then_schema, path))
    return errors


def select_source_record(document: Any, selector: dict[str, Any]) -> Any:
    kind = selector["kind"]
    if kind == "whole_document":
        return document
    if kind == "array_index":
        return document[selector["index"]]
    if kind == "object_array_index":
        return document[selector["key"]][selector["index"]]
    raise ValueError(f"unsupported source selector: {kind}")


def get_field(record: dict[str, Any], dotted: str) -> tuple[bool, Any]:
    value: Any = record
    for component in dotted.split("."):
        if not isinstance(value, dict) or component not in value:
            return False, None
        value = value[component]
    return True, value


def complete_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def evidence_complete(record: dict[str, Any], mode: str | None) -> bool | None:
    if mode is None:
        return None
    if mode == "issue_evidence_array":
        items = record.get("evidence")
        return bool(items) and all(
            isinstance(item, dict)
            and all(isinstance(item.get(key), str) and item[key].strip() for key in ("source", "fact_id", "quoted_fact"))
            for item in items
        )
    if mode == "related_issues":
        refs = record.get("related_issues")
        return isinstance(refs, list) and bool(refs) and all(isinstance(item, str) and item for item in refs)
    if mode == "decision_references":
        evidence = record.get("related_evidence_ids")
        issues = record.get("related_issue_ids")
        relations = record.get("related_relation_ids")
        return (
            isinstance(evidence, list)
            and bool(evidence)
            and all(isinstance(item, str) and item for item in evidence)
            and isinstance(issues, list)
            and isinstance(relations, list)
            and bool(issues or relations)
        )
    if mode == "final_gate_references":
        hash_pattern = re.compile(r"^[0-9a-f]{64}$")
        canonical = record.get("canonical_human_items", {})
        run_state = record.get("run_state", {})
        validator = record.get("validator", {})
        return all(
            [
                isinstance(canonical.get("path"), str) and bool(canonical["path"]),
                bool(hash_pattern.fullmatch(str(canonical.get("sha256", "")))),
                isinstance(run_state.get("path"), str) and bool(run_state["path"]),
                bool(hash_pattern.fullmatch(str(run_state.get("sha256", "")))),
                validator.get("result") == "PASS",
                isinstance(validator.get("raw_output"), str) and bool(validator["raw_output"]),
            ]
        )
    raise ValueError(f"unsupported evidence check: {mode}")


def explainability(record: dict[str, Any], mode: str | None) -> bool | None:
    if mode == "professional_issue" and record.get("status") == "insufficient_evidence":
        missing = record.get("missing_information")
        return (
            isinstance(missing, list)
            and bool(missing)
            and all(isinstance(item, str) and item.strip() for item in missing)
            and bool(str(record.get("rule_or_reason", "")).strip())
            and bool(str(record.get("recommendation", "")).strip())
        )
    if mode == "human_decision" and record.get("decision") == "REQUEST_MORE_EVIDENCE":
        missing = record.get("missing_information")
        return (
            isinstance(missing, list)
            and bool(missing)
            and all(isinstance(item, str) and item.strip() for item in missing)
            and bool(str(record.get("reason", "")).strip())
            and record.get("new_status") == "blocked_for_evidence"
        )
    return None


def human_gate_ready(record: dict[str, Any], mode: str | None) -> bool | None:
    if mode is None:
        return None
    if mode == "run001_confirmation_item":
        return (
            bool(str(record.get("item_id", "")).strip())
            and isinstance(record.get("related_issues"), list)
            and bool(record["related_issues"])
            and bool(str(record.get("description", "")).strip())
            and record.get("requires_design_intent_confirmation") is True
        )
    if mode == "human_decision":
        mapping = {
            "ACCEPT": "accepted",
            "REJECT": "rejected",
            "REQUEST_MORE_EVIDENCE": "blocked_for_evidence",
            "RERUN": "rerun_required",
        }
        return (
            record.get("previous_status") == "pending_human"
            and mapping.get(record.get("decision")) == record.get("new_status")
            and bool(str(record.get("operator", "")).strip())
            and bool(str(record.get("timestamp", "")).strip())
            and bool(str(record.get("source_room", "")).strip())
            and bool(str(record.get("message_event_id", "")).strip())
        )
    if mode == "final_gate_state":
        return (
            record.get("status") == "WAITING_HUMAN"
            and record.get("human_gate_closed") is False
            and record.get("human_items") == record.get("pending", 0) + record.get("processed", 0)
            and record.get("processed") == record.get("decisions")
            and record.get("validator", {}).get("result") == "PASS"
        )
    raise ValueError(f"unsupported human gate check: {mode}")


def metric(numerator: int, denominator: int, formula: str) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "formula": formula,
        "score": round(numerator / denominator, 6) if denominator else None,
    }


def score(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    required_num = required_den = 0
    evidence_num = evidence_den = 0
    explain_num = explain_den = 0
    gate_num = gate_den = 0
    schema_num = schema_den = 0
    artifact_hash_num = record_match_num = 0
    schema_failures: list[dict[str, Any]] = []

    for case in cases:
        artifact = ROOT / case["source_artifact"]
        artifact_hash_ok = artifact.is_file() and sha256_file(artifact) == case["source_sha256"]
        artifact_hash_num += int(artifact_hash_ok)
        record_match = False
        if artifact_hash_ok:
            document = json.loads(artifact.read_text(encoding="utf-8"))
            record_match = select_source_record(document, case["source_selector"]) == case["actual_record"]
        record_match_num += int(record_match)

        record = case["actual_record"]
        requirements = case["evaluation_requirements"]
        missing_required: list[str] = []
        for field in requirements["required_fields"]:
            required_den += 1
            exists, value = get_field(record, field)
            if exists and complete_value(value):
                required_num += 1
            else:
                missing_required.append(field)

        evidence_ok = evidence_complete(record, requirements.get("evidence_reference_check"))
        if evidence_ok is not None:
            evidence_den += 1
            evidence_num += int(evidence_ok)

        explain_ok = explainability(record, requirements.get("insufficient_evidence_check"))
        if explain_ok is not None:
            explain_den += 1
            explain_num += int(explain_ok)

        gate_ok = human_gate_ready(record, requirements.get("human_gate_readiness_check"))
        if gate_ok is not None:
            gate_den += 1
            gate_num += int(gate_ok)

        schema_path = requirements.get("schema_path")
        errors: list[str] = []
        schema_ok: bool | None = None
        if schema_path:
            schema_den += 1
            errors = schema_errors(record, load_json(schema_path))
            schema_ok = not errors
            schema_num += int(schema_ok)
            if errors:
                schema_failures.append({"case_id": case["case_id"], "errors": errors})

        details.append(
            {
                "case_id": case["case_id"],
                "record_type": requirements["record_type"],
                "source_artifact_sha256_match": artifact_hash_ok,
                "actual_record_matches_source": record_match,
                "missing_required_fields": missing_required,
                "evidence_references_complete": evidence_ok,
                "insufficient_evidence_explainable": explain_ok,
                "human_gate_ready": gate_ok,
                "schema_valid": schema_ok,
                "schema_errors": errors,
            }
        )

    metrics = {
        "required_field_completeness": metric(
            required_num,
            required_den,
            "populated required field slots / all required field slots",
        ),
        "evidence_reference_completeness": metric(
            evidence_num,
            evidence_den,
            "cases passing their declared evidence-reference check / applicable cases",
        ),
        "insufficient_evidence_explainability": metric(
            explain_num,
            explain_den,
            "insufficient-evidence records with explicit rationale and missing information / applicable insufficient-evidence records",
        ),
        "human_gate_readiness": metric(
            gate_num,
            gate_den,
            "records passing their type-specific Human Gate readiness check / applicable Human Gate records",
        ),
        "schema_validity": metric(
            schema_num,
            schema_den,
            "records valid against an existing applicable project JSON Schema / schema-covered records",
        ),
    }
    integrity = {
        "source_artifact_sha256": metric(
            artifact_hash_num,
            len(cases),
            "cases whose declared source SHA-256 matches the current frozen source artifact / dataset cases",
        ),
        "actual_record_match": metric(
            record_match_num,
            len(cases),
            "actual_record values exactly matching their source selector / dataset cases",
        ),
    }

    findings: list[dict[str, Any]] = []
    if artifact_hash_num != len(cases) or record_match_num != len(cases):
        findings.append(
            {
                "finding_id": "G04A-DATASET-INTEGRITY",
                "summary": "Dataset provenance does not match one or more frozen source artifacts.",
            }
        )
    if schema_failures:
        findings.append(
            {
                "finding_id": "G04A-SCHEMA-001",
                "affected_cases": [item["case_id"] for item in schema_failures],
                "summary": (
                    "One or more records do not conform to their declared JSON Schema. "
                    "See case_results for the actual field errors."
                ),
                "constraint": "Preserve input records; correct the producer or the declared data contract before reevaluation.",
            }
        )

    integrity_ok = artifact_hash_num == len(cases) and record_match_num == len(cases)
    if not integrity_ok:
        status = "INVALID_DATASET"
    elif findings:
        status = "COMPLETED_WITH_FINDINGS"
    else:
        status = "COMPLETED"
    return {
        "evaluation_id": "archmind-evaluation-v0.1",
        "baseline_status": status,
        "dataset": {
            "path": str(DATASET.relative_to(ROOT)),
            "cases": len(cases),
            "sha256": sha256_file(DATASET),
            "source_runs": sorted({case["source_run"] for case in cases}),
        },
        "integrity": integrity,
        "metrics": metrics,
        "classification_metrics_not_used": ["accuracy", "precision", "recall", "F1"],
        "classification_metrics_reason": "No Golden Labels exist for this baseline.",
        "actionable_findings": findings,
        "case_results": details,
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# ArchMind Synthetic Review Evaluation",
        "",
        "This evaluation uses synthetic review fixtures. It performs no model call,",
        "business replay, HumanDecision mutation or Skill change.",
        "",
        "## Dataset",
        "",
        f"- Cases: `{result['dataset']['cases']}`",
        f"- SHA-256: `{result['dataset']['sha256']}`",
        f"- Source runs: `{', '.join(result['dataset']['source_runs'])}`",
        f"- Status: `{result['baseline_status']}`",
        "",
        "All source artifact hashes and `actual_record` selectors are verified before scoring.",
        "",
        "## Metrics",
        "",
        "| Metric | Numerator | Denominator | Score | Formula |",
        "|---|---:|---:|---:|---|",
    ]
    for name, value in result["metrics"].items():
        score_text = "N/A" if value["score"] is None else f"{value['score']:.2%}"
        lines.append(
            f"| `{name}` | {value['numerator']} | {value['denominator']} | "
            f"{score_text} | {value['formula']} |"
        )
    lines.extend(
        [
            "",
            "Schema validity is scored only for records covered by an existing project JSON Schema:",
            "the bundled professional issues have schema coverage; human confirmation items do not.",
            "Records without schema coverage are excluded from that metric.",
            "",
            "No Golden Labels exist, so accuracy, precision, recall and F1 are not calculated.",
            "",
            "## Actionable findings",
            "",
        ]
    )
    if not result["actionable_findings"]:
        lines.append("NONE")
    else:
        for finding in result["actionable_findings"]:
            lines.append(f"- **{finding['finding_id']}** — {finding['summary']}")
            if finding.get("affected_cases"):
                lines.append(f"  Affected cases: `{', '.join(finding['affected_cases'])}`.")
            if finding.get("constraint"):
                lines.append(f"  Boundary: {finding['constraint']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This report is a baseline measurement, not an improvement claim. Frozen evidence is not",
            "rewritten to resolve findings, and no before/after comparison is made.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dataset", action="store_true")
    args = parser.parse_args()
    if args.build_dataset or not DATASET.is_file():
        cases = build_dataset()
    else:
        cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]
    result = score(cases)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(render_report(result), encoding="utf-8")
    print(f"DATASET_CASES={result['dataset']['cases']}")
    print(f"DATASET_SHA256={result['dataset']['sha256']}")
    print(f"BASELINE_STATUS={result['baseline_status']}")
    for name, value in result["metrics"].items():
        print(f"{name}={value['numerator']}/{value['denominator']} score={value['score']}")
    print(f"ACTIONABLE_FINDINGS={len(result['actionable_findings'])}")
    return 0 if result["baseline_status"] != "INVALID_DATASET" else 1


if __name__ == "__main__":
    raise SystemExit(main())
