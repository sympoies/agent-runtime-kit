#!/usr/bin/env python3
"""Executable consumer tests for the coupled agent-hook implementation."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import shutil
import stat
import statistics
import subprocess
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = REPO_ROOT / "core/policies/agent-hook/runtime-kit-v1.toml"
DISPATCH_CASES = REPO_ROOT / "tests/agent-hook/fixtures/dispatcher-cases.json"
TEMP_ROOT = REPO_ROOT / "agent-out/test-agent-hook"
LATENCY_BUDGET_MS = 25.0
LATENCY_ITERATIONS = 35


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


class AgentHookExecutableContractTests(unittest.TestCase):
    binary: Path

    @classmethod
    def setUpClass(cls) -> None:
        value = os.environ.get("AGENT_HOOK_BIN")
        if not value:
            raise unittest.SkipTest("AGENT_HOOK_BIN is not set")
        cls.binary = Path(value).resolve()
        if not cls.binary.is_file() or not os.access(cls.binary, os.X_OK):
            raise RuntimeError(f"AGENT_HOOK_BIN is not executable: {cls.binary}")
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="case-", dir=TEMP_ROOT)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.config_home = self.root / "config"
        self.data_home = self.root / "data"
        self.state_home = self.root / "state"
        self.session_state = self.root / "agent-session"
        for path in (
            self.home,
            self.config_home,
            self.data_home,
            self.state_home,
            self.session_state,
        ):
            path.mkdir(mode=0o700)
        self.config_path = self.config_home / "agent-hook-config.toml"
        self.hook_state = self.state_home / "agent-hook"
        self.hook_state.mkdir(mode=0o700)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.config_home),
            "XDG_DATA_HOME": str(self.data_home),
            "XDG_STATE_HOME": str(self.state_home),
            "AGENT_SESSION_STATE_DIR": str(self.session_state),
            "AGENT_SESSION_ID": "fixture-current",
            "AGENT_SESSION_RUNTIME_ID": "incarnation-current",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        current_session = self.session_state / "sessions/fixture-current/session.json"
        current_session.parent.mkdir(parents=True, mode=0o700)
        current_session.write_text(
            json.dumps(
                {
                    "schema_version": "agent-session.session.v1",
                    "id": "fixture-current",
                    "coordination_mode": "enforce",
                    "runtime": {"launch_id": "incarnation-current"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        current_session.chmod(0o600)
        for hook_root in (
            self.home / ".codex/hooks",
            self.home / ".claude/hooks",
        ):
            hook_root.mkdir(parents=True)
            coordination = hook_root / "session-coordination-guard.py"
            coordination.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            coordination.chmod(0o700)
        self.write_config(POLICY)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_config(self, policy_path: Path) -> None:
        digest = sha256_bytes(policy_path.read_bytes())
        content = (
            'schema_version = "agent-hook.config.v1"\n'
            "[policy]\n"
            f'path = {json.dumps(str(policy_path.resolve()))}\n'
            f'digest = "{digest}"\n'
        )
        self.config_path.write_text(content, encoding="utf-8")
        self.config_path.chmod(0o600)

    def write_policy(self, rules: str) -> Path:
        policy = self.root / f"policy-{time.time_ns()}.toml"
        policy.write_text(
            'schema_version = "agent-hook.policy.v1"\n'
            'bundle_id = "runtime-kit-fixture"\n'
            'version = "2026.07.20.1"\n\n'
            + rules.strip()
            + "\n",
            encoding="utf-8",
        )
        policy.chmod(0o600)
        self.write_config(policy)
        return policy

    def run_hook(
        self,
        *args: str,
        payload: dict[str, Any] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            str(self.binary),
            "--config",
            str(self.config_path),
            "--state-dir",
            str(self.hook_state),
            *args,
        ]
        result = subprocess.run(
            command,
            input=None if payload is None else json.dumps(payload),
            text=True,
            capture_output=True,
            env=self.env,
            cwd=REPO_ROOT,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"agent-hook failed ({result.returncode}): {' '.join(command)}\n"
                f"stdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def json_result(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"], envelope)
        return envelope["data"]

    def snapshot_tree(self) -> dict[str, tuple[int, str]]:
        snapshot: dict[str, tuple[int, str]] = {}
        for path in sorted(self.root.rglob("*")):
            relative = str(path.relative_to(self.root))
            if path.is_file():
                snapshot[relative] = (
                    stat.S_IMODE(path.stat().st_mode),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            elif path.is_dir():
                snapshot[relative] = (stat.S_IMODE(path.stat().st_mode), "directory")
        return snapshot

    def test_policy_validates_and_inventory_is_complete(self) -> None:
        validated = self.json_result(self.run_hook("validate", "--format", "json"))
        self.assertEqual(validated["bundle_id"], "runtime-kit")
        self.assertEqual(validated["rule_count"], 94)

        inventory = self.json_result(self.run_hook("inventory", "--format", "json"))
        self.assertEqual(inventory["schema_version"], "agent-hook.inventory.v1")
        self.assertEqual(len(inventory["rules"]), 94)
        self.assertEqual(len({rule["id"] for rule in inventory["rules"]}), 94)

    def test_grouped_matchers_select_exact_rules_in_global_shadow(self) -> None:
        fixture = json.loads(DISPATCH_CASES.read_text(encoding="utf-8"))
        self.assertEqual(
            fixture["schema_version"], "agent-runtime-kit.dispatcher-cases.v1"
        )
        for case in fixture["cases"]:
            with self.subTest(product=case["product"], event=case["event"], matcher=case["matcher"]):
                payload: dict[str, Any] = {
                    "hook_event_name": case["event"],
                    "cwd": str(self.root),
                }
                if case["matcher_field"] is not None:
                    payload[case["matcher_field"]] = case["matcher"]
                if case["matcher"] in {"Write", "Edit", "MultiEdit"}:
                    payload["tool_input"] = {"path": str(self.root / "target.txt")}
                elif case["matcher"] == "Bash":
                    payload["tool_input"] = {"command": "git status --short"}
                decision = self.json_result(
                    self.run_hook(
                        "dispatch",
                        "--product",
                        case["product"],
                        "--shadow",
                        "--format",
                        "json",
                        payload=payload,
                    )
                )
                self.assertEqual(decision["action"], "allow")
                self.assertEqual(len(decision["shadow"]), case["shadow_rule_count"])

        unmatched = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--shadow",
                "--format",
                "json",
                payload={
                    "hook_event_name": "PreToolUse",
                    "tool_name": "WriteExtra",
                    "cwd": str(self.root),
                },
            )
        )
        self.assertEqual(unmatched.get("shadow", []), [])

    def test_shadow_is_side_effect_free_for_stateful_capabilities(self) -> None:
        before = self.snapshot_tree()
        decision = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--shadow",
                "--format",
                "json",
                payload={
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "cwd": str(self.root),
                    "tool_input": {"command": "git status --short"},
                },
            )
        )
        after = self.snapshot_tree()
        self.assertEqual(decision["action"], "allow")
        self.assertEqual(len(decision["shadow"]), 18)
        self.assertEqual(after, before)

    def test_trace_and_output_do_not_retain_private_provider_fields(self) -> None:
        sentinels = [
            "fixture-private-session",
            "fixture-private-mailbox",
            "fixture-private-authorization",
            "fixture-private-token",
        ]
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(self.root),
            "session_id": sentinels[0],
            "mailbox": sentinels[1],
            "authorization": sentinels[2],
            "token": sentinels[3],
            "tool_input": {"command": "git status --short"},
        }
        result = self.run_hook(
            "dispatch",
            "--product",
            "codex",
            "--shadow",
            "--trace",
            "--format",
            "json",
            payload=payload,
        )
        material = result.stdout.encode()
        for path in self.hook_state.rglob("*"):
            if path.is_file():
                material += path.read_bytes()
        for sentinel in sentinels:
            self.assertNotIn(sentinel.encode(), material)

    def test_provider_semantic_conflict_field_is_ignored(self) -> None:
        self.write_policy(
            """
