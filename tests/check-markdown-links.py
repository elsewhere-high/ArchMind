#!/usr/bin/env python3
"""Check that relative Markdown links resolve inside the public package."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    failures = []
    checked = 0
    readme_checked = 0
    for source in sorted(ROOT.rglob("*.md")):
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = unquote(target.split("#", 1)[0])
            if not path_part:
                continue
            checked += 1
            if source.name == "README.md":
                readme_checked += 1
            resolved = (source.parent / path_part).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"{source.relative_to(ROOT)}: link escapes package: {target}")
                continue
            if not resolved.exists():
                failures.append(f"{source.relative_to(ROOT)}: missing target: {target}")
    if failures:
        print("\n".join(f"FAIL {item}" for item in failures))
        return 1
    print(f"MARKDOWN_LINKS_PASS internal_links={checked} readme_links={readme_checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
