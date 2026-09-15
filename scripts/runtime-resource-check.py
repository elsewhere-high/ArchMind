#!/usr/bin/env python3
"""Validate an AgentTeams JSON resource without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable


READY_VALUES = {"active", "available", "healthy", "ready", "running", "succeeded"}
NOT_READY_VALUES = {
    "creating",
    "error",
    "failed",
    "pending",
    "provisioning",
    "sleeping",
    "stopped",
    "terminating",
}


def dictionaries(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)


def resource_name(item: dict[str, Any]) -> str | None:
    metadata = item.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("name"), str):
        return metadata["name"]
    for key in ("name", "workerName", "managerName", "teamName", "humanName"):
        if isinstance(item.get(key), str):
            return item[key]
    return None


def find_resource(payload: Any, name: str) -> dict[str, Any] | None:
    matches = [item for item in dictionaries(payload) if resource_name(item) == name]
    if not matches:
        return None
    return max(matches, key=lambda item: len(json.dumps(item, ensure_ascii=False)))


def readiness(item: dict[str, Any]) -> tuple[bool | None, str]:
    status = item.get("status")
    if isinstance(status, dict):
        conditions = status.get("conditions")
        if isinstance(conditions, list):
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue
                if str(condition.get("type", "")).lower() == "ready":
                    value = str(condition.get("status", "")).lower()
                    if value in {"true", "1"}:
                        return True, "condition Ready=True"
                    if value in {"false", "0"}:
                        return False, "condition Ready=False"
        for key in ("ready", "isReady"):
            if isinstance(status.get(key), bool):
                return status[key], f"status.{key}"
        for key in ("phase", "state", "status", "runtimeStatus"):
            value = status.get(key)
            if isinstance(value, str):
                normalized = value.lower()
                if normalized in READY_VALUES:
                    return True, f"status.{key}={normalized}"
                if normalized in NOT_READY_VALUES:
                    return False, f"status.{key}={normalized}"
    if isinstance(status, str):
        normalized = status.lower()
        if normalized in READY_VALUES:
            return True, f"status={normalized}"
        if normalized in NOT_READY_VALUES:
            return False, f"status={normalized}"
    for key in ("phase", "state", "runtimeStatus"):
        value = item.get(key)
        if isinstance(value, str):
            normalized = value.lower()
            if normalized in READY_VALUES:
                return True, f"{key}={normalized}"
            if normalized in NOT_READY_VALUES:
                return False, f"{key}={normalized}"
    return None, "no recognized readiness field"


def package_references(item: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for node in dictionaries(item):
        for key in ("package", "packageUri", "packageURI"):
            value = node.get(key)
            if isinstance(value, str):
                values.add(value)
    return values


def member_names(item: dict[str, Any]) -> set[str] | None:
    for node in dictionaries(item):
        for key in ("workerMembers", "members", "workers"):
            members = node.get(key)
            if not isinstance(members, list):
                continue
            names: set[str] = set()
            for member in members:
                if isinstance(member, str):
                    names.add(member)
                elif isinstance(member, dict):
                    name = resource_name(member)
                    if name:
                        names.add(name)
            return names
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--expected-package")
    parser.add_argument("--members", nargs="*")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"invalid AgentTeams JSON: {exc}")
        return 1

    item = find_resource(payload, args.name)
    if item is None:
        print(f"resource not found: {args.name}")
        return 1

    if args.expected_package:
        references = package_references(item)
        if args.expected_package not in references:
            print(f"package reference mismatch for {args.name}")
            return 1

    if args.members is not None:
        actual = member_names(item)
        if actual is None:
            print(f"team membership field unavailable for {args.name}")
            return 3
        missing = sorted(set(args.members) - actual)
        if missing:
            print(f"team members missing for {args.name}: {', '.join(missing)}")
            return 1

    if args.require_ready:
        ready, reason = readiness(item)
        if ready is None:
            print(f"readiness unavailable for {args.name}: {reason}")
            return 3
        if not ready:
            print(f"resource not ready: {args.name} ({reason})")
            return 1

    print(f"resource valid: {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