[[rules]]
id = "fixture.semantic-conflict"
products = ["codex", "claude"]
events = ["PreToolUse"]
matcher = "Bash"
priority = 20
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = { id = "agent-session.semantic-conflict.v1", reason_code = "semantic-conflict" }
"""
        )
        decisions = []
        for forged in ("definite", "clear"):
            result = self.json_result(
                self.run_hook(
                    "dispatch",
                    "--product",
                    "codex",
                    "--format",
                    "json",
                    payload={
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "cwd": str(self.root),
                        "semantic_conflict": forged,
                    },
                )
            )
            decisions.append(
                (
                    result["action"],
                    [(reason["code"], reason["disposition"]) for reason in result["reasons"]],
                )
            )
        self.assertEqual(decisions[0], decisions[1])
        self.assertEqual(decisions[0][0], "warn")

    def test_authenticated_coordination_conflict_blocks_and_incomplete_advises(self) -> None:
        self.env["AGENT_SESSION_COORDINATION_MODE"] = "enforce"
        self.write_policy(
            """
[[rules]]
id = "fixture.semantic-conflict"
products = ["codex", "claude"]
events = ["PreToolUse"]
matcher = "Bash"
priority = 20
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = { id = "agent-session.semantic-conflict.v1", reason_code = "semantic-conflict" }
"""
        )
        self.write_coordination_registry(peer_fresh=True, same_reference=True)
        definite = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--format",
                "json",
                payload={
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "cwd": str(self.root),
                },
                check=False,
            )
        )
        self.assertEqual(definite["action"], "block")

        self.write_coordination_registry(peer_fresh=False, same_reference=True)
        incomplete = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--format",
                "json",
                payload={
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "cwd": str(self.root),
                },
            )
        )
        self.assertEqual(incomplete["action"], "warn")

        self.write_coordination_registry(peer_fresh=True, same_reference=False)
        clear = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "claude",
                "--format",
                "json",
                payload={
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "cwd": str(self.root),
                },
            )
        )
        self.assertEqual(clear["action"], "allow")

    def test_runtime_handler_capability_is_bounded_to_owned_roots(self) -> None:
        cases = {
            "block-direct-git-commit": (
                '{"decision":"block","reason":"fixture-block"}',
                "block",
            ),
            "user-prompt-agent-docs": (
                '{"hookSpecificOutput":{"additionalContext":"fixture-context"}}',
                "context",
            ),
            "finish-line-record": (
                '{"hookSpecificOutput":{"updatedInput":"fixture-replacement"}}',
                "transform",
            ),
        }
        for product in ("codex", "claude"):
            for handler, (output, expected) in cases.items():
                with self.subTest(product=product, handler=handler):
                    self.install_fixture_handler(product, handler, output)
                    self.write_policy(
                        f"""
