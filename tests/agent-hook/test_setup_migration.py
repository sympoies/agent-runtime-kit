#!/usr/bin/env python3
"""Consumer acceptance for setup-owned ingress and runtime-kit config sync."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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
        damaged = live_hooks / "pre-edit-intent-gate.py"
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
agent-hook() {
  case " $* " in
    *" --apply "*) return 73 ;;
  esac
  "$AGENT_HOOK_BIN" "$@"
}
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
        owned = [command for command in commands if command.startswith("agent-hook dispatch")]
        self.assertEqual(len(owned), len(applied["owned_groups"]))
        self.assertEqual(commands.count("third-party-hook"), 1)
        self.assertFalse(any("/hooks/" in command for command in owned))
        self.assertEqual(document["notify"][:5], [
            "agent-session",
            "activity",
            "notify",
            "--agent",
            "codex",
        ])
        self.assertIn("--forward-notify-argv-json", document["notify"])
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
        owned = [command for command in commands if command.startswith("agent-hook dispatch")]
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
