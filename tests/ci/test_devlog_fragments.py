#!/usr/bin/env python3
"""Kit environment and fragment-aware validation contract, using released devlog."""
import os
import base64
import io
import json
from unittest.mock import patch
import yaml
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RuntimeEnvironmentTests(unittest.TestCase):
    def render(self, switch=None):
        env = dict(os.environ)
        env.pop('AGENT_RUNTIME_DEVLOG_FRAGMENTS', None)
        if switch is not None:
            env['AGENT_RUNTIME_DEVLOG_FRAGMENTS'] = switch
        script = ROOT / 'scripts/render-runtime-env.sh'
        return subprocess.run(['bash', str(script)],
                              env=env, capture_output=True, text=True)

    def test_off_preserves_environment_and_month_writer_bytes(self):
        for switch in (None, '0'):
            with self.subTest(switch=switch):
                result = self.render(switch)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, ':\n')

    def test_enabled_environment_reaches_a_child_writer_without_shared_edits(self):
        if subprocess.run(['devlog', 'fold', '--help'], capture_output=True).returncode:
            self.skipTest('Opt-in fragments require released nils-cli >=1.31.14')
        rendered = self.render('1')
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            subprocess.run(['git', 'init', '-q', '--initial-branch=main'], cwd=repo, check=True)
            log = repo / 'docs/devlog'
            log.mkdir(parents=True)
            index = log / 'README.md'
            index.write_text('# Development log\n\n## Months\n')
            command = rendered.stdout + '\nexec devlog new --title Example --slug independent --date 2001-01-01 --result Result --why Reason --evidence Test\n'
            result = subprocess.run(['bash', '-c', command], cwd=repo, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((log / 'pending/2001-01-01-independent.md').exists())
            self.assertEqual(index.read_text(), '# Development log\n\n## Months\n')
            self.assertFalse((log / '2001-01.md').exists())
            result = subprocess.run(['bash', str(ROOT / 'scripts/ci/devlog-check.sh')],
                                    cwd=repo, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_bad_switch_fails_closed(self):
        self.assertEqual(self.render('typo').returncode, 64)


class WorkflowSourceTests(unittest.TestCase):
    def test_called_workflow_revision_is_provider_bound(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/devlog-fold.yml').read_text())
        steps = workflow['jobs']['fold']['steps']
        source = steps[0]['run']
        code = source.split("python3 - <<'PY_SOURCE'\n", 1)[1].rsplit('PY_SOURCE', 1)[0]
        self.assertNotIn('kit-ref', json.dumps(workflow))
        self.assertEqual(steps[1]['with']['ref'], '${{ steps.source.outputs.sha }}')
        owner = 'sympoies/agent-runtime-kit/.github/workflows/devlog-fold.yml'
        cases = [({'job_workflow_ref': owner + '@main', 'job_workflow_sha': 'a' * 40}, True),
                 ({'job_workflow_ref': 'other/kit/.github/workflows/devlog-fold.yml@main', 'job_workflow_sha': 'a' * 40}, False),
                 ({'job_workflow_ref': owner + '@main', 'job_workflow_sha': 'main'}, False)]
        for claims, passes in cases:
            with self.subTest(claims=claims), tempfile.TemporaryDirectory() as raw:
                token = 'header.' + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=') + '.signature'
                response = io.BytesIO(json.dumps({'value': token}).encode())
                output = Path(raw) / 'output'
                env = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.invalid/token?request=1',
                       'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'synthetic-token', 'GITHUB_OUTPUT': str(output)}
                with patch.dict(os.environ, env), patch('urllib.request.urlopen', return_value=response):
                    if passes:
                        exec(compile(code, '<workflow-source>', 'exec'), {})
                        self.assertEqual(output.read_text(), 'sha=' + 'a' * 40 + '\n')
                    else:
                        with self.assertRaises(SystemExit):
                            exec(compile(code, '<workflow-source>', 'exec'), {})
                        self.assertFalse(output.exists())
        names = [step['name'] for step in steps]
        self.assertLess(names.index('Resolve checksum-pinned fold tools without the App token'),
                        names.index('Mint repository-scoped fold token'))
        self.assertNotIn('with-nils-version', steps[-1]['run'])


if __name__ == '__main__':
    unittest.main()
