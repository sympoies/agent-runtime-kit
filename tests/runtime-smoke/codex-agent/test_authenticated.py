#!/usr/bin/env python3
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('authenticated.sh')

class AuthenticatedArtifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        harness = self.repo / 'tests/runtime-smoke/codex-agent'
        harness.mkdir(parents=True)
        shutil.copy(SCRIPT, harness / 'authenticated.sh')
        (harness / 'run.py').write_text('print("{}")\n')
        self.home = self.root / 'home'
        self.home.mkdir()
        (self.home / 'auth.json').write_text('synthetic')
        bindir = self.root / 'bin'
        bindir.mkdir()
        for name, body in [('codex', 'exit 0'), ('codex-cli', '''if [ "$2" = doctor ]; then
  printf '%s\\n' '{"schema_version":"cli.codex-cli.agent.doctor.v1","data":{"ready":true}}'
else
  echo wrong-response
fi''')]:
            path = bindir / name
            path.write_text('#!/bin/sh\n' + body + '\n')
            path.chmod(0o700)
        self.env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.defpath,
                        RUNTIME_SMOKE_CODEX_AUTHENTICATED='1',
                        RUNTIME_SMOKE_SOURCE_CODEX_HOME=str(self.home))
        self.script = harness / 'authenticated.sh'

    def invoke(self, output):
        return subprocess.run(['bash', str(self.script)], env=dict(self.env,
            RUNTIME_SMOKE_ARTIFACTS_DIR=str(output)), capture_output=True, text=True, timeout=10)

    def test_existing_directory_is_refused_without_chmod(self):
        output = self.root / 'existing'
        output.mkdir(mode=0o755)
        result = self.invoke(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.stat().st_mode & 0o777, 0o755)
        self.assertEqual(list(output.iterdir()), [])

    def test_symlink_parent_is_refused(self):
        target = self.root / 'target'
        target.mkdir()
        alias = self.root / 'alias'
        alias.symlink_to(target, target_is_directory=True)
        self.assertNotEqual(self.invoke(alias / 'output').returncode, 0)
        self.assertFalse((target / 'output').exists())

    def test_raw_outputs_removed_when_assertion_fails(self):
        output = self.root / 'output'
        result = self.invoke(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(output.glob('doctor.json')))
        self.assertFalse(any(output.glob('knowledge.*.txt')))

if __name__ == '__main__':
    unittest.main()
