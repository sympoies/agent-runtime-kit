#!/usr/bin/env python3
"""Static owner tests for the runtime-kit agent-hook policy contract."""

from __future__ import annotations

import json
import re
import tomllib
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_CONFIG = REPO_ROOT / "targets/codex/hooks/config.block.toml"
CLAUDE_CONFIG = REPO_ROOT / "core/hooks/claude/settings.hooks.jsonc"
INVENTORY = REPO_ROOT / "manifests/hook-rules.yaml"
POLICY = REPO_ROOT / "core/policies/agent-hook/runtime-kit-v1.toml"
PARITY_CASES = REPO_ROOT / "tests/agent-hook/fixtures/parity-cases.json"
COORDINATION_CASES = REPO_ROOT / "tests/agent-hook/fixtures/coordination-cases.json"
READ_ONLY_SHADOW_CASES = (
    REPO_ROOT / "tests/agent-hook/fixtures/read-only-shadow-cases.json"
)
LEGACY_REGISTRATIONS = (
    REPO_ROOT / "tests/agent-hook/fixtures/legacy-registrations.tsv"
)

EXPECTED_HANDLERS = {
    "agent-scope-lock-guard",
    "block-claude-coauthor-trailer",
    "block-direct-git-commit",
    "block-direct-git-worktree",
    "block-direct-pr-create",
    "block-direct-python",
    "block-project-memory-write",
    "block-unsafe-default-delivery",
    "checkout-lease-guard",
    "finish-line-record",
    "forge-label-reminder",
    "mcp-secret-scan",
    "memory-write-principle-reminder",
    "portable-paths-scan",
    "pre-edit-intent-gate",
    "semantic-commit-body-gate",
    "session-start-healthcheck",
    "skill-usage-reminder",
    "stop-finish-line-gate",
    "stop-pre-pr-reminder",
    "user-prompt-agent-docs",
    "user-prompt-agent-memory",
}

EXPECTED_EVENT_COUNTS = {
    "codex": Counter(
        {"PreToolUse": 22, "UserPromptSubmit": 4, "Stop": 4, "SessionStart": 1}
    ),
    "claude": Counter(
        {"PreToolUse": 29, "UserPromptSubmit": 3, "Stop": 4, "SessionStart": 1}
    ),
}

INVENTORY_RULE_FIELDS = {
    "id",
    "products",
    "events",
    "matcher",
    "capability",
    "mode",
    "priority",
    "failure_posture",
    "override_class",
    "state_owner",
    "transformation",
    "recovery",
    "docs",
    "test_owner",
    "disposition",
    "legacy_handler",
}

POLICY_RULE_FIELDS = {
    "id",
    "products",
    "events",
    "matcher",
    "priority",
    "mode",
    "failure_posture",
    "override_class",
    "capability",
}

LOCKED_CAPABILITIES = {
    "agent-session.owner-liveness.v1",
    "agent-session.semantic-conflict.v1",
}

COORDINATION_CAPABILITY_COUNTS = Counter(
    {
        "agent-session.activity.v1": 7,
        "agent-session.semantic-conflict.v1": 6,
        "agent-session.owner-liveness.v1": 5,
        "agent-session.coordination.v1": 8,
    }
)

READ_ONLY_SHADOW_RULE_ID = "runtime.shared.pre-tool-use.bash.read-only-shadow"

TERMINAL_COORDINATION_GROUPS = {
    (
        "codex",
        "PostToolUse",
        "Bash|Write|Edit|NotebookEdit|apply_patch",
    ),
    (
        "codex",
        "PostToolUseFailure",
        "Bash|Write|Edit|NotebookEdit|apply_patch",
    ),
    (
        "claude",
        "PostToolUse",
        "Bash|Write|Edit|NotebookEdit|MultiEdit",
    ),
    (
        "claude",
        "PostToolUseFailure",
        "Bash|Write|Edit|NotebookEdit|MultiEdit",
    ),
}

FORBIDDEN_POLICY_FRAGMENTS = (
    "/home/",
    "/Users/",
    "session_id",
    "mailbox",
    "authorization",
    "bearer",
    "token",
)


