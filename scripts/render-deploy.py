#!/usr/bin/env python3
"""Resolve package URIs and render the AgentTeams deployment template.

Only environment variable names and status markers are printed. URI values are
never logged because deployments may use non-public storage locations.
"""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse


PACKAGES = {
    "PACKAGE_URI_REVIEW_COORDINATOR": "review-coordinator.zip",
    "PACKAGE_URI_HARDSCAPE_REVIEWER": "hardscape-reviewer.zip",
    "PACKAGE_URI_PLANTING_REVIEWER": "planting-reviewer.zip",
    "PACKAGE_URI_STORMWATER_SPONGE_REVIEWER": "stormwater-sponge-reviewer.zip",
    "PACKAGE_URI_EVIDENCE_VERIFIER": "evidence-verifier.zip",
}
URI_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^\s]+$")


def resolve_uris() -> dict[str, str]:
    base = os.environ.get("PACKAGE_URI_BASE", "").strip().rstrip("/")
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for variable, archive in PACKAGES.items():
        value = os.environ.get(variable, "").strip()
        if not value and base:
            value = f"{base}/{archive}"
        if not value:
            missing.append(variable)
            continue
        if not URI_PATTERN.match(value):
            raise ValueError(f"{variable} must be an absolute URI with a scheme")
        parsed = urlparse(value)
        if parsed.username or parsed.password:
            raise ValueError(f"{variable} must not embed credentials")
        if parsed.query or parsed.fragment:
            raise ValueError(f"{variable} must not use query or fragment credentials")
        if "${" in value or "PACKAGE_URI_" in value:
            raise ValueError(f"{variable} is unresolved")
        resolved[variable] = value
    if missing:
        raise ValueError(
            "missing package URI configuration: " + ", ".join(sorted(missing))
        )
    return resolved


def render(template: Path, output: Path, values: dict[str, str]) -> None:
    if not template.is_file():
        raise ValueError("deployment template does not exist")
    text = template.read_text(encoding="utf-8")
    for placeholder, value in values.items():
        count = text.count(placeholder)
        if count != 1:
            raise ValueError(
                f"template must contain {placeholder} exactly once; found {count}"
            )
        text = text.replace(placeholder, value)
    if "PACKAGE_URI_" in text:
        raise ValueError("deployment template still contains unresolved package URI")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.chmod(0o600)
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    try:
        values = resolve_uris()
        print(f"PACKAGE_URI_RESOLUTION_PASS count={len(values)} values_redacted=true")
        if args.check_only:
            return 0
        if args.output is None:
            raise ValueError("--output is required unless --check-only is used")
        render(args.template, args.output, values)
        print("DEPLOY_RENDER_PASS placeholders=5 secrets_written=0")
        return 0
    except (OSError, ValueError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
