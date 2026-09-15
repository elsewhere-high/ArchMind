#!/usr/bin/env python3
"""Value-oriented secret scan for the final submission staging tree."""

from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path


PARSER = argparse.ArgumentParser(description="Scan ArchMind source or an exported package.")
PARSER.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
PARSER.add_argument("--workspace", action="store_true", help="Exclude only the root Git metadata directory.")
ARGS = PARSER.parse_args()
ROOT = ARGS.root.resolve()
SELF = Path(__file__).resolve()
SKIP_SUFFIXES = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}
FORBIDDEN_FILE_NAMES = {".DS_Store", ".env"}
FORBIDDEN_DIR_NAMES = {
    ".git", ".idea", ".vscode", "__pycache__", ".venv", "venv", "node_modules", "cache", "logs"
}
PATTERNS = {
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "OPENAI_OR_DASHSCOPE_SK": re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_.-]{16,}"),
    "MATRIX_ACCESS_TOKEN": re.compile(r"\bsyt_[A-Za-z0-9_-]{12,}"),
    "BEARER_VALUE": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{16,}"),
    "ALIBABA_ACCESS_KEY": re.compile(r"\bLTAI[A-Za-z0-9]{12,}\b"),
    "AWS_ACCESS_KEY": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "BASIC_AUTH_URL": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
}
ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|access[_-]?key|secret[_-]?key|password|authorization|bearer|cookie|session)\b"
    r"\s*[:=]\s*[\"']?([^\s,;\"']+)"
)
SAFE_VALUE_PREFIXES = ("<", "${", "$", "YOUR_", "REDACTED", "OMITTED", "NONE", "NULL", "EXAMPLE_")


def main() -> int:
    failures: list[tuple[str, int, str]] = []
    files_scanned = 0

    for path in sorted(ROOT.rglob("*")):
        if ARGS.workspace and path.relative_to(ROOT).parts[0] == ".git":
            continue
        if path.is_dir() and path.name in FORBIDDEN_DIR_NAMES:
            failures.append((str(path.relative_to(ROOT)), 0, "FORBIDDEN_DIRECTORY"))
        if not path.is_file():
            continue
        if path.name in FORBIDDEN_FILE_NAMES:
            failures.append((str(path.relative_to(ROOT)), 0, "FORBIDDEN_FILE"))
        if path.suffix.lower() in SKIP_SUFFIXES or path.resolve() == SELF:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        files_scanned += 1
        for number, line in enumerate(lines, 1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    failures.append((str(path.relative_to(ROOT)), number, kind))
            for match in ASSIGNMENT.finditer(line):
                value = match.group(1).strip()
                normalized = value.upper()
                if value and not normalized.startswith(SAFE_VALUE_PREFIXES):
                    failures.append((str(path.relative_to(ROOT)), number, "CREDENTIAL_ASSIGNMENT_VALUE"))

    if failures:
        for path, line, kind in failures:
            print(f"FAIL {path}:{line}:{kind}")
        return 1

    print(f"SECRET_SCAN_PASS files_scanned={files_scanned} credential_values=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
