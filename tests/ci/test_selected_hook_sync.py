#!/usr/bin/env python3
"""The selected hook owns sync operations even when PATH contains another hook."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SYNC = ROOT / 'scripts/sync-runtime-surfaces.sh'


class SelectedHookSyncTests(unittest.TestCase):
    def test_standalone_without_hook_keeps_dry_run_command(self):
        env = os.environ.copy()
        env.update(PATH="", AGENT_SESSION_BIN="", AGENT_RUNTIME_TRUSTED_CLI_ROOT="")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/lib/selected-cli-pair.py")],
                                env=env, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "agent-hook")
        self.assertIn("unselected PATH", result.stderr)

    def test_selected_hook_owns_sync_and_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected = root / 'selected'
            poison = root / 'poison'
            selected.mkdir()
            poison.mkdir()
            log = root / 'calls'
            for name in ('agent-session', 'agent-hook'):
                path = selected / name
                path.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\ncase "$1" in\n setup) printf "{\\"schema_version\\":\\"cli.agent-hook.setup.v1\\",\\"ok\\":true,\\"data\\":{\\"schema_version\\":\\"agent-hook.setup-result.v1\\",\\"plan_digest\\":\\"digest\\",\\"configured\\":%s}}\\n" "$(case " $* " in *" --remove "*) echo false;; *) echo true;; esac)";;\n doctor) printf "{\\"schema_version\\":\\"cli.agent-hook.doctor.v1\\",\\"ok\\":true,\\"data\\":[{\\"status\\":\\"converged\\"}]}\\n";;\nesac\n')
                path.chmod(0o755)
            bad = poison / 'agent-hook'
            bad.write_text('#!/bin/sh\necho poison >> "$CALL_LOG"\nexit 99\n')
            bad.chmod(0o755)
            env = os.environ.copy()
            env.update(HOME=tmp, XDG_CONFIG_HOME=str(root / 'config-home'), XDG_DATA_HOME=str(root / 'data-home'), XDG_STATE_HOME=str(root / 'state-home'), PATH=f'{poison}:' + env['PATH'], AGENT_SESSION_BIN=str(selected / 'agent-session'), CALL_LOG=str(log))
            script = '''SYNC_RUNTIME_SURFACES_LIB=1 . "$1"
resolve_agent_hook_paths
AGENT_HOOK_CONFIG="$HOME/config"; AGENT_HOOK_STATE_DIR="$HOME/state"
APPLY=0; sync_agent_hook_setup codex; doctor_agent_hook_product codex
SOURCE_ROOT="$2"; APPLY=1; sync_agent_hook_policy; sync_agent_hook_setup codex; doctor_agent_hook_product codex; sync_agent_hook_setup codex --remove
'''
            result = subprocess.run(['bash', '-c', script, 'bash', str(SYNC), str(ROOT)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(selected / 'agent-hook'), result.stdout)
            calls = log.read_text().splitlines()
            self.assertEqual(len(calls), 6)
            self.assertTrue(any(call.startswith("validate ") for call in calls))
            self.assertFalse(any('poison' in call for call in calls))
            self.assertTrue(any('--remove' in call for call in calls))


if __name__ == '__main__':
    unittest.main()
