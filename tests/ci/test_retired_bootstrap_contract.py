import json
import os
import tempfile
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RetiredBootstrapContract(unittest.TestCase):
    def test_retired_flags_are_rejected(self):
        for script, args in (
            ('sync-runtime-surfaces.sh', ['--codex-plugin-activation', '--help']),
        ):
            with self.subTest(script=script):
                result = subprocess.run(['bash', str(ROOT / 'scripts' / script), *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_private_both_is_rejected(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, AGENT_PRIVATE_SKILLS_HOME='')
            result = subprocess.run(['bash', str(ROOT / 'scripts/sync-private-skills.sh'), '--product', 'both'], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('invalid --product value', result.stderr)

    def test_setup_uses_bootstrap_without_feature_probe(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root) / 'home'
            home.mkdir()
            bindir = Path(root) / 'bin'
            bindir.mkdir()
            runtime = bindir / 'agent-runtime'
            runtime.write_text('#!/bin/sh\nexit 1\n')
            runtime.chmod(0o755)
            env = dict(os.environ, HOME=str(home), CODEX_HOME=str(home / '.codex'), CLAUDE_CONFIG_DIR=str(home / '.claude'), PATH=f'{bindir}:{os.environ["PATH"]}')
            result = subprocess.run(['bash', str(ROOT / 'scripts/setup.sh'), '--profile', 'core', '--skip-homebrew-install', '--skip-cli-tools', '--dry-run'], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('+ agent-runtime bootstrap-host ', result.stdout)

    def test_schema_rejects_retired_role_and_aliases(self):
        schema = json.loads((ROOT / 'core/docs/schemas/skills.schema.json').read_text())
        roles = schema['$defs']['invocation']['properties']['role']['enum']
        self.assertNotIn('compatibility', roles)
        self.assertNotIn('aliases', schema['$defs']['skill']['properties'])

if __name__ == "__main__":
    unittest.main()
