#!/usr/bin/env python3
"""Regression tests for the precise public-safety allowlists."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "tests/validate-public-safety.py"


class PublicSafetyRegressionTests(unittest.TestCase):
    def scan(self, relative_path: str, content: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="public-safety-regression-") as temporary:
            root = Path(temporary)
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            return subprocess.run(
                [sys.executable, str(SCANNER), str(root)],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

    def assert_passes(self, relative_path: str, content: str) -> None:
        result = self.scan(relative_path, content)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PUBLIC_SAFETY_PASS", result.stdout)

    def assert_fails(self, relative_path: str, content: str, category: str) -> None:
        result = self.scan(relative_path, content)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(category, result.stdout)

    def test_real_cn_mobile_phone_fails(self) -> None:
        phone = "138" + "00138000"
        self.assert_fails("contact.txt", f"emergency contact: {phone}\n", "CN_MOBILE_PHONE")

    def test_phone_like_digits_inside_sha256_pass(self) -> None:
        value = ("a" * 20) + ("138" + "00138000") + ("b" * 33)
        self.assertEqual(len(value), 64)
        self.assert_passes("manifest.json", f'{{"sha256":"{value}"}}\n')

    def test_phone_like_digits_inside_task_timestamp_id_pass(self) -> None:
        suffix = "138" + "00138000"
        self.assert_passes("task.txt", f"task-20260903-120000-{suffix}\n")

    def test_exact_local_matrix_test_evidence_passes(self) -> None:
        server = "matrix-local.agentteams.io" + ":18080"
        room = "!" + "LocalEvidenceRoom0123:" + server
        self.assert_passes(
            "tests/fixtures/matrix/matrix.json",
            f'{{"room_id":"{room}"}}\n',
        )

    def test_unknown_matrix_homeserver_fails(self) -> None:
        room = "!" + "UnknownEvidenceRoom0123:" + "matrix.example.org"
        self.assert_fails(
            "tests/fixtures/matrix/matrix.json",
            f'{{"room_id":"{room}"}}\n',
            "MATRIX_ROOM_ID",
        )

    def test_local_matrix_identity_outside_explicit_evidence_scope_fails(self) -> None:
        server = "matrix-local.agentteams.io" + ":18080"
        user_id = "@manager:" + server
        self.assert_fails("notes.txt", f"{user_id}\n", "MATRIX_USER_ID")

    def test_archmind_schema_namespace_passes(self) -> None:
        namespace = "https://" + "archmind.local/schemas/human-decision-v0.2.schema.json"
        self.assert_passes("schema.json", f'{{"$id":"{namespace}"}}\n')

    def test_other_internal_url_fails(self) -> None:
        internal = "https://" + "service.local/api"
        self.assert_fails("config.txt", f"endpoint={internal}\n", "INTERNAL_URL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
