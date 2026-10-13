#!/usr/bin/env python3
"""Derive hook inventory and legacy provenance from the canonical policy."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path
from typing import Any


POLICY_PATH = Path("core/policies/agent-hook/runtime-kit-v1.toml")
ANNOTATION_PREFIX = "# inventory: "
ANNOTATION_FIELDS = (
    "state_owner", "transformation", "recovery", "docs", "test_owner",
    "disposition", "legacy_handler",
)
RULE_FIELDS = (
    "id", "products", "events", "matcher", "capability", "mode", "priority",
    "failure_posture", "timeout_posture", "override_class",
)


def load_policy(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def policy_inventory(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    policy = tomllib.loads(text)
    blocks = re.split(r"(?m)^\s*\[\[rules\]\]\s*$", text)[1:]
    if len(blocks) != len(policy["rules"]):
        raise ValueError("expected one [[rules]] block per policy rule")
    rules = []
    for rule, block in zip(policy["rules"], blocks, strict=True):
        annotations = [
            line.strip()[len(ANNOTATION_PREFIX):]
            for line in block.splitlines()
            if line.strip().startswith(ANNOTATION_PREFIX)
        ]
        if len(annotations) != 1:
            raise ValueError(f"{rule['id']}: expected one inventory annotation")
        metadata = json.loads(annotations[0])
        if not isinstance(metadata, dict) or set(metadata) != set(ANNOTATION_FIELDS):
            raise ValueError(f"{rule['id']}: invalid inventory annotation fields")
        derived = {key: rule.get(key) for key in RULE_FIELDS}
        derived.update((key, metadata[key]) for key in ANNOTATION_FIELDS)
        rules.append(derived)
    legacy = [rule for rule in rules if rule["legacy_handler"] is not None]
    return {
        "schema_version": "agent-runtime-kit.hook-rules.v1",
        "policy_bundle": POLICY_PATH.as_posix(),
        "legacy_handler_count": len({rule["legacy_handler"] for rule in legacy}),
        "legacy_registration_count": sum(
            len(rule["products"]) * len(rule["events"]) for rule in legacy
        ),
        "rules": rules,
    }


def legacy_registrations(inventory: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    return [
        (product, event, rule["matcher"] or "", rule["legacy_handler"])
        for rule in inventory["rules"]
        if rule["legacy_handler"] is not None
        for product in rule["products"]
        for event in rule["events"]
    ]


def matching_rule_ids(
    policy: dict[str, Any], product: str, event: str, matcher: str | None,
) -> set[str]:
    """Select the bundle's literal/alternation bindings for dispatcher fixtures."""
    return {
        rule["id"]
        for rule in policy["rules"]
        if product in rule["products"] and event in rule["events"]
        and (rule.get("matcher") is None or matcher in rule["matcher"].split("|"))
    }


def generated_files(root: Path) -> dict[Path, str]:
    inventory = policy_inventory(root / POLICY_PATH)
    legacy_lines = ["# agent-runtime-kit.legacy-hook-registrations.v1"]
    legacy_lines.extend(
        "\t".join((product, event, matcher or "-", handler))
        for product, event, matcher, handler in legacy_registrations(inventory)
    )
    return {
        root / "manifests/hook-rules.yaml": json.dumps(inventory, indent=2) + "\n",
        root / "tests/agent-hook/fixtures/legacy-registrations.tsv":
            "\n".join(legacy_lines) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--write", action="store_true")
    args = parser.parse_args()
    outputs = generated_files(args.repo)
    stale = []
    for path, content in outputs.items():
        if args.write:
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(path.relative_to(args.repo))
    for path in stale:
        print(f"stale generated hook inventory: {path}; run hook_policy_inventory.py --write")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