def load_claude_fragment() -> dict[str, Any]:
    cleaned = "\n".join(
        line
        for line in CLAUDE_CONFIG.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    return json.loads("{\n" + cleaned + "\n}")


def handler_from_command(command: str) -> str | None:
    match = re.search(r"/hooks/([a-z0-9-]+)\.(?:py|sh)", command)
    return match.group(1) if match else None


def active_provider_registrations() -> list[tuple[str, str, str, str]]:
    registrations: list[tuple[str, str, str, str]] = []
    codex = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))["hooks"]
    for event, groups in codex.items():
        for group in groups:
            matcher = group.get("matcher", "")
            for hook in group["hooks"]:
                handler = handler_from_command(hook["command"])
                if handler is not None:
                    registrations.append(("codex", event, matcher, handler))

    claude = load_claude_fragment()["hooks"]
    for event, groups in claude.items():
        for group in groups:
            matcher = group.get("matcher", "")
            for hook in group["hooks"]:
                handler = handler_from_command(hook["command"])
                if handler is not None:
                    registrations.append(("claude", event, matcher, handler))
    return registrations


def frozen_legacy_registrations() -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    lines = LEGACY_REGISTRATIONS.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "# agent-runtime-kit.legacy-hook-registrations.v1":
        raise AssertionError("invalid legacy registration fixture schema")
    for line in lines[1:]:
        product, event, matcher, handler = line.split("\t")
        rows.append((product, event, "" if matcher == "-" else matcher, handler))
    return rows


def load_inventory() -> dict[str, Any]:
    # JSON is a strict subset of YAML. Keeping this manifest JSON-compatible
    # makes the governance check dependency-free on macOS and Linux.
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


