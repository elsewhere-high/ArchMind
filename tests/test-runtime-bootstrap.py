#!/usr/bin/env python3
"""Offline regression tests for ArchMind runtime helpers."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render-deploy.py"
RESOURCE_CHECK = ROOT / "scripts" / "runtime-resource-check.py"
TEMPLATE = ROOT / "deploy" / "archmind-minimal.template.yaml"


class RuntimeBootstrapTests(unittest.TestCase):
    def run_renderer(self, environment: dict[str, str], *arguments: str):
        env = dict(os.environ)
        for name in (
            "PACKAGE_URI_BASE",
            "PACKAGE_URI_REVIEW_COORDINATOR",
            "PACKAGE_URI_HARDSCAPE_REVIEWER",
            "PACKAGE_URI_PLANTING_REVIEWER",
            "PACKAGE_URI_STORMWATER_SPONGE_REVIEWER",
            "PACKAGE_URI_EVIDENCE_VERIFIER",
        ):
            env.pop(name, None)
        env.update(environment)
        return subprocess.run(
            ["python3", str(RENDERER), "--template", str(TEMPLATE), *arguments],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_resource(self, payload: object, *arguments: str):
        return subprocess.run(
            ["python3", str(RESOURCE_CHECK), *arguments],
            cwd=ROOT,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_package_base_renders_all_placeholders(self):
        with tempfile.TemporaryDirectory(prefix="runtime-render-") as directory:
            output = Path(directory) / "rendered.yaml"
            result = self.run_renderer(
                {"PACKAGE_URI_BASE": "https://packages.example.com/archmind"},
                "--output",
                str(output),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = output.read_text(encoding="utf-8")
            self.assertNotIn("PACKAGE_URI_", text)
            self.assertEqual(text.count("package: https://"), 5)
            self.assertNotIn("packages.example.com", result.stdout)

    def test_missing_package_uri_fails(self):
        result = self.run_renderer({}, "--check-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing package URI configuration", result.stdout)

    def test_uri_with_embedded_credentials_fails(self):
        unsafe_uri = "https://" + "user" + ":" + "credential" + "@packages.example.com/files"
        result = self.run_renderer(
            {"PACKAGE_URI_BASE": unsafe_uri},
            "--check-only",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not embed credentials", result.stdout)
        self.assertNotIn("credential@", result.stdout)

    def test_ready_worker_and_package_reference(self):
        payload = {
            "metadata": {"name": "planting-reviewer"},
            "spec": {"package": "https://packages.example.com/planting-reviewer.zip"},
            "status": {"phase": "Running"},
        }
        result = self.run_resource(
            payload,
            "--name",
            "planting-reviewer",
            "--require-ready",
            "--expected-package",
            "https://packages.example.com/planting-reviewer.zip",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_readiness_is_not_pass(self):
        payload = {"metadata": {"name": "default"}, "status": {}}
        result = self.run_resource(payload, "--name", "default", "--require-ready")
        self.assertEqual(result.returncode, 3)
        self.assertIn("readiness unavailable", result.stdout)

    def test_team_membership(self):
        members = [
            "review-coordinator",
            "hardscape-reviewer",
            "planting-reviewer",
            "stormwater-sponge-reviewer",
            "evidence-verifier",
        ]
        payload = {
            "metadata": {"name": "archmind-review-team"},
            "spec": {"workerMembers": [{"name": name} for name in members]},
        }
        result = self.run_resource(
            payload,
            "--name",
            "archmind-review-team",
            "--members",
            *members,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
