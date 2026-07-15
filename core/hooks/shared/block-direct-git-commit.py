#!/usr/bin/env python3
"""PreToolUse hook: block direct git commit invocations.

Agents should use semantic-commit so commit messages, validation, and
dirty-tree handling stay auditable.
"""

from __future__ import annotations

import re
import sys
from pathlib import PurePosixPath

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    emit_block,
    invocation_is_unresolved_nested,
    invocation_tokens,
    opaque_invocation_candidates,
    read_payload,
    simple_commands_with_nested_shells,
)

BLOCK_REASON = "Do not use git commit directly. Use semantic-commit instead."

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*")
GIT_OPTIONS_WITH_VALUE = {
    "-C",
    "-c",
    "--config-env",
    "--exec-path",
    "--git-dir",
    "--namespace",
    "--work-tree",
}
GIT_OPTIONS_WITH_VALUE_PREFIXES = (
    "--config-env=",
    "--exec-path=",
    "--git-dir=",
    "--namespace=",
    "--work-tree=",
)


def basename(token: str) -> str:
    return PurePosixPath(token).name


def is_assignment(token: str) -> bool:
    return bool(ASSIGNMENT_RE.match(token))


def skip_env_prefix(tokens: list[str], index: int) -> int:
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if is_assignment(token):
            index += 1
            continue
        if token in {"-i", "--ignore-environment", "-0", "--null"}:
            index += 1
            continue
        if token in {"-u", "--unset"}:
            index += 2
            continue
        if token.startswith("--unset="):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return index
    return index


def git_command_index(simple_command: list[str]) -> int | None:
    invocation = invocation_tokens(simple_command)
    if not invocation:
        return None
    return 0 if basename(invocation[0]) == "git" else None


def git_subcommand(simple_command: list[str]) -> str | None:
    invocation = invocation_tokens(simple_command)
    if not invocation or basename(invocation[0]) != "git":
        return None

    index = 1
    while index < len(invocation):
        token = invocation[index]
        if token == "--":
            return None
        if token in GIT_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            index += 1
            continue
        if token.startswith("-c") and token != "-c":
            index += 1
            continue
        if token.startswith(GIT_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return token
    return None


def invokes_git_commit(command: str) -> bool:
    for simple_command in simple_commands_with_nested_shells(command):
        if git_subcommand(simple_command) == "commit":
            return True
        invocation = invocation_tokens(simple_command)
        if invocation_is_unresolved_nested(invocation):
            return True
        if any(
            invocation_is_unresolved_nested(candidate)
            or git_subcommand(candidate) == "commit"
            for candidate in opaque_invocation_candidates(invocation, {"git"})
        ):
            return True
    return False


def main() -> int:
    command = command_from(read_payload())
    if command and invokes_git_commit(command):
        emit_block(BLOCK_REASON)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
