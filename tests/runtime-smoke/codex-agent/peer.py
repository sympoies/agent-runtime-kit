#!/usr/bin/env python3
"""Fixture peers for the released wrapper; never run a model or publish Git."""
import json
import os
import subprocess
import sys
from pathlib import Path

FLAGS = ['--ignore-user-config', '--ignore-rules', '--ephemeral',
         '--skip-git-repo-check', '--disable']
FEATURES = ['hooks', 'plugins', 'remote_plugin', 'apps', 'memories', 'goals',
            'multi_agent', 'workspace_dependencies', 'shell_tool', 'unified_exec']


def emit(event, **fields):
    with Path(os.environ['ACCEPTANCE_LOG']).open('a') as stream:
        stream.write(json.dumps(dict(event=event, **fields)) + '\n')


def option(args, name):
    return args[args.index(name) + 1]


def main():
    tool, args = Path(sys.argv[0]).name, sys.argv[1:]
    mode = os.environ.get('ACCEPTANCE_MODE', '')
    if tool == 'git':
        if 'push' in args:
            emit('push')
            return int(os.environ.get('ACCEPTANCE_PUSH_EXIT', '0'))
        if 'commit' in args:
            emit('raw-commit')
            return 93
        return subprocess.call([os.environ['ACCEPTANCE_GIT'], *args])
    if tool == 'semantic-commit':
        emit('semantic', argv=args)
        if args[0] == 'staged-context':
            # Real staged bytes, with untracked/unstaged content excluded.
            root = option(args, '--repo')
            return subprocess.call([os.environ['ACCEPTANCE_GIT'], '-C', root,
                                    'diff', '--cached', '--no-ext-diff'])
        if args[0] == 'commit':
            return int(os.environ.get('ACCEPTANCE_COMMIT_EXIT', '0'))
        return 94
    if tool != 'codex':
        return 95
    if args == ['exec', '--help']:
        print(' '.join(flag for flag in FLAGS if mode != 'missing-flag' or flag != '--ignore-rules'))
        return 0
    if args == ['features', 'list']:
        print(' '.join(feature for feature in FEATURES if mode != 'missing-feature' or feature != 'hooks'))
        return 0
    if 'debug' in args:
        emit('debug')
        if mode == 'doctor-instruction-leak':
            print(Path('AGENTS.md').read_text())
        elif mode == 'doctor-hook-leak':
            (Path(os.environ['CODEX_HOME']) / 'hooks.json').write_text('{}')
            print('[]')
        else:
            print('[]')
        return 0
    home = Path(os.environ['CODEX_HOME'])
    auth = home / 'auth.json'
    stripped = ['CODEX_AUTH_FILE', 'CODEX_SECRET_DIR', 'CODEX_SECRET_CACHE_DIR',
                'CODEX_CLI_AGENT_RUNTIME', 'CODEX_AUTH_REMOTE_SENTINEL',
                'AGENT_DOCS_SENTINEL', 'AGENT_SESSION_SENTINEL',
                'AGENT_HOOK_SENTINEL', 'AGENT_EVIDENCE_SENTINEL']
    emit('child', argv=args, home=str(home), mode=home.stat().st_mode & 0o777,
         entries=sorted(p.name for p in home.iterdir()),
         auth_link=auth.is_symlink(), auth_target=os.readlink(auth) if auth.is_symlink() else None,
         cwd=os.getcwd(), shell_home=os.environ.get('HOME'),
         stripped={name: name in os.environ for name in stripped},
         retained={name: os.environ.get(name) for name in ['SSH_AUTH_SOCK', 'GIT_CONFIG_GLOBAL', 'XDG_RUNTIME_DIR']})
    if args[0] == 'resume':
        return 7
    if mode == 'replace-auth':
        auth.unlink()
        auth.write_text('synthetic replacement')
    if '--output-last-message' in args:
        message = json.loads(os.environ['ACCEPTANCE_MESSAGE'])
        Path(option(args, '--output-last-message')).write_text(json.dumps(message))
        if mode == 'index-drift':
            Path('drift.txt').write_text('concurrent fixture change')
            subprocess.run([os.environ['ACCEPTANCE_GIT'], 'add', 'drift.txt'], check=True)
        elif mode == 'head-drift':
            # Move to an already-created fixture object without authoring a commit.
            subprocess.run([os.environ['ACCEPTANCE_GIT'], 'update-ref', 'HEAD',
                            os.environ['ACCEPTANCE_OTHER_HEAD']], check=True)
    return int(os.environ.get('ACCEPTANCE_CHILD_EXIT', '0'))


if __name__ == '__main__':
    sys.exit(main())
