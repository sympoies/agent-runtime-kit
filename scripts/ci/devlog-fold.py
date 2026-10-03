#!/usr/bin/env python3
"""Trusted CI fold owner. Create verified App commits, retry only a moved branch."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request


class ApiError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'GitHub API returned HTTP {status}')


def api(method, endpoint, payload=None):
    request = urllib.request.Request(
        'https://api.github.com/' + endpoint,
        data=None if payload is None else json.dumps(payload).encode(), method=method,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not print requests, headers, tokens or provider payloads.
        raise ApiError(error.code) from None


def tool_env():
    return {key: value for key, value in os.environ.items() if key not in ('GH_TOKEN', 'GITHUB_TOKEN')}


def git(*args):
    env = tool_env()
    if args and args[0] == 'fetch':
        # Supply App credentials only to this fetch, without repository config
        # or secret-bearing argv/URLs that an exception could print.
        credential = base64.b64encode(('x-access-token:' + os.environ['GH_TOKEN']).encode()).decode()
        env.update({'GIT_CONFIG_COUNT': '1',
                    'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                    'GIT_CONFIG_VALUE_0': 'AUTHORIZATION: basic ' + credential})
    return subprocess.check_output(['git', *args], text=True, env=env).strip()


def remote_head(repo, branch):
    endpoint = f'repos/{repo}/git/ref/heads/{urllib.parse.quote(branch, safe="")}'
    return api('GET', endpoint)['object']['sha']


def prepare_fold(repo, branch, log_dir):
    # Runs only in a clean, disposable CI checkout. Never reset a developer tree.
    if git('status', '--porcelain'):
        raise RuntimeError('fold owner requires a clean disposable checkout')
    git('fetch', '--no-tags', 'origin', f'refs/heads/{branch}')
    base = git('rev-parse', 'FETCH_HEAD')
    git('checkout', '--detach', base)
    tree = git('rev-parse', 'HEAD^{tree}')
    subprocess.run(['devlog', 'fold', '--dir', log_dir], check=True,
                   env={**tool_env(), 'DEVLOG_LAYOUT': 'fragments'})
    subprocess.run(['devlog', 'check', '--dir', log_dir, '--base', base], check=True, env=tool_env())
    git('add', '--all', '--', log_dir)
    names = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z', '--', log_dir]).split(b'\0')
    changes = []
    for raw in names:
        if not raw:
            continue
        name = raw.decode('utf-8')
        path = Path(name)
        item = {'path': name, 'mode': '100644', 'type': 'blob'}
        if path.exists():
            blob = api('POST', f'repos/{repo}/git/blobs',
                       {'content': base64.b64encode(path.read_bytes()).decode(), 'encoding': 'base64'})
            item['sha'] = blob['sha']
        else:
            item['sha'] = None
        changes.append(item)
    # Retry starts from the original parent, with no local unpushed commit.
    git('restore', '--source=HEAD', '--staged', '--worktree', '--', log_dir)
    return base, tree, changes


def publish(repo, branch, log_dir, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        base, tree, changes = prepare_fold(repo, branch, log_dir)
        if not changes:
            return {'status': 'noop', 'attempts': attempt, 'base': base}
        created_tree = api('POST', f'repos/{repo}/git/trees', {'base_tree': tree, 'tree': changes})
        commit = api('POST', f'repos/{repo}/git/commits',
                     {'message': 'docs(devlog): fold pending entries', 'tree': created_tree['sha'], 'parents': [base]})
        if not commit.get('verification', {}).get('verified'):
            raise RuntimeError('App fold commit is not verified; refusing publication')
        try:
            api('PATCH', f'repos/{repo}/git/refs/heads/{urllib.parse.quote(branch, safe="")}',
                {'sha': commit['sha'], 'force': False})
        except ApiError as error:
            if error.status not in (409, 422) or remote_head(repo, branch) == base or attempt == max_attempts:
                raise
            continue
        # A concurrent later commit is fine; the accepted fast-forward is immutable.
        return {'status': 'folded', 'attempts': attempt, 'base': base, 'commit': commit['sha'], 'verified': True}
    raise RuntimeError('fold retry budget exhausted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--dir', default='docs/devlog')
    args = parser.parse_args()
    if os.environ.get('AGENT_RUNTIME_DEVLOG_FRAGMENTS', '0') != '1':
        print(json.dumps({'status': 'disabled'}))
        return
    log = Path(args.dir)
    if args.dir not in ('docs/devlog', 'docs/source/devlog') or not (log / 'README.md').is_file():
        parser.error('--dir must be docs/devlog or docs/source/devlog with an index')
    print(json.dumps(publish(args.repo, args.branch, args.dir), sort_keys=True))


if __name__ == '__main__':
    main()
