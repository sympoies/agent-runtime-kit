#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import contextlib
import errno
import hashlib
import importlib.util
import itertools
import json
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

# This runner imports source hooks as modules. Disable bytecode before adding
# their directory to sys.path so direct and focused invocations cannot pollute
# the trusted handler source with __pycache__.
sys.dont_write_bytecode = True


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = REPO_ROOT / "core" / "hooks" / "shared"
DIRTY_ADOPTION_FIXTURE_DIR = (
    REPO_ROOT / "tests" / "hooks" / "fixtures" / "dirty-checkout-adoption"
)
TEST_RUNTIME_STATE = tempfile.TemporaryDirectory(
    prefix="agent-runtime-kit-hook-state-"
)
sys.path.insert(0, str(HOOK_DIR))

import hook_common  # noqa: E402
from hook_common import (  # noqa: E402
    command_matches_validation,
    effective_workdir,
    session_id_from_payload,
)

# Fake agent-session with the released broker's single nonterminal operation
# per session, idempotent admission replay, token-bound completion, and
# two-phase quiescence-proven reconciliation.
SINGLE_SLOT_AGENT_SESSION = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_BROKER_STATE"])
log_path = Path(os.environ["FAKE_BROKER_LOG"])
args = sys.argv[1:]
if args[:1] == ["--state-dir"]:
    args = args[2:]
with log_path.open("a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
NONTERMINAL = {"active", "completing", "reconcile_pending"}


def option(name):
    return args[args.index(name) + 1] if name in args else None


def ok(data):
    print(json.dumps({"ok": True, "data": data}))
    sys.exit(0)


def fail(code):
    print(json.dumps({"ok": False, "error": {"code": code, "message": "synthetic"}}))
    sys.exit(1)


def lease_body(lease_id, lease):
    return {
        "schema_version": "agent-session.operation-lease.v1",
        "lease_id": lease_id,
        "revision": lease["revision"],
        "state": lease["state"],
    }


if args == ["--version"]:
    print("agent-session 1.29.2")
    sys.exit(0)
command = args[:2]
if command == ["work-context", "--help"]:
    print("show check admit complete reconcile")
    sys.exit(0)
if command == ["work-context", "show"]:
    ok({
        "schema_version": "agent-session.work-context.v1",
        "session_id": "managed-session",
        "session_incarnation": "incarnation-1",
        "claim_id": "claim-1",
        "revision": 3,
        "state": "active",
    })
if command == ["work-context", "check"]:
    ok({
        "schema_version": "agent-session.conflict-evaluation.v1",
        "classification": "clear",
        "complete": True,
        "reasons": [],
        "peers": [],
    })
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except FileNotFoundError:
    state = {"leases": {}, "receipts": {}}


def save():
    state_path.write_text(json.dumps(state), encoding="utf-8")


if command == ["broker", "status"]:
    leases = list(state["leases"].values())
    ok({
        "schema_version": "agent-session.coordination-broker.v1",
        "session_id": "managed-session",
        "state": "ready",
        "generation": 1,
        "capability_available": True,
        "heartbeat_fresh": True,
        "claim": None,
        "operation": {
            "active": sum(lease["state"] == "active" for lease in leases),
            "uncertain": sum(
                lease["state"] in {"completing", "reconcile_pending"}
                for lease in leases
            ),
        },
    })
if command == ["work-context", "admit"]:
    key = option("--idempotency-key")
    broker_lost = Path(os.environ["FAKE_BROKER_FLAGS"], "broker-lost")
    if broker_lost.exists():
        # Broker checks run before admit's idempotency lookup.
        broker_lost.unlink()
        fail("coordination-broker-lost")
    if key in state["receipts"]:
        ok(lease_body(state["receipts"][key], {"revision": 1, "state": "active"}))
    if any(lease["state"] in NONTERMINAL for lease in state["leases"].values()):
        fail("coordination-unavailable")
    lease_id = f"lease-{len(state['leases']) + 1}"
    state["leases"][lease_id] = {"revision": 1, "state": "active"}
    state["receipts"][key] = lease_id
    save()
    garble = Path(os.environ["FAKE_BROKER_FLAGS"], "garble-admit")
    if garble.exists():
        garble.unlink()
        print("admission response lost")
        sys.exit(0)
    ok(lease_body(lease_id, state["leases"][lease_id]))
if command in (["work-context", "complete"], ["work-context", "reconcile"]):
    lease_id = option("--lease")
    lease = state["leases"].get(lease_id)
    if lease is None:
        fail("operation-not-found")
    if lease["state"] not in NONTERMINAL or str(lease["revision"]) != option(
        "--if-revision"
    ):
        fail("operation-revision-conflict")
    if command[1] == "complete":
        outcome = option("--outcome")
    else:
        proof = json.loads(Path(option("--proof-file")).read_text(encoding="utf-8"))
        assert set(proof) == {"schema_version", "execution_token", "outcome"}, proof
        assert proof["schema_version"] == "agent-session.operation-reconcile-proof.v1"
        assert proof["execution_token"].startswith("hook-")
        outcome = proof["outcome"]
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"RECONCILE-PROOF outcome={outcome}\n")
        if os.environ.get("FAKE_BROKER_QUIESCENT") != "1":
            fail("operation-still-running")
        if lease["state"] != "reconcile_pending":
            lease.update(state="reconcile_pending", revision=lease["revision"] + 1)
            save()
            ok(lease_body(lease_id, lease))
        # The real CLI needs a second observation five seconds later.
        if not Path(os.environ["FAKE_BROKER_FLAGS"], "reconcile-ready").exists():
            fail("operation-reconcile-pending")
    lease.update(
        state="completed" if outcome == "pass" else "failed",
        revision=lease["revision"] + 1,
    )
    save()
    ok(lease_body(lease_id, lease))
