#!/usr/bin/env python3
"""A1–A14 consumer acceptance, using a released codex-cli executable.

Boundary mode substitutes only child executables. Product mode additionally
uses real Codex's no-API diagnostic. Neither mode loads operator credentials.
A machine-readable matrix keeps live acceptance explicitly pending.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FEATURES = ['hooks', 'plugins', 'remote_plugin', 'apps', 'memories', 'goals',
            'multi_agent', 'workspace_dependencies']
HOME_SENTINEL = 'ACCEPTANCE_HOME_INSTRUCTION_SENTINEL'
PROJECT_SENTINEL = 'ACCEPTANCE_PROJECT_INSTRUCTION_SENTINEL'
AUTH_SENTINEL = 'synthetic-auth-do-not-log'
MESSAGE = dict(type='test', scope='fixture', subject='accept staged change', body_bullets=[])
CLI = ''
CODEX = ''


def run(argv, env, cwd, check=True):
    result = subprocess.run([str(arg) for arg in argv], env=env, cwd=cwd,
                            text=True, capture_output=True, timeout=45)
    if check and result.returncode:
        # Fixture-only output: this runner never loads real auth or configuration.
        raise AssertionError(f'command failed ({result.returncode}): {result.stderr}')
    return result


def values(args, key):
    return [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == key]


class Fixture:
    def __init__(self, root):
        self.root = root
        self.home = root / 'home'
        self.codex_home = self.home / '.codex'
        self.workspace = root / 'workspace'
        self.bin = root / 'bin'
        self.log = root / 'events.jsonl'
        for directory in [self.codex_home, self.workspace, self.bin, root / 'runtime', root / 'tmp']:
            directory.mkdir(parents=True)
        for name in ['codex', 'semantic-commit', 'git']:
            # An absolute interpreter keeps the stub PATH deliberately closed.
            (self.bin / name).write_text(f'#!{sys.executable}\n' +
                                        (HERE / 'peer.py').read_text().split('\n', 1)[1])
            (self.bin / name).chmod(0o700)
        self.env = {
            'PATH': str(self.bin), 'HOME': str(self.home),
            'CODEX_HOME': str(self.codex_home),
            'XDG_RUNTIME_DIR': str(root / 'runtime'), 'TMPDIR': str(root / 'tmp'),
            'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data'),
            'XDG_STATE_HOME': str(root / 'state'), 'XDG_CACHE_HOME': str(root / 'cache'),
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(root / 'gitconfig'),
            'GIT_AUTHOR_NAME': 'Acceptance Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Acceptance Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
            'ACCEPTANCE_GIT': shutil.which('git') or '', 'ACCEPTANCE_LOG': str(self.log),
            'ACCEPTANCE_MESSAGE': json.dumps(MESSAGE),
            'CODEX_CLI_MODEL': 'acceptance-model', 'CODEX_CLI_REASONING': 'low',
            'ZDOTDIR': str(root / 'shell'),
            'CODEX_ALLOW_DANGEROUS_ENABLED': 'false',
            'SSH_AUTH_SOCK': str(root / 'synthetic-signing-socket'),
        }
        for name in ['CODEX_AUTH_REMOTE_SENTINEL', 'AGENT_DOCS_SENTINEL',
                     'AGENT_SESSION_SENTINEL', 'AGENT_HOOK_SENTINEL', 'AGENT_EVIDENCE_SENTINEL',
                     'CODEX_SECRET_DIR', 'CODEX_SECRET_CACHE_DIR']:
            self.env[name] = str(root / 'synthetic-control')
        prompts = root / 'shell/prompts'
        prompts.mkdir(parents=True)
        for name in ['actionable-advice', 'actionable-knowledge']:
            (prompts / f'{name}.md').write_text('$ARGUMENTS')
        (self.codex_home / 'auth.json').write_text(AUTH_SENTINEL)
        (self.codex_home / 'AGENTS.md').write_text(HOME_SENTINEL)
        (self.workspace / 'AGENTS.md').write_text(PROJECT_SENTINEL)
        for name in ['hooks', 'plugins', 'skills', 'agents', 'memories', 'goals']:
            (self.codex_home / name).mkdir()
            (self.codex_home / name / 'sentinel.txt').write_text('AMBIENT_' + name.upper())
        (self.codex_home / 'hooks.json').write_text('{}')
        (self.codex_home / 'config.toml').write_text('[features]\nhooks = true\n')

    def invoke(self, *args, check=True, **updates):
        return run([CLI, 'agent', *args], dict(self.env, **updates), self.workspace, check)

    def events(self, event=None):
        rows = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return [row for row in rows if event is None or row['event'] == event]

    def clear(self):
        self.log.unlink(missing_ok=True)

    def git(self, *args):
        return run([self.env['ACCEPTANCE_GIT'], *args], self.env, self.workspace).stdout.strip()

    def staged_repo(self):
        self.git('init', '-b', 'fixture')
        (self.workspace / 'tracked.txt').write_text('baseline\n')
        self.git('add', 'tracked.txt')
        # Fixture Git sees no system/global config, signing setup or native hooks.
        self.git('commit', '-m', 'test: fixture baseline')
        old_head = self.git('rev-parse', 'HEAD')
        (self.workspace / 'tracked.txt').write_text('STAGED_BUNDLE_SENTINEL\n')
        self.git('add', 'tracked.txt')
        # A second object provides a real HEAD race, authored only in this fixture.
        tree = self.git('write-tree')
        self.env['ACCEPTANCE_OTHER_HEAD'] = self.git('commit-tree', tree, '-p', old_head, '-m', 'test: concurrent fixture')
        (self.workspace / 'tracked.txt').write_text('UNSTAGED_CONTENT_SENTINEL\n')
        (self.workspace / 'untracked.txt').write_text('UNTRACKED_CONTENT_SENTINEL\n')
        return old_head


class BoundaryAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='codex-agent-acceptance-')
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name))

    def child(self):
        rows = self.f.events('child')
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_A1_default_home_argv_environment_and_cleanup(self):
        homes = []
        for _ in range(2):
            self.f.clear()
            self.f.invoke('prompt', 'literal $(must-not-run); prompt')
            child = self.child()
            args = child['argv']
            self.assertEqual(args[:3], ['--ask-for-approval', 'never', 'exec'])
            for flag in ['--ignore-user-config', '--ignore-rules', '--ephemeral', '--skip-git-repo-check']:
                self.assertEqual(args.count(flag), 1)
            self.assertEqual(values(args, '--disable'), FEATURES)
            self.assertIn('project_doc_max_bytes=0', values(args, '-c'))
            self.assertEqual(values(args, '--sandbox'), ['workspace-write'])
            self.assertEqual(values(args, '--model'), ['acceptance-model'])
            self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', args)
            self.assertEqual(args[-2:], ['--', 'literal $(must-not-run); prompt'])
            self.assertEqual(child['cwd'], str(self.f.workspace))
            self.assertEqual(child['shell_home'], str(self.f.home))
            self.assertFalse(any(child['stripped'].values()))
            for name, actual in child['retained'].items():
                self.assertEqual(actual, self.f.env[name])
            self.assertEqual(child['mode'], 0o700)
            self.assertFalse(Path(child['home']).exists())
            homes.append(child['home'])
        self.assertNotEqual(*homes)

    def test_A3_A4_child_has_no_ambient_runtime_surfaces(self):
        self.f.invoke('prompt', 'surface probe')
        self.assertEqual(self.child()['entries'], ['auth.json'])
        self.f.clear()
        self.f.invoke('prompt', '--runtime', 'inherited', 'control', CODEX_ALLOW_DANGEROUS_ENABLED='true')
        child = self.child()
        self.assertEqual(child['home'], str(self.f.codex_home))
        for name in ['AGENTS.md', 'config.toml', 'hooks.json', 'hooks', 'plugins', 'skills', 'agents', 'memories', 'goals']:
            self.assertIn(name, child['entries'])

    def test_A5_auth_link_precedence_replacement_and_failure_cleanup(self):
        alternate = self.f.root / 'alternate-auth.json'
        alternate.write_text(AUTH_SENTINEL)
        for mode in ['', 'replace-auth']:
            self.f.clear()
            result = self.f.invoke('prompt', 'auth boundary', CODEX_AUTH_FILE=str(alternate), ACCEPTANCE_MODE=mode)
            child = self.child()
            self.assertTrue(child['auth_link'])
            self.assertEqual(child['auth_target'], str(alternate))
            self.assertEqual(child['entries'], ['auth.json'])
            self.assertEqual(alternate.read_text(), AUTH_SENTINEL)
            self.assertNotIn(AUTH_SENTINEL, result.stdout + result.stderr + self.f.log.read_text())
            self.assertFalse(Path(child['home']).exists())
            self.assertEqual('isolated-auth-write-not-propagated' in result.stderr, mode == 'replace-auth')
        self.f.clear()
        result = self.f.invoke('prompt', 'child failure', check=False, ACCEPTANCE_CHILD_EXIT='19')
        self.assertEqual(result.returncode, 19)
        self.assertFalse(Path(self.child()['home']).exists())
        (self.f.codex_home / 'auth.json').unlink()
        self.f.clear()
        self.f.invoke('prompt', 'credential-store fallback')
        self.assertEqual(self.child()['entries'], [])

    def test_A6_command_sandbox_selection(self):
        for command, sandbox in [('prompt', 'workspace-write'), ('advice', 'read-only'), ('knowledge', 'read-only')]:
            with self.subTest(command=command):
                self.f.clear()
                self.f.invoke(command, 'sandbox boundary')
                self.assertEqual(values(self.child()['argv'], '--sandbox'), [sandbox])

    def test_A7_missing_capabilities_fail_before_child_without_fallback(self):
        for mode in ['missing-flag', 'missing-feature']:
            with self.subTest(mode=mode):
                self.f.clear()
                result = self.f.invoke('prompt', 'must not launch', check=False, ACCEPTANCE_MODE=mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('isolated-runtime-unsupported', result.stderr)
                self.assertEqual(self.f.events('child'), [])

    def test_A7_home_creation_failure_never_launches_child(self):
        unavailable = self.f.root / 'not-a-directory'
        unavailable.write_text('fixture')
        result = self.f.invoke('prompt', 'must not launch', check=False,
                               XDG_RUNTIME_DIR=str(unavailable), TMPDIR=str(unavailable))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('isolated-home-create-failed', result.stderr)
        self.assertEqual(self.f.events('child'), [])

    def test_A8_runtime_precedence_invalid_values_and_inherited_gate(self):
        result = self.f.invoke('prompt', '--runtime', 'inherited', 'gate', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CODEX_ALLOW_DANGEROUS_ENABLED', result.stderr)
        self.assertEqual(self.f.events('child'), [])
        for args, environment, inherited in [
            ([], 'inherited', True), (['--runtime', 'isolated'], 'inherited', False),
            (['--runtime', 'inherited'], 'isolated', True), (['--ephemeral'], 'isolated', False),
            (['--runtime', 'inherited', '--ephemeral'], 'isolated', True),
        ]:
            self.f.clear()
            self.f.invoke('prompt', *args, 'precedence', CODEX_CLI_AGENT_RUNTIME=environment,
                          CODEX_ALLOW_DANGEROUS_ENABLED='true')
            child = self.child()
            self.assertEqual(child['home'] == str(self.f.codex_home), inherited)
            self.assertEqual('--dangerously-bypass-approvals-and-sandbox' in child['argv'], inherited)
            self.assertEqual('--ignore-user-config' in child['argv'], not inherited)
            if inherited:
                expected = ['exec', '--dangerously-bypass-approvals-and-sandbox',
                            '-s', 'workspace-write', '-m', 'acceptance-model',
                            '-c', 'model_reasoning_effort="low"']
                if '--ephemeral' in args:
                    expected.append('--ephemeral')
                self.assertEqual(child['argv'], expected + ['--', 'precedence'])
        for args, env in [(['--runtime', 'invalid'], {}), ([], {'CODEX_CLI_AGENT_RUNTIME': 'invalid'})]:
            self.f.clear()
            result = self.f.invoke('prompt', *args, 'invalid selector', check=False, **env)
            self.assertEqual(result.returncode, 64)
            self.assertEqual(self.f.events('child'), [])

    def test_A8_resume_uses_recorded_home_exact_argv_and_exit(self):
        sessions = self.f.codex_home / 'sessions'
        sessions.mkdir()
        recorded = self.f.root / 'recorded workspace'
        recorded.mkdir()
        (sessions / 'rollout.jsonl').write_text(json.dumps(dict(type='session_meta',
            payload=dict(id='acceptance-session', cwd=str(recorded),
                         source='cli', timestamp='2099-01-01T00:00:00Z'))) + '\n')
        result = self.f.invoke('resume', 'acceptance-session', check=False)
        self.assertEqual(result.returncode, 7)
        child = self.child()
        self.assertEqual(child['home'], str(self.f.codex_home))
        self.assertEqual(child['argv'], ['resume', 'acceptance-session', '--cd', str(recorded), '--no-alt-screen'])
        self.f.clear()
        result = self.f.invoke('resume', 'acceptance-session', '--runtime', 'isolated', check=False)
        self.assertEqual(result.returncode, 64)
        self.assertEqual(self.f.events('child'), [])

    def test_A9_commit_only_staged_bundle_and_semantic_owner(self):
        old_head = self.f.staged_repo()
        tree = self.f.git('write-tree')
        self.f.invoke('commit')
        child = self.child()
        args = child['argv']
        self.assertEqual(values(args, '--sandbox'), ['read-only'])
        self.assertEqual(values(args, '--disable'), FEATURES + ['shell_tool', 'unified_exec'])
        self.assertIn('--output-schema', args)
        self.assertIn('--output-last-message', args)
        self.assertIn('STAGED_BUNDLE_SENTINEL', args[-1])
        for sentinel in ['UNSTAGED_CONTENT_SENTINEL', 'UNTRACKED_CONTENT_SENTINEL']:
            self.assertNotIn(sentinel, args[-1])
        calls = self.f.events('semantic')
        self.assertEqual(calls[0]['argv'], ['staged-context', '--format', 'bundle', '--repo', str(self.f.workspace)])
        commit = calls[1]['argv']
        self.assertEqual(commit[0], 'commit')
        self.assertEqual(values(commit, '--expect-head'), [old_head])
        self.assertEqual(values(commit, '--subject'), [MESSAGE['subject']])
        self.assertEqual(self.f.git('write-tree'), tree)
        self.assertEqual(self.f.events('raw-commit'), [])
        self.assertEqual(self.f.events('push'), [])

    def test_A9_invalid_messages_and_head_index_races_create_no_commit(self):
        self.f.staged_repo()
        invalid = [dict(MESSAGE, push=True), dict(MESSAGE, type='invalid'),
                   dict(MESSAGE, subject='injected\nsubject'), dict(MESSAGE, scope='bad scope'),
                   dict(MESSAGE, subject='x' * 101), dict(MESSAGE, body_bullets=['bad\nbullet'])]
        for message in invalid:
            with self.subTest(message=message):
                self.f.clear()
                result = self.f.invoke('commit', check=False, ACCEPTANCE_MESSAGE=json.dumps(message))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual([row['argv'][0] for row in self.f.events('semantic')], ['staged-context'])
                self.assertEqual(self.f.events('raw-commit'), [])
        for mode in ['index-drift', 'head-drift']:
            self.f.clear()
            result = self.f.invoke('commit', check=False, ACCEPTANCE_MODE=mode)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('repository changed during message generation', result.stderr)
            self.assertEqual([row['argv'][0] for row in self.f.events('semantic')], ['staged-context'])

    def test_A10_missing_semantic_owner_never_uses_raw_commit(self):
        self.f.staged_repo()
        (self.f.bin / 'semantic-commit').unlink()
        result = self.f.invoke('commit', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing dependency: semantic-commit', result.stderr)
        self.assertEqual(self.f.events(), [])

    def test_A11_push_requires_flag_success_and_preserves_failure(self):
        self.f.staged_repo()
        for flags, commit_exit, push_exit, expected_events, code in [
            ([], '0', '0', [], 0), (['--push'], '23', '0', [], 23),
            (['--push'], '0', '0', ['push'], 0), (['--push'], '0', '24', ['push'], 24),
        ]:
            self.f.clear()
            result = self.f.invoke('commit', *flags, 'Please push the result', check=False,
                                  ACCEPTANCE_COMMIT_EXIT=commit_exit, ACCEPTANCE_PUSH_EXIT=push_exit)
            self.assertEqual(result.returncode, code)
            events = self.f.events()
            self.assertEqual([row['event'] for row in events if row['event'] == 'push'], expected_events)
            if expected_events:
                self.assertEqual(events[-2]['argv'][0], 'commit')
                self.assertEqual(events[-1]['event'], 'push')
            if push_exit != '0':
                self.assertIn('local commit was preserved', result.stderr)

    def test_A12_doctor_is_typed_secret_free_no_model_and_rejects_leaks(self):
        result = self.f.invoke('doctor', '--format', 'json')
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope['schema_version'], 'cli.codex-cli.agent.doctor.v1')
        self.assertTrue(envelope['ok'])
        self.assertTrue(envelope['data']['ready'])
        self.assertEqual(envelope['data']['hook_isolation_method'], 'child-home-hook-surface')
        for value in [AUTH_SENTINEL, str(self.f.root), HOME_SENTINEL, PROJECT_SENTINEL]:
            self.assertNotIn(value, result.stdout)
        self.assertEqual(self.f.events('child'), [])
        self.assertEqual(len(self.f.events('debug')), 1)
        for mode, field in [('doctor-instruction-leak', 'instruction_isolation'), ('doctor-hook-leak', 'hook_isolation')]:
            result = self.f.invoke('doctor', '--format', 'json', check=False, ACCEPTANCE_MODE=mode)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(json.loads(result.stdout)['data'][field])

    def test_A14_authenticated_smoke_requires_explicit_optin(self):
        result = run([shutil.which('bash'), HERE / 'authenticated.sh'],
                     self.f.env, self.f.workspace, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn('RUNTIME_SMOKE_CODEX_AUTHENTICATED=1', result.stderr)
        self.assertEqual(self.f.events(), [])

    def test_A13_no_codex_agent_exemption_in_hook_control_surfaces(self):
        paths = [path for path in (ROOT / 'core/hooks').rglob('*')
                 if path.suffix in ['.py', '.sh', '.toml', '.json', '.jsonc']] + [
            ROOT / 'core/policies/agent-hook/runtime-kit-v1.toml', ROOT / 'manifests/hook-rules.yaml',
            ROOT / 'targets/codex/hooks/config.block.toml']
        pattern = re.compile(r'codex-cli\s+agent|codex-cli[\'\"]\s*,\s*[\'\"]agent')
        for path in paths:
            # No command-specific branch exists in the current control plane.
            self.assertIsNone(pattern.search(path.read_text()), str(path.relative_to(ROOT)))


class ProductAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='codex-agent-product-')
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name))
        # No synthetic auth is supplied to real Codex. Credential-store lookup
        # is bounded by fixture HOME and XDG roots; no exec/model call is made.
        (self.f.codex_home / 'auth.json').unlink()
        self.f.env['PATH'] = str(Path(CODEX).parent) + os.pathsep + os.defpath

    def test_A2_real_prompt_input_has_inherited_positive_control(self):
        inherited = run([CODEX, 'debug', 'prompt-input', 'instruction control'], self.f.env, self.f.workspace)
        for sentinel in [HOME_SENTINEL, PROJECT_SENTINEL]:
            self.assertIn(sentinel, inherited.stdout)
        # This is the documented isolated prompt-input shape, not a model run.
        isolated_home = self.f.root / 'empty-child'
        isolated_home.mkdir(mode=0o700)
        args = [CODEX, '-c', 'project_doc_max_bytes=0']
        for feature in FEATURES:
            args += ['--disable', feature]
        isolated = run([*args, 'debug', 'prompt-input', 'instruction control'],
                       dict(self.f.env, CODEX_HOME=str(isolated_home)), self.f.workspace)
        for sentinel in [HOME_SENTINEL, PROJECT_SENTINEL]:
            self.assertNotIn(sentinel, isolated.stdout)

    def test_A12_real_doctor_without_credentials_or_api(self):
        result = self.f.invoke('doctor', '--format', 'json')
        data = json.loads(result.stdout)
        self.assertEqual(data['schema_version'], 'cli.codex-cli.agent.doctor.v1')
        self.assertTrue(data['data']['ready'])
        self.assertTrue(all(data['data']['flags'].values()))
        self.assertTrue(all(data['data']['features'].values()))
        self.assertEqual(data['data']['hook_isolation_method'], 'child-home-hook-surface')
        self.assertNotIn(str(self.f.root), result.stdout)


def main():
    global CLI, CODEX
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layer', choices=['boundary', 'product'], default='boundary')
    parser.add_argument('--codex-cli', default=os.environ.get('RUNTIME_SMOKE_CODEX_CLI', 'codex-cli'))
    parser.add_argument('--matrix-out', type=Path)
    options = parser.parse_args()
    CLI = shutil.which(options.codex_cli) or ''
    if not CLI:
        parser.error('released codex-cli is required')
    version = subprocess.run([CLI, '--version'], capture_output=True, text=True, check=True).stdout
    observed = re.search(r'^codex-cli (\d+\.\d+\.\d+)', version).group(1)
    pin_text = (ROOT / 'docs/source/nils-cli-pin.yaml').read_text()
    validated = re.search(r'validated_tag:\s*"v([^"]+)"', pin_text).group(1)
    minimum = re.search(r'minimum_supported_tag:\s*"v([^"]+)"', pin_text).group(1)
    if tuple(map(int, observed.split('.'))) < tuple(map(int, minimum.split('.'))):
        parser.error('codex-cli is below the repository compatibility minimum')
    if options.layer == 'product' and observed != validated:
        parser.error('product acceptance requires the exact validated_tag release; use scripts/dev/with-nils-version.sh')
    CODEX = shutil.which('codex') or ''
    if options.layer == 'product' and not CODEX:
        parser.error('real Codex is required for the product layer')
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BoundaryAcceptance)
    if options.layer == 'product':
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ProductAcceptance))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    # A passing test suite is deliberately distinct from full issue acceptance.
    failed_rows = set()
    for test, _ in result.failures + result.errors:
        failed_rows.update(re.findall(r'A\d+', test.id()))
    remaining = {
        3: 'Observed trusted home/project lifecycle execution and suppression',
        4: 'Observed inherited discovery and isolated suppression of each integration',
        5: 'Authenticated credential bridge smoke (synthetic link boundary passed)',
        6: 'Observed sandbox writes and denied attempts with native tool events',
        7: 'Unsafe auth-symlink failure on a platform that denies the bridge',
        14: 'Scheduled authenticated doctor and knowledge smoke receipt',
    }
    rows = []
    for number in range(1, 15):
        row = dict(id=f'A{number}', boundary='pass' if result.wasSuccessful() else 'unverified')
        if number == 2:
            row['boundary'] = 'not-applicable'
        if number in [2, 12, 14]:
            row['product'] = ('pass' if result.wasSuccessful() else 'unverified') if options.layer == 'product' else 'pending'
        row['status'] = 'partial' if number in remaining else ('pending-product' if number == 2 and options.layer != 'product' else 'pass')
        if number in remaining:
            row['remaining'] = remaining[number]
        if row['id'] in failed_rows:
            row['status'] = 'fail'
            row['boundary'] = 'fail'
        if not result.wasSuccessful() and row['status'] == 'pass':
            row['status'] = 'unverified'
        rows.append(row)
    matrix = {
        'schema_version': 'codex-agent-acceptance.v1', 'codex_cli_version': observed,
        'validated_version': validated, 'layer': options.layer,
        'tests_run': result.testsRun, 'tests_passed': result.wasSuccessful(),
        'codex_version': (subprocess.run([CODEX, '--version'], capture_output=True, text=True, check=True).stdout.strip()
                          if options.layer == 'product' else None),
        'acceptance_complete': False, 'rows': rows,
    }
    if options.matrix_out:
        options.matrix_out.parent.mkdir(parents=True, exist_ok=True)
        options.matrix_out.write_text(json.dumps(matrix, indent=2) + '\n')
    print(json.dumps(matrix))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
