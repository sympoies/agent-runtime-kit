#!/usr/bin/env python3
"""Fold delivery behavior with a transport fake; real provider acceptance is separate."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/ci/devlog-fold.py'


class FoldPublisherTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'The fold publisher must exist in kit CI')
        spec = importlib.util.spec_from_file_location('devlog_fold', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_noop_has_no_provider_mutation(self):
        with patch.object(self.module, 'prepare_fold', return_value=('base', 'tree', [])), patch.object(self.module, 'api') as api:
            self.assertEqual(self.module.publish('example/project', 'main', 'docs/devlog')['status'], 'noop')
            api.assert_not_called()

    def test_verified_commit_has_no_custom_identity_and_fast_forward_only(self):
        with patch.object(self.module, 'prepare_fold', return_value=('base', 'tree', [{'path': 'docs/devlog/2001-01.md', 'content': 'month'}])), patch.object(self.module, 'api', side_effect=[{'sha': 'newtree'}, {'sha': 'newcommit', 'verification': {'verified': True}}, {}]) as api:
            result = self.module.publish('example/project', 'main', 'docs/devlog')
            self.assertEqual(result['status'], 'folded')
            commit = api.call_args_list[1].args[2]
            self.assertEqual(set(commit), {'message', 'tree', 'parents'})
            self.assertEqual(commit['parents'], ['base'])
            self.assertEqual(api.call_args_list[2].args[2], {'sha': 'newcommit', 'force': False})

    def test_unsigned_commit_is_never_published(self):
        with patch.object(self.module, 'prepare_fold', return_value=('base', 'tree', [{'path': 'docs/devlog/2001-01.md', 'content': 'month'}])), patch.object(self.module, 'api', side_effect=[{'sha': 'newtree'}, {'sha': 'bad', 'verification': {'verified': False}}]) as api:
            with self.assertRaisesRegex(RuntimeError, 'verified'):
                self.module.publish('example/project', 'main', 'docs/devlog')
            self.assertEqual(api.call_count, 2)

    def test_moved_branch_refetches_and_reruns_fold(self):
        error = self.module.ApiError(422)
        effects = [{'sha': 't1'}, {'sha': 'c1', 'verification': {'verified': True}}, error,
                   {'sha': 't2'}, {'sha': 'c2', 'verification': {'verified': True}}, {}]
        with patch.object(self.module, 'prepare_fold', side_effect=[('b1', 'oldtree', [{'path': 'docs/devlog/a.md', 'content': 'one'}]), ('b2', 'newtree', [{'path': 'docs/devlog/a.md', 'content': 'two'}])]) as prepare, patch.object(self.module, 'api', side_effect=effects) as api, patch.object(self.module, 'remote_head', return_value='b2'):
            self.assertEqual(self.module.publish('example/project', 'main', 'docs/devlog')['attempts'], 2)
            self.assertEqual(prepare.call_count, 2)
            self.assertEqual(api.call_args_list[4].args[2]['parents'], ['b2'])

    def test_permission_failure_or_unchanged_tip_is_not_retried(self):
        for status in (403, 422):
            with self.subTest(status=status), patch.object(self.module, 'prepare_fold', return_value=('base', 'tree', [{'path': 'docs/devlog/a.md', 'content': 'one'}])) as prepare, patch.object(self.module, 'api', side_effect=[{'sha': 't1'}, {'sha': 'c1', 'verification': {'verified': True}}, self.module.ApiError(status)]), patch.object(self.module, 'remote_head', return_value='base'):
                with self.assertRaises(self.module.ApiError):
                    self.module.publish('example/project', 'main', 'docs/devlog')
                self.assertEqual(prepare.call_count, 1)

    def test_fetch_auth_is_ephemeral_and_other_children_have_no_token(self):
        with patch.dict(os.environ, {'PATH': '/usr/bin', 'GH_TOKEN': 'synthetic-token', 'GITHUB_TOKEN': 'other-synthetic-token', 'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'synthetic-oidc-token', 'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://example.invalid/token'}, clear=True), patch.object(self.module.subprocess, 'check_output', return_value='base') as command:
            self.module.git('fetch', 'origin', 'main')
            env = command.call_args.kwargs['env']
            self.assertNotIn('GH_TOKEN', env)
            self.assertNotIn('GITHUB_TOKEN', env)
            self.assertFalse('ACTIONS_ID_TOKEN_REQUEST_TOKEN' in env, 'OIDC request credential inherited')
            self.assertFalse('ACTIONS_ID_TOKEN_REQUEST_URL' in env, 'OIDC request endpoint inherited')
            self.assertEqual(env['GIT_CONFIG_KEY_0'], 'http.https://github.com/.extraheader')
            self.assertNotIn('synthetic-token', str(command.call_args.args))
            self.module.git('rev-parse', 'HEAD')
            self.assertNotIn('GIT_CONFIG_VALUE_0', command.call_args.kwargs['env'])
            self.assertNotIn('GH_TOKEN', self.module.tool_env())

    def test_non_devlog_directory_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as raw:
            original = os.getcwd()
            try:
                os.chdir(raw)
                Path('README.md').write_text('# Example\n')
                with patch.dict(os.environ, {'AGENT_RUNTIME_DEVLOG_FRAGMENTS': '1'}), patch.object(self.module, 'publish') as publish, patch('sys.argv', ['devlog-fold.py', '--repo', 'example/project', '--branch', 'main', '--dir', '.']):
                    with self.assertRaises(SystemExit):
                        self.module.main()
                    publish.assert_not_called()
            finally:
                os.chdir(original)


if __name__ == '__main__':
    unittest.main()
