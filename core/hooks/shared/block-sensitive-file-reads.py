#!/usr/bin/env python3
"""Refuse common value-printing shell reads of configured sensitive paths."""
from __future__ import annotations

import fnmatch
import os
import shlex
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from hook_common import (
    ALLOW,
    command_from,
    effective_workdir,
    emit_block,
    invocation_tokens,
    read_payload,
    scoped_simple_commands_with_nested_shells,
)

PATTERN_ENV = "AGENT_RUNTIME_SENSITIVE_PATH_PATTERNS"
DEFAULT_PATTERNS = ("*.env", "*.enc.*", "~/.ssh/*")
READERS = frozenset({"cat", "awk", "sed", "head", "tail", "less", "bat"})


def sensitive_patterns() -> tuple[str, ...]:
    configured = os.environ.get(PATTERN_ENV)
    return tuple(configured.splitlines()) if configured is not None else DEFAULT_PATTERNS


def matches_path(argument: str, cwd: Path, patterns: tuple[str, ...]) -> bool:
    path = os.path.expanduser(os.path.expandvars(argument))
    if not os.path.isabs(path):
        path = os.path.join(str(cwd), path)
    path = os.path.normpath(path)
    paths = (path, os.path.realpath(path))
    for pattern in patterns:
        if not pattern:
            continue
        expanded = os.path.expanduser(pattern)
        if any(fnmatch.fnmatchcase(candidate, expanded) for candidate in paths):
            return True
    return False


def main() -> int:
    payload = read_payload()
    cwd_by_scope = {(): effective_workdir(payload)}
    patterns = sensitive_patterns()
    for simple, scope in scoped_simple_commands_with_nested_shells(command_from(payload), strict=True):
        if scope not in cwd_by_scope:
            cwd_by_scope[scope] = cwd_by_scope.get(scope[:-1], cwd_by_scope[()])
        cwd = cwd_by_scope[scope]
        invocation = invocation_tokens(simple)
        if invocation and invocation[0] == "cd":
            args = invocation[1:]
            while args and args[0] in {"-L", "-P", "-e"}:
                args = args[1:]
            if args and args[0] == "--":
                args = args[1:]
            if len(args) <= 1 and args != ["-"]:
                target = os.path.expanduser(os.path.expandvars(args[0] if args else "~"))
                cwd_by_scope[scope] = Path(os.path.abspath(os.path.join(cwd, target)))
            continue
        if not invocation or Path(invocation[0]).name not in READERS:
            continue
        operands = []
        end_options = False
        for arg in invocation[1:]:
            if arg == "--" and not end_options:
                end_options = True
            elif end_options or not arg.startswith("-"):
                operands.append(arg)
        if any(matches_path(arg, cwd, patterns) for arg in operands):
            helper = shlex.quote(str(Path(__file__).with_name("secret-structure")))
            emit_block(f"Sensitive file read blocked. Use {helper} <file> to inspect names and line counts, or grep -c for counts.")
            return ALLOW
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