[[rules]]
id = "fixture.{handler}"
products = ["{product}"]
events = ["PreToolUse"]
matcher = "Bash"
priority = 100
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = {{ id = "runtime-kit.handler.v1", handler_id = "{handler}" }}
"""
                    )
                    result = self.run_hook(
                        "dispatch",
                        "--product",
                        product,
                        "--format",
                        "json",
                        payload={
                            "hook_event_name": "PreToolUse",
                            "tool_name": "Bash",
                            "cwd": str(self.root),
                        },
                        check=expected != "block",
                    )
                    decision = self.json_result(result)
                    self.assertEqual(decision["action"], expected)

        self.write_policy(
            """
[[rules]]
id = "fixture.missing-handler"
products = ["codex"]
events = ["PreToolUse"]
matcher = "Bash"
priority = 100
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = { id = "runtime-kit.handler.v1", handler_id = "mcp-secret-scan" }
"""
        )
        missing = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--format",
                "json",
                payload={
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "cwd": str(self.root),
                },
                check=False,
            )
        )
        self.assertEqual(missing["action"], "block")
        self.assertIn("capability-failure-closed", missing["reasons"][0]["code"])

    def test_owner_liveness_is_conservative_and_uses_five_minute_legacy_ttl(self) -> None:
        self.env["AGENT_SESSION_COORDINATION_MODE"] = "enforce"
        self.write_policy(
            """
