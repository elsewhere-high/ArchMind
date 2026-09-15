#!/usr/bin/env python3
"""Public-package safety checks that distinguish keyword mentions from values."""

from __future__ import annotations

import re
import sys
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ROOT
SKIP_SUFFIXES = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}
FORBIDDEN_NAMES = {".DS_Store", ".env", "initial-round-sensitive-scan.txt"}

VALUE_PATTERNS = {
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "JWT_VALUE": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "SK_KEY_VALUE": re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    "BEARER_VALUE": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{20,}"),
    "MATRIX_TOKEN_VALUE": re.compile(r"\bsyt_[A-Za-z0-9_-]{15,}"),
    "ALIBABA_ACCESS_KEY": re.compile(r"\bLTAI[A-Za-z0-9]{12,}\b"),
    "CREDENTIAL_ASSIGNMENT": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?key|secret[_-]?key|token|password|authorization|cookie|session)\b\s*[:=]\s*[\"']?(?!<|\$\{|YOUR_|none\b|null\b|omitted\b|redacted\b)[A-Za-z0-9._~+/-]{16,}"
    ),
}

IDENTIFIER_PATTERNS = {
    "PERSONAL_PATH": re.compile(r"/Users/[^<\s/]+/|/home/[^<\s/]+/"),
    "ROOT_ABSOLUTE_PATH": re.compile(r"/root/"),
    "LOCALHOST_OR_PRIVATE_IP": re.compile(r"(?i)\b(?:localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
    "EMAIL_ADDRESS": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
}
MATRIX_PATTERNS = {
    "MATRIX_ROOM_ID": re.compile(
        r"![A-Za-z0-9_-]{10,}(?::(?P<host>[A-Za-z0-9.-]+)(?::(?P<port>\d+))?)?"
    ),
    "MATRIX_USER_ID": re.compile(
        r"@[A-Za-z0-9._=-]+:(?P<host>[A-Za-z0-9.-]+)(?::(?P<port>\d+))?"
    ),
}
CN_MOBILE_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
SHA256_VALUE = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])")
TASK_TIMESTAMP_ID = re.compile(
    r"(?<![A-Za-z0-9_-])task-\d{8}-\d{6}-[A-Za-z0-9._-]+(?![A-Za-z0-9._-])"
)
URL_VALUE = re.compile(r"https?://[^\s<>)\]`\"']+")

LOCAL_TEST_MATRIX_HOST = "matrix-local.agentteams.io"
LOCAL_TEST_MATRIX_PORT = "18080"
# Only this synthetic fixture scope is classified as local AgentTeams test evidence.
LOCAL_TEST_MATRIX_EVIDENCE_PREFIXES = (
    "tests/fixtures/matrix/",
)
LOCAL_TEST_MATRIX_EVIDENCE_EXACT_FILES = frozenset(
    {"evaluation/dataset/eval-set-v0.1.jsonl"}
)
SCHEMA_NAMESPACE_HOST = "archmind.local"
SCHEMA_NAMESPACE_PREFIX = "/schemas/"


def text_files():
    for path in ROOT.rglob("*"):
        if path.relative_to(ROOT).parts[0] == ".git":
            continue
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part.startswith(".venv") for part in path.parts):
            continue
        if path.resolve() == Path(__file__).resolve():
            # The scanner contains its own detection regexes.
            continue
        yield path


def is_within(match: re.Match[str], containers: list[re.Match[str]]) -> bool:
    return any(start.start() <= match.start() and match.end() <= start.end() for start in containers)


def is_allowed_local_test_matrix(path: Path, match: re.Match[str]) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    in_explicit_evidence_scope = any(
        relative.startswith(prefix) for prefix in LOCAL_TEST_MATRIX_EVIDENCE_PREFIXES
    ) or relative in LOCAL_TEST_MATRIX_EVIDENCE_EXACT_FILES
    return (
        in_explicit_evidence_scope
        and (match.groupdict().get("host") or "").lower() == LOCAL_TEST_MATRIX_HOST
        and match.groupdict().get("port") == LOCAL_TEST_MATRIX_PORT
    )


def is_allowed_schema_namespace(raw_url: str) -> bool:
    parsed = urlparse(raw_url)
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == SCHEMA_NAMESPACE_HOST
        and parsed.port is None
        and parsed.username is None
        and parsed.password is None
        and parsed.path.startswith(SCHEMA_NAMESPACE_PREFIX)
    )


def main() -> int:
    failures = []
    allowlisted_matrix_ids = 0
    allowlisted_schema_namespaces = 0
    ignored_structured_numeric_matches = 0
    for path in ROOT.rglob("*"):
        if path.relative_to(ROOT).parts[0] == ".git":
            continue
        if path.is_file() and path.name in FORBIDDEN_NAMES:
            failures.append((path, 0, "FORBIDDEN_FILE"))
        if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            failures.append((path, 0, "LARGE_FILE_OVER_10MB"))

    for path in text_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            for kind, pattern in {**VALUE_PATTERNS, **IDENTIFIER_PATTERNS}.items():
                if pattern.search(line):
                    failures.append((path, number, kind))
            for kind, pattern in MATRIX_PATTERNS.items():
                for match in pattern.finditer(line):
                    if is_allowed_local_test_matrix(path, match):
                        allowlisted_matrix_ids += 1
                    else:
                        failures.append((path, number, kind))
            structured_values = list(SHA256_VALUE.finditer(line)) + list(TASK_TIMESTAMP_ID.finditer(line))
            for match in CN_MOBILE_PHONE.finditer(line):
                if is_within(match, structured_values):
                    ignored_structured_numeric_matches += 1
                else:
                    failures.append((path, number, "CN_MOBILE_PHONE"))
            for raw_url in URL_VALUE.findall(line):
                host = (urlparse(raw_url).hostname or "").lower()
                internal = not host or "." not in host or host.endswith(".local")
                try:
                    internal = internal or ip_address(host).is_private
                except ValueError:
                    pass
                if internal:
                    if is_allowed_schema_namespace(raw_url):
                        allowlisted_schema_namespaces += 1
                    else:
                        failures.append((path, number, "INTERNAL_URL"))

    if failures:
        for path, line, kind in failures:
            print(f"FAIL {path.relative_to(ROOT)}:{line}:{kind}")
        return 1

    print("keyword_mentions=allowed credential_values=0")
    print(
        f"local_test_matrix_ids={allowlisted_matrix_ids} "
        f"schema_namespaces={allowlisted_schema_namespaces} "
        f"structured_numeric_exclusions={ignored_structured_numeric_matches}"
    )
    print("PUBLIC_SAFETY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