class AgentHookPolicyContractTests(unittest.TestCase):
    def test_baseline_inventory_is_complete_and_exact(self) -> None:
        registrations = frozen_legacy_registrations()
        self.assertEqual(len(registrations), 68)
        self.assertEqual({row[3] for row in registrations}, EXPECTED_HANDLERS)
        for product in ("codex", "claude"):
            event_counts = Counter(row[1] for row in registrations if row[0] == product)
            self.assertEqual(event_counts, EXPECTED_EVENT_COUNTS[product], product)

        product_handlers = {
            product: {row[3] for row in registrations if row[0] == product}
            for product in ("codex", "claude")
        }
        self.assertEqual(len(product_handlers["codex"]), 21)
        self.assertEqual(len(product_handlers["claude"]), 21)
        self.assertEqual(
            product_handlers["codex"] - product_handlers["claude"],
            {"user-prompt-agent-memory"},
        )
        self.assertEqual(
            product_handlers["claude"] - product_handlers["codex"],
            {"block-claude-coauthor-trailer"},
        )

    def test_inventory_and_policy_sources_exist(self) -> None:
        self.assertTrue(INVENTORY.is_file(), "missing manifests/hook-rules.yaml")
        self.assertTrue(POLICY.is_file(), "missing versioned runtime-kit policy bundle")

    def test_inventory_dispositions_cover_every_legacy_handler(self) -> None:
        inventory = load_inventory()
        self.assertEqual(
            set(inventory),
            {
                "schema_version",
                "policy_bundle",
                "legacy_handler_count",
                "legacy_registration_count",
                "rules",
            },
        )
        self.assertEqual(inventory["schema_version"], "agent-runtime-kit.hook-rules.v1")
        self.assertEqual(inventory["policy_bundle"], "core/policies/agent-hook/runtime-kit-v1.toml")
        self.assertEqual(inventory["legacy_handler_count"], 22)
        self.assertEqual(inventory["legacy_registration_count"], 68)

        rules = inventory["rules"]
        self.assertIsInstance(rules, list)
        self.assertEqual(len(rules), 95)
        ids = [rule["id"] for rule in rules]
        self.assertEqual(len(ids), len(set(ids)), "duplicate inventory rule id")
        for rule in rules:
            self.assertEqual(set(rule), INVENTORY_RULE_FIELDS, rule.get("id"))

        dispositions: dict[str, set[str]] = defaultdict(set)
        for rule in rules:
            handler = rule["legacy_handler"]
            if handler is not None:
                dispositions[handler].add(rule["disposition"])
        self.assertEqual(set(dispositions), EXPECTED_HANDLERS)
        for handler, values in dispositions.items():
            self.assertEqual(len(values), 1, f"ambiguous disposition for {handler}")

        legacy_rules = [rule for rule in rules if rule["legacy_handler"] is not None]
        inventory_registrations = [
            (
                rule["products"][0],
                rule["events"][0],
                rule["matcher"] or "",
                rule["legacy_handler"],
            )
            for rule in legacy_rules
        ]
        self.assertEqual(inventory_registrations, frozen_legacy_registrations())

        priorities: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        for rule in legacy_rules:
            self.assertEqual(len(rule["products"]), 1, rule["id"])
            self.assertEqual(len(rule["events"]), 1, rule["id"])
            key = (rule["products"][0], rule["events"][0], rule["matcher"] or "")
            priorities[key].append(rule["priority"])
        for key, values in priorities.items():
            self.assertEqual(values, sorted(values), key)
            self.assertEqual(len(values), len(set(values)), key)

        added_rules = [rule for rule in rules if rule["legacy_handler"] is None]
        read_only_rules = [
            rule for rule in added_rules if rule["id"] == READ_ONLY_SHADOW_RULE_ID
        ]
        self.assertEqual(len(read_only_rules), 1)
        self.assertEqual(
            read_only_rules[0]["capability"]["id"], "execution.read-only.v1"
        )
        self.assertEqual(read_only_rules[0]["products"], ["codex", "claude"])
        self.assertEqual(read_only_rules[0]["events"], ["PreToolUse"])
        self.assertEqual(read_only_rules[0]["matcher"], "Bash")
        self.assertEqual(read_only_rules[0]["mode"], "shadow")
        self.assertEqual(read_only_rules[0]["disposition"], "added-read-only-shadow")

        coordination_rules = [
            rule for rule in added_rules if rule["id"] != READ_ONLY_SHADOW_RULE_ID
        ]
        self.assertEqual(len(coordination_rules), 26)
        self.assertEqual(
            Counter(rule["capability"]["id"] for rule in coordination_rules),
            COORDINATION_CAPABILITY_COUNTS,
        )
        self.assertTrue(
            all(rule["disposition"] == "added-coordination" for rule in coordination_rules)
        )

        selected_groups = {
            (product, event, rule["matcher"] or "")
            for rule in rules
            for product in rule["products"]
            for event in rule["events"]
        }
        legacy_groups = {
            (product, event, matcher)
            for product, event, matcher, _ in frozen_legacy_registrations()
        }
        self.assertEqual(selected_groups, legacy_groups | TERMINAL_COORDINATION_GROUPS)

        for rule in rules:
            self.assertLessEqual(len(rule["id"]), 128, rule["id"])
            if rule["matcher"] is not None:
                atoms = rule["matcher"].split("|")
                self.assertEqual(len(atoms), len(set(atoms)), rule["id"])
                self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9_.:-]+", atom) for atom in atoms))
            docs_path = REPO_ROOT / rule["docs"]
            self.assertTrue(docs_path.is_file(), f"missing docs owner for {rule['id']}")
            test_path = REPO_ROOT / rule["test_owner"].split("::", 1)[0]
            self.assertTrue(test_path.is_file(), f"missing test owner for {rule['id']}")

    def test_strict_toml_policy_matches_inventory(self) -> None:
        inventory = load_inventory()
        policy_text = POLICY.read_text(encoding="utf-8")
        policy = tomllib.loads(policy_text)
        self.assertEqual(set(policy), {"schema_version", "bundle_id", "version", "rules"})
        self.assertEqual(policy["schema_version"], "agent-hook.policy.v1")
        self.assertEqual(policy["bundle_id"], "runtime-kit")
        self.assertRegex(policy["version"], r"^\d{4}\.\d{2}\.\d{2}\.\d+$")

        policy_rules = policy["rules"]
        inventory_by_id = {rule["id"]: rule for rule in inventory["rules"]}
        self.assertEqual({rule["id"] for rule in policy_rules}, set(inventory_by_id))
        self.assertEqual(len(policy_rules), len(inventory_by_id))
        for rule in policy_rules:
            expected = inventory_by_id[rule["id"]]
            expected_fields = set(POLICY_RULE_FIELDS)
            if expected["matcher"] is None:
                expected_fields.remove("matcher")
            self.assertEqual(set(rule), expected_fields, rule["id"])
            for key in (
                "products",
                "events",
                "priority",
                "mode",
                "failure_posture",
                "override_class",
                "capability",
            ):
                self.assertEqual(rule[key], expected[key], f"{rule['id']}:{key}")
            self.assertEqual(rule.get("matcher"), expected["matcher"], f"{rule['id']}:matcher")
            capability_id = rule["capability"]["id"]
            if rule["override_class"] == "locked" or capability_id in LOCKED_CAPABILITIES:
                self.assertEqual(rule["failure_posture"], "closed", rule["id"])

        lowered = policy_text.lower()
        for fragment in FORBIDDEN_POLICY_FRAGMENTS:
            self.assertNotIn(fragment.lower(), lowered)

    def test_parity_baseline_covers_every_decision_form(self) -> None:
        cases = json.loads(PARITY_CASES.read_text(encoding="utf-8"))
        self.assertEqual(cases["schema_version"], "agent-runtime-kit.hook-parity.v1")
        self.assertEqual(
            {case["expected_action"] for case in cases["cases"]},
            {"allow", "warn", "block", "context", "transform", "failure"},
        )
        inventory_ids = {rule["id"] for rule in load_inventory()["rules"]}
        for case in cases["cases"]:
            if case["rule_id"] is not None:
                self.assertIn(case["rule_id"], inventory_ids)
            self.assertRegex(case["owner_test"], r"^tests/")

    def test_read_only_shadow_mismatches_have_finite_dispositions(self) -> None:
        fixture = json.loads(READ_ONLY_SHADOW_CASES.read_text(encoding="utf-8"))
        self.assertEqual(
            fixture["schema_version"],
            "agent-runtime-kit.read-only-shadow-cases.v1",
        )
        self.assertEqual(fixture["rule_id"], READ_ONLY_SHADOW_RULE_ID)
        self.assertEqual(fixture["production_authority"], "legacy-pre-edit-intent-gate")
        self.assertEqual(len(fixture["unknown_feedback_routes"]), 2)
        self.assertIn("agent-run inspect", fixture["unknown_feedback_routes"][0])
        self.assertIn("prepare project-dev", fixture["unknown_feedback_routes"][1])
        comparisons = Counter(case["comparison"] for case in fixture["cases"])
        self.assertEqual(comparisons, Counter({"mismatch": 2, "parity": 2}))
        for case in fixture["cases"]:
            self.assertTrue(case["disposition"].strip(), case["case"])
            self.assertNotIn("allowlist", case["disposition"].lower())

    def test_coordination_admission_baseline_is_conservative(self) -> None:
        cases = json.loads(COORDINATION_CASES.read_text(encoding="utf-8"))
        self.assertEqual(cases["schema_version"], "agent-runtime-kit.coordination-cases.v1")
        by_case = {case["case"]: case["expected_action"] for case in cases["cases"]}
        self.assertEqual(by_case["semantic-definite"], "block")
        self.assertEqual(by_case["semantic-potential"], "warn")
        self.assertEqual(by_case["semantic-unknown"], "warn")
        self.assertEqual(by_case["semantic-clear"], "allow")
        self.assertEqual(by_case["writer-active-foreign"], "block")
        self.assertEqual(by_case["writer-stale-clean"], "allow")
        self.assertEqual(by_case["writer-stale-dirty"], "block")
        self.assertEqual(by_case["writer-orphaned-clean"], "warn")
        self.assertEqual(by_case["writer-orphaned-dirty"], "block")
        self.assertEqual(by_case["writer-unknown"], "block")


if __name__ == "__main__":
    unittest.main()
