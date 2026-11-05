#!/usr/bin/env python3
"""Resolve the coordination-selected session and its hook sibling."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True

HOOKS = Path(__file__).resolve().parents[2] / 'core/hooks/shared'
sys.path.insert(0, str(HOOKS))
spec = importlib.util.spec_from_file_location('coordination_guard', HOOKS / 'session-coordination-guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def selected_pair():
    session = guard.resolved_agent_session()
    if not session:
        return None, None
    candidates = [os.environ.get('AGENT_SESSION_BIN', '')]
    candidates.extend(str(Path(root) / 'agent-session') for root in os.environ.get('AGENT_RUNTIME_TRUSTED_CLI_ROOT', '').split(os.pathsep) if root and os.path.isabs(root))
    candidates.extend([shutil.which('agent-session') or '', session])
    for candidate in candidates:
        if candidate and os.path.realpath(candidate) == session:
            hook = Path(candidate).parent / 'agent-hook'
            if hook.is_file() and os.access(hook, os.X_OK):
                return session, str(hook.resolve())
    return session, None


if __name__ == '__main__':
    session, hook = selected_pair()
    if hook:
        print(hook)
    elif session or os.environ.get('AGENT_RUNTIME_TRUSTED_CLI_ROOT', '').strip() or os.environ.get('AGENT_SESSION_BIN', '').strip():
        print('selected agent-session pair is unavailable', file=sys.stderr)
        sys.exit(1)
    else:
        print('warning: no selected pair; using unselected PATH agent-hook', file=sys.stderr)
        fallback = shutil.which('agent-hook')
        print(os.path.abspath(fallback) if fallback else 'agent-hook')
