#!/usr/bin/env python3
"""PreToolUse hook: block direct git worktree invocations.

Agents should use git-cli worktree so worktree paths, branch names, JSON
contracts, and cleanup behavior stay consistent across sessions.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping
from pathlib import PurePosixPath

# Codex may execute hooks through a source symlink; keep the checkout clean.
sys.dont_write_bytecode = True

from hook_common import (
    ALLOW,
    command_from,
    emit_block,
    invocation_is_unresolved_nested,
    invocation_tokens,
    marker_environment_before_invocation,
    nested_shell_payload,
    opaque_invocation_candidates,
    read_payload,
    simple_commands,
)

BLOCK_REASON = (
    "Do not use mutating git worktree commands directly. Use git-cli worktree "
    "instead. Emergency override: prefix with ALLOW_DIRECT_GIT_WORKTREE=1."
)

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*")
MUTATING_WORKTREE_COMMANDS = {
    "add",
    "remove",
    "move",
    "prune",
    "repair",
    "lock",
    "unlock",
}
OVERRIDE_ENV_NAMES = (
    "ALLOW_DIRECT_GIT_WORKTREE",
    "AGENT_RUNTIME_ALLOW_DIRECT_GIT_WORKTREE",
)
TRUTHY_VALUES = {"1", "true", "yes"}
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
    found = git_subcommand_with_index(simple_command)
    return found[0] if found is not None else None


def git_subcommand_with_index(simple_command: list[str]) -> tuple[str, int] | None:
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
        return token, index
    return None


def git_worktree_action(simple_command: list[str]) -> str | None:
    invocation = invocation_tokens(simple_command)
    if not invocation:
        return None
    found = git_subcommand_with_index(simple_command)
    if found is None:
        return None
    subcommand, index = found
    if subcommand != "worktree":
        return None

    index += 1
    while index < len(invocation):
        token = invocation[index]
        if token == "--":
            return None
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return token
    return None


def process_override_environment() -> dict[str, str]:
    return {
        name: value
        for name in OVERRIDE_ENV_NAMES
        if (value := os.environ.get(name)) is not None
    }


def override_enabled(environment: Mapping[str, str]) -> bool:
    return any(
        environment.get(name, "").lower() in TRUTHY_VALUES
        for name in OVERRIDE_ENV_NAMES
    )


def invokes_git_worktree(
    command: str,
    *,
    inherited_overrides: Mapping[str, str] | None = None,
    depth: int = 0,
    max_depth: int = 5,
) -> bool:
    if depth > max_depth:
        return False
    base_environment = (
        dict(inherited_overrides)
        if inherited_overrides is not None
        else process_override_environment()
    )
    for simple_command in simple_commands(command):
        command_environment = marker_environment_before_invocation(
            simple_command, OVERRIDE_ENV_NAMES, base_environment
        )
        command_override = override_enabled(command_environment)
        invocation = invocation_tokens(simple_command)
        opaque_worktree_mutation = any(
            invocation_is_unresolved_nested(candidate)
            or git_worktree_action(candidate) in MUTATING_WORKTREE_COMMANDS
            for candidate in opaque_invocation_candidates(invocation, {"git"})
        )
        if (
            (
                git_worktree_action(simple_command) in MUTATING_WORKTREE_COMMANDS
                or opaque_worktree_mutation
            )
            and not command_override
        ):
            return True
        payload = nested_shell_payload(invocation)
        if payload and depth >= max_depth and not command_override:
            return True
        if payload and invokes_git_worktree(
            payload,
            inherited_overrides=command_environment,
            depth=depth + 1,
            max_depth=max_depth,
        ):
            return True
    return False


def main() -> int:
    command = command_from(read_payload())
    if command and invokes_git_worktree(command):
        emit_block(BLOCK_REASON)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
