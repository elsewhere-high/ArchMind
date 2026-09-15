#!/usr/bin/env python3
"""Offline regressions for human authorization and source/export boundaries."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HumanGateTests(unittest.TestCase):
    def gate(self, status="WAITING_HUMAN", item_status="pending_human", decisions=None):
        with tempfile.TemporaryDirectory(prefix="archmind-gate-") as directory:
            target = Path(directory)
            state = {
                "run_id": "run-002-human-gate", "status": status,
                "history": [{"from": "EVIDENCE_VERIFYING", "to": status}],
                "unprocessed_human_required_items": int(item_status == "pending_human"),
                "human_gate_closed": status == "COMPLETED",
                "completed_at": "2026-01-01T00:00:00Z",
                "completed_by": "chief-engineer", "final_summary_ref": "summary.md",
            }
            items = [{"human_item_id": "HCI-001", "status": item_status, "requires_human_review": True}]
            for name, value in [("state", state), ("items", items), ("decisions", decisions or [])]:
                (target / (name + ".json")).write_text(json.dumps(value))
            return subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts/validate-run002-gate.py"),
                 "--state", str(target / "state.json"), "--human-items", str(target / "items.json"),
                 "--decisions", str(target / "decisions.json")], capture_output=True, text=True,
            )

    def test_waiting_keeps_pending_items(self):
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pending=1", result.stdout)

    def test_pending_items_cannot_complete(self):
        self.assertNotEqual(self.gate(status="COMPLETED").returncode, 0)

    def test_processed_item_needs_human_decision(self):
        self.assertNotEqual(self.gate(status="COMPLETED", item_status="accepted").returncode, 0)

    def test_agent_cannot_replace_human(self):
        decisions = [{"human_item_id": "HCI-001", "operator": "review-coordinator", "source_room": "synthetic-room"}]
        self.assertNotEqual(self.gate("COMPLETED", "accepted", decisions).returncode, 0)

    def test_blocked_evidence_cannot_complete(self):
        decisions = [{"human_item_id": "HCI-001", "operator": "chief-engineer", "source_room": "synthetic-room"}]
        self.assertNotEqual(self.gate("COMPLETED", "blocked_for_evidence", decisions).returncode, 0)

    def test_input_guard_rejects_tampering(self):
        with tempfile.TemporaryDirectory(prefix="archmind-integrity-") as directory:
            target = Path(directory)
            script = target / "scripts/check-run002-immutability.sh"
            script.parent.mkdir()
            shutil.copy2(ROOT / "scripts/check-run002-immutability.sh", script)
            inputs = "samples/skill-evidence/01_input/source"
            shutil.copytree(ROOT / inputs, target / inputs)
            result = subprocess.run(["bash", str(script)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (target / inputs / "drawing-facts.json").open("a") as handle:
                handle.write("\n ")
            result = subprocess.run(["bash", str(script)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_export_rejects_git_and_workspace_rejects_nested_git(self):
        scanner = ROOT / "tests/validate-final-secret-scan.py"
        with tempfile.TemporaryDirectory(prefix="archmind-export-") as directory:
            target = Path(directory)
            (target / ".git").mkdir()
            args = [sys.executable, "-B", str(scanner), "--root", str(target)]
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(args + ["--workspace"], capture_output=True).returncode, 0)
            (target / "nested/.git").mkdir(parents=True)
            self.assertNotEqual(subprocess.run(args + ["--workspace"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