[[rules]]
id = "fixture.owner-liveness"
products = ["codex", "claude"]
events = ["PreToolUse"]
matcher = "Bash"
priority = 30
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = { id = "agent-session.owner-liveness.v1", reason_code = "foreign-writer-liveness", legacy_ttl_seconds = 300 }
"""
        )
        checkout = self.root / "checkout"
        checkout.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(checkout)],
            check=True,
            capture_output=True,
            text=True,
        )

        cases = [
            ("active", False, "block"),
            ("stale", False, "allow"),
            ("orphaned", False, "warn"),
            ("stale", True, "block"),
            ("orphaned", True, "block"),
        ]
        for broker_state, dirty, expected in cases:
            with self.subTest(broker_state=broker_state, dirty=dirty):
                dirty_path = checkout / "dirty.txt"
                if dirty:
                    dirty_path.write_text("dirty\n", encoding="utf-8")
                else:
                    dirty_path.unlink(missing_ok=True)
                self.write_owner_registry(checkout, broker_state=broker_state)
                decision = self.json_result(
                    self.run_hook(
                        "dispatch",
                        "--product",
                        "codex",
                        "--format",
                        "json",
                        payload={
                            "hook_event_name": "PreToolUse",
                            "tool_name": "Bash",
                            "cwd": str(checkout),
                        },
                        check=expected != "block",
                    )
                )
                self.assertEqual(decision["action"], expected)

        unknown = self.json_result(
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--format",
                "json",
                payload={"hook_event_name": "PreToolUse", "tool_name": "Bash"},
                check=False,
            )
        )
        self.assertEqual(unknown["action"], "block")

    def test_shadow_trace_latency_budget(self) -> None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(self.root),
            "tool_input": {"command": "git status --short"},
        }
        for _ in range(5):
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--shadow",
                "--trace",
                "--format",
                "json",
                payload=payload,
            )
        samples = []
        for _ in range(LATENCY_ITERATIONS):
            started = time.perf_counter()
            self.run_hook(
                "dispatch",
                "--product",
                "codex",
                "--shadow",
                "--trace",
                "--format",
                "json",
                payload=payload,
            )
            samples.append((time.perf_counter() - started) * 1000)
        ordered = sorted(samples)
        p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
        report = {
            "schema_version": "agent-runtime-kit.agent-hook-latency.v1",
            "iterations": len(samples),
            "min_ms": round(min(samples), 3),
            "p50_ms": round(statistics.median(samples), 3),
            "p95_ms": round(p95, 3),
            "max_ms": round(max(samples), 3),
            "budget_ms": LATENCY_BUDGET_MS,
            "product": "codex",
            "event": "PreToolUse",
            "matcher": "Bash",
            "mode": "shadow",
            "trace": True,
        }
        if report_path := os.environ.get("AGENT_HOOK_LATENCY_REPORT"):
            destination = Path(report_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        self.assertLessEqual(p95, LATENCY_BUDGET_MS, report)

    def install_fixture_handler(self, product: str, handler: str, output: str) -> None:
        if product == "codex":
            root = self.root / "codex-home/hooks"
            self.env["CODEX_HOME"] = str(self.root / "codex-home")
        else:
            root = self.home / ".claude/hooks"
        root.mkdir(parents=True, exist_ok=True)
        suffix = ".sh" if handler == "user-prompt-agent-docs" else ".py"
        path = root / f"{handler}{suffix}"
        if suffix == ".sh":
            content = f"#!/usr/bin/env bash\nprintf '%s\\n' {json.dumps(output)}\n"
        else:
            content = (
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "_ = sys.stdin.buffer.read()\n"
                f"print({output!r})\n"
            )
        path.write_text(content, encoding="utf-8")
        path.chmod(0o700)

    def write_coordination_registry(
        self, *, peer_fresh: bool, same_reference: bool
    ) -> None:
        now = datetime.now(UTC)
        now_epoch = int(now.timestamp())
        expires = now + timedelta(minutes=5)
        provider = {"kind": "issue", "repository": "graysurf/agent-runtime-kit", "number": 686}
        peer_provider = (
            provider
            if same_reference
            else {"kind": "issue", "repository": "example/other", "number": 999}
        )

        def broker(session: str, incarnation: str, heartbeat: int) -> dict[str, Any]:
            heartbeat_path = (
                self.session_state
                / "sessions"
                / session
                / "coordination/heartbeat"
            )
            heartbeat_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            heartbeat_path.write_text(
                f"{incarnation}:{heartbeat}\n", encoding="utf-8"
            )
            heartbeat_path.chmod(0o600)
            return {
                "session_id": session,
                "incarnation": incarnation,
                "capability_digest": sha256_bytes(f"{session}-capability".encode()),
                "generation": 1,
                "state": "ready",
                "heartbeat_at": now.isoformat().replace("+00:00", "Z"),
                "heartbeat_epoch": heartbeat,
                "coordination_mode": "enforce",
                "runtime_identity_digest": sha256_bytes(f"{session}-runtime".encode()),
            }

        def claim(
            session: str, incarnation: str, reference: dict[str, Any]
        ) -> dict[str, Any]:
            return {
                "schema_version": "agent-session.work-context.v1",
                "session_id": session,
                "session_incarnation": incarnation,
                "claim_id": f"claim-{session}",
                "revision": 1,
                "state": "active",
                "intent": "project-dev",
                "tier": "L3",
                "repositories": [reference["repository"]],
                "worktrees": [],
                "provider_refs": [reference],
                "plan_refs": [],
                "scopes": [],
                "summary": "fixture",
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "expires_at": expires.isoformat().replace("+00:00", "Z"),
                "expires_at_epoch": int(expires.timestamp()),
            }

        registry = {
            "schema_version": "agent-session.coordination-registry.v1",
            "fingerprint_epoch": 1,
            "fingerprint_key": "fixture-fingerprint-key-32-bytes-minimum",
            "brokers": {
                "fixture-current": broker(
                    "fixture-current", "incarnation-current", now_epoch
                ),
                "fixture-peer": broker(
                    "fixture-peer",
                    "incarnation-peer",
                    now_epoch if peer_fresh else now_epoch - 300,
                ),
            },
            "claims": [
                claim("fixture-current", "incarnation-current", provider),
                claim("fixture-peer", "incarnation-peer", peer_provider),
            ],
            "operations": [],
            "completion_events": [],
            "messages": [],
            "cursors": {},
            "receipts": {},
            "notifications": {},
        }
        target = self.session_state / "coordination/registry.json"
        target.parent.mkdir(mode=0o700, exist_ok=True)
        target.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        target.chmod(0o600)

    def write_owner_registry(self, checkout: Path, *, broker_state: str) -> None:
        now = datetime.now(UTC)
        now_epoch = int(now.timestamp())
        expires = now + timedelta(minutes=5)
        key = b"fixture-fingerprint-key-32-bytes-minimum"
        digest = hmac.new(key, os.fsencode(checkout.resolve()), hashlib.sha256).hexdigest()
        fingerprint = f"hmac-sha256:1:{digest}"
        brokers: dict[str, Any] = {}
        if broker_state != "orphaned":
            heartbeat = now_epoch if broker_state == "active" else now_epoch - 300
            brokers["fixture-peer"] = {
                "session_id": "fixture-peer",
                "incarnation": "incarnation-peer",
                "capability_digest": sha256_bytes(b"peer-capability"),
                "generation": 1,
                "state": "ready",
                "heartbeat_at": now.isoformat().replace("+00:00", "Z"),
                "heartbeat_epoch": heartbeat,
                "coordination_mode": "enforce",
                "runtime_identity_digest": sha256_bytes(b"peer-runtime"),
            }
            heartbeat_path = (
                self.session_state
                / "sessions/fixture-peer/coordination/heartbeat"
            )
            heartbeat_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            heartbeat_path.write_text(
                f"incarnation-peer:{heartbeat}\n", encoding="utf-8"
            )
            heartbeat_path.chmod(0o600)
        claim = {
            "schema_version": "agent-session.work-context.v1",
            "session_id": "fixture-peer",
            "session_incarnation": "incarnation-peer",
            "claim_id": "claim-fixture-peer",
            "revision": 1,
            "state": "active",
            "intent": "project-dev",
            "tier": "L3",
            "repositories": ["graysurf/agent-runtime-kit"],
            "worktrees": [fingerprint],
            "provider_refs": [],
            "plan_refs": [],
            "scopes": [],
            "summary": "fixture",
            "updated_at": now.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "expires_at_epoch": int(expires.timestamp()),
        }
        registry = {
            "schema_version": "agent-session.coordination-registry.v1",
            "fingerprint_epoch": 1,
            "fingerprint_key": key.decode(),
            "brokers": brokers,
            "claims": [claim],
            "operations": [],
            "completion_events": [],
            "messages": [],
            "cursors": {},
            "receipts": {},
            "notifications": {},
        }
        target = self.session_state / "coordination/registry.json"
        target.parent.mkdir(mode=0o700, exist_ok=True)
        target.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        target.chmod(0o600)


if __name__ == "__main__":
    unittest.main()
