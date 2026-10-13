#!/usr/bin/env python3
"""Inspect synthetic fixtures and exercise the existing gate guard offline."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def input_demo():
    facts = read("samples/case-001/drawing-facts.json")
    print("[合成样例] case-001 | 北入口树池与汇水节点")
    print(f"结构化事实: {len(facts['facts'])} 条 | 本轮无 CAD/BIM 解析")
    for fact in facts["facts"]:
        if fact["fact_id"] in {"H-002", "P-001", "P-002", "S-002"}:
            print(f"\n{fact['fact_id']} | {fact['drawing_reference']}")
            print(fact["statement"])
    print("\n事实保留编号、专业、图纸引用、位置与原始陈述。")


def review_demo():
    print("[预写回归数据] 展示字段与追溯链，本次不调用模型。")
    for name, label in [("hardscape", "园建"), ("planting", "植物"), ("stormwater-sponge", "雨水海绵")]:
        rows = read(f"tests/fixtures/review/worker-results/{name}-review.json")
        print(f"{label}: {len(rows)} 条专业意见")
    row = read("tests/fixtures/review/worker-results/planting-review.json")[0]
    print(f"\nissue_id: {row['issue_id']} | discipline: {row['discipline']}")
    print(f"drawing_reference: {', '.join(row['drawing_reference'])}")
    for evidence in row["evidence"]:
        print(f"fact_id: {evidence['fact_id']}")
        print(f"原始事实: {evidence['quoted_fact']}")
    print(f"risk_level: {row['risk_level']}")
    print(f"requires_human_review: {str(row['requires_human_review']).lower()}")
    print("\n编号化意见连接原始事实，并保留人工复核要求。")


def evidence_demo():
    report = read("tests/fixtures/review/evidence-verification.json")
    print("[预写回归数据] 跨专业核验与补充资料")
    print(f"跨专业核验记录: {len(report['cross_discipline_verifications'])} 条")
    for row in report["cross_discipline_verifications"][:2]:
        print(f"{row['cross_issue_id']}: {' + '.join(row['involved_issue_ids_verified'])}")
    row = read("tests/fixtures/review/worker-results/stormwater-sponge-review.json")[0]
    print(f"\n{row['issue_id']} | status: {row['status']}")
    print("缺失资料（节选）:")
    for item in row["missing_information"][:3]:
        print(f"  - {item}")
    print(f"\n待人工确认: {len(report['human_confirmation_items'])} 项")
    print("HCI-003 关联: " + " + ".join(report["human_confirmation_items"][2]["related_issues"]))
    print("核验追溯引用；证据不足仍须补充资料与人工处置。")


def gate_demo():
    print("[合成状态测试] 调用项目现有人工确认校验器")
    print("只写临时测试文件；不创建人工决定或真实审批。")
    with tempfile.TemporaryDirectory(prefix="archmind-os2026-gate-") as directory:
        target = Path(directory)
        items = [{"human_item_id": "HCI-001", "status": "pending_human", "requires_human_review": True}]
        state = {"run_id": "run-002-human-gate", "status": "WAITING_HUMAN", "history": [{"from": "EVIDENCE_VERIFYING", "to": "WAITING_HUMAN"}], "unprocessed_human_required_items": 1, "human_gate_closed": False}
        (target / "items.json").write_text(json.dumps(items), encoding="utf-8")
        (target / "decisions.json").write_text("[]", encoding="utf-8")
        command = [sys.executable, "-B", "scripts/validate-run002-gate.py", "--state", str(target / "state.json"), "--human-items", str(target / "items.json"), "--decisions", str(target / "decisions.json")]
        for status, expected in [("WAITING_HUMAN", 0), ("COMPLETED", 1)]:
            state["status"] = status
            state["human_gate_closed"] = status == "COMPLETED"
            state["history"] = [{"from": "EVIDENCE_VERIFYING", "to": status}]
            (target / "state.json").write_text(json.dumps(state), encoding="utf-8")
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            print(f"\n校验 {status} | exit={result.returncode}")
            print((result.stdout + result.stderr).strip())
            if result.returncode != expected:
                raise SystemExit("Unexpected gate result")
    print("\nGUARD_DEMO_PASS: 有待确认事项时，提前完成被拒绝。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["input", "review", "evidence", "gate"])
    args = parser.parse_args()
    if not os.environ.get("CONDA_PREFIX"):
        parser.error("Activate the archmind Conda environment first")
    {"input": input_demo, "review": review_demo, "evidence": evidence_demo, "gate": gate_demo}[args.stage]()


if __name__ == "__main__":
    main()