sys.exit(64)
'''


def parse_stdout(stdout: str) -> dict[str, object] | None:
    stripped = stdout.strip()
    if not stripped:
        return None
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise AssertionError(f"hook stdout was not a JSON object: {stdout!r}")
    return parsed


def snapshot_repository_content(repo: Path) -> dict[str, bytes]:
    """Capture working-tree file content without private Git metadata."""
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }


def load_claude_hook_fragment() -> dict[str, Any]:
    text = (
        REPO_ROOT / "core" / "hooks" / "claude" / "settings.hooks.jsonc"
    ).read_text(encoding="utf-8")
    cleaned = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )
    parsed = json.loads("{\n" + cleaned + "\n}")
    if not isinstance(parsed, dict):
        raise AssertionError("Claude hook fragment did not parse as a JSON object")
    return parsed


def load_hook_inventory() -> list[dict[str, Any]]:
    document = json.loads(
        (REPO_ROOT / "manifests" / "hook-rules.yaml").read_text(encoding="utf-8")
    )
    return document["rules"]


def inventory_rules(
    *,
    product: str | None = None,
    event: str | None = None,
    handler: str | None = None,
    capability: str | None = None,
) -> list[dict[str, Any]]:
    selected = []
    for rule in load_hook_inventory():
        if product is not None and product not in rule["products"]:
            continue
        if event is not None and event not in rule["events"]:
            continue
        if handler is not None and rule["legacy_handler"] != handler:
            continue
        if capability is not None and rule["capability"]["id"] != capability:
            continue
        selected.append(rule)
    return selected


def inventory_tools(rules: list[dict[str, Any]]) -> set[str]:
    return {
        tool
        for rule in rules
        for tool in (rule["matcher"] or "").split("|")
        if tool
    }


def prepare_trusted_test_agent_docs(
    full_env: dict[str, str],
    cwd: Path | None,
) -> tempfile.TemporaryDirectory[str] | None:
    if "AGENT_RUNTIME_TRUSTED_CLI_ROOT" in full_env:
        return None
    agent_docs = shutil.which("agent-docs", path=full_env.get("PATH"))
    if not agent_docs:
        return None
    if cwd is not None:
        try:
            Path(agent_docs).resolve().relative_to(cwd.resolve())
        except ValueError:
            # The hook validates the lexical command path against configured
            # trusted roots before resolving a Homebrew Cellar symlink.
            full_env["AGENT_RUNTIME_TRUSTED_CLI_ROOT"] = str(
                Path(agent_docs).absolute().parent
            )
            return None
    trusted = tempfile.TemporaryDirectory()
    trusted_binary = Path(trusted.name) / "agent-docs"
    shutil.copy2(agent_docs, trusted_binary)
    trusted_binary.chmod(0o755)
    full_env["AGENT_RUNTIME_TRUSTED_CLI_ROOT"] = trusted.name
    full_env["PATH"] = trusted.name + os.pathsep + full_env.get("PATH", "")
    return trusted


# Finish-line waiver/suppress envs (mirror WAIVER_ENVS + SUPPRESS_ENVS in
# stop-finish-line-gate.py). The live agent runtime commonly exports these in
# the session, so scrub them from the inherited environment before launching a
# hook subprocess; a test that exercises the waiver/suppress path re-supplies
# the env explicitly via `env=`, which is applied after the scrub.
AMBIENT_GATE_ENVS = (
    "AGENT_RUNTIME_VALIDATION_WAIVER",
    "AGENT_KIT_VALIDATION_WAIVER",
    "CLAUDE_KIT_VALIDATION_WAIVER",
    "AGENT_RUNTIME_SUPPRESS_FINISH_GATE",
    "AGENT_KIT_SUPPRESS_FINISH_GATE",
    "CLAUDE_KIT_SUPPRESS_FINISH_GATE",
)


# Operator-facing trust overrides. Kept apart from AMBIENT_GATE_ENVS because
# that tuple mirrors a specific hook's env list; this one does not. A developer
# on a split nils-cli install legitimately exports the trusted CLI root, but
# prepare_trusted_test_agent_docs cannot tell that inherited value apart from a
# fixture-supplied one and skips installing the per-fixture trusted root, so
# every fixture's temporary agent-docs fails closed as untrusted.
AMBIENT_TRUST_ENVS = ("AGENT_RUNTIME_TRUSTED_CLI_ROOT",)


def scrub_ambient_envs(full_env: dict[str, str]) -> None:
    for name in AMBIENT_GATE_ENVS + AMBIENT_TRUST_ENVS:
        full_env.pop(name, None)
    for name in ("FORGE_IDENTITY_PRINCIPAL", "AGENT_SESSION_RUNTIME_ID",
                 "AGENT_SESSION_CAPABILITY_FILE"):
        full_env.pop(name, None)


def gate_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Inherited environment with the gate's own ambient switches removed.

    A test that spawns a gate with a bare ``**os.environ`` is not testing the
    gate, it is testing whatever the developer happens to export: the finish-line
    gate reads AMBIENT_GATE_ENVS, so an operator who has
    `AGENT_RUNTIME_VALIDATION_WAIVER` set in their shell makes the gate take its
    waiver branch and the assertion fails deterministically -- locally and in
    every pre-push hook, while CI stays green.
    """
    full_env = dict(os.environ)
    scrub_ambient_envs(full_env)
    if overrides:
        full_env.update(overrides)
    return full_env


def run_controller(
    arguments: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke the out-of-band validation recovery controller.

    The lane exists precisely for a session whose `PreToolUse` is failing
    closed, so it is never reached through a provider hook.
    """
    full_env = dict(os.environ)
    full_env.pop("AGENT_SESSION_ID", None)
    scrub_ambient_envs(full_env)
    full_env["PYTHONPATH"] = str(HOOK_DIR)
    full_env["PYTHONDONTWRITEBYTECODE"] = "1"
    full_env.setdefault("AGENT_RUNTIME_STATE_HOME", TEST_RUNTIME_STATE.name)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validation-recovery.py"),
         *arguments, "--format", "json"],
        capture_output=True,
        text=True,
        env=full_env,
    )

def run_hook(
    script_name: str,
    payload: dict[str, Any],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    unset_env: tuple[str, ...] = (),
    dont_write_bytecode: bool = True,
) -> tuple[int, dict[str, object] | None, str]:
    full_env = dict(os.environ)
    # Tests model an unmanaged launch unless the fixture explicitly supplies a
    # managed session identity. Do not inherit the runner's managed identity.
    full_env.pop("AGENT_SESSION_ID", None)
    scrub_ambient_envs(full_env)
    full_env["PYTHONPATH"] = str(HOOK_DIR)
    if dont_write_bytecode:
        full_env["PYTHONDONTWRITEBYTECODE"] = "1"
    else:
        full_env.pop("PYTHONDONTWRITEBYTECODE", None)
    state_overrides = {
        "AGENT_RUNTIME_STATE_HOME",
        "CODEX_AGENT_STATE_HOME",
        "CLAUDE_KIT_STATE_HOME",
    }
    if not env or state_overrides.isdisjoint(env):
        full_env["AGENT_RUNTIME_STATE_HOME"] = TEST_RUNTIME_STATE.name
    # Existing strict project-dev fixtures test the enforce contract. Keep that
    # partition explicit now that production defaults to advisory; default-mode
    # tests pass an empty value, which deterministically selects advisory.
    if script_name == "pre-edit-intent-gate.py":
        full_env["AGENT_RUNTIME_PROJECT_DEV_MODE"] = "enforce"
    if env:
        full_env.update(env)
    for name in unset_env:
        full_env.pop(name, None)
    payload_for_hook = payload
    if (
        script_name == "pre-edit-intent-gate.py"
        and cwd is not None
        and payload.get("tool_name") == "Bash"
        and "transcript_path" not in payload
        and "cwd" not in payload
    ):
        tool_input = payload.get("tool_input")
        if isinstance(tool_input, dict) and not any(
            key in tool_input
            for key in (
                "workdir",
                "cwd",
                "current_working_directory",
                "working_directory",
            )
        ):
            # Model the host-attested per-call workdir that real hooked Bash
            # envelopes carry, without mutating the caller's fixture object.
            payload_for_hook = dict(payload)
            payload_for_hook["tool_input"] = {
                **tool_input,
                "workdir": str(cwd.resolve()),
            }
    trusted = prepare_trusted_test_agent_docs(full_env, cwd)
    try:
        completed = subprocess.run(
            [sys.executable, str(HOOK_DIR / script_name)],
            input=json.dumps(payload_for_hook),
            capture_output=True,
            text=True,
            cwd=cwd,
            env=full_env,
            check=False,
        )
    finally:
        if trusted is not None:
            trusted.cleanup()
    return completed.returncode, parse_stdout(completed.stdout), completed.stderr


def run_enforced_hook(
    script_name: str,
    payload: dict[str, Any],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    dont_write_bytecode: bool = True,
) -> tuple[int, dict[str, object] | None, str]:
    """Run a legacy strict-coordination fixture with explicit enforce mode."""
    enforced_env = dict(env or {})
    enforced_env.setdefault("AGENT_SESSION_COORDINATION_MODE", "enforce")
    return run_hook(
        script_name,
        payload,
        cwd=cwd,
        env=enforced_env,
        dont_write_bytecode=dont_write_bytecode,
    )


def run_shell_hook(
    script_name: str,
    payload: dict[str, Any],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, dict[str, object] | None, str]:
    """Run a shell (bash) shared hook; mirrors run_hook for `.sh` hooks."""
    full_env = dict(os.environ)
    full_env.pop("AGENT_SESSION_ID", None)
    scrub_ambient_envs(full_env)
    if env:
        full_env.update(env)
    trusted = prepare_trusted_test_agent_docs(full_env, cwd)
    try:
        completed = subprocess.run(
            ["bash", str(HOOK_DIR / script_name)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=cwd,
            env=full_env,
            check=False,
        )
    finally:
        if trusted is not None:
            trusted.cleanup()
    return completed.returncode, parse_stdout(completed.stdout), completed.stderr


def command_payload(command: str, **tool_input: str) -> dict[str, Any]:
    return {"tool_name": "Bash", "tool_input": {"command": command, **tool_input}}


def command_event_payload(
    event: str,
    command: str,
    *,
    tool_response: Any | None = None,
    tool_use_id: str = "validation-tool-1",
    **tool_input: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "hook_event_name": event,
        "tool_name": "Bash",
        "tool_use_id": tool_use_id,
        "tool_input": {"command": command, **tool_input},
    }
    if tool_response is not None:
        payload["tool_response"] = tool_response
    return payload


def write_payload(path: str, content: str) -> dict[str, Any]:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def codex_link_map_hook_body() -> str:
    lines = (REPO_ROOT / "targets" / "codex" / "link-map.yaml").read_text(
        encoding="utf-8"
    ).splitlines()
    in_codex_config = False
    in_body = False
    body: list[str] = []
    for line in lines:
        if line == "  - id: hooks.codex-config":
            in_codex_config = True
            continue
        if in_codex_config and line == "    body_template: |-":
            in_body = True
            continue
        if in_body:
            if line.startswith("  - id: "):
                break
            body.append(line[6:] if line.startswith("      ") else line)
    return "\n".join(body).rstrip() + "\n"


class HookTestCase(unittest.TestCase):

    def assert_blocked(self, decision: dict[str, object] | None, fragment: str) -> None:
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertEqual(decision.get("decision"), "block")
        self.assertIn(fragment, str(decision.get("reason", "")))


    def assert_allowed(self, decision: dict[str, object] | None) -> None:
        self.assertIsNone(decision)


    def assert_unprovable_validation_advisory(
        self, decision: dict[str, object] | None
    ) -> str:
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertEqual(set(decision), {"systemMessage"})
        message = str(decision.get("systemMessage", ""))
        self.assertEqual(message.count("validation_outcome_unprovable"), 1)
        self.assertIn("will not satisfy the finish-line gate", message)
        return message


    def _require_agent_docs(self) -> None:
        if shutil.which("agent-docs") is None:
            self.skipTest("agent-docs not on PATH")


    @staticmethod
    def _init_contract_repo(
        tmp: str,
        commands: tuple[str, ...] = ("bash scripts/ci/all.sh",),
        marker: str = ".cache/agent-validation/project-dev.ok",
    ) -> Path:
        repo = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        rendered = ", ".join(f'"{command}"' for command in commands)
        (repo / "AGENT_DOCS.toml").write_text(
            '[[validation]]\ncontext = "project-dev"\n'
            f"commands = [{rendered}]\n"
            f'marker = "{marker}"\n',
            encoding="utf-8",
        )
        return repo


    @staticmethod
    def _snapshot_outside_repo(root: Path, repo: Path) -> dict[str, object]:
        """Capture every sibling artifact, including type, content, and mtime."""
        snapshot: dict[str, object] = {}
        lexical_repo = repo.absolute()
        for path in sorted(root.rglob("*")):
            try:
                path.absolute().relative_to(lexical_repo)
            except ValueError:
                pass
            else:
                continue
            relative = str(path.relative_to(root))
            metadata = path.lstat()
            if path.is_symlink():
                payload: object = ("symlink", os.readlink(path))
            elif path.is_file():
                payload = ("file", path.read_bytes())
            elif path.is_dir():
                payload = ("directory",)
            else:
                payload = ("other",)
            snapshot[relative] = (
                metadata.st_mode,
                metadata.st_size,
                metadata.st_mtime_ns,
                payload,
            )
        return snapshot


    @staticmethod
    def _write_fake_agent_docs(bin_dir: Path, body: str) -> None:
        script = bin_dir / "agent-docs"
        script.write_text(body, encoding="utf-8")
        script.chmod(0o755)


    @staticmethod
    def _phase_aware_fake_agent_docs(
        *,
        log_path: Path,
        marker: Path,
        product: str = "codex",
        prepared_intent: str = "project-dev",
    ) -> str:
        """Fake agent-docs that records argv and models the #601 3d phase surface.

        ``session verify`` reports the intent active once ``marker`` exists
        (modeling the primitive rule that a full, no-phase preparation satisfies
        any phase-scoped verify), and ``session prepare`` succeeds and creates the marker. Every
        invocation appends ``$*`` to ``log_path`` so a test can assert which
        ``--phase`` the hook threaded into each call.
        """
        log_q = shlex.quote(str(log_path))
        marker_q = shlex.quote(str(marker))
        return f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> {log_q}
if [[ "$*" == *"session prepare"* ]]; then
  printf 'prepared\\n' > {marker_q}
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.prepare.v1","ok":true,"data":{{"product":"{product}","active_intents":["{prepared_intent}"],"record_file":"r.json","verified":true,"prepared_intents":["{prepared_intent}"],"reason":"prepared"}}}}'
  exit 0
fi
if [[ "$*" == *"session verify"* ]]; then
  if [[ -f {marker_q} ]]; then
    printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":true,"data":{{"product":"{product}","active_intents":["project-dev"],"verified":true}}}}'
    exit 0
  fi
  printf '%s\\n' '{{"schema_version":"cli.agent-docs.session.verify.v1","ok":false,"error":{{"code":"required-intent-not-active"}}}}'
  exit 1
fi
exit 64
"""


    def _run_declared_validation(
        self,
        repo: Path,
        command: str,
        *,
        env: dict[str, str],
        session_id: str | None = None,
    ) -> None:
        """Credit a declared validation the way provider wiring does.

        The PreToolUse hook rewrites the command into its outcome wrapper, and
        running that wrapper records the observed exit status. A missing
        ``bash <script>`` target is stubbed to succeed so the fixture models a
        passing validation.
        """
        words = shlex.split(command)
        if len(words) == 2 and words[0] == "bash":
            script = repo / words[1]
            if not script.exists():
                script.parent.mkdir(parents=True, exist_ok=True)
                script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                script.chmod(0o755)
        payload = command_event_payload(
            "PreToolUse",
            command,
            tool_use_id=f"declared-validation-{secrets.token_hex(4)}",
        )
        if session_id is not None:
            payload["session_id"] = session_id
        code, rewrite, stderr = run_hook(
            "finish-line-record.py", payload, cwd=repo, env=env
        )
        self.assertEqual(code, 0, stderr)
        assert rewrite is not None, stderr
        hook_output = rewrite["hookSpecificOutput"]
        assert isinstance(hook_output, dict)
        updated_input = hook_output["updatedInput"]
        assert isinstance(updated_input, dict)
        completed = subprocess.run(
            ["bash", "-c", str(updated_input["command"])],
            cwd=repo,
            env=gate_env(env),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


    @staticmethod
    def _mark_runtime_kit_source_checkout(repo: Path) -> None:
        (repo / "AGENT_HOME.md").write_text("# Home\n", encoding="utf-8")
        (repo / "manifests").mkdir(exist_ok=True)
        (repo / "manifests" / "skills.yaml").write_text("skills: []\n", encoding="utf-8")
        (repo / "core" / "policies").mkdir(parents=True, exist_ok=True)
        (repo / "scripts").mkdir(exist_ok=True)
        (repo / "scripts" / "sync-runtime-surfaces.sh").write_text(
            "#!/usr/bin/env bash\n", encoding="utf-8"
        )


    def _phase_gate_env(self, repo: Path, bin_dir: Path) -> dict[str, str]:
        return {
            "AGENT_RUNTIME_DOCS_HOME": str(repo),
            "AGENT_RUNTIME_PRODUCT": "codex",
            "CODEX_AGENT_STATE_HOME": str(repo / "state"),
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }


    @staticmethod
    def _verify_calls(call_log: Path) -> list[str]:
        return [
            line
            for line in call_log.read_text(encoding="utf-8").splitlines()
            if "session verify" in line and "--help" not in line
        ]


    def _pull_request_head_repo(self, root: Path, branch: str = "feat/topic") -> Path:
        repo = root / "repo"
        (repo / "src").mkdir(parents=True)
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch", branch],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "remote",
                "add",
                "origin",
                "https://example.invalid/example/repository.git",
            ],
            cwd=repo,
            check=True,
        )
        return repo


    def single_slot_coordination_fixture(
        self, root: Path
    ) -> tuple[Path, dict[str, str], Path, Path]:
        """Model the released broker's one nonterminal operation per session."""
        repo = root / "repo"
        (repo / "src").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://example.invalid/example/repo.git"],
            cwd=repo,
            check=True,
        )
        bin_dir = root / "bin"
        bin_dir.mkdir()
        agent_session = bin_dir / "agent-session"
        agent_session.write_text(SINGLE_SLOT_AGENT_SESSION, encoding="utf-8")
        agent_session.chmod(0o755)
        capability = root / "capability"
        capability.write_text("secret\n", encoding="utf-8")
        capability.chmod(0o600)
        runtime_state = root / "runtime-state"
        call_log = root / "calls.log"
        env = {
            "AGENT_RUNTIME_PRODUCT": "claude",
            "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(bin_dir),
            "AGENT_RUNTIME_STATE_HOME": str(runtime_state),
            "AGENT_SESSION_ID": "managed-session",
            "AGENT_SESSION_CAPABILITY_FILE": str(capability),
            "AGENT_SESSION_STATE_DIR": str(root / "session-state"),
            "FAKE_BROKER_STATE": str(root / "broker.json"),
            "FAKE_BROKER_LOG": str(call_log),
            "FAKE_BROKER_FLAGS": str(root),
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }
        namespace = runtime_state / "session-coordination" / hashlib.sha256(
            b"managed-session"
        ).hexdigest()
        return repo, env, namespace, call_log


    @staticmethod
    def operation_records(namespace: Path) -> list[dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(namespace.glob("*.json"))
            if not path.name.endswith(".targets.json")
        ]


    @staticmethod
    def edit_event(tool_use_id: str, event: str = "PreToolUse") -> dict[str, Any]:
        payload = write_payload(f"src/{tool_use_id}.rs", "fn main() {}\n")
        payload.update(
            {
                "session_id": "product-session",
                "tool_use_id": tool_use_id,
                "hook_event_name": event,
            }
        )
        if event == "PostToolUse":
            payload["tool_response"] = {"success": True}
        return payload


    @staticmethod
    def _init_checkout_lease_repo(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
        subprocess.run(
            [
                "git",
                "config",
                "core.hooksPath",
                str(path / ".git" / "hooks"),
            ],
            cwd=path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Hook Test"], cwd=path, check=True
        )
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"], cwd=path, check=True
        )
        (path / "README.md").write_text("# lease fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=path, check=True)
        remote = path.parent / f"{path.name}-origin.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "--initial-branch=main", str(remote)],
            check=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote)], cwd=path, check=True
        )
        subprocess.run(["git", "push", "-q", "origin", "main"], cwd=path, check=True)
        subprocess.run(
            [
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main",
            ],
            cwd=path,
            check=True,
        )


    @staticmethod
    def _add_checkout_lease_worktree(primary: Path, branch: str) -> Path:
        linked = primary.parent / f"{primary.name}-{branch.replace('/', '-')}"
        subprocess.run(
            ["git", "worktree", "add", "-q", "-b", branch, str(linked)],
            cwd=primary,
            check=True,
        )
        return linked


    def assert_process_stopped(self, pid: int) -> None:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            status = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(pid)],
                capture_output=True,
                text=True,
                check=False,
            )
            if status.returncode != 0 or status.stdout.lstrip().startswith("Z"):
                return
            time.sleep(0.02)
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            return
        self.fail(f"descendant process {pid} survived GitProbe cleanup")


    @staticmethod
    def _checkout_lease_payload(
        session_id: str,
        path: Path,
        *,
        tool_name: str = "Write",
        command: str = "",
    ) -> dict[str, Any]:
        if tool_name == "Bash":
            tool_input: dict[str, Any] = {"command": command}
        else:
            tool_input = {"file_path": str(path), "content": "updated\n"}
        return {
            "session_id": session_id,
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
        }


    @staticmethod
    def _checkout_lease_files(state: Path) -> list[Path]:
        return list((state / "checkout-leases").rglob("lease.json"))


    @staticmethod
    def _write_adopted_checkout_lease_v2(
        lease_file: Path,
        *,
        expires_offset: int = 60,
        session_key: str | None = None,
    ) -> dict[str, Any]:
        v1 = json.loads(lease_file.read_text(encoding="utf-8"))
        lease = json.loads(
            (
                DIRTY_ADOPTION_FIXTURE_DIR / "checkout-lease-v2.json"
            ).read_text(encoding="utf-8")
        )
        now = int(time.time())
        expires_at = now + expires_offset
        refreshed_at = min(now, expires_at)
        adopted_at = refreshed_at
        root_bytes = os.fsencode(v1["checkout_root"])
        git_dir_bytes = os.fsencode(v1["checkout_git_dir"])
        lease.update(
            {
                "session_key": session_key or v1["session_key"],
                "checkout_instance": v1["checkout_instance"],
                "checkout_root": root_bytes.decode("utf-8", errors="replace"),
                "checkout_git_dir": git_dir_bytes.decode(
                    "utf-8", errors="replace"
                ),
                "checkout_root_bytes": root_bytes.hex(),
                "checkout_git_dir_bytes": git_dir_bytes.hex(),
                "acquired_at": min(int(v1["acquired_at"]), adopted_at),
                "refreshed_at": refreshed_at,
                "expires_at": expires_at,
            }
        )
        lease["adoption"].update(
            {
                "adopted_at": adopted_at,
                "challenge_issued_at": adopted_at,
            }
        )
        lease_file.write_text(
            json.dumps(lease, sort_keys=True) + "\n", encoding="utf-8"
        )
        return lease


    @staticmethod
    def _dirty_adoption_command(advisory: dict[str, object]) -> dict[str, Any]:
        """Parse the advisory's adoption command for either git-cli transport.

        A git-cli that still accepts ``--challenge <bearer>`` receives the
        legacy argv command. A released git-cli that reads the bearer only
        through ``--challenge-fd`` receives the hook's launcher command, which
        takes the bearer on stdin from a here-string.
        """
        hook_output = advisory.get("hookSpecificOutput")
        if not isinstance(hook_output, dict):
            raise AssertionError("dirty adoption advisory omitted hook output")
        context = hook_output.get("additionalContext")
        if not isinstance(context, str):
            raise AssertionError("dirty adoption advisory omitted context")
        legacy = re.search(
            r"`(git-cli worktree adopt-dirty --challenge [^`]*)`", context
        )
        if legacy is not None:
            argv = shlex.split(legacy.group(1))
            return {
                "transport": "argv",
                "argv": argv,
                "token": argv[4],
                "reason_file": Path(argv[6]),
            }
        launcher = re.search(
            r"`([^`]* adopt-dirty --reason-file [^`]* <<< [0-9a-f]{64})`", context
        )
        if launcher is not None:
            words = shlex.split(launcher.group(1))
            if len(words) != 6 or words[1:3] != ["adopt-dirty", "--reason-file"]:
                raise AssertionError("dirty adoption launcher command is malformed")
            return {
                "transport": "fd",
                "argv": words[:4],
                "token": words[5],
                "reason_file": Path(words[3]),
            }
        raise AssertionError("dirty adoption advisory omitted adopt command")


    @staticmethod
    def _dirty_adoption_shell_command(details: dict[str, Any], *extra: str) -> str:
        command = shlex.join([*details["argv"], *extra])
        if details["transport"] == "fd":
            command += f" <<< {details['token']}"
        return command


    @staticmethod
    def _dirty_adoption_launcher_command(
        details: dict[str, Any], launcher: Path | None = None
    ) -> str:
        """Build the launcher-form command for a challenge of either transport."""
        executable = launcher or HOOK_DIR / "checkout-lease-guard.py"
        return (
            shlex.join(
                [
                    str(executable),
                    "adopt-dirty",
                    "--reason-file",
                    str(details["reason_file"]),
                ]
            )
            + f" <<< {details['token']}"
        )


    @staticmethod
    def _invalid_utf8_checkout_path(root: Path, name: bytes = b"repo-\xff") -> Path:
        return Path(os.fsdecode(os.fsencode(root) + os.fsencode(os.sep) + name))


    def _native_non_utf8_checkout_path_or_skip(self, root: Path) -> Path:
        path = self._invalid_utf8_checkout_path(root)
        try:
            path.mkdir()
            path.rmdir()
        except OSError as exc:
            if exc.errno == errno.EILSEQ:
                self.skipTest(
                    "host filesystem/Python rejects native non-UTF-8 path bytes"
                )
            raise
        return path


    def _dirty_snapshot_capability_or_skip(self, repo: Path) -> None:
        if sys.platform != "darwin":
            return
        completed = subprocess.run(
            ["git-cli", "worktree", "dirty-snapshot", "--format=json"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return
        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return
        error = envelope.get("error") if isinstance(envelope, dict) else None
        if (
            isinstance(error, dict)
            and error.get("code") == "dirty-checkout-resource-unavailable"
        ):
            self.skipTest(
                "Darwin kqueue NOTE_TRACK is unavailable for dirty-snapshot "
                "process containment"
            )


    @staticmethod
    def _released_v2_fixture_for_paths(
        checkout_root: Path,
        checkout_git_dir: Path,
        *,
        session_key: str = "2" * 64,
        checkout_instance: str = "c" * 32,
    ) -> dict[str, Any]:
        lease = json.loads(
            (
                DIRTY_ADOPTION_FIXTURE_DIR / "checkout-lease-v2.json"
            ).read_text(encoding="utf-8")
        )
        now = int(time.time())
        root_bytes = os.fsencode(checkout_root)
        git_dir_bytes = os.fsencode(checkout_git_dir)
        lease.update(
            {
                "session_key": session_key,
                "checkout_instance": checkout_instance,
                "checkout_root": root_bytes.decode("utf-8", errors="replace"),
                "checkout_git_dir": git_dir_bytes.decode(
                    "utf-8", errors="replace"
                ),
                "checkout_root_bytes": root_bytes.hex(),
                "checkout_git_dir_bytes": git_dir_bytes.hex(),
                "acquired_at": now,
                "refreshed_at": now,
                "expires_at": now + 60,
            }
        )
        lease["adoption"].update(
            {"adopted_at": now, "challenge_issued_at": now}
        )
        return lease


    @staticmethod
    def _write_challenge_fd_git_cli_stub(bin_dir: Path, record: Path) -> Path:
        """A git-cli stub that records how it received the adoption bearer."""
        bin_dir.mkdir(parents=True, exist_ok=True)
        stub = bin_dir / "git-cli"
        stub.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib, json, os, socket, stat, struct, sys\n"
            "is_socket = stat.S_ISSOCK(os.fstat(0).st_mode)\n"
            "peer_is_parent = None\n"
            "if is_socket and sys.platform.startswith('linux'):\n"
            "    probe = socket.socket(fileno=os.dup(0))\n"
            "    creds = probe.getsockopt(\n"
            "        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')\n"
            "    )\n"
            "    probe.close()\n"
            "    peer_is_parent = struct.unpack('3i', creds)[0] == os.getppid()\n"
            "data = b''\n"
            "while True:\n"
            "    chunk = os.read(0, 256)\n"
            "    if not chunk:\n"
            "        break\n"
            "    data += chunk\n"
            "bearer = data.decode('ascii', 'replace')\n"
            f"with open({str(record)!r}, 'w', encoding='utf-8') as handle:\n"
            "    json.dump({\n"
            "        'argv': sys.argv[1:],\n"
            "        'is_socket': is_socket,\n"
            "        'peer_is_parent': peer_is_parent,\n"
            "        'digest': hashlib.sha256(data).hexdigest(),\n"
            "        'bearer_in_argv': any(bearer in a for a in sys.argv),\n"
            "        'bearer_in_env': any(bearer in v for v in os.environ.values()),\n"
            "    }, handle)\n"
            "print(json.dumps({'ok': True}))\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        return stub


    def _run_dirty_adoption_launcher(
        self,
        arguments: list[str],
        stdin: str,
        bin_dir: Path,
        *,
        trusted: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        if trusted:
            env["AGENT_RUNTIME_TRUSTED_CLI_ROOT"] = str(bin_dir)
        else:
            env.pop("AGENT_RUNTIME_TRUSTED_CLI_ROOT", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [str(HOOK_DIR / "checkout-lease-guard.py"), "adopt-dirty", *arguments],
            input=stdin,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )


    @staticmethod
    def _harness_wrapped(command: str, cwd_sentinel: str) -> str:
        # Reproduce the Claude Bash tool's command wrapper: a shell-snapshot
        # source, setopt, the real command under `eval '…' < /dev/null`, and a
        # trailing cwd-capture `pwd -P >| <sentinel>`. The PreToolUse hook sees
        # this whole string, not the raw command. `cwd_sentinel` is an absolute
        # path outside every checkout (kept under the test tree so the fixture
        # does not depend on /tmp being a non-repo).
        return (
            "source /home/x/.claude/shell-snapshots/snap.sh 2>/dev/null || true && "
            "setopt NO_EXTENDED_GLOB NO_BARE_GLOB_QUAL 2>/dev/null || true && "
            f"eval {shlex.quote(command)} < /dev/null && "
            f"pwd -P >| {shlex.quote(cwd_sentinel)}"
        )



    def _load(self, module_name: str, filename: str):
        import importlib.util

        spec = importlib.util.spec_from_file_location(module_name, HOOK_DIR / filename)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


    @contextlib.contextmanager
    def _managed_cli_home_fixture(self, *, symlinked_ancestor: bool = False):
        """Temporary HOME holding a per-user managed CLI bin and a decoy bin.

        Scoped per test rather than in setUp: this class has no setUp, and
        adding one would retarget HOME for all of its other tests, which breaks
        every fixture that shells out to git.

        With `symlinked_ancestor`, HOME is reached through a symlink, so the
        managed bin's resolved path differs from its lexical one for a reason
        that has nothing to do with the binary. That is the ordinary shape of
        any macOS path under `/var`, and it is what separates "this binary is a
        symlink" from "some parent directory is" (#66).
        """
        saved = {
            key: os.environ.get(key)
            for key in ("HOME", "PATH", "AGENT_RUNTIME_TRUSTED_CLI_ROOT", "AGENT_SESSION_BIN")
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home_bin = root / "home" / ".local" / "nils-cli" / "bin"
            other_bin = root / "elsewhere" / "bin"
            for directory in (home_bin, other_bin):
                directory.mkdir(parents=True)
                for tool in ("semantic-commit", "agent-docs", "agent-session"):
                    binary = directory / tool
                    binary.write_text("#!/bin/sh\nexit 0\n")
                    binary.chmod(0o755)
            if symlinked_ancestor:
                (root / "elsewhere-home").symlink_to(root / "home")
                os.environ["HOME"] = str(root / "elsewhere-home")
                home_bin = root / "elsewhere-home" / ".local" / "nils-cli" / "bin"
            else:
                os.environ["HOME"] = str(root / "home")
            os.environ.pop("AGENT_RUNTIME_TRUSTED_CLI_ROOT", None)
            os.environ.pop("AGENT_SESSION_BIN", None)
            sys.path.insert(0, str(HOOK_DIR))
            # Importing a hook would drop __pycache__ into core/hooks/shared,
            # and the trusted materializer refuses any non-regular file there.
            saved_bytecode = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                yield home_bin, other_bin
            finally:
                sys.dont_write_bytecode = saved_bytecode
                if sys.path and sys.path[0] == str(HOOK_DIR):
                    sys.path.pop(0)
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


    # ---- agent artifact routing (issue #90) ---------------------------------
    #
    # `agent-out` is a command that allocates a run directory outside the
    # checkout; it is never a directory name. Writes to any `agent-out` path
    # segment, and repo-local `.cache/` scratch outside the sanctioned
    # `agent-validation` marker subtree, are blocked with an actionable route.
    #
    # The check is carried by `portable-paths-scan` rather than its own handler:
    # a dispatch group has a hard executable-capability budget and the Bash
    # group was already at it. The two share posture and domain, which is what
    # makes one rule able to express both.

    ARTIFACT_ROUTING_HOOK = "portable-paths-scan.py"


    def _artifact_routing_repo(self, tmp: str) -> Path:
        repo = Path(tmp) / "repo"
        (repo / ".cache" / "agent-validation").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        return repo


    def _artifact_routing_tracked_worktree(self, tmp: str) -> Path:
        primary = Path(tmp) / "primary"
        self._init_checkout_lease_repo(primary)
        for relative in (
            "crates/agent-out/tests/integration/retention.rs",
            "agent-out/tracked-scratch.md",
            ".cache/agent-out/tracked-scratch.md",
        ):
            source = primary / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("tracked fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "--", "crates", "agent-out", ".cache"],
                       cwd=primary, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "tracked source fixture"],
                       cwd=primary, check=True)
        return self._add_checkout_lease_worktree(primary, "fix/tracked-source")

