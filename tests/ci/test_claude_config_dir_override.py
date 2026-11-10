#!/usr/bin/env python3
"""A symlinked CLAUDE_CONFIG_DIR settings.json never surfaces as a generic
provider-config-untrusted rollback after the migration began (#387)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SYNC = ROOT / 'scripts/sync-runtime-surfaces.sh'
# Resolve bash explicitly: CreateProcess searches System32 before PATH, so a
# bare 'bash' would pick the WSL launcher on Windows hosts.
BASH = shutil.which('bash') or 'bash'

SCRIPT = """
SYNC_RUNTIME_SURFACES_LIB=1 . "$1"
APPLY="$2"
if resolve_claude_config_dir_override; then
  rc=0
else
  rc=$?
fi
printf 'rc=%s\\n' "$rc"
printf 'config_dir=%s\\n' "${CLAUDE_CONFIG_DIR-UNSET}"
printf 'pinned_is_live=%s\\n' "$([ -n "${CLAUDE_CONFIG_DIR:-}" ] && [ "$(cd "$CLAUDE_CONFIG_DIR" 2>/dev/null && pwd -P)" = "$(cd "$HOME/.claude" 2>/dev/null && pwd -P)" ] && echo yes || echo no)"
exit "$rc"
"""


def run(home, apply, config_dir):
    env = os.environ.copy()
    env['HOME'] = str(home)
    env.pop('CLAUDE_CONFIG_DIR', None)
    if config_dir is not None:
        env['CLAUDE_CONFIG_DIR'] = str(config_dir)
    return subprocess.run([BASH, '-c', SCRIPT, 'bash', str(SYNC), apply],
                          env=env, text=True, capture_output=True)


def result_fields(result):
    fields = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition('=')
        fields[key] = value
    return fields


class ClaudeConfigDirOverrideTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.live_home = self.home / '.claude'
        self.live_home.mkdir(parents=True)
        self.live_settings = self.live_home / 'settings.json'
        self.live_settings.write_text('{"theme": "dark"}\n', encoding='utf-8')
        self.override = self.home / 'accounts' / 'acct-1'
        self.override.mkdir(parents=True)

    def test_unset_override_is_a_noop(self):
        result = run(self.home, '1', None)
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = result_fields(result)
        self.assertEqual(fields['rc'], '0')
        self.assertEqual(fields['config_dir'], 'UNSET')

    def test_regular_settings_json_keeps_the_override(self):
        (self.override / 'settings.json').write_text(
            '{"theme": "light"}\n', encoding='utf-8')
        for apply in ('0', '1'):
            with self.subTest(apply=apply):
                result = run(self.home, apply, self.override)
                self.assertEqual(result.returncode, 0, result.stderr)
                fields = result_fields(result)
                self.assertEqual(fields['rc'], '0')
                self.assertEqual(fields['config_dir'], str(self.override))

    def test_symlink_to_the_live_home_pins_the_override(self):
        (self.override / 'settings.json').symlink_to(self.live_settings)
        result = run(self.home, '1', self.override)
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = result_fields(result)
        self.assertEqual(fields['rc'], '0')
        # bash spells the live home its own way (MSYS /tmp on Windows), so
        # compare directory identity rather than path strings.
        self.assertEqual(fields['pinned_is_live'], 'yes')
        self.assertNotEqual(fields['config_dir'], str(self.override))
        self.assertIn('pinning CLAUDE_CONFIG_DIR=', result.stdout)
        self.assertIn('#387', result.stdout)

    def test_symlink_elsewhere_fails_early_in_apply(self):
        foreign = self.home / 'dotfiles' / 'claude-settings.json'
        foreign.parent.mkdir(parents=True)
        foreign.write_text('{"theme": "light"}\n', encoding='utf-8')
        (self.override / 'settings.json').symlink_to(foreign)
        result = run(self.home, '1', self.override)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('provider-config-untrusted', result.stderr)
        self.assertIn('unset CLAUDE_CONFIG_DIR', result.stderr)
        self.assertEqual(result_fields(result)['rc'], '1')

    def test_symlink_elsewhere_warns_instead_of_failing_in_dry_run(self):
        foreign = self.home / 'dotfiles' / 'claude-settings.json'
        foreign.parent.mkdir(parents=True)
        foreign.write_text('{"theme": "light"}\n', encoding='utf-8')
        (self.override / 'settings.json').symlink_to(foreign)
        result = run(self.home, '0', self.override)
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = result_fields(result)
        self.assertEqual(fields['rc'], '0')
        self.assertEqual(fields['config_dir'], str(self.override))
        self.assertIn('provider-config-untrusted', result.stderr)
        self.assertIn('unset CLAUDE_CONFIG_DIR', result.stderr)

    def test_dangling_symlink_fails_early_in_apply(self):
        (self.override / 'settings.json').symlink_to(
            self.home / 'missing-settings.json')
        result = run(self.home, '1', self.override)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('provider-config-untrusted', result.stderr)


if __name__ == '__main__':
    unittest.main()
