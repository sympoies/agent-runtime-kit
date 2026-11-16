#!/usr/bin/env python3
"""Consumer acceptance for setup-owned ingress and runtime-kit config sync."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import shlex
import subprocess
import sys
import time
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_SOURCE = REPO_ROOT / "core/policies/agent-hook/runtime-kit-v1.toml"
SYNC = REPO_ROOT / "scripts/sync-runtime-surfaces.sh"
AGENT_HOOK = os.environ["AGENT_HOOK_BIN"]


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


# nils-cli v1.40.11 provider_entrypoint::selector; exact equality matches
# the producer's ownership test and rejects lookalike shell programs.
SELECTOR = """resolve() {
  target=$1; count=0
  directory=$(CDPATH= cd -P "${target%/*}" 2>/dev/null && pwd -P) || return 1
  target=$directory/${target##*/}
  while [ -L "$target" ]; do
    count=$((count + 1)); [ "$count" -le 40 ] || return 1
    link=$(/usr/bin/readlink "$target") || return 1
    case "$link" in /*) target=$link ;; *) target=${target%/*}/$link ;; esac
    directory=$(CDPATH= cd -P "${target%/*}" 2>/dev/null && pwd -P) || return 1
    target=$directory/${target##*/}
  done
  printf '%s' "$target"
}
configured=${AGENT_SESSION_BIN:-}
case "$configured" in /*/agent-session) if [ -f "$configured" ] && [ -x "$configured" ]; then selected=${configured%/*}/{executable}; session_real=$(resolve "$configured") && selected_real=$(resolve "$selected") && [ "${session_real%/*}" = "${selected_real%/*}" ] && [ -f "$selected" ] && [ -x "$selected" ] && exec "$selected" "$@"; exit 127; fi ;; esac
configured_roots=${AGENT_RUNTIME_TRUSTED_CLI_ROOT:-}
roots=${configured_roots:-/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:${HOME:-/nonexistent}/.local/nils-cli/bin}
trusted_default() {
  target=$1; approved=$2
  approved=$(CDPATH= cd -P "$approved" 2>/dev/null && pwd -P) || return 1
  target=$(resolve "$target") || return 1
  case "$approved" in
    /opt/homebrew/bin|/home/linuxbrew/.linuxbrew/bin)
      case "$target" in "$approved/{executable}"|"${approved%/bin}/Cellar/nils-cli/"*) return 0 ;; esac ;;
    *) [ "$target" = "$approved/{executable}" ] && return 0 ;;
  esac
  return 1
}
set -f
old_ifs=$IFS; IFS=:
for root in $roots; do
  case "$root" in /*) selected=$root/{executable}; if [ -f "$selected" ] && [ -x "$selected" ] && { [ -n "$configured_roots" ] || trusted_default "$selected" "$root"; }; then IFS=$old_ifs; exec "$selected" "$@"; fi ;; esac
done
exit 127"""


def selector(executable: str) -> str:
    return SELECTOR.replace("{executable}", executable)


def is_owned_dispatch(command: str, product: str) -> bool:
    # Supported nils-cli v1.36.21 through v1.40.10 use the bare command.
    if command == f"agent-hook dispatch --product {product}":
        return True
    return shlex.split(command) == [
        "/bin/sh", "-c", selector("agent-hook"), "provider-entrypoint",
        "dispatch", "--product", product,
    ]


def is_owned_notify(argv: list[str]) -> bool:
    return argv == [
        "/bin/sh", "-c", selector("agent-session"), "provider-entrypoint",
        "activity", "notify", "--agent", "codex",
    ]


def read_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    document = json.loads(result.stdout)
    if document.get("ok") is not True:
        raise AssertionError(document)
    return document


class AgentHookSetupMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.codex_home = self.home / ".codex"
        self.claude_home = self.home / ".claude"
        self.config_home = self.root / "config"
        self.data_home = self.root / "data"
        self.state_home = self.root / "state"
        self.policy = self.data_home / "agent-hook/policies/runtime-kit-v1.toml"
        self.config = self.config_home / "agent-hook/config.toml"
        self.state = self.state_home / "agent-hook"
        for hook_home in (
            self.codex_home / "hooks",
            self.claude_home / "hooks",
        ):
            hook_home.mkdir(parents=True)
            # Match the installed runtime posture for the directory chain too.
            # A group-writable checkout umask must not make the live runtime-home
            # fixture fail the production owner-controlled-directory guard.
            hook_home.parent.chmod(0o700)
            hook_home.chmod(0o700)
            for handler in sorted((REPO_ROOT / "core/hooks/shared").iterdir()):
                if handler.is_file() and not handler.is_symlink():
                    destination = hook_home / handler.name
                    shutil.copy2(handler, destination)
                    # Match the installed runtime posture: sync-runtime-surfaces
                    # writes handlers 0o700/0o600, and the agent-hook trust check
                    # rejects group/world-writable handlers. Normalize here so the
                    # fixture does not inherit a group-writable working-tree mode
                    # left by a lax checkout umask (git tracks these as 0o755).
                    executable = bool(handler.stat().st_mode & 0o111)
                    destination.chmod(0o700 if executable else 0o600)
        self.policy.parent.mkdir(parents=True)
        shutil.copyfile(POLICY_SOURCE, self.policy)
        self.policy.chmod(0o600)
        digest = hashlib.sha256(self.policy.read_bytes()).hexdigest()
        write_private(
            self.config,
            (
                'schema_version = "agent-hook.config.v1"\n\n'
                "[policy]\n"
                f'path = "{self.policy}"\n'
                f'digest = "sha256:{digest}"\n'
            ),
        )
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "CODEX_HOME": str(self.codex_home),
                "XDG_CONFIG_HOME": str(self.config_home),
                "XDG_DATA_HOME": str(self.data_home),
                "XDG_STATE_HOME": str(self.state_home),
            }
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def agent_hook(
        self,
        *arguments: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                AGENT_HOOK,
                *arguments,
                "--config",
                str(self.config),
                "--state-dir",
                str(self.state),
                "--format",
                "json",
            ],
            env=self.env,
            text=True,
            capture_output=True,
            check=check,
        )

    def setup_preview(self, product: str, *action: str) -> dict[str, Any]:
        return read_json(
            self.agent_hook("setup", "--product", product, *action, "--dry-run")
        )["data"]

    def test_isolated_full_policy_launch_keeps_guards(self) -> None:
        """Real launcher, registered ingress, synthetic provider; no live authority."""
        tmux_bin = shutil.which("tmux")
        self.assertIsNotNone(tmux_bin, "isolated runtime acceptance requires tmux; install it before running the gate")
        cli_root = Path(AGENT_HOOK).resolve().parent
        producer = cli_root / "agent-session"
        self.assertTrue(producer.is_file(), "acceptance needs the released CLI pair")
        cwd = self.root / "synthetic-cwd"
        cwd.mkdir()
        provider_config = self.root / "provider-config"
        provider_config.mkdir()
        # A whitelist, rather than inherited managed identity or provider auth.
        self.env = {
            "HOME": str(self.home), "PATH": str(cli_root) + os.pathsep + os.defpath,
            "SHELL": "/bin/sh", "TERM": "xterm",
            "CLAUDE_CONFIG_DIR": str(provider_config),
            "XDG_CONFIG_HOME": str(self.config_home),
            "XDG_DATA_HOME": str(self.data_home), "XDG_STATE_HOME": str(self.state_home),
            "AGENT_HOME": str(self.root / "runtime"),
            "AGENT_RUNTIME_STATE_HOME": str(self.root / "runtime-state"),
            "AGENT_SESSION_STATE_DIR": str(self.root / "session-state"),
            "AGENT_SESSION_BIN": str(producer),
            "AGENT_RUNTIME_TRUSTED_CLI_ROOT": str(cli_root),
            "TMPDIR": str(self.root), "PYTHONDONTWRITEBYTECODE": "1",
        }
        # Exercise the same bounded handler owner used by the tester recipe.
        # setUp's other tests use direct trusted copies; this profile starts empty.
        shutil.rmtree(self.claude_home / "hooks")
        for apply in (False, True):
            handlers = self.sync_trusted_handlers(
                REPO_ROOT, "claude", self.claude_home, apply=apply,
            )
            self.assertEqual(handlers.returncode, 0, "isolated handler sync failed")
        # Settings and handler roots deliberately differ: CLAUDE_CONFIG_DIR
        # never changes agent-hook's $HOME/.claude/hooks lookup.
        for action in ("--dry-run", "--apply"):
            setup = subprocess.run([
                str(producer), "activity", "setup", "--agent", "claude", action,
                "--format", "json",
            ], env=self.env, capture_output=True, text=True, timeout=30)
            self.assertEqual(setup.returncode, 0, "isolated activity setup failed")
        settings = json.loads((provider_config / "settings.json").read_text())
        prompt_commands = [h["command"] for g in settings["hooks"]["UserPromptSubmit"]
                           for h in g["hooks"] if h["type"] == "command"]
        self.assertEqual(len(prompt_commands), 1)
        tmux = self.root / "fixture-tmux"
        tmux.write_text("#!/bin/sh\nexec " + shlex.join([
            tmux_bin, "-S", str(self.root / "tmux.sock")]) + ' "$@"\n')
        tmux.chmod(0o700)
        provider = self.root / "fixture-claude"
        provider.write_text("#!" + sys.executable + "\n" + r'''
import json, os, pathlib, subprocess, sys, time
root = pathlib.Path(os.environ["HOME"]).parent
# Wait for the launcher to finish its initial runtime activity activation.
while not (root / "launch-ready").exists():
    time.sleep(.05)
report = {}
def call(args, payload=None, env=None):
    return subprocess.run(args, input=json.dumps(payload) if payload else None,
                          env=env, text=True, capture_output=True, timeout=30)
def dispatch(payload, env=None):
    result = call(["agent-hook", "dispatch", "--product", "claude", "--format", "json"], payload, env)
    data = json.loads(result.stdout)["data"]
    return {"action": data["action"], "codes": [r["code"] for r in data["reasons"]]}
try:
    report["readiness"] = call(["agent-session", "readiness", "--format", "json"]).returncode
    report["runtime_inputs"] = all(os.environ.get(k) for k in (
        "AGENT_SESSION_ID", "AGENT_SESSION_RUNTIME_ID", "AGENT_SESSION_CAPABILITY_FILE",
        "AGENT_SESSION_CHECKPOINT_FILE", "AGENT_SESSION_ATTENTION_AUTHORITY"))
    report["mode"] = os.environ.get("AGENT_SESSION_COORDINATION_MODE")
    payload = {"hook_event_name": "UserPromptSubmit", "cwd": os.getcwd(),
               "session_id": sys.argv[sys.argv.index("--session-id") + 1], "prompt": "synthetic"}
    settings = json.loads((pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "settings.json").read_text())
    command = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    report["native_prompt_exit"] = call(["/bin/sh", "-c", command], payload).returncode
    activity = call(["agent-session", "activity", "status", os.environ["AGENT_SESSION_ID"], "--format", "json"])
    report["working_phase"] = json.loads(activity.stdout)["data"]["turn_state"]["phase"]
    handler = pathlib.Path(os.environ["HOME"]) / ".claude/hooks/checkout-lease-guard.py"
    saved = handler.with_suffix(".saved")
    handler.rename(saved)
    try:
        report["missing_handler"] = dispatch(payload)
    finally:
        saved.rename(handler)
    report["restored_handler"] = dispatch(payload)
    stop = dict(payload, hook_event_name="Stop", stop_hook_active=False, background_tasks=[])
    command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
    report["native_stop_exit"] = call(["/bin/sh", "-c", command], stop).returncode
    # Stop is observed evidence; the provider's idle notification completes
    # the turn on the supported released consumer surfaces.
    idle = dict(payload, hook_event_name="Notification", notification_type="idle_prompt")
    command = settings["hooks"]["Notification"][0]["hooks"][0]["command"]
    report["native_idle_exit"] = call(["/bin/sh", "-c", command], idle).returncode
    deadline = time.monotonic() + 5
    while True:
        activity = call(["agent-session", "activity", "status", os.environ["AGENT_SESSION_ID"], "--format", "json"])
        report["idle_phase"] = json.loads(activity.stdout)["data"]["turn_state"]["phase"]
        if report["idle_phase"] == "waiting" or time.monotonic() >= deadline:
            break
        time.sleep(.05)
    config = pathlib.Path(os.environ["XDG_CONFIG_HOME"]) / "agent-hook/config.toml"
    locked = root / "locked.toml"
    locked.write_text(config.read_text() + '\n[overrides."runtime.claude.user-prompt-submit.all.checkout-lease-guard"]\nmode = "disabled"\n')
    locked.chmod(0o600)
    result = call(["agent-hook", "--config", str(locked), "validate", "--format", "json"])
    report["locked_override"] = {"exit": result.returncode, "code": json.loads(result.stdout).get("error", {}).get("code")}
except Exception:
    # Never retain raw stderr, provider output, capability or checkpoint bytes.
    report = {"fixture_error": True}
(root / "receipt.tmp").write_text(json.dumps(report))
(root / "receipt.tmp").replace(root / "receipt.json")
while not (root / "finish").exists():
    time.sleep(.05)
''')
        provider.chmod(0o700)
        try:
            launch = subprocess.run([
                str(producer), "start", "--agent", "claude", "--id", "fixture",
                "--agent-bin", str(provider), "--tmux-bin", str(tmux),
                "--cwd", str(cwd), "--coordination-mode", "enforce", "--format", "json",
            ], env=self.env, cwd=cwd, capture_output=True, text=True, timeout=45)
            self.assertEqual(launch.returncode, 0, "isolated synthetic runtime failed to start")
            (self.root / "launch-ready").touch()
            receipt = self.root / "receipt.json"
            deadline = time.monotonic() + 30
            while not receipt.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(receipt.exists(), "synthetic provider did not finish its probe")
            report = json.loads(receipt.read_text())
            self.assertNotIn("fixture_error", report, "synthetic provider probe failed")
            self.assertEqual(report["readiness"], 0)
            self.assertTrue(report["runtime_inputs"])
            self.assertEqual(report["mode"], "enforce")
            self.assertEqual(report["native_prompt_exit"], 0)
            self.assertEqual(report["working_phase"], "working")
            self.assertEqual(report["native_stop_exit"], 0)
            self.assertEqual(report["native_idle_exit"], 0)
            self.assertEqual(report["idle_phase"], "waiting")
            self.assertEqual(report["missing_handler"]["action"], "block")
            self.assertIn("runtime.claude.user-prompt-submit.all.checkout-lease-guard:capability-failure-closed",
                          report["missing_handler"]["codes"])
            self.assertNotEqual(report["restored_handler"]["action"], "block")
            self.assertEqual(report["locked_override"], {"exit": 65, "code": "locked-rule-override"})
        finally:
            (self.root / "finish").touch()
            subprocess.run([str(tmux), "kill-server"], env=self.env, capture_output=True, timeout=10)

    def test_selector_ownership_rejects_lookalikes(self) -> None:
        for executable in ("agent-hook", "agent-session"):
            programs = (
                f'exit 0 # selected=$root/{executable} exec "$selected" "$@"',
                selector(executable).replace(f"$root/{executable}", f"$root/{executable}-other"),
            )
            for program in programs:
                if executable == "agent-hook":
                    for product in ("codex", "claude"):
                        command = shlex.join([
                            "/bin/sh", "-c", program, "provider-entrypoint",
                            "dispatch", "--product", product,
                        ])
                        self.assertFalse(is_owned_dispatch(command, product))
                else:
                    self.assertFalse(is_owned_notify([
                        "/bin/sh", "-c", program, "provider-entrypoint",
                        "activity", "notify", "--agent", "codex",
                    ]))

    def test_codex_setup_owns_compact_ingress(self) -> None:
        preview = self.setup_preview("codex")
        groups = {
            group.get("matcher", "")
            for group in preview["owned_groups"]
            if group["event"] == "SessionStart"
        }
        self.assertIn("startup|resume|clear", groups)
        self.assertIn("compact", groups)
        # Each native group dispatches the complete policy. Overlapping groups
        # would execute memory/health and the reminder twice on startup.
        for source in ("startup", "resume", "clear", "compact"):
            self.assertEqual(sum(source in matcher.split("|") for matcher in groups), 1)

    def setup_apply(
        self,
        product: str,
        plan_digest: str,
        *action: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.agent_hook(
            "setup",
            "--product",
            product,
            *action,
            "--expected-plan-digest",
            plan_digest,
            check=check,
        )

    def sync_trusted_handlers(
        self,
        source_root: Path,
        product: str,
        live_home: Path,
        *,
        apply: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                "-c",
                (
                    'SYNC_RUNTIME_SURFACES_LIB=1 . "$1"; '
                    'SOURCE_ROOT="$2"; APPLY="$3"; OWNED_SOURCE_ROOTS=(); '
                    'sync_agent_hook_handlers "$4" "$5"'
                ),
                "bash",
                str(SYNC),
                str(source_root),
                "1" if apply else "0",
                product,
                str(live_home),
            ],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_sync_materializes_trusted_handlers_from_group_writable_source(
        self,
    ) -> None:
        source_root = self.root / "source"
        source_hooks = source_root / "core/hooks/shared"
        shutil.copytree(REPO_ROOT / "core/hooks/shared", source_hooks)
        source_hooks.chmod(0o775)
        for source in source_hooks.iterdir():
            source.chmod(0o775 if source.stat().st_mode & 0o100 else 0o664)

        live_hooks = self.codex_home / "hooks"
        shutil.rmtree(live_hooks)
        live_hooks.symlink_to(source_hooks, target_is_directory=True)

        preview = self.sync_trusted_handlers(
            source_root, "codex", self.codex_home, apply=False
        )
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("changed=true", preview.stdout)
        self.assertTrue(live_hooks.is_symlink())

        applied = self.sync_trusted_handlers(
            source_root, "codex", self.codex_home, apply=True
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertIn("changed=true", applied.stdout)
        self.assertTrue(live_hooks.is_dir())
        self.assertFalse(live_hooks.is_symlink())
        self.assertEqual(live_hooks.stat().st_mode & 0o777, 0o700)
        for source in source_hooks.iterdir():
            target = live_hooks / source.name
            self.assertTrue(target.is_file())
            self.assertFalse(target.is_symlink())
            expected_mode = 0o700 if source.stat().st_mode & 0o100 else 0o600
            self.assertEqual(target.stat().st_mode & 0o777, expected_mode)

        write_private(self.codex_home / "config.toml", "# test config\n")
        add = self.setup_preview("codex")
        read_json(self.setup_apply("codex", add["plan_digest"], "--apply"))
        self.assert_doctor("codex")
        damaged = live_hooks / "checkout-lease-guard.py"
        damaged.chmod(0o770)
        rejected = self.agent_hook(
            "doctor", "--product", "codex", check=False
        )
        self.assertEqual(rejected.returncode, 65)
        self.assertEqual(json.loads(rejected.stdout)["error"]["code"], "handler-untrusted")

        restored = self.sync_trusted_handlers(
            source_root, "codex", self.codex_home, apply=True
        )
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertIn("changed=true", restored.stdout)
        self.agent_hook("doctor", "--product", "codex")

        converged = self.sync_trusted_handlers(
            source_root, "codex", self.codex_home, apply=True
        )
        self.assertEqual(converged.returncode, 0, converged.stderr)
        self.assertIn("changed=false", converged.stdout)

    def test_sync_accepts_owned_bytecode_caches(self) -> None:
        for location in ("source", "live"):
            with self.subTest(location=location):
                source_root = self.root / ("source-" + location)
                source_hooks = source_root / "core/hooks/shared"
                shutil.copytree(REPO_ROOT / "core/hooks/shared", source_hooks)
                live_home = self.root / ("home-" + location)
                live_home.mkdir(mode=0o700)
                initial = self.sync_trusted_handlers(source_root, "codex", live_home, apply=True)
                self.assertEqual(initial.returncode, 0, initial.stderr)
                cache_root = source_hooks if location == "source" else live_home / "hooks"
                cache = cache_root / "__pycache__"
                cache.mkdir()
                (cache / "helper.cpython-313.pyc").write_bytes(b"cache")
                (cache_root / "legacy.pyc").write_bytes(b"cache")
                result = self.sync_trusted_handlers(source_root, "codex", live_home, apply=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("changed=false", result.stdout)

    def test_sync_refuses_writable_bytecode_caches(self) -> None:
        for location in ("source", "live"):
            for entry, write_bit in ((entry, bit) for entry in ("directory", "child", "file") for bit in (0o020, 0o002)):
                with self.subTest(location=location, entry=entry, write_bit=write_bit):
                    source_root = self.root / ("source-" + location + entry + str(write_bit))
                    source_hooks = source_root / "core/hooks/shared"
                    shutil.copytree(REPO_ROOT / "core/hooks/shared", source_hooks)
                    live_home = self.root / ("home-" + location + entry + str(write_bit))
                    live_home.mkdir(mode=0o700)
                    initial = self.sync_trusted_handlers(source_root, "codex", live_home, apply=True)
                    self.assertEqual(initial.returncode, 0, initial.stderr)
                    cache_root = source_hooks if location == "source" else live_home / "hooks"
                    if entry == "file":
                        target = cache_root / "legacy.pyc"
                        target.write_bytes(b"cache")
                    else:
                        cache = cache_root / "__pycache__"
                        cache.mkdir(mode=0o700)
                        target = cache / "helper.pyc"
                        target.write_bytes(b"cache")
                        if entry == "directory":
                            target = cache
                    target.chmod((0o755 if entry == "directory" else 0o644) | write_bit)
                    result = self.sync_trusted_handlers(source_root, "codex", live_home, apply=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_sync_refuses_symlinked_bytecode_caches(self) -> None:
        for location in ("source", "live"):
            for name in ("__pycache__", "legacy.pyc", "__pycache__/nested.pyc", "__pycache__/unexpected.txt"):
                with self.subTest(location=location, name=name):
                    source_root = self.root / ("source-" + location + name)
                    source_hooks = source_root / "core/hooks/shared"
                    shutil.copytree(REPO_ROOT / "core/hooks/shared", source_hooks)
                    live_home = self.root / ("home-" + location + name)
                    live_home.mkdir(mode=0o700)
                    initial = self.sync_trusted_handlers(source_root, "codex", live_home, apply=True)
                    self.assertEqual(initial.returncode, 0, initial.stderr)
                    cache_root = source_hooks if location == "source" else live_home / "hooks"
                    if "/" in name:
                        (cache_root / "__pycache__").mkdir()
                    (cache_root / name).symlink_to(self.root)
                    result = self.sync_trusted_handlers(source_root, "codex", live_home, apply=True)
                    self.assertNotEqual(result.returncode, 0)

    def test_sync_refuses_foreign_live_handler_symlink(self) -> None:
        source_root = self.root / "source"
        source_hooks = source_root / "core/hooks/shared"
        shutil.copytree(REPO_ROOT / "core/hooks/shared", source_hooks)
        foreign_hooks = self.root / "foreign-hooks"
        shutil.copytree(REPO_ROOT / "core/hooks/shared", foreign_hooks)

        live_hooks = self.codex_home / "hooks"
        shutil.rmtree(live_hooks)
        live_hooks.symlink_to(foreign_hooks, target_is_directory=True)

        preview = self.sync_trusted_handlers(
            source_root, "codex", self.codex_home, apply=False
        )
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("review-needed=true", preview.stdout)
        self.assertTrue(live_hooks.is_symlink())

        refused = self.sync_trusted_handlers(
            source_root, "codex", self.codex_home, apply=True
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("not owned by an authorized runtime-kit source", refused.stderr)
        self.assertTrue(live_hooks.is_symlink())
        self.assertEqual(live_hooks.resolve(), foreign_hooks.resolve())

    def assert_doctor(self, product: str, expected: str = "converged") -> None:
        data = read_json(self.agent_hook("doctor", "--product", product))["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], expected)

    def run_sync_library(
        self,
        script: str,
        *,
        check: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = self.env.copy()
        environment["SYNC_RUNTIME_SURFACES_LIB"] = "1"
        environment["AGENT_HOOK_BIN"] = AGENT_HOOK
        if extra_env:
            environment.update(extra_env)
        return subprocess.run(
            ["bash", "-c", script, "sync-agent-hook", str(SYNC), str(REPO_ROOT)],
            env=environment,
            text=True,
            capture_output=True,
            check=check,
        )

    @staticmethod
    def legacy_codex_config() -> bytes:
        return (
            '# exact legacy provider bytes retained for rollback\n'
            'notify = ["legacy-notify", "--flag"]\n\n'
            '[[hooks.Stop]]\n'
            '[[hooks.Stop.hooks]]\n'
            'type = "command"\n'
            'command = \'AGENT_RUNTIME_PRODUCT=codex "${CODEX_HOME:-$HOME/.codex}/hooks/session-coordination-guard.py"\'\n'
            'timeout = 60\n'
            'statusMessage = "agent-runtime-kit: Audit managed operation completion"\n'
        ).encode()

    def test_production_sync_prepares_setup_before_legacy_hook_cleanup(self) -> None:
        result = self.run_sync_library(
            r'''
source "$1"
parse_args() { :; }
require_commands() { :; }
resolve_source_root() { :; }
resolve_owned_source_roots() { :; }
resolve_agent_hook_paths() { :; }
validate_live_sync_source_root() { :; }
pull_source() { :; }
check_source_counts() { :; }
sync_agent_hook_policy() { :; }
preflight_selected_product_activation() { :; }
render_home_prompt_base() { :; }
selected_products() { printf '%s\n' codex; }
render_home_prompt_product() { :; }
ensure_home_prompt() { :; }
render_product() { printf '%s\n' render; }
product_live_home() { printf '%s\n' "$HOME/.codex"; }
sync_agent_hook_handlers() { printf '%s\n' materialize-agent-hook; }
prepare_agent_hook_cutover() { printf '%s\n' prepare-agent-hook; }
sync_agent_hook_setup() { printf '%s\n' direct-agent-hook-setup; }
install_product() { printf '%s\n' install-product; }
prune_product() { printf '%s\n' prune-product; }
sync_product_activation() { printf '%s\n' activate-product; }
complete_agent_hook_cutover() { printf '%s\n' complete-agent-hook; }
run_verification() { :; }
print_summary() { :; }
main
'''
        )
        operations = [
            line
            for line in result.stdout.splitlines()
            if line
            in {
                "render",
                "materialize-agent-hook",
                "prepare-agent-hook",
                "direct-agent-hook-setup",
                "install-product",
                "prune-product",
                "activate-product",
                "complete-agent-hook",
            }
        ]
        self.assertEqual(
            operations,
            [
                "render",
                "materialize-agent-hook",
                "prepare-agent-hook",
                "install-product",
                "prune-product",
                "activate-product",
                "complete-agent-hook",
            ],
        )

    def test_forced_setup_failure_preserves_legacy_provider_bytes(self) -> None:
        provider = self.codex_home / "config.toml"
        original = self.legacy_codex_config()
        provider.parent.mkdir(parents=True, exist_ok=True)
        provider.write_bytes(original)
        provider.chmod(0o600)

        result = self.run_sync_library(
            r'''
source "$1"
SOURCE_ROOT="$2"
APPLY=1
resolve_agent_hook_paths
fake_agent_hook() {
  case " $* " in
    *" --apply "*) return 73 ;;
  esac
  "$AGENT_HOOK_BIN" "$@"
}
AGENT_HOOK_EXECUTABLE=fake_agent_hook
if prepare_agent_hook_cutover codex; then
  exit 99
else
  status=$?
fi
[ "$status" -eq 73 ]
''',
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(provider.read_bytes(), original)
        self.assertFalse((self.state / "runtime-kit-migration-v1/codex").exists())

    def test_successful_cutover_remove_restores_exact_legacy_bytes(self) -> None:
        provider = self.codex_home / "config.toml"
        original = self.legacy_codex_config()
        provider.parent.mkdir(parents=True, exist_ok=True)
        provider.write_bytes(original)
        provider.chmod(0o600)

        self.run_sync_library(
            r'''
source "$1"
SOURCE_ROOT="$2"
APPLY=1
resolve_agent_hook_paths
prepare_agent_hook_cutover codex
complete_agent_hook_cutover codex
remove_agent_hook_cutover codex
'''
        )

        self.assertEqual(provider.read_bytes(), original)
        self.assertEqual(provider.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.state / "runtime-kit-migration-v1/codex").exists())

    def test_sync_updates_only_policy_selection_and_preserves_behavior_tables(self) -> None:
        old_policy = self.root / "old-policy.toml"
        write_private(
            self.config,
            (
                'schema_version = "agent-hook.config.v1"\n\n'
                "[policy]\n"
                f'path = "{old_policy}"\n'
                f'digest = "sha256:{"0" * 64}"\n\n'
                "[providers.codex]\n"
                'mode = "shadow"\n\n'
                '[overrides."runtime.codex.pre-tool-use.bash.block-direct-git-commit"]\n'
                'mode = "shadow"\n'
            ),
        )
        environment = self.env.copy()
        environment["SYNC_RUNTIME_SURFACES_LIB"] = "1"
        subprocess.run(
            [
                "bash",
                "-c",
                (
                    'source "$1"; SOURCE_ROOT="$2"; APPLY=1; '
                    "resolve_agent_hook_paths; sync_agent_hook_policy"
                ),
                "sync-agent-hook-policy",
                str(SYNC),
                str(REPO_ROOT),
            ],
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )

        config = tomllib.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(config["providers"]["codex"]["mode"], "shadow")
        self.assertEqual(
            config["overrides"][
                "runtime.codex.pre-tool-use.bash.block-direct-git-commit"
            ]["mode"],
            "shadow",
        )
        self.assertEqual(Path(config["policy"]["path"]), self.policy)
        self.assertEqual(
            config["policy"]["digest"],
            "sha256:" + hashlib.sha256(self.policy.read_bytes()).hexdigest(),
        )

    def test_codex_add_remove_is_exact_and_preserves_unrelated_notify(self) -> None:
        self.codex_home.mkdir(parents=True, exist_ok=True)
        original_notify = ["custom-notify", "--flag"]
        write_private(
            self.codex_home / "config.toml",
            (
                'notify = ["custom-notify", "--flag"]\n\n'
                "[[hooks.PreToolUse]]\n"
                'matcher = "Custom"\n'
                "[[hooks.PreToolUse.hooks]]\n"
                'type = "command"\n'
                'command = "third-party-hook"\n'
                "timeout = 3\n"
            ),
        )

        preview = self.setup_preview("codex")
        applied = read_json(
            self.setup_apply("codex", preview["plan_digest"], "--apply")
        )["data"]
        self.assertTrue(applied["configured"])
        document = tomllib.loads(
            (self.codex_home / "config.toml").read_text(encoding="utf-8")
        )
        commands = [
            hook["command"]
            for groups in document["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        owned = [command for command in commands if is_owned_dispatch(command, "codex")]
        self.assertEqual(len(owned), len(applied["owned_groups"]))
        self.assertEqual(commands.count("third-party-hook"), 1)
        self.assertFalse(is_owned_dispatch("third-party-hook", "codex"))
        self.assertFalse(any("/hooks/" in command for command in owned))
        notify = document["notify"]
        if notify[0] == "agent-session":
            # Supported nils-cli v1.36.21 through v1.40.10 use bare argv.
            self.assertEqual(notify[:5], ["agent-session", "activity", "notify", "--agent", "codex"])
            forward = notify[5:]
        else:
            self.assertTrue(is_owned_notify(notify[:8]))
            forward = notify[8:]
        self.assertEqual(len(forward), 2)
        self.assertEqual(forward[0], "--forward-notify-argv-json")
        self.assertEqual(json.loads(forward[1]), original_notify)
        self.assert_doctor("codex")

        remove = self.setup_preview("codex", "--remove")
        stale = self.setup_apply(
            "codex",
            preview["plan_digest"],
            "--remove",
            check=False,
        )
        self.assertEqual(stale.returncode, 65)
        self.assertEqual(json.loads(stale.stdout)["error"]["code"], "setup-plan-digest-mismatch")
        read_json(self.setup_apply("codex", remove["plan_digest"], "--remove"))
        restored = tomllib.loads(
            (self.codex_home / "config.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(restored["notify"], original_notify)
        restored_commands = [
            hook["command"]
            for groups in restored["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertEqual(restored_commands, ["third-party-hook"])

    def test_claude_setup_owns_one_dispatcher_per_group(self) -> None:
        original = {
            "permissions": {"allow": ["Read"]},
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Custom",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "third-party-hook",
                                "timeout": 3,
                            }
                        ],
                    }
                ]
            },
        }
        write_private(
            self.claude_home / "settings.json",
            json.dumps(original, indent=2) + "\n",
        )

        preview = self.setup_preview("claude")
        applied = read_json(
            self.setup_apply("claude", preview["plan_digest"], "--apply")
        )["data"]
        settings = json.loads(
            (self.claude_home / "settings.json").read_text(encoding="utf-8")
        )
        commands = [
            hook["command"]
            for groups in settings["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        owned = [command for command in commands if is_owned_dispatch(command, "claude")]
        self.assertEqual(len(owned), len(applied["owned_groups"]))
        self.assertEqual(commands.count("third-party-hook"), 1)
        self.assertIn("StopFailure", applied["owned_events"])
        self.assertIn("Notification", applied["owned_events"])
        self.assertEqual(
            [
                group
                for group in applied["owned_groups"]
                if group["event"] == "StopFailure"
            ],
            [{"event": "StopFailure"}],
        )
        self.assertEqual(
            [
                group
                for group in applied["owned_groups"]
                if group["event"] == "Notification"
            ],
            [{"event": "Notification", "matcher": "agent_needs_input|idle_prompt"}],
        )
        self.assertIn("PermissionRequest", applied["owned_events"])
        self.assertEqual(
            [
                group
                for group in applied["owned_groups"]
                if group["event"] == "PermissionRequest"
            ],
            [{"event": "PermissionRequest"}],
        )
        self.assertEqual(len(settings["hooks"]["PermissionRequest"]), 1)
        self.assertEqual(len(settings["hooks"]["StopFailure"]), 1)
        self.assertEqual(len(settings["hooks"]["Notification"]), 1)
        for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            with self.subTest(event=event):
                self.assertIn(
                    "AskUserQuestion",
                    {
                        group.get("matcher")
                        for group in applied["owned_groups"]
                        if group["event"] == event
                    },
                )
                self.assertEqual(
                    len(
                        [
                            group
                            for group in settings["hooks"][event]
                            if group.get("matcher") == "AskUserQuestion"
                        ]
                    ),
                    1,
                )
        self.assert_doctor("claude")

        remove = self.setup_preview("claude", "--remove")
        read_json(self.setup_apply("claude", remove["plan_digest"], "--remove"))
        self.assertEqual(
            json.loads((self.claude_home / "settings.json").read_text(encoding="utf-8")),
            original,
        )


if __name__ == "__main__":
    unittest.main()
