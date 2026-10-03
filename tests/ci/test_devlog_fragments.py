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
        source = next(step['run'] for step in steps if step.get('id') == 'source')
        code = source.split("python3 - <<'PY_SOURCE'\n", 1)[1].rsplit('PY_SOURCE', 1)[0]
        self.assertNotIn('kit-ref', json.dumps(workflow))
        checkout = next(step for step in steps if step['name'] == 'Checkout trusted kit owner')
        self.assertEqual(checkout['with']['ref'], '${{ steps.source.outputs.sha }}')
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


class WorkflowAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.safe_load((ROOT / '.github/workflows/devlog-fold.yml').read_text())
        # PyYAML's YAML 1.1 loader treats the Actions key `on` as a boolean.
        self.call = self.workflow.get('on', self.workflow.get(True))['workflow_call']
        self.steps = self.workflow['jobs']['fold']['steps']

    def test_app_is_default_and_minting_is_explicit(self):
        self.assertEqual(self.call['inputs']['authentication']['default'], 'app')
        for secret in ('BOT_APP_ID', 'BOT_APP_PRIVATE_KEY'):
            self.assertFalse(self.call['secrets'][secret]['required'])
        mint = next(step for step in self.steps if step.get('id') == 'app')
        self.assertEqual(mint['if'], "inputs.authentication == 'app'")
        self.assertEqual(mint['with']['permission-contents'], 'write')

    def test_mode_and_app_credentials_are_validated_before_checkout(self):
        validation = self.steps[0]
        self.assertEqual(validation['name'], 'Validate fold authentication')
        self.assertEqual(validation['env'], {
            'FOLD_AUTHENTICATION': '${{ inputs.authentication }}',
            'BOT_APP_ID': '${{ secrets.BOT_APP_ID }}',
            'BOT_APP_PRIVATE_KEY': '${{ secrets.BOT_APP_PRIVATE_KEY }}',
        })
        cases = [('app', '123', 'synthetic-private-key', 0),
                 ('app', '', 'synthetic-private-key', 64),
                 ('app', '123', '', 64),
                 ('app', '', '', 64),
                 ('github-token', '', '', 0),
                 ('github-token', '123', 'synthetic-private-key', 0),
                 ('unknown', '123', 'synthetic-private-key', 64),
                 ('', '', '', 64)]
        for mode, app_id, key, expected in cases:
            with self.subTest(mode=mode, app_id_present=bool(app_id), key_present=bool(key)):
                result = subprocess.run(['bash', '-c', validation['run']], text=True,
                                        capture_output=True, env={**os.environ,
                                            'FOLD_AUTHENTICATION': mode,
                                            'BOT_APP_ID': app_id, 'BOT_APP_PRIVATE_KEY': key})
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertNotIn('synthetic-private-key', result.stdout + result.stderr)

    def test_publication_uses_workflow_token_only_in_explicit_mode(self):
        publish = self.steps[-1]
        self.assertEqual(publish['env']['GH_TOKEN'],
                         "${{ inputs.authentication == 'github-token' && github.token || steps.app.outputs.token }}")

    def test_callee_inherits_caller_permissions_without_read_only_downgrade(self):
        self.assertNotIn('permissions', self.workflow)
        self.assertNotIn('permissions', self.workflow['jobs']['fold'])


if __name__ == '__main__':
    unittest.main()
