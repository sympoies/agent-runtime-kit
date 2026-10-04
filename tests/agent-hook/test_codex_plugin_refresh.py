"""Provider bytes survive registry refresh; opt in to the real Codex CLI."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BEGIN = "# >>> example-owner MCP >>>"
END = "# <<< example-owner MCP <<<"
BLOCK = f'{BEGIN}\n[mcp_servers.example]\nurl = "https://example.invalid/mcp"\n{END}\n'

# The real CLI reproduction established that deleting/replacing an existing
# marketplace table drops a preceding closing comment. CI needs no Codex/network.
FAKE_CODEX = '''#!/usr/bin/env python3
import json, os, shutil, sys, tomllib
from pathlib import Path
args = sys.argv[1:]
home = Path(os.environ["CODEX_HOME"])
config = home / "config.toml"
with open(os.environ["COMMAND_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if "--help" in args:
    raise SystemExit(0)
data = tomllib.loads(config.read_text())
market = data.get("marketplaces", {}).get("marker-fixture", {})
if args == ["plugin", "marketplace", "list", "--json"]:
    print(json.dumps({"marketplaces": [{"name": "marker-fixture", "root": market["source"]}]}))
elif args == ["plugin", "list", "--json"]:
    print(json.dumps({"installed": [{"pluginId": "demo@marker-fixture"}], "available": []}))
elif args[:3] == ["plugin", "marketplace", "remove"] or (
    args[:3] == ["plugin", "marketplace", "add"] and market
):
    config.write_text(config.read_text().replace("# <<< example-owner MCP <<<\\n", ""))
elif args[:2] == ["plugin", "add"]:
    source = Path(market["source"]) / "plugins/demo/skills/demo/SKILL.md"
    cache = home / "plugins/cache/marker-fixture/demo/0.1.0/skills/demo/SKILL.md"
    cache.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, cache)
'''


class CodexPluginRefreshTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="kit-registry-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.home = self.root / "home"
        self.codex_home = self.home / ".codex"
        self.codex_home.mkdir(parents=True, mode=0o700)
        self.source = self.root / "source"
        self.state = self.root / "state"
        self.marketplace = self.state / "plugin-marketplaces/marker-fixture"
        self.command_log = self.root / "commands.jsonl"
        self.manifest = {"name": "marker-fixture", "plugins": [{
            "name": "demo", "version": "0.1.0",
            "source": {"source": "local", "path": "./plugins/demo"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }]}
        manifest = self.source / "targets/codex/.agents/plugins/marketplace.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps(self.manifest))
        plugin = self.source / "targets/codex/plugins/demo/.codex-plugin/plugin.json"
        plugin.parent.mkdir(parents=True)
        plugin.write_text(json.dumps({"name": "demo", "version": "0.1.0", "description": "fixture"}))
        self.skill = self.source / "build/codex/plugins/demo/skills/demo/SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text("# Updated fixture skill\n")
        self.marketplace.mkdir(parents=True)
        shutil.copytree(self.source / "targets/codex", self.marketplace, dirs_exist_ok=True)
        old_skill = self.marketplace / "plugins/demo/skills/demo/SKILL.md"
        old_skill.parent.mkdir(parents=True)
        old_skill.write_text("# Previous fixture skill\n")
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home),
                    "CODEX_HOME": str(self.codex_home), "TMPDIR": str(self.root),
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_STATE_HOME": str(self.home / ".local/state"),
                    "XDG_CACHE_HOME": str(self.home / ".cache"),
                    "PYTHONDONTWRITEBYTECODE": "1", "COMMAND_LOG": str(self.command_log)}
        self.real = os.environ.get("KIT_TEST_REAL_CODEX") == "1"
        if self.real:
            self.codex = shutil.which("codex")
            self.assertIsNotNone(self.codex)
            self.assertEqual(self.cli("--version").stdout.strip(), "codex-cli 0.160.0")
            self.cli("plugin", "marketplace", "add", str(self.marketplace))
            self.cli("plugin", "add", "demo@marker-fixture")
            self.config.write_text(BLOCK + self.config.read_text())
        else:
            binary = self.root / "bin/codex"
            binary.parent.mkdir()
            binary.write_text(FAKE_CODEX)
            binary.chmod(0o700)
            self.env["PATH"] = str(binary.parent) + os.pathsep + self.env["PATH"]
            self.codex = str(binary)
            self.config.write_text(BLOCK + '\n[marketplaces.marker-fixture]\nsource = ' + json.dumps(str(self.marketplace)) + '\nsource_type = "local"\n\n[plugins."demo@marker-fixture"]\nenabled = true\n')
        self.config.chmod(0o600)

    @property
    def config(self):
        return self.codex_home / "config.toml"

    def cli(self, *args):
        result = subprocess.run([self.codex, *args], env=self.env, cwd=self.root,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, "fixture CLI command failed")
        return result

    def refresh(self):
        env = dict(self.env, FIXTURE_SOURCE=str(self.source), FIXTURE_STATE=str(self.state))
        return subprocess.run(["bash", "-c", '''
SYNC_RUNTIME_SURFACES_LIB=1 . "$1/scripts/sync-runtime-surfaces.sh"
APPLY=1
SOURCE_ROOT="$FIXTURE_SOURCE"
sync_codex_plugin_registry "$CODEX_HOME" "$FIXTURE_STATE"
''', "fixture", str(ROOT)], env=env, cwd=self.root,
                              text=True, capture_output=True, timeout=40)

    def test_registered_refresh_preserves_markers_and_updates_cache(self):
        result = self.refresh()
        self.assertEqual(result.returncode, 0, "supported registry refresh failed")
        self.assertIn(BLOCK, self.config.read_text(), "registry refresh destroyed foreign marker balance")
        cache = list((self.codex_home / "plugins/cache").rglob("SKILL.md"))
        self.assertTrue(any(p.read_text() == self.skill.read_text() for p in cache), "same-version cached plugin content was not refreshed")
        if not self.real:
            commands = [json.loads(line) for line in self.command_log.read_text().splitlines()]
            self.assertNotIn(["plugin", "remove", "demo@marker-fixture"], commands)
            self.assertFalse(any(command[:2] == ["plugin", "marketplace"] and command[2] in {"add", "remove"} for command in commands))

    def test_relocation_marker_loss_restores_exact_snapshot_and_stops(self):
        old = self.root / "old-marketplace"
        shutil.copytree(self.marketplace, old)
        self.config.write_text(self.config.read_text().replace(str(self.marketplace), str(old)))
        original = self.config.read_bytes()
        result = self.refresh()
        self.assertEqual(result.returncode, 65, "marker loss must stop registry refresh")
        self.assertEqual(self.config.read_bytes(), original, "rollback did not restore exact pre-step bytes")
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertIn('"outcome": "restored-marker-loss"', result.stdout)
        self.assertNotIn("plugin registry installed", result.stdout)
        self.assertFalse(list(self.codex_home.glob(".codex-config-snapshot.*")))


class CodexConfigGuardTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="kit-guard-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.config = self.root / "config.toml"
        self.config.write_text(BLOCK)
        self.config.chmod(0o600)

    def guarded(self, code):
        return subprocess.run([sys.executable, str(ROOT / "scripts/lib/codex-config-guard.py"),
                               str(self.config), "--", sys.executable, "-c", code,
                               str(self.config)], cwd=self.root, capture_output=True,
                              text=True, timeout=5)

    def test_partial_failure_restores_both_marker_loss_shapes_without_disclosure(self):
        for marker in (END + "\n", BLOCK):
            with self.subTest(removed="one-or-both-delimiters"):
                original = self.config.read_bytes()
                result = self.guarded('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text().replace(' + repr(marker) + ', "")); sys.exit(7)')
                self.assertEqual(result.returncode, 65)
                self.assertEqual(self.config.read_bytes(), original)
                self.assertIn('"command_exit": 7', result.stdout)
                self.assertIn('"outcome": "restored-marker-loss"', result.stdout)
                self.assertNotIn("example-owner", result.stdout + result.stderr)
                self.assertNotIn(str(self.config), result.stdout + result.stderr)
                self.assertFalse(list(self.root.glob(".codex-config-snapshot.*")))

    def test_ordinary_command_failure_is_preserved_and_snapshot_cleaned(self):
        original = self.config.read_bytes()
        result = self.guarded("raise SystemExit(7)")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertIn('"outcome": "preserved"', result.stdout)
        self.assertFalse(list(self.root.glob(".codex-config-snapshot.*")))

    def test_private_snapshot_restores_original_group_read_mode(self):
        self.config.chmod(0o640)
        result = self.guarded('''import pathlib,stat,sys
p=pathlib.Path(sys.argv[1])
snapshots=list(p.parent.glob(".codex-config-snapshot.*"))
assert len(snapshots)==1 and stat.S_IMODE(snapshots[0].stat().st_mode)==0o600
p.write_text(p.read_text().replace("# <<< example-owner MCP <<<\\n", ""))
''')
        self.assertEqual(result.returncode, 65)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.config.read_text(), BLOCK)

    def test_unsafe_targets_refuse_before_external_command(self):
        for kind in ("symlink", "hardlink", "fifo", "group-writable"):
            with self.subTest(kind=kind):
                self.config.unlink()
                neighbor = self.root / "neighbor"
                neighbor.write_text(BLOCK)
                if kind == "symlink":
                    self.config.symlink_to(neighbor)
                elif kind == "hardlink":
                    os.link(neighbor, self.config)
                elif kind == "fifo":
                    os.mkfifo(self.config)
                else:
                    self.config.write_text(BLOCK)
                    self.config.chmod(0o660)
                sentinel = self.root / "command-ran"
                result = self.guarded('import pathlib,sys; pathlib.Path(sys.argv[1]).with_name("command-ran").touch()')
                self.assertEqual(result.returncode, 65)
                self.assertFalse(sentinel.exists())
                self.assertEqual(neighbor.read_text(), BLOCK)
                self.assertNotIn(str(self.config), result.stdout + result.stderr)
                self.assertFalse(list(self.root.glob(".codex-config-snapshot.*")))

    def test_unreadable_post_step_retains_private_snapshot_without_overwrite(self):
        result = self.guarded('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.unlink(); p.mkdir()')
        self.assertEqual(result.returncode, 65)
        self.assertTrue(self.config.is_dir())
        snapshots = list(self.root.glob(".codex-config-snapshot.*"))
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].read_text(), BLOCK)
        self.assertEqual(snapshots[0].stat().st_mode & 0o777, 0o600)
        self.assertIn('"outcome": "snapshot-retained"', result.stderr)
        self.assertNotIn(str(self.config), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
