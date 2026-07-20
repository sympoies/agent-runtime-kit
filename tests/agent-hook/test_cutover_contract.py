#!/usr/bin/env python3
"""Test-first contract for setup-owned provider cutover and sequencing."""

from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_CONFIG = REPO_ROOT / "targets/codex/hooks/config.block.toml"
CLAUDE_CONFIG = REPO_ROOT / "core/hooks/claude/settings.hooks.jsonc"
INVENTORY = REPO_ROOT / "manifests/hook-rules.yaml"
POLICY = REPO_ROOT / "core/policies/agent-hook/runtime-kit-v1.toml"
SYNC = REPO_ROOT / "scripts/sync-runtime-surfaces.sh"
CUTOVER_CASES = (
    REPO_ROOT / "tests/agent-hook/fixtures/cutover-sequencing-cases.json"
)


def load_claude_fragment() -> dict[str, Any]:
    cleaned = "\n".join(
        line
        for line in CLAUDE_CONFIG.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    return json.loads("{\n" + cleaned + "\n}")


def provider_commands() -> list[tuple[str, str, str, str]]:
    commands: list[tuple[str, str, str, str]] = []
    codex = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8")).get("hooks", {})
    for event, groups in codex.items():
        for group in groups:
            for hook in group["hooks"]:
                commands.append(("codex", event, group.get("matcher", ""), hook["command"]))
    for event, groups in load_claude_fragment()["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                commands.append(("claude", event, group.get("matcher", ""), hook["command"]))
    return commands


class AgentHookCutoverContractTests(unittest.TestCase):
    def test_cutover_fixture_freezes_one_ingress_and_post_allow_order(self) -> None:
        fixture = json.loads(CUTOVER_CASES.read_text(encoding="utf-8"))
        self.assertEqual(
            fixture["schema_version"],
            "agent-runtime-kit.hook-cutover-sequencing.v1",
        )
        invariants = fixture["invariants"]
        self.assertEqual(invariants["provider_ingress_per_group"], 1)
        self.assertTrue(invariants["coordination_runs_only_after_allow"])
        self.assertFalse(invariants["provider_sibling_coordination_hook"])
        self.assertEqual(invariants["setup_owner"], "agent-hook")
        by_case = {case["case"]: case for case in fixture["cases"]}
        self.assertEqual(by_case["pre-tool-blocked"]["coordination_operation"], "none")
        self.assertEqual(by_case["pre-tool-allowed"]["coordination_operation"], "admit")
        self.assertEqual(by_case["post-tool-passed"]["coordination_operation"], "complete-pass")
        self.assertEqual(by_case["post-tool-failed"]["coordination_operation"], "complete-fail")
        self.assertEqual(by_case["stop-with-pending-operation"]["coordination_operation"], "reconcile")

    def test_policy_owns_transactional_coordination_lifecycle(self) -> None:
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        transactional = [
            rule
            for rule in inventory["rules"]
            if rule["legacy_handler"] is None
            and rule["state_owner"] == "agent-session.work-context.v1"
        ]
        self.assertTrue(transactional, "missing typed transactional coordination rules")
        events = {event for rule in transactional for event in rule["events"]}
        self.assertTrue(
            {"PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop"} <= events
        )
        self.assertTrue(all(rule["override_class"] == "locked" for rule in transactional))
        policy = tomllib.loads(POLICY.read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in policy["rules"]}
        self.assertTrue(all(rule["id"] in by_id for rule in transactional))

    def test_source_provider_fragments_have_no_rule_specific_or_sibling_ingress(self) -> None:
        forbidden = re.compile(
            r"/hooks/(?:[a-z0-9-]+\.(?:py|sh)|claude-pretool-sequence\.py)"
        )
        residue = [row for row in provider_commands() if forbidden.search(row[3])]
        self.assertFalse(
            residue,
            f"provider sources still own {len(residue)} rule-specific hooks; first={residue[:2]}",
        )

    def test_sync_delegates_exact_ingress_ownership_to_agent_hook_setup(self) -> None:
        source = SYNC.read_text(encoding="utf-8")
        for required in (
            "agent-hook setup",
            "--expected-plan-digest",
            "agent-hook doctor",
        ):
            self.assertTrue(required in source, f"sync is missing {required!r}")
        self.assertTrue(
            "claude-pretool-sequence.py" not in source,
            "sync still references the provider-owned Claude sequencer",
        )


if __name__ == "__main__":
    unittest.main()
