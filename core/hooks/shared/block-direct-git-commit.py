#!/usr/bin/env python3
"""PreToolUse hook: block direct git commit invocations.

Agents should use semantic-commit so commit messages, validation, and
dirty-tree handling stay auditable.
"""

from __future__ import annotations

import functools
import re
import subprocess
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
OPAQUE_REASON = (
    "Command intent could not be resolved safely. Classification: "
    "rule=opaque-executable; operation=dynamic-executable. A shell-expanded "
    "or opaque invocation can change the executable or subcommand; use a "
    "stable command name and literal arguments in a separate tool call."
)
ALIAS_REASON = (
    "Git subcommand dispatch could not be admitted safely. Classification: "
    "rule=git-alias-resolution; operation=dynamic-subcommand. A non-builtin "
    "subcommand or invocation-defined alias can resolve through configured or "
    "shell aliases to `commit`; use a literal Git builtin, or use "
    "semantic-commit for commit creation."
)

ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*")
GIT_SUBCOMMAND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
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


def token_is_dynamic(token: str) -> bool:
    """Whether shell expansion can change a parsed Git subcommand token."""
    return any(marker in token for marker in "$`*?[]{}()#^~")


def selected_inline_alias(simple_command: list[str]) -> str | None:
    """Return a selected alias defined by this Git invocation, if any."""
    invocation = invocation_tokens(simple_command)
    if not invocation or basename(invocation[0]) != "git":
        return None

    aliases: set[str] = set()
    index = 1
    while index < len(invocation):
        token = invocation[index]
        config: str | None = None
        if token == "-c":
            if index + 1 >= len(invocation):
                return None
            config = invocation[index + 1]
            index += 2
        elif token.startswith("-c") and token != "-c":
            config = token[2:]
            index += 1
        elif token == "--config-env":
            if index + 1 >= len(invocation):
                return None
            config = invocation[index + 1]
            index += 2
        elif token.startswith("--config-env="):
            config = token.removeprefix("--config-env=")
            index += 1
        elif token in GIT_OPTIONS_WITH_VALUE:
            index += 2
        elif token.startswith("-C") and token != "-C":
            index += 1
        elif token.startswith(GIT_OPTIONS_WITH_VALUE_PREFIXES):
            index += 1
        elif token.startswith("-") and token != "-":
            index += 1
        else:
            return token if token.lower() in aliases else None

        if config is not None:
            key = config.split("=", 1)[0].lower()
            if key.startswith("alias.") and len(key) > len("alias."):
                aliases.add(key.removeprefix("alias."))
    return None


@functools.lru_cache(maxsize=1)
def git_builtin_commands() -> frozenset[str]:
    """Return Git builtins under a bounded probe, with a conservative fallback."""
    fallback = frozenset(
        {
            "add",
            "branch",
            "checkout",
            "clone",
            "commit",
            "config",
            "diff",
            "fetch",
            "grep",
            "init",
            "log",
            "merge",
            "mv",
            "pull",
            "push",
            "rebase",
            "reset",
            "restore",
            "rev-parse",
            "rm",
            "show",
            "status",
            "switch",
            "tag",
            "worktree",
        }
    )
    try:
        completed = subprocess.run(
            ["git", "--list-cmds=builtins"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return fallback
    if completed.returncode != 0 or len(completed.stdout) > 1024 * 1024:
        return fallback
    return fallback | frozenset(completed.stdout.split())


def git_commit_block_reason(command: str) -> str:
    for simple_command in simple_commands_with_nested_shells(command):
        if selected_inline_alias(simple_command) is not None:
            return ALIAS_REASON
        subcommand = git_subcommand(simple_command)
        if subcommand == "commit":
            return BLOCK_REASON
        if subcommand is not None and token_is_dynamic(subcommand):
            return OPAQUE_REASON
        if (
            subcommand is not None
            and GIT_SUBCOMMAND_RE.fullmatch(subcommand)
            and subcommand not in git_builtin_commands()
        ):
            return ALIAS_REASON
        invocation = invocation_tokens(simple_command)
        if invocation_is_unresolved_nested(invocation):
            return OPAQUE_REASON
        for candidate in opaque_invocation_candidates(invocation, {"git"}):
            if selected_inline_alias(candidate) is not None:
                return ALIAS_REASON
            candidate_subcommand = git_subcommand(candidate)
            if candidate_subcommand == "commit":
                return BLOCK_REASON
            if candidate_subcommand is not None and token_is_dynamic(
                candidate_subcommand
            ):
                return OPAQUE_REASON
            if (
                candidate_subcommand is not None
                and GIT_SUBCOMMAND_RE.fullmatch(candidate_subcommand)
                and candidate_subcommand not in git_builtin_commands()
            ):
                return ALIAS_REASON
            if invocation_is_unresolved_nested(candidate):
                return OPAQUE_REASON
    return ""


def invokes_git_commit(command: str) -> bool:
    return bool(git_commit_block_reason(command))


def main() -> int:
    command = command_from(read_payload())
    reason = git_commit_block_reason(command) if command else ""
    if reason:
        emit_block(reason)
    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
