#!/usr/bin/env python3
"""Read-only consistency guard for Run-002 Human Gate artifacts.

This validator never creates a HumanDecision or changes task state. It only
rejects state artifacts that would bypass the real Human gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


FINAL_ITEM_STATES = {"accepted", "rejected"}
PROCESSED_ITEM_STATES = FINAL_ITEM_STATES | {"blocked_for_evidence", "rerun_required"}


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--human-items", type=Path)
    parser.add_argument("--decisions", type=Path)
    args = parser.parse_args()

    state = load(args.state)
    require(state["run_id"] == "run-002-human-gate", "unexpected run_id")
    require(isinstance(state.get("history"), list) and state["history"], "state history is empty")

    status = state["status"]
    declared_pending = state["unprocessed_human_required_items"]
    items = []
    if args.human_items:
        item_doc = load(args.human_items)
        items = item_doc["human_items"] if isinstance(item_doc, dict) else item_doc
        require(isinstance(items, list), "human_items must be an array")
        ids = [item["human_item_id"] for item in items]
        require(len(ids) == len(set(ids)), "human_item_id values are not unique")

    if status in {
        "WAITING_HUMAN",
        "RESUMED",
        "BLOCKED_FOR_EVIDENCE",
        "RERUN_REQUIRED",
        "REVIEW_REJECTED",
        "COMPLETED",
    }:
        require(args.human_items is not None, f"{status} requires --human-items")
        require(bool(items), f"{status} requires at least one Human Item")

    actual_pending = sum(
        1
        for item in items
        if item.get("requires_human_review") is True and item.get("status") == "pending_human"
    )
    require(actual_pending == declared_pending,
            f"pending count mismatch: state={declared_pending}, items={actual_pending}")

    decisions = []
    if args.decisions:
        decision_doc = load(args.decisions)
        decisions = decision_doc["decisions"] if isinstance(decision_doc, dict) else decision_doc
        require(isinstance(decisions, list), "decisions must be an array")
        decision_items = [decision["human_item_id"] for decision in decisions]
        require(len(decision_items) == len(set(decision_items)),
                "only one current decision per Human Item is allowed in this validator")
        for decision in decisions:
            require(decision["operator"] == "chief-engineer",
                    f"{decision['human_item_id']} was not decided by chief-engineer")
            require(bool(decision.get("source_room")),
                    f"{decision['human_item_id']} lacks source_room")

    decision_by_item = {decision["human_item_id"]: decision for decision in decisions}
    for item in items:
        item_status = item.get("status")
        if item_status in PROCESSED_ITEM_STATES:
            require(item["human_item_id"] in decision_by_item,
                    f"processed item {item['human_item_id']} lacks preserved HumanDecision")

    if status == "WAITING_HUMAN":
        require(actual_pending > 0, "WAITING_HUMAN requires pending Human Items")
        require(state["human_gate_closed"] is False, "WAITING_HUMAN cannot close Human gate")

    if status == "BLOCKED_FOR_EVIDENCE":
        require(any(item.get("status") == "blocked_for_evidence" for item in items),
                "BLOCKED_FOR_EVIDENCE lacks a blocked Human Item")

    if status == "RERUN_REQUIRED":
        require(any(item.get("status") == "rerun_required" for item in items),
                "RERUN_REQUIRED lacks a rerun Human Item")

    if status == "COMPLETED":
        require(actual_pending == 0, "COMPLETED has unprocessed Human Items")
        require(all(item.get("status") in FINAL_ITEM_STATES for item in items),
                "COMPLETED has blocked/rerun/non-terminal Human Item")
        require(state["human_gate_closed"] is True, "COMPLETED requires human_gate_closed=true")
        for field in ("completed_at", "completed_by", "final_summary_ref"):
            require(bool(state.get(field)), f"COMPLETED lacks {field}")

    print(
        f"RUN002_GATE_VALID status={status} items={len(items)} "
        f"pending={actual_pending} decisions={len(decisions)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"RUN002_GATE_INVALID: {error}", file=sys.stderr)
        raise SystemExit(1)
