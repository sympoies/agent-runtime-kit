#!/usr/bin/env python3
"""Executable consumer tests for the coupled agent-hook implementation."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import shlex
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = Path(
    os.environ.get(
        "AGENT_HOOK_POLICY",
        REPO_ROOT / "core/policies/agent-hook/runtime-kit-v1.toml",
    )
)
DISPATCH_CASES = REPO_ROOT / "tests/agent-hook/fixtures/dispatcher-cases.json"
LATENCY_BUDGET_MS = 25.0
LATENCY_ITERATIONS = 35
LATENCY_HARD_GATE_ENV = "AGENT_HOOK_ENFORCE_LATENCY_BUDGET"


def boolean_environment_value(
    environ: Mapping[str, str], name: str
) -> bool:
    value = environ.get(name)
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"", "0", "false", "no", "off"}:
        return False
    raise RuntimeError(
        f"{name} must be a boolean value, got {value!r}"
    )


def latency_budget_is_hard(environ: Mapping[str, str]) -> bool:
    return boolean_environment_value(
        environ, "CI"
    ) or boolean_environment_value(environ, LATENCY_HARD_GATE_ENV)


def default_test_output_root() -> Path:
    command = [
        "agent-out",
        "project",
        "--topic",
        "agent-hook-tests-direct",
        "--repo",
        str(REPO_ROOT),
        "--mkdir",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"agent-hook test output allocation failed: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "no stderr"
        raise RuntimeError(
            f"agent-hook test output allocation failed ({result.returncode}): {detail}"
        )
    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(paths) != 1:
        raise RuntimeError(
            "agent-hook test output allocation returned "
            f"{len(paths)} paths; expected exactly one"
        )
    output_root = Path(paths[0]).expanduser()
    if not output_root.is_absolute():
        raise RuntimeError(
            f"agent-hook test output allocation returned a relative path: {output_root}"
        )
    return output_root


def validate_test_output_root(
    output_root: Path, repo_root: Path = REPO_ROOT
) -> Path:
    lexical_repo_root = Path(os.path.abspath(repo_root.expanduser()))
    lexical_output_root = Path(os.path.abspath(output_root.expanduser()))
    try:
        lexical_output_root.relative_to(lexical_repo_root)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            "agent-hook test output root must not use a repository path: "
            f"{lexical_output_root}"
        )

    resolved_output_root = lexical_output_root.resolve()
    try:
        resolved_output_root.relative_to(lexical_repo_root.resolve())
    except ValueError:
        return resolved_output_root
    raise RuntimeError(
        "agent-hook test output root must resolve outside repository: "
        f"{resolved_output_root}"
    )


configured_test_output_root = os.environ.get("AGENT_HOOK_TEST_OUTPUT_ROOT")
if configured_test_output_root:
    candidate_test_output_root = Path(configured_test_output_root).expanduser()
    if not candidate_test_output_root.is_absolute():
        raise RuntimeError(
            "AGENT_HOOK_TEST_OUTPUT_ROOT must be an absolute path: "
            f"{candidate_test_output_root}"
        )
    TEMP_ROOT = validate_test_output_root(candidate_test_output_root)
else:
    TEMP_ROOT = validate_test_output_root(default_test_output_root())


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

    def test_output_root_is_outside_repository(self) -> None:
        try:
            TEMP_ROOT.relative_to(REPO_ROOT)
        except ValueError:
            return
        self.fail(f"agent-hook test output root is inside repository: {TEMP_ROOT}")

    def test_inside_repository_output_override_fails_before_creation(self) -> None:
        repo_agent_out = REPO_ROOT / "agent-out"
        inside_root = repo_agent_out / "test-agent-hook-inside-override"
        self.assertFalse(repo_agent_out.exists() or repo_agent_out.is_symlink())
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "AgentHookExecutableContractTests.test_output_root_is_outside_repository",
            ],
            cwd=REPO_ROOT,
            env={
                **os.environ,
                "AGENT_HOOK_BIN": str(self.binary),
                "AGENT_HOOK_TEST_OUTPUT_ROOT": str(inside_root),
            },
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "agent-hook test output root must not use a repository path",
            result.stderr,
        )
        self.assertFalse(inside_root.exists())
        self.assertFalse(repo_agent_out.exists() or repo_agent_out.is_symlink())

    def test_lexical_repo_symlink_escape_is_rejected(self) -> None:
        synthetic_root = self.root / "synthetic"
        synthetic_repo = synthetic_root / "repo"
        external_root = synthetic_root / "external-agent-out"
        synthetic_repo.mkdir(parents=True)
        external_root.mkdir()
        repo_agent_out = synthetic_repo / "agent-out"
        repo_agent_out.symlink_to(external_root, target_is_directory=True)
        inside_root = repo_agent_out / "test-agent-hook-symlink-escape"

        with self.assertRaisesRegex(
            RuntimeError,
            "agent-hook test output root must not use a repository path",
        ):
            validate_test_output_root(inside_root, repo_root=synthetic_repo)

        self.assertFalse((external_root / inside_root.name).exists())

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
            "CODEX_HOME": str(self.home / ".codex"),
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
        env: Mapping[str, str] | None = None,
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
            env=self.env if env is None else env,
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
        self.assertEqual(validated["rule_count"], 100)

        inventory = self.json_result(self.run_hook("inventory", "--format", "json"))
        self.assertEqual(inventory["schema_version"], "agent-hook.inventory.v1")
        self.assertEqual(len(inventory["rules"]), 100)
        self.assertEqual(len({rule["id"] for rule in inventory["rules"]}), 100)

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
                self.assertEqual(decision["action"], "allow", decision)
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
        self.assertEqual(len(decision["shadow"]), 19)
        self.assertEqual(after, before)

    def test_read_only_capability_shadow_is_product_parity_evidence_only(self) -> None:
        agent_docs = self.binary.with_name("agent-docs")
        cases = (
            (
                "managed-query",
                " ".join(
                    (
                        "builtin command",
                        str(agent_docs),
                        "--docs-home",
                        str(REPO_ROOT),
                        "--project-path",
                        str(REPO_ROOT),
                        "preflight --intent project-dev --format json",
                    )
                ),
                "allow",
                "read-only-capability",
            ),
            (
                "mutation",
                "printf changed > tracked.txt",
                "block",
                "read-only-command-unsupported",
            ),
            (
                "unknown",
                "echo unsupported",
                "block",
                "read-only-command-unsupported",
            ),
        )
        for case_name, command, expected_action, expected_code in cases:
            decisions = []
            for product in ("codex", "claude"):
                decision = self.json_result(
                    self.run_hook(
                        "dispatch",
                        "--product",
                        product,
                        "--shadow",
                        "--format",
                        "json",
                        payload={
                            "hook_event_name": "PreToolUse",
                            "tool_name": "Bash",
                            "cwd": str(REPO_ROOT),
                            "tool_input": {"command": command},
                        },
                    )
                )
                evidence = [
                    row
                    for row in decision["shadow"]
                    if row["rule_id"] == "runtime.shared.pre-tool-use.bash.read-only-shadow"
                ]
                self.assertEqual(len(evidence), 1, (case_name, product, decision))
                self.assertEqual(evidence[0]["action"], expected_action)
                self.assertEqual(evidence[0]["code"], expected_code)
                self.assertEqual(decision["action"], "allow")
                decisions.append(evidence[0])
            self.assertEqual(decisions[0], decisions[1], case_name)

    def test_trace_and_output_do_not_retain_private_provider_fields(self) -> None:
        sentinels = [
            "fixture-private-session",
            "fixture-private-mailbox",
            "fixture-private-authorization",
            "fixture-private-token",
            "fixture-private-command-material",
        ]
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(self.root),
            "session_id": sentinels[0],
            "mailbox": sentinels[1],
            "authorization": sentinels[2],
            "token": sentinels[3],
            "tool_input": {"command": sentinels[4]},
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

    def test_runtime_checkpoint_write_reaches_real_product_dispatchers(self) -> None:
        self.env["AGENT_SESSION_COORDINATION_MODE"] = "enforce"
        self.env["AGENT_SESSION_ID"] = "fixture-current"
        self.env["AGENT_SESSION_RUNTIME_ID"] = "incarnation-current"
        session_dir = self.session_state / "sessions" / "fixture-current"
        coordination_dir = session_dir / "coordination"
        coordination_dir.mkdir(mode=0o700)
        session_dir.chmod(0o700)
        capability = coordination_dir / "capability"
        capability.write_text("private-capability\n", encoding="utf-8")
        capability.chmod(0o600)
        checkpoint = coordination_dir / (
            "main-agent-checkpoint-"
            f"{hashlib.sha256(b'incarnation-current').hexdigest()}.json"
        )
        checkpoint.write_text("", encoding="utf-8")
        checkpoint.chmod(0o600)
        self.env["AGENT_SESSION_CAPABILITY_FILE"] = str(capability)
        self.env["AGENT_SESSION_CHECKPOINT_FILE"] = str(checkpoint)
        activity_bin = self.root / "agent-session-activity-fixture"
        activity_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        activity_bin.chmod(0o700)
        self.env["AGENT_SESSION_BIN"] = str(activity_bin)
        self.write_coordination_registry(peer_fresh=False, same_reference=False)
        registry_path = self.session_state / "coordination/registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["brokers"].pop("fixture-peer")
        registry["claims"] = [
            claim
            for claim in registry["claims"]
            if claim["session_id"] == "fixture-current"
        ]
        registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        body = json.dumps(
            {
                "schema_version": "main-agent.checkpoint-input.v1",
                "summary": "aggregate dispatch passed",
                "next_action": "submit",
                "state": "submitted",
            }
        )

        for product, matcher, tool_input in (
            (
                "codex",
                "Bash",
                {
                    "command": (
                        "printf '%s\\n' "
                        f"{shlex.quote(body)} > {shlex.quote(str(checkpoint))}"
                    )
                },
            ),
            (
                "claude",
                "Write",
                {"file_path": str(checkpoint), "content": body + "\n"},
            ),
        ):
            with self.subTest(product=product):
                hook_root = (
                    Path(self.env["CODEX_HOME"]) / "hooks"
                    if product == "codex"
                    else self.home / ".claude/hooks"
                )
                shutil.copytree(
                    REPO_ROOT / "core/hooks/shared",
                    hook_root,
                    dirs_exist_ok=True,
                )
                self.write_config(POLICY)
                payload = {
                    "hook_event_name": "PreToolUse",
                    "tool_name": matcher,
                    "tool_use_id": f"checkpoint-{product}",
                    "cwd": str(REPO_ROOT),
                    "tool_input": tool_input,
                }
                decision = self.json_result(
                    self.run_hook(
                        "dispatch",
                        "--product",
                        product,
                        "--format",
                        "json",
                        payload=payload,
                    )
                )
                self.assertEqual(decision["action"], "allow", decision)
                if matcher == "Bash":
                    subprocess.run(
                        ["bash", "-c", tool_input["command"]],
                        cwd=REPO_ROOT,
                        env=self.env,
                        check=True,
                    )
                else:
                    checkpoint.write_text(tool_input["content"], encoding="utf-8")
                self.assertEqual(json.loads(checkpoint.read_text()), json.loads(body))
                self.assertEqual(stat.S_IMODE(checkpoint.stat().st_mode), 0o600)
                post = self.json_result(
                    self.run_hook(
                        "dispatch",
                        "--product",
                        product,
                        "--format",
                        "json",
                        payload={
                            **payload,
                            "hook_event_name": "PostToolUse",
                            "tool_response": {"ok": True},
                        },
                    )
                )
                self.assertEqual(post["action"], "allow")

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

[[rules]]
id = "fixture.coordination"
products = ["codex", "claude"]
events = ["PreToolUse"]
matcher = "Bash"
priority = 40
mode = "enforce"
failure_posture = "closed"
override_class = "locked"
capability = { id = "agent-session.coordination.v1", reason_code = "coordination" }
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

    def test_unmanaged_shells_bypass_foreign_owner_for_codex_and_claude(self) -> None:
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
        checkout = self.root / "unmanaged-checkout"
        checkout.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(checkout)],
            check=True,
            capture_output=True,
            text=True,
        )
        default_session_state = self.state_home / "agent-session"
        self.write_owner_registry(
            checkout,
            broker_state="active",
            state_root=default_session_state,
        )
        unmanaged_env = {
            name: value
            for name, value in self.env.items()
            if not name.startswith("AGENT_SESSION_")
        }
        unmanaged_env["AGENT_SESSION_BIN"] = "/nonexistent/agent-session"

        for product in ("codex", "claude"):
            with self.subTest(product=product):
                decision = self.json_result(
                    self.run_hook(
                        "dispatch",
                        "--product",
                        product,
                        "--format",
                        "json",
                        payload={
                            "hook_event_name": "PreToolUse",
                            "tool_name": "Bash",
                            "cwd": str(checkout),
                            "tool_input": {"command": "pwd"},
                        },
                        env=unmanaged_env,
                    )
                )
                self.assertEqual(decision["action"], "allow")
                self.assertEqual(
                    [reason["code"] for reason in decision["reasons"]],
                    ["coordination-unmanaged", "coordination-unmanaged"],
                )

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
        hard_gate = latency_budget_is_hard(os.environ)
        exceeded = p95 > LATENCY_BUDGET_MS
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
            "enforcement": "hard" if hard_gate else "advisory",
            "exceeded": exceeded,
        }
        if report_path := os.environ.get("AGENT_HOOK_LATENCY_REPORT"):
            destination = Path(report_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if exceeded and hard_gate:
            self.fail(report)
        if exceeded:
            print(
                "warning: uncontrolled-host agent-hook latency budget "
                f"exceeded: {json.dumps(report, sort_keys=True)}",
                file=sys.stderr,
            )

    def test_latency_budget_hard_gate_is_ci_or_explicit(self) -> None:
        self.assertFalse(latency_budget_is_hard({}))
        self.assertFalse(latency_budget_is_hard({"CI": "false"}))
        self.assertTrue(latency_budget_is_hard({"CI": "true"}))
        self.assertTrue(
            latency_budget_is_hard({LATENCY_HARD_GATE_ENV: "1"})
        )
        with self.assertRaisesRegex(
            RuntimeError, LATENCY_HARD_GATE_ENV
        ):
            latency_budget_is_hard({LATENCY_HARD_GATE_ENV: "sometimes"})

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

    def write_owner_registry(
        self,
        checkout: Path,
        *,
        broker_state: str,
        state_root: Path | None = None,
    ) -> None:
        state_root = self.session_state if state_root is None else state_root
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
                state_root
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
        target = state_root / "coordination/registry.json"
        target.parent.mkdir(mode=0o700, exist_ok=True)
        target.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        target.chmod(0o600)


if __name__ == "__main__":
    unittest.main()
